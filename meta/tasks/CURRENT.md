# Task - Project Generation Cross-File Interface Validation

## Queue Binding

- Queue Item: `ADHOC-20260508-source-generation-interface-validation`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: user clarified they want to test CTCP itself, not receive a manually created project. The latest real API-only generation reached source generation but failed on API-authored cross-file constructor/call signature drift.
- Lane: Delivery Lane.
- Scope boundary: improve CTCP generic source-generation validation and retry feedback so future generated projects are blocked and repaired on concrete interface mismatches. Do not add local project templates and do not manually patch generated output as proof.

## Task Truth Source

- task_purpose:
  - Detect generated Python cross-file constructor/function call signature drift before delivery.
  - Feed concrete mismatch evidence back into source_generation retries.
  - Add focused regression coverage for the repeated missing-argument and unexpected-keyword failures.
- allowed_behavior_change:
  - Generic generated-project validation may fail when generated Python call sites do not match generated definitions.
  - Source-generation retry prompt may include static signature mismatch evidence.
  - Tests and issue memory may be updated for this failure class.
- forbidden_goal_shift:
  - Do not add local deterministic project templates.
  - Do not manually generate or repair a concrete project as proof.
  - Do not change provider credentials or endpoint config.
  - Do not broaden into domain-specific VN or voice-assistant rules.
- in_scope_modules:
  - `tools/providers/project_generation_signature_validation.py`
  - `tools/providers/project_generation_validation.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_generated_project_signature_validation.py`
  - `issue_memory/modifications.jsonl`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - task/report archive files for this topic
  - `meta/backlog/execution_queue.json`
- out_of_scope_modules:
  - provider credential files
  - generated project source edits
  - local deterministic materializers/templates
  - unrelated support bot/runtime changes
- completion_evidence:
  - static validator reports missing required args and unexpected keywords for generated Python files.
  - source_generation retry prompt carries those exact mismatch details.
  - focused tests pass.
  - repo gates pass or first failure is recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `tools/providers/project_generation_signature_validation.py`
  - `tools/providers/project_generation_validation.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_generated_project_signature_validation.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-source-generation-interface-validation.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-source-generation-interface-validation.md`
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
  - `.venv\Scripts\python.exe -m unittest tests.test_generated_project_signature_validation -v`
  - `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Reproduced failure evidence:
  - `VoiceAssistantService.__init__() missing 1 required positional argument: 'whitelist'`.
  - `CommandWhitelist.__init__() got an unexpected keyword argument 'commands'`.
- Validation target:
  - generated Python class constructors and generated call sites in startup/business/test files.
  - missing required positional/keyword parameters.
  - unexpected keyword arguments.
  - too many positional arguments where no varargs exist.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: `tools/providers/project_generation_validation.py` generic validation.
- current_module: new static generated Python signature validator.
- downstream: `artifacts/source_generation_report.json` retry evidence and `ctcp_adapters/source_generation_prompt.py` self-repair prompt.
- source_of_truth: generated files in the run directory plus validation report.
- fallback: if static parsing cannot confidently check a call, skip that call rather than inventing a mismatch.
- acceptance_test:
  - focused unit tests
  - workflow/module/patch/code-health checks
- forbidden_bypass:
  - no manual generated source edits
  - no local template fallback
- user_visible_effect: future CTCP tests should fail with actionable API-authored interface mismatch evidence instead of opaque runtime TypeErrors.

## DoD Mapping

- [x] DoD-1: Static signature validator implemented and integrated.
- [x] DoD-2: Retry prompt consumes signature mismatch evidence.
- [x] DoD-3: Regression tests cover the repeated failure class.
- [x] DoD-4: Metadata/report/archive closure completed.
- [x] DoD-5: Canonical verification passes or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Previous live run reached API source_generation with no provider fallback, but generated source blocked at runtime self-checks.
- contrast:
  - This task changes CTCP validation and retry feedback, not the generated project itself.
  - Successful API usage still does not equal deliverable unless generated interfaces agree across files.
- fix:
  - Add generic static signature validation and make source_generation retries see the exact mismatch.
  - Do not add project-specific standards or hand-authored project content.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: generic validation calls the signature validator.
- accumulated: validation report carries caller/callee mismatch details.
- consumed: source-generation retry prompt includes those details.

## Issue Memory Decision Evidence

- issue_memory_decision: required because this is the concrete repair for recorded repeated API-authored cross-file signature drift.

## Plan

1. Bind the interface-validation repair task.
2. Inspect existing generated-project validation and retry prompt code.
3. Add a small AST-based generated Python signature validator.
4. Integrate validator output into generic validation pass/fail.
5. Add retry prompt consumption for concrete mismatch evidence.
6. Add focused regression tests.
7. Run focused checks and canonical verify.
8. Archive task/report and leave the repo clean.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed for scoped repair.
- [x] Static validator integrated.
- [x] Retry prompt evidence integrated.
- [x] Focused tests pass.
- [x] Metadata closure checks pass.

## Results

- Static validator added at `tools/providers/project_generation_signature_validation.py`.
- Generic validation now includes `python_signature_consistency` and fails delivery when direct generated call sites do not match direct generated definitions.
- Source-generation retry prompts now include `signature_consistency` lines with caller path, line, callee, target signature, missing required args, unexpected keywords, and positional mismatch notes.
- Regression coverage:
  - `.venv\Scripts\python.exe -m unittest tests.test_generated_project_signature_validation -v`: PASS, 3 tests OK.
  - `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v`: PASS, 2 tests OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`: PASS, 48 tests OK.
  - `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`: PASS, 523 Python tests OK, 4 skipped.

## Notes / Decisions

- Default choice made: validate generated Python calls statically with conservative AST checks; skip ambiguous calls instead of failing on uncertain inference.
- Skill decision: skillized: no, this is a validator extension inside the existing project-generation workflow, not a reusable agent workflow.
- persona_lab_impact: none.
