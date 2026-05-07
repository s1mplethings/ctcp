# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260508-generated-project-signature-test-validation.md`
- Date: `2026-05-08`
- Topic: `Generated Project Signature And Test-Import Validation Hardening`

### Readlist
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
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_project_generation_artifacts.py`
- live run evidence: `%TEMP%\ctcp_runs\ctcp\voice-assistant-phone-pc-live-20260508`

### Plan
1. Bind `ADHOC-20260508-generated-project-signature-test-validation`.
2. Add generic generated-test validation and import-style checks.
3. Add retry prompt feedback for generated-test and constructor/signature failures.
4. Add focused regression tests.
5. Run focused tests, code-health, workflow checks, and canonical verify.

### Changes
- Added `tools/providers/project_generation_generated_tests.py` as a generic generated-project unittest/import-style validator.
- Wired `generic_validation` to run generated tests with generated `src` on `PYTHONPATH` and to block `src.<package>` imports in generated tests.
- Extended source-generation retry feedback so `generated_tests` failures and constructor/signature runtime errors are consumed by the next API source_generation prompt.
- Added regression coverage in `tests/test_generated_project_validation_self_repair.py`.
- Added issue memory entry `20260508_001` for the repeated user-visible generated-source self-check failure.

### Verify
- PASS: `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tools\providers\project_generation_validation.py tools\providers\project_generation_generated_tests.py tests\test_generated_project_validation_self_repair.py` returned 0.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v` returned 0, 2 tests OK.
- PASS: `$env:PYTHONPATH=(Get-Location).Path; .venv\Scripts\python.exe tests\test_project_generation_artifacts.py -k source_generation -v` returned 0, 11 tests OK.
- PASS: `.venv\Scripts\python.exe tests\test_api_agent_templates.py -k source_generation -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, ownership `task-owned`, no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0 after keeping `project_generation_validation.py` at its baseline line count.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after report evidence was updated.
- PASS: `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. The canonical run executed lite build/ctest, workflow gate, module protection, prompt/plan/patch/behavior/contract/doc-index/code-health gates, triplet guard, lite replay, and 519 Python unit tests with 4 skipped.
- FIRST FAILURE POINT: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 1 before this report update because `LAST.md` lacked mandatory evidence fields; implementation tests had already passed.
- MINIMAL FIX STRATEGY: record the exact command evidence, triplet evidence, issue memory decision, and first-failure/minimal-fix fields in this report, then rerun workflow and canonical verify.

### Questions
- None.

### Demo
- Target failure classes from live run:
  - `VoiceAssistantService.__init__()` missing required `whitelist`.
  - generated tests importing `src.readme`.

### Integration Proof
- connected: `generic_validation` calls `generated_tests_validation`, and source_generation already consumes `generic_validation` as its blocking report.
- accumulated: generated-test import-style violations and unittest stdout/stderr tails are stored under `generic_validation.generated_tests` in `artifacts/source_generation_report.json`.
- consumed: `render_source_generation_payload_requirements` reads `generic_validation.generated_tests` and injects concrete retry repair instructions into the next source_generation prompt.

### Issue Memory
- issue memory decision: required, because this was a repeated user-visible generated-project failure after prior source_generation prompt hardening.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.

### First Failure And Repair
- first failure point evidence: workflow gate initially failed only on missing `LAST.md` mandatory evidence, not on code behavior.
- minimal fix strategy evidence: update report evidence, keep code patch unchanged, rerun workflow and canonical verify; final canonical verify passed.

### Skill Decision
- skillized: no, because this is a focused validation hardening; it can become a reusable skill only after several generated-project domains use the same self-check loop.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
