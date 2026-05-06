# Task - Source Stage Boundary Refactor

## Queue Binding

- Queue Item: `ADHOC-20260506-source-stage-boundary-refactor`
- Layer/Priority: `L1 / P1`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user asked to continue cleaning up the currently open `project_generation_source_stage.py`.
- Dependency check: `ADHOC-20260504-vn-generated-source-consistency-retest = done`
- Lane: Delivery Lane.
- Scope boundary: split low-coupling helper logic out of source stage while preserving source-generation behavior and public artifacts.

## Task Truth Source

- task_purpose:
  - Reduce `tools/providers/project_generation_source_stage.py` size and responsibility count.
  - Extract provider-authored source-file handling into its own module.
  - Extract high-quality extended evidence materialization into its own module.
- allowed_behavior_change:
  - No intended runtime behavior change.
  - Internal module boundaries may change.
- forbidden_goal_shift:
  - Do not change source-generation validation semantics.
  - Do not change provider prompt contracts.
  - Do not add local production templates or fallback materializers.
  - Do not combine with orchestrator/support-bot refactors.
- in_scope_modules:
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_provider_source_files.py`
  - `tools/providers/project_generation_extended_evidence.py`
  - focused source-generation tests and repo task/report metadata
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - support bot runtime
  - API endpoint/model behavior
  - generated project live API retests
- completion_evidence:
  - focused source-generation tests pass.
  - code-health changed-only check passes.
  - canonical verify passes or the first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_provider_source_files.py`
  - `tools/providers/project_generation_extended_evidence.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260506-source-stage-boundary-refactor.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260506-source-stage-boundary-refactor.md`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated run directories
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - Do not weaken generation validation or provenance gates.
  - Do not reintroduce production local project templates.
  - Do not skip the canonical verify entrypoint; record first failure if it fails.
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_source_stage.py tools\providers\project_generation_provider_source_files.py tools\providers\project_generation_extended_evidence.py`
  - `.venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v`
  - `.venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Entrypoint analysis: `tools/providers/project_generation_artifacts.py::normalize_source_generation()` calls `normalize_source_generation_stage()`.
- Downstream consumer analysis: orchestrator and manifest consumers rely on `artifacts/source_generation_report.json` fields staying stable.
- Source of truth: existing source-generation tests, canonical verify, and project-generation artifact contracts.
- Current break point / missing wiring: `project_generation_source_stage.py` still owns provider file parsing, provider source map writes, extended evidence generation, validation, and main stage orchestration.
- Repo-local search sufficient: yes.
- If no, external research artifact: none.

## Integration Check

- upstream: API/mock/local providers call project-generation artifact normalization.
- current_module: source-stage helper extraction.
- downstream: source generation report, project manifest, delivery gate, and tests consume unchanged outputs.
- source_of_truth: existing behavior and focused regression tests.
- fallback: if tests fail, revert only this extraction pattern by moving helpers back into source stage.
- acceptance_test:
  - focused source-generation py_compile/tests
  - workflow/module/code-health checks
  - canonical verify
- forbidden_bypass:
  - no validation relaxation
  - no template fallback
  - no source report field removal
- user_visible_effect: none expected; this is maintainability work.

## DoD Mapping

- [x] DoD-1: Provider-authored source file parsing and materialization are extracted from project_generation_source_stage.py without behavior changes.
- [x] DoD-2: High-quality extended evidence materialization is extracted from project_generation_source_stage.py without behavior changes.
- [x] DoD-3: Focused source-generation tests and code-health checks pass, with worktree cleanliness recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - `project_generation_source_stage.py` reduced from 995 lines to 648 lines.
  - `.venv\Scripts\python.exe -m py_compile ...` passed.
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` passed 11 tests.
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` passed 3 tests.
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` passed.
- contrast:
  - source-stage outputs should remain unchanged while file size/responsibility count drops.
  - existing tests directly imported private helpers from the old module.
- fix:
  - extracted provider source-file helpers and extended evidence helpers.
  - kept compatibility re-export for `_ensure_provider_package_init_files`.
  - left `normalize_source_generation_stage()` orchestration in place.

## Issue Memory Decision Evidence

- issue_memory_decision: no new issue-memory entry; this is behavior-preserving refactor work.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: source-stage imports and calls extracted modules.
- accumulated: test and verify evidence is recorded in `meta/reports/LAST.md`.
- consumed: focused tests and canonical verify consume the refactored source-generation path.

## Plan

1. Bind task and allowed write scope.
2. Extract provider source-file helper logic into a new module.
3. Extract high-quality extended evidence helper logic into a new module.
4. Update source stage imports and remove extracted helper bodies.
5. Run focused source-generation tests and code-health checks.
6. Run canonical verify or record first failure.
7. Update report/task archive and leave worktree clean or explicitly report dirty state.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed.
- [x] Provider source helper extracted.
- [x] Extended evidence helper extracted.
- [x] Focused tests pass.
- [x] Code-health check passes.
- [x] Canonical verify pass or first failure recorded.
- [x] Demo report updated: `meta/reports/LAST.md`.

## Notes / Decisions

- Default choices made: extract helper modules only; leave main orchestration untouched.
- Alternatives considered: splitting `normalize_source_generation_stage()` itself was deferred because it has higher behavioral risk.
- Any contract exception reference: none.
- Issue memory decision: no new issue-memory entry.
- Skill decision: skillized: no, because this is a one-off source-stage boundary refactor using existing `ctcp-workflow`.
- persona_lab_impact: none.

## Results

- Files changed:
  - `tools/providers/project_generation_source_stage.py`
  - `tools/providers/project_generation_provider_source_files.py`
  - `tools/providers/project_generation_extended_evidence.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260506-source-stage-boundary-refactor.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260506-source-stage-boundary-refactor.md`
- Verification summary:
  - focused source-generation tests passed.
  - code-health changed-only check passed.
  - canonical verify passed with profile `code`, ownership `task-owned`, lite replay 15 passed / 0 failed, Python tests 517 OK / 4 skipped.
- Queue status update suggestion: `done`.

## Closure

- closed_report: `meta/reports/archive/20260506-source-stage-boundary-refactor.md`
- canonical_verify: passed on 2026-05-06 with `CTCP_FORCE_PROVIDER` cleared and `CTCP_RUNS_ROOT` set to `%TEMP%\ctcp_runs`.
