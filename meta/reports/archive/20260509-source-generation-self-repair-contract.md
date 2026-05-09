# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260509-source-generation-self-repair-contract.md`
- Date: `2026-05-09`
- Topic: `Source Generation Self-Repair Contract For API-Authored Projects`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `tools/providers/project_generation_goal_slug.py`
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_project_generation_voice_assistant_contract.py`
- `tests/test_source_generation_prompt_leakage.py`
- `issue_memory/modifications.jsonl`

### Plan
1. Bind `ADHOC-20260509-source-generation-self-repair-contract`.
2. Add regressions for mixed Chinese/English project identity and source_generation retry-feedback consumption.
3. Repair semantic slug priority so weak artifact words do not override product semantics.
4. Strengthen retry prompt requirements after blocked generic validation.
5. Run focused suites and related project-generation/api-agent regressions.
6. Run repo gates and archive evidence.

### Changes
- Updated `semantic_project_slug()` so weak artifact words such as `web`, `readme`, `service`, `project`, and `test` do not dominate a mixed Chinese/English goal when semantic product markers are present.
- Mapped `voice + control + mobile/pc` to `voice-assistant` so the exact phone-to-PC voice-control test goal freezes as `project_output/voice-assistant` and package `voice_assistant`.
- Added `retry_gate` source_generation prompt lines when a previous `source_generation_report.json` is blocked.
- The retry gate requires the API to replace the broken manifest/interface contract and affected files together so startup, imports, signatures, generated tests, and smoke probes can pass as one consistent set.
- Added focused regressions for the `web-readme` identity failure and for consuming startup/import/interface/signature/abstract-stub/generated-test failure evidence.
- Recorded issue-memory fix attempt `20260509_005`.

### Verify
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_voice_assistant_contract.py" -v` returned 0, 2 tests OK.
- FIRST FAILURE: the first run of `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_voice_assistant_contract.py" -v` returned 1 because the exact mixed goal froze as `voice-mobile-pc-web`; minimal repair was to map `voice + control + mobile/pc` to `voice-assistant`.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_source_generation_prompt_leakage.py" -v` returned 0, 2 tests OK.
- PASS: `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_goal_slug.py ctcp_adapters\source_generation_prompt.py tests\test_project_generation_voice_assistant_contract.py tests\test_source_generation_prompt_leakage.py` returned 0.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v` returned 0, 22 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` returned 0, 48 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 1 because `meta/reports/LAST.md` had not yet been updated; minimal repair was this report update.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after task/report evidence updates.
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; Remove-Item Env:CTCP_FORMAL_API_ONLY -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. It ran code profile, CMake lite build/ctest, workflow/module/prompt/plan/patch/behavior/contract/doc/code-health/triplet gates, and 529 Python unit tests OK with 4 skipped. Lite replay was skipped by `CTCP_SKIP_LITE_REPLAY=1`.

### Questions
- None.

### Demo
- The exact test goal containing Chinese product text plus English `Web` and `README` now freezes to:
  - `project_id=voice-assistant`
  - `project_root=project_output/voice-assistant`
  - `package_name=voice_assistant`
- A blocked source_generation report containing `cannot import name execute_command`, interface mismatch, constructor/signature mismatch, `NotImplementedError`, and generated-test import failure now renders those concrete failures into the next API prompt with a blocking `retry_gate`.

### Integration Proof
- connected: `normalize_output_contract_freeze()` reaches the updated `semantic_project_slug()` through `_slug(goal)`, and source_generation prompt rendering reads `artifacts/source_generation_report.json`.
- accumulated: issue memory entry `20260509_005` records the API-only run failure and this fix attempt.
- consumed: `api_agent._render_prompt()` includes the corrected project identity and validation-failure retry gate in source_generation prompts consumed by chunked manifest and file-content batches.

### Issue Memory
- issue memory decision: required; this task fixes a repeated source_generation convergence failure after API-authored code still failed generic validation.

### First Failure And Repair
- first failure point evidence: API-only source_generation authored files with fallback disabled but delivery blocked on `generic_validation.passed=false`; the project froze as `web-readme` and generated code failed import/signature/test/startup checks.
- minimal fix strategy evidence: repair CTCP contract/prompt feedback so API receives the correct project identity and exact validation blockers; do not patch generated project files.

### Skill Decision
- skillized: no, because this is a local project-generation bug fix in the existing CTCP workflow.
- future skill condition: if repeated API retry triage becomes a recurring operator procedure, package a dedicated CTCP source-generation failure bundle skill.
- persona_lab_impact: none.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
