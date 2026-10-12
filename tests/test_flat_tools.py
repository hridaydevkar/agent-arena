"""Integration tests for the simplified flat tool interface.

All tests are deterministic — no real model calls. They exercise the
_dispatch_flat_tool adapter layer and the mock-model solver dispatch.
"""

import json
import httpx
import pytest

from agent_arena import Task, ToolContext
from arena_server.agents import ModelAgent, _dispatch_flat_tool, _coerce_filter_value, _normalize_tool_args, _parse_freetext_filter
from arena_server.data_tools import analyze_records
from arena_server.engine import TASK_MAP


# ── Synthetic fixtures (not the invoice task, proving generality) ──

@pytest.fixture
def order_fixtures():
    return {
        "orders": [
            {"id": "ORD-1", "amount": 500, "status": "shipped", "region": "US"},
            {"id": "ORD-2", "amount": 300, "status": "cancelled", "region": "EU"},
            {"id": "ORD-3", "amount": 700, "status": "shipped", "region": "US"},
            {"id": "ORD-4", "amount": 200, "status": "shipped", "region": "EU"},
        ],
        "refunds": [
            {"refund_id": "R1", "order_id": "ORD-1", "amount": 100},
            {"refund_id": "R1", "order_id": "ORD-1", "amount": 100},  # duplicate
            {"refund_id": "R2", "order_id": "ORD-3", "amount": 50},
        ],
    }


# Also keep the invoice fixtures for the invoice-specific test
@pytest.fixture
def invoice_fixtures():
    return {
        "invoices": [
            {"id": "INV-101", "amount": 1200, "status": "open"},
            {"id": "INV-102", "amount": 800, "status": "open"},
            {"id": "INV-103", "amount": 500, "status": "void"},
            {"id": "INV-104", "amount": 600, "status": "open"},
        ],
        "payments": [
            {"payment_id": "P1", "invoice_id": "INV-101", "amount": 1200},
            {"payment_id": "P2", "invoice_id": "INV-102", "amount": 300},
            {"payment_id": "P2", "invoice_id": "INV-102", "amount": 300},
            {"payment_id": "P3", "invoice_id": "INV-103", "amount": 500},
        ],
    }


class FakeToolContext:
    """Minimal stub for ToolContext in dispatch tests."""
    def record(self, kind, name, metadata, fn):
        return fn()


# ── _dispatch_flat_tool unit tests ──

def test_filter_records_dispatch(order_fixtures):
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "filter_records",
        {"table": "orders", "column": "orders.status", "op": "eq", "value": "shipped"},
        order_fixtures,
        ctx,
        order_fixtures,
    )
    assert len(result["rows"]) == 3
    assert all(r["orders.status"] == "shipped" for r in result["rows"])


def test_sum_column_dispatch(order_fixtures):
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "sum_column",
        {
            "table": "orders",
            "column": "orders.amount",
            "filter_column": "orders.status",
            "filter_op": "eq",
            "filter_value": "shipped",
        },
        order_fixtures,
        ctx,
        order_fixtures,
    )
    assert result == {"total": 500 + 700 + 200}


def test_sum_column_without_filter(order_fixtures):
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "sum_column",
        {"table": "orders", "column": "orders.amount"},
        order_fixtures,
        ctx,
        order_fixtures,
    )
    assert result == {"total": 500 + 300 + 700 + 200}


def test_join_and_aggregate_dispatch(order_fixtures):
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "left_table": "orders",
            "right_table": "refunds",
            "left_on": "orders.id",
            "right_on": "refunds.order_id",
            "how": "inner",
            "dedup_column": "refunds.refund_id",
            "agg_op": "sum",
            "agg_column": "refunds.amount",
        },
        order_fixtures,
        ctx,
        order_fixtures,
    )
    # After dedup: R1=100 for ORD-1, R2=50 for ORD-3 => total 150
    rows = result["rows"]
    assert len(rows) == 1  # no grouping, single aggregate
    assert rows[0]["amount"] == 150


