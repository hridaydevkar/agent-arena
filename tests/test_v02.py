"""Protocol, publication and safety tests. All provider replies are mocked, never real inference."""

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from agent_arena import Task, ToolContext
from arena_server.agents import ModelAgent
from arena_server.engine import SUITE_HASH, TASK_MAP
from arena_server.main import app
from arena_server.provider import check_provider, openrouter_catalog
from arena_server.publishing import make_snapshot


def patch_model_transport(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(
        "arena_server.agents.httpx.Client", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs)
    )


@pytest.mark.parametrize("architecture,expected_calls", [("direct", 1), ("tools", 2), ("verify", 3)])
def test_architectures_have_distinct_protocols(monkeypatch, architecture, expected_calls):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.delenv("ARENA_READ_ONLY", raising=False)
    requests = []
    expected = {"carrier": "Cargo", "total_cost": 20, "delivery_days": 3}

    def handler(req):
        body = json.loads(req.content)
        requests.append(body)
        assert body["model"] == "test/specific-model"
        assert body["provider"] == {"require_parameters": True, "allow_fallbacks": False}
        if len(requests) == 1 and architecture != "direct":
            content = {
                "role": "assistant",
                "content": None,
                "reasoning_details": [{"type": "reasoning.encrypted", "data": "PRIVATE-SIGNATURE"}],
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "read_fixture", "arguments": '{"name":"shipment"}'},
                    }
                ],
            }
        else:
            content = {"role": "assistant", "content": json.dumps(expected)}
        return httpx.Response(
            200,
            json={
                "model": "resolved/test-model",
                "choices": [{"message": content, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )

    patch_model_transport(monkeypatch, handler)
    task = Task.from_dict(TASK_MAP["shipping-planner"])
    tools = ToolContext(task)
    result = ModelAgent("test/specific-model", architecture, 6, 1800).run(task, tools)
    assert result.output == expected
    assert len(requests) == expected_calls
    assert tools.model_calls == expected_calls
    assert tools.cost_usd == pytest.approx(expected_calls * 0.001)
    assert tools.cost_source == "provider-reported"
    assert tools.resolved_models == ["resolved/test-model"]
    trace = json.dumps(tools.trace())
    assert "private-test-key" not in trace and "PRIVATE-SIGNATURE" not in trace
    first_input = json.loads(requests[0]["messages"][1]["content"])
    assert isinstance(first_input["fixtures"], dict if architecture == "direct" else list)
    if architecture == "direct":
        assert "tools" not in requests[0]
    else:
        # Thought signatures are retained only on the wire for providers requiring continuation.
        assert requests[1]["messages"][2]["reasoning_details"][0]["data"] == "PRIVATE-SIGNATURE"
    if architecture == "verify":
        review = json.loads(requests[-1]["messages"][1]["content"])
        assert set(review) == {"task", "output_schema", "fixtures", "draft"}
        assert review["draft"] == expected
        assert "tools" in requests[-1]
        assert any(
            tool["function"]["name"] == "calculate"
            for tool in requests[-1]["tools"]
        )
        assert any(e.name.endswith(".verification") for e in tools.events)


@pytest.mark.parametrize("status", [401, 402, 429, 503])
def test_provider_errors_are_safe_and_not_retried(monkeypatch, status):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(status, json={"error": {"message": "PRIVATE PROVIDER CONTENT"}})

    patch_model_transport(monkeypatch, handler)
    tools = ToolContext(Task.from_dict(TASK_MAP["shipping-planner"]))
    with pytest.raises(RuntimeError, match=f"HTTP {status}"):
        ModelAgent("test", "direct", 4, 1024).run(tools.task, tools)
    assert len(calls) == 1
    assert tools.cost_usd is None
    assert "PRIVATE PROVIDER CONTENT" not in json.dumps(tools.trace())


def test_request_budget_is_enforced(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    calls = []

    def handler(req):
        calls.append(json.loads(req.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": f"c{len(calls)}",
                                    "function": {"name": "read_fixture", "arguments": '{"name":"shipment"}'},
                                }
                            ],
                        }
                    }
                ]
            },
        )

    patch_model_transport(monkeypatch, handler)
    tools = ToolContext(Task.from_dict(TASK_MAP["shipping-planner"]))
    with pytest.raises(ValueError, match="tool-call budget"):
        ModelAgent("test", "tools", 3, 1024).run(tools.task, tools)
    assert len(calls) == 3
    assert "tools" not in calls[-1]


