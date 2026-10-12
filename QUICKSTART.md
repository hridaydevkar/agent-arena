# Your Mac → real experiment → public release

## Use the NEW v0.2 folder

Extract the new ZIP separately from your old copy. Open a terminal in the new **agent-arena** folder. Keep your old project as a backup. Don't copy old virtual environments or node_modules into the new folder.

## Run these three commands, in order

```bash
python3 scripts/start.py --check
```

```bash
.venv/bin/python scripts/setup_openrouter.py
```

Paste your OpenRouter key only at the hidden local-terminal prompt. Choose a **specific** current model with tool support. Confirm saving `.env`. The wizard checks metadata only, not model generation. Set a low per-key spending cap in your OpenRouter account.

```bash
python3 scripts/start.py --port 8002
```

## Open http://localhost:8002 → Experiments

1. Leave **Reconcile a messy invoice ledger** as the only task selected.
2. Check the configured model ID.
3. Keep the default budgets initially.
4. Read/confirm the usage warning.
5. Click **Run three-agent comparison**.

The three agents are different:
- **Direct:** one prompt, all fixtures, no tools.
- **Tool user:** retrieves data and calculates using tools.
- **Verifier:** tool-using solver plus a separate review pass, without expected answers.

This is real cloud inference using your key. Your M2/8 GB Mac doesn't load the model. A free-priced model can still be rate-limited or unavailable. See the error in Replay if a run fails; no automatic retries or silent model switching occur.

## What success looks like

Three recorded runs with **model-call trace events**. Quality can be high or low—that is what you are measuring. Inspect calls, outputs and evaluator checks before drawing conclusions. Don't confuse Atlas/Meridian/etc. with AI models; those remain scripted references.

## Then publish BOTH source and a results website

```bash
python3 scripts/publish_results.py --url http://localhost:8002 --latest --confirm-public
```

Review `public-data/results.json`. It contains summaries, not raw traces. Then follow **docs/PUBLISH.md** for GitHub and a public read-only website. You must connect your own accounts and confirm deployment. No key belongs on that public server.

**Don't send your API key to anyone.** To ask for help, send a screenshot of the result/error with no key or `.env` contents visible.
