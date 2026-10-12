"""Deterministic regression tests for general-purpose tool behavior and deduplication semantics.

Tests cover:
1. Multiple legitimate child rows sharing a foreign key (must NOT be auto-deduplicated).
2. Explicit deduplication by a designated unique key (e.g. txn_id or payment_id).
3. Single-table sum_column retains all rows unless explicitly asked to deduplicate.
4. Filtering, aggregation, and listing on a synthetic inventory dataset.
5. Strict output schema type coercion and malformed argument rejection.
6. Independent verification correcting an intentionally wrong draft without model calls.
"""

import json
import pytest
from agent_arena import ToolContext, evaluate
from arena_server.agents import (
    ModelAgent,
    _coerce_filter_value,
    _dispatch_flat_tool,
    _normalize_tool_args,
    _parse_freetext_filter,
)
from arena_server.data_tools import analyze_records


class FakeToolContext:
    def record(self, kind, name, metadata, fn):
        return fn()

    def note(self, text):
        pass


@pytest.fixture
def department_fixtures():
    """Departments and employees: multiple employees legitimately share dept_id."""
    return {
        "departments": [
            {"id": "D1", "name": "Engineering"},
            {"id": "D2", "name": "Sales"},
        ],
        "employees": [
            {"emp_id": "E1", "dept_id": "D1", "salary": 100},
            {"emp_id": "E2", "dept_id": "D1", "salary": 120},
            {"emp_id": "E3", "dept_id": "D1", "salary": 110},
            {"emp_id": "E4", "dept_id": "D2", "salary": 90},
        ],
    }


@pytest.fixture
def department_with_duplicate_emp_fixtures():
    """Employees where E2 is duplicated, but E1, E2, E3 legitimately share D1."""
    return {
        "departments": [
            {"id": "D1", "name": "Engineering"},
            {"id": "D2", "name": "Sales"},
        ],
        "employees": [
            {"emp_id": "E1", "dept_id": "D1", "salary": 100},
            {"emp_id": "E2", "dept_id": "D1", "salary": 120},
            {"emp_id": "E2", "dept_id": "D1", "salary": 120},  # duplicate record
            {"emp_id": "E3", "dept_id": "D1", "salary": 110},
            {"emp_id": "E4", "dept_id": "D2", "salary": 90},
        ],
    }


@pytest.fixture
def inventory_fixtures():
    """Synthetic inventory dataset completely unrelated to invoices or orders."""
    return {
        "warehouses": [
            {"code": "WH-A", "region": "North", "active": True},
            {"code": "WH-B", "region": "South", "active": True},
            {"code": "WH-C", "region": "North", "active": False},
        ],
        "inventory": [
            {"sku": "SKU-101", "wh_code": "WH-A", "qty": 50, "cost": 10},
            {"sku": "SKU-102", "wh_code": "WH-A", "qty": 30, "cost": 25},
            {"sku": "SKU-103", "wh_code": "WH-B", "qty": 20, "cost": 15},
            {"sku": "SKU-104", "wh_code": "WH-C", "qty": 40, "cost": 5},
        ],
    }


# ── 1. Multiple legitimate child rows sharing foreign key ──

def test_multiple_child_rows_per_parent_retained(department_fixtures):
    """Multiple employees legitimately share dept_id='D1'.

    Without explicit deduplication, all 3 employees in D1 must be summed:
    100 + 120 + 110 = 330.
    """
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "departments",
            "right_table": "employees",
            "left_on": "departments.id",
            "right_on": "employees.dept_id",
            "group_column": "departments.id",
            "agg_column": "employees.salary",
            "agg_op": "sum",
        },
        department_fixtures,
        ctx,
        department_fixtures,
    )
    rows_by_id = {r["id"]: r["salary"] for r in result["rows"]}
    assert rows_by_id["D1"] == 330
    assert rows_by_id["D2"] == 90
    assert result["total"] == 420


def test_sum_column_no_auto_deduplication_on_foreign_key(department_fixtures):
    """sum_column on child table must NOT auto-deduplicate by foreign key dept_id."""
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "employees.salary"},
        department_fixtures,
        ctx,
        department_fixtures,
    )
    # Total must be 100 + 120 + 110 + 90 = 420
    assert result == {"total": 420}


