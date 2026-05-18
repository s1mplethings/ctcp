# Task - Full-Stack Kanban Expansion With Local Cleanup

## Queue Binding

- Queue Item: `ADHOC-20260514-full-stack-kanban-expansion-cleanup`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: enter CTCP Phase 14 and expand ordinary concrete/full-stack project generation with `local_kanban_board_app`.
- Existing Phase 13 full-stack benchmark passes for `local_task_board_app`.
- This task must add functionality and small local structure cleanup, not a broad refactor.

## Task Truth Source

- task_purpose:
  - Add a Full-Stack Kanban App benchmark for ordinary generated `local_kanban_board_app`.
  - Add bounded shared helpers/registry for fast path dispatch, provenance, and template writing.
- required_runtime_chain:
  - `new-run -> status -> advance -> analysis -> source_generation -> project_output -> generated tests -> frontend HTTP validation -> API validation -> SQLite validation`.
- allowed_behavior_change:
  - Add a bounded Kanban full-stack concrete fast path with static frontend, local HTTP API, SQLite persistence, generated tests, and provenance.
  - Add local helper modules for fast path registry/provenance/template writing and route existing relevant fast paths through them where scoped.
  - Extend full-stack benchmark runner to validate both task board and kanban cases.
- completion_evidence:
  - Full-stack benchmark summary reports `local_task_board_app` and `local_kanban_board_app` passed.
  - Existing concrete matrix and concrete issue tracker benchmarks remain passed.
  - Agent planner/runtime/factory benchmarks remain passed.
  - Full unittest discover, script gates, and canonical repo verify pass.
- forbidden_goal_shift:
  - Do not use `agent-manifest`, `agent-scaffold`, or `agent-project` as a substitute.
  - Do not mock HTTP, frontend, SQLite, or provider success.
  - Do not weaken fixtures or skip analysis/source_generation.
  - Do not delete existing concrete or agent benchmarks.
  - Do not rewrite orchestrator or migrate unrelated modules.
