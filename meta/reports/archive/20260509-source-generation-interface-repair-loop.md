# Demo Report - Source Generation Interface Repair Loop Hardening

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
- `tools/providers/project_generation_signature_validation.py`
- `tools/providers/project_generation_validation.py`
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_generated_project_signature_validation.py`

## Plan

1. Bind `ADHOC-20260509-source-generation-interface-repair-loop`.
2. Extend generic validation for abstract stubs and signature matrix drift.
3. Strengthen source_generation retry prompt consumption.
4. Add focused regression tests.
5. Run focused/project-generation checks and canonical verify.
6. Archive task/report evidence.

## Changes

- Added provider-declared signature matrix validation under `python_signature_consistency.interface_signature_mismatches`.
- Added generated Python abstract-stub validation under `python_signature_consistency.abstract_stub_violations`.
- Wired provider interface contracts into signature validation from `generic_validation`.
- Strengthened the source_generation prompt to require `interfaces[path].signatures`, forbid runtime `raise NotImplementedError`, and render `signature_matrix` / `abstract_stub` retry evidence.
- Added focused regression coverage for signature matrix drift and abstract runtime stubs.
- Recorded issue-memory fix `20260509_002`.

## Verify

- PASS: `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_signature_validation.py tools\providers\project_generation_validation.py ctcp_adapters\source_generation_prompt.py tests\test_generated_project_signature_validation.py`
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generated_project_signature_validation -v` returned 0, 5 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v` returned 0, 2 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v` returned 0, 22 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` returned 0, 48 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after report evidence update.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: triplet guard tests returned 0: runtime wiring 25 OK, issue memory 3 OK, skill consumption 3 OK.
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. It ran code profile and 525 Python tests OK with 4 skipped.

## Questions

- None.

## Demo

- Focused regression creates a generated `VoiceAssistantService(command_whitelist)` implementation while the provider interface contract declares `VoiceAssistantService(whitelist)`; `python_signature_consistency.interface_signature_mismatches` blocks the mismatch.
- The same regression includes a generated method that raises `NotImplementedError`; `python_signature_consistency.abstract_stub_violations` blocks it.

## Integration Proof

- connected: `generic_validation()` passes provider interface contracts into `python_signature_consistency_validation()`.
- accumulated: the signature report now carries call-site, signature-matrix, and abstract-stub blockers.
- consumed: `render_source_generation_payload_requirements()` renders those blockers as concrete retry requirements.

## Issue Memory

- issue memory decision: required and recorded as `20260509_002`.

## First Failure And Repair

- first failure point evidence: live retest blocked at `generic_validation.passed must be true` with signature drift and abstract `NotImplementedError` runtime path.
- minimal fix strategy evidence: harden generic validation and retry prompt; do not patch generated source or add deterministic templates.

## Skill Decision

- skillized: no, this is a validator/prompt integration inside an existing workflow, not a reusable agent workflow.
- persona_lab_impact: none.
