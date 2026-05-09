# Task - Source Generation Self-Repair Contract For API-Authored Projects

## Queue Binding

- Queue Item: `ADHOC-20260509-source-generation-self-repair-contract`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: API-only run `voice-assistant-api-only-20260509` proved `api_agent` can author source files, but CTCP still blocked delivery because `source_generation` produced `project_output/web-readme`, startup imports failed, generated tests failed, and interface/signature validation failures were not repaired by subsequent API retries.
- Lane: Delivery Lane.
- Scope boundary: improve project identity freezing and source_generation retry feedback. Do not manually patch generated project files and do not add a local deterministic project template.

## Task Truth Source

- task_purpose:
  - Ensure mixed Chinese/English goals such as "本地 Web 服务 ... README" still freeze to the semantic product identity, e.g. `voice-assistant`, not incidental `web-readme`.
  - Ensure generic validation failures are rendered as mandatory repair instructions for the next API source_generation attempt.
  - Make API-authored source retries fix startup, import, signature, interface, abstract stub, and generated-test failures before delivery can pass.
- allowed_behavior_change:
  - Project slug selection may prefer semantic goal tokens over weak artifact words such as `web` and `readme`.
  - Source-generation prompts may include compact prior validation failure summaries from `artifacts/source_generation_report.json`.
  - Retry instructions may explicitly require replacing inconsistent API-authored files rather than preserving broken interfaces.
- forbidden_goal_shift:
  - Do not add generated voice-assistant implementation code to the repo.
  - Do not manually edit files under an external run's `project_output`.
  - Do not add local deterministic business templates/materializers.
  - Do not change provider credentials or endpoint config.
- in_scope_modules:
  - `tools/providers/project_generation_goal_slug.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_project_generation_voice_assistant_contract.py`
  - `tests/test_source_generation_prompt_leakage.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260509-source-generation-self-repair-contract.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-source-generation-self-repair-contract.md`
- out_of_scope_modules:
  - generated run source files
  - provider credentials
  - Telegram bot runtime
  - local project templates/materializers
- completion_evidence:
  - regression proves mixed Chinese/English voice assistant goal does not freeze to `web-readme`.
  - regression proves source_generation prompt consumes prior generic_validation failure details.
  - focused suites and canonical verify pass or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_goal_slug.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_project_generation_voice_assistant_contract.py`
  - `tests/test_source_generation_prompt_leakage.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260509-source-generation-self-repair-contract.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-source-generation-self-repair-contract.md`
- Protected Paths:
  - provider credentials
  - generated run `project_output`
  - local deterministic project templates/materializers
  - frozen kernels
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no generated source patching
  - no deterministic template fallback
  - no provider credential changes
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_voice_assistant_contract.py" -v`
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_source_generation_prompt_leakage.py" -v`
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Reproduced evidence from external run:
  - provider ledger shows `source_generation` executed via `api_agent`, `fallback_used=false`, three times.
  - generated source exists under `project_output/web-readme`, proving project identity still came from weak English artifact words.
  - `generic_validation.passed=false` because startup imports failed, generated tests failed, interface declarations did not match actual Python symbols, signatures mismatched, and abstract stub violations remained.
- Validation target:
  - project identity must remain semantic and goal-specific even when the goal includes English artifact words.
  - retries must explicitly feed validation failures back into the API prompt.
- External research artifact: none.

## Integration Check

- upstream: `output_contract_freeze` goal slug selection and `source_generation` prompt assembly.
- current_module: project-generation goal slug helper and source-generation prompt adapter.
- downstream: API-authored source_generation batches, generic validation, delivery gate.
- source_of_truth: external run `voice-assistant-api-only-20260509` artifacts plus current task card.
- fallback: block delivery when validation still fails; do not locally repair generated source.
- acceptance_test:
  - focused slug regression.
  - focused retry-feedback prompt regression.
  - api-agent template suite.
  - canonical verify.
- forbidden_bypass:
  - no generated source patching.
  - no deterministic template fallback.
- user_visible_effect:
  - future API-only project generation should name the project from the user's actual product goal and should retry source_generation with concrete validation blockers instead of repeating broken source bundles.

## DoD Mapping