- in_scope_modules:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_materializers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_validation.py`
  - `tools/providers/project_generation_concrete_validation.py`
  - `tools/providers/project_generation_fast_path_materializers.py`
  - `tools/providers/project_generation_full_stack_fast_path.py`
  - `tools/providers/project_generation_fast_path_registry.py`
  - `tools/providers/project_generation_kanban_fast_path.py`
  - `tools/providers/project_generation_template_writer.py`
  - `tools/providers/project_generation_provenance_writer.py`
  - `tests/full_stack_app_benchmark/**`
  - `tests/test_full_stack_app_generation.py`
  - `tests/test_kanban_app_generation.py`
  - `tests/test_project_generation_fast_path_registry.py`
  - `tests/test_project_generation_template_writer.py`
  - `README.md`
  - `docs/project_generation.md`
  - `docs/concrete_project_pipeline.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260514-full-stack-kanban-expansion-cleanup.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260514-full-stack-kanban-expansion-cleanup.md`
- out_of_scope_modules:
  - agent runtime, planner, web tool, approval queue feature changes
  - real external API integration
  - benchmark fixture lowering
  - unrelated fast paths beyond registry dispatch metadata
  - orchestrator refactors

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_materializers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_validation.py`
  - `tools/providers/project_generation_concrete_validation.py`
  - `tools/providers/project_generation_fast_path_materializers.py`
  - `tools/providers/project_generation_full_stack_fast_path.py`
  - `tools/providers/project_generation_fast_path_registry.py`
  - `tools/providers/project_generation_kanban_fast_path.py`
  - `tools/providers/project_generation_template_writer.py`
  - `tools/providers/project_generation_provenance_writer.py`
  - `tests/full_stack_app_benchmark/`
  - `tests/test_full_stack_app_generation.py`
  - `tests/test_kanban_app_generation.py`
  - `tests/test_project_generation_fast_path_registry.py`
  - `tests/test_project_generation_template_writer.py`
  - `README.md`
  - `docs/project_generation.md`
  - `docs/concrete_project_pipeline.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260514-full-stack-kanban-expansion-cleanup.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260514-full-stack-kanban-expansion-cleanup.md`
- Protected Paths:
  - `.git`
  - agent runtime/planner/web implementation files unless benchmark output changes during regression
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
  - no broad orchestrator rewrite
- Acceptance Checks:
  - `.venv\Scripts\python.exe tests\full_stack_app_benchmark\run_full_stack_benchmark.py`
  - `.venv\Scripts\python.exe tests\concrete_project_matrix\run_matrix_benchmark.py`
  - `.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py`
  - `.venv\Scripts\python.exe -m unittest tests.test_kanban_app_generation -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_project_generation_fast_path_registry -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_project_generation_template_writer -v`
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

- Current full-stack benchmark proves one static frontend + API + SQLite app, but not a richer multi-model interaction like Kanban card movement.
- The cleanup must stay local to project generation fast paths and benchmark validators.
- The Kanban benchmark must validate generated tests, live frontend assets, backend endpoints, SQLite evidence, and no agent scaffold artifacts.

## Integration Check

- upstream: ordinary orchestrator `new-run/status/advance`, output_contract_freeze, source_generation, concrete fast path selection.
- current_module: fast path registry/helpers, full-stack materializer, full-stack benchmark validator.
- downstream: generated tests, live frontend HTTP probes, API probes, SQLite persistence checks, concrete and agent regressions.
- source_of_truth: run artifacts, `analysis.md`, `source_generation_report.json`, `project_output`, generated tests, HTTP probes, persistence evidence, benchmark summary.
- user_visible_effect: ordinary concrete project generation demonstrates a richer browser-facing Kanban MVP.
- fallback: non-Kanban goals continue through existing project generation logic.
- acceptance_test: full-stack benchmark, Kanban focused tests, registry/helper tests, and listed regressions.
- forbidden_bypass: no agent runtime substitution, no fake frontend/API/database success, no fixture weakening.

## Plan

1. Add small shared provenance/template writer helpers and a fast path registry.
2. Add `local_kanban_board_app` full-stack templates with boards, cards, columns, movement, static frontend, generated tests, and provenance.
3. Extend full-stack benchmark fixture/runner to run both task board and Kanban through ordinary `new-run/status/advance`.
4. Add focused Kanban, registry, and helper tests.
5. Update docs and run the required benchmark/regression/verify commands.

## Acceptance

- [x] full-stack benchmark runs ordinary project generation for `local_task_board_app` and `local_kanban_board_app`.
- [x] generated Kanban project is `project_output/local_kanban_board_app`.
- [x] generated Kanban project is not an agent scaffold.
- [x] generated Kanban app supports `python app.py --host 127.0.0.1 --port <port>`.
- [x] static HTML/CSS/JS are served over HTTP.
- [x] generated tests pass.
- [x] API validation passes for board/card create/list/move/update/delete flow.
- [x] SQLite persistence validation passes.
- [x] provenance is recorded through shared helper.
- [x] fast path registry dispatches issue/todo/notes/auth/fullstack/kanban.
- [x] ordinary `new-run/status/advance` mainline is preserved.
- [x] old full-stack, concrete matrix, and concrete benchmark remain pass.
- [x] agent planner/runtime/factory benchmarks remain pass.
- [x] unittest discover passes.
- [x] repo verification passes.

## Check/Contrast/Fix Loop Evidence

- check: full-stack benchmark `2/2`, concrete matrix `3/3`, concrete issue tracker PASS, agent planner/runtime/factory PASS, `unittest discover` PASS, and `verify_repo.ps1 -Profile code` PASS.
- contrast: Phase 13 full-stack benchmark passing does not prove multi-column card movement or shared fast path structure.
- fix: added bounded Kanban fast path plus local helper split for registry, materialization dispatch, Kanban templates, provenance, template writing, and concrete validation.

## Completion Criteria Evidence

- connected + accumulated + consumed.
- connected: ordinary `new-run/status/advance` drives both full-stack benchmark cases into `analysis`, `source_generation`, `project_output`, generated tests, HTTP probes, and SQLite probes.
- accumulated: benchmark reports and summaries capture project status, frontend validation, backend runtime validation, SQLite validation, and structure cleanup helpers.
- consumed: final gates consume `meta/tasks/CURRENT.md`, `meta/reports/LAST.md`, benchmark summaries, module protection scope, code health, and repo verify.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new issue-memory rule was needed; first failure was report evidence/code-health growth during implementation and was resolved before final verify.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: scoped repo workflow change requiring task binding, implementation, verification, and report evidence.
- skillized: no.
- reason: this task adds local benchmark/project-generation support, not a reusable operator workflow.
