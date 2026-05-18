# Task - Concrete Project Generalization Matrix

## Queue Binding

- Queue Item: `ADHOC-20260514-concrete-project-generalization-matrix`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: enter CTCP Phase 12 and verify ordinary concrete project generation generalizes beyond the Local Issue Tracker API fast path.
- The active risk is overfitting: one hardcoded issue tracker materializer may pass a single benchmark without proving concrete generation breadth.
- Agent runtime/planner/web lines are out of scope except for regression verification.

## Task Truth Source

- task_purpose:
  - Add a Concrete Project Generalization Matrix for three distinct ordinary generated projects: Todo REST API, Markdown Notes API, and Simple Auth API.
  - Each benchmark must validate generated tests, live runtime endpoints, persistence, provenance, and ordinary `new-run/status/advance` mainline.
- required_runtime_chain:
  - `new-run -> status -> advance -> analysis -> source_generation -> project_output -> generated tests -> runtime validation -> persistence validation`.
- allowed_behavior_change:
  - Add bounded concrete fast paths and deterministic local materializers for matrix project categories.
  - Add project-type-specific validators and focused tests.
  - Record provenance for each generated project under `artifacts/project_generation_provenance.json`.
- completion_evidence:
  - Matrix benchmark summary reports `matrix_total=3`, `passed=3`, `failed=0`, `unsupported=0`.
  - Existing concrete issue tracker benchmark remains passed.
  - Focused matrix tests, agent regressions, full unittest discover, script gates, and canonical repo verify pass.
- forbidden_goal_shift:
  - Do not use `agent-manifest`, `agent-scaffold`, or `agent-project` as a substitute.
  - Do not handwrite benchmark outputs outside ordinary project generation.
  - Do not mock HTTP, SQLite, file persistence, or provider success.
  - Do not weaken fixtures or skip analysis/source_generation.
  - Do not delete existing concrete or agent benchmarks.
- in_scope_modules:
  - `tools/providers/api_agent.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_materializers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_issue_tracker_fast_path.py`
  - `tools/providers/project_generation_matrix_fast_paths.py`
  - `tests/concrete_project_matrix/**`
  - `tests/test_concrete_project_matrix.py`
  - `tests/test_todo_api_generation.py`
  - `tests/test_notes_api_generation.py`
  - `tests/test_auth_api_generation.py`
  - `README.md`
  - `docs/project_generation.md`
  - `docs/concrete_project_pipeline.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260514-concrete-project-generalization-matrix.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260514-concrete-project-generalization-matrix.md`
- out_of_scope_modules:
  - agent runtime, planner, web tool, approval queue feature changes
  - real external API integration
  - benchmark fixture lowering
  - unrelated project generation domains

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/api_agent.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_generic_materializers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_issue_tracker_fast_path.py`
  - `tools/providers/project_generation_matrix_fast_paths.py`
  - `tests/concrete_project_matrix/`
  - `tests/test_concrete_project_matrix.py`
  - `tests/test_todo_api_generation.py`
  - `tests/test_notes_api_generation.py`
  - `tests/test_auth_api_generation.py`
  - `README.md`
  - `docs/project_generation.md`
  - `docs/concrete_project_pipeline.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260514-concrete-project-generalization-matrix.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260514-concrete-project-generalization-matrix.md`
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
  - no fake HTTP or persistence success
  - no benchmark fixture weakening
  - no source_generation skip
  - no benchmark runner hardcoded pass
- Acceptance Checks:
  - `.venv\Scripts\python.exe tests\concrete_project_matrix\run_matrix_benchmark.py`
  - `.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py`
  - `.venv\Scripts\python.exe -m unittest tests.test_concrete_project_matrix -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_todo_api_generation -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_notes_api_generation -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_auth_api_generation -v`
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

- Existing issue tracker benchmark proves one concrete fast path, but not category-level generalization.
- The matrix must exercise distinct data models, persistence patterns, runtime behavior, and validators.
- The fast path can be deterministic, but it must be inside ordinary output contract/source_generation and provenance-recorded.

## Plan

1. Add matrix fixtures and validators for Todo REST API, Markdown Notes API, and Simple Auth API.
2. Extend concrete fast path detection/defaults/materialization for the three categories without weakening issue tracker behavior.
3. Ensure ordinary source_generation emits `artifacts/project_generation_provenance.json` for each concrete generated project.
4. Add focused generation/runtime tests for each project category and the matrix runner.
5. Run matrix benchmark, existing concrete benchmark, agent regressions, full discover, script gates, and canonical verify.

## Acceptance

- [x] matrix benchmark runs all three fixtures.
- [x] Todo REST API benchmark passes.
- [x] Markdown Notes API benchmark passes.
- [x] Simple Auth API benchmark passes.
- [x] each project is not an agent scaffold.
- [x] each project supports `python app.py --host 127.0.0.1 --port <port>`.
- [x] generated tests pass for every project.
- [x] runtime endpoint validation passes for every project.
- [x] SQLite/file persistence validation passes as appropriate.
- [x] provenance is recorded for every project.
- [x] ordinary `new-run/status/advance` mainline is preserved.
- [x] existing Local Issue Tracker concrete benchmark remains pass.
- [x] agent planner/runtime/factory benchmarks remain pass.
- [x] unittest discover passes.
- [x] repo verification passes.

## Integration Check

- upstream: ordinary orchestrator `new-run/status/advance`, output_contract_freeze, source_generation, concrete fast path selection.
- current_module: concrete matrix fast path materializers and validators.
- downstream: generated tests, live HTTP probes, persistence checks, agent benchmark regression.
- source_of_truth: run artifacts, `analysis.md`, `source_generation_report.json`, `project_output`, generated tests, HTTP probes, persistence evidence, matrix summary.
- user_visible_effect: ordinary concrete project generation now demonstrates multiple runnable API categories with real tests, HTTP probes, persistence validation, and provenance evidence.
- fallback: non-matrix goals continue through existing project generation logic.
- acceptance_test: matrix benchmark and focused tests.
- forbidden_bypass: no agent runtime substitution, no fake runtime/database/filesystem success, no fixture weakening.

## Check/Contrast/Fix Loop Evidence

- check: `tests/concrete_project_matrix/run_matrix_benchmark.py` produced `matrix_total=3`, `passed=3`, `failed=0`, `unsupported=0`.
- contrast: the matrix validates three distinct project categories beyond the existing Local Issue Tracker fast path.
- fix: added matrix-specific materializers, validators, provenance emission, docs, and focused tests while preserving ordinary `new-run/status/advance`.

## Completion Criteria Evidence

- connected + accumulated + consumed.
- connected: ordinary output contract/source_generation now routes matrix categories to concrete generated projects.
- accumulated: matrix summary, benchmark report, generated tests, HTTP endpoint probes, SQLite/file evidence, and provenance are written.
- consumed: focused tests, concrete benchmark, agent benchmarks, full discover, script gates, and repo verify all passed.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new reusable issue-memory artifact needed; the failure/fix chain is captured in `meta/reports/LAST.md` and benchmark reports.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: this is a scoped repo workflow repair requiring task binding, implementation, verification, and report evidence.
- skillized: no.
- reason: this is concrete project generation capability work, not a reusable operator workflow.
