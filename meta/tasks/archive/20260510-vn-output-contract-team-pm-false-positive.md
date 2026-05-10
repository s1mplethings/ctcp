# Task - VN Output Contract Team PM False Positive

## Queue Binding

- Queue Item: `ADHOC-20260510-vn-output-contract-team-pm-false-positive`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- Lane: `Delivery Lane`
- [x] Code changes allowed

## Context

- Why this item now: two customer-style VN generation runs used `api_agent` for all critical steps but could not proceed through `output_contract_freeze`.
- User request context: generate a VN project with story line, backgrounds, and character sprites without Codex manually writing generated project code.
- Primary run: `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b`.
- Live failure class repaired: provider VN output included ordinary background object wording such as `notice board` / `timetable board`; local normalization treated `board` as a Plane-lite/team PM signal and raised a freeze mismatch error.
- Second structural failure repaired: narrative VN output contract did not supply required non-empty structural lists such as `core_modules`, `required_outputs`, and `explicit_non_goals`.
- Current live run status after repair: advanced to `source_generation`, then blocked at `generic_validation.passed must be true`.

## Task Truth Source

- task_purpose:
  - Repair narrow output contract blockers so VN project-generation can advance past design/contract freeze.
  - Keep explicit Plane-lite/team task PM goals protected by the existing guard.
  - Retry the VN customer run after the fix without hand-writing generated project source.
- allowed_behavior_change:
  - output_contract_freeze team PM guard may ignore provider-generated full `project_spec` prose for hard request detection when the resolved domain is not team task management.
  - narrative VN output contracts may fill missing required structural spec lists from domain defaults.
- forbidden_goal_shift:
  - Do not weaken explicit team task PM benchmark/domain enforcement.
  - Do not hand-write or patch generated VN project source.
  - Do not replace API generation with local templates.
  - Do not weaken project-generation validation gates.
- in_scope_modules:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_narrative_spec.py`
  - `tests/test_project_generation_narrative_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260510-vn-output-contract-team-pm-false-positive.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260510-vn-output-contract-team-pm-false-positive.md`
  - external VN run retry evidence under `CTCP_RUNS_ROOT`
- out_of_scope_modules:
  - generated project source files
  - provider credentials
  - unrelated project-generation routing rules
  - frozen kernels
- completion_evidence:
  - focused narrative contract regressions pass.
  - Plane-lite regression suite still passes.
  - VN customer run retries past output_contract_freeze and records the next first blocker at source_generation.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_artifacts.py`
  - `tools/providers/project_generation_decisions.py`
  - `tools/providers/project_generation_narrative_spec.py`
  - `tests/test_project_generation_narrative_contract.py`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260510-vn-output-contract-team-pm-false-positive.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260510-vn-output-contract-team-pm-false-positive.md`
  - external VN run retry evidence under `CTCP_RUNS_ROOT`
- Protected Paths:
  - provider credentials
  - generated project source files
  - frozen kernels
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no generated-source manual patching.
  - no local template substitution for the VN run.
  - no Plane-lite/team PM guard removal.
- Acceptance Checks:
  - `.venv\Scripts\python.exe -m unittest tests.test_project_generation_narrative_contract -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_project_generation_artifacts.ProjectGenerationArtifactTests.test_output_contract_freeze_production_narrative_request_is_not_benchmark_default -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_plane_lite_benchmark_regression -v`
  - retry `scripts\ctcp_orchestrate.py advance` for the VN run.
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`

## Analysis / Find

- Break point 1:
  - `tools/providers/project_generation_artifacts.py::normalize_output_contract_freeze`.
  - `team_pm_requested` scanned provider-generated `project_spec` prose.
  - VN provider output included ordinary background text such as `notice board` and `timetable board`.
  - `TEAM_PM_KEYWORDS` includes broad token `board`, so narrative text triggered the Plane-lite/team PM guard.
- Break point 2:
  - `tools/providers/project_generation_decisions.py::enrich_project_spec`.
  - narrative VN branch returned before the generic/default structural fields were populated.
  - project-generation structural gate requires non-empty `core_modules`, `required_outputs`, `required_pages_or_views`, `data_models`, `key_interactions`, `export_targets`, `delivery_requirements`, and `explicit_non_goals`.
- Live run after repair:
  - `vn-project-generation-customer-20260510b` reached `source_generation_report.json`.
  - provider-authored source was applied with `generated_business_file_count=21`.
  - source customization completion passed.
  - generic validation failed on generated project import/interface/test/visual evidence issues.

## Integration Check

- upstream: API-authored `output_contract_freeze` payload for a VN customer run.
- current_module: output contract normalization and narrative spec enrichment.
- downstream: project-generation stage progression into source_generation.
- source_of_truth: user goal and resolved project domain/intent, not incidental generated asset prose.
- fallback: source_generation blocker is recorded for a later retry; generated source was not manually patched.
- acceptance_test: focused narrative contract regression, Plane-lite regression suite, VN run retry, workflow/module/patch/code-health checks.
- forbidden_bypass: explicit team PM enforcement remains; generated source is not hand-repaired.
- user_visible_effect: VN runs can pass output_contract_freeze and now fail at the real generated-source validation point.

## Plan

1. Bind this narrow Delivery Lane repair.
2. Add a regression for VN output containing `timetable board`.
3. Change the hard team PM guard signal to exclude full generated `project_spec` prose unless the resolved domain already indicates team PM.
4. Add narrative VN domain defaults for required structural spec lists.
5. Run focused regressions and Plane-lite regressions.
6. Retry the VN customer run without manual generated-source edits.
7. Record the next first blocker and gate evidence.

