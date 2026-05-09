# Task - Intent/Spec Slug And Source-Generation Prompt Leakage Repair

## Queue Binding

- Queue Item: `ADHOC-20260509-intent-spec-prompt-leakage-repair`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: live API retest `voice-assistant-interface-repair-api-20260509` used `api_agent/gpt-4.1` without local fallback, but the generated project collapsed to `project_output/readme` and source_generation prompt leaked stale VN/GUI constraints into a generic web-service request.
- Lane: Delivery Lane.
- Scope boundary: fix generic project-id/spec shaping and prompt conditionality. Do not add local deterministic project templates or manually repair generated output.

## Task Truth Source

- task_purpose:
  - Prevent Chinese/non-ASCII project goals from deriving `project_id=readme` only because README is the only ASCII token.
  - Preserve goal-specific problem/scope/acceptance signals in generic project specs so API source_generation receives a concrete project contract.
  - Stop unconditional narrative GUI / `run_project_gui.py` prompt rules from leaking into non-narrative web-service source_generation prompts.
- allowed_behavior_change:
  - Default project slug generation may use curated generic semantic tokens from the user goal.
  - Generic project spec fallback may be more concrete while remaining project-agnostic.
  - Source-generation prompt requirements may be conditional on output contract domain, delivery shape, and startup entrypoint.
- forbidden_goal_shift:
  - Do not add local deterministic project templates.
  - Do not manually patch generated project files.
  - Do not change provider credentials or endpoint config.
  - Do not add a voice-assistant-specific generated implementation.
