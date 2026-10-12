# AgentArena · v0.2

### Does adding tools or a verification pass actually make an agent better?

AgentArena is a local-first workbench for answering that question with **real model calls, explicit task checks, and inspectable traces**. It connects to OpenRouter (or another OpenAI-compatible endpoint), runs three different agent implementations on the same controlled task, and records quality, latency, calls, tokens, and known/unknown cost.

**The four starter agents are scripted reference policies, not AI models.** The new **Experiments** page is where you run genuine model-backed comparisons. Your provider key is required for those calls. No live model results have been invented or bundled into this release.

![Real model experiment setup](docs/screenshots/experiments.png)

## What changed from v0.1?

- **OpenRouter setup wizard:** hidden terminal key entry, authenticated metadata check, live model catalogue, saved git-ignored `.env`.
- **Automatic `.env` loading:** the launcher now reads local settings. No repeated shell exports.
- **Three real architectures:** Direct, Tool user, and Verifier—different code paths, not just different names.
- **Controlled experiments:** one model, selected tasks, explicit call and output-token budgets, visible consent.
- **Better evidence:** architecture, request counts, tokens, returned model IDs, and cost source are recorded.
- **OpenRouter integration:** provider-reported cost when available; helpful 401/402/429 errors; no automatic retries, model routers, or provider fallback in experiments.
- **Public results mode:** blocks writes/inference, refuses provider credentials, and uses an isolated database.
- **Summary-only publication:** export measured results without raw prompts, outputs, traces, or private error details.
- **GitHub + Render guide:** prepared deployment files, not an already-deployed website.

## For your M2 Mac with 8 GB RAM: start here

OpenRouter runs the model in the cloud. Your Mac only runs the UI/backend, so you do **not** need to load Llama locally or run Docker for this route.

### 1. Extract the new archive into a NEW folder

Do not overwrite an older customized checkout. Open a terminal in the new `agent-arena` folder. You need **Python 3.11+**, preferably 3.12/3.13. Internet is needed for dependency installation and provider calls.

The downloadable ZIP includes the compiled UI. Node is unnecessary unless you change frontend source.

### 2. Install/check the app

```bash
python3 scripts/start.py --check
```

### 3. Connect OpenRouter privately

```bash
.venv/bin/python scripts/setup_openrouter.py
```

The wizard:
1. Asks for your key with hidden typing. **Do not paste it into a chat or screenshot.**
2. Checks `/api/v1/key`—no model inference.
3. Fetches current model metadata and lists specific IDs advertising tool support.
4. Lets you select a model, including free-token-priced options if currently listed.
5. Explains pricing and requests confirmation before saving a plaintext `.env` file with owner-only permissions on macOS/Linux.

Free models still have quotas and capacity limits. Catalogue support is not a guarantee of successful tool calls. Set a low **per-key spending cap in the OpenRouter dashboard**; request/token limits in this app are not hard dollar caps.

If the catalogue cannot load, the wizard permits a manually entered model ID, but its pricing/tool support is explicitly unverified. Do not use `openrouter/free` or `openrouter/auto` for a controlled comparison because they may choose different models.

### 4. Start the app

```bash
python3 scripts/start.py --port 8002
```

Open **http://localhost:8002 → Experiments**.

Local `.env` settings override inherited shell settings when using this launcher. Secrets are not printed. Raw `uvicorn` commands do not invoke this loader; use `--env-file .env` or exported variables in that case.

### 5. Run your FIRST experiment on ONE task

1. Verify the configured model ID.
2. Keep **Reconcile a messy invoice ledger** selected; leave other tasks unselected.
3. Start with 6 calls per tool-based agent and 1,800 output tokens per request.
4. Read and confirm the provider-usage notice.
5. Click **Run three-agent comparison**.

This queues **three actual model runs**. Maximum default usage for one task is **13 model requests** (1 + 6 + 6), not necessarily 13 actual calls. Input tokens also consume quota/cost. The wizard sets one worker and a 3.2-second process-wide interval between request starts; other apps using your key can still exhaust account limits.

**If a reasoning-heavy model runs out of output tokens**, the run fails visibly. Choose a less reasoning-heavy model or explicitly raise the output cap and rerun. No invisible repair call is made.

### 6. Read the evidence

| Agent | Actual implementation |
|---|---|
| Direct | One model call with all fixtures in the prompt. No tools. |
| Tool user | Named fixture reads and arithmetic tools; bounded model/tool loop. |
| Verifier | Tool-using solver followed by a separate review call with the task, original fixtures, and draft. **No expected answers are provided.** |

