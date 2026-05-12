# Concrete Project Generation Benchmark Report

## Summary
- concrete benchmark status: `failed`
- fixture: `tests/concrete_project_benchmark/fixtures/issue_tracker_api.json`
- generated project path: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\project_output\generate-a-real-runnable-local-http-api-project-`
- run_dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
- elapsed_seconds: `380.279`
- timeout_step: `resume_advance`

## Entrypoint Discovery
- selected ordinary entrypoint: `scripts/ctcp_orchestrate.py new-run + advance`
- ordinary entrypoints found: `new-run, status, advance, scaffold, scaffold-pointcloud`
- excluded agent modes found: `agent-manifest, agent-project, agent-scaffold`

## Commands Executed
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py new-run --goal Generate a real runnable local HTTP API project for tracking issues. The project must not be an agent manifest, agent scaffold, or agent dry-run. It must be a concrete software project with README, source code, automated tests, and SQLite persistence. Required endpoints: POST /issues, GET /issues, GET /issues/{id}, PATCH /issues/{id}/status, POST /issues/{id}/close. Use SQLite persistence. Valid issue statuses: open, in_progress, closed. Generate the concrete project files, tests, README, runnable local HTTP server, and delivery package. --run-id concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `[ctcp_orchestrate] run_dir=C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `rate] run_status=running
[ctcp_orchestrate] iterations=0/3 (source=guardrails.md)
[ctcp_orchestrate] blocked: waiting for analysis.md
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/analysis.md
[ctcp_orchestrate] reason=waiting for analysis.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `s.md)
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=resolve_find_local
[ctcp_orchestrate] owner=Local Orchestrator
[ctcp_orchestrate] path=artifacts/find_result.json
[ctcp_orchestrate] reason=run local resolver`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `s.md)
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=resolve_find_local
[ctcp_orchestrate] owner=Local Orchestrator
[ctcp_orchestrate] path=artifacts/find_result.json
[ctcp_orchestrate] reason=run local resolver`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `uest.json
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/file_request.json
[ctcp_orchestrate] reason=waiting for file_request.json`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `uest.json
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/file_request.json
[ctcp_orchestrate] reason=waiting for file_request.json`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `ck.json
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Local Librarian
[ctcp_orchestrate] path=artifacts/context_pack.json
[ctcp_orchestrate] reason=waiting for context_pack.json`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `ck.json
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Local Librarian
[ctcp_orchestrate] path=artifacts/context_pack.json
[ctcp_orchestrate] reason=waiting for context_pack.json`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `for PLAN_draft.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/PLAN_draft.md
[ctcp_orchestrate] reason=waiting for PLAN_draft.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `for PLAN_draft.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/PLAN_draft.md
[ctcp_orchestrate] reason=waiting for PLAN_draft.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `ct.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Contract Guardian
[ctcp_orchestrate] path=reviews/review_contract.md
[ctcp_orchestrate] reason=waiting for review_contract.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `ct.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Contract Guardian
[ctcp_orchestrate] path=reviews/review_contract.md
[ctcp_orchestrate] reason=waiting for review_contract.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: ` review_cost.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Cost Controller
[ctcp_orchestrate] path=reviews/review_cost.md
[ctcp_orchestrate] reason=waiting for review_cost.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: ` review_cost.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Cost Controller
[ctcp_orchestrate] path=reviews/review_cost.md
[ctcp_orchestrate] reason=waiting for review_cost.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `ing for signed PLAN.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/PLAN.md
[ctcp_orchestrate] reason=waiting for signed PLAN.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `ing for signed PLAN.md
[ctcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/PLAN.md
[ctcp_orchestrate] reason=waiting for signed PLAN.md`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/output_contract_freeze.json
[ctcp_orchestrate] reason=waiting for output_contract_freeze`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/output_contract_freeze.json
[ctcp_orchestrate] reason=waiting for output_contract_freeze`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `tcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/source_generation_report.json
[ctcp_orchestrate] reason=waiting for source_generation`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `tcp_orchestrate] analysis_progress status=completed last_event=artifact_write_completed duration_seconds=8.47
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/source_generation_report.json
[ctcp_orchestrate] reason=waiting for source_generation`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `0`
  - stdout_tail: `[ctcp_orchestrate] blocked: provider reported executed but target missing: artifacts/source_generation_report.json`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py status --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845`
  - exit_code: `0`
  - stdout_tail: `_progress=completed_batches=1/6, generated_files=3, materialized_files=3, remaining_batches=5, status=running