- in_scope_modules:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_goal_slug.py`
  - `tools/providers/project_generation_generic_spec.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_project_generation_voice_assistant_contract.py`
  - `tests/test_source_generation_prompt_leakage.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260509-intent-spec-prompt-leakage-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-intent-spec-prompt-leakage-repair.md`
- out_of_scope_modules:
  - provider credentials
  - generated project source files
  - local deterministic materializers/templates
  - Telegram bot runtime
- completion_evidence:
  - focused tests prove voice-assistant-like Chinese goal does not freeze as `readme`.
  - focused tests prove generic web-service prompt excludes narrative GUI leakage.
  - canonical verify passes or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_goal_slug.py`
  - `tools/providers/project_generation_generic_spec.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_project_generation_artifacts.py`
  - `tests/test_api_agent_templates.py`
  - `tests/test_project_generation_voice_assistant_contract.py`
  - `tests/test_source_generation_prompt_leakage.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260509-intent-spec-prompt-leakage-repair.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-intent-spec-prompt-leakage-repair.md`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated project source files
  - local deterministic project templates/materializers
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no local project template fallback
  - no generated-run source patching
  - no provider credential changes
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m unittest tests.test_project_generation_voice_assistant_contract.VoiceAssistantContractTests.test_chinese_voice_assistant_goal_uses_goal_specific_slug_and_spec -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_source_generation_prompt_leakage.SourceGenerationPromptLeakageTests.test_web_service_prompt_excludes_narrative_gui_leakage -v`
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Reproduced evidence:
  - `normalize_output_contract_freeze({}, goal=<Chinese phone-to-PC voice assistant goal>)` returns `project_id=readme` and `package_name=readme`.
  - The same output contract keeps generic fallback problem/scope/acceptance rather than goal-specific product flow.
  - `render_source_generation_payload_requirements()` always includes `run_project_gui.py`, `workspace_preview.html` narrative controls, and `tkinter` guidance even for web-service contracts.
- Validation target:
  - generated project ID/package name should come from user-goal semantics, not incidental README token.
  - source_generation prompt should be domain/shape-specific.
- External research artifact: none.

## Integration Check

- upstream: `output_contract_freeze` and source_generation prompt rendering.
- current_module: project-generation artifact normalization and API prompt requirements.
- downstream: API-authored source_generation batches and generated project validation.
- source_of_truth: frozen output contract plus current task failure evidence `20260509_003`.
- fallback: keep generic behavior for unknown goals, but improve slug/spec signal rather than generating a local project.
- acceptance_test:
  - focused regression tests.
  - project-generation/api-agent suites.
  - canonical verify.
- forbidden_bypass:
  - no generated source patching.
  - no deterministic template fallback.
- user_visible_effect: future API generation should receive a concrete, non-contaminated source_generation contract for the user's actual project goal.

## DoD Mapping

- [x] DoD-1: Chinese/non-ASCII voice-assistant goal no longer freezes as `readme`.
- [x] DoD-2: Generic project spec fallback carries goal-specific scope/acceptance.
- [x] DoD-3: Web-service source_generation prompt excludes narrative GUI leakage.
- [x] DoD-4: Focused and broader regression tests pass.
- [x] DoD-5: Canonical verification passes or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Reproduce contract collapse and prompt leakage from the previous API retest goal.
- contrast:
  - The generated code failed partly because upstream contract/prompt was inconsistent before API wrote files.
- fix:
  - Repair generic slug/spec shaping and conditional prompt rendering.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: output_contract_freeze and prompt rendering consume the improved goal/domain/shape data.
- accumulated: tests capture both failure classes as regression evidence.
- consumed: source_generation prompt uses the corrected contract to guide API output.

## Issue Memory Decision Evidence

- issue_memory_decision: required; this task is the fix attempt for recorded regression `20260509_003`.

## Plan

1. Bind the code repair task.
2. Add failing regressions for the voice-assistant slug/spec collapse and prompt leakage.
3. Implement generic slug/spec shaping improvements.
4. Make source_generation prompt sections conditional by project domain/shape/startup entrypoint.
5. Run focused and broad regression checks.
6. Run repo gates and archive evidence.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed for scoped repair.
- [x] Slug/spec repair implemented.
- [x] Prompt leakage repair implemented.
- [x] Tests pass.
- [x] Metadata closure checks pass.

## Results

- Implemented semantic slug fallback for non-ASCII goals in `tools/providers/project_generation_goal_slug.py` so the phone-to-PC voice assistant goal freezes as:
  - `project_id=voice-assistant`
  - `package_name=voice_assistant`
  - `project_archetype=web_service`
  - `delivery_shape=web_first`
- Generic web-service project specs now include goal-specific scope and acceptance signals from `tools/providers/project_generation_generic_spec.py` for local web startup, `/` and `/status`, generated-test/service signature agreement, and sample data alignment.
- `source_generation` prompt rendering now uses the actual `package_name` in import examples.
- GUI/narrative-only prompt guidance is now conditional:
  - `run_project_gui.py`, `tkinter`, and launcher compatibility table appear only for GUI entrypoints/shapes.
  - `story/scene/branch editor` and character/asset management preview requirements appear only for narrative/VN contracts.
  - web `/` and `/status` guidance remains for web or GUI shapes.
- Issue memory fix attempt recorded as `20260509_004`.
- Focused checks:
  - `.venv\Scripts\python.exe -m unittest tests.test_project_generation_voice_assistant_contract.VoiceAssistantContractTests.test_chinese_voice_assistant_goal_uses_goal_specific_slug_and_spec -v`: PASS.
  - `.venv\Scripts\python.exe -m unittest tests.test_source_generation_prompt_leakage.SourceGenerationPromptLeakageTests.test_web_service_prompt_excludes_narrative_gui_leakage -v`: PASS.
  - `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_artifacts.py tools\providers\project_generation_decisions.py tools\providers\project_generation_goal_slug.py tools\providers\project_generation_generic_spec.py ctcp_adapters\source_generation_prompt.py tests\test_project_generation_artifacts.py tests\test_api_agent_templates.py tests\test_project_generation_voice_assistant_contract.py tests\test_source_generation_prompt_leakage.py`: PASS.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v`: PASS, 22 tests OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`: PASS, 48 tests OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_voice_assistant_contract.py" -v`: PASS, 1 test OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_source_generation_prompt_leakage.py" -v`: PASS, 1 test OK.
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`: PASS after moving new helpers/tests into small files.
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`: PASS.
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`: PASS.
  - `.venv\Scripts\python.exe scripts\patch_check.py`: PASS.
  - `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; Remove-Item Env:CTCP_FORMAL_API_ONLY -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`: PASS, 527 Python tests OK, 4 skipped.

## Notes / Decisions

- Default choice made: implement generic semantic slug/spec repair, not a local generated project template.
- Skill decision: skillized: no, this is a project-generation bug fix inside an existing workflow, not a reusable agent workflow.
- persona_lab_impact: none.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