Verifier's review is included in its total request budget. Verification is **not an oracle** and can worsen the answer. All three have access to the same source information, but through different mechanisms. Provider aliases, routing, model nondeterminism, and budget differences remain confounders.

Open each **Replay** and inspect the real messages/tool results. Use **Evaluation** for field checks, then **Compare** for output divergence. A single pass on one fixture is exploratory evidence, not a publishable “best agent” claim.

## Windows / Linux

Windows: `py scripts/start.py --check`, then `.venv\Scripts\python.exe scripts/setup_openrouter.py`, then `py scripts/start.py --port 8002`.

Linux: use the macOS commands. If `venv` is unavailable, install the distro's Python venv package. These paths are provided, but native macOS/Windows execution was not performed in the delivery environment.

## Can I use Gemini or my local Llama instead?

Yes, the adapter speaks the OpenAI-compatible chat-completions protocol. OpenRouter is the simplest first path for your existing key. Do not configure all providers at once.

- **Gemini:** configure Google's OpenAI-compatible base URL and a model available to your AI Studio project. Account/model/tool support and quota determine compatibility.
- **Local Llama:** if it is installed through Ollama, `ollama list` shows the exact model name. A local endpoint can use `http://localhost:11434/v1` with a non-empty compatibility key such as `ollama`. Your 8 GB shared RAM limits practical model size and tool reliability; don't download a large model just for this project. Local models are optional, not required for the OpenRouter workflow.

See [provider notes](docs/OPENROUTER.md). No Gemini account, OpenRouter key, or Ollama instance was accessed in this delivery.

---

## Publishing: both open source AND a usable website

Use two separate environments:

```text
Your Mac / a user's computer                  Public results website
───────────────────────────                  ──────────────────────
Own .env + provider key                       NO provider keys
Run actual experiments             ──►        Selected summary-only report
Full private traces                           Metrics and comparisons
Editable workspace                            Read-only UI; writes blocked
```

This is the responsible first public release: visitors explore results, inspect the protocol/source, and run the project locally with their own keys. They cannot spend your OpenRouter credits through the website.

**The publication files are ready; your accounts still need to be created/connected and deployment confirmed by you.** Nothing has been pushed to GitHub or deployed to Render automatically. Follow the [step-by-step publication guide](docs/PUBLISH.md).

### Export measured results

After a real model experiment completes:

```bash
python3 scripts/publish_results.py --url http://localhost:8002 --latest --confirm-public
```

This writes `public-data/results.json`. Alternatively, download **Export public report** in Experiments and put that file at the same path.

The export uses an allowlist and removes prompts, outputs, trace payloads, free-text descriptions, and detailed errors. **Review it anyway:** agent names, model names, timing, costs and metrics are intentionally public. It is not a general-purpose PII detector. Do not publish the private workspace snapshot or database.

Public exports are maintainer-published measurements, **not independently attested submissions**. A malicious maintainer could edit a result file; this edition does not solve that trust problem.

### Preview the public site locally

Keep the private app running on 8002 if desired. In a second terminal:

```bash
ARENA_READ_ONLY=1 OPENAI_API_KEY='' \
  .venv/bin/python -m uvicorn arena_server.main:app \
  --host 127.0.0.1 --port 8003
```

Open **http://localhost:8003**. This raw command intentionally does **not** load your private `.env`. The public app reads `public-data/results.json` if present, or shows explicitly labelled reference demos if it is absent. It creates a separate `public-readonly/arena.db` under the data directory and never opens the private database as the public workspace.

### Docker / hosting

- `Dockerfile` builds the UI and runs the Python app non-root.
- `compose.yaml` runs the private local workbench on loopback by default.
- `render.yaml` configures a public **read-only** results site with no provider key.
- `public-data/results.json`, if intentionally committed, is copied into the image.
- There is no automatic deployment workflow that can accidentally upload a local `.env`.

**No Docker daemon was available here: the image and Render deployment have not been executed.** Review the hosting plan and charges before confirming deployment. The native build and test results are documented separately.

## What this does NOT claim