# ── 2. Explicit deduplication by designated unique key ──

def test_explicit_deduplication_by_unique_key(department_with_duplicate_emp_fixtures):
    """When dedup_column='emp_id' is explicitly requested, only duplicate emp_id is dropped."""
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "departments",
            "right_table": "employees",
            "left_on": "departments.id",
            "right_on": "employees.dept_id",
            "dedup_column": "employees.emp_id",
            "group_column": "departments.id",
            "agg_column": "employees.salary",
            "agg_op": "sum",
        },
        department_with_duplicate_emp_fixtures,
        ctx,
        department_with_duplicate_emp_fixtures,
    )
    rows_by_id = {r["id"]: r["salary"] for r in result["rows"]}
    # D1 has E1 (100) + E2 (120 deduped) + E3 (110) = 330
    assert rows_by_id["D1"] == 330
    assert rows_by_id["D2"] == 90
    assert result["total"] == 420


def test_absence_of_deduplication_when_unrequested(department_with_duplicate_emp_fixtures):
    """Without dedup_column, all records including the repeated row are preserved."""
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "employees.salary"},
        department_with_duplicate_emp_fixtures,
        ctx,
        department_with_duplicate_emp_fixtures,
    )
    # 100 + 120 + 120 + 110 + 90 = 540
    assert result == {"total": 540}


# ── 3. Generic filtering, aggregation, and listing on synthetic inventory ──

def test_inventory_filter_and_aggregation(inventory_fixtures):
    """Filtering and aggregation on synthetic warehouse/inventory data."""
    ctx = FakeToolContext()

    # Filter active warehouses (boolean true)
    wh_result = _dispatch_flat_tool(
        "filter_records",
        {"table": "warehouses", "column": "active", "op": "eq", "value": "true"},
        inventory_fixtures,
        ctx,
        inventory_fixtures,
    )
    assert len(wh_result["rows"]) == 2
    active_codes = {r["warehouses.code"] for r in wh_result["rows"]}
    assert active_codes == {"WH-A", "WH-B"}

    # Filter inactive warehouses (boolean false)
    wh_inactive = _dispatch_flat_tool(
        "filter_records",
        {"table": "warehouses", "column": "active", "op": "eq", "value": "false"},
        inventory_fixtures,
        ctx,
        inventory_fixtures,
    )
    assert len(wh_inactive["rows"]) == 1
    assert wh_inactive["rows"][0]["warehouses.code"] == "WH-C"

    # List SKUs sorted
    skus = _dispatch_flat_tool(
        "list_column",
        {"table": "inventory", "column": "sku", "sort": "asc"},
        inventory_fixtures,
        ctx,
        inventory_fixtures,
    )
    assert skus == {"values": ["SKU-101", "SKU-102", "SKU-103", "SKU-104"]}

    # Sum quantity for WH-A
    wh_a_qty = _dispatch_flat_tool(
        "sum_column",
        {
            "table": "inventory",
            "column": "qty",
            "filter_column": "wh_code",
            "filter_op": "eq",
            "filter_value": "WH-A",
        },
        inventory_fixtures,
        ctx,
        inventory_fixtures,
    )
    assert wh_a_qty == {"total": 80}  # 50 + 30


# ── 4. Rejection of malformed arguments ──

def test_rejection_of_invalid_table(inventory_fixtures):
    ctx = FakeToolContext()
    with pytest.raises(ValueError, match="'table' must name one of the supplied fixtures"):
        _dispatch_flat_tool(
            "filter_records",
            {"table": "nonexistent_table", "column": "qty", "op": "gt", "value": "10"},
            inventory_fixtures,
            ctx,
            inventory_fixtures,
        )


def test_rejection_of_invalid_column(inventory_fixtures):
    ctx = FakeToolContext()
    with pytest.raises(ValueError, match="Unknown column"):
        _dispatch_flat_tool(
            "sum_column",
            {"table": "inventory", "column": "inventory.nonexistent_col"},
            inventory_fixtures,
            ctx,
            inventory_fixtures,
        )


