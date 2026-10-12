"""CLI for running trusted local Python agents and uploading self-reported traces."""

import argparse
import importlib.util
import inspect
import json
import os
import time
from pathlib import Path

import httpx

from .core import Agent, AgentResult, Task, ToolContext


def main():
    parser = argparse.ArgumentParser(description="AgentArena local agent workbench")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tasks", help="List benchmark tasks")
    run = sub.add_parser("run", help="Run a TRUSTED local Python agent; this is not sandboxed")
    run.add_argument("file")
    run.add_argument("--task", required=True)
    run.add_argument("--output", default="arena-run.json")
    run.add_argument("--submit", action="store_true", help="Upload as a self-reported SDK run")
    replay = sub.add_parser("replay")
    replay.add_argument("run_id")
    args = parser.parse_args()
    headers = {"Authorization": f"Bearer {os.environ['ARENA_API_TOKEN']}"} if os.getenv("ARENA_API_TOKEN") else {}
    with httpx.Client(base_url=args.url, headers=headers, timeout=60) as client:
        if args.command == "tasks":
            resp = client.get("/api/tasks")
            resp.raise_for_status()
            for task in resp.json():
                print(f"{task['id']:<25} {task['title']}")
        elif args.command == "replay":
            resp = client.get(f"/api/runs/{args.run_id}")
            resp.raise_for_status()
            print(json.dumps(resp.json(), indent=2))
        else:
            resp = client.get(f"/api/tasks/{args.task}")
            resp.raise_for_status()
            task = Task.from_dict(resp.json())
            file = Path(args.file).resolve()
            spec = importlib.util.spec_from_file_location("user_agent", file)
            if not spec or not spec.loader:
                parser.error("Could not load Python file")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            classes = [
                c
                for _, c in inspect.getmembers(module, inspect.isclass)
                if issubclass(c, Agent) and c is not Agent and c.__module__ == "user_agent"
            ]
            if len(classes) != 1:
                parser.error("Your file must define exactly one Agent subclass")
            tools = ToolContext(task)
            start = time.perf_counter()
            result = classes[0]().run(task, tools)
            if not isinstance(result, AgentResult):
                parser.error("Agent.run must return AgentResult")
            payload = {
                "agent_name": classes[0].__name__,
                "task_id": task.id,
                "output": result.output,
                "events": tools.trace(),
                "duration_ms": (time.perf_counter() - start) * 1000,
                "summary": result.summary,
            }
            Path(args.output).write_text(json.dumps(payload, indent=2), encoding="utf-8")
            print(f"Saved {args.output}")
            if args.submit:
                resp = client.post("/api/import", json=payload)
                resp.raise_for_status()
                print(f"Imported self-reported run: {resp.json()['id']} (excluded from verified rankings)")


if __name__ == "__main__":
    main()
