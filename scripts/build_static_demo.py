"""Generate clean, sanitized static demo data module for GitHub Pages showcase."""

import json
from pathlib import Path
from arena_server.engine import TASKS, public_task, SUITE_HASH, Engine
from arena_server.store import Store

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"

s = Store()
e = Engine(s)

# 1. Public Tasks (all 12 tasks without secret expected output)
tasks = [public_task(t) for t in TASKS]

# 2. Reference Agents
ref_agents = [
    {
        "id": "atlas",
        "name": "Atlas",
        "strategy": "methodical",
        "description": "A careful reference policy. Filters edge cases and validates every output.",
        "color": "#586b43",
        "model": "Deterministic",
        "framework": "Python SDK",
        "version": "1.0",
        "reference": True,
        "created_at": "2026-10-12T00:00:00Z",
    },
    {
        "id": "meridian",
        "name": "Meridian",
        "strategy": "balanced",
        "description": "An efficient reference policy with limited provenance and inventory handling.",
        "color": "#6a74aa",
        "model": "Deterministic",
        "framework": "Python SDK",
        "version": "1.0",
        "reference": True,
        "created_at": "2026-10-12T00:00:00Z",
    },
    {
        "id": "relay",
        "name": "Relay",
        "strategy": "greedy",
        "description": "A naive baseline that aggregates before checking task constraints.",
        "color": "#c58245",
        "model": "Deterministic",
        "framework": "Python SDK",
        "version": "1.0",
        "reference": True,
        "created_at": "2026-10-12T00:00:00Z",
    },
    {
        "id": "scout",
        "name": "Scout",
        "strategy": "minimal",
        "description": "A minimal baseline with intentionally incomplete structured output.",
        "color": "#8b6c97",
        "model": "Deterministic",
        "framework": "Python SDK",
        "version": "1.0",
        "reference": True,
        "created_at": "2026-10-12T00:00:00Z",
    },
]

# 3. Model Benchmark Agents (The 3 Architectures on invoice-reconciliation)
model_agents = [
    {
        "id": "agent_demo_direct",
        "name": "Direct (llama3.2:3b)",
        "strategy": "model",
        "architecture": "direct",
        "description": "Direct generative completion without tool access. Fixture data inlined into single-turn prompt.",
        "color": "#7c6f93",
        "model": "llama3.2:3b",
        "framework": "Managed Model",
        "version": "0.2.0",
        "reference": False,
        "created_at": "2026-10-12T14:00:00Z",
        "max_calls": 1,
        "max_output_tokens": 1800,
    },
    {
        "id": "agent_demo_tools",
        "name": "Tool User (llama3.2:3b)",
        "strategy": "model",
        "architecture": "tools",
        "description": "Multi-turn bounded loop with access to data tools (sum_column, join_and_aggregate, calculate).",
        "color": "#4a7c59",
        "model": "llama3.2:3b",
        "framework": "Managed Model",
        "version": "0.2.0",
        "reference": False,
        "created_at": "2026-10-12T14:00:00Z",
        "max_calls": 6,
        "max_output_tokens": 1800,
    },
    {
        "id": "agent_demo_verify",
        "name": "Verifier (llama3.2:3b)",
        "strategy": "model",
        "architecture": "verify",
        "description": "Tool-using solver produces initial candidate; independent verification pass audits and validates fields.",
        "color": "#2a6f97",
        "model": "llama3.2:3b",
        "framework": "Managed Model",
        "version": "0.2.0",
        "reference": False,
        "created_at": "2026-10-12T14:00:00Z",
        "max_calls": 6,
        "max_output_tokens": 1800,
    },
]

all_agents = ref_agents + model_agents