# ── 5. Output schema parsing and type coercion ──

def test_parse_output_type_strictness():
    agent = ModelAgent("test-model", "tools")
    schema = {
        "count": "int",
        "ratio": "float",
        "tags": "list",
    }

    # Clean JSON
    parsed = agent.parse_output('{"count": 5, "ratio": 0.25, "tags": ["a", "b"]}', schema)
    assert parsed == {"count": 5, "ratio": 0.25, "tags": ["a", "b"]}

    # Coerced stringified list with single quotes
    parsed_coerced = agent.parse_output('{"count": 5, "ratio": 0.25, "tags": "[\'a\', \'b\']"}', schema)
    assert parsed_coerced == {"count": 5, "ratio": 0.25, "tags": ["a", "b"]}

    # Rejection of invalid list (e.g. number when list expected)
    with pytest.raises(ValueError, match="expected list"):
        agent.parse_output('{"count": 5, "ratio": 0.25, "tags": 123}', schema)

    # Rejection of invalid number (e.g. non-numeric string)
    with pytest.raises(ValueError, match="expected int"):
        agent.parse_output('{"count": "not_a_number", "ratio": 0.25, "tags": ["a"]}', schema)


# ── 6. Verification that generic joins do not inject invoice keys ──

def test_no_invoice_fields_in_generic_joins(department_fixtures):
    """Generic join of departments and employees must not contain invoice-specific keys."""
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "departments",
            "right_table": "employees",
            "left_on": "departments.id",
            "right_on": "employees.dept_id",
            "group_column": "departments.id",
            "agg_column": "employees.salary",
            "agg_op": "sum",
        },
        department_fixtures,
        ctx,
        department_fixtures,
    )
    for forbidden_key in ["paid_total", "billed_total", "outstanding_total", "unpaid_ids"]:
        assert forbidden_key not in result, f"Found unexpected invoice key: {forbidden_key}"
    for row in result.get("rows", []):
        for forbidden_key in ["billed_amount", "paid_amount", "balance"]:
            assert forbidden_key not in row, f"Found unexpected invoice key: {forbidden_key}"


# ── 7. Independent verification of intentionally incorrect draft ──

