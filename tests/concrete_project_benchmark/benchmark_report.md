# Concrete Project Generation Benchmark Report

## Summary
- concrete benchmark status: `passed`
- fixture: `tests/concrete_project_benchmark/fixtures/issue_tracker_api.json`
- generated project path: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1779094244\project_output\local_issue_tracker_api`
- run_dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1779094244`
- elapsed_seconds: `155.0`
- timeout_step: `(none)`

## Mainline Evidence
- selected ordinary entrypoint: `scripts/ctcp_orchestrate.py new-run + advance`
- command_count: `22`
- project_found: `True`
- source_project_root: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1779094244\project_output\local_issue_tracker_api`

## Attribution
- attribution_path: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1779094244\artifacts\generation_attribution.json`
- ordinary_mainline: `True`
- used_agent_project: `False`
- used_agent_scaffold: `False`
- used_local_agent_runtime: `False`
- used_local_materializer: `True`
- provider_authorship: `not_claimed`

## Validation Results
- not_agent_artifact: `passed`
- readme: `passed`
- source: `passed`
- tests: `passed`
- project_tests: `passed`
  - reason: `unittest passed`
- http_api: `passed`
  - routes: `GET /, GET /issues, GET /issues/{id}, GET /status, PATCH /issues/{id}/status, POST /issues, POST /issues/{id}/close`
  - POST /issues: `passed` status=`201`
  - GET /issues: `passed` status=`200`
  - GET /issues/{id}: `passed` status=`200`
  - PATCH /issues/{id}/status: `passed` status=`200`
  - POST /issues/{id}/close: `passed` status=`200`
- sqlite: `passed`
  - database file created: `True`
- shared_contracts: `passed`
- generation_attribution: `passed`

## Failed Assertions
- (none)

## Reproduction
- `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