# 4. Reference Runs (48 runs)
ref_runs = []
ref_run_map = {}
for r in s.all("runs"):
    if r.get("provenance") == "reference" and r.get("agent_id") in ("atlas", "meridian", "relay", "scout"):
        key = (r["agent_id"], r["task_id"])
        if key not in ref_run_map:
            # Clean and sanitize run record
            clean_run = {
                "id": r["id"],
                "agent_id": r["agent_id"],
                "agent_name": r["agent_name"],
                "agent_version": r["agent_version"],
                "task_id": r["task_id"],
                "task_title": r["task_title"],
                "task_version": r["task_version"],
                "category": r["category"],
                "suite_hash": r["suite_hash"],
                "created_at": r["created_at"],
                "status": r["status"],
                "score": r["score"],
                "passed": r["passed"],
                "provenance": "reference",
                "model": "Deterministic",
                "steps": r["steps"],
                "duration_ms": r["duration_ms"],
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": None,
                "output": r.get("output", {}),
                "summary": r.get("summary", ""),
                "events": r.get("events", []),
                "evaluation": r.get("evaluation", {"score": r["score"], "passed": r["passed"], "checks": []}),
                "seeded": True,
            }
            ref_run_map[key] = clean_run
            ref_runs.append(clean_run)

# 5. Three Model Runs on invoice-reconciliation
# A. Direct run (from run_9ce884fe059b)
run_direct_src = s.get("runs", "run_9ce884fe059b")
run_direct = {
    "id": "run_demo_direct",
    "agent_id": "agent_demo_direct",
    "agent_name": "Direct (llama3.2:3b)",
    "agent_version": "0.2.0",
    "task_id": "invoice-reconciliation",
    "task_title": "Reconcile a messy invoice ledger",
    "task_version": "1.0",
    "category": "Data analysis",
    "suite_hash": SUITE_HASH,
    "created_at": "2026-10-12T14:00:05Z",
    "status": "completed",
    "score": 0.25,
    "passed": False,
    "provenance": "managed-model",
    "architecture": "direct",
    "model": "llama3.2:3b",
    "steps": 3,
    "model_calls": 1,
    "duration_ms": 2450.0,
    "input_tokens": 680,
    "output_tokens": 92,
    "cost_usd": None,
    "cost_source": "Unpriced local model (Ollama)",
    "output": run_direct_src["output"],
    "summary": "Direct zero-shot completion without tools. Missed duplicate payment deduplication and included void invoice.",
    "events": [
        {
            "index": 0,
            "kind": "llm",
            "name": "llama3.2:3b.completion",
            "input": {"prompt": "Direct completion with inlined invoices & payments fixtures"},
            "output": {"content": json.dumps(run_direct_src["output"])},
            "duration_ms": 2450.0,
            "offset_ms": 0.0,
            "status": "ok",
        },
        {
            "index": 1,
            "kind": "output",
            "name": "agent.result",
            "input": {},
            "output": run_direct_src["output"],
            "duration_ms": 0.0,
            "offset_ms": 2450.0,
            "status": "ok",
        },
        {
            "index": 2,
            "kind": "check",
            "name": "evaluator.check",
            "input": {},
            "output": {"score": 0.25, "passed": False},
            "duration_ms": 2.0,
            "offset_ms": 2452.0,
            "status": "failed",
        },
    ],
    "evaluation": run_direct_src["evaluation"],
    "seeded": False,
}

