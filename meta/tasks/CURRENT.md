# Task - Live Generated Project Test After Agent Interaction Source Repair

## Queue Binding

- Queue Item: `ADHOC-20260508-agent-interaction-live-generation-test`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [x] Code changes allowed

## Context

- Why this item now: the previous task strengthened source_generation agent handoff and the user asked to start testing.
- Lane: Delivery Lane.
- Scope boundary: run a fresh generated-project test and record evidence; do not change production source unless the test reveals a concrete repo-owned defect requiring a separate bound task.

## Task Truth Source

- task_purpose:
  - Prove whether the new source-generation handoff improves a real phone-to-PC voice assistant generated project.
  - Keep runtime/generated output outside the repo.
  - Minimize API usage while still allowing the formal generation path to reach source_generation or a concrete first blocker.
- allowed_behavior_change:
  - Metadata/report updates only.
- forbidden_goal_shift:
  - Do not edit generated project files as the proof.
  - Do not add local templates or deterministic project fallback.
  - Do not expose credentials, proxy details, or Telegram secrets.
  - Do not change production code in this test task.
- in_scope_modules:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-agent-interaction-live-generation-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-agent-interaction-live-generation-test.md`
- out_of_scope_modules:
  - `ctcp_adapters/source_generation_prompt.py`
  - `tools/providers/project_generation_source_stage.py`
  - Telegram/support bot runtime files
  - provider credential configuration
  - generated run directories inside the repo
- completion_evidence:
  - fresh run_dir path recorded.
  - orchestrator command trace and return codes recorded.
  - source_generation status or first blocker recorded.
  - generated-project concrete test matrix recorded when project files exist.

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-agent-interaction-live-generation-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-agent-interaction-live-generation-test.md`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - generated run directories under repo
  - local API/proxy secrets
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no local project template fallback
  - no generated-run source patching as proof
  - no validation relaxation
- Acceptance Checks:
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --goal <voice assistant goal>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps <n>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>`
  - generated project concrete runnable checks if source exists
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`

## Analysis / Find

- Skill decision: using `ctcp-orchestrate-loop` because this task drives `scripts/ctcp_orchestrate.py` state.
- Baseline: commit `db9b70a` passed canonical verify and left worktree clean.
- Test goal: phone connects to computer over LAN to control a voice assistant; local computer runs the service, phone uses browser/voice input, safe whitelist actions, README/startup/core code/test evidence required.
- API budget stance: set source-generation/output-contract attempts to 1 and retry delay to 0 to avoid repeated expensive calls; stop at first concrete blocker if API or validation blocks.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: fresh `new-run` goal intake.
- current_module: orchestrator run loop and generated-project runtime evidence.
- downstream: source_generation report and concrete generated-project runnable checks.
- source_of_truth: external run_dir artifacts and this report.
- fallback: if source_generation does not produce a project, record first blocker and stop.
- acceptance_test:
  - orchestrator status/advance trace
  - generated-project smoke matrix when source exists
- forbidden_bypass:
  - no generated-project manual patching
  - no local template fallback
  - no dependency installation bypass
- user_visible_effect: the user gets a concrete pass/fail result for the generated voice-assistant project and a bounded next repair item instead of an ambiguous "still testing" status.

## DoD Mapping

- [x] DoD-1: Fresh external run created.
- [x] DoD-2: Run advanced to source_generation pass or first concrete blocker.
- [x] DoD-3: Generated project concrete runnable test matrix recorded when source exists.

## Check/Contrast/Fix Loop Evidence

- check:
  - Fresh run `voice-assistant-phone-pc-live-20260508` reached source_generation with provider-authored API source.
  - Concrete generated-project matrix failed at CLI help, README serve, headless export, generated unittest, direct service construction, and HTTP endpoint probe.
- contrast:
  - Improved from previous run: README quality passed and bare `No module named 'service'` import failure is gone.
  - Still failing: `VoiceAssistantService.__init__()` requires `whitelist` while app imports construct it without arguments; generated tests import `src.readme` incorrectly; web endpoints never become reachable.
- fix:
  - This task is test-only; follow-up backlog item `ADHOC-20260508-generated-project-signature-test-validation` records the next repair target.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: fresh run reached orchestrator source_generation and produced `artifacts/source_generation_report.json`.
- accumulated: this report captures provider evidence, first blocker, and generated-project test matrix.
- consumed: follow-up repair item `ADHOC-20260508-generated-project-signature-test-validation` was created for constructor/test-import validation hardening.

## Issue Memory Decision Evidence

- issue_memory_decision: not required at task start because this task is a live regression test, not a repair. If the test exposes a new or repeated user-visible failure class, record it in the report and bind a follow-up repair task that updates issue memory.

## Plan

1. Bind this live generation test task.
2. Create a fresh external run for the voice-assistant goal.
3. Advance with minimal API attempts until source_generation passes or blocks.
4. Inspect provider/source_generation evidence.
5. If files exist, run concrete generated-project tests.
6. Update report/archive and leave worktree clean if possible.

## Acceptance

- [x] DoD written.
- [x] Code changes allowed for metadata only.
- [x] Fresh run created.
- [x] Orchestrator evidence recorded.
- [x] Generated project tested or first blocker recorded.
- [ ] Workflow/metadata checks pass.

## Notes / Decisions

- Default choice made: use the same phone-to-PC voice assistant goal to make the before/after comparison meaningful.
- Skill decision: skillized: no, because this is a one-off live regression run using the existing `ctcp-orchestrate-loop` skill.
- persona_lab_impact: none.

## Results

- Run ID: `voice-assistant-phone-pc-live-20260508`
- Run dir: `%TEMP%\ctcp_runs\ctcp\voice-assistant-phone-pc-live-20260508`
- Orchestrator result:
  - `new-run` exit 0.
  - `advance --max-steps 12` timed out after 20 minutes, but the run had reached source_generation and written reports.
  - `status` exit 0: blocked at `artifacts/source_generation_report.json`, reason `generic_validation.passed must be true`.
- Provider evidence:
  - `fallback_count=0`
  - `all_critical_steps_api=true`
  - `critical_api_step_count=10`
  - source_generation executed by `api_agent` three times.
- Source_generation report:
  - `status=blocked`
  - `project_root=project_output/readme`
  - `project_id=readme`
  - `package_name=readme`
  - `readme_quality.passed=true`
  - `generic_validation.passed=false`
  - `ux_validation.passed=false`
- Concrete generated-project test matrix:
  - file list: pass
  - Python syntax compile: pass
  - CLI `--help`: fail
  - README `--serve` entry: fail
  - headless export: fail
  - generated unittest: fail
  - direct service construction: fail
  - HTTP `/` and `/status` probe: fail
- First generated-project blocker:
  - `TypeError: VoiceAssistantService.__init__() missing 1 required positional argument: 'whitelist'`
  - generated test import also fails with `ModuleNotFoundError: No module named 'src.readme'`

## Closure

- closed_report: `meta/reports/archive/20260508-agent-interaction-live-generation-test.md`
- follow_up: `ADHOC-20260508-generated-project-signature-test-validation`
