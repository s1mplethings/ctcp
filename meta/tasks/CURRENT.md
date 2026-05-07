# Task - Generated Project Signature And Test-Import Validation Hardening

## Queue Binding

- Queue Item: `ADHOC-20260508-generated-project-signature-test-validation`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: the fresh live run improved README and package imports, but the generated project still failed on constructor/API signature mismatch and generated tests importing `src.readme`.
- Lane: Delivery Lane.
- Scope boundary: add generic generated-project self-check and retry feedback for signature/test-import failures; do not add local production templates or patch generated run output.

## Task Truth Source

- task_purpose:
  - Generated-project validation must detect generated tests that use the wrong src-layout import mode.
  - Runtime probe/import-time constructor signature failures must be converted into actionable API retry feedback.
  - The fix should be generic across generated Python projects, not specific to the phone-to-PC voice assistant.
- allowed_behavior_change:
  - Generic validation may run generated tests as part of source_generation validation.
  - Source-generation prompt feedback may add self-check and generated-test repair requirements.
- forbidden_goal_shift:
  - Do not create local deterministic project templates.
  - Do not auto-patch generated business logic as proof.
  - Do not install dependencies to make broken generated projects pass.
  - Do not change provider credentials or endpoint config.
- in_scope_modules:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tools/providers/project_generation_validation.py`
  - `tools/providers/project_generation_generated_tests.py`
  - `tests/test_generated_project_validation_self_repair.py`
  - `issue_memory/modifications.jsonl`
  - repo task/report metadata
- out_of_scope_modules:
  - generated run directories
  - Telegram/support bot runtime
  - provider credential files
  - local deterministic materializers/templates
- completion_evidence:
  - focused self-check validation tests pass.
  - source-generation prompt carries generated-test/signature failure feedback.
  - workflow/code-health/canonical verify pass or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tools/providers/project_generation_validation.py`
  - `tools/providers/project_generation_generated_tests.py`
  - `tests/test_generated_project_validation_self_repair.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-generated-project-signature-test-validation.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-generated-project-signature-test-validation.md`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated run directories under repo
  - local API/proxy secrets
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no local project template fallback
  - no generated-run source patching as proof
  - no validation relaxation
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tools\providers\project_generation_validation.py tools\providers\project_generation_generated_tests.py tests\test_generated_project_validation_self_repair.py`
  - `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v`
  - `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`
  - `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Live failure evidence: `voice-assistant-phone-pc-live-20260508` reached API source_generation with `fallback_count=0` and blocked at `generic_validation.passed`.
- First generated-project runtime blocker:
  - `TypeError: VoiceAssistantService.__init__() missing 1 required positional argument: 'whitelist'`
  - generated tests failed with `ModuleNotFoundError: No module named 'src.readme'`
- Current gap:
  - Runtime probes catch constructor signature errors, but generated tests are not validated as a first-class generic self-check result.
  - Previous-failure feedback does not have a dedicated `generated_tests` repair lane.
  - Prompt guidance says not to use `src.<package>` generally, but does not make generated tests prove the same runtime import mode.
- Self-repair strategy:
  - Add a generic generated-test validation stage under `generic_validation`.
  - Treat `src.<package>` imports in generated tests as a validation failure, independent of whether namespace-package behavior makes them importable in one environment.
  - Run generated unittest discovery with the same src-layout assumptions and feed stdout/stderr into the next API retry.
  - Keep local code as validator/feedback only; provider-authored source remains the repair source.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: source_generation materializes provider-authored files.
- current_module: generic generated-project validation and source-generation retry prompt.
- downstream: `artifacts/source_generation_report.json`, next API source_generation retry, and final generated-project delivery gate.
- source_of_truth: generated-project validation report and focused tests.
- fallback: if generated tests cannot be run, report the exception as generated-test validation failure rather than passing silently.
- acceptance_test:
  - new self-check validation tests
  - existing source_generation artifact regressions
  - canonical verify code profile
- forbidden_bypass:
  - no local template fallback
  - no generated-run source patching
  - no dependency installation bypass
- user_visible_effect: future generated projects should fail earlier with specific test/signature feedback, and API retries should have enough evidence to repair without the user manually debugging the bundle.

## DoD Mapping

- [x] DoD-1: Validation detects wrong generated-test `src.<package>` imports.
- [x] DoD-2: Validation reports generated-test runtime failures in `generic_validation`.
- [x] DoD-3: Source-generation retry prompt consumes generated-test/signature blockers.
- [x] DoD-4: Focused tests and canonical verify pass or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Fresh live generated project syntax compiled but failed runtime and generated unittest checks.
  - Existing validation surfaced runtime probe stderr but not generated tests as a structured validation lane.
- contrast:
  - A project can pass syntax/readme/import checks and still fail because tests use the wrong import convention or import-time service construction calls the wrong constructor signature.
  - Prompt-only instruction is weaker than validator-backed repair feedback.
- fix:
  - Add generated-test validation to `generic_validation`.
  - Add source-generation prompt feedback for generated-test stderr/import-style violations.
  - Add focused regression tests for both failure classes.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: generated-test validation is called from `generic_validation`, which is called by source_generation.
- accumulated: generated-test failures are stored in `source_generation_report.json`.
- consumed: source-generation prompt reads those failures and turns them into retry repair instructions.

## Issue Memory Decision Evidence

- issue_memory_decision: required because this is a repeated user-visible generated-project failure after a prior prompt-only repair.

## Plan

1. Bind task and allowed write scope.
2. Add generic generated-test validation and import-style checks.
3. Add retry prompt feedback for generated-test and constructor/signature failures.
4. Add focused regression tests.
5. Run focused tests, code-health, workflow checks, and canonical verify.
6. Archive report/task and keep worktree clean if possible.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed.
- [x] Generic self-check validation updated.
- [x] Focused tests pass.
- [x] Code-health check passes.
- [x] Canonical verify pass or first failure recorded.

## Notes / Decisions

- Default choice made: implement generic validator-backed retry feedback, not local generated-project auto-patching, because production source should still come from the API agent.
- Skill decision: skillized: no, because this is a focused validation hardening; it can become a reusable skill only after several generated-project domains use the same self-check loop.
- persona_lab_impact: none.

## Results

- Added generic generated-project unittest/import-style validation in `tools/providers/project_generation_generated_tests.py`.
- `generic_validation` now blocks generated-test failures and stores `generated_tests` evidence for source_generation retry.
- `render_source_generation_payload_requirements` consumes generated-test and constructor/signature failures as repair instructions.
- Issue memory entry `20260508_001` records the repeated generated-source self-check failure.
- Canonical verify: `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0.