[ctcp_orchestrate] next=blocked
[ctcp_orchestrate] owner=Chair/Planner
[ctcp_orchestrate] path=artifacts/source_generation_report.json
[ctcp_orchestrate] reason=waiting for source_generation`
  - stderr_tail: ``
- command: `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe D:\.c_projects\adc\ctcp\scripts\ctcp_orchestrate.py advance --run-dir C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845 --max-steps 1`
  - exit_code: `124`
  - stdout_tail: ``
  - stderr_tail: ``

## Step Timings
- discovery: `passed` duration=`0.348`
- new_run: `passed` duration=`0.617`
- status_before_generation: `passed` duration=`0.375`
- advance_1: `passed` duration=`9.404`
- status_after_advance: `passed` duration=`0.334`
- advance_2: `passed` duration=`2.924`
- status_after_advance: `passed` duration=`0.348`
- advance_3: `passed` duration=`13.222`
- status_after_advance: `passed` duration=`0.343`
- advance_4: `passed` duration=`0.739`
- status_after_advance: `passed` duration=`0.365`
- advance_5: `passed` duration=`29.645`
- status_after_advance: `passed` duration=`0.35`
- advance_6: `passed` duration=`13.622`
- status_after_advance: `passed` duration=`0.365`
- advance_7: `passed` duration=`12.614`
- status_after_advance: `passed` duration=`0.382`
- advance_8: `passed` duration=`31.26`
- status_after_advance: `passed` duration=`0.351`
- advance_9: `passed` duration=`15.99`
- status_after_advance: `passed` duration=`0.421`
- interrupted_advance: `passed` duration=`65.546`
- status_after_advance: `passed` duration=`0.423`
- resume_advance: `timeout` duration=`180.036`
- source_generation: `timeout` duration=`246.011`
- generated_project_discovery: `passed` duration=`0.017`
- convergence_extraction: `passed` duration=`0.031`
  - drift_count: `0`
  - graph_hash: `b82efc098fb337989feccff3fab052a2da2f770f8a358e838f7d7bb0604e035f`
- convergence_validation: `passed` duration=`0.0`
  - drift_count: `0`
  - graph_hash: `b82efc098fb337989feccff3fab052a2da2f770f8a358e838f7d7bb0604e035f`
- convergence_repair: `passed` duration=`0.0`
  - drift_count: `0`
  - graph_hash: `b82efc098fb337989feccff3fab052a2da2f770f8a358e838f7d7bb0604e035f`
- generated_project_tests: `failed` duration=`0.002`
- HTTP probe: `failed` duration=`0.001`
- SQLite validation: `passed` duration=`0.113`
- report_write: `passed` duration=`0.011`

## Analysis Progress
- target: `artifacts/analysis.md`
- status: `completed`
- last_event: `artifact_write_completed`
- timeout: `True`
- error: `(none)`
- prompt_path: `outbox/AGENT_PROMPT_chair_plan_draft.md`
- provider: `api_agent`
- provider_model: `gpt-4.1-mini`
- provider_timeout_seconds: `90`
- analysis_profile: `fast`
- prompt_char_count: `2232`
- prompt_estimated_tokens: `558`
- max_output_tokens: `900`
- output_contract: `ype
One short paragraph naming the concrete software project type.

## Required Files
Bullets for the minimum files/directories the later source_generation step must create.

## Runtime
Bullets for entrypoint, HTTP/server behavior, CLI args if needed, and local run command expectations.

## Data Model
Bullets for persisted entities, fields, enums/status values, and SQLite expectations.

## Acceptance Checks
Bullets for generated tests, HTTP probes, SQLite validation, and README/run instructions.`
- raw_exists: `True` path=`artifacts/analysis.raw.txt`
- partial_exists: `False` path=`(none)`
- resume_possible: `False`

## Source Generation Recovery
- intentional interrupt: `True`
- resume attempted: `True`
- partial project_output seen: `True`
- completed batches after interrupt: `1`
- completed batches after resume: `1`

## Generated Project Discovery
- project_found: `True`
- source_project_root: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\project_output\generate-a-real-runnable-local-http-api-project-`
- project_path_pointer: `D:\.c_projects\adc\ctcp\tests\concrete_project_benchmark\generated\issue_tracker_api\project_path.txt`
- candidates:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\project_output\generate-a-real-runnable-local-http-api-project-` score=`5`

## Validation Results
- not_agent_artifact: `passed`
- readme: `passed`
- source: `failed`
- tests: `failed`
- project_tests: `failed`
  - reason: `no generated test files found`
- http_api: `failed`
  - route registry: ``
  - runtime entrypoint: ``
  - runtime supported CLI args: ``
  - missing_required_route: `GET /issues`
  - missing_required_route: `GET /issues/{id}`
  - missing_required_route: `PATCH /issues/{id}/status`
  - missing_required_route: `POST /issues`
  - missing_required_route: `POST /issues/{id}/close`
- sqlite: `passed`
  - sqlite3 usage detected: `True`
  - database file created: `False`
- shared_contracts: `passed`
  - contract_graph: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\artifacts\contract_graph.json`
  - graph_hash: `b82efc098fb337989feccff3fab052a2da2f770f8a358e838f7d7bb0604e035f`
  - generated_symbols: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\artifacts\generated_symbols.json`
  - generated_routes: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\artifacts\generated_routes.json`
  - runtime_contract: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\artifacts\runtime_contract.json`
  - reconciliation_report: `C:\Users\sunom\AppData\Local\Temp\ctcp_concrete_project_benchmark_runs\ctcp\concrete-issue-tracker-1778591845\artifacts\reconciliation_report.json`
  - reconciliation_status: `passed`
  - converged: `True`
  - typed_issue_count: `0`
  - provider_call_count: `0`
  - stopped_reason: `converged`
  - max_passes: `3`
  - max_wall_clock_seconds: `120.0`
  - cache_hits: `0`
  - cache_misses: `0`

## Failed Assertions
- source check failed
- tests check failed
- project_tests check failed
- http_api check failed

## Unsupported Reasons
- (none)

## Reproduction
- `D:\.c_projects\adc\ctcp\.venv\Scripts\python.exe tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