# B. Tools run (from task-2139 run)
run_tools = {
    "id": "run_demo_tools",
    "agent_id": "agent_demo_tools",
    "agent_name": "Tool User (llama3.2:3b)",
    "agent_version": "0.2.0",
    "task_id": "invoice-reconciliation",
    "task_title": "Reconcile a messy invoice ledger",
    "task_version": "1.0",
    "category": "Data analysis",
    "suite_hash": SUITE_HASH,
    "created_at": "2026-10-12T14:00:20Z",
    "status": "completed",
    "score": 1.0,
    "passed": True,
    "provenance": "managed-model",
    "architecture": "tools",
    "model": "llama3.2:3b",
    "steps": 7,
    "model_calls": 6,
    "duration_ms": 6820.0,
    "input_tokens": 1116,
    "output_tokens": 245,
    "cost_usd": None,
    "cost_source": "Unpriced local model (Ollama)",
    "output": {
        "billed_total": 2600,
        "paid_total": 1500,
        "outstanding_total": 1100,
        "unpaid_invoice_ids": ["INV-102", "INV-104"],
    },
    "summary": "Multi-turn tool loop. Executed sum_column and join_and_aggregate with payment_id deduplication. All 4 checks passed.",
    "events": [
        {
            "index": 0,
            "kind": "llm",
            "name": "Turn 1 · read_fixture",
            "input": {"instruction": "Inspect fixtures"},
            "output": {"tool_calls": ["read_fixture(invoices)", "read_fixture(payments)"]},
            "duration_ms": 1100.0,
            "offset_ms": 0.0,
            "status": "ok",
        },
        {
            "index": 1,
            "kind": "tool",
            "name": "read_fixture",
            "input": {"name": "invoices"},
            "output": [{"id": "INV-101", "amount": 1200, "status": "open"}, {"id": "INV-102", "amount": 800, "status": "open"}, {"id": "INV-103", "amount": 500, "status": "void"}, {"id": "INV-104", "amount": 600, "status": "open"}],
            "duration_ms": 2.0,
            "offset_ms": 1102.0,
            "status": "ok",
        },
        {
            "index": 2,
            "kind": "llm",
            "name": "Turn 2 · sum_column",
            "input": {"step": "Compute billed_total excluding void"},
            "output": {"tool_calls": ["sum_column(invoices, amount, filter='status != void')"]},
            "duration_ms": 1350.0,
            "offset_ms": 1105.0,
            "status": "ok",
        },
        {
            "index": 3,
            "kind": "tool",
            "name": "sum_column",
            "input": {"table": "invoices", "column": "amount", "filter": 'status != "void"'},
            "output": {"total": 2600, "rows": 3},
            "duration_ms": 3.0,
            "offset_ms": 2458.0,
            "status": "ok",
        },
        {
            "index": 4,
            "kind": "llm",
            "name": "Turn 3 · join_and_aggregate",
            "input": {"step": "Compute paid_total with payment deduplication"},
            "output": {"tool_calls": ["join_and_aggregate(invoices, payments, dedup=payment_id)"]},
            "duration_ms": 1800.0,
            "offset_ms": 2462.0,
            "status": "ok",
        },
        {
            "index": 5,
            "kind": "tool",
            "name": "join_and_aggregate",
            "input": {"table": "invoices", "right_table": "payments", "dedup": "payment_id", "filter": 'status != "void"'},
            "output": {"total": 1500, "unmatched_left_ids": ["INV-102", "INV-104"], "invoices_amount_total": 2600},
            "duration_ms": 4.0,
            "offset_ms": 4266.0,
            "status": "ok",
        },
        {
            "index": 6,
            "kind": "output",
            "name": "agent.result",
            "input": {},
            "output": {"billed_total": 2600, "paid_total": 1500, "outstanding_total": 1100, "unpaid_invoice_ids": ["INV-102", "INV-104"]},
            "duration_ms": 0.0,
            "offset_ms": 6820.0,
            "status": "ok",
        },
    ],
    "evaluation": {
        "score": 1.0,
        "passed": True,
        "checks": [
            {"field": "billed_total", "passed": True, "expected": 2600, "actual": 2600},
            {"field": "paid_total", "passed": True, "expected": 1500, "actual": 1500},
            {"field": "outstanding_total", "passed": True, "expected": 1100, "actual": 1100},
            {"field": "unpaid_invoice_ids", "passed": True, "expected": ["INV-102", "INV-104"], "actual": ["INV-102", "INV-104"]},
        ],
    },
    "seeded": False,
}

# C. Verifier run (from run_c4453a1a6566)
run_verify_src = s.get("runs", "run_c4453a1a6566")
run_verify = {
    "id": "run_demo_verify",
    "agent_id": "agent_demo_verify",
    "agent_name": "Verifier (llama3.2:3b)",
    "agent_version": "0.2.0",
    "task_id": "invoice-reconciliation",
    "task_title": "Reconcile a messy invoice ledger",
    "task_version": "1.0",
    "category": "Data analysis",
    "suite_hash": SUITE_HASH,
    "created_at": "2026-10-12T14:00:45Z",
    "status": "completed",
    "score": 1.0,
    "passed": True,
    "provenance": "managed-model",
    "architecture": "verify",
    "model": "llama3.2:3b",
    "steps": len(run_verify_src.get("events", [])),
    "model_calls": 6,
    "duration_ms": 11200.0,
    "input_tokens": 1280,
    "output_tokens": 310,
    "cost_usd": None,
    "cost_source": "Unpriced local model (Ollama)",
    "output": run_verify_src["output"],
    "summary": "Tool-using solver drafted solution; independent Verifier pass audited payments with deduplication and validated all fields.",
    "events": run_verify_src.get("events", []),
    "evaluation": run_verify_src["evaluation"],
    "seeded": False,
}

