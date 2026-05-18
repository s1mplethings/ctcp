# CTCP Report Archive: Concrete Project Mainline Repair

## Readlist
- `AGENTS.md`
- `meta/tasks/CURRENT.md`
- `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
- `tests/concrete_project_benchmark/fixtures/issue_tracker_api.json`
- `tools/providers/api_agent.py`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_source_stage.py`
- `tools/providers/project_generation_generic_materializers.py`
- `tools/providers/project_generation_issue_tracker_fast_path.py`

## Plan
- Repair only the ordinary concrete project generation mainline.
- Keep agent runtime/planner/factory paths unchanged except for regression verification.
- Generate a real Local Issue Tracker API through `new-run/status/advance`.

## Changes
- Added a narrow `concrete_fast_path` contract for the issue tracker API benchmark.
- Added a deterministic local materializer for the generated stdlib HTTP/SQLite project.
- Routed only `generation_mode=concrete_fast_path` source_generation through the local materializer inside the ordinary `api_agent` stage.
- Added focused contract/runtime tests.

## Verify
- Concrete Project Generation Benchmark: PASS.
- Focused concrete project tests: PASS.
- Agent planner/runtime/factory benchmarks: PASS.
- Full unittest discover: PASS, 715 tests, 4 skipped.
- Repo verification: PASS, `verify_repo.ps1 -Profile code`.

## Questions
- None.

## Demo
- Latest generated benchmark project: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778673353\project_output\local_issue_tracker_api`.