def test_join_and_aggregate_with_group(order_fixtures):
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "left_table": "orders",
            "right_table": "refunds",
            "left_on": "orders.id",
            "right_on": "refunds.order_id",
            "how": "inner",
            "dedup_column": "refunds.refund_id",
            "group_column": "orders.id",
            "agg_op": "sum",
            "agg_column": "refunds.amount",
        },
        order_fixtures,
        ctx,
        order_fixtures,
    )
    rows = result["rows"]
    assert len(rows) == 2
    by_id = {r["id"]: r for r in rows}
    assert by_id["ORD-1"]["amount"] == 100
    assert by_id["ORD-3"]["amount"] == 50


def test_list_column_dispatch(order_fixtures):
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "list_column",
        {
            "table": "orders",
            "column": "orders.id",
            "filter_column": "orders.status",
            "filter_op": "eq",
            "filter_value": "shipped",
            "sort": "asc",
        },
        order_fixtures,
        ctx,
        order_fixtures,
    )
    assert result["values"] == ["ORD-1", "ORD-3", "ORD-4"]


def test_list_column_without_filter(order_fixtures):
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "list_column",
        {"table": "orders", "column": "orders.id", "sort": "asc"},
        order_fixtures,
        ctx,
        order_fixtures,
    )
    assert result["values"] == ["ORD-1", "ORD-2", "ORD-3", "ORD-4"]


# ── Error handling tests ──

def test_dispatch_unknown_tool_raises(order_fixtures):
    ctx = FakeToolContext()
    with pytest.raises(ValueError, match="Unknown data tool"):
        _dispatch_flat_tool("bogus_tool", {}, order_fixtures, ctx, order_fixtures)


def test_dispatch_missing_fixtures_raises(order_fixtures):
    ctx = FakeToolContext()
    # task_inputs has a fixture "missing" that is not in fixture_data
    with pytest.raises(ValueError, match="Read all task fixtures"):
        _dispatch_flat_tool(
            "filter_records",
            {"table": "orders", "column": "orders.status", "op": "eq", "value": "shipped"},
            order_fixtures,
            ctx,
            {**order_fixtures, "missing": []},
        )


def test_dispatch_invalid_table_raises(order_fixtures):
    ctx = FakeToolContext()
    with pytest.raises(ValueError, match="supplied fixtures"):
        _dispatch_flat_tool(
            "filter_records",
            {"table": "nonexistent", "column": "x", "op": "eq", "value": "y"},
            order_fixtures,
            ctx,
            order_fixtures,
        )


def test_dispatch_invalid_column_raises(order_fixtures):
    ctx = FakeToolContext()
    with pytest.raises(ValueError, match="Unknown column"):
        _dispatch_flat_tool(
            "sum_column",
            {"table": "orders", "column": "orders.nonexistent"},
            order_fixtures,
            ctx,
            order_fixtures,
        )


# ── Type coercion tests ──

def test_coerce_filter_value_numeric():
    fixtures = {"t": [{"x": 42}]}
    assert _coerce_filter_value("10", fixtures, "t", "t.x") == 10
    assert _coerce_filter_value("3.5", fixtures, "t", "t.x") == 3.5


def test_coerce_filter_value_string():
    fixtures = {"t": [{"x": "hello"}]}
    assert _coerce_filter_value("world", fixtures, "t", "t.x") == "world"


def test_coerce_filter_value_missing_table():
    assert _coerce_filter_value("val", {}, "t", "t.x") == "val"


# ── Invoice reconciliation via flat tools (proving correctness) ──

