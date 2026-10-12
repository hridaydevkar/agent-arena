from __future__ import annotations

import ast
import json
import math
import operator
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Task:
    id: str
    title: str
    description: str
    category: str
    operation: str
    inputs: dict[str, Any]
    output_schema: dict[str, str]
    version: str = "1.0.0"

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentResult:
    output: dict[str, Any]
    summary: str = ""


@dataclass
class TraceEvent:
    index: int
    kind: str
    name: str
    input: Any
    output: Any
    duration_ms: float
    offset_ms: float
    status: str = "ok"
    usage: dict = field(default_factory=dict)


class ToolContext:
    """Instrumented, read-only fixture tools. No shell, filesystem, or arbitrary network access."""

    def __init__(self, task: Task):
        self.task = task
        self.events: list[TraceEvent] = []
        self.started = time.perf_counter()
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost_usd: float | None = 0.0
        self.cost_source: str = "no-model-calls"
        self.model_calls: int = 0
        self.resolved_models: list[str] = []

    def record(self, kind: str, name: str, payload: Any, fn, usage: dict | None = None):
        start = time.perf_counter()
        status = "ok"
        result: Any = None
        try:
            result = fn()
        except Exception as exc:
            status = "error"
            result = {"error": type(exc).__name__, "message": str(exc)[:400]}
            raise
        finally:
            self.events.append(
                TraceEvent(
                    len(self.events),
                    kind,
                    name,
                    payload,
                    result,
                    round((time.perf_counter() - start) * 1000, 3),
                    round((start - self.started) * 1000, 3),
                    status,
                    usage or {},
                )
            )
        return result

    def read_file(self, name: str) -> Any:
        def read():
            if name not in self.task.inputs:
                raise ValueError(f"Unknown fixture: {name}")
            # A copy prevents agents mutating the shared fixture.
            return json.loads(json.dumps(self.task.inputs[name]))

        return self.record("tool", "fixtures.read", {"name": name}, read)

    def calculate(self, expression: str) -> float:
        """Evaluate a small arithmetic AST. Never calls eval()."""

        def calc() -> float:
            if len(expression) > 500:
                raise ValueError("Expression is too long")
            ops: dict[type[ast.operator], Any] = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
            }

            def visit(node: ast.AST) -> float:
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, (int, float))
                    and not isinstance(node.value, bool)
                ):
                    val = float(node.value)
                    if not math.isfinite(val) or abs(val) > 1e15:
                        raise ValueError("Number out of bounds")
                    return val
                if isinstance(node, ast.BinOp) and type(node.op) in ops:
                    op_func = ops[type(node.op)]
                    value = float(op_func(visit(node.left), visit(node.right)))
                    if not math.isfinite(value) or abs(value) > 1e18:
                        raise ValueError("Result out of bounds")
                    return value
                if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
                    return -visit(node.operand)
                raise ValueError("Only numbers and +, -, *, / are allowed")

            return visit(ast.parse(expression, mode="eval").body)

        return float(self.record("tool", "calculator.evaluate", {"expression": expression}, calc))

    def note(self, summary: str):
        """Record a short observable action summary, not private chain-of-thought."""
        return self.record("note", "agent.summary", {}, lambda: summary)

    def trace(self) -> list[dict]:
        return [{**asdict(e), "index": i} for i, e in enumerate(sorted(self.events, key=lambda e: e.offset_ms))]


class Agent(ABC):
    @abstractmethod
    def run(self, task: Task, tools: ToolContext) -> AgentResult:
        """Return JSON-serializable structured output. Tools are automatically traced."""
        raise NotImplementedError


def _matches(actual, expected):
    if isinstance(expected, bool):
        return type(actual) is bool and actual == expected
    if isinstance(expected, (int, float)):
        try:
            return type(actual) in (int, float) and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=0.01)
        except (OverflowError, TypeError):
            return False
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(k in actual and _matches(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return (
            isinstance(actual, list)
            and len(actual) == len(expected)
            and all(_matches(a, b) for a, b in zip(actual, expected))
        )
    return actual == expected


def evaluate(output: dict, expected: dict) -> dict:
    """Equal weight per expected top-level field. Lists are ordered; extra fields are ignored."""
    checks = [
        {"field": key, "passed": _matches(output.get(key), value), "expected": value, "actual": output.get(key)}
        for key, value in expected.items()
    ]
    score = sum(c["passed"] for c in checks) / len(checks) if checks else 0.0
    return {"score": round(score, 4), "passed": bool(checks) and all(c["passed"] for c in checks), "checks": checks}
