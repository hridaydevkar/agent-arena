"""Deterministic regression tests for relational generalization on synthetic orders dataset.

Verifies:
1. Generic join and aggregation tools can join orders with order_items using correct keys.
2. Multiple child rows with the same order_id are retained.
3. Filtering on parent order's status excludes cancelled orders.
4. The resulting total line_total is 205 without deduplicating by order_id.
5. Explicit deduplication remains available when the task actually requests it.
6. Generic aggregation outputs do not contain unrelated invoice-specific fields.
7. Unknown tables and invalid columns remain safely rejected.
8. Synthetic orders task evaluation logic passes with score 1.0.
"""

import pytest
from agent_arena import Task, ToolContext, evaluate
from arena_server.agents import _dispatch_flat_tool, _normalize_tool_args
from arena_server.data_tools import analyze_records


class FakeToolContext:
    def record(self, kind, name, metadata, fn):
        return fn()

    def note(self, text):
        pass


@pytest.fixture
def orders_fixtures():
    """Standard synthetic orders and order_items dataset."""
    return {
        "orders": [
            {"id": "O-101", "status": "completed"},
            {"id": "O-102", "status": "completed"},
            {"id": "O-103", "status": "cancelled"},
            {"id": "O-104", "status": "completed"},
        ],
        "order_items": [
            {"item_id": "I-1", "order_id": "O-101", "line_total": 60},
            {"item_id": "I-2", "order_id": "O-101", "line_total": 15},
            {"item_id": "I-3", "order_id": "O-102", "line_total": 60},
            {"item_id": "I-4", "order_id": "O-102", "line_total": 20},
            {"item_id": "I-5", "order_id": "O-103", "line_total": 500},
            {"item_id": "I-6", "order_id": "O-104", "line_total": 30},
            {"item_id": "I-7", "order_id": "O-104", "line_total": 20},
        ],
    }


def test_join_retains_multiple_child_rows_without_dedup(orders_fixtures):
    """Multiple child rows with the same order_id are retained upon joining."""
    spec = {
        "table": "orders",
        "join": {
            "table": "order_items",
            "left_on": "orders.id",
            "right_on": "order_items.order_id",
            "how": "inner",
        },
    }
    result = analyze_records(spec, orders_fixtures)
    rows = result["rows"]

    # All 7 order items across all 4 orders must be present
    assert len(rows) == 7
    o101_items = [r for r in rows if r["orders.id"] == "O-101"]
    assert len(o101_items) == 2
    assert {r["order_items.item_id"] for r in o101_items} == {"I-1", "I-2"}
    assert {r["order_items.line_total"] for r in o101_items} == {60, 15}

    o102_items = [r for r in rows if r["orders.id"] == "O-102"]
    assert len(o102_items) == 2
    assert {r["order_items.item_id"] for r in o102_items} == {"I-3", "I-4"}

    o104_items = [r for r in rows if r["orders.id"] == "O-104"]
    assert len(o104_items) == 2
    assert {r["order_items.item_id"] for r in o104_items} == {"I-6", "I-7"}


def test_parent_status_filter_excludes_cancelled_orders(orders_fixtures):
    """Filtering on parent order's status excludes cancelled orders and retains all active items."""
    spec = {
        "table": "orders",
        "join": {
            "table": "order_items",
            "left_on": "orders.id",
            "right_on": "order_items.order_id",
            "how": "left",
        },
        "filters": [{"column": "orders.status", "op": "eq", "value": "completed"}],
    }
    result = analyze_records(spec, orders_fixtures)
    rows = result["rows"]

    # Exactly 6 items across the 3 completed orders (O-101, O-102, O-104)
    assert len(rows) == 6
    order_ids = {r["orders.id"] for r in rows}
    assert order_ids == {"O-101", "O-102", "O-104"}
    assert "O-103" not in order_ids

    # The cancelled order item with line_total 500 must NOT be present
    line_totals = [r["order_items.line_total"] for r in rows]
    assert 500 not in line_totals
    assert sum(line_totals) == 205