def test_invoice_reconciliation_via_flat_tools(invoice_fixtures):
    """Verify the flat tools can compute the correct invoice answer, equivalent
    to what a model would do if it called the tools correctly."""
    ctx = FakeToolContext()

    # Step 1: billed_total — sum non-void invoices
    billed = _dispatch_flat_tool(
        "sum_column",
        {
            "table": "invoices",
            "column": "invoices.amount",
            "filter_column": "invoices.status",
            "filter_op": "ne",
            "filter_value": "void",
        },
        invoice_fixtures, ctx, invoice_fixtures,
    )
    assert billed["total"] == 2600

    # Step 2: paid_total — join deduped payments with non-void invoices
    paid = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "left_table": "payments",
            "right_table": "invoices",
            "left_on": "payments.invoice_id",
            "right_on": "invoices.id",
            "how": "inner",
            "dedup_column": "payments.payment_id",
            "filter_column": "invoices.status",
            "filter_op": "eq",
            "filter_value": "open",
            "agg_op": "sum",
            "agg_column": "payments.amount",
        },
        invoice_fixtures, ctx, invoice_fixtures,
    )
    assert paid["rows"][0]["amount"] == 1500

    # Step 3: outstanding = billed - paid
    outstanding = billed["total"] - paid["rows"][0]["amount"]
    assert outstanding == 1100

    # Step 4: unpaid_invoice_ids via join + balance computation
    balance_result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "left_table": "invoices",
            "right_table": "payments",
            "left_on": "invoices.id",
            "right_on": "payments.invoice_id",
            "how": "left",
            "dedup_column": "payments.payment_id",
            "filter_column": "invoices.status",
            "filter_op": "ne",
            "filter_value": "void",
            "group_column": "invoices.id",
            "agg_op": "sum",
            "agg_column": "payments.amount",
        },
        invoice_fixtures, ctx, invoice_fixtures,
    )
    # Find invoices where amount > paid (i.e. positive balance)
    unpaid_ids = []
    for row in balance_result["rows"]:
        inv_id = row.get("id")
        paid_amt = row.get("amount", 0) or 0
        # We need the original invoice amount; it's in the group key
        inv_amount = None
        for inv in invoice_fixtures["invoices"]:
            if inv["id"] == inv_id:
                inv_amount = inv["amount"]
                break
        if inv_amount is not None and inv_amount > paid_amt:
            unpaid_ids.append(inv_id)
    unpaid_ids.sort()
    assert unpaid_ids == ["INV-102", "INV-104"]


# ── Mock-model solver integration test ──

