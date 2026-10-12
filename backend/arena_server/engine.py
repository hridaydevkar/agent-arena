import hashlib
import json
import os
import statistics
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from importlib.resources import files

from agent_arena import Task, ToolContext, evaluate

from .agents import ModelAgent, ReferenceAgent
from .provider import provider_name

TASKS = json.loads(files("arena_server").joinpath("task_library.json").read_text())
TASK_MAP = {t["id"]: t for t in TASKS}
SUITE_HASH = hashlib.sha256(json.dumps(TASKS, sort_keys=True).encode()).hexdigest()[:12]


def now():
    return datetime.now(UTC).isoformat()


def uid(prefix):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def public_task(task):
    return {k: v for k, v in task.items() if k != "expected"}


def run_summary(run):
    return {k: v for k, v in run.items() if k not in ("events", "output", "evaluation")}


class Engine:
    def __init__(self, store):
        self.store = store
        self.pool = ThreadPoolExecutor(max_workers=max(1, min(4, int(os.getenv("ARENA_WORKERS", "2")))))
        self.lock = threading.RLock()
        # Recover visibly, rather than leaving runs stuck after a process restart.
        for job in store.all("jobs"):
            if job["status"] in ("queued", "running"):
                job.update(status="interrupted", error="Server restarted before this job finished.", finished_at=now())
                store.put("jobs", job)

    def seed(self):
        if self.store.initialized():
            return
        definitions = [
            (
                "atlas",
                "Atlas",
                "methodical",
                "A careful reference policy. Filters edge cases and validates every output.",
                "#586b43",
            ),
            (
                "meridian",
                "Meridian",
                "balanced",
                "An efficient reference policy with limited provenance and inventory handling.",
                "#6a74aa",
            ),
            (
                "relay",
                "Relay",
                "greedy",
                "A naive baseline that aggregates before checking task constraints.",
                "#c58245",
            ),
            (
                "scout",
                "Scout",
                "minimal",
                "A minimal baseline with intentionally incomplete structured output.",
                "#8b6c97",
            ),
        ]
        for slug, name, strategy, description, color in definitions:
            agent = {
                "id": slug,
                "name": name,
                "strategy": strategy,
                "description": description,
                "color": color,
                "model": "Deterministic",
                "framework": "Python SDK",
                "version": "1.0.0",
                "created_at": now(),
                "reference": True,
            }
            self.store.put("agents", agent)
            for task in TASKS:
                self.execute(agent, task, seeded=True)
        self.store.mark_initialized()

    def execute(self, agent, definition, job_id=None, seeded=False):
        task = Task.from_dict(definition)
        tools = ToolContext(task)
        run = {
            "id": uid("run"),
            "agent_id": agent["id"],
            "agent_name": agent["name"],
            "agent_version": agent["version"],
            "task_id": task.id,
            "task_title": task.title,
            "category": task.category,
            "task_version": task.version,
            "suite_hash": SUITE_HASH,
            "created_at": now(),
            "job_id": job_id,
            "seeded": seeded,
            "provenance": "reference" if agent["strategy"] != "model" else "managed-model",
            "model": agent["model"],
            "strategy": agent["strategy"],
            "runner_version": "0.2.0",
            "architecture": agent.get("architecture", "tools" if agent["strategy"] == "model" else "reference"),
            "max_calls": agent.get("max_calls", 8),
            "max_output_tokens": agent.get("max_output_tokens", 1800),
            "provider": provider_name() if agent["strategy"] == "model" else "local-python",
            "pricing_per_million": {"input": os.getenv("ARENA_INPUT_PRICE"), "output": os.getenv("ARENA_OUTPUT_PRICE")}
            if agent["strategy"] == "model" and agent["model"] == os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            else None,
        }
        start = time.perf_counter()
        try:
            impl = (
                ModelAgent(
                    agent["model"],
                    agent.get("architecture", "tools"),
                    agent.get("max_calls", 8),
                    agent.get("max_output_tokens", 1800),
                )
                if agent["strategy"] == "model"
                else ReferenceAgent(agent["strategy"])
            )
            result = impl.run(task, tools)
            evaluation = evaluate(result.output, definition["expected"])
            run.update(
                status="completed",
                output=result.output,
                summary=result.summary,
                evaluation=evaluation,
                score=evaluation["score"],
                passed=evaluation["passed"],
                error=None,
            )
        except Exception as exc:
            # Do not expose provider errors, credentials, or stack traces.
            message = (
                str(exc)[:350]
                if isinstance(exc, (ValueError, RuntimeError))
                else f"Execution failed ({type(exc).__name__}). Check server configuration."
            )
            run.update(
                status="failed",
                output={},
                summary="Run did not complete.",
                evaluation=evaluate({}, definition["expected"]),
                score=0,
                passed=False,
                error=message,
            )
        run.update(
            duration_ms=round((time.perf_counter() - start) * 1000, 3),
            events=tools.trace(),
            steps=len(tools.events),
            input_tokens=tools.input_tokens,
            output_tokens=tools.output_tokens,
            cost_usd=tools.cost_usd,
            cost_source=getattr(tools, "cost_source", "no-model-calls"),
            model_calls=getattr(tools, "model_calls", 0),
            resolved_models=getattr(tools, "resolved_models", []),
        )
        self.store.put("runs", run)
        return run

    def submit(self, agent_ids, task_ids):
        from .provider import read_only

        if read_only():
            raise ValueError("Public read-only mode prohibits execution")
        with self.lock:
            if len([j for j in self.store.all("jobs") if j["status"] in ("queued", "running")]) >= 8:
                raise ValueError("Queue is full. Wait for an active benchmark to finish.")
            job = {
                "id": uid("job"),
                "agent_ids": agent_ids,
                "task_ids": task_ids,
                "total": len(agent_ids) * len(task_ids),
                "completed": 0,
                "failed": 0,
                "run_ids": [],
                "status": "queued",
                "created_at": now(),
                "finished_at": None,
            }
            self.store.put("jobs", job)
            snapshot = json.loads(json.dumps(job))
            self.pool.submit(self.work, job)
            return snapshot

    def work(self, job):
        try:
            with self.lock:
                current = self.store.get("jobs", job["id"])
                if current.get("cancel_requested"):
                    job.update(status="cancelled", cancel_requested=True, finished_at=now())
                    self.store.put("jobs", job)
                    return
                job["status"] = "running"
                self.store.put("jobs", job)
            for aid in job["agent_ids"]:
                for tid in job["task_ids"]:
                    current = self.store.get("jobs", job["id"])
                    if current.get("cancel_requested"):
                        job.update(status="cancelled", finished_at=now())
                        self.store.put("jobs", job)
                        return
                    run = self.execute(self.store.get("agents", aid), TASK_MAP[tid], job["id"])
                    job["run_ids"].append(run["id"])
                    job["completed"] += 1
                    job["failed"] += int(run["status"] == "failed")
                    # Keep cancellation sticky even if requested while execute was running.
                    with self.lock:
                        current = self.store.get("jobs", job["id"])
                        job["cancel_requested"] = current.get("cancel_requested", False)
                        self.store.put("jobs", job)
            job.update(status="completed", finished_at=now())
            self.store.put("jobs", job)
        except Exception:
            job.update(status="failed", error="Benchmark worker failed. See server logs.", finished_at=now())
            self.store.put("jobs", job)
            import logging

            logging.exception("Benchmark worker failed")

    def leaderboard(self, category="All"):
        runs = [
            r
            for r in self.store.all("runs")
            if r["provenance"] != "self-reported"
            and r["suite_hash"] == SUITE_HASH
            and (category == "All" or r["category"] == category)
        ]
        latest = {}
        for r in sorted(runs, key=lambda r: r["created_at"]):
            latest[(r["agent_id"], r["task_id"])] = r
        # A transparent descriptive Elo: one matchup per task per unordered pair,
        # based on latest run quality. Rebuilt in task-ID / agent-ID order, K=24.
        # This is not a confidence estimate or a statistical significance claim.
        ratings, matches = {}, {}
        agents = self.store.all("agents")
        for agent in agents:
            ratings[agent["id"]], matches[agent["id"]] = 1000.0, 0
        ids = sorted(ratings)
        for tid in sorted(TASK_MAP):
            for i, a in enumerate(ids):
                for b in ids[i + 1 :]:
                    ra, rb = latest.get((a, tid)), latest.get((b, tid))
                    if not ra or not rb or ra["provenance"] != rb["provenance"]:
                        continue
                    outcome = 1 if ra["score"] > rb["score"] else (0 if ra["score"] < rb["score"] else 0.5)
                    expected = 1 / (1 + 10 ** ((ratings[b] - ratings[a]) / 400))
                    change = 24 * (outcome - expected)
                    ratings[a] += change
                    ratings[b] -= change
                    matches[a] += 1
                    matches[b] += 1
        result = []
        total = len([t for t in TASKS if category == "All" or t["category"] == category])
        for agent in agents:
            items = [r for (aid, _), r in latest.items() if aid == agent["id"]]
            if not items:
                continue
            all_costs = [r["cost_usd"] for r in items]
            result.append(
                {
                    **agent,
                    "rating": round(ratings[agent["id"]]),
                    "matches": matches[agent["id"]],
                    "success_rate": sum(r["passed"] for r in items) / len(items),
                    "quality": sum(r["score"] for r in items) / len(items),
                    "latency_ms": statistics.median(r["duration_ms"] for r in items),
                    "cost_usd": sum(all_costs) / len(items) if all(c is not None for c in all_costs) else None,
                    "task_count": len(items),
                    "total_tasks": total,
                    "run_count": sum(r["agent_id"] == agent["id"] for r in runs),
                    "latest_run_id": max(items, key=lambda r: r["created_at"])["id"],
                    "coverage": len(items) / total,
                    "track": "reference" if agent["strategy"] != "model" else "managed-model",
                }
            )
        return sorted(result, key=lambda r: (-r["coverage"], -r["quality"], -r["success_rate"], r["name"]))
