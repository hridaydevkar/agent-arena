import csv
import io
import json
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal

from agent_arena import evaluate
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .engine import SUITE_HASH, TASK_MAP, TASKS, Engine, now, public_task, run_summary, uid
from .store import Store
from . import provider


@asynccontextmanager
async def lifespan(app):
    if provider.read_only() and os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "Remove OPENAI_API_KEY from public deployments. No provider credentials belong on the public results server."
        )
    app.state.store = Store()
    app.state.engine = Engine(app.state.store)
    snapshot_path = Path(os.getenv("ARENA_PUBLIC_SNAPSHOT", "public-data/results.json"))
    if provider.read_only() and snapshot_path.is_file():
        from .publishing import load_snapshot

        load_snapshot(app.state.store, snapshot_path, SUITE_HASH)
    else:
        app.state.engine.seed()
    yield
    app.state.engine.pool.shutdown(wait=True, cancel_futures=True)


app = FastAPI(
    title="AgentArena API",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    description="Local-first benchmark workbench. Reference, managed model, and self-reported runs are distinct trust tracks.",
)


@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Avoid echoing sensitive request input or non-finite JSON values in errors.
    details = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return JSONResponse({"detail": details}, status_code=422)


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        if provider.read_only():
            return JSONResponse(
                {
                    "detail": "This is a read-only public results site. Download the project to run it with your own key."
                },
                403,
            )
        # Prevent accidental cross-origin writes to an unauthenticated local workbench.
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in (
            str(request.base_url).rstrip("/"),
            f"https://{request.headers.get('host')}",
            f"http://{request.headers.get('host')}",
        ):
            return JSONResponse(
                {"detail": "Cross-origin writes are disabled. Use the frontend's same-origin API proxy."}, 403
            )
        token = os.getenv("ARENA_API_TOKEN")
        if token and not secrets.compare_digest(request.headers.get("authorization", ""), f"Bearer {token}"):
            return JSONResponse({"detail": "A workspace API token is required. Add it in Settings."}, 401)
        length = request.headers.get("content-length")
        if length:
            try:
                if int(length) > 2_000_000:
                    return JSONResponse({"detail": "Request exceeds 2 MB limit"}, 413)
            except ValueError:
                return JSONResponse({"detail": "Invalid Content-Length"}, 400)
        body = await request.body()
        if len(body) > 2_000_000:
            return JSONResponse({"detail": "Request exceeds 2 MB limit"}, 413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def store():
    return app.state.store


def engine():
    return app.state.engine


def require(table, id):
    item = store().get(table, id)
    if not item:
        raise HTTPException(404, f"{table[:-1].capitalize()} not found")
    return item


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": "0.2.0",
        "suite_hash": SUITE_HASH,
        "mode": "public-readonly" if provider.read_only() else "local",
        "read_only": provider.read_only(),
        "provider": "Not connected (public results)" if provider.read_only() else provider.provider_name(),
        "model_configured": provider.configured(),
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "auth_enabled": bool(os.getenv("ARENA_API_TOKEN")),
        "task_count": len(TASKS),
        "provider_interval_seconds": float(os.getenv("ARENA_CALL_INTERVAL_SECONDS", "0")),
        "has_model_results": any(r["provenance"] == "managed-model" for r in store().all("runs")),
    }


@app.get("/api/overview")
def overview():
    runs = store().all("runs")
    verified = [r for r in runs if r["provenance"] != "self-reported"]
    board = engine().leaderboard()
    categories = []
    for cat in ["Data analysis", "Research", "Operations"]:
        rows = engine().leaderboard(cat)
        subset = [r for r in verified if r["category"] == cat]
        categories.append(
            {
                "name": cat,
                "tasks": sum(t["category"] == cat for t in TASKS),
                "runs": len(subset),
                "success_rate": sum(r["passed"] for r in subset) / len(subset) if subset else 0,
                "leader": rows[0]["name"] if rows else None,
            }
        )
    return {
        "agents": len(store().all("agents")),
        "tasks": len(TASKS),
        "runs": len(runs),
        "successful_runs": sum(r["passed"] for r in verified),
        "active_jobs": sum(j["status"] in ("queued", "running") for j in store().all("jobs")),
        "leader": board[0] if board else None,
        "categories": categories,
        "recent_runs": [run_summary(r) for r in runs[:8]],
        "suite_hash": SUITE_HASH,
        "suite_version": "1.0.0",
    }