- [x] DoD-1: mixed Chinese/English voice-assistant goal freezes to `voice-assistant`, not `web-readme`.
- [x] DoD-2: source_generation prompt includes compact validation failure feedback from prior source_generation report.
- [x] DoD-3: retry feedback names startup/import/test/interface/signature/abstract-stub repair obligations.
- [x] DoD-4: focused and broader regression tests pass.
- [x] DoD-5: canonical verification passes or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - API-only run `voice-assistant-api-only-20260509` showed `api_agent` authored source files but froze project identity as `web-readme` and remained blocked on `generic_validation.passed=false`.
  - Focused regression initially reproduced a related slug failure: the mixed Chinese/English goal froze as `voice-mobile-pc-web` instead of `voice-assistant`.
- contrast:
  - The previous slug fix handled goals with explicit `助理/assistant`, but not goals expressed as `语音输入 + 手机/电脑 + 操控` plus incidental English artifact words.
  - Existing validation feedback existed, but API retries could still preserve a broken manifest/interface contract instead of replacing all affected files together.
- fix:
  - Prefer semantic voice-control product identity over weak artifact ASCII words.
  - Add retry-gate instructions that make validation failure evidence blocking repair input for the next source_generation attempt.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: `normalize_output_contract_freeze()` reaches the updated slug helper through `_slug(goal)`, and source_generation prompt rendering reads the prior `artifacts/source_generation_report.json`.
- accumulated: issue memory entry `20260509_005` records the API-only run failure and this fix attempt.
- consumed: `api_agent._render_prompt()` includes the corrected identity and retry-gate validation blockers in prompts used by source_generation manifest and file-content batches.

## Plan

1. Bind this repair task.
2. Add/extend focused regressions for mixed-language project identity and validation-feedback prompt consumption.
3. Update semantic slug priority to prefer product semantics over weak artifact words.
4. Add compact source_generation validation failure rendering to API prompt requirements.
5. Run focused suites, repo gates, and canonical verify.
6. Record issue memory and archive task/report evidence.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed for scoped repair.
- [x] Slug priority repair implemented.
- [x] Validation-feedback prompt repair implemented.
- [x] Tests pass.
- [x] Metadata closure checks pass.

## Results

- Implemented semantic slug priority repair in `tools/providers/project_generation_goal_slug.py`:
  - Weak delivery/artifact ASCII words such as `web`, `readme`, `service`, `test`, and `project` no longer override semantic Chinese goal markers.
  - `voice + control + mobile/pc` now freezes as `voice-assistant` even when the literal word `assistant`/`助理` is absent.
- Strengthened source-generation retry feedback in `ctcp_adapters/source_generation_prompt.py`:
  - When a previous `source_generation_report.json` is blocked, the next prompt includes a `retry_gate`.
  - The `retry_gate` requires replacing the broken manifest/interface contract and affected file contents together, rather than preserving failing imports, signatures, re-exports, tests, or startup commands.
- Added regressions:
  - mixed Chinese/English phone-to-PC voice-control goal freezes to `project_output/voice-assistant` and `voice_assistant`, not `web-readme`.
  - retry prompt consumes startup/import/interface/signature/abstract-stub/generated-test failures from `generic_validation`.
- Issue memory fix attempt recorded as `20260509_005`.
- Checks:
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_voice_assistant_contract.py" -v`: PASS, 2 tests OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_source_generation_prompt_leakage.py" -v`: PASS, 2 tests OK.
  - `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_goal_slug.py ctcp_adapters\source_generation_prompt.py tests\test_project_generation_voice_assistant_contract.py tests\test_source_generation_prompt_leakage.py`: PASS.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v`: PASS, 22 tests OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`: PASS, 48 tests OK.
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`: PASS.
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`: PASS, no violations.
  - `.venv\Scripts\python.exe scripts\patch_check.py`: PASS.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`: PASS, 3 tests OK.
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`: FIRST FAILURE, `meta/reports/LAST.md` not updated yet; repair is to update the report before rerun.
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`: PASS after task/report evidence updates.
  - `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; Remove-Item Env:CTCP_FORMAL_API_ONLY -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`: PASS, 529 Python tests OK, 4 skipped.

## Notes / Decisions

- Default choice made: repair CTCP's contract/prompt feedback loop, not the generated project.
- Skill decision: skillized: no, because this is a project-generation bug fix in an existing CTCP workflow; it can become a skill only if repeated API retry triage becomes a reusable operator workflow.
- persona_lab_impact: none.
