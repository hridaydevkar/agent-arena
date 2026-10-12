# Provider notes — OpenRouter first

## Why your existing OpenRouter key works

The implementation uses an OpenAI-compatible `/chat/completions` schema, not a requirement to buy an OpenAI account. With OpenRouter the base URL is `https://openrouter.ai/api/v1`. A specific model ID (including its provider prefix) is passed on every request.

The compatibility environment variable is still called `OPENAI_API_KEY`. The setup wizard fills it with your **OpenRouter** key, sets the correct base URL/model and stores the result locally. Never put that provider key in the browser's optional workspace-token field.

Official references checked while preparing v0.2:
- API / headers / request format: https://openrouter.ai/docs/api_reference/overview
- Key metadata / credits / rate limits: https://openrouter.ai/docs/api_reference/limits
- Live public model catalogue: https://openrouter.ai/api/v1/models
- Model discovery: https://openrouter.ai/models?supported_parameters=tools

Provider documentation/catalogues are the source of truth, not a pinned list of “free models.” The setup lists current metadata; it does not guarantee availability.

## Setup safety

Run `python3 scripts/start.py --check`, then `.venv/bin/python scripts/setup_openrouter.py` on macOS/Linux. This uses the installed certifi CA bundle when available; TLS verification is never disabled.

The wizard calls only `GET /key` (authenticated) and `GET /models` (public). It does not send a chat-completion request, authorize a purchase, or create a new provider key. It cannot promise that the chosen model will accept a later tool request. It requests confirmation before saving a plaintext `.env` with owner-only file permissions on macOS/Linux. The file is git-ignored, not encrypted.

When using `scripts/start.py`, local `.env` values override inherited shell environment settings. The v0.1 launcher did not load .env; make sure you're using the new code.

## Limits and cost

- Provider free-route limits are real; check current account metadata/dashboard. Multiple API keys do not give you unlimited capacity.
- The setup selects one worker and a 3.2-second interval between model-request starts. This is a local pacing policy, not a guarantee against account-wide rate limits.
- One selected task in the default three-agent experiment allows at most 13 model requests: 1 direct + 6 tool user + 6 verifier (including review).
- Output tokens are capped per request; input tokens also cost money.
- Use provider-side per-key spending caps. The app does not enforce a hard dollar limit or manage your billing account.
- For OpenRouter, valid `usage.cost` is used when returned. Otherwise, configured per-million-token prices can estimate cost only for the configured model. Missing/unknown usage/pricing stays unknown. Partial failed requests can be billable, so no-response errors are not labelled free.
- No automatic model fallback, provider fallback, retry, or JSON-repair inference call occurs in the model runner. A retry from the UI is a new execution with possible charges.
- `openrouter/free` and `openrouter/auto` are rejected by the controlled-experiment API because they can route across model identities.

The adapter requests required parameter support and disables provider fallback. Model-provider routing can still select an eligible initial provider; the actual responding model ID is recorded if returned. Different upstream providers, aliases, model versions and nondeterminism remain comparability limitations.

## Output formats and private reasoning

The model is instructed to return a JSON object. A single enclosing Markdown JSON fence is accepted and stripped, but malformed prose/JSON fails visibly; the app does not invent an answer. A length-truncated completion is a visible error.

Provider-specific thought signatures may be kept in memory and returned on subsequent tool-continuation requests when required. Private reasoning and signature fields are omitted from persisted message traces. Observable prompts, tool arguments, outputs and final answers remain private workspace data until you choose to export a summary. This is not a complete PII/secret-redaction system; don't insert private data into fixtures or agent names.

## Gemini / AI Studio alternative

If you later choose direct Gemini compatibility, configure a Gemini key locally and use:

```text
OPENAI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
OPENAI_MODEL=<a model available to your Google project with the required tool support>
OPENAI_API_KEY=<your Gemini API key>
```

The generic adapter is not a native Gemini SDK. Model availability, region, account terms, quota, parameter support and billing are provider-dependent. The OpenRouter-specific metadata checker is not a Gemini authentication test. No live Gemini calls were tested here.

## Your small local Llama alternative

First identify the runtime. If you use Ollama:

```bash
ollama list
```

Use the exact installed model name. An Ollama-compatible setup commonly uses:

```text
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=<exact installed model name>
OPENAI_API_KEY=ollama
```

The non-empty key is a compatibility placeholder, not a paid credential. Keep the endpoint on loopback. Small models on an M2 with 8 GB unified memory may struggle with JSON/tool use; no inference-speed or memory-fit guarantee is made. Don't run a large local model plus Docker/IDE merely to try this workbench. OpenRouter does not consume your Mac's model-weight memory.
