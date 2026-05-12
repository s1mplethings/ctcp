# Task - Incremental Source Generation Repair

## Queue Binding

- Queue Item: `ADHOC-20260512-incremental-source-generation-repair`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: repair ordinary CTCP concrete project source generation after diagnosing `source_generation` as an all-or-nothing long transaction.
- Current blocker: `scripts/ctcp_orchestrate.py advance --max-steps 1` can be killed by caller timeout while `source_generation` is still generating provider batches, leaving no `source_generation_report.json`, no `project_output/`, no progress, and no resume path.
- Explicitly forbidden paths:
  - no benchmark fixture simplification
  - no mock provider pretending to generate concrete source
  - no agent manifest/scaffold/project substitution
  - no provider call removal

## Task Truth Source

- task_purpose:
  - Make source generation incremental and checkpointed.
  - Persist completed source-generation batches under `artifacts/source_generation_batches/`.
  - Materialize files for each completed batch immediately.
  - Persist `artifacts/source_generation_state.json` and `artifacts/source_generation_partial_report.json`.
  - Allow a later `advance --run-dir ...` to resume pending batches without regenerating completed batches.
  - Surface source-generation progress in status output.
  - Add focused tests for checkpointing, partial materialization, resume, and adaptive batching.
- allowed_behavior_change:
  - Modify source-generation chunking/provider normalization paths.
  - Modify orchestrator status display to surface source-generation progress.
  - Extend the concrete project benchmark with recovery behavior without changing fixture difficulty.
  - Add regression tests and update task/report metadata.
- forbidden_goal_shift:
  - Do not mock provider output as if it were real source generation.
  - Do not hardcode the issue-tracker benchmark output.
  - Do not relax benchmark validators or fixtures.
  - Do not disable source-generation timeout behavior.
  - Do not use agent manifest/scaffold/project output as concrete project output.
- in_scope_modules:
  - `llm_core/providers/api_source_chunking.py`
  - `llm_core/providers/api_provider.py`
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_provider_source_files.py`
  - `tools/source_generation_progress.py`
  - `scripts/ctcp_orchestrate.py`
  - `tests/test_incremental_source_generation.py`
  - `tests/test_source_generation_resume.py`
  - `tests/test_source_generation_partial_materialization.py`
  - `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
  - `tests/concrete_project_benchmark/benchmark_report.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- out_of_scope_modules:
  - agent manifest/scaffold/project generator fixtures and validators
  - benchmark fixture inputs
  - provider credentials
  - unrelated CTCP project-generation behavior
- completion_evidence:
  - focused checkpoint/resume/materialization tests pass.
  - concrete benchmark records partial output and resume evidence.
  - canonical repo gates are recorded with first failure if any remains.

## Write Scope / Protection

- Allowed Write Paths:
  - `llm_core/providers/api_source_chunking.py`
  - `tools/providers/project_generation_source_helpers.py`
  - `tools/providers/project_generation_source_stage.py`
  - `tools/source_generation_progress.py`
  - `scripts/ctcp_orchestrate.py`
  - `tests/test_incremental_source_generation.py`
  - `tests/test_source_generation_resume.py`
  - `tests/test_source_generation_partial_materialization.py`
  - `tests/test_api_source_chunking.py`
  - `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`
  - `tests/concrete_project_benchmark/benchmark_report.md`
  - `tests/concrete_project_benchmark/generated/issue_tracker_api/**`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
- Protected Paths:
  - `.git`
  - provider credentials
  - benchmark fixtures
  - agent factory benchmark fixtures and validators
  - unrelated frozen kernels
- Frozen Kernels Touched: `true`
- Explicit Elevation Required: `true`
- Explicit Elevation Signal: `user requested source_generation repair`
- Forbidden Bypass:
  - no fake source report
  - no mock concrete project
  - no unsupported-as-passed
  - no timeout disabling
- Acceptance Checks:
  - `.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py`
  - `.venv\Scripts\python.exe -m unittest tests.test_incremental_source_generation -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_source_generation_resume -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_source_generation_partial_materialization -v`
  - `.venv\Scripts\python.exe -m unittest discover tests -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- The source-generation provider already produces a manifest and valid per-file batch JSON before timeout.
- Current writer only normalizes and materializes after all batches complete.
- The repair should preserve existing chunk generation and add durable batch checkpoints plus immediate materialization.

## Plan

1. Add source-generation state/checkpoint helpers.
2. Write each successful batch response to `artifacts/source_generation_batches/batch_XXX.json`.
3. Materialize batch file rows immediately without waiting for the final merged source report.
4. Persist partial state/report and make status display progress.
5. Add resume logic to skip completed batches and continue pending batches.
6. Add adaptive batch size defaults and focused tests.
7. Run concrete benchmark recovery and repo gates.

## Acceptance

- [x] Checkpoints are written per completed batch.
- [x] Partial materialized `project_output/` exists before final report.
- [x] Resume skips completed batches.
- [x] Status shows source-generation progress.
- [x] Final source report can still be generated.
- [x] Concrete project benchmark can recover after an interrupted source-generation run.
- [x] Repo verification recorded.

## Integration Check

- upstream: ordinary CTCP `new-run -> advance -> source_generation` concrete project flow.
- current_module: chunked API source-generation provider and source-stage normalization/materialization.
- downstream: `project_output/`, `artifacts/source_generation_report.json`, concrete benchmark, and delivery gates.
- source_of_truth: external run artifacts under the benchmark-created CTCP run directory.
- fallback: if final generated project quality fails, report that failure separately from source-generation infrastructure.
- acceptance_test: focused incremental source-generation tests, concrete benchmark recovery run, full unittest discovery, and canonical repo verify.
- forbidden_bypass: no fixture simplification, no provider mock, no generated output hardcoding, no timeout disabling.
- user_visible_effect: users can see partial source files and progress after an interrupted source-generation advance, then resume.

## Check/Contrast/Fix Loop Evidence

- check: ordinary source generation reached provider batch generation but previously lost all progress when the outer advance timed out.
- contrast: provider, planner graph, workflow selection, and chunk batches were not the failing layer; the all-or-nothing transaction and long-lived runtime probe were the repair target.
- fix: added per-batch checkpoints, immediate materialization, resumable state, partial report, progress status, adaptive batching, and runtime probe timeout handling.
- re-check: focused incremental tests pass; concrete benchmark now reaches real generated project validation instead of remaining unsupported due missing source output.

## Completion Criteria Evidence

- completion criteria evidence: connected + accumulated + consumed.
- connected: source-generation checkpoints are written by the same ordinary provider path used by `ctcp_orchestrate.py advance`.
- accumulated: state, batch checkpoints, partial report, materialized files, and benchmark summary are persisted as artifacts.
- consumed: resume reads completed batch checkpoints, skips completed batches, and continues pending generation.
- concrete outcome: benchmark still fails generated project quality checks, but it now has a real source directory and source-generation recovery evidence.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new issue-memory entry.
- reason: this task repairs local source-generation transaction behavior and records benchmark evidence; it does not introduce a reusable support/runtime incident pattern yet.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: the task required queue binding, scoped source-generation repair, gate execution, and auditable reporting.
- skillized: no; the repair is repo-local source-generation infrastructure, not a reusable external workflow.
- persona_lab_impact: none.
