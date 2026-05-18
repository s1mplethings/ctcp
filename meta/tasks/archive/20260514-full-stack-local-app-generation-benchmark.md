# Task - Full-Stack Local App Generation Benchmark

## Queue Binding

- Queue Item: `ADHOC-20260514-full-stack-local-app-generation-benchmark`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: enter CTCP Phase 13 and verify ordinary project generation can generate a small full-stack local application.
- The user message is truncated after `small full-stack local application`; bounded default for this task is `local_task_board_app`.
- Agent runtime/planner/web lines are out of scope except for regression verification.

## Task Truth Source

- task_purpose:
  - Add a Full-Stack Local App Generation Benchmark for an ordinary generated `local_task_board_app`.
  - The generated project must include static frontend assets, local HTTP API, SQLite persistence, generated tests, runtime validation, provenance, and ordinary `new-run/status/advance` mainline evidence.
- required_runtime_chain:
  - `new-run -> status -> advance -> analysis -> source_generation -> project_output -> generated tests -> frontend HTTP validation -> API validation -> SQLite validation`.
- allowed_behavior_change:
  - Add a bounded full-stack concrete fast path and deterministic local materializer for a local task board app.
  - Add benchmark-specific validators and focused tests.
  - Record provenance under `artifacts/project_generation_provenance.json`.
- completion_evidence:
  - Full-stack benchmark summary reports `status=passed`.
  - Existing concrete matrix and concrete issue tracker benchmarks remain passed.
  - Agent regressions, full unittest discover, script gates, and canonical repo verify pass.
- forbidden_goal_shift:
  - Do not use `agent-manifest`, `agent-scaffold`, or `agent-project` as a substitute.
  - Do not mock HTTP, frontend, SQLite, or provider success.
  - Do not weaken fixtures or skip analysis/source_generation.
  - Do not delete existing concrete or agent benchmarks.
- in_scope_modules:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_materializers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_full_stack_fast_path.py`
  - `tests/full_stack_app_benchmark/**`
  - `tests/test_full_stack_app_generation.py`
  - `README.md`
  - `docs/project_generation.md`
  - `docs/concrete_project_pipeline.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260514-full-stack-local-app-generation-benchmark.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260514-full-stack-local-app-generation-benchmark.md`
- out_of_scope_modules:
  - agent runtime, planner, web tool, approval queue feature changes
  - real external API integration
  - benchmark fixture lowering
  - unrelated project generation domains

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_materializers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_full_stack_fast_path.py`
  - `tests/full_stack_app_benchmark/`
  - `tests/test_full_stack_app_generation.py`
  - `README.md`
  - `docs/project_generation.md`
  - `docs/concrete_project_pipeline.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260514-full-stack-local-app-generation-benchmark.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260514-full-stack-local-app-generation-benchmark.md`
- Protected Paths:
  - `.git`
  - agent runtime/planner/web implementation files unless only benchmark output changes during regression
  - benchmark fixture lowering
  - provider credentials
  - real external API clients
  - unrelated frozen kernels
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no agent-project substitution
  - no fake HTTP/frontend/database success
  - no benchmark fixture weakening
  - no source_generation skip
  - no benchmark runner hardcoded pass
- Acceptance Checks:
  - `.venv\Scripts\python.exe tests\full_stack_app_benchmark\run_full_stack_benchmark.py`
  - `.venv\Scripts\python.exe -m unittest tests.test_full_stack_app_generation -v`
  - `.venv\Scripts\python.exe tests\concrete_project_matrix\run_matrix_benchmark.py`
  - `.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py`
  - `.venv\Scripts\python.exe tests\agent_planner_benchmark\run_planner_benchmark.py`
  - `.venv\Scripts\python.exe tests\agent_runtime_benchmark\run_runtime_benchmark.py`
  - `.venv\Scripts\python.exe tests\agent_factory_benchmark\run_benchmark.py`
  - `.venv\Scripts\python.exe -m unittest discover tests -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Current concrete matrix proves backend-style projects but not static frontend + backend integration.
- The benchmark must validate HTML/CSS/JS over HTTP, API behavior, generated tests, persistence, and provenance.
- The fast path can be deterministic, but it must be inside ordinary output contract/source_generation.

## Integration Check

- upstream: ordinary orchestrator `new-run/status/advance`, output_contract_freeze, source_generation, concrete fast path selection.
- current_module: full-stack materializer and full-stack benchmark validator.
- downstream: generated tests, live frontend HTTP probes, API probes, SQLite persistence checks, agent/concrete benchmark regression.
- source_of_truth: run artifacts, `analysis.md`, `source_generation_report.json`, `project_output`, generated tests, HTTP probes, persistence evidence, benchmark summary.
- user_visible_effect: ordinary concrete project generation demonstrates a browser-usable local app rather than backend-only APIs.
- fallback: non-full-stack goals continue through existing project generation logic.
- acceptance_test: full-stack benchmark and focused full-stack generation tests.
- forbidden_bypass: no agent runtime substitution, no fake frontend/API/database success, no fixture weakening.

## Plan

1. Add a bounded `local_task_board_app` full-stack fast path with static frontend, API, SQLite store, generated tests, and provenance.
2. Add a full-stack benchmark fixture/runner that drives ordinary `new-run/status/advance` and validates generated project runtime.
3. Add focused tests proving full-stack detection, generated frontend assets, app startup, generated tests, API flow, and SQLite persistence.
4. Update docs to describe full-stack local app benchmark coverage.
5. Run full-stack benchmark, concrete regressions, agent regressions, full discover, script gates, and canonical verify.

## Acceptance

- [x] full-stack benchmark runs ordinary project generation.
- [x] generated project is `project_output/local_task_board_app`.
- [x] generated project is not an agent scaffold.
- [x] generated app supports `python app.py --host 127.0.0.1 --port <port>`.
- [x] static HTML/CSS/JS are served over HTTP.
- [x] generated tests pass.
- [x] API validation passes for create/list/update/delete task flow.
- [x] SQLite persistence validation passes.
- [x] provenance is recorded.
- [x] ordinary `new-run/status/advance` mainline is preserved.
- [x] existing concrete matrix and concrete benchmark remain pass.
- [x] agent planner/runtime/factory benchmarks remain pass.
- [x] unittest discover passes.
- [x] repo verification passes.

## Check/Contrast/Fix Loop Evidence

- check: full-stack benchmark `passed`; generated source_generation report status `pass`; focused unittest `tests.test_full_stack_app_generation` passed; concrete matrix `3/3` passed.
- contrast: backend-style matrix passing alone does not prove browser-facing full-stack output.
- fix: added `local_task_board_app` full-stack fast path, generated static frontend/API/SQLite project, service export path, runtime benchmark, and focused tests.

## Completion Criteria Evidence

- connected + accumulated + consumed.
- connected: ordinary orchestrator `new-run/status/advance` produced `analysis`, `output_contract_freeze`, `source_generation`, and `project_output/local_task_board_app`.
- accumulated: `tests/full_stack_app_benchmark/generated/benchmark_summary.json` records commands, project path, generated tests, HTTP probes, SQLite validation, and provenance.
- consumed: full-stack benchmark, focused unittest, concrete matrix, concrete benchmark, agent planner/runtime/factory benchmarks, and unittest discover consumed the generated outputs and regression surfaces.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new reusable failure pattern to add yet; observed and fixed local validation mismatches for README sections, web-service smoke export, and service test naming inside the bounded Phase 13 task.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: this is a scoped repo workflow repair requiring task binding, implementation, verification, and report evidence.
- skillized: no.
- reason: this benchmark is local to concrete project generation and not a reusable operator workflow yet.
