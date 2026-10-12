import time

from arena_server.engine import SUITE_HASH
from arena_server.main import app


def wait_job(client, id):
    # Test-only bounded polling of asynchronous job completion.
    for _ in range(100):
        job = client.get(f"/api/jobs/{id}").json()
        if job["status"] not in ("queued", "running"):
            return job
        time.sleep(0.02)
    raise AssertionError("Job did not complete")


def test_startup_and_seed(client):
    health = client.get("/api/health").json()
    assert health["status"] == "ok"
    assert health["suite_hash"] == SUITE_HASH
    assert len(client.get("/api/tasks").json()) == 12
    assert len(client.get("/api/agents").json()) == 4
    assert client.get("/api/runs").json()["total"] == 48
    overview = client.get("/api/overview").json()
    assert overview["successful_runs"] == 22
    assert overview["leader"]["name"] == "Atlas"
    assert not any("expected" in t for t in client.get("/api/tasks").json())


def test_full_vertical_slice(client):
    agent = client.post("/api/agents", json={"name": "Northstar", "strategy": "methodical"}).json()
    response = client.post(
        "/api/benchmarks", json={"agent_ids": [agent["id"]], "task_ids": ["invoice-reconciliation", "shipping-planner"]}
    )
    assert response.status_code == 202
    job = wait_job(client, response.json()["id"])
    assert job["status"] == "completed" and job["completed"] == 2
    run = client.get(f"/api/runs/{job['run_ids'][0]}").json()
    assert run["passed"] and run["score"] == 1
    assert run["output"]["outstanding_total"] == 1100
    assert len(run["events"]) >= 6
    assert run["model"] == "Deterministic"
    exported = client.get(f"/api/runs/{run['id']}/export")
    assert exported.status_code == 200 and exported.json() == run
    board = client.get("/api/leaderboard").json()
    assert next(a for a in board if a["id"] == agent["id"])["task_count"] == 2
    assert board[0]["id"] == "atlas"  # coverage outranks a cherry-picked subset


def test_import_rechecks_but_cannot_change_rankings(client):
    before = client.get("/api/leaderboard").json()
    result = client.post(
        "/api/import",
        json={
            "agent_name": "ExternalAgent",
            "task_id": "shipping-planner",
            "duration_ms": 5,
            "output": {"carrier": "Cargo", "total_cost": 20, "delivery_days": 3},
        },
    )
    assert result.status_code == 201
    assert result.json()["provenance"] == "self-reported"
    assert result.json()["passed"] is True
    assert client.get("/api/leaderboard").json() == before


def test_duplicate_or_invalid_requests(client):
    assert client.post("/api/agents", json={"name": "Atlas"}).status_code == 409
    assert client.post("/api/agents", json={"name": "   "}).status_code == 422
    assert client.post("/api/agents", json={"name": "Hosted", "strategy": "model"}).status_code == 422
    assert client.post("/api/agents", json={"name": "Image", "strategy": "docker"}).status_code == 422
    assert (
        client.post(
            "/api/benchmarks", json={"agent_ids": ["atlas", "atlas"], "task_ids": ["shipping-planner"]}
        ).status_code
        == 422
    )
    assert client.post("/api/benchmarks", json={"agent_ids": ["atlas"], "task_ids": ["missing"]}).status_code == 422
    assert (
        client.post("/api/benchmarks", json={"agent_ids": ["missing"], "task_ids": ["shipping-planner"]}).status_code
        == 404
    )
    assert client.get("/api/runs/missing").status_code == 404
    assert client.get("/api/tasks/missing").status_code == 404
    assert client.get("/api/unknown").status_code == 404
    assert client.get("/api/runs?limit=1001").status_code == 422