@app.get("/api/tasks")
def tasks():
    return [public_task(t) for t in TASKS]


@app.get("/api/tasks/{task_id}")
def task_detail(task_id: str):
    if task_id not in TASK_MAP:
        raise HTTPException(404, "Task not found")
    return public_task(TASK_MAP[task_id])


@app.get("/api/agents")
def agents():
    return store().all("agents")


@app.get("/api/agents/{agent_id}")
def agent_detail(agent_id: str):
    return require("agents", agent_id)


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=40, pattern=r"^[\w .-]+$")
    description: str = Field(default="", max_length=300)
    strategy: Literal["methodical", "balanced", "greedy", "minimal", "model"] = "balanced"
    model_id: str | None = Field(default=None, max_length=160, pattern=r"^[A-Za-z0-9._:/+\-]+$")
    architecture: Literal["direct", "tools", "verify"] = "tools"
    max_calls: int = Field(default=6, ge=2, le=8)
    max_output_tokens: int = Field(default=1800, ge=256, le=4096)
    color: str = Field(default="#586b43", pattern=r"^#[0-9a-fA-F]{6}$")


@app.post("/api/agents", status_code=201)
def create_agent(data: AgentCreate):
    if not data.name.strip():
        raise HTTPException(422, "Agent name cannot be empty")
    if len(store().all("agents")) >= 100:
        raise HTTPException(409, "This local workspace supports up to 100 agents")
    if any(a["name"].lower() == data.name.strip().lower() for a in store().all("agents")):
        raise HTTPException(409, "An agent with this name already exists")
    if data.strategy == "model" and data.architecture == "verify" and data.max_calls < 4:
        raise HTTPException(
            422, "Verifier needs a budget of at least four model calls (2 solver turns + 2 review turns)"
        )
    if data.strategy == "model" and not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(422, "Configure OPENAI_API_KEY on the server before creating a model-backed agent")
    return store().put(
        "agents",
        {
            "id": uid("agent"),
            **data.model_dump(),
            "name": data.name.strip(),
            "model": (data.model_id or os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
            if data.strategy == "model"
            else "Deterministic",
            "framework": provider.provider_name() if data.strategy == "model" else "Python SDK",
            "version": "1.0.0",
            "created_at": now(),
            "reference": data.strategy != "model",
        },
    )


@app.post("/api/provider/check")
def provider_check():
    try:
        return provider.check_provider()
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    except Exception:
        raise HTTPException(
            502,
            "Provider authentication failed or timed out. Check the key, network and account restrictions. No inference was requested.",
        ) from None


@app.get("/api/models")
def model_catalog():
    if provider.read_only():
        return {"items": [], "note": "Public results site: no provider connections"}
    if provider.provider_name() == "OpenRouter":
        try:
            return {
                "items": provider.openrouter_catalog(),
                "note": "Live public catalogue. Listed support and prices are not guarantees of capacity. No inference requested.",
            }
        except Exception:
            raise HTTPException(
                502, "Could not retrieve OpenRouter model metadata. Use your configured model or retry later."
            ) from None
    return {
        "items": [
            {
                "id": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "name": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                "supports_tools": None,
                "free": False,
            }
        ],
        "note": "Using the server-configured model; tool support is not verified.",
    }


class ExperimentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9._:/+\-]+$")
    task_ids: list[str] = Field(min_length=1, max_length=12)
    max_calls: int = Field(default=6, ge=3, le=8)
    max_output_tokens: int = Field(default=1800, ge=256, le=4096)
    acknowledge_provider_usage: bool = False


