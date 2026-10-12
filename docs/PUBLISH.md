# Publish source AND a public results site

## The release you can responsibly launch now

**An open-source agent experiment workbench with a read-only results gallery.**

Other people can:
- explore your measured results and the task/scoring protocol on the website;
- read and fork the code;
- download the project and use their own provider key locally;
- implement custom SDK agents and inspect their own runs.

They cannot submit arbitrary code to your server, use your OpenRouter account, or purchase compute through the public site. Those would require a separate hosted execution product with authentication, ownership, quotas, billing and genuine untrusted-code isolation. Don't add an API key to the public deployment to make a disabled button work.

The deployment manifests and scripts are pre-configured. Follow the phases below to publish your results gallery.

---

## Phase 1 — collect results worth showing

1. Configure your model provider following the [Quick Start in README.md](../README.md#quick-start-first-5-minutes) or [docs/OPENROUTER.md](OPENROUTER.md).
2. Run a one-task experiment on the Experiments page.
3. Confirm there are actual model-call events, and resolve provider errors before expanding.
4. Run the three starter tasks (invoice reconciliation, source conflict, inventory restock) once the connection works. Be mindful of daily free-route requests and output caps.
5. Inspect Direct, Tool user and Verifier outputs. Do NOT claim verification always helps—it may not.
6. Repeat a controlled experiment if you can afford it. The current UI does not provide statistical uncertainty or repeated-seed significance; describe your sample honestly.

Suggested first write-up question:

> On these three public synthetic tasks, did a separate model review improve field-level correctness, and what extra calls/time did it use?

Record the exact model ID, date, task suite fingerprint, request/output-token budgets, number of attempts, errors and known cost source. Review your local experiment run traces before publishing to verify tool accuracy and cost reporting.

## Phase 2 — export only the intended public report

Keep the private app running on 8000, then in a second terminal:

```bash
python3 scripts/publish_results.py --url http://localhost:8000 --latest --confirm-public
```

Or export a specific completed job:

```bash
python3 scripts/publish_results.py --url http://localhost:8000 --job YOUR_JOB_ID --confirm-public
```

The output is **public-data/results.json**. The whole selected job is exported, including failed executions; it does not select only the best attempts. The endpoint requires at least one completed model execution; reference-only or all-provider-error jobs are rejected.

What is public: agent/model names, architecture, budgets, task/version identities, quality, success, time, token/call counts and reported/estimated/unknown cost.

What is omitted: API keys, provider headers, free-text agent descriptions, raw prompts/responses, tool inputs/outputs, final artifacts, detailed error text, and expected/actual field values.

**Review the JSON manually.** Names themselves can contain sensitive content; an allowlist is not universal PII redaction. The report is a maintainer-published local measurement, not cryptographic attestation. Do not publish `.env`, `.arena`, `arena-run.json`, full trace exports, or the private workspace metadata snapshot.

### Preview exactly what visitors will see

Use a separate terminal and this command (not the private launcher, which loads your .env):

```bash
ARENA_READ_ONLY=1 OPENAI_API_KEY='' \
  .venv/bin/python -m uvicorn arena_server.main:app \
  --host 127.0.0.1 --port 8003
```

Open **http://localhost:8003**. The banner must say **Public results · read only**. Try the UI; requests to all write routes must be rejected. If `results.json` is missing, the site displays reference-only demos with an explicit warning, not fake model results.

Public mode uses a separate `public-readonly/arena.db` and refuses to boot with `OPENAI_API_KEY` set. Raw traces are unavailable in published summaries; that is intentional, not a replay bug.

## Phase 3 — put the source on GitHub

### Option A: GitHub Desktop (GUI)

1. Install GitHub Desktop and sign into your GitHub account.
2. Use **File → Add Local Repository** and select this project folder. If it isn't a Git repository, choose the option to create one here.
3. Inspect the Changes list before committing. `.env` and `.arena` must NOT be listed. `public-data/results.json` should be listed only if you reviewed and intend to publish it.
4. Commit with a message such as `Launch local agent experiment workbench`.
5. Choose **Publish repository**. Use a name you have checked for conflicts; AgentArena is only a working title.
6. Make the repository public only once you have reviewed it. Keep the MIT license and font attributions.

Never upload the entire folder through a browser without reviewing exclusions. `.gitignore` helps, but previously tracked secrets remain tracked. If a key is ever pushed, revoke/rotate it; deleting the current file isn't enough.

### Option B: Terminal Git

```bash
git init
git add .
git status --short
# Review staged filenames and content before the commit.
git diff --cached --stat
git ls-files .env '.arena/*'
# The last command must produce no private files.
git commit -m "Launch agent experiment workbench"
git branch -M main
```

Create an empty GitHub repo, then follow its instructions to add the remote and push using authenticated Git credentials. Don't embed tokens in remote URLs or shell commands shown publicly.

### Add a runnable GitHub Release

A source clone does not include `frontend/dist` (correctly git-ignored). The release ZIP should include it so users need only Python.

```bash
cd frontend
npm ci
npm run build
cd ..
python3 scripts/package.py --output ../AgentArena-v0.2.zip
```

Create a GitHub Release (`v0.2.0`) and attach that ZIP. The packager intentionally excludes `.env`, databases, dependencies, and `results.json`; downloaded private workspaces start fresh. The hosted site gets the reviewed report from the repository instead.

Update the README's actual repository/release/demo links after they exist. Do not insert made-up URLs or claim the SDK is on PyPI.

## Phase 4 — deploy the PUBLIC results showcase

### Option A: GitHub Pages (Recommended — 100% Free, No Credit Card Required)

A GitHub Actions workflow is provided at `.github/workflows/deploy-pages.yml` to build and publish a static, read-only showcase of AgentArena directly on GitHub Pages. It requires zero billing setup, no credit card, and no backend server maintenance:

1. **Enable GitHub Pages via Actions:**
   - In your GitHub repository, go to **Settings** → **Pages**.
   - Under **Build and deployment** → **Source**, select **GitHub Actions**.
2. **Deploy:**
   - Push to `main` or trigger the workflow manually from **Actions** → **Deploy Static Demo to GitHub Pages** → **Run workflow**.
   - The workflow installs frontend dependencies, compiles the static demo bundle (`VITE_STATIC_DEMO=true npm run build`), configures 404 fallbacks for SPA client-side routing, and deploys the artifact to GitHub Pages.
3. **Verify:**
   - Open your GitHub Pages URL (`https://<username>.github.io/<repo-name>/`).
   - Confirm all views load: Overview, Leaderboard, Tasks, Runs, Replay, and Experiments.
   - The demo runs 100% client-side with bundled public benchmark data, making zero calls to localhost or private inference servers.

### Option B: Containerized Hosting (Render / Docker)

A **Render blueprint** is provided in `render.yaml` for users who prefer containerized hosting. Note that cloud container providers (such as Render) may request credit card verification:

1. Log into Render and connect the reviewed GitHub repo.
2. Create a new **Blueprint** from that repo (Render reads `render.yaml`).
3. Review the proposed service, region, compute plan, and any charges before approving.
4. Confirm these environment settings:

```text
ARENA_READ_ONLY=1
ARENA_DATA_DIR=/tmp/arena-public
ARENA_PUBLIC_SNAPSHOT=/app/public-data/results.json
```

5. **Do not add OPENAI_API_KEY**, OPENROUTER_API_KEY, a Gemini key, or your `.env`. The service needs no inference credentials.
6. Deploy. The image builds the frontend and installs the Python app. Container port 8000 is used by the included image.
7. Open the assigned HTTPS URL and test:
   - `/api/health` reports `read_only: true` and `model_configured: false`;
   - the public-mode banner is visible;
   - your expected report appears, or an explicit reference-only demo warning appears if you did not include a report;
   - direct refreshes of `/leaderboard`, `/experiments` and `/compare` work;
   - `POST /api/experiments` and other write routes return 403;
   - no raw prompts or private outputs are available in run exports.

## Phase 5 — tell a credible launch story

Use your actual observations, not placeholder percentages:

> I built an open-source workbench to compare a direct-answer agent, a tool-using agent and a verification agent using the same model and tasks. It records actual model/tool calls and independently checks structured outputs. Here is what happened on [N tasks / M attempts], with [exact model ID and budgets]. The tasks are synthetic and public; this is an exploratory comparison, not a general intelligence ranking. The results site is read-only. Anyone can run the workbench locally with their own key.

Include one short video: select a task → run → inspect a failed check → compare the two outputs. Explain an interesting failure, not only a perfect score.

Before posting:
- [ ] Repository and release ZIP really exist
- [ ] Demo URL loads and has no provider key
- [ ] Your real experiment completed; no test/mocked results are presented as real
- [ ] Model ID, task/version, budgets, sample size and limitations are stated
- [ ] No secret, private terminal command, account page, or `.env` appears in the video
- [ ] You're not claiming to be the first agent benchmark or a production-safe code sandbox
- [ ] Someone else has followed the setup guide successfully

## What “bigger” should mean next

1. Get a few external builders to run the SDK on their agents and report friction.
2. Add meaningful domain tasks with licensed, held-out variants and stronger negative tests.
3. Add repeated runs, variance, budget-normalized cohorts and explicit comparability groups.
4. Add adapters for real external agent implementations—without confusing self-reported traces with attested execution.
5. Only then design hosted accounts, queue isolation, quotas, billing and sandboxing.

A public write-enabled copy of the local app is NOT that hosted product. Do not expose it just to make the project look bigger.