def test_write_token_and_cross_origin(client, monkeypatch):
    monkeypatch.setenv("ARENA_API_TOKEN", "test-secret")
    assert client.get("/api/health").json()["auth_enabled"]
    assert client.post("/api/agents", json={"name": "A new one"}).status_code == 401
    assert (
        client.post(
            "/api/agents", json={"name": "A new one"}, headers={"Authorization": "Bearer test-secret"}
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/agents",
            json={"name": "Another one"},
            headers={"Authorization": "Bearer test-secret", "Origin": "https://untrusted.invalid"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/agents",
            json={"name": "Safe origin"},
            headers={"Authorization": "Bearer test-secret", "Origin": "http://testserver"},
        ).status_code
        == 201
    )


def test_rankings_do_not_farm_matches(client):
    before = client.get("/api/leaderboard").json()
    job = client.post("/api/benchmarks", json={"agent_ids": ["atlas"], "task_ids": ["shipping-planner"]}).json()
    wait_job(client, job["id"])
    after = client.get("/api/leaderboard").json()
    assert [a["rating"] for a in before] == [a["rating"] for a in after]
    assert [a["matches"] for a in before] == [a["matches"] for a in after]
    assert after[0]["run_count"] == before[0]["run_count"] + 1
    assert after[0]["matches"] == 36


def test_category_filter_and_csv(client):
    rows = client.get("/api/leaderboard?category=Research").json()
    assert all(a["task_count"] == 4 and a["total_tasks"] == 4 and a["matches"] == 12 for a in rows)
    assert client.get("/api/leaderboard?category=Invalid").status_code == 422
    export = client.get("/api/export/leaderboard")
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "Atlas" in export.text and len(export.text.splitlines()) == 5
    assert "cost_usd" in export.text


def test_bad_trace_and_body_limit(client):
    body = {
        "agent_name": "Test",
        "task_id": "shipping-planner",
        "duration_ms": 5,
        "output": {},
        "events": [{"name": "bad"}],
    }
    assert client.post("/api/import", json=body).status_code == 422
    assert (
        client.post(
            "/api/import",
            content='{"agent_name":"X","task_id":"shipping-planner","duration_ms":0,"output":{"a":NaN}}',
            headers={"Content-Type": "application/json"},
        ).status_code
        == 422
    )
    assert client.post("/api/agents", content="x" * 2_000_001).status_code == 413


def test_existing_completed_job_cannot_cancel(client):
    job = client.post("/api/benchmarks", json={"agent_ids": ["atlas"], "task_ids": ["shipping-planner"]}).json()
    wait_job(client, job["id"])
    assert client.post(f"/api/jobs/{job['id']}/cancel").status_code == 409


def test_current_suite_excludes_stale_run(client):
    row = app.state.store.all("runs")[0]
    row["suite_hash"] = "stale"
    app.state.store.put("runs", row)
    board = client.get("/api/leaderboard").json()
    assert next(r for r in board if r["id"] == row["agent_id"])["task_count"] == 11


def test_seed_idempotent(client):
    app.state.engine.seed()
    assert client.get("/api/runs").json()["total"] == 48


def test_verifier_max_calls_boundary(client, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    # Verify architecture: max_calls = 3 must be rejected with 422
    res_three = client.post(
        "/api/agents",
        json={"name": "Verifier-3", "strategy": "model", "architecture": "verify", "max_calls": 3},
    )
    assert res_three.status_code == 422
    assert "at least four model calls" in res_three.text

    # Verify architecture: max_calls = 4 must be accepted with 201
    res_four = client.post(
        "/api/agents",
        json={"name": "Verifier-4", "strategy": "model", "architecture": "verify", "max_calls": 4},
    )
    assert res_four.status_code == 201
    assert res_four.json()["architecture"] == "verify"
    assert res_four.json()["max_calls"] == 4

    # Other architectures (direct, tools) with max_calls = 3 must NOT be rejected by this check
    res_tools = client.post(
        "/api/agents",
        json={"name": "Tools-3", "strategy": "model", "architecture": "tools", "max_calls": 3},
    )
    assert res_tools.status_code == 201

