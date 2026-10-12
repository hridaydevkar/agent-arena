# Verification record · v0.2

## Executed in the delivery environment

Linux x86_64, Python 3.13, Node 20, npm 10, headless Chromium through Playwright. The following are implementation tests, not real model benchmark scores.

- **74 Python tests passed.** Coverage includes SDK tools/evaluation, all 12 correct reference solutions, API validation/write-token/origin/body limits, SQLite persistence, interrupted jobs, independent rescoring and self-reported provenance, ranking/category behavior, plus:
  - Direct / Tool user / Verifier wire protocols with distinct call histories;
  - bounded requests and verification reservation;
  - strict final JSON handling, with no hidden repair inference;
  - safe 401/402/429/503 errors, no retry, unknown cost on no-response failure;
  - partial token usage plus a later timeout, without claiming a known total cost;
  - private thought signatures retained only for continuation, not in persisted traces;
  - OpenRouter metadata mapping and key/label exclusion;
  - experiment consent/validation/registration;
  - full experiment queue → model adapter → evaluation → three records → summary report flow using test-only HTTP replies;
  - model overrides do not inherit unrelated manual token prices;
  - public report field allowlists, import resanitization, isolated public database, write/inference prohibitions and credential refusal;
  - atomic `.env` updates and owner-only Unix permissions.
- **Ruff check passed** for backend, SDK, tests, scripts and examples.
- **Production frontend build passed:** TypeScript checking and Vite bundling.
- **7 Playwright browser tests passed**, covering:
  1. Register → benchmark → execution → replay playback → checks → artifact → comparison → JSON download.
  2. Task/category/difficulty filtering and fixture/schema inspection.
  3. Leaderboard/search/export/scoring modal/SDK docs.
  4. Nine main views at 390px with no document-wide horizontal overflow and working mobile navigation.
  5. OpenRouter setup, three architecture cards, task selection, changing request budgets and no-key execution guard.
  6. A separately running public read-only server: banner, execution disabled, POST denied and mobile layout.
  7. Summary-only replay: withheld details are not falsely shown as an empty model answer (explicit transformed-response UI test).
- **Live public OpenRouter model catalogue fetched successfully.** This was an unauthenticated GET, not model inference. Catalogue records/prices/tool-support fields were parsed; availability may change.
- **Fresh release ZIP install:** integrity/exclusion audit; extracted into another directory; created a new project virtual environment; installed dependencies; detected and used the bundled UI without Node or a frontend source build.
- **All seven browser tests repeated successfully with the private app served from the extracted release**, with the separate read-only server used for its public boundary test.
- **Fresh launcher served on 8002:** verified v0.2 health and `.env` overriding an intentionally different inherited setting, without storing a real provider key.
- **SDK CLI smoke test:** the included revenue agent executed locally, saved a real reference-style tool trace and imported it as self-reported (not managed model evidence).
- Desktop and mobile experiment/setup screenshots inspected. UI uses bundled fonts and inline graphics.

The optional public browser test requires `ARENA_PUBLIC_TEST_URL`; otherwise it is skipped. The included CI definition starts both servers, but CI has not been executed on GitHub during delivery.

## Not executed / not claimed

- **No live model inference, paid OR free.** Your OpenRouter key was not supplied or used. Mock replies validate application/protocol behavior, not provider capacity, task accuracy, generation latency, cost or tool reliability. First live one-task validation must happen on your own machine/account.
- Setup's authenticated `/key` call was tested with mocked HTTP metadata, not your credentials. A successful real metadata check alone does not guarantee inference will work.
- No live Gemini or Ollama inference; no local model/runtime identified on your Mac.
- No Docker daemon was available: Docker/Compose were not built or executed, and Render was not deployed.
- No native macOS/Windows run was performed. Platform-specific commands are provided, but delivery verification occurred on Linux.
- No account creation/authorization, GitHub push/release, public website deployment or PyPI publication.
- No load test, penetration test, production security audit, accessibility audit, or statistical/general-intelligence validation.

One upstream Starlette TestClient/httpx deprecation warning appeared. It did not fail the tests or affect the running provider HTTP adapter.

## Reproduce

See README.md for Python/build/test commands. Browser tests require a production-style server (default port 8000 or `ARENA_TEST_URL`) and a disposable data directory because they register an agent and execute reference tasks. For the public boundary test, start a separate server with `ARENA_READ_ONLY=1`, no provider key, a different data directory and port 8003, then set `ARENA_PUBLIC_TEST_URL=http://127.0.0.1:8003`.

Public source and release ZIP intentionally contain no actual model-result snapshot. Run a genuine experiment first and review its report before following PUBLISH.md.
