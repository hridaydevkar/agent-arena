"""Allowlisted, summary-only publication. Never exports prompts, keys, fixtures, or outputs."""

import json
from datetime import UTC, datetime
from pathlib import Path

AGENT_FIELDS = {
    "id",
    "name",
    "model",
    "strategy",
    "architecture",
    "framework",
    "version",
    "color",
    "reference",
    "created_at",
    "max_calls",
    "max_output_tokens",
}
RUN_FIELDS = {
    "id",
    "agent_id",
    "agent_name",
    "agent_version",
    "task_id",
    "task_title",
    "task_version",
    "category",
    "suite_hash",
    "created_at",
    "status",
    "score",
    "passed",
    "provenance",
    "model",
    "strategy",
    "runner_version",
    "architecture",
    "max_calls",
    "max_output_tokens",
    "provider",
    "duration_ms",
    "steps",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "cost_source",
    "model_calls",
    "resolved_models",
}


def public_agent(agent):
    return {
        **{k: v for k, v in agent.items() if k in AGENT_FIELDS},
        "description": "Published benchmark entry. Raw prompts, traces and outputs are withheld.",
    }


def public_run(run):
    result = {k: v for k, v in run.items() if k in RUN_FIELDS}
    result.update(
        visibility="summary-only",
        events=[],
        output={},
        summary="Public summary only. Raw model messages and artifacts were not published.",
        error="Execution failed; details withheld from public report." if run["status"] == "failed" else None,
        seeded=False,
        job_id=None,
        evaluation={"score": run["score"], "passed": run["passed"], "checks": []},
    )
    return result


def make_snapshot(agents, runs, suite_hash):
    selected = [r for r in runs if r["provenance"] == "managed-model" and r["suite_hash"] == suite_hash]
    if not selected:
        raise ValueError(
            "There are no current-suite model runs to publish. Run a real experiment first; reference policies are not model results."
        )
    ids = {r["agent_id"] for r in selected}
    return {
        "format": "agent-arena-public-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "suite_hash": suite_hash,
        "notice": "Maintainer-published local results, not independently attested. Public synthetic development tasks; a small sample, not general intelligence rankings.",
        "agents": [public_agent(a) for a in agents if a["id"] in ids],
        "runs": [public_run(r) for r in selected],
    }


def load_snapshot(store, path: Path, suite_hash):
    if path.stat().st_size > 10_000_000:
        raise ValueError("Public snapshot exceeds 10 MB")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "agent-arena-public-v1" or payload.get("suite_hash") != suite_hash:
        raise ValueError("Snapshot format or task suite is incompatible")
    # Reapply the allowlist even to hand-edited input files.
    clean = make_snapshot(payload["agents"], payload["runs"], suite_hash)
    if len(clean["agents"]) > 100 or len(clean["runs"]) > 1000:
        raise ValueError("Public snapshot is too large for this workbench")
    ids = {a["id"] for a in clean["agents"]}
    for run in clean["runs"]:
        if run["agent_id"] not in ids or not 0 <= run["score"] <= 1:
            raise ValueError("Invalid published run")
    store.replace_public(clean["agents"], clean["runs"])
