# Scoring and leaderboard methodology

## Task checks

Each task has an expected JSON object. One check is assigned to each expected top-level key, with equal weight. For that field:

- booleans must match booleans;
- numeric values use `math.isclose(rel_tol=1e-6, abs_tol=0.01)`;
- strings must match exactly;
- dictionaries must contain matching expected keys (extra keys are ignored);
- lists must match length, ordering, and values;
- missing fields fail.

Quality = passing checks / expected checks. Task success = all checks pass. An execution error contributes zero quality and no task success. The evaluator runs outside the managed agent, and managed agents do not receive the expected object through their tools. The public source still includes the expected answers: **this is not a secret test set**.

## Ranking

The default UI sorts by:

1. fraction of selected-category tasks attempted on the current suite fingerprint;
2. mean field quality across those tasks;
3. mean task success;
4. agent name for a deterministic tie breaker.

The latest attempt for each agent/task is used, not the best attempt. Reference and model tracks are shown separately. Self-reported imports are excluded. Reported latency is the median latest-run duration, and reported cost is the mean latest-run model cost; if any included cost is unknown, the mean is unknown.

Partial coverage remains visible rather than silently assigning unattempted tasks a score. Coverage has priority, which is explicit in the UI and CSV. Sorting by latency or Elo in the UI changes the displayed order; it is not the default ranking policy.

## Descriptive Elo

For each unordered pair of agents on a shared current-suite task in the same provenance track:

- larger field quality = win (`S=1`), smaller = loss (`S=0`), equal = tie (`S=0.5`);
- initial rating is 1000;
- expected outcome `E_A = 1 / (1 + 10 ** ((R_B - R_A) / 400))`;
- update `R_A += 24 * (S_A - E_A)` and `R_B -= 24 * (S_A - E_A)`.

Ratings are reconstructed from latest runs in **sorted task-ID and agent-ID order**. One pair is counted once per task; rerunning the identical result does not farm pair counts or ratings. Categories are rebuilt independently. Agent names are not used for pair order, but changing the membership of the field can change the update sequence.

This is a simple, order-sensitive descriptive Elo, **not** a Bayesian skill estimate, human preference rating, composite cost/quality rating, or a calibrated probability of real-world success. There are no claimed confidence intervals. A solitary model agent is correctly unrated even when its quality is visible.

## Scientific limitations

- Only 12 public synthetic tasks; no held-out tasks or contamination controls.
- Reference policies are tailored to the fixture operations.
- A single latest attempt does not measure run-to-run variance.
- A successful task is not proof of general reasoning, safety, or production robustness.
- No fairness guarantees between agent budgets, hidden upstream inference, or hardware.
- Reference runtimes are trivial and should not be compared to hosted LLM latency as equivalent workloads.
- No human judge validation, win-rate confidence intervals, Bradley–Terry estimation, or repeated-seed analysis is implemented.

For serious evaluation, define a preregistered protocol, held-out tasks, repeated runs, budget-normalized cohorts, audit trails, and uncertainty reporting. This app is a debugging and evaluation workbench, not a substitute for those practices.
