"""One-shot model-driven generalization test on the synthetic orders-and-items dataset.

Run with:  python tests/e2e_orders.py

This script directly invokes the production ModelAgent with the synthetic relational task
against the local Ollama server (llama3.2:3b) using the Tools architecture.
"""
import json
import os
import sys
import time

# Ensure the project packages are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sdk"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Set env for local Ollama
os.environ.setdefault("OPENAI_API_KEY", "ollama")
os.environ.setdefault("OPENAI_BASE_URL", "http://localhost:11434/v1")
os.environ.setdefault("OPENAI_MODEL", "llama3.2:3b")

from agent_arena import Task, ToolContext, evaluate
from arena_server.agents import ModelAgent

TASK_DEF = {
    "id": "orders-completed-revenue",
    "title": "Orders Completed Revenue",
    "description": (
        "Join orders with order_items using orders.id and order_items.order_id. "
        "Calculate the total line_total for completed orders only. Exclude cancelled orders. "
        "Each order item is a distinct valid record, even when multiple items share the same order_id. "
        "Do not deduplicate order_items by order_id. Return exactly one JSON object with total_completed_revenue as an integer."
    ),
    "category": "sales",
    "operation": "orders",
    "inputs": {
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
    },
    "output_schema": {
        "total_completed_revenue": "int",
    },
    "expected": {
        "total_completed_revenue": 205,
    },
}

MODEL = os.environ["OPENAI_MODEL"]
ARCHITECTURE = os.environ.get("ARENA_ARCH", "tools")
MAX_CALLS = 6
MAX_OUTPUT_TOKENS = 1800


def main():
    task = Task.from_dict(TASK_DEF)
    tools = ToolContext(task)

    print(f"Running relational generalization test: {task.id} | model={MODEL} | arch={ARCHITECTURE}")
    print(f"  max_calls={MAX_CALLS}  max_output_tokens={MAX_OUTPUT_TOKENS}")
    print()

    start = time.time()
    try:
        agent = ModelAgent(MODEL, ARCHITECTURE, MAX_CALLS, MAX_OUTPUT_TOKENS)
        result = agent.run(task, tools)
        elapsed = time.time() - start

        print(f"✅ Completed in {elapsed:.1f}s")
        print(f"   Model calls: {tools.model_calls}")
        print(f"   Output: {json.dumps(result.output, indent=2)}")
        print()

        ev = evaluate(result.output, TASK_DEF["expected"])
        print(f"   Score: {ev['score']}")
        print(f"   Passed: {ev['passed']}")
        for check in ev.get("checks", []):
            status = "✅" if check["passed"] else "❌"
            print(f"   {status} {check['field']}: expected={check['expected']} actual={check['actual']}")
        print()

        print("── Trace Events ──")
        for event in tools.events:
            print(f"  [{event.kind:5s}] {event.name:30s}  status={event.status}  dur={event.duration_ms:.0f}ms")
            if event.input:
                print(f"         input: {json.dumps(event.input, indent=None)}")
            if event.output is not None:
                result_str = json.dumps(event.output, indent=None) if not isinstance(event.output, str) else event.output
                print(f"         output: {result_str}")

        if not ev["passed"]:
            print("\n⚠️  Not all checks passed. See trace above.")
            sys.exit(1)
        else:
            print("\n🎉 All checks passed!")

    except Exception as exc:
        elapsed = time.time() - start
        print(f"❌ Failed after {elapsed:.1f}s: {type(exc).__name__}: {exc}")
        print()

        print("── Trace Events (partial) ──")
        for event in tools.events:
            print(f"  [{event.kind:5s}] {event.name:30s}  status={event.status}  dur={event.duration_ms:.0f}ms")
            if event.input:
                print(f"         input: {json.dumps(event.input, indent=None)}")
            if event.output is not None:
                result_str = json.dumps(event.output, indent=None) if not isinstance(event.output, str) else event.output
                print(f"         output: {result_str}")

        sys.exit(2)


if __name__ == "__main__":
    main()
