# Demo Report - Project Generation Cross-File Interface Validation

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
- `tools/providers/project_generation_validation.py`
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_generated_project_validation_self_repair.py`

## Plan

1. Bind `ADHOC-20260508-source-generation-interface-validation`.
2. Add conservative AST-based generated Python signature validation.
3. Feed mismatch evidence into source_generation retries.
4. Add focused regression tests.
5. Run focused checks and canonical verify.
6. Archive task/report evidence.

## Changes

- Added `tools/providers/project_generation_signature_validation.py`, a conservative AST validator for generated Python definitions and direct call sites.
- Integrated `python_signature_consistency` into `generic_validation` pass/fail and source-generation report evidence.
- Added retry prompt feedback for `signature_consistency` mismatches.
- Added focused regression coverage for missing required constructor args and unexpected keyword args.
- Recorded issue-memory fix `20260508_003`.

## Verify

- PASS: `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_signature_validation.py tools\providers\project_generation_validation.py ctcp_adapters\source_generation_prompt.py tests\test_generated_project_signature_validation.py`
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generated_project_signature_validation -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v` returned 0, 2 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v` returned 0, 22 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` returned 0, 48 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after report evidence update.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: triplet guard tests returned 0: runtime wiring 25 OK, issue memory 3 OK, skill consumption 3 OK.
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. It ran code profile and 523 Python tests OK with 4 skipped.

## Questions

- None.

## Demo

The focused regression constructs a generated project where `VoiceAssistantService.__init__(whitelist)` is called as `VoiceAssistantService()` and `CommandWhitelist.__init__(allowed)` is called as `CommandWhitelist(commands=set())`. `python_signature_consistency` reports both mismatches and blocks `generic_validation.passed`.

## Integration Proof

- connected: `generic_validation()` calls `python_signature_consistency_validation()`.
- accumulated: `generic_validation` returns a `python_signature_consistency` report with concrete mismatch rows.
- consumed: `render_source_generation_payload_requirements()` converts those rows into retry prompt lines for the next API source_generation attempt.

## First Failure And Repair

- first failure point evidence: prior CTCP run blocked at `generic_validation.passed must be true` due cross-file signature drift.
- verify first failure: inherited `CTCP_FORCE_PROVIDER=api_agent` overrode mock-provider routing; clearing the environment override made the affected mock pipeline test and canonical verify pass.
- minimal fix strategy evidence: add generic signature validation and retry feedback; do not patch generated code locally.

## Skill Decision

- skillized: no, this is a validator extension inside the existing project-generation workflow, not a reusable agent workflow.
- persona_lab_impact: none.
