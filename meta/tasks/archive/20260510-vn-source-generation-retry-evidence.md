# Task - VN Source Generation Retry Evidence

## Queue Binding

- Queue Item: `ADHOC-20260510-vn-source-generation-retry-evidence`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- User request: check the step-by-step records, find the problem, then modify it.
- Run inspected: `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b`.
- Step records inspected:
  - `TRACE.md`
  - `artifacts/provider_ledger_summary.json`
  - `artifacts/output_contract_freeze.json`
  - `artifacts/source_generation_report.json`
  - `meta/reports/LAST.md`
- Current source_generation blocker:
  - provider-authored source was generated.
  - `generic_validation.passed=false`.
  - missing symbols: `service`, `GameState`, `CharacterState`.
  - interface contract drift in package `__init__.py` and `story/__init__.py`.
  - generated tests fail on `StoryOutline.__init__() got an unexpected keyword argument 'synopsis'`.
  - UX validation lacks real visual files, preview source page, forms, inputs, actions, hooks, interaction trace, workspace snapshot, and export script.

## Task Truth Source

- task_purpose:
  - Strengthen source_generation retry evidence so the next API retry receives the complete live VN blocker set.
  - Preserve the boundary that generated VN source is not manually patched by Codex.
- allowed_behavior_change:
  - source_generation retry prompts may include more concrete `ux_validation.interaction_acceptance` evidence.
  - source_generation retry prompt may preserve longer generated-test/probe snippets when needed to expose exact constructor/signature failures.
- forbidden_goal_shift:
  - Do not edit generated VN project source files.
  - Do not weaken validation gates.
  - Do not replace API generation with local templates.
  - Do not hide visual evidence requirements.
- in_scope_modules:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_source_generation_prompt_leakage.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260510-vn-source-generation-retry-evidence.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260510-vn-source-generation-retry-evidence.md`
- out_of_scope_modules:
  - generated run source files
  - provider credentials
  - project generation gates
  - frozen kernels
- completion_evidence:
  - focused retry prompt test passes.
  - workflow/module/patch/code-health gates pass or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_source_generation_prompt_leakage.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260510-vn-source-generation-retry-evidence.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260510-vn-source-generation-retry-evidence.md`
- Protected Paths:
  - generated VN project source files
  - provider credentials
  - frozen kernels
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no generated-source manual patching.
  - no gate weakening.
  - no local template substitution.
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_source_generation_prompt_leakage.py" -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`

## Analysis / Find

- The run records show the pipeline reached source_generation, so the previous output_contract_freeze blockers are no longer the current first failure.
- `source_generation_report.json` is the authority for the next failure.
- Existing retry prompt already includes missing symbols, interface mismatches, signature consistency, generated test failure summary, and top-level UX reasons.
- Gap found: the retry prompt does not include `ux_validation.interaction_acceptance.reasons`, so the next API retry may miss the exact preview interaction evidence requirements.
- Minimal repair: render interaction acceptance reasons into `_previous_failure_lines`.

## Integration Check

- upstream: blocked source_generation report from the live VN run.
- current_module: retry evidence rendering in `ctcp_adapters/source_generation_prompt.py`.
- downstream: `api_agent._render_prompt()` and the next `chair/source_generation` retry.
- source_of_truth: `artifacts/source_generation_report.json`.
- fallback: if retry still blocks, report the new first blocker; do not hand-edit generated source.
- acceptance_test: focused retry prompt leakage suite.
- forbidden_bypass: no generated-source manual repair.
- user_visible_effect: the next API retry sees concrete UX interaction evidence requirements instead of only generic visual evidence text.

## Plan

1. Bind this Delivery Lane task.
2. Add focused regression for live VN source_generation UX interaction evidence.
3. Render `ux_validation.interaction_acceptance.reasons` into retry prompt feedback.
4. Run focused tests and gates.
5. Update report/archive with the exact evidence chain.

## Acceptance

- [x] Lane selected as Delivery Lane.
- [x] Queue item bound before implementation.
- [x] focused retry prompt regression passes.
- [x] module/patch/code-health gates pass.
- [x] workflow gate passes.
- [x] canonical verify timeout recorded.

## Results

- Added `ux_validation.interaction_acceptance.reasons` rendering in `ctcp_adapters/source_generation_prompt.py`.
- Added a focused regression in `tests/test_source_generation_prompt_leakage.py` proving the next source_generation retry prompt includes:
  - import consistency for missing `service`.
  - signature mismatch for `StoryOutline(title, theme, chapters)` and unexpected `synopsis`.
  - generated-test `StoryOutline.__init__()` TypeError evidence.
  - UX interaction blockers for forms, inputs, actions, hooks, interaction trace, workspace snapshot, and export script.
- No generated VN project source files were edited.

## Command Evidence

- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_source_generation_prompt_leakage.py" -v` returned 0, 4 tests OK.
- PASS: `.venv\Scripts\python.exe -m py_compile ctcp_adapters\source_generation_prompt.py tests\test_source_generation_prompt_leakage.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 with no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0.
- triplet runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- triplet issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- triplet skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0.
- TIMEOUT: `$env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` exceeded 30 minutes while running lite scenario replay.
- CLEANUP: stopped matching orphaned `verify_repo.ps1 -Profile code` and `simlab\run.py --suite lite` processes.
- Latest incomplete replay dir observed: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-194847`; no complete `summary.json` was available at inspection time.

## Failure Bundle Evidence

- command: `$env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
- return code: timeout after 30 minutes.
- first failing/blocked gate: canonical verify did not return during `lite scenario replay`.
- evidence path: latest incomplete replay directory `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-194847`.
- minimal fix strategy: keep this task scoped to retry evidence; investigate replay duration/status-owner failures separately before claiming full canonical verify pass.

## Check/Contrast/Fix Loop Evidence

- check: rendered the retry prompt from `vn-project-generation-customer-20260510b` and found it already included import/signature/generated-test blockers but not interaction-acceptance details.
- contrast: `source_generation_report.json` contained explicit UX interaction blockers, including missing forms, inputs, actions, hooks, interaction trace, workspace snapshot, and export script.
- fix: added `ux_interaction` retry lines sourced from `ux_validation.interaction_acceptance.reasons`.
- re-check: focused prompt regression passed and verifies the exact live blocker class reaches the next API retry prompt.

## Completion Criteria Evidence

- completion criteria evidence: connected + accumulated + consumed.
- connected: blocked source_generation reports are read by `_previous_failure_lines`.
- accumulated: UX interaction reasons are converted into explicit retry lines.
- consumed: `api_agent._render_prompt()` includes those lines for the next source_generation API call.

## Issue Memory Decision Evidence

- issue memory decision evidence: no new issue-memory entry in this patch.
- reason: this is a prompt evidence propagation repair for an active live run; the generated-source mismatch itself should be tracked only if a later repair changes validation or generation behavior.

## Skill Decision Evidence

- skill used: `ctcp-workflow` and `ctcp-failure-bundle`.
- reason: this task changed repo code/tests under CTCP queue discipline and was driven by an existing failure evidence chain.
- no new skill created: the change is a narrow retry-evidence rendering repair.
- persona_lab_impact: none.