## Acceptance

- [x] Lane selected as Delivery Lane.
- [x] Queue item bound before implementation.
- [x] focused narrative contract regressions pass.
- [x] Plane-lite regression suite passes.
- [x] VN run retried without manual generated-source patching.
- [x] VN run advanced past output_contract_freeze.
- [x] next first blocker recorded at source_generation generic validation.
- [x] module/patch/code-health gates pass.
- [x] workflow gate passes.
- [x] canonical verify first failure recorded.

## Results

- Added `tools/providers/project_generation_narrative_spec.py` for narrative VN structural defaults.
- Updated `tools/providers/project_generation_artifacts.py` so the hard team-PM guard does not scan full provider-generated VN prose for broad tokens such as `board`.
- Updated `tools/providers/project_generation_decisions.py` to apply narrative VN structural defaults while keeping the oversized file growth guard clean.
- Added `tests/test_project_generation_narrative_contract.py` covering:
  - `timetable board` in VN asset text does not trigger team PM freeze enforcement.
  - narrative VN output contracts supply required structural lists.
- Retried `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b` through `source_generation`.
- Current run blocker:
  - `generic_validation.passed=false`.
  - generated tests fail with `StoryOutline.__init__() got an unexpected keyword argument 'synopsis'`.
  - import consistency reports missing `service`, `GameState`, and `CharacterState` symbols.
  - provider interface contract mismatches `__init__.py` and `story/__init__.py`.
  - UX validation fails because real visual evidence files and preview source page are missing.

## Command Evidence

- PASS: `.venv\Scripts\python.exe -m unittest tests.test_project_generation_narrative_contract -v` returned 0, 2 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_project_generation_artifacts.ProjectGenerationArtifactTests.test_output_contract_freeze_production_narrative_request_is_not_benchmark_default -v` returned 0, 1 test OK.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_plane_lite_benchmark_regression -v` returned 0, 16 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 with no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 1 because direct edits grew oversized `tests/test_project_generation_artifacts.py` and `tools/providers/project_generation_decisions.py`.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task` returned 0 after moving narrative defaults and tests to focused new files.
- triplet runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- triplet issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- triplet skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- RUN: `scripts\ctcp_orchestrate.py advance --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b --max-steps 20` reached `source_generation_report.json`; the shell command timed out at 30 minutes after writing source_generation evidence, and orphaned matching advance processes were stopped.
- STATUS: `scripts\ctcp_orchestrate.py status --run-dir D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b` reports `blocked: generic_validation.passed must be true`.
- FIRST FAILURE: `$env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 1 at `lite scenario replay`; prior gates passed, then replay reported 11 passed and 4 failed scenarios in `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-161139\summary.json`.
- SimLab first failure: `S13_lite_dispatch_outbox_on_missing_review`, step 6 expected `owner=Contract Guardian` in `artifacts/_dispatch_status.out.txt`.
- Failure bundle path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-161139\S13_lite_dispatch_outbox_on_missing_review\failure_bundle.zip`.
- Minimal next repair: inspect why the status rendering no longer emits the expected owner label for missing `review_contract.md`; keep it separate from the VN output-contract repair.

## Failure Bundle Evidence

- command: `$env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
- return code: `1`
- first failing gate: `lite scenario replay`
- first failing check: `S13_lite_dispatch_outbox_on_missing_review`, step 6 include assertion missing `owner=Contract Guardian`.
- evidence path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-161139\summary.json`.
- trace path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-161139\S13_lite_dispatch_outbox_on_missing_review\TRACE.md`.
- bundle path: `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-161139\S13_lite_dispatch_outbox_on_missing_review\failure_bundle.zip`.
- minimal fix strategy: repair the support/status owner text regression in a separate task; do not expand this VN output-contract patch.

## Check/Contrast/Fix Loop Evidence

- check: live VN run failed output_contract_freeze because broad team PM detection treated generated VN asset prose containing `board` as a Plane-lite/team PM request.
- contrast: explicit Plane-lite goals should still freeze as `team_task_management/team_task_pm/team_task_pm_web`, but resolved VN domain should remain `narrative_vn_editor/narrative_gui_editor/narrative_copilot`.
- fix: restricted hard team-PM detection to resolved domain plus user goal/intent, and added narrative VN defaults for required structural lists.
- re-check: focused narrative contract tests, production narrative contract test, Plane-lite regression suite, module protection, patch check, and code-health passed.
- live re-check: the VN run advanced past output_contract_freeze into source_generation and recorded the next real blocker.

## Completion Criteria Evidence

- completion criteria evidence: connected + accumulated + consumed.
- connected: `normalize_output_contract_freeze` consumes API-authored VN output and resolved project domain/intent.
- accumulated: narrative defaults are added to the output contract before structural gate evaluation.
- consumed: `vn-project-generation-customer-20260510b` consumed the repaired path and produced `artifacts/source_generation_report.json`.
- remaining blocker: generated project delivery is blocked by provider-authored source validation, not output_contract_freeze.

## Issue Memory Decision Evidence

- issue memory decision evidence: no issue-memory entry added in this patch.
- reason: this task is tied to the active live VN run evidence and remains captured in task/report archives; a broader recurring issue-memory entry should be created only if the source_generation validation failure is repaired as a separate task.

## Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: this changed repo code/tests and advanced an external CTCP generation run under queue discipline.
- no new skill created: the change is a narrow output-contract repair, not a reusable operator workflow.
- persona_lab_impact: none.