@pytest.mark.parametrize("content", ["not json", "[]", '{"x":NaN}', "", None])
def test_bad_model_outputs_fail_without_hidden_repair(content):
    with pytest.raises(ValueError):
        ModelAgent.parse_output(content)


def test_fenced_json_is_explicitly_accepted():
    assert ModelAgent.parse_output('```json\n{"x":1}\n```') == {"x": 1}


def test_public_model_catalog_is_metadata_only(monkeypatch):
    seen = []

    def get(url, **kwargs):
        seen.append((url, kwargs))
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "test/free",
                        "pricing": {"prompt": "0", "completion": "0"},
                        "supported_parameters": ["tools"],
                    },
                    {
                        "id": "test/paid",
                        "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                        "supported_parameters": [],
                    },
                ]
            },
        )

    monkeypatch.setattr("arena_server.provider.httpx.get", get)
    rows = openrouter_catalog()
    assert rows[0]["free"] is True and rows[0]["supports_tools"] is True
    assert rows[1]["input_per_million"] == 1
    assert "headers" not in seen[0][1]
    assert all("/chat/completions" not in url for url, _ in seen)


def test_key_check_never_returns_key_or_label(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setattr(
        "arena_server.provider.httpx.get",
        lambda *a, **kw: httpx.Response(
            200,
            json={
                "data": {"label": "PRIVATE LABEL", "limit_remaining": 2, "free_model_daily_requests": {"remaining": 8}}
            },
        ),
    )
    result = check_provider()
    assert result["status"] == "authenticated" and result["key_limit_remaining"] == 2
    assert "PRIVATE" not in json.dumps(result) and "private-test-key" not in json.dumps(result)


def test_experiment_validation_and_registration(client, monkeypatch):
    assert (
        client.post("/api/experiments", json={"model_id": "test/model", "task_ids": ["shipping-planner"]}).status_code
        == 422
    )
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    payload = {"model_id": "test/model", "task_ids": ["shipping-planner"], "acknowledge_provider_usage": True}
    assert client.post("/api/experiments", json={**payload, "model_id": "openrouter/free"}).status_code == 422
    assert client.post("/api/experiments", json={**payload, "task_ids": ["missing"]}).status_code == 422
    captured = {}

    def submit(aids, tids):
        captured["agents"] = [app.state.store.get("agents", aid) for aid in aids]
        return {"id": "job-test", "agent_ids": aids, "task_ids": tids, "status": "queued"}

    monkeypatch.setattr(app.state.engine, "submit", submit)
    response = client.post("/api/experiments", json=payload)
    assert response.status_code == 202
    assert response.json()["max_model_requests"] == 13
    assert [a["architecture"] for a in captured["agents"]] == ["direct", "tools", "verify"]
    assert all(a["model"] == "test/model" and a["max_calls"] == 6 for a in captured["agents"])


def fake_publish_input():
    agent = {
        "id": "model1",
        "name": "Test fixture, not real inference",
        "strategy": "model",
        "model": "test/fixture",
        "description": "SECRET DESCRIPTION",
        "api_key": "SECRET KEY",
        "framework": "Test only",
        "version": "1",
        "color": "#586b43",
        "reference": False,
        "created_at": "2026-01-01",
        "architecture": "tools",
    }
    run = {
        "id": "r1",
        "agent_id": "model1",
        "agent_name": agent["name"],
        "agent_version": "1",
        "task_id": "shipping-planner",
        "task_title": "Shipping",
        "task_version": "1.0.0",
        "category": "Operations",
        "suite_hash": SUITE_HASH,
        "status": "completed",
        "score": 1,
        "passed": True,
        "provenance": "managed-model",
        "model": "test/fixture",
        "created_at": "2026-01-01",
        "steps": 3,
        "duration_ms": 5,
        "cost_usd": 0,
        "input_tokens": 4,
        "output_tokens": 5,
        "events": [{"output": "SECRET PROMPT"}],
        "output": {"key": "SECRET OUTPUT"},
        "error": "SECRET ERROR",
        "evaluation": {"checks": [{"expected": "SECRET EXPECTED"}]},
    }
    return agent, run


def test_public_export_is_an_allowlist_not_raw_trace_copy():
    a, r = fake_publish_input()
    report = make_snapshot([a], [r], SUITE_HASH)
    assert "SECRET" not in json.dumps(report)
    assert report["runs"][0]["events"] == [] and report["runs"][0]["output"] == {}
    assert report["runs"][0]["visibility"] == "summary-only"
    assert report["runs"][0]["score"] == 1
    assert report["agents"][0]["architecture"] == "tools"
    with pytest.raises(ValueError):
        make_snapshot([a], [{**r, "provenance": "self-reported"}], SUITE_HASH)


def test_readonly_uses_isolated_store_and_blocks_all_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("ARENA_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("ARENA_READ_ONLY", "1")
    monkeypatch.setenv("ARENA_PUBLIC_SNAPSHOT", str(tmp_path / "missing.json"))
    with TestClient(app) as client:
        assert app.state.store.path == tmp_path / "public-readonly/arena.db"
        assert client.get("/api/health").json()["read_only"] is True
        assert client.get("/api/models").json()["items"] == []
        for endpoint in (
            "/api/benchmarks",
            "/api/experiments",
            "/api/agents",
            "/api/provider/check",
            "/api/import",
            "/api/jobs/x/cancel",
        ):
            assert client.post(endpoint, json={}).status_code == 403
        with pytest.raises(ValueError, match="read-only"):
            app.state.engine.submit(["atlas"], ["shipping-planner"])


def test_public_boot_refuses_provider_credentials(tmp_path, monkeypatch):
    monkeypatch.setenv("ARENA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ARENA_READ_ONLY", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "private-test-key")
    with pytest.raises(RuntimeError, match="Remove OPENAI_API_KEY"):
        with TestClient(app):
            pass


def test_public_snapshot_import_withholds_arbitrary_fields(tmp_path, monkeypatch):
    a, r = fake_publish_input()
    payload = make_snapshot([a], [r], SUITE_HASH)
    payload["runs"][0]["output"] = {"leak": "SECRET INJECTED"}
    path = tmp_path / "results.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setenv("ARENA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ARENA_READ_ONLY", "1")
    monkeypatch.setenv("ARENA_PUBLIC_SNAPSHOT", str(path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(app) as client:
        assert client.get("/api/health").json()["has_model_results"] is True
        response = client.get("/api/runs/r1")
        assert "SECRET" not in response.text
        assert len(client.get("/api/agents").json()) == 1
        assert client.get("/api/leaderboard").json()[0]["quality"] == 1


def test_env_writer_keeps_secret_private_and_other_settings(tmp_path):
    import importlib.util

    path = Path(__file__).parents[1] / "scripts/setup_openrouter.py"
    spec = importlib.util.spec_from_file_location("wizard", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    target = tmp_path / ".env"
    target.write_text("ARENA_DATA_DIR=my-data\nOPENAI_API_KEY=old\n")
    module.write_env(target, {"OPENAI_API_KEY": "private-new-key", "OPENAI_MODEL": "test/free"})
    assert target.read_text().count("OPENAI_API_KEY=") == 1
    assert "ARENA_DATA_DIR=my-data" in target.read_text()
    import os

    if os.name != "nt":
        assert target.stat().st_mode & 0o077 == 0


def test_full_experiment_to_public_report_flow(client, monkeypatch):
    """End-to-end orchestration against a test-only HTTP transport, not real results."""
    import time

    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append(body)
        if "tools" in body and not any(m["role"] == "tool" for m in body["messages"]):
            message = {
                "role": "assistant",
                "tool_calls": [
                    {"id": "fixture", "function": {"name": "read_fixture", "arguments": '{"name":"shipment"}'}}
                ],
            }
        else:
            message = {"role": "assistant", "content": '{"carrier":"Cargo","total_cost":20,"delivery_days":3}'}
        return httpx.Response(
            200,
            json={
                "model": "test/fixture-only-not-real-inference",
                "choices": [{"message": message}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "cost": 0.001},
            },
        )

    patch_model_transport(monkeypatch, handler)
    response = client.post(
        "/api/experiments",
        json={
            "model_id": "test/fixture-only-not-real-inference",
            "task_ids": ["shipping-planner"],
            "acknowledge_provider_usage": True,
        },
    )
    assert response.status_code == 202
    jid = response.json()["id"]
    job = {}
    for _ in range(100):
        job = client.get(f"/api/jobs/{jid}").json()
        if job["status"] == "completed":
            break
        time.sleep(0.01)
    assert job["status"] == "completed" and job["completed"] == 3
    assert job["failed"] == 0
    assert len(calls) == 7
    records = client.get(f"/api/runs?job_id={jid}").json()["items"]
    assert len(records) == 3 and all(r["job_id"] == jid for r in records)
    assert {r["architecture"]: r["model_calls"] for r in records} == {"direct": 1, "tools": 2, "verify": 4}
    report = client.get(f"/api/jobs/{jid}/report")
    assert report.status_code == 200
    assert len(report.json()["runs"]) == 3
    assert all(r["visibility"] == "summary-only" and not r["events"] and not r["output"] for r in report.json()["runs"])
    assert "test-only-key" not in report.text


def test_timeout_after_partial_usage_does_not_claim_known_total(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 2:
            raise httpx.ReadTimeout("private provider text not for persistence")
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "fixture",
                                    "function": {"name": "read_fixture", "arguments": '{"name":"shipment"}'},
                                }
                            ],
                        }
                    }
                ],
                "usage": {"cost": 0.001, "prompt_tokens": 10, "completion_tokens": 10},
            },
        )

    patch_model_transport(monkeypatch, handler)
    task = Task.from_dict(TASK_MAP["shipping-planner"])
    tools = ToolContext(task)
    with pytest.raises(RuntimeError, match="timed out"):
        ModelAgent("test/fixture", "tools", 4, 1024).run(task, tools)
    assert tools.model_calls == 2
    assert tools.input_tokens == 10
    assert tools.cost_usd is None and tools.cost_source == "unknown"
    assert "private provider text" not in json.dumps(tools.trace())


@pytest.mark.parametrize("configured_model", [None, "test/other-model"])
def test_overridden_model_never_borrows_configured_prices(monkeypatch, configured_model):
    monkeypatch.setenv("OPENAI_API_KEY", "test-only-key")
    monkeypatch.setenv("ARENA_CALL_INTERVAL_SECONDS", "0")
    monkeypatch.setenv("ARENA_INPUT_PRICE", "1")
    monkeypatch.setenv("ARENA_OUTPUT_PRICE", "2")
    if configured_model:
        monkeypatch.setenv("OPENAI_MODEL", configured_model)
    else:
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
    patch_model_transport(
        monkeypatch,
        lambda req: httpx.Response(
            200,
            json={
                "choices": [
    {
        "message": {
            "role": "assistant",
            "content": '{"carrier":"Test Carrier","total_cost":100,"delivery_days":2}',
        }
    }
],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10},
            },
        ),
    )
    task = Task.from_dict(TASK_MAP["shipping-planner"])
    tools = ToolContext(task)
    ModelAgent("test/overridden-model", "direct", 4, 1024).run(task, tools)
    assert tools.cost_usd is None and tools.cost_source == "unknown"