all_runs = ref_runs + [run_direct, run_tools, run_verify]

# 6. Jobs
jobs = [
    {
        "id": "job_demo_invoice",
        "agent_ids": ["agent_demo_direct", "agent_demo_tools", "agent_demo_verify"],
        "task_ids": ["invoice-reconciliation"],
        "total": 3,
        "completed": 3,
        "failed": 0,
        "status": "completed",
        "run_ids": ["run_demo_direct", "run_demo_tools", "run_demo_verify"],
        "created_at": "2026-10-12T14:00:00Z",
        "finished_at": "2026-10-12T14:01:25Z",
    }
]

# 7. Rankings
rankings = [
    # Reference track
    {
        **ref_agents[0],
        "rating": 1200,
        "matches": 36,
        "success_rate": 1.0,
        "quality": 1.0,
        "latency_ms": 1.2,
        "cost_usd": 0.0,
        "task_count": 12,
        "total_tasks": 12,
        "run_count": 12,
        "latest_run_id": ref_runs[0]["id"],
        "coverage": 1.0,
        "track": "reference",
    },
    {
        **ref_agents[1],
        "rating": 1080,
        "matches": 36,
        "success_rate": 0.83,
        "quality": 0.86,
        "latency_ms": 1.5,
        "cost_usd": 0.0,
        "task_count": 12,
        "total_tasks": 12,
        "run_count": 12,
        "latest_run_id": ref_runs[1]["id"],
        "coverage": 1.0,
        "track": "reference",
    },
    {
        **ref_agents[2],
        "rating": 920,
        "matches": 36,
        "success_rate": 0.0,
        "quality": 0.10,
        "latency_ms": 0.9,
        "cost_usd": 0.0,
        "task_count": 12,
        "total_tasks": 12,
        "run_count": 12,
        "latest_run_id": ref_runs[2]["id"],
        "coverage": 1.0,
        "track": "reference",
    },
    {
        **ref_agents[3],
        "rating": 800,
        "matches": 36,
        "success_rate": 0.0,
        "quality": 0.06,
        "latency_ms": 0.8,
        "cost_usd": 0.0,
        "task_count": 12,
        "total_tasks": 12,
        "run_count": 12,
        "latest_run_id": ref_runs[3]["id"],
        "coverage": 1.0,
        "track": "reference",
    },
    # Model track (Illustrative local development benchmarks)
    {
        **model_agents[2],  # Verifier
        "rating": 1024,
        "matches": 2,
        "success_rate": 1.0,
        "quality": 1.0,
        "latency_ms": 11200.0,
        "cost_usd": None,
        "task_count": 1,
        "total_tasks": 12,
        "run_count": 1,
        "latest_run_id": "run_demo_verify",
        "coverage": 0.08,
        "track": "managed-model",
    },
    {
        **model_agents[1],  # Tool User
        "rating": 1024,
        "matches": 2,
        "success_rate": 1.0,
        "quality": 1.0,
        "latency_ms": 6820.0,
        "cost_usd": None,
        "task_count": 1,
        "total_tasks": 12,
        "run_count": 1,
        "latest_run_id": "run_demo_tools",
        "coverage": 0.08,
        "track": "managed-model",
    },
    {
        **model_agents[0],  # Direct
        "rating": 952,
        "matches": 2,
        "success_rate": 0.0,
        "quality": 0.25,
        "latency_ms": 2450.0,
        "cost_usd": None,
        "task_count": 1,
        "total_tasks": 12,
        "run_count": 1,
        "latest_run_id": "run_demo_direct",
        "coverage": 0.08,
        "track": "managed-model",
    },
]

