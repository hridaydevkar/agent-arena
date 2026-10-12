# API reference

Interactive documentation: **http://localhost:8000/api/docs**. JSON OpenAPI schema: `/api/openapi.json`. Swagger's own JS/CSS is supplied by FastAPI's CDN defaults; the main application does not need that CDN.

All write requests use JSON. If `ARENA_API_TOKEN` is set, include `Authorization: Bearer <token>`. Read endpoints are unauthenticated in this local edition.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Version, provider configured flag, suite fingerprint |
| GET | `/api/overview` | Actual aggregate metrics and latest runs |
| GET | `/api/tasks` | Visible task definitions (without expected answers) |
| GET | `/api/tasks/{id}` | Task instruction, fixtures, rubric, output schema |
| GET | `/api/agents` | Registry |
| POST | `/api/agents` | Create a managed identity with an allowlisted policy |
| GET | `/api/agents/{id}` | Agent metadata |
| POST | `/api/benchmarks` | Enqueue managed task executions |
| GET | `/api/jobs` | Latest 50 jobs |
| GET | `/api/jobs/{id}` | Job status and resulting run IDs |
| POST | `/api/jobs/{id}/cancel` | Request cancellation between tasks |
| GET | `/api/runs` | Run summaries; optional agent_id, task_id, limit (1–1000), offset |
| GET | `/api/runs/{id}` | Full recorded result, trace, evaluation |
| GET | `/api/runs/{id}/export` | JSON attachment |
| POST | `/api/import` | Rescore and save a self-reported SDK trace |
| GET | `/api/leaderboard` | Current-suite rankings; optional category |
| GET | `/api/export/leaderboard` | CSV of all categories combined |

## Create an agent

```json
{
  "name": "Northstar",
  "description": "My local reference baseline",
  "strategy": "methodical",
  "color": "#586b43"
}
```

Strategies: `methodical`, `balanced`, `greedy`, `minimal`, or `model`. `model` requires a configured server provider. Creating a new identity from a reference policy does not install new code. Names are limited to 2–40 word characters, spaces, periods, and hyphens, and must be unique ignoring case.

## Enqueue a benchmark

```json
{
  "agent_ids": ["atlas", "relay"],
  "task_ids": ["invoice-reconciliation", "shipping-planner"]
}
```

Response is `202` with a job ID. Poll the job endpoint until status is one of `completed`, `cancelled`, `failed`, or `interrupted`. A completed job may contain individual failed executions; inspect `failed` and each run's `error`.

## SDK import

```json
{
  "agent_name": "MyAgent",
  "task_id": "shipping-planner",
  "duration_ms": 10,
  "output": {"carrier": "Cargo", "total_cost": 20, "delivery_days": 3},
  "events": [],
  "summary": "Selected the cheapest carrier satisfying the constraints."
}
```

Events must include kind, name, input, output, duration_ms, and offset_ms. Kinds are `tool`, `llm`, `note`, `check`, or `output`. Timings must be finite and nonnegative. Imports are capped at 2 MB and 500 events. The server never trusts a submitted score; it derives one from output. Imported timing, agent identity, and events remain unverified.

## Error responses

`401`: write token missing/incorrect. `403`: cross-origin write. `404`: resource absent. `409`: duplicate name or non-active job cancellation. `413`: request too large. `422`: invalid schema/unsupported input/provider missing. `429`: local queue full.

Errors have a `detail` string or an array of validation details. Validation responses omit raw input values to avoid reflecting sensitive content.

## v0.2: controlled model experiments

`GET /api/health` additionally reports `provider`, `read_only`, `has_model_results`, `provider_interval_seconds`, and the configured model ID. No key is returned.

`GET /api/models` fetches public OpenRouter model metadata, never inference. Public read-only mode returns an empty catalogue.

`POST /api/provider/check` performs OpenRouter key metadata authentication only. Other compatible providers return configuration status without a live credential check. Requires the optional workspace write token if configured. This is NOT a generation/capacity test.

`POST /api/experiments`:

```json
{
  "model_id": "provider/specific-model-id",
  "task_ids": ["invoice-reconciliation"],
  "max_calls": 6,
  "max_output_tokens": 1800,
  "acknowledge_provider_usage": true
}
```

Returns 202 and a queued job, `experiment_id`, and `max_model_requests` (13 at default budgets for one task). Creates Direct, Tool user, Verifier identities on the same model. A provider must be configured; task IDs must be distinct/current; routers `openrouter/free` and `openrouter/auto` are rejected. Experiment call budgets are 3–8 and output caps 256–4096. Direct uses one request; Verifier's review consumes one of its own total calls. These are not dollar limits. The job may complete with failed individual runs.

`POST /api/agents` accepts model fields `model_id`, `architecture` (`direct`, `tools`, `verify`), `max_calls` (default 6, range 2–8; Verifier requires at least 4), and `max_output_tokens` (default 1800, range 256–4096). Model overrides never borrow the configured model's manual price estimate.

`GET /api/runs?job_id=...` filters run summaries to a selected job. Full runs additionally record architecture, model_calls, cost_source, resolved_models, provider and budgets; older run records may lack these fields.

`GET /api/jobs/{id}/report` returns a summary-only public report for a completed job with at least one completed managed-model execution. All current-suite model runs in that job are included, including failures. No prompt/output/trace/error details are included. The report is not independently attested. Names and metrics remain public and need human review.

## Read-only publication

With `ARENA_READ_ONLY=1`, all non-GET/HEAD/OPTIONS API requests are rejected with 403 before processing. The engine and model runner also prohibit job submission/inference. The public startup refuses `OPENAI_API_KEY` and uses a separate database. Existing summary-only run exports contain empty events/output and a `visibility: summary-only` marker. They are not full execution traces.

This is a public results viewer, not a hosted inference endpoint. See PUBLISH.md and SECURITY.md.
