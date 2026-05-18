# Task Archive: Concrete Project Mainline Repair

- Queue Item: `ADHOC-20260513-concrete-project-mainline-repair`
- Lane: Delivery
- Status: done

## Scope
Repair ordinary concrete project generation so the issue tracker API benchmark produces a real runnable project through `new-run/status/advance`, not through agent scaffold/project modes.

## Write Scope
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/api_agent.py`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_generic_materializers.py`
- `tools/providers/project_generation_issue_tracker_fast_path.py`
- `tests/test_concrete_project_fast_path.py`
- `tests/test_issue_tracker_generation_contract.py`
- `tests/test_concrete_project_runtime_contract.py`
- `meta/tasks/CURRENT.md`
- `meta/reports/LAST.md`

## Acceptance Evidence
- Concrete benchmark PASS, status `passed`.
- Generated project is not an agent scaffold.
- Generated tests, HTTP endpoint probes, and SQLite validation pass.
- Agent planner/runtime/factory benchmarks remain passing.
- `unittest discover` PASS, 715 tests, 4 skipped.
- `verify_repo.ps1 -Profile code` PASS.
