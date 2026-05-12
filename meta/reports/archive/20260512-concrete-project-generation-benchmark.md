# Concrete Project Generation Benchmark Report

## Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `scripts/ctcp_orchestrate.py`
- `scripts/project_generation_gate.py`
- `tools/run_paths.py`
- `tools/providers/project_generation_source_stage.py`
- `tests/concrete_project_benchmark/benchmark_report.md`
- `tests/concrete_project_benchmark/generated/issue_tracker_api/benchmark_summary.json`

## Plan
1. Add the Local Issue Tracker API fixture.
2. Add a concrete benchmark runner that scouts and uses ordinary CTCP project generation only.
3. Exclude agent manifest/scaffold/project modes.
4. Run ordinary `new-run/status/advance`.
5. Validate project structure, tests, HTTP endpoints, and SQLite only if a project exists.
6. Record benchmark and repo gate evidence.

## Changes
- Added `tests/concrete_project_benchmark/fixtures/issue_tracker_api.json`.
- Added `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`.
- Added benchmark report and summary evidence under `tests/concrete_project_benchmark/`.
- Did not modify provider/core project-generation logic.
- Did not use agent modes.

## Verify
- PASS: concrete benchmark runner executed; latest status `unsupported`.
- PASS: py_compile for benchmark runner.
- PASS: workflow checks.
- FAIL: module protection check due dirty frozen-kernel `scripts/ctcp_orchestrate.py` outside current task scope.
- PASS: patch check.
- PASS: code health changed-only.
- FAIL: canonical verify failed at module protection for the same reason.

## Questions
- None.

## Demo
- Concrete benchmark status: `unsupported`.
- Actual ordinary command sequence: `ctcp_orchestrate.py new-run`, `ctcp_orchestrate.py status`, `ctcp_orchestrate.py advance --max-steps 1`.
- Latest run dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778523229`.
- Generated project path: none.
- Project tests: not available.
- HTTP endpoint tests: not available.
- SQLite verification: not available.
- Benchmark report: `tests/concrete_project_benchmark/benchmark_report.md`.

## First Failure And Repair
- First benchmark implementation copied generated source into repo, which caused code-health to judge generated benchmark subject files as repo code.
- Repaired by keeping generated project artifacts in external run dirs and storing only report/summary evidence in repo.
- Remaining repo gate blocker is unrelated dirty frozen-kernel scope in `scripts/ctcp_orchestrate.py`.

## Check/Contrast/Fix Loop Evidence
- check: ordinary generation was invoked and progressed to source_generation.
- contrast: the latest run timed out before producing a project, so endpoint/SQLite checks cannot honestly run.
- fix: result is recorded as `unsupported`, not passed.

## Completion Criteria Evidence
- connected + accumulated + consumed.
- connected: benchmark invokes ordinary CTCP project-generation mainline.
- accumulated: fixture, runner, summary, and report exist.
- consumed: command outputs and project discovery evidence drove the unsupported verdict.

## Issue Memory Decision Evidence
- no new issue-memory entry.

## Skill Decision
- skill used: `ctcp-workflow`.
- skillized: no.