def _patch_model_transport(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(
        "arena_server.agents.httpx.Client",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


def test_flat_tools_mock_model_solver(monkeypatch):
    """Full solver loop with mocked model responses using the new flat tools.
    The model reads fixtures, calls sum_column, and returns the answer."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("ARENA_READ_ONLY", raising=False)

    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        n = len(requests)

        if n == 1:
            # Model reads both fixtures
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "r1", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"invoices"}'}},
                    {"id": "r2", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"payments"}'}},
                ],
            }
        elif n == 2:
            # Model calls sum_column for billed_total
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "s1",
                        "type": "function",
                        "function": {
                            "name": "sum_column",
                            "arguments": json.dumps({
                                "table": "invoices",
                                "column": "invoices.amount",
                                "filter_column": "invoices.status",
                                "filter_op": "ne",
                                "filter_value": "void",
                            }),
                        },
                    },
                    {
                        "id": "s2",
                        "type": "function",
                        "function": {
                            "name": "join_and_aggregate",
                            "arguments": json.dumps({
                                "left_table": "payments",
                                "right_table": "invoices",
                                "left_on": "payments.invoice_id",
                                "right_on": "invoices.id",
                                "how": "inner",
                                "dedup_column": "payments.payment_id",
                                "filter_column": "invoices.status",
                                "filter_op": "eq",
                                "filter_value": "open",
                                "agg_op": "sum",
                                "agg_column": "payments.amount",
                            }),
                        },
                    },
                ],
            }
        else:
            # Model returns final answer
            msg = {
                "role": "assistant",
                "content": json.dumps({
                    "billed_total": 2600,
                    "paid_total": 1500,
                    "outstanding_total": 1100,
                    "unpaid_invoice_ids": ["INV-102", "INV-104"],
                }),
            }

        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [{"message": msg, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )

    _patch_model_transport(monkeypatch, handler)
    task = Task.from_dict(TASK_MAP["invoice-reconciliation"])
    tools = ToolContext(task)
    result = ModelAgent("test/model", "tools", 6, 1800).run(task, tools)

    assert result.output["billed_total"] == 2600
    assert result.output["paid_total"] == 1500
    assert result.output["outstanding_total"] == 1100
    assert result.output["unpaid_invoice_ids"] == ["INV-102", "INV-104"]
    assert len(requests) == 3


def test_flat_tools_mock_model_verify_architecture(monkeypatch):
    """Full verify architecture with mocked model using flat tools."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("ARENA_READ_ONLY", raising=False)

    requests = []
    correct_answer = json.dumps({
        "billed_total": 2600,
        "paid_total": 1500,
        "outstanding_total": 1100,
        "unpaid_invoice_ids": ["INV-102", "INV-104"],
    })

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        n = len(requests)

        if n == 1:
            # Solver reads fixtures
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "r1", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"invoices"}'}},
                    {"id": "r2", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"payments"}'}},
                ],
            }
        elif n == 2:
            # Solver returns draft (deliberately wrong to test verifier)
            msg = {
                "role": "assistant",
                "content": json.dumps({
                    "billed_total": 9999,
                    "paid_total": 0,
                    "outstanding_total": 9999,
                    "unpaid_invoice_ids": ["INV-101"],
                }),
            }
        elif n == 3:
            # Verifier calls sum_column to independently check
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "v1",
                        "type": "function",
                        "function": {
                            "name": "sum_column",
                            "arguments": json.dumps({
                                "table": "invoices",
                                "column": "invoices.amount",
                                "filter_column": "invoices.status",
                                "filter_op": "ne",
                                "filter_value": "void",
                            }),
                        },
                    },
                ],
            }
        else:
            # Verifier returns corrected answer
            msg = {"role": "assistant", "content": correct_answer}

        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [{"message": msg, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )

    _patch_model_transport(monkeypatch, handler)
    task = Task.from_dict(TASK_MAP["invoice-reconciliation"])
    tools = ToolContext(task)
    result = ModelAgent("test/model", "verify", 6, 1800).run(task, tools)

    assert result.output["billed_total"] == 2600
    assert result.output["paid_total"] == 1500
    assert result.output["outstanding_total"] == 1100
    assert result.output["unpaid_invoice_ids"] == ["INV-102", "INV-104"]
    assert len(requests) == 4  # 2 solver + 2 verifier
    # Verify that a verification event was recorded
    assert any(e.name.endswith(".verification") for e in tools.events)


def test_repeated_flat_tool_failure_is_stopped(monkeypatch):
    """An identical failed flat tool request must not execute twice."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("ARENA_READ_ONLY", raising=False)

    requests = []
    # This tool call is invalid (bad table name)
    bad_tool_args = json.dumps({
        "table": "nonexistent",
        "column": "x",
        "op": "eq",
        "value": "y",
    })

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        n = len(requests)

        if n == 1:
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "r1", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"invoices"}'}},
                    {"id": "r2", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"payments"}'}},
                ],
            }
        else:
            # Model keeps calling filter_records with same bad args
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": f"f{n}", "type": "function", "function": {"name": "filter_records", "arguments": bad_tool_args}},
                ],
            }

        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [{"message": msg, "finish_reason": "tool_calls"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10},
            },
        )

    _patch_model_transport(monkeypatch, handler)
    task = Task.from_dict(TASK_MAP["invoice-reconciliation"])
    tools = ToolContext(task)

    with pytest.raises(ValueError, match="repeated a previously failed tool request"):
        ModelAgent("test/model", "tools", 6, 1800).run(task, tools)

    # First call reads fixtures, second call has the bad tool (first attempt),
    # third call would have the bad tool (repeat) which gets caught
    assert len(requests) == 3


def test_truncated_response_with_valid_tool_calls(monkeypatch):
    """A truncated completion containing valid read_fixture calls should be processed."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("ARENA_READ_ONLY", raising=False)

    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        n = len(requests)

        if n == 1:
            # Truncated response but with valid tool calls
            msg = {
                "role": "assistant",
                "content": "some garbled text that got cut off...",
                "tool_calls": [
                    {"id": "r1", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"shipment"}'}},
                ],
            }
            finish = "length"
        else:
            msg = {"role": "assistant", "content": '{"carrier":"Cargo","total_cost":20,"delivery_days":3}'}
            finish = "stop"

        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [{"message": msg, "finish_reason": finish}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10},
            },
        )

    _patch_model_transport(monkeypatch, handler)
    task = Task.from_dict(TASK_MAP["shipping-planner"])
    tools = ToolContext(task)
    result = ModelAgent("test/model", "tools", 4, 1024).run(task, tools)
    assert result.output == {"carrier": "Cargo", "total_cost": 20, "delivery_days": 3}


