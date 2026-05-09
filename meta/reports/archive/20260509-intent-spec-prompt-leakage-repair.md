# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260509-intent-spec-prompt-leakage-repair.md`
- Date: `2026-05-09`
- Topic: `Intent/Spec Slug And Source-Generation Prompt Leakage Repair`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `tools/providers/project_generation_artifacts.py`
- `tools/providers/project_generation_goal_slug.py`
- `tools/providers/project_generation_generic_spec.py`
- `tools/providers/project_generation_decisions.py`
- `tools/providers/project_generation_domain_contract.py`
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_project_generation_artifacts.py`
- `tests/test_api_agent_templates.py`
- `tests/test_project_generation_voice_assistant_contract.py`
- `tests/test_source_generation_prompt_leakage.py`

### Plan
1. Bind `ADHOC-20260509-intent-spec-prompt-leakage-repair`.
2. Add regressions for non-ASCII slug/spec collapse and prompt leakage.
3. Repair generic project slug/spec shaping.
4. Make source_generation prompt rules conditional by contract.
5. Run focused and broader checks.
6. Run canonical verify and archive evidence.

### Changes
- Added semantic slug fallback for non-ASCII project goals, avoiding incidental `readme` project IDs.
- Added generic web-service goal-specific scope and acceptance criteria to the enriched project spec.
- Made source_generation prompt import examples use the actual package name from `output_contract_freeze`.
- Made GUI/narrative prompt requirements conditional on the frozen contract instead of unconditional.
- Added focused regressions for the voice-assistant API retest failure class.
- Recorded issue-memory fix attempt `20260509_004`.

### Verify
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_project_generation_voice_assistant_contract.VoiceAssistantContractTests.test_chinese_voice_assistant_goal_uses_goal_specific_slug_and_spec -v` returned 0.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_source_generation_prompt_leakage.SourceGenerationPromptLeakageTests.test_web_service_prompt_excludes_narrative_gui_leakage -v` returned 0.
- PASS: `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_artifacts.py tools\providers\project_generation_decisions.py tools\providers\project_generation_goal_slug.py tools\providers\project_generation_generic_spec.py ctcp_adapters\source_generation_prompt.py tests\test_project_generation_artifacts.py tests\test_api_agent_templates.py tests\test_project_generation_voice_assistant_contract.py tests\test_source_generation_prompt_leakage.py` returned 0.
- FIRST FAILURE: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v` initially returned 1 because the existing VN/GUI prompt test still expected the `/status` web self-test guidance. Minimal repair: retain the `/status` guidance for both web and GUI shapes while keeping GUI/narrative-only leakage conditional.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0 after moving new helpers/tests into small files.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v` returned 0, 22 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v` returned 0, 48 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_voice_assistant_contract.py" -v` returned 0, 1 test OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_source_generation_prompt_leakage.py" -v` returned 0, 1 test OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, no violations.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after report evidence update.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: issue memory JSONL parse check returned 0.
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; Remove-Item Env:CTCP_FORMAL_API_ONLY -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. It ran code profile, CMake lite build/ctest, workflow/module/prompt/plan/patch/behavior/contract/doc/code-health/triplet gates, and 527 Python unit tests OK with 4 skipped. Lite replay was skipped by `CTCP_SKIP_LITE_REPLAY=1`.

### Questions
- None.

### Demo
- For the previous API retest goal, `normalize_output_contract_freeze()` now returns `project_id=voice-assistant` and `package_name=voice_assistant` instead of `readme`.
- For a web-service source_generation contract, the prompt includes `from voice_assistant.service`, `/` plus `/status` requirements, and `--serve`; it excludes stale `run_project_gui.py`, `tkinter`, `from vn.service`, and `story/scene/branch editor` requirements.

### Integration Proof
- connected: `normalize_output_contract_freeze()` feeds the improved project ID/spec into the frozen output contract.
- accumulated: regression tests capture both the contract-collapse and prompt-leakage failure classes.
- consumed: `render_source_generation_payload_requirements()` consumes `project_root`, `package_name`, `project_domain`, `project_archetype`, `delivery_shape`, and `startup_entrypoint` to render the corrected API prompt.

### Issue Memory
- issue memory decision: required; this task is the fix attempt for recorded regression `20260509_003`.

### First Failure And Repair
- first failure point evidence: live API retest generated `project_output/readme` and leaked narrative GUI prompt rules into a generic web-service request.
- minimal fix strategy evidence: repair slug/spec shaping and prompt conditionality; do not add a local deterministic project template.

### Skill Decision
- skillized: no, this is a project-generation bug fix inside an existing workflow, not a reusable agent workflow.
- persona_lab_impact: none.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