def test_resulting_total_is_205_without_deduplicating_order_id(orders_fixtures):
    """Direct analysis and flat tool dispatch both calculate 205 for completed orders."""
    ctx = FakeToolContext()

    # 1. Direct analyze_records with aggregate
    spec = {
        "table": "orders",
        "join": {
            "table": "order_items",
            "left_on": "orders.id",
            "right_on": "order_items.order_id",
            "how": "left",
        },
        "filters": [{"column": "orders.status", "op": "eq", "value": "completed"}],
        "aggregates": [{"op": "sum", "column": "order_items.line_total", "as": "line_total"}],
    }
    direct_res = analyze_records(spec, orders_fixtures)
    assert direct_res["rows"][0]["line_total"] == 205

    # 2. Via _dispatch_flat_tool with natural arguments
    dispatched = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "orders",
            "right_table": "order_items",
            "join": "order_id",
            "filter": "status == 'completed'",
            "columns": "line_total",
        },
        orders_fixtures,
        ctx,
        {"orders": [], "order_items": []},
    )
    assert dispatched.get("total") == 205

    # 3. Via _dispatch_flat_tool with inequality filter
    dispatched_ne = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "orders",
            "right_table": "order_items",
            "join": "order_id",
            "filter": "status != 'cancelled'",
            "columns": ["line_total"],
        },
        orders_fixtures,
        ctx,
        {"orders": [], "order_items": []},
    )
    assert dispatched_ne.get("total") == 205

    # 4. Via _dispatch_flat_tool with compound join expression
    dispatched_compound = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "orders",
            "right_table": "order_items",
            "join": "orders.id = order_items.order_id",
            "filter": "orders.status == 'completed'",
            "col": "line_total",
        },
        orders_fixtures,
        ctx,
        {"orders": [], "order_items": []},
    )
    assert dispatched_compound.get("total") == 205


def test_explicit_deduplication_works_when_requested(orders_fixtures):
    """Explicit deduplication on order_items by order_id retains only 1 item per order."""
    ctx = FakeToolContext()

    # Without deduplication -> 205 (60+15 + 60+20 + 30+20)
    # With dedup="order_id" on order_items -> 60 + 60 + 30 = 150
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "orders",
            "right_table": "order_items",
            "join": "order_id",
            "filter": "status == 'completed'",
            "dedup": "order_id",
            "columns": "line_total",
        },
        orders_fixtures,
        ctx,
        {"orders": [], "order_items": []},
    )
    assert result.get("total") == 150


def test_generic_aggregation_outputs_have_no_invoice_specific_fields(orders_fixtures):
    """Generic join_and_aggregate results never acquire invoice-specific keys."""
    ctx = FakeToolContext()
    result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "orders",
            "right_table": "order_items",
            "join": "order_id",
            "filter": "status == 'completed'",
            "columns": "line_total",
        },
        orders_fixtures,
        ctx,
        {"orders": [], "order_items": []},
    )

    forbidden_keys = {
        "billed_total",
        "paid_total",
        "outstanding_total",
        "unpaid_ids",
        "unpaid_invoice_ids",
        "balance",
        "invoices_amount",
        "invoices_amount_total",
    }
    assert forbidden_keys.isdisjoint(result.keys()), f"Found invoice keys in result: {result.keys()}"
    for row in result.get("rows", []):
        assert forbidden_keys.isdisjoint(row.keys()), f"Found invoice keys in row: {row.keys()}"


def test_unknown_tables_and_invalid_columns_safely_rejected(orders_fixtures):
    """Unknown tables and invalid columns are properly rejected with ValueError."""
    ctx = FakeToolContext()

    # Unknown primary table
    with pytest.raises(ValueError, match="must name one of the supplied fixtures"):
        analyze_records({"table": "unknown_table"}, orders_fixtures)

    # Unknown join table
    with pytest.raises(ValueError, match="Join table must name a supplied fixture table"):
        analyze_records(
            {
                "table": "orders",
                "join": {
                    "table": "ghost_table",
                    "left_on": "orders.id",
                    "right_on": "ghost_table.id",
                },
            },
            orders_fixtures,
        )

    # Invalid column in aggregate
    with pytest.raises(ValueError, match="Unknown column"):
        analyze_records(
            {
                "table": "orders",
                "aggregates": [{"op": "sum", "column": "orders.nonexistent_column", "as": "val"}],
            },
            orders_fixtures,
        )


def test_orders_task_evaluation_logic():
    """Synthetic orders task evaluates correctly with evaluate()."""
    task_def = {
        "id": "orders-completed-revenue",
        "title": "Orders Completed Revenue",
        "description": "Calculate total line_total for completed orders only.",
        "category": "sales",
        "operation": "orders",
        "inputs": {"orders": [], "order_items": []},
        "output_schema": {"total_completed_revenue": "int"},
        "expected": {"total_completed_revenue": 205},
    }
    task = Task.from_dict(task_def)

    ev_pass = evaluate({"total_completed_revenue": 205}, task_def["expected"])
    assert ev_pass["passed"] is True
    assert ev_pass["score"] == 1.0

    ev_fail = evaluate({"total_completed_revenue": 705}, task_def["expected"])
    assert ev_fail["passed"] is False
    assert ev_fail["score"] < 1.0
