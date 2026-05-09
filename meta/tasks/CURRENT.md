# Task - Source Generation Interface Repair Loop Hardening

## Queue Binding

- Queue Item: `ADHOC-20260509-source-generation-interface-repair-loop`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: live retest `voice-assistant-signature-retest-20260508` proved the new signature validator is connected, but source_generation still emitted incompatible batches and abstract runtime stubs.
- Lane: Delivery Lane.
- Scope boundary: harden generic validation and retry feedback for interface convergence. Do not add project-specific templates or manually repair generated output.

## Task Truth Source

- task_purpose:
  - Block generated runtime source that contains abstract `raise NotImplementedError` stubs.
  - Make signature-consistency mismatches mandatory self-repair input for source_generation retries.
  - Allow provider interface payloads to include a concrete signature matrix and validate that it agrees with generated code.
- allowed_behavior_change:
  - Generic validation may fail generated Python files containing runtime abstract stubs.
  - Retry prompt may include stronger signature-matrix and abstract-stub repair requirements.
  - Provider `interfaces` may include expected signatures for generated functions/classes.
- forbidden_goal_shift:
  - Do not add local deterministic project templates.
  - Do not manually patch any generated project output.
  - Do not change provider credentials or endpoint config.
  - Do not add voice-assistant-specific acceptance content.
- in_scope_modules:
  - `tools/providers/project_generation_signature_validation.py`
  - `tools/providers/project_generation_validation.py`
  - `ctcp_adapters/source_generation_prompt.py`
  - `tests/test_generated_project_signature_validation.py`
  - `issue_memory/modifications.jsonl`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260509-source-generation-interface-repair-loop.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-source-generation-interface-repair-loop.md`
- out_of_scope_modules:
  - provider credential files
  - generated project source files
  - local deterministic materializers/templates
  - unrelated support bot/runtime behavior
- completion_evidence:
  - focused tests cover abstract stub rejection.
  - focused tests cover signature-matrix mismatch detection and prompt feedback.
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
  - `meta/tasks/archive/20260509-source-generation-interface-repair-loop.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260509-source-generation-interface-repair-loop.md`
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
  - `.venv\Scripts\python.exe -m unittest tests.test_project_generation_artifacts -v`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`
  - `powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`

## Analysis / Find

- Reproduced evidence:
  - signature mismatch rows are present in `python_signature_consistency`.
  - generated tests fail on `CommandRequest(command_text=...)`.
  - generated service path calls an abstract method that raises `NotImplementedError`.
- Validation target:
  - static call-vs-definition mismatches.
  - provider-declared signature matrix mismatches.
  - abstract runtime stubs in generated Python files.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: provider source_generation JSON and previous failure report.
- current_module: generic validation and source_generation prompt rendering.
- downstream: `artifacts/source_generation_report.json` and next API retry.
- source_of_truth: generated Python files plus provider interface payload.
- fallback: skip uncertain dynamic inference, but block explicit abstract stubs and explicit signature contradictions.
- acceptance_test:
  - focused unit tests.
  - project generation artifact regression.
  - metadata/gate checks.
- forbidden_bypass:
  - no local generated-source patching.
  - no deterministic template fallback.
- user_visible_effect: CTCP should force API source_generation to repair interfaces before claiming delivery.

## DoD Mapping

- [x] DoD-1: Abstract `NotImplementedError` stub validation implemented.
- [x] DoD-2: Provider signature matrix validation implemented or accepted via existing interface payload.
- [x] DoD-3: Retry prompt includes mandatory signature-matrix repair guidance.
- [x] DoD-4: Focused and project-generation regression tests pass.
- [x] DoD-5: Canonical verification passes or first failure is recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Live retest showed the validator catches signature drift, but generation still repeats incompatible API surfaces.
- contrast:
  - Prompt-only broad instructions are insufficient when validation has structured mismatch rows.
  - The repair must connect generated validation evidence back into source_generation retry behavior.
- fix:
  - Add explicit abstract-stub validation.
  - Add explicit provider signature-matrix comparison.
  - Strengthen retry prompt to require repairing all signature rows before emitting new file batches.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: generic validation computes the new blockers.
- accumulated: source_generation report carries structured blocker rows.
- consumed: retry prompt renders those rows and repair requirements.

## Issue Memory Decision Evidence

- issue_memory_decision: required because this is a repair for recorded regression `20260509_001`.

## Plan

1. Bind the code repair task.
2. Extend signature/static validation for abstract stubs and optional provider signature matrix.
3. Strengthen source_generation retry prompt consumption.
4. Add focused regression tests.
5. Run focused and project-generation checks.
6. Run repo gates and archive evidence.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed for scoped repair.
- [x] Validator changes integrated.
- [x] Prompt changes integrated.
- [x] Tests pass.
- [x] Metadata closure checks pass.

## Results

- `python_signature_consistency` now includes:
  - `interface_signature_mismatches` for provider-declared `interfaces[path].signatures` that disagree with actual generated AST definitions.
  - `abstract_stub_violations` for generated runtime Python methods/functions that raise `NotImplementedError`.
- `generic_validation` passes the provider interface contract into signature validation.
- `source_generation` prompt now requires `interfaces[path].signatures`, forbids abstract runtime implementations, and renders `signature_matrix` plus `abstract_stub` failures as mandatory retry evidence.
- Focused/regression checks:
  - `.venv\Scripts\python.exe -m py_compile tools\providers\project_generation_signature_validation.py tools\providers\project_generation_validation.py ctcp_adapters\source_generation_prompt.py tests\test_generated_project_signature_validation.py`: PASS.
  - `.venv\Scripts\python.exe -m unittest tests.test_generated_project_signature_validation -v`: PASS, 5 tests OK.
  - `.venv\Scripts\python.exe -m unittest tests.test_generated_project_validation_self_repair -v`: PASS, 2 tests OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_api_agent_templates.py" -v`: PASS, 22 tests OK.
  - `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_project_generation_artifacts.py" -v`: PASS, 48 tests OK.
  - `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`: PASS, 525 Python tests OK, 4 skipped.

## Notes / Decisions

- Default choice made: keep checks generic and Python-AST based; no voice-assistant-specific content.
- Skill decision: skillized: no, this is a validator/prompt integration inside an existing workflow, not a reusable agent workflow.
- persona_lab_impact: none.
