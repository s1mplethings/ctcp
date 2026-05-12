# Task Archive - Concrete Project Generation Benchmark

## Queue Binding

- Queue Item: `ADHOC-20260512-concrete-project-generation-benchmark`
- Lane: Delivery Lane
- Status: blocked by repo module-protection gate.

## Scope

- Added `tests/concrete_project_benchmark/fixtures/issue_tracker_api.json`.
- Added `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`.
- Added benchmark evidence under `tests/concrete_project_benchmark/`.

## Outcome

- Concrete benchmark status: `unsupported`.
- Ordinary project generation command used: `ctcp_orchestrate.py new-run/status/advance`.
- Agent modes were discovered but excluded: `agent-manifest`, `agent-scaffold`, `agent-project`.
- Latest run did not produce a concrete project because `source_generation` timed out before a generated project was discoverable.

## Verification

- PASS: benchmark runner executed and wrote `tests/concrete_project_benchmark/benchmark_report.md`.
- PASS: py_compile for benchmark runner.
- PASS: workflow checks after task-card evidence update.
- PASS: patch check.
- PASS: code health changed-only after generated project source was no longer copied into repo.
- FAIL: module protection and canonical verify, because `scripts/ctcp_orchestrate.py` is dirty and frozen-kernel protected outside this task write scope.

## Report

- `tests/concrete_project_benchmark/benchmark_report.md`