- Not a public arbitrary-code execution service or a multi-user SaaS.
- No strangers' Docker images, Python uploads, hosted agent endpoints, logins or billing system.
- 12 **public synthetic development tasks**, not held-out tests of general intelligence.
- One latest attempt per task in default rankings; no confidence intervals or repeated-seed statistical analysis.
- Descriptive Elo is secondary and order-sensitive. Output checks and task coverage are the main metrics.
- No private chain-of-thought capture. Provider thought signatures can be retained in memory for continuation but are excluded from stored traces.
- Costs may be unknown. OpenRouter-reported cost is preferred; manual token-price estimates are labelled and used only for the configured model. Model overrides without applicable usage/prices stay unknown.
- Free route availability is not guaranteed. 429/402 errors are visible; the app does not retry or switch models behind your back.
- No claim to be the first agent benchmark or to have completed a production security audit. Check the working project's name before a public launch.

## Your own Python agent

The local SDK is still included:

```bash
.venv/bin/arena --url http://localhost:8002 run examples/revenue_agent.py \
  --task revenue-by-region --submit
```

Only run code you trust: SDK code executes in your local process. Imported outputs are rescored, but execution/timing/traces remain **self-reported** and are excluded from managed rankings. See the in-app Documentation → Bring your agent and [API reference](docs/API.md).

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m uvicorn arena_server.main:app --host 127.0.0.1 --port 8000 --reload --env-file .env
# second terminal:
cd frontend
npm ci
npm run dev
```

Development UI: http://localhost:5173. Vite proxies `/api` to port 8000. The compiled release uses one server; `scripts/start.py --rebuild` rebuilds frontend source with Node 20.19+ (Node 22 LTS recommended).

Use a single Uvicorn worker. Jobs are persisted as records but the queue is in-process: a restart marks incomplete jobs interrupted. Cancellation is cooperative between tasks. The default per-request network timeout is 90 seconds (15-second connect timeout); it is not a hard whole-task CPU limit.

### Tests

```bash
pip install -e '.[dev]'
pytest -q
ruff check backend sdk tests scripts examples
cd frontend
npm ci
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests expect a running production-style server on port 8000, or `ARENA_TEST_URL`. Use a disposable data directory: tests create a test agent and run. Model protocol tests use **mock HTTP replies**, never your provider credits. Do not confuse test results with real benchmark performance. See [verification record](docs/VERIFICATION.md).

## Troubleshooting

| Symptom | Next step |
|---|---|
| Still only Atlas/Meridian/Relay/Scout | Those are references. Configure OpenRouter and use **Experiments**, not another reference benchmark. |
| `.env` changes do nothing | Stop/restart via the **v0.2** launcher; check you are in the new project folder. Raw uvicorn needs `--env-file`. |
| Provider key entered in Settings token box | Wrong field. Clear it. Provider key goes through `scripts/setup_openrouter.py`. |
| Mac setup SSL certificate error | Run the wizard with `.venv/bin/python` after `start.py --check`, so it can use the installed certifi bundle. Do not disable TLS checks. |
| HTTP 401 | Key rejected. Rerun setup and restart. Never paste the key into issue reports. |
| HTTP 402 | Check balance, per-key caps, and in-flight limits in OpenRouter. Lower budgets or resolve account limits; do not assume more credits are always the only fix. |
| HTTP 429 | Wait and inspect provider quota. One experiment can use multiple requests. |
| HTTP 400 / no provider for parameters | Choose another specific model advertising tool support; routing/privacy settings may restrict availability. |
| Output cap reached / no JSON | Use a less reasoning-heavy model or explicitly increase the cap. Inspect the trace; no hidden repair/fallback was made. |
| `<1 ms` and zero model requests | You ran a reference policy, not a model agent. |
| Model cost says Unknown | Provider did not return usable cost and no applicable pricing was configured. Unknown is intentional. |
| Public app refuses to start | Remove `OPENAI_API_KEY` from that environment. Public mode deliberately refuses credentials. |
| Public site only has reference demos | No `public-data/results.json` was included. Generate a real experiment report, review, commit, and redeploy. |
| Port already in use | Stop the old process or use `--port 8002` / another free port. |
| Lost connection during an experiment | Check terminal logs and job status. A browser refresh does not cancel the background job. |

## Project map

`backend/arena_server/`: API, runner, provider adapter, SQLite, publishing boundary.  
`sdk/agent_arena/`: traced local tools, agent interface, evaluator, CLI.  
`frontend/`: custom React UI, local fonts, browser tests.  
`scripts/`: launcher, OpenRouter setup, report export, release packaging.  
`public-data/`: intentional publishable summaries only.  
`docs/`: architecture, scoring, security, providers, publishing, verification.

MIT licensed. Bundled Inter/Manrope fonts use SIL OFL; licenses are included. The source is provided locally; no PyPI package or public repository has been published for you.
