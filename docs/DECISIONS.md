# Design decisions

| Decision | Reason | Trade-off |
|---|---|---|
| React + Vite instead of Next.js | This is an interactive local workbench, with no SEO/server-rendering requirement. A static UI served by FastAPI is one process to run. | No SSR or Next-specific hosting features. |
| SQLite instead of PostgreSQL | No external service, portable data, easy local start. | JSON scans and single-process orchestration limit scale. |
| Thread pool instead of Redis/Celery | A bounded, inspectable execution path with no broker setup. | Queue does not resume across restarts. |
| Managed policies, not arbitrary uploads | Avoid pretending a Docker container alone is a safe untrusted-code sandbox. | Custom implementations use the local SDK and are not attested for public rankings. |
| Synthetic structured tasks | Reproducible fixtures and independent deterministic checks. | Narrow evaluation scope; no claims about general intelligence. |
| Explicit reference/model/import tracks | Prevents an offline demo or self-reported run looking like verified AI performance. | More labels and constraints in the UI. |
| Coverage + quality primary ranking | A directly interpretable score. | Does not capture subjective preference or uncertainty. |
| Descriptive Elo secondary | Demonstrates real same-task pairwise updates without inventing human votes. | Order sensitive; not statistically validated. |
| Unknown costs stay unknown | Invented dollar values mislead. | Users must configure provider prices. |
| Observable traces, no private reasoning | Real tool/model I/O is enough to inspect behavior. | Cannot claim to expose every internal operation or chain-of-thought. |
| Public fixtures and source | Makes development reproducible and auditing easy. | They are easy to overfit; not a held-out benchmark. |
| Self-hosted fonts and inline SVG | The core interface does not depend on external CDNs or image endpoints. | Slightly larger downloadable bundle. |
| Prebuilt UI in release ZIP | A Python-only local launch lowers installation friction. | Source UI changes still need Node/npm to rebuild. |