def test_verifier_independent_draft_correction(monkeypatch):
    """Verify that a corrupted draft is not blindly copied; verifier recomputes from fixtures."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    agent = ModelAgent("test-model", "verify", max_calls=4)
    task_def = {
        "id": "synthetic-dept-summary",
        "title": "Synthetic Department Summary",
        "category": "Operations",
        "operation": "summary",
        "description": "Compute total_salary across departments.",
        "inputs": {
            "departments": [{"id": "D1"}, {"id": "D2"}],
            "employees": [{"id": "E1", "salary": 200}, {"id": "E2", "salary": 300}],
        },
        "output_schema": {"total_salary": "int"},
        "expected": {"total_salary": 500},
    }
    from agent_arena import Task
    task = Task.from_dict(task_def)
    tools = ToolContext(task)

    # Intentionally bad draft with wrong salary
    bad_draft = '{"total_salary": 9999}'
    corrected = '{"total_salary": 500}'

    calls = 0
    def mock_post(url, json=None, headers=None, timeout=None):
        nonlocal calls
        calls += 1
        class MockResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                # Turn 1: solver produces bad draft
                if calls == 1:
                    return {"choices": [{"message": {"content": bad_draft}}]}
                # Turn 2: verifier uses tool to sum
                elif calls == 2:
                    return {"choices": [{"message": {
                        "content": "",
                        "tool_calls": [{"id": "c1", "type": "function", "function": {
                            "name": "sum_column",
                            "arguments": '{"table": "employees", "column": "employees.salary"}'
                        }}]
                    }}]}
                # Turn 3: verifier produces corrected final answer based on tool output
                else:
                    return {"choices": [{"message": {"content": corrected}}]}
        return MockResponse()

    import httpx
    monkeypatch.setattr(httpx.Client, "post", lambda self, *a, **kw: mock_post(*a, **kw))

    res = agent.run(task, tools)
    assert res.output == {"total_salary": 500}
    ev = evaluate(res.output, task_def["expected"])
    assert ev["passed"] is True


def test_verifier_does_not_select_non_deduplicated_candidate_result(monkeypatch):
    """Verify that when multiple candidate join results exist (one with dedup, one without),
    the verifier prompt explicitly enforces selecting the deduplicated result."""
    monkeypatch.setenv("OPENAI_API_KEY", "mock-key")
    agent = ModelAgent("test-model", "verify", max_calls=4)

    task_def = {
        "id": "invoice-reconciliation",
        "title": "Reconcile a messy invoice ledger",
        "category": "Data analysis",
        "operation": "invoices",
        "description": "Read invoices and payments. Ignore void invoices. Exclude duplicate payments with the same payment_id.",
        "inputs": {
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
        },
        "output_schema": {
            "billed_total": "int",
            "paid_total": "int",
            "outstanding_total": "int",
            "unpaid_invoice_ids": "list",
        },
        "expected": {
            "billed_total": 2600,
            "paid_total": 1500,
            "outstanding_total": 1100,
            "unpaid_invoice_ids": ["INV-102", "INV-104"],
        },
    }
    from agent_arena import Task
    task = Task.from_dict(task_def)
    tools = ToolContext(task)

    draft = json.dumps({
        "billed_total": 2600,
        "paid_total": 1500,
        "outstanding_total": 1100,
        "unpaid_invoice_ids": ["INV-102", "INV-104"],
    })
    verified_answer = json.dumps({
        "billed_total": 2600,
        "paid_total": 1500,
        "outstanding_total": 1100,
        "unpaid_invoice_ids": ["INV-102", "INV-104"],
    })

    prompts_seen = []
    calls = 0

    def mock_post(url, json=None, headers=None, timeout=None):
        nonlocal calls
        calls += 1
        messages = json.get("messages", [])
        prompts_seen.append(messages)

        class MockResponse:
            status_code = 200
            def raise_for_status(self): pass
            def json(self):
                # Turn 1: solver produces draft
                if calls == 1:
                    return {"choices": [{"message": {"content": draft}}]}
                # Turn 2: verifier issues multiple tool calls:
                # call 1: sum_column (2600)
                # call 2: join_and_aggregate with dedup (1500)
                # call 3: join_and_aggregate WITHOUT dedup (1800)
                elif calls == 2:
                    return {"choices": [{"message": {
                        "content": "",
                        "tool_calls": [
                            {"id": "c1", "type": "function", "function": {
                                "name": "sum_column",
                                "arguments": '{"table": "invoices", "column": "amount", "filter": "status != \\"void\\""}'
                            }},
                            {"id": "c2", "type": "function", "function": {
                                "name": "join_and_aggregate",
                                "arguments": '{"table": "invoices", "right_table": "payments", "join": "invoice_id", "dedup": "payment_id", "filter": "status != \\"void\\"", "columns": "amount", "group": "invoice_id"}'
                            }},
                            {"id": "c3", "type": "function", "function": {
                                "name": "join_and_aggregate",
                                "arguments": '{"table": "invoices", "right_table": "payments", "join": "invoice_id", "filter": "status != \\"void\\"", "columns": "amount", "group": "invoice_id"}'
                            }},
                        ]
                    }}]}
                # Turn 3: verifier produces final answer
                else:
                    return {"choices": [{"message": {"content": verified_answer}}]}
        return MockResponse()

    import httpx
    monkeypatch.setattr(httpx.Client, "post", lambda self, *a, **kw: mock_post(*a, **kw))

    res = agent.run(task, tools)
    assert res.output["paid_total"] == 1500
    assert res.output["outstanding_total"] == 1100
    assert res.output["unpaid_invoice_ids"] == ["INV-102", "INV-104"]

    # Check the final prompt sent to the verifier in Turn 3
    final_messages = prompts_seen[-1]
    user_messages = [m for m in final_messages if m.get("role") == "user"]
    final_user_msg = user_messages[-1]["content"]
    assert "When the task explicitly requires deduplication" in final_user_msg
    assert "Never substitute or select a similar result from a call that omitted the required deduplication" in final_user_msg
    assert "deduplicated join_and_aggregate result of 1500" in final_user_msg