def test_unknown_tool_name_returns_error_message(monkeypatch):
    """If the model calls a tool that doesn't exist, it should get a helpful error, not crash."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("ARENA_READ_ONLY", raising=False)

    requests = []

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        n = len(requests)

        if n == 1:
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "r1", "type": "function", "function": {"name": "read_fixture", "arguments": '{"name":"shipment"}'}},
                ],
            }
        elif n == 2:
            # Model calls a non-existent tool
            msg = {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "bad", "type": "function", "function": {"name": "analyze_records", "arguments": '{"table":"shipment"}'}},
                ],
            }
        else:
            msg = {"role": "assistant", "content": '{"carrier":"Cargo","total_cost":20,"delivery_days":3}'}

        return httpx.Response(
            200,
            json={
                "model": "test/model",
                "choices": [{"message": msg, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10},
            },
        )

    _patch_model_transport(monkeypatch, handler)
    task = Task.from_dict(TASK_MAP["shipping-planner"])
    tools = ToolContext(task)
    result = ModelAgent("test/model", "tools", 6, 1024).run(task, tools)
    # The model should have received an error and then produced the correct answer
    assert result.output == {"carrier": "Cargo", "total_cost": 20, "delivery_days": 3}


# ── Separate run isolation test ──

def test_separate_runs_do_not_share_state(order_fixtures, invoice_fixtures):
    """Two dispatch calls with different fixtures produce independent results."""
    ctx = FakeToolContext()

    result1 = _dispatch_flat_tool(
        "sum_column",
        {"table": "orders", "column": "orders.amount"},
        order_fixtures, ctx, order_fixtures,
    )

    result2 = _dispatch_flat_tool(
        "sum_column",
        {"table": "invoices", "column": "invoices.amount"},
        invoice_fixtures, ctx, invoice_fixtures,
    )

    assert result1["total"] == 500 + 300 + 700 + 200  # 1700
    assert result2["total"] == 1200 + 800 + 500 + 600  # 3100
    assert result1["total"] != result2["total"]


# ── parse_output type coercion tests ──

def test_parse_output_coerces_string_list():
    """Model returns unpaid_invoice_ids as '["INV-102","INV-104"]' string."""
    content = json.dumps({
        "billed_total": 2600,
        "paid_total": 1500,
        "outstanding_total": 1100,
        "unpaid_invoice_ids": '["INV-102", "INV-104"]',
    })
    schema = {"billed_total": "int", "paid_total": "int", "outstanding_total": "int", "unpaid_invoice_ids": "list"}
    output = ModelAgent.parse_output(content, schema)
    assert output["unpaid_invoice_ids"] == ["INV-102", "INV-104"]
    assert isinstance(output["unpaid_invoice_ids"], list)


def test_parse_output_coerces_string_int():
    """Model returns numeric fields as strings like '2600'."""
    content = json.dumps({"count": "42"})
    output = ModelAgent.parse_output(content, {"count": "int"})
    assert output["count"] == 42
    assert type(output["count"]) is int


def test_parse_output_coerces_float_to_int():
    """Model returns 2600.0 instead of 2600."""
    content = json.dumps({"total": 2600.0})
    output = ModelAgent.parse_output(content, {"total": "int"})
    assert output["total"] == 2600
    assert type(output["total"]) is int


def test_parse_output_rejects_truly_wrong_types():
    """A dict where a list is expected should still fail."""
    content = json.dumps({"items": {"a": 1}})
    with pytest.raises(ValueError, match="schema mismatch"):
        ModelAgent.parse_output(content, {"items": "list"})


def test_parse_output_rejects_non_parseable_string():
    """A plain string that can't be parsed as JSON list should still fail."""
    content = json.dumps({"items": "not a list at all"})
    with pytest.raises(ValueError, match="schema mismatch"):
        ModelAgent.parse_output(content, {"items": "list"})


# ── Argument normalization tests ──

def test_normalize_qualifies_bare_column():
    result = _normalize_tool_args("sum_column", {"table": "invoices", "column": "amount"})
    assert result["column"] == "invoices.amount"