@app.post("/api/experiments", status_code=202)
def create_experiment(data: ExperimentCreate):
    if not data.acknowledge_provider_usage:
        raise HTTPException(422, "Confirm provider usage before starting an experiment")
    if not provider.configured():
        raise HTTPException(422, "Run scripts/setup_openrouter.py locally and restart the server first")
    if len(set(data.task_ids)) != len(data.task_ids) or any(t not in TASK_MAP for t in data.task_ids):
        raise HTTPException(422, "Select distinct tasks from the library")
    if data.model_id in ("openrouter/free", "openrouter/auto"):
        raise HTTPException(422, "Select a specific model ID for this comparison, not an automatic model router")
    with engine().lock:
        if len(store().all("agents")) > 97:
            raise HTTPException(409, "The workspace needs room for three experiment agents")
        if len([j for j in store().all("jobs") if j["status"] in ("queued", "running")]) >= 8:
            raise HTTPException(429, "Queue is full; wait before starting another experiment")
        experiment_id = uid("exp")
        ids = []
        for architecture, label, color in (
            ("direct", "Direct", "#6a74aa"),
            ("tools", "Tool user", "#586b43"),
            ("verify", "Verifier", "#c58245"),
        ):
            agent = create_agent(
                AgentCreate(
                    name=f"{label} {experiment_id[-6:]}",
                    strategy="model",
                    model_id=data.model_id,
                    architecture=architecture,
                    max_calls=data.max_calls,
                    max_output_tokens=data.max_output_tokens,
                    color=color,
                    description=f"Experiment {experiment_id}: {architecture} architecture. Same model and task fixtures; separate inference calls.",
                )
            )
            ids.append(agent["id"])
        job = engine().submit(ids, data.task_ids)
        return {
            **job,
            "experiment_id": experiment_id,
            "max_model_requests": len(data.task_ids) * (1 + data.max_calls * 2),
        }


@app.get("/api/leaderboard")
def leaderboard(category: Literal["All", "Data analysis", "Research", "Operations"] = "All"):
    return engine().leaderboard(category)


