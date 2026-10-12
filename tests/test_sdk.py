import pytest
from agent_arena import Task, ToolContext, evaluate
from arena_server.agents import ReferenceAgent
from arena_server.engine import TASKS


@pytest.mark.parametrize("definition", TASKS, ids=lambda t: t["id"])
def test_reference_solves_every_task(definition):
    task = Task.from_dict(definition)
    tools = ToolContext(task)
    result = ReferenceAgent("methodical").run(task, tools)
    assert evaluate(result.output, definition["expected"])["passed"]
    assert len(tools.events) >= 4
    assert all(e["duration_ms"] >= 0 for e in tools.trace())
    assert [e["index"] for e in tools.trace()] == list(range(len(tools.events)))
    offsets = [e["offset_ms"] for e in tools.trace()]
    assert offsets == sorted(offsets)


@pytest.mark.parametrize(
    "actual,expected,passed",
    [
        ({"x": 1}, {"x": 1}, True),
        ({"x": 1.004}, {"x": 1}, True),
        ({"x": 1.1}, {"x": 1}, False),
        ({"x": True}, {"x": 1}, False),
        ({"x": 1}, {"x": True}, False),
        ({"x": [1, 2]}, {"x": [2, 1]}, False),
        ({"x": [1, 2]}, {"x": [1]}, False),
        ({"x": {"a": 1, "b": 2}}, {"x": {"a": 1}}, True),
        ({"x": 10**500}, {"x": 2}, False),
        ({}, {"x": 2}, False),
        ({"x": "1"}, {"x": 1}, False),
        ({"x": float("nan")}, {"x": 1}, False),
    ],
)
def test_evaluator_values(actual, expected, passed):
    assert evaluate(actual, expected)["passed"] is passed


def test_partial_and_empty():
    assert evaluate({"a": 1}, {"a": 1, "b": 2})["score"] == 0.5
    assert evaluate({}, {}) == {"score": 0, "passed": False, "checks": []}


@pytest.mark.parametrize(
    "expression",
    ["__import__('os').system('id')", "2 ** 100", "[1,2]", "1e10000", "open('file')", "(lambda:1)()", "1/0", "1" * 501],
)
def test_calculator_rejects_unsafe_expressions(expression):
    tools = ToolContext(Task.from_dict(TASKS[0]))
    with pytest.raises((ValueError, ZeroDivisionError)):
        tools.calculate(expression)
    assert tools.events[-1].status == "error"


def test_read_fixtures_returns_copy():
    task = Task.from_dict(TASKS[0])
    tools = ToolContext(task)
    invoices = tools.read_file("invoices")
    invoices[0]["amount"] = 0
    assert task.inputs["invoices"][0]["amount"] == 1200
    assert tools.calculate("(10 + 2) * 3 / 2") == 18
    with pytest.raises(ValueError):
        tools.read_file("/etc/passwd")
