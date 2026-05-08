# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260508-source-generation-interface-validation.md`
- Date: `2026-05-08`
- Topic: `Project Generation Cross-File Interface Validation`

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
- `meta/backlog/execution_queue.json`
- `tools/providers/project_generation_validation.py`
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_generated_project_validation_self_repair.py`

### Plan
1. Bind `ADHOC-20260508-source-generation-interface-validation`.
2. Inspect existing generated-project validation and source_generation retry prompt.
3. Add conservative AST-based generated Python signature validation.
4. Feed mismatch evidence into source_generation retries.
5. Add focused regression tests.
6. Run focused checks and canonical verify.
7. Archive task/report evidence.

### Changes
- Added `tools/providers/project_generation_signature_validation.py`, a conservative AST-based validator for generated Python definitions and direct call sites.
- Integrated `python_signature_consistency` into `generic_validation` pass/fail and source-generation report evidence.
- Added retry prompt feedback for `signature_consistency` mismatches, including caller path/line, callee, target signature, missing args, unexpected keywords, and positional mismatch notes.
- Added focused regression coverage for `VoiceAssistantService(whitelist)` missing required construction and `CommandWhitelist(commands=...)` unexpected keyword drift.
- Recorded the concrete fix in `issue_memory/modifications.jsonl` as `20260508_003`.

### Verify
- PASS: `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_signature_validation.py tools\providers\project_generation_validation.py ctcp_adapters\source_generation_prompt.py tests\test_generated_project_signature_validation.py`
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generated_project_signature_validation -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v` returned 0, 2 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v` returned 0, 22 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` returned 0, 48 tests OK.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\workflow_checks.py` initially returned 1 because this report did not yet include triplet evidence lines. Minimal repair: add the triplet command evidence above and rerun workflow checks.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after report evidence update.
- FIRST FAILURE: `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` initially returned 1 because inherited `CTCP_FORCE_PROVIDER=api_agent` overrode mock-provider routing in `test_mock_agent_pipeline.py`. Minimal repair: clear the environment override for verify.
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. It ran code profile, CMake lite build/ctest, workflow/module/prompt/plan/patch/behavior/contract/doc/code-health/triplet gates, and 523 Python unit tests OK with 4 skipped. Lite replay was skipped by `CTCP_SKIP_LITE_REPLAY=1`.

### Questions
- None.

### Demo
- The focused regression constructs a generated project where `VoiceAssistantService.__init__(whitelist)` is called as `VoiceAssistantService()` and `CommandWhitelist.__init__(allowed)` is called as `CommandWhitelist(commands=set())`; `python_signature_consistency` reports both mismatches and blocks `generic_validation.passed`.

### Integration Proof
- connected: `generic_validation()` calls `python_signature_consistency_validation()`.
- accumulated: `generic_validation` returns a `python_signature_consistency` report with concrete mismatch rows.
- consumed: `render_source_generation_payload_requirements()` converts those rows into retry prompt lines for the next API source_generation attempt.

### Issue Memory
- issue memory decision: required because this task implements a repair for recorded issue `20260508_002`.

### First Failure And Repair
- first failure point evidence: prior CTCP run blocked at `generic_validation.passed must be true` due cross-file signature drift.
- minimal fix strategy evidence: add generic signature validation and retry feedback; do not patch generated code locally.

### Skill Decision
- skillized: no, this is a validator extension inside the existing project-generation workflow, not a reusable agent workflow.
- persona_lab_impact: none.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
