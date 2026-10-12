# Creating a task

The shipped suite is intentionally fixed. The API exposes tasks read-only. To extend it, edit source and restart the app.

## 1. Define an unambiguous challenge

Use small synthetic fixtures, a clear allowed-tool boundary, a structured output schema, and explicit tie breakers. Avoid live search, real purchases, user files, or facts that silently change over time.

## 2. Add a task definition

The canonical generator is `scripts/create_tasks.py`. Add an `add(...)` call containing:

```python
add(
    "unique-task-id",
    "A short task title",
    "Data analysis",          # or Research / Operations
    "Medium",                 # Easy / Medium / Hard
    "A precise instruction, including ordering and rounding rules.",
    "unique_operation",
    {"fixture_name": [{"example": 42}]},
    {"required_output": 42},  # independent expected output
    ["A skill", "Another skill"],
)
```

The generator writes `backend/arena_server/task_library.json`. It derives the visible output schema from the expected top-level fields. This edition uses JSON definitions, not YAML. Do not only edit the generated file if you intend to rerun the generator later.

## 3. Add a reference solver

In `backend/arena_server/agents.py`, handle the new `operation`. Retrieve inputs with `tools.read_file(name)`, perform actual computation, and return an `AgentResult`. Do not make the reference policy return the `expected` object directly.

The model-backed policy follows the natural-language instruction and output schema; it does not need a task-specific code branch.

## 4. Test

```bash
python scripts/create_tasks.py
pytest -q
```

The parametrized reference test checks every shipped task. Add negative tests for ambiguous edge cases and malformed output. Update the task count limits in `BenchmarkCreate`, frontend copy, and suite docs if expanding beyond 12 tasks; the current UI has deliberately explicit v1 counts rather than pretending to be an unbounded task marketplace.

## 5. Version and rerun

Bump the task version for semantic changes. The suite fingerprint is content-derived, so any task-definition change removes old-suite runs from current rankings while preserving them in history. Restart the backend and benchmark the updated suite. Automatic starter seeding happens once per workspace, not on every task change.

## Evaluation checklist

- [ ] Can a human verify the expected answer directly from the fixture?
- [ ] Does every output field test a meaningful requirement?
- [ ] Are duplicates, sort order, units, rounding, and ties specified?
- [ ] Is there at least one intentionally difficult edge case?
- [ ] Are the fixtures synthetic or appropriately licensed and free of PII?
- [ ] Is the reference solver computing the answer, not copying it?
- [ ] Is the limitation of a public development task clearly stated?