@app.get("/api/runs")
def runs(
    agent_id: str | None = None,
    task_id: str | None = None,
    job_id: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items = [
        r
        for r in store().all("runs")
        if (not agent_id or r["agent_id"] == agent_id)
        and (not task_id or r["task_id"] == task_id)
        and (not job_id or r.get("job_id") == job_id)
    ]
    return {"items": [run_summary(r) for r in items[offset : offset + limit]], "total": len(items)}


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    return require("runs", run_id)


@app.get("/api/runs/{run_id}/export")
def export_run(run_id: str):
    data = require("runs", run_id)
    return Response(
        json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{data["id"]}.json"'},
    )


class BenchmarkCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    agent_ids: list[str] = Field(min_length=1, max_length=8)
    task_ids: list[str] = Field(min_length=1, max_length=12)


@app.post("/api/benchmarks", status_code=202)
def benchmark(data: BenchmarkCreate):
    if len(set(data.agent_ids)) != len(data.agent_ids) or len(set(data.task_ids)) != len(data.task_ids):
        raise HTTPException(422, "Duplicate agents or tasks are not allowed")
    for aid in data.agent_ids:
        require("agents", aid)
    if any(tid not in TASK_MAP for tid in data.task_ids):
        raise HTTPException(422, "Unknown task")
    try:
        return engine().submit(data.agent_ids, data.task_ids)
    except ValueError as exc:
        raise HTTPException(429, str(exc)) from exc


@app.get("/api/jobs")
def jobs():
    return store().all("jobs")[:50]


@app.get("/api/jobs/{job_id}")
def job_detail(job_id: str):
    return require("jobs", job_id)


@app.get("/api/jobs/{job_id}/report")
def public_job_report(job_id: str):
    from .publishing import make_snapshot

    job = require("jobs", job_id)
    if job["status"] != "completed":
        raise HTTPException(409, "Wait for this job to complete before exporting its report")
    selected = [require("runs", rid) for rid in job["run_ids"]]
    if not any(r["status"] == "completed" and r["provenance"] == "managed-model" for r in selected):
        raise HTTPException(422, "No completed model executions in this job. Resolve provider errors and rerun first.")
    try:
        report = make_snapshot(store().all("agents"), selected, SUITE_HASH)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    return Response(
        json.dumps(report, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="results.json"'},
    )


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    with engine().lock:
        job = require("jobs", job_id)
        if job["status"] not in ("queued", "running"):
            raise HTTPException(409, "This job is no longer active")
        job["cancel_requested"] = True
        store().put("jobs", job)
        return job


class TraceImport(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    agent_name: str = Field(min_length=1, max_length=60)
    task_id: str
    output: dict
    events: list[dict] = Field(default_factory=list, max_length=500)
    duration_ms: float = Field(ge=0, le=86_400_000)
    summary: str = Field(default="", max_length=500)

    @field_validator("output", "events")
    @classmethod
    def finite_json(cls, value):
        json.dumps(value, allow_nan=False)
        return value


@app.post("/api/import", status_code=201)
def import_run(data: TraceImport):
    definition = TASK_MAP.get(data.task_id)
    if not definition:
        raise HTTPException(422, "Unknown task")
    required = {"kind", "name", "input", "output", "duration_ms", "offset_ms"}
    for event in data.events:
        if not required <= event.keys() or event["kind"] not in ("tool", "llm", "note", "check", "output"):
            raise HTTPException(422, "Invalid trace event schema")
        if not isinstance(event["name"], str):
            raise HTTPException(422, "Trace event name must be a string")
        for key in ("duration_ms", "offset_ms"):
            if type(event[key]) not in (float, int) or not 0 <= event[key] <= 86_400_000:
                raise HTTPException(422, "Invalid trace timing")
    evaluation = evaluate(data.output, definition["expected"])
    run = {
        "id": uid("run"),
        "agent_id": "sdk-external",
        "agent_name": data.agent_name,
        "agent_version": "unverified",
        "task_id": data.task_id,
        "task_title": definition["title"],
        "category": definition["category"],
        "task_version": definition["version"],
        "suite_hash": SUITE_HASH,
        "created_at": now(),
        "job_id": None,
        "seeded": False,
        "provenance": "self-reported",
        "model": "Unverified",
        "strategy": "sdk",
        "status": "completed",
        "output": data.output,
        "summary": data.summary,
        "evaluation": evaluation,
        "score": evaluation["score"],
        "passed": evaluation["passed"],
        "error": None,
        "duration_ms": data.duration_ms,
        "events": [{**e, "index": i} for i, e in enumerate(data.events)],
        "steps": len(data.events),
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": None,
    }
    store().put("runs", run)
    return run_summary(run)


@app.get("/api/export/leaderboard")
def export_leaderboard():
    fields = [
        "name",
        "model",
        "track",
        "quality",
        "success_rate",
        "task_count",
        "total_tasks",
        "rating",
        "matches",
        "latency_ms",
        "cost_usd",
    ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in engine().leaderboard():
        safe = dict(row)
        for key in fields:
            value = safe.get(key)
            if isinstance(value, str) and value.startswith(("=", "+", "-", "@", "\t", "\r")):
                safe[key] = "'" + value
        writer.writerow(safe)
    return Response(
        buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="agent-arena-leaderboard.csv"'},
    )


# Production mode: API and built frontend share one origin. Development uses Vite's /api proxy.
FRONTEND = Path(os.getenv("ARENA_FRONTEND_DIR", Path(__file__).resolve().parents[2] / "frontend" / "dist"))


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path.startswith("api/"):
        raise HTTPException(404, "API endpoint not found")
    root = FRONTEND.resolve()
    file = (root / path).resolve()
    if file.is_relative_to(root) and file.is_file():
        return FileResponse(file)
    if (root / "index.html").exists():
        return FileResponse(root / "index.html")
    return JSONResponse(
        {
            "message": "AgentArena API is running. Start the frontend with npm run dev, or build it with npm run build.",
            "docs": "/docs",
        }
    )