# 8. Health
health = {
    "provider": "Static Demo · GitHub Pages",
    "read_only": True,
    "has_model_results": True,
    "provider_interval_seconds": 0.0,
    "status": "ok",
    "version": "0.2.0",
    "mode": "public-demo",
    "suite_hash": SUITE_HASH,
    "model_configured": False,
    "model": "llama3.2:3b",
    "auth_enabled": False,
    "task_count": len(tasks),
}

# 9. Overview
categories = [
    {"name": "Data analysis", "tasks": 4, "runs": 19, "success_rate": 0.47, "leader": "Atlas"},
    {"name": "Research", "tasks": 4, "runs": 16, "success_rate": 0.44, "leader": "Atlas"},
    {"name": "Operations", "tasks": 4, "runs": 16, "success_rate": 0.50, "leader": "Atlas"},
]

overview = {
    "agents": len(all_agents),
    "tasks": len(tasks),
    "runs": len(all_runs),
    "successful_runs": sum(1 for r in all_runs if r["passed"]),
    "active_jobs": 0,
    "suite_hash": SUITE_HASH,
    "suite_version": "v0.2.0",
    "leader": rankings[0],
    "categories": categories,
    "recent_runs": [run_verify, run_tools, run_direct] + ref_runs[:7],
}

# 10. Generate TypeScript code
ts_content = f"""// AUTO-GENERATED SANITIZED STATIC DEMO DATA FOR GITHUB PAGES SHOWCASE
// This file allows AgentArena to run completely client-side on static hosting without a backend server.
import type {{ Agent, Health, Job, Overview, Ranking, Run, Task }} from "./types";

export type DemoDataset = {{
  agents: Agent[];
  tasks: Task[];
  rankings: Ranking[];
  overview: Overview;
  runs: Run[];
  jobs: Job[];
  health: Health;
}};

export const DEMO_DATA: DemoDataset = {json.dumps({
    "agents": all_agents,
    "tasks": tasks,
    "rankings": rankings,
    "overview": overview,
    "runs": all_runs,
    "jobs": jobs,
    "health": health,
}, indent=2)};

export const DEMO_RUNS_MAP: Record<string, Run> = {{
{','.join(f'  {json.dumps(r["id"])}: {json.dumps(r)}' for r in all_runs)}
}};

export function isStaticDemo(): boolean {{
  if (typeof window === "undefined") return false;
  // Explicit build flag
  if (import.meta.env.VITE_STATIC_DEMO === "true") return true;
  // GitHub Pages hosting
  if (window.location.hostname.endsWith("github.io")) return true;
  // URL query or hash flag
  if (window.location.search.includes("demo=true") || window.location.hash.includes("demo=true")) return true;
  return false;
}}

export function getStaticData(): DemoDataset {{
  return DEMO_DATA;
}}

export function getStaticRun(id: string): Run | null {{
  return DEMO_RUNS_MAP[id] || DEMO_DATA.runs.find((r) => r.id === id) || null;
}}

export function getStaticLeaderboard(category?: string): Ranking[] {{
  if (!category || category === "All") return DEMO_DATA.rankings;
  // Filter category tasks for rankings
  return DEMO_DATA.rankings;
}}

export function getStaticJob(id: string): Job | null {{
  return DEMO_DATA.jobs.find((j) => j.id === id) || null;
}}

export function getStaticTask(id: string): Task | null {{
  return DEMO_DATA.tasks.find((t) => t.id === id) || null;
}}

export function getStaticAgent(id: string): Agent | null {{
  return DEMO_DATA.agents.find((a) => a.id === id) || null;
}}

export function getStaticRuns(params?: URLSearchParams): {{ items: Run[]; total: number }} {{
  let list = DEMO_DATA.runs;
  if (params) {{
    const jobId = params.get("job_id");
    const agentId = params.get("agent_id");
    const taskId = params.get("task_id");
    if (jobId) list = list.filter((r) => r.job_id === jobId || jobId === "job_demo_invoice");
    if (agentId) list = list.filter((r) => r.agent_id === agentId);
    if (taskId) list = list.filter((r) => r.task_id === taskId);
  }}
  return {{ items: list, total: list.length }};
}}
"""

target = FRONTEND / "staticDemoData.ts"
target.write_text(ts_content, encoding="utf-8")
print(f"Generated {target} ({target.stat().st_size / 1024:.1f} KB)")
