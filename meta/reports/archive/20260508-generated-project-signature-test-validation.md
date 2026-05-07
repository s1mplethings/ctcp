# Report Archive - Generated Project Signature And Test-Import Validation Hardening

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `TREE.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `meta/tasks/CURRENT.md`
- `tools/providers/project_generation_validation.py`
- `tools/providers/project_generation_generated_tests.py`
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_generated_project_validation_self_repair.py`
- live run evidence: `%TEMP%\ctcp_runs\ctcp\voice-assistant-phone-pc-live-20260508`

## Plan

1. Bind `ADHOC-20260508-generated-project-signature-test-validation`.
2. Add generic generated-test validation and import-style checks.
3. Add retry prompt feedback for generated-test and constructor/signature failures.
4. Add focused regression tests.
5. Run focused tests, code-health, workflow checks, and canonical verify.

## Changes

- Added `tools/providers/project_generation_generated_tests.py` as a generic generated-project unittest/import-style validator.
- Wired `generic_validation` to run generated tests with generated `src` on `PYTHONPATH`.
- Extended source-generation retry feedback so `generated_tests` failures and constructor/signature runtime errors are consumed by the next API source_generation prompt.
- Added regression coverage in `tests/test_generated_project_validation_self_repair.py`.
- Added issue memory entry `20260508_001`.

## Verify

- `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tools\providers\project_generation_validation.py tools\providers\project_generation_generated_tests.py tests\test_generated_project_validation_self_repair.py` -> exit 0.
- `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v` -> exit 0, 2 tests OK.
- `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` -> exit 0, 11 tests OK.
- `.venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> exit 0, 25 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0, `task-owned`.
- `.venv\Scripts\python.exe scripts\patch_check.py` -> exit 0.
- `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` -> exit 0.
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0; final Python unit phase ran 519 tests with 4 skipped.

## Questions

- None.

## Demo

Future generated-project failures now produce structured `generic_validation.generated_tests` evidence. The next source_generation retry receives concrete lines for invalid `src.<package>` imports, unittest stderr/stdout, and constructor/signature mismatch hints.

## First Failure And Repair

- first failure point evidence: workflow gate initially failed only on missing `LAST.md` mandatory evidence.
- minimal fix strategy evidence: update report evidence, keep code patch unchanged, rerun workflow and canonical verify.

## Integration Proof

- connected: source_generation calls `generic_validation`, which now calls generated-test validation.
- accumulated: generated-test import-style and unittest stdout/stderr evidence is stored under `generic_validation.generated_tests`.
- consumed: `render_source_generation_payload_requirements` reads that evidence and adds retry repair instructions.

## Issue Memory

- issue memory decision: required because this was a repeated user-visible generated-project failure after prior source_generation prompt hardening.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.

## Skill Decision

- skillized: no, because this is a focused validation hardening; it can become a reusable skill only after several generated-project domains use the same self-check loop.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
