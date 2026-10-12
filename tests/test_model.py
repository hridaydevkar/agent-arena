import json
import sqlite3

import httpx
import pytest
from agent_arena import Task, ToolContext, evaluate
from arena_server.agents import (
    ModelAgent,
    _execute_readonly_fixture_query,
)
from arena_server.engine import TASK_MAP


def test_real_adapter_with_mock_provider(monkeypatch):
    """Validates wire protocol and token accounting without making paid model calls."""
    monkeypatch.setenv("OPENAI_API_KEY", "unit-test-secret")
    monkeypatch.setenv("OPENAI_MODEL", "pinned-test-model")
    monkeypatch.setenv("ARENA_INPUT_PRICE", "1")
    monkeypatch.setenv("ARENA_OUTPUT_PRICE", "2")
    calls = []

    def handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        assert request.headers["Authorization"] == "Bearer unit-test-secret"
        assert payload["model"] == "pinned-test-model"
        if len(calls) == 1:
            msg = {
                "role": "assistant",
                "content": None,
                "reasoning_content": "must not persist",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "read_fixture", "arguments": '{"name":"shipment"}'},
                    }
                ],
            }
        else:
            assert payload["messages"][-1]["role"] == "tool"
            msg = {"role": "assistant", "content": '{"carrier":"Cargo","total_cost":20,"delivery_days":3}'}
        return httpx.Response(
            200, json={"choices": [{"message": msg}], "usage": {"prompt_tokens": 100, "completion_tokens": 20}}
        )

    original = httpx.Client
    monkeypatch.setattr(
        "arena_server.agents.httpx.Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )
    definition = TASK_MAP["shipping-planner"]
    task = Task.from_dict(definition)
    tools = ToolContext(task)
    result = ModelAgent("pinned-test-model").run(task, tools)
    assert evaluate(result.output, definition["expected"])["passed"]
    assert len(calls) == 2
    assert tools.input_tokens == 200 and tools.output_tokens == 40
    assert tools.cost_usd == pytest.approx(0.00028)
    trace = json.dumps(tools.trace())
    assert "must not persist" not in trace and "unit-test-secret" not in trace
    assert any(e.kind == "llm" for e in tools.events)


def test_model_requires_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    task = Task.from_dict(TASK_MAP["shipping-planner"])
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        ModelAgent("test").run(task, ToolContext(task))
def test_repeated_failed_calculator_call_is_stopped(monkeypatch):
    """An identical failed calculator request must not execute twice."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("OPENAI_MODEL", "llama3.2:3b")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("ARENA_READ_ONLY", raising=False)

    requests = []
    bad_args = json.dumps({
        "expression": "sum(invoices.amount)"
    })

    def handler(request):
        requests.append(json.loads(request.content))
        n = len(requests)

        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [{
                "id": f"calc-{n}",
                "type": "function",
                "function": {
                    "name": "calculate",
                    "arguments": bad_args,
                },
            }],
        }

        return httpx.Response(
            200,
            json={
                "choices": [{
                    "message": message,
                    "finish_reason": "tool_calls",
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                },
            },
        )

    original = httpx.Client
    monkeypatch.setattr(
        "arena_server.agents.httpx.Client",
        lambda **kwargs: original(
            transport=httpx.MockTransport(handler),
            **kwargs,
        ),
    )

    task = Task.from_dict(TASK_MAP["invoice-reconciliation"])
    tools = ToolContext(task)

    with pytest.raises(
        ValueError,
        match="repeated a previously failed tool request",
    ):
        ModelAgent(
            "llama3.2:3b",
            "tools",
            max_calls=4,
            max_output_tokens=1800,
        ).run(task, tools)

    assert len(requests) == 2
    assert sum(
        event.name == "calculator.evaluate"
        for event in tools.events
    ) == 1


def test_readonly_sql_cte_invoice_query():
    fixtures = {
        "invoices": [
            {"id": "INV-101", "amount": 1200, "status": "paid"},
            {"id": "INV-102", "amount": 800, "status": "active"},
            {"id": "INV-103", "amount": 500, "status": "void"},
            {"id": "INV-104", "amount": 300, "status": "active"},
        ],
        "payments": [
            {"payment_id": "P-1", "invoice_id": "INV-101", "amount": 1200},
            {"payment_id": "P-2", "invoice_id": "INV-101", "amount": 1200},
            {"payment_id": "P-3", "invoice_id": "INV-104", "amount": 150},
        ],
    }
    unpaid_query = """
    WITH active_invoices AS (
        SELECT id, amount
        FROM invoices
        WHERE status <> 'void'
    ),
    ranked_payments AS (
        SELECT payment_id, invoice_id, amount,
               ROW_NUMBER() OVER (
                   PARTITION BY payment_id ORDER BY rowid
               ) AS rn
        FROM payments
    ),
    valid_payments AS (
        SELECT p.invoice_id, p.amount
        FROM ranked_payments p
        JOIN active_invoices i ON i.id = p.invoice_id
        WHERE p.rn = 1
    )
    SELECT i.id AS invoice_id
    FROM active_invoices i
    LEFT JOIN valid_payments p ON p.invoice_id = i.id
    GROUP BY i.id, i.amount
    HAVING i.amount > COALESCE(SUM(p.amount), 0)
    ORDER BY i.id
    """
    unpaid = _execute_readonly_fixture_query(unpaid_query, fixtures)
    assert [row["invoice_id"] for row in unpaid["rows"]] == ["INV-102", "INV-104"]


def test_readonly_sql_rejects_write_queries():
    fixtures = {
        "invoices": [{"id": "INV-101", "amount": 1200}]
    }
    with pytest.raises(ValueError, match="read-only"):
        _execute_readonly_fixture_query(
            "DELETE FROM invoices",
            fixtures,
        )


def test_readonly_sql_cannot_read_sqlite_internal_tables():
    fixtures = {
        "invoices": [{"id": "INV-101", "amount": 1200}]
    }
    with pytest.raises(sqlite3.DatabaseError):
        _execute_readonly_fixture_query(
            "SELECT name FROM sqlite_master",
            fixtures,
        )


def test_readonly_sql_supports_bound_parameters():
    fixtures = {
        "invoices": [
            {"id": "INV-101", "amount": 1200, "status": "open"},
            {"id": "INV-103", "amount": 500, "status": "void"},
        ]
    }
    result = _execute_readonly_fixture_query(
        "SELECT SUM(amount) AS total FROM invoices WHERE status = ?",
        fixtures,
        ["open"],
    )
    assert result["rows"] == [{"total": 1200}]


def test_readonly_sql_accepts_legacy_string_parameters():
    fixtures = {
        "invoices": [
            {"id": "INV-101", "amount": 1200, "status": "open"},
            {"id": "INV-103", "amount": 500, "status": "void"},
        ]
    }
    result = _execute_readonly_fixture_query(
        "SELECT SUM(amount) AS total FROM invoices WHERE status = ?",
        fixtures,
        "['open']",
    )
    assert result["rows"] == [{"total": 1200}]