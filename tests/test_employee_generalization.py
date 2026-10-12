"""Deterministic regression tests for generalization on employee dataset.

Verifies:
1. Summing employee salaries without a deduplication request returns 420.
2. Repeated department_id values never cause employee records to be discarded.
3. Explicit deduplication still works when a task actually requests it.
4. Generic employee-data results never acquire invoice-specific keys.
5. Existing boolean filtering and multi-row join behavior remain correct.
"""

import pytest
from agent_arena import Task, ToolContext, evaluate
from arena_server.agents import _dispatch_flat_tool
from arena_server.data_tools import analyze_records


class FakeToolContext:
    def record(self, kind, name, metadata, fn):
        return fn()

    def note(self, text):
        pass


@pytest.fixture
def employee_fixtures():
    """Standard synthetic employee dataset."""
    return {
        "employees": [
            {"employee_id": "E1", "department_id": "D1", "salary": 100},
            {"employee_id": "E2", "department_id": "D1", "salary": 120},
            {"employee_id": "E3", "department_id": "D1", "salary": 110},
            {"employee_id": "E4", "department_id": "D2", "salary": 90},
        ]
    }


@pytest.fixture
def employee_dept_fixtures():
    """Employees and departments for multi-row join verification."""
    return {
        "departments": [
            {"department_id": "D1", "dept_name": "Engineering"},
            {"department_id": "D2", "dept_name": "Sales"},
        ],
        "employees": [
            {"employee_id": "E1", "department_id": "D1", "salary": 100, "is_active": True},
            {"employee_id": "E2", "department_id": "D1", "salary": 120, "is_active": False},
            {"employee_id": "E3", "department_id": "D1", "salary": 110, "is_active": True},
            {"employee_id": "E4", "department_id": "D2", "salary": 90, "is_active": True},
        ],
    }


def test_sum_employee_salaries_without_dedup_returns_420(employee_fixtures):
    """Summing employee salaries without deduplication returns 420."""
    ctx = FakeToolContext()

    # Via _dispatch_flat_tool
    result = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary"},
        employee_fixtures,
        ctx,
        employee_fixtures,
    )
    assert result == {"total": 420}

    # Via table.column qualification
    result_qualified = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "employees.salary"},
        employee_fixtures,
        ctx,
        employee_fixtures,
    )
    assert result_qualified == {"total": 420}

    # Via col alias (emitted by smaller LLMs)
    result_col = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "col": "salary"},
        employee_fixtures,
        ctx,
        employee_fixtures,
    )
    assert result_col == {"total": 420}

    # Direct analyze_records spec
    spec = {
        "table": "employees",
        "aggregates": [{"op": "sum", "column": "employees.salary", "as": "total"}],
    }
    raw = analyze_records(spec, employee_fixtures)
    assert raw["rows"] == [{"total": 420}]


def test_repeated_department_id_preserves_all_employee_records(employee_fixtures, employee_dept_fixtures):
    """Repeated department_id values (D1 shared by E1, E2, E3) never cause records to be dropped."""
    ctx = FakeToolContext()

    # Summing employees has 3 employees sharing D1 (100, 120, 110) + 1 in D2 (90) = 420
    result = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary"},
        employee_fixtures,
        ctx,
        employee_fixtures,
    )
    assert result["total"] == 420

    # Join departments and employees grouped by department_id
    join_result = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "departments",
            "right_table": "employees",
            "left_on": "departments.department_id",
            "right_on": "employees.department_id",
            "group_by": "departments.department_id",
            "agg_column": "employees.salary",
            "agg_op": "sum",
        },
        employee_dept_fixtures,
        ctx,
        employee_dept_fixtures,
    )

    # Engineering (D1) should sum all 3 employees: 100 + 120 + 110 = 330
    # Sales (D2) should sum E4: 90
    rows = {r["department_id"]: r["salary"] for r in join_result["rows"]}
    assert rows == {"D1": 330, "D2": 90}
    assert join_result["total"] == 420


def test_explicit_deduplication_works_when_requested(employee_fixtures):
    """Explicit deduplication must be honored when requested."""
    ctx = FakeToolContext()

    # If deduplicating by department_id, D1 is counted once (100) and D2 once (90) -> 190
    dedup_dept = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary", "dedup": "department_id"},
        employee_fixtures,
        ctx,
        employee_fixtures,
    )
    assert dedup_dept == {"total": 190}

    # If deduplicating by employee_id, each employee is distinct -> 420
    dedup_emp = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary", "dedup": "employee_id"},
        employee_fixtures,
        ctx,
        employee_fixtures,
    )
    assert dedup_emp == {"total": 420}

    # Fixture with an actual duplicate employee record
    fixtures_with_dup = {
        "employees": [
            {"employee_id": "E1", "department_id": "D1", "salary": 100},
            {"employee_id": "E2", "department_id": "D1", "salary": 120},
            {"employee_id": "E2", "department_id": "D1", "salary": 120},  # duplicate
            {"employee_id": "E3", "department_id": "D1", "salary": 110},
            {"employee_id": "E4", "department_id": "D2", "salary": 90},
        ]
    }
    # Without dedup: 100 + 120 + 120 + 110 + 90 = 540
    no_dedup = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary"},
        fixtures_with_dup,
        ctx,
        fixtures_with_dup,
    )
    assert no_dedup == {"total": 540}

    # With explicit dedup on employee_id: duplicate E2 is removed -> 420
    with_dedup = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary", "dedup": "employee_id"},
        fixtures_with_dup,
        ctx,
        fixtures_with_dup,
    )
    assert with_dedup == {"total": 420}


