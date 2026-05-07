# Task - Generated Project Runnable Source Guard

## Queue Binding

- Queue Item: `ADHOC-20260507-generated-project-runnable-source-guard`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: a live API run for a phone-to-PC voice-assistant project generated provider-authored source, but source-generation validation blocked because the generated project was not runnable in the verifier environment.
- Dependency check: `ADHOC-20260504-vn-generated-source-consistency-retest = done`; `ADHOC-20260506-source-stage-boundary-refactor = done`.
- Lane: Delivery Lane.
- Scope boundary: improve source-generation prompt and failure feedback so future API retries repair runnable-project defects instead of repeating undeclared dependency and README/interface mistakes.

## Task Truth Source

- task_purpose:
  - Generated projects must run under the current validation environment without relying on undeclared or uninstalled external packages.
  - Source-generation retries must receive exact README, runtime-probe, external-dependency, interface, and UX blocker feedback.
  - Provider-authored source remains required; do not reintroduce local production templates.
- allowed_behavior_change:
  - Source-generation API prompt constraints may become stricter.
  - Previous-failure prompt feedback may include more blocker details.
- forbidden_goal_shift:
  - Do not install dependencies as part of CTCP validation to mask broken generated projects.
  - Do not relax generic_validation/readme/ux gates.
  - Do not add local deterministic project templates or materializer fallbacks.
  - Do not change Telegram/support bot runtime behavior in this task.
- in_scope_modules:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_api_agent_templates.py`
  - `issue_memory/modifications.jsonl`
  - repo task/report metadata
- out_of_scope_modules:
  - `scripts/ctcp_orchestrate.py`
  - `tools/providers/project_generation_source_stage.py` orchestration behavior
  - generated run output files
  - provider credentials, API endpoint, model selection
- completion_evidence:
  - focused source-generation prompt tests pass.
  - source-generation artifact tests still pass.
  - workflow/code-health/canonical verify pass or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_api_agent_templates.py`
  - `issue_memory/modifications.jsonl`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260507-generated-project-runnable-source-guard.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260507-generated-project-runnable-source-guard.md`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated run directories
  - local API/proxy secrets
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - Do not weaken project-generation validation.
  - Do not mark source generation pass when runtime probes fail.
  - Do not hide API-generated source defects behind dependency installation.
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tests\test_api_agent_templates.py`
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v`
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Entrypoint analysis: `ctcp_adapters.ctcp_artifact_normalizers._render_prompt()` appends `render_source_generation_payload_requirements()` for `chair/source_generation`.
- Downstream consumer analysis: `llm_core.providers.api_source_chunking` reuses the same prompt text for manifest and file-content batches, so prompt changes affect live API source generation without changing materialization logic.
- Source of truth: live run `voice-assistant-phone-pc-smoke-20260507` showed `api_agent` source generation with `fallback_count=0`, then blocked at `generic_validation.passed=false`.
- Current break point / missing wiring:
  - Prompt says "standard library first" but does not state that runtime probes do not install project dependencies.
  - Previous-failure feedback includes startup/export stderr and interface mismatch but omits README missing sections and external dependency blockers as explicit repair items.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: API source-generation prompt renderer.
- current_module: source-generation requirements and previous-failure feedback.
- downstream: chunked API source generation, provider-authored file payload, local source materialization, generic/readme/ux validation.
- source_of_truth: generated-project validation report and focused tests.
- fallback: if prompt tests fail, narrow the wording to the exact assertions without touching validation gates.
- acceptance_test:
  - source-generation prompt tests
  - source-generation artifact tests
  - canonical verify code profile
- forbidden_bypass:
  - no validation relaxation
  - no local template fallback
  - no dependency installation bypass
- user_visible_effect: future generated project attempts should fail less often on undeclared dependencies and incomplete README/UX repair loops.

## DoD Mapping

- [x] DoD-1: Source-generation prompt states generated projects must be runnable by verifier probes without uninstalled external packages.
- [x] DoD-2: Previous-failure prompt feedback includes external dependency, README quality, and UX blocker details.
- [x] DoD-3: Focused tests and canonical verify pass or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - live run blocked at `generic_validation.passed must be true`.
  - startup/export probes failed with `ModuleNotFoundError: No module named 'flask'`.
  - README quality missed required sections.
  - interface contract mismatch listed undeclared actual symbols.
- contrast:
  - provider ledger showed API source generation did happen, so this is generated-source quality, not local-template fallback.
  - current prompt already includes import consistency guidance, but not verifier-environment dependency constraints or README feedback in retry context.
- fix:
  - strengthened source-generation prompt requirements for dependency-free verifier paths.
  - added previous-failure feedback for dependency errors, README missing sections, README reasons, and UX blockers.
  - kept tests within the 1000-line code-health growth guard.

## Issue Memory Decision Evidence

- issue_memory_decision: capture required because generated-source validation failure has recurred across live API project-generation attempts and is user-visible as "generated but not deliverable".

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: source-generation prompt renderer is reached from API source-generation dispatch.
- accumulated: issue memory and report record live failure class and verification commands.
- consumed: focused prompt tests assert the new constraints are included.

## Plan

1. Bind task and allowed write scope.
2. Strengthen source-generation prompt requirements for verifier-runnable, dependency-light generated projects.
3. Add previous-failure feedback for README missing sections, dependency errors, and UX blockers.
4. Add/update focused prompt tests.
5. Run focused source-generation tests and code-health checks.
6. Run canonical verify or record first failure.
7. Archive task/report and leave worktree clean or explicitly report dirty state.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed.
- [x] Prompt/runtime repair guidance updated.
- [x] Focused tests pass.
- [x] Code-health check passes.
- [x] Canonical verify pass or first failure recorded.
- [x] Demo report updated: `meta/reports/LAST.md`.

## Notes / Decisions

- Default choices made: fix the source-generation prompt and feedback loop first, because live evidence shows API source was produced but repeatedly failed validation.
- Alternatives considered: installing Flask during validation was rejected because it hides generated-project portability defects and does not solve future undeclared dependency drift.
- Any contract exception reference: none.
- Issue memory decision: required, see above.
- Skill decision: skillized: no, because this is a bounded source-generation quality repair using existing `ctcp-workflow`.
- persona_lab_impact: none.

## Results

- Files changed:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_api_agent_templates.py`
  - `issue_memory/modifications.jsonl`
  - `artifacts/PLAN.md`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260507-generated-project-runnable-source-guard.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260507-generated-project-runnable-source-guard.md`
- Verification summary:
  - focused source-generation prompt tests passed.
  - focused source-generation artifact tests passed.
  - workflow/module/patch/code-health checks passed.
  - canonical verify passed with profile `code`, ownership `task-owned`, lite replay `15 passed / 0 failed`, Python tests `517 OK / 4 skipped`.
- Queue status update: `done`.

## Closure

- closed_report: `meta/reports/archive/20260507-generated-project-runnable-source-guard.md`
- canonical_verify: passed on 2026-05-07 with `CTCP_FORCE_PROVIDER` cleared and `CTCP_RUNS_ROOT` set to `%TEMP%\ctcp_runs`.
