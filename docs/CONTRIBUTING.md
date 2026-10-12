# Contributing

1. Read README.md and SECURITY.md; keep the local trust boundary explicit.
2. Use Python 3.11+ and Node 20.19+ (22 LTS recommended).
3. Install `pip install -e '.[dev]'` and run `npm ci` in frontend.
4. Run the backend and Vite as described in the README.
5. Add tests for new behavior. Run pytest, Ruff, the frontend build, and Playwright.
6. Keep fixture changes reproducible and bump their semantic version.
7. Never commit `.env`, credentials, private traces, customer fixtures, or a local database.
8. Do not silently promote self-reported runs into managed rankings.

Task contributions should follow TASK_CREATION_GUIDE.md. Security-boundary changes require a threat model, not just a new endpoint. Avoid adding a shell-execution or Docker-socket route to the web API.

The frontend uses custom CSS, local Inter/Manrope fonts, and lucide icons. Maintain responsive layouts, keyboard navigation, focus handling, reduced-motion behavior, and clear loading/error/empty states. Keep UI claims tied to real data.
