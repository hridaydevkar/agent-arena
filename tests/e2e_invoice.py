"""One-shot end-to-end test against the real local model.

Run with:  python tests/e2e_invoice.py

This script directly invokes the ModelAgent with the invoice-reconciliation
task against the local Ollama server. It prints the full trace and result,
and reports whether evaluation checks pass.
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
from arena_server.engine import TASK_MAP

TASK_ID = "invoice-reconciliation"
MODEL = os.environ["OPENAI_MODEL"]
ARCHITECTURE = os.environ.get("ARENA_ARCH", "tools")
MAX_CALLS = 6
MAX_OUTPUT_TOKENS = 1800

EXPECTED = {
    "billed_total": 2600,
    "paid_total": 1500,
    "outstanding_total": 1100,
    "unpaid_invoice_ids": ["INV-102", "INV-104"],
}


def main():
    task_def = TASK_MAP[TASK_ID]
    task = Task.from_dict(task_def)
    tools = ToolContext(task)

    print(f"Running: {TASK_ID} | model={MODEL} | arch={ARCHITECTURE}")
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

        # Run evaluation
        ev = evaluate(result.output, task_def["expected"])
        print(f"   Score: {ev['score']}")
        print(f"   Passed: {ev['passed']}")
        for check in ev.get("checks", []):
            status = "✅" if check["passed"] else "❌"
            print(f"   {status} {check['field']}: expected={check['expected']} actual={check['actual']}")
        print()

        # Print trace events with details
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

        # Print partial trace
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
