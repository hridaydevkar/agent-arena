# Architecture

## A complete local vertical slice

The app is intentionally a single-user workbench. React + TypeScript provides the UI; FastAPI serves the JSON API; SQLite stores agents, jobs, and complete run records. A bounded thread pool runs trusted reference policies or a bounded model-tool loop. This keeps setup small and avoids implying that scaffolding for a distributed service is production-ready.

### Request flow

1. `POST /api/benchmarks` validates the selected agents/tasks, duplicate IDs, and queue capacity.
2. A job record is created with its initial status. The executor schedules it.
3. The worker instantiates `Task` and `ToolContext` from a versioned synthetic fixture.
4. A reference policy performs real transformations; a model policy calls the configured provider and can read named fixtures or evaluate arithmetic.
5. The independent evaluator compares structured output to expected top-level fields.
6. A complete immutable-by-convention run JSON is stored, including result, evaluation, events, timing, token usage, and known/unknown cost.
7. Job progress is persisted after each task. Browser polling refreshes the UI.
8. Leaderboards derive the latest current-suite run for each `(agent_id, task_id)`; repeated runs do not manufacture new Elo matches.

### Storage

`Store` uses SQLite with WAL mode, short connections, parameterized values, a process-local lock, and a 30-second connection timeout. Four tables hold JSON records and initialization metadata. Table names are selected from explicit allowlists.

This favors inspectability and minimal migrations over analytics scale. There is no durable queue, relational trace indexing, object storage, database encryption, automatic retention, or row-level ownership.

### Execution boundaries

There are three provenance values:

- `reference`: the server runs one of four trusted, hand-written Python policies.
- `managed-model`: the server calls the registered model through a configured provider and exposes only read-only fixture/arithmetic tools.
- `self-reported`: the SDK runs custom code on the submitter’s computer and imports JSON. The server rechecks output but cannot attest to execution.

The API never imports uploaded Python, accepts shell commands, fetches submitted URLs, or starts agent containers. Docker is only the app packaging format. See SECURITY.md before considering public hosting.

### Model execution

Model requests use an explicit registered model identifier. Model requests are bounded by each agent’s budget (default API budget 6, maximum 8), with at most 8 tool calls per solver turn. Output-token caps default to 1,800 and can be configured up to 4,096. Network timeouts are 90 seconds, with a 15-second connect timeout; these are not hard whole-task deadlines. Direct makes one model request, and Verifier reserves one of its budgeted requests for review. Provider credentials remain server-side. Persisted message fields are limited to role/content/tool_calls; private provider reasoning fields are omitted. Usage-based cost is calculated only when usage and prices are available.

Prices and runner version are included in managed run metadata. The provider base URL is environment configuration, not a versioned agent artifact. Upstream model aliases and provider behavior can drift; this local edition does not attest to model weights or remote environment stability.

### Task versioning

The suite fingerprint is a SHA-256-derived identifier of the serialized task definitions, including expected values. It changes whenever definitions change. Stale-suite runs remain inspectable in history but are omitted from current rankings. Version labels are human-managed; fingerprints are content-derived.

### Frontend

Routes cover overview, leaderboard, experiments, tasks, agent profiles, history, replay, comparison, documentation, and settings. All functional data comes from the API. Relative `/api` calls work under the native server, Docker, or the Vite same-origin development proxy. The design uses self-hosted fonts and inline SVG, not a CDN UI dependency.

Workspace data refreshes every 6 seconds while the page is visible; a benchmark dialog polls its active job every 750ms. Most pages load up to 1,000 latest run summaries. Trace detail is fetched only when needed. This is intentionally not a websocket/live-streaming tracing system.

### Restart semantics

Completed runs persist. A new server process marks persisted queued/running jobs `interrupted`; it does not resume an unknown partial job. Cancellation is cooperative between tasks. Do not start multiple Uvicorn workers: the queue, locks, and cancellation protocol are single-process.

### Scale-out path

1. Introduce users, ownership, read authentication, audit logs, and per-user quotas.
2. Move relational metadata to PostgreSQL with migrations and indexed task/version lookups.
3. Put large trace objects in object storage with redaction and retention.
4. Replace the thread pool with a durable, idempotent job queue and leases.
5. Build a separately isolated execution plane for untrusted artifacts (microVMs or equivalent), with no host Docker socket exposed to API workers.
6. Add controlled model/network gateways, billing controls, dataset governance, held-out evaluations, and audited provenance before publishing rankings.

## v0.2 additions

`provider.py` owns provider recognition, safe error descriptions, process-wide pacing and metadata-only catalogue/key checks. `ModelAgent` now branches into direct, bounded tool-use and tool-use-plus-review protocols. Verifier reserves one request from its total budget for a fresh review with original fixtures/draft, never expected answers. Private continuation signatures stay in memory and are stripped from trace projections.

`POST /api/experiments` creates three identities and queues their executions with common model/tasks/budgets. Output evaluation remains the independent field evaluator. Failed provider calls are recorded without retry or repair. Token/model/cost evidence is attached to each run; provider-reported cost is preferred and unknown cost is never presented as zero.

`publishing.py` produces and loads a versioned, allowlisted summary report. Public startup reads `public-data/results.json` into an isolated database, blocks all mutation routes, and refuses provider credentials. It exposes no paid execution capability and does not accept community submissions. The report is maintainer-published, not independently attested.

`scripts/setup_openrouter.py` handles hidden local key input and model selection. `scripts/serve.py` loads `.env` before Uvicorn imports the app; `scripts/start.py` invokes it in the project virtual environment. Docker gets environment settings directly and does not load local dotenv files. `render.yaml` is an optional read-only deployment blueprint, not a completed deployment.
