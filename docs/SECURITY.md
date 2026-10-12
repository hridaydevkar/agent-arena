# Security model and public-deployment checklist

## Supported use

One trusted person, running a local workbench on a trusted device. The launcher binds `127.0.0.1`; Docker publishes `127.0.0.1:8000`. Do not expose it to the internet with real credentials or sensitive traces.

An optional `ARENA_API_TOKEN` protects write routes, but read endpoints remain open. This is **not multi-user authentication**. Cross-origin browser writes are blocked; this is not a complete local-service hardening story (e.g. DNS rebinding). A malicious local process may reach the service. Keep it loopback-only and use the optional write token.

## What does not run on the server

- Arbitrary uploaded Python
- User-submitted shell commands
- Agent Docker images
- User-submitted remote agent endpoints
- Unrestricted filesystem tools
- Live booking/payment/purchase tools

Built-in policies operate on in-memory synthetic JSON fixtures. The calculator traverses a restricted AST and has expression/result magnitude limits. It never calls `eval()` or `exec()`.

The model provider URL is configured by the trusted operator in the server environment. It is not accepted as a per-request user URL. A model can request only named fixture reads or constrained arithmetic. Fixture text is identified as untrusted data in the model system prompt, but no claim of universally prompt-injection-proof behavior is made.

## SDK trust boundary

`arena run` imports and executes your Python file locally with your permissions. Only run code you trust. The server accepts a capped JSON trace after execution and reruns output checks. Neither the trace nor timing is attested; imported results are excluded from managed leaderboards.

## Traces and secrets

Provider Authorization headers and API keys are not placed in normal run trace payloads. Private provider reasoning fields are removed before message persistence. Observable prompts/tool arguments/results may still contain sensitive information if you add it to tasks or your custom instrumentation. Automated secret/PII redaction is **not implemented**. Never record keys in inputs or use real customer data in this edition.

The frontend stores a workspace write token in local storage if you explicitly save it. Do not use an untrusted browser/device or add untrusted frontend code. Read endpoints can expose complete traces, expected results, and metadata to anyone who can reach the port.

## Resource limits

8 queued/running jobs, 1–4 worker threads, at most 8 agents × 12 tasks per job, 100 registered agents, capped imported request size and event count. Model calls have turn/tool/output-token limits and network timeouts. These are local reliability controls, **not** hostile-code isolation or complete spend controls. Cancellation waits for the current task to finish. There is no hard CPU interrupt for reference policies (they are fixed trusted code).

## Before accepting untrusted public users

- [ ] TLS, secure sessions, authenticated reads and writes
- [ ] User ownership and authorization on every resource
- [ ] CSRF, origin/host allowlists, rate limits, quotas, and abuse controls
- [ ] A durable queue with idempotent task leases, retries, and cancellation semantics
- [ ] Separately isolated untrusted execution workers, ideally VM/microVM boundaries
- [ ] No Docker socket mounted into the web/API service
- [ ] Egress restrictions; controlled model/tool proxy; DNS and metadata-IP protections
- [ ] Provider-scoped credentials and hard budget controls
- [ ] Artifact/image validation, provenance, read-only mounts, syscall restrictions
- [ ] Secret/PII redaction before trace persistence; retention and deletion controls
- [ ] Monitoring, audit logging, incident response, vulnerability management
- [ ] Held-out benchmark data and defenses against leaderboard gaming

The included Dockerfile runs the app non-root, drops capabilities through Compose, and uses a read-only root filesystem. Those are good packaging defaults, **not evidence that arbitrary agent code is safe to execute inside it**.

## v0.2 public results mode (separate from private execution)

A limited public **read-only** service is supported with `ARENA_READ_ONLY=1`. It is NOT the private app with a password removed.

- Startup refuses a configured `OPENAI_API_KEY`; do not add any provider credentials to the public environment.
- All mutation methods are denied by middleware; Engine.submit and ModelAgent.run have additional guards.
- The store is isolated under `<data-root>/public-readonly/arena.db`. A public snapshot is reloaded through explicit agent/run field allowlists, not copied from the private database.
- `GET /api/models` does not query a provider in public mode. Key metadata checks are POST and are blocked.
- Reports include selected names, identities and metrics, but no raw trace/prompt/output fields or detailed errors. Names can still contain private data; review them. Allowlisting is not general PII detection.
- Private reasoning/signatures are removed from persisted traces, but can remain transiently in the model continuation history where provider protocols require them.
- The public report is maintainer-produced, editable and not independently attested. It cannot establish execution provenance against a dishonest maintainer.
- Use HTTPS through the hosting platform. No formal penetration test or production security audit was performed.
- Public-mode protections do not make the write-enabled local service safe to expose publicly. Account authentication, authorization, abuse controls, rate limiting, durable queues and sandboxing remain future work.

The setup wizard uses TLS verification and hidden terminal input, writes a git-ignored plaintext `.env` with owner-only Unix permissions, and performs no inference. The file is not encrypted. The launcher intentionally lets that local file override inherited shell exports; use raw uvicorn (without --env-file) for a second public-mode preview so private settings aren't reloaded accidentally.

Request count/output-token bounds and process-local pacing reduce accidental usage, but **are not monetary limits**. Use a provider-side per-key spending cap. Request timeouts/failures may still consume quota or charges, so cost is marked unknown when usage cannot be verified.
