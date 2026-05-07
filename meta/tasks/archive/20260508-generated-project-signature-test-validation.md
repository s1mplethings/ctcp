# Task Archive - Generated Project Signature And Test-Import Validation Hardening

## Queue Binding

- Queue Item: `ADHOC-20260508-generated-project-signature-test-validation`
- Layer/Priority: `L1 / P0`
- Status: `done`
- Lane: Delivery Lane

## Scope

Add generic generated-project self-check and source_generation retry feedback for the failure classes found in the live phone-to-PC voice assistant run: constructor/API signature mismatch and generated tests importing `src.<package>`.

Out of scope:
- local deterministic project templates
- generated-run source patching as proof
- dependency installation bypasses

## Results

- Added `tools/providers/project_generation_generated_tests.py`.
- `generic_validation` now runs generated unittest discovery with the generated `src` directory on `PYTHONPATH`.
- Generated tests that import `src` or `src.<package>` are blocked as invalid import style.
- `source_generation_prompt` now consumes `generic_validation.generated_tests` and runtime constructor/signature failures as retry repair evidence.
- Added `tests/test_generated_project_validation_self_repair.py`.
- Added issue memory record `20260508_001`.

## Verify

- `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tools\providers\project_generation_validation.py tools\providers\project_generation_generated_tests.py tests\test_generated_project_validation_self_repair.py` -> exit 0.
- `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v` -> exit 0, 2 tests OK.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK.
- `.venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, `task-owned`.
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0.

## First Failure And Repair

- first failure point evidence: workflow gate initially failed because `meta/reports/LAST.md` lacked mandatory evidence fields.
- minimal fix strategy evidence: add report evidence for first failure, triplet tests, issue memory, and skill decision; then rerun workflow/canonical verify.

## Integration Proof

- connected: source_generation calls `generic_validation`, which now calls generated-test validation.
- accumulated: generated-test import-style and unittest stdout/stderr evidence is stored under `generic_validation.generated_tests`.
- consumed: `render_source_generation_payload_requirements` reads that evidence and adds retry repair instructions.

## Skill Decision

- skillized: no, because this is a focused validation hardening; it can become a reusable skill only after several generated-project domains use the same self-check loop.
