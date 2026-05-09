# Task - Live Source Generation Retest After Signature Validation

## Queue Binding

- Queue Item: `ADHOC-20260508-source-signature-live-retest`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [ ] Code changes allowed

## Context

- Why this item now: user asked to continue after CTCP signature validation was implemented and verified. The next useful step is a real CTCP run, not manual project generation.
- Lane: Delivery Lane.
- Scope boundary: run a bounded live generation retest and record evidence. Do not patch production code or generated project source during this test.

## Task Truth Source

- task_purpose:
  - Create a fresh concrete phone-to-PC voice assistant generation run.
  - Advance it with bounded API usage.
  - Inspect whether `python_signature_consistency` appears in source_generation evidence and whether the run reaches delivery or a new blocker.
- allowed_behavior_change:
  - External run artifacts may be created under `CTCP_RUNS_ROOT`.
  - Repo metadata may record task/report/archive evidence.
- forbidden_goal_shift:
  - Do not manually create or repair the generated project.
  - Do not add local deterministic templates.
  - Do not modify provider credentials or endpoint configuration.
  - Do not change CTCP production code in this test task.
- in_scope_modules:
  - external run directory under `%TEMP%\ctcp_runs`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-source-signature-live-retest.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-source-signature-live-retest.md`
  - `issue_memory/modifications.jsonl` only if a repeated/new user-visible failure must be captured
- out_of_scope_modules:
  - production source files
  - generated project source files
  - provider credential files
  - local deterministic materializers/templates
- completion_evidence:
  - run id and run_dir recorded.
  - new-run/advance/status commands and return codes recorded.
  - source_generation/generic validation result recorded.
  - first blocker or delivery result recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-source-signature-live-retest.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-source-signature-live-retest.md`
  - `issue_memory/modifications.jsonl`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - production source files
  - generated project source files
  - local deterministic project templates/materializers
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no manual generated-source edits
  - no local project template fallback
  - no provider credential changes
- Acceptance Checks:
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id <run-id> --goal <goal>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps <bounded>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`

## Analysis / Find

- Test target:
  - phone opens a LAN/local web page served by the computer.
  - supports voice/text command entry.
  - computer executes whitelist-only commands.
  - generated delivery includes README, startup entrypoint, source files, tests, sample data, and verification evidence.
- API budget stance:
  - Use one bounded run.
  - Stop at the first clear blocker or delivery result.
  - Do not run repeated unbounded retries.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: fresh user-style project goal.
- current_module: `scripts/ctcp_orchestrate.py` external run mainline.
- downstream: run artifacts and source_generation validation reports.
- source_of_truth: run_dir artifacts and command return codes.
- fallback: if blocked, record first blocker and minimal next repair without patching generated output.
- acceptance_test:
  - orchestrator commands.
  - metadata closure checks.
- forbidden_bypass:
  - no manual generated source edits.
  - no local template fallback.
- user_visible_effect: user gets a CTCP-generated run result after the signature validation repair.

## DoD Mapping

- [x] DoD-1: Fresh external run created.
- [x] DoD-2: Run advanced with bounded API usage.
- [x] DoD-3: Status and source_generation evidence inspected.
- [x] DoD-4: First blocker or delivery result recorded.
- [x] DoD-5: Metadata closure checks pass.

## Check/Contrast/Fix Loop Evidence

- check:
  - Previous comparable run reached API source_generation but blocked on cross-file signature drift.
  - Current run should show whether signature-consistency validation produces clearer repair evidence or allows progress.
- contrast:
  - This task is a live CTCP pipeline test, not a production code patch.
  - API/provider success alone is not delivery success; generated artifacts must pass validation.
- fix:
  - If blocked, record the first blocker and minimal next repair.
  - Do not patch generated files manually during this task.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: orchestrator creates and advances the external run.
- accumulated: run_dir artifacts record provider/source_generation/status evidence.
- consumed: report turns those artifacts into a concrete next decision.

## Issue Memory Decision Evidence

- issue_memory_decision: required. The retest shows signature validation is connected, but API source_generation still does not converge after feedback and still emits cross-file interface drift.

## Plan

1. Bind the live retest task.
2. Create a fresh run under `%TEMP%\ctcp_runs`.
3. Advance with bounded `max-steps`.
4. Inspect status and `source_generation_report.json`.
5. Record result and first blocker or delivery evidence.
6. Run metadata closure checks and archive the task/report.

## Acceptance

- [x] DoD written.
- [x] Code changes disallowed for this test.
- [x] Run created.
- [x] Run advanced.
- [x] Result evidence recorded.
- [x] Metadata closure checks pass.

## Results

- Run ID: `voice-assistant-signature-retest-20260508`
- Run dir: `%TEMP%\ctcp_runs\ctcp\voice-assistant-signature-retest-20260508`
- `new-run`: exit 0, 0.699 seconds.
- First `status`: exit 0, blocked waiting for `artifacts/analysis.md`.
- `advance --max-steps 12`: exit 0, 286.579 seconds.
- Result after first advance: blocked at `artifacts/source_generation_report.json`, reason `generic_validation.passed must be true`.
- Generated files: 19; missing required files: 0.
- Validation result:
  - `generic_validation.passed=false`
  - `python_syntax.passed=true`
  - `python_import_consistency.passed=false`
  - `python_signature_consistency.passed=false`
  - `generated_tests.passed=false`
  - `smoke_run.passed=false`
  - `readme_quality.passed=true`
  - `domain_validation.passed=true`
  - `ux_validation.passed=false`
- Signature evidence:
  - `VoiceAssistantService(command_whitelist=...)` conflicts with `VoiceAssistantService(whitelist=...)`.
  - `run_server(host=...)` conflicts with `run_server(port=..., service_inst=..., blocking=...)`.
  - `CommandRequest(command=..., input_mode=...)` conflicts with `CommandRequest(command, args)`.
  - generated tests call `CommandRequest(command_text=...)` although the dataclass requires `command, args`.
- Generated tests also hit `NotImplementedError` because the generated service path calls an abstract `service_contract` method.
- One bounded retry was attempted with `advance --max-steps 1`; it timed out after 604.8 seconds. New API calls were recorded, but no newer `source_generation_report.json` was written. No generated files were manually edited.
- First blocker: source_generation still does not produce a deliverable generated project, but the new signature validation now exposes actionable caller/callee mismatch evidence.
- Minimal next repair: improve source_generation batch planning/self-repair so it consumes `python_signature_consistency` evidence before issuing more file batches, and block abstract-interface stubs that raise `NotImplementedError` from being used as runtime implementations.

## Notes / Decisions

- Default choice made: reuse the previous phone-to-PC voice assistant goal so this retest is comparable.
- Skill decision: skillized: no, this is a one-off orchestrator retest using the existing `ctcp-orchestrate-loop`.
- persona_lab_impact: none.