def test_normalize_preserves_qualified_column():
    result = _normalize_tool_args("sum_column", {"table": "invoices", "column": "invoices.amount"})
    assert result["column"] == "invoices.amount"


def test_normalize_parses_freetext_filter():
    result = _normalize_tool_args(
        "sum_column",
        {"table": "invoices", "column": "amount", "filter": 'status != "void"'},
    )
    assert result["filter_column"] == "invoices.status"
    assert result["filter_op"] == "ne"
    assert result["filter_value"] == "void"


def test_normalize_parses_condition_filter():
    result = _normalize_tool_args(
        "filter_records",
        {"table": "orders", "condition": "region == US"},
    )
    assert result["filter_column"] == "orders.region"
    assert result["filter_op"] == "eq"
    assert result["filter_value"] == "US"


def test_normalize_join_qualifies_columns():
    result = _normalize_tool_args(
        "join_and_aggregate",
        {
            "left_table": "invoices",
            "right_table": "payments",
            "left_on": "id",
            "right_on": "invoice_id",
            "how": "left",
            "dedup_column": "payment_id",
            "agg_column": "amount",
            "group_column": "id",
        },
    )
    assert result["left_on"] == "invoices.id"
    assert result["right_on"] == "payments.invoice_id"
    assert result["dedup_column"] == "payments.payment_id"
    assert result["agg_column"] == "payments.amount"
    assert result["group_column"] == "invoices.id"


def test_sum_column_with_freetext_filter_end_to_end(invoice_fixtures):
    """Reproduce the exact model failure: sum_column with bare column + freetext filter."""
    ctx = FakeToolContext()
    # This is what llama3.2:3b actually sends:
    result = _dispatch_flat_tool(
        "sum_column",
        {"table": "invoices", "column": "amount", "filter": 'status != "void"'},
        invoice_fixtures,
        ctx,
        invoice_fixtures,
    )
    # Should filter out void invoices: 1200 + 800 + 600 = 2600
    assert result["total"] == 2600


def test_parse_freetext_ne():
    result = _parse_freetext_filter('status != "void"', "invoices")
    assert result == {"filter_column": "invoices.status", "filter_op": "ne", "filter_value": "void"}


def test_parse_freetext_eq():
    result = _parse_freetext_filter('status == "open"', "invoices")
    assert result == {"filter_column": "invoices.status", "filter_op": "eq", "filter_value": "open"}


def test_parse_freetext_gt():
    result = _parse_freetext_filter('amount > 500', "orders")
    assert result == {"filter_column": "orders.amount", "filter_op": "gt", "filter_value": "500"}


def test_join_and_aggregate_model_shorthand_end_to_end(invoice_fixtures):
    """Test join_and_aggregate with shorthand parameters and explicit dedup.

    Model sends shorthand:
    columns="['amount']", join="invoice_id", group="invoice_id", table="invoices", dedup="payment_id", filter='status != "void"'
    """
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "columns": "['amount']",
            "join": "invoice_id",
            "group": "invoice_id",
            "table": "invoices",
            "dedup": "payment_id",
            "filter": 'status != "void"',
        },
        invoice_fixtures,
        ctx,
        invoice_fixtures,
    )
    # Check that it auto-joined, applied explicit dedup, filtered void, and produced generic aggregate
    assert result["total"] == 1500
    raw_rows = {r["id"]: r for r in result["rows"]}
    assert raw_rows["INV-101"]["amount"] == 1200
    assert raw_rows["INV-102"]["amount"] == 300
    assert raw_rows["INV-104"]["amount"] == 0
    # Verify no invoice-specific fields are injected
    assert "paid_total" not in result
    assert "billed_total" not in result
    assert "outstanding_total" not in result
    assert "unpaid_ids" not in result
    assert "balance" not in raw_rows["INV-101"]


def test_join_and_aggregate_shorthand_without_group(invoice_fixtures):
    """join_and_aggregate shorthand without grouping returns paid total with explicit dedup."""
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "columns": "amount",
            "join": "invoice_id",
            "table": "invoices",
            "dedup": "payment_id",
            "filter": 'status != "void"',
        },
        invoice_fixtures,
        ctx,
        invoice_fixtures,
    )
    assert result["total"] == 1500


