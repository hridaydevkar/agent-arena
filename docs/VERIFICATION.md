# Verification Record · v0.2.0

This document records the automated test suites, end-to-end benchmarks, and system checks validating the **AgentArena v0.2.0** release.

---

## 1. Automated Test Suite

- **147 Python tests passed (`pytest -q`):**
  - **Data Tools & Query Engine:** Tests for deterministic AST calculation (`calculate`), table reading (`read_fixture`), single-table filtering/aggregation (`sum_column`), column extraction (`list_column`), and multi-table relational joins with deduplication (`join_and_aggregate`).
  - **Three Wire Protocols:** Verifies distinct request sequences, bounded tool loops, and independent review passes for **Direct**, **Tools**, and **Verifier** architectures.
  - **Verifier Safeguards:** Enforces the 4-call budget minimum (`max_calls >= 4`) for solver and verification passes (`backend/arena_server/main.py:203`).
  - **Deterministic Evaluator:** Field-by-field equality validation, numeric tolerance checks (`abs_tol=0.01`), array ordering, and isolation from agent context.
  - **API & Queue Mechanics:** Concurrency limits, job lifecycle transitions (`pending` → `running` → `completed` / `interrupted`), cooperative cancellation, and optional write-token (`ARENA_API_TOKEN`) enforcement.
  - **Public Read-Only Security Boundary:** Middleware verification that `ARENA_READ_ONLY=1` rejects all mutation requests (HTTP 403), refuses server startup if `OPENAI_API_KEY` is present, and filters exported reports through strict field allowlists.
  - **Generalization Regressions:** Complete regression coverage for synthetic datasets across accounting, human resources, and supply-chain relational tables.

---

## 2. End-to-End Model Benchmarks

Three standalone model-driven benchmark harnesses validate real LLM execution:

- **Invoice Reconciliation (`tests/e2e_invoice.py`):**
  - Evaluates multi-turn tool interaction, handling void status exclusions, and payment deduplication.
  - Validated with `Tools` and `Verifier` architectures.
- **Employee Data Generalization (`tests/e2e_employee.py`):**
  - Tests department salary aggregation and filtering without reliance on task-specific prompt hints.
- **Relational Orders & Items (`tests/e2e_orders.py`):**
  - Tests multi-table joins, calculating order totals and category breakdowns across relational boundaries.

---

## 3. Frontend & UI Verification

- **Production Build:** Passes clean TypeScript compilation (`tsc -b`) and Vite production bundling (`npm run build`).
- **Zero External Runtime Dependencies:** Self-hosted Inter and Manrope fonts (`frontend/public/fonts/`) with SIL Open Font License compliance.
- **Browser Playwright E2E Suite (`npm run test:e2e`):**
  - Full user journey: agent selection → benchmark run → trace replay → field evaluation → architectural comparison.
  - Mobile responsiveness: 9 core views verified at 390px viewport width without horizontal overflow.
  - Read-only gallery mode: Banner display and write-guard UI state confirmation.

---

## 4. Release Verification Boundaries

- **Local-First Scope:** Benchmarks operate locally or against user-configured endpoints; no cloud accounts, keys, or external tracking are bundled.
- **Synthetic Evaluation:** The 12 core tasks use versioned synthetic fixtures designed for deterministic evaluation; they do not represent universal general intelligence claims.
- **Security Scope:** The system binds loopback (`127.0.0.1`) by default and never executes arbitrary user-uploaded code or remote shell commands.

---

## 5. How to Reproduce

```bash
# 1. Run complete automated test suite
source .venv/bin/activate
pytest -q

# 2. Build production frontend assets
cd frontend
npm ci
npm run build
cd ..

# 3. Run browser integration tests (requires server on port 8000)
cd frontend
npm run test:e2e
```