def test_generic_employee_result_has_no_invoice_keys(employee_dept_fixtures):
    """Generic employee queries must never inject invoice-specific keys."""
    ctx = FakeToolContext()

    sum_res = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary"},
        employee_dept_fixtures,
        ctx,
        employee_dept_fixtures,
    )
    for forbidden in ["billed_total", "paid_total", "outstanding_total", "unpaid_ids", "unpaid_invoice_ids"]:
        assert forbidden not in sum_res

    join_res = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "departments",
            "right_table": "employees",
            "left_on": "departments.department_id",
            "right_on": "employees.department_id",
            "group_by": "departments.department_id",
            "agg_column": "employees.salary",
            "agg_op": "sum",
        },
        employee_dept_fixtures,
        ctx,
        employee_dept_fixtures,
    )
    for forbidden in ["billed_total", "paid_total", "outstanding_total", "unpaid_ids", "unpaid_invoice_ids"]:
        assert forbidden not in join_res

    for r in join_res.get("rows", []):
        for forbidden in ["billed_amount", "paid_amount", "balance"]:
            assert forbidden not in r


def test_boolean_filtering_and_multi_row_join_remain_correct(employee_dept_fixtures):
    """Boolean filters and multi-row joins function properly on employee dataset."""
    ctx = FakeToolContext()

    # Active employees: E1(100) + E3(110) + E4(90) = 300
    active_res = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary", "filter_column": "is_active", "filter_op": "eq", "filter_value": "true"},
        employee_dept_fixtures,
        ctx,
        employee_dept_fixtures,
    )
    assert active_res == {"total": 300}

    # Inactive employees: E2(120) = 120
    inactive_res = _dispatch_flat_tool(
        "sum_column",
        {"table": "employees", "column": "salary", "filter_column": "is_active", "filter_op": "eq", "filter_value": "false"},
        employee_dept_fixtures,
        ctx,
        employee_dept_fixtures,
    )
    assert inactive_res == {"total": 120}

    # Filter with join: active employees in D1 = E1(100) + E3(110) = 210
    active_join = _dispatch_flat_tool(
        "join_and_aggregate",
        {
            "table": "departments",
            "right_table": "employees",
            "left_on": "departments.department_id",
            "right_on": "employees.department_id",
            "filter_column": "employees.is_active",
            "filter_op": "eq",
            "filter_value": "true",
            "group_by": "departments.department_id",
            "agg_column": "employees.salary",
            "agg_op": "sum",
        },
        employee_dept_fixtures,
        ctx,
        employee_dept_fixtures,
    )
    rows = {r["department_id"]: r["salary"] for r in active_join["rows"]}
    assert rows["D1"] == 210
    assert rows["D2"] == 90
    assert active_join["total"] == 300


def test_synthetic_employee_task_evaluation():
    """Task definition and evaluation logic against expected output schema."""
    task_def = {
        "id": "employee-salary-sum",
        "title": "Employee Salary Sum",
        "category": "finance",
        "operation": "employees",
        "description": (
            "Read the employees data and calculate the total salary across all employees. "
            "Every employee is a distinct record. Do not deduplicate or exclude records. "
            "Return exactly one JSON object with total_salary as an integer."
        ),
        "inputs": {
            "employees": [
                {"employee_id": "E1", "department_id": "D1", "salary": 100},
                {"employee_id": "E2", "department_id": "D1", "salary": 120},
                {"employee_id": "E3", "department_id": "D1", "salary": 110},
                {"employee_id": "E4", "department_id": "D2", "salary": 90},
            ]
        },
        "output_schema": {"total_salary": "int"},
        "expected": {"total_salary": 420},
    }

    task = Task.from_dict(task_def)
    assert task.id == "employee-salary-sum"
    assert task.output_schema == {"total_salary": "int"}

    ev = evaluate({"total_salary": 420}, task_def["expected"])
    assert ev["passed"] is True
    assert ev["score"] == 1.0

    ev_wrong = evaluate({"total_salary": 330}, task_def["expected"])
    assert ev_wrong["passed"] is False
    assert ev_wrong["score"] == 0.0
