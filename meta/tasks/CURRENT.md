# Task - Voice Assistant Concrete Project Generation Speed Test

## Queue Binding

- Queue Item: `ADHOC-20260508-voice-assistant-generation-speed-test`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`
- [ ] Code changes allowed

## Context

- Why this item now: user asked to start a concrete project generation speed test after local librarian and generated-project self-repair improvements.
- Lane: Delivery Lane.
- Scope boundary: run and measure one concrete generated-project attempt; do not edit generated project source as proof.

## Task Truth Source

- task_purpose:
  - Run a fresh concrete phone-to-PC voice assistant generation.
  - Measure timing and final/blocking state.
  - Inspect provider/source_generation evidence.
- allowed_behavior_change:
  - Repo metadata may record task/report/archive evidence.
  - External run artifacts may be created under `CTCP_RUNS_ROOT`.
- forbidden_goal_shift:
  - Do not patch generated project source manually.
  - Do not add local deterministic project templates.
  - Do not change provider credentials or endpoint config.
  - Do not change production code during this test task.
- in_scope_modules:
  - external run directory under `%TEMP%\ctcp_runs`
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-voice-assistant-generation-speed-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-voice-assistant-generation-speed-test.md`
  - `issue_memory/modifications.jsonl`
- out_of_scope_modules:
  - production source files
  - provider credential files
  - generated project source edits
  - local deterministic materializers/templates
- completion_evidence:
  - run id and run_dir recorded.
  - new-run/advance/status timings recorded.
  - first blocker or delivery result recorded.
  - workflow checks pass or first failure recorded.

## Write Scope / Protection

- Allowed Write Paths:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/CURRENT.md`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/archive/20260508-voice-assistant-generation-speed-test.md`
  - `meta/reports/LAST.md`
  - `meta/reports/archive/20260508-voice-assistant-generation-speed-test.md`
  - `issue_memory/modifications.jsonl`
- Protected Paths:
  - provider credentials
  - Telegram token/env files
  - production source files
  - generated project source files
- Frozen Kernels Touched: `false`
- Explicit Elevation Required: `false`
- Explicit Elevation Signal: `none`
- Forbidden Bypass:
  - no local project template fallback
  - no generated-run source patching as proof
  - no provider credential changes
- Acceptance Checks:
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id voice-assistant-speed-20260508 --goal <voice assistant goal>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps <n>`
  - `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>`
  - `.venv\Scripts\python.exe scripts\workflow_checks.py`
  - `.venv\Scripts\python.exe scripts\module_protection_check.py --json`
  - `.venv\Scripts\python.exe scripts\patch_check.py`

## Analysis / Find

- Test target:
  - local computer starts a service.
  - phone opens a LAN web page.
  - supports voice or text command entry.
  - computer executes whitelist-only commands.
  - generated delivery includes README, startup entrypoint, core code, tests, sample data, and runnable verification evidence.
- Measurement plan:
  - record new-run wall time.
  - record advance wall time.
  - inspect status gate/path/reason.
  - inspect provider ledger/source_generation report when present.
- Repo-local search sufficient: yes.
- External research artifact: none.

## Integration Check

- upstream: user concrete project goal.
- current_module: `scripts/ctcp_orchestrate.py` external run mainline.
- downstream: run artifacts and provider/source_generation reports.
- source_of_truth: run_dir artifacts and command return codes.
- fallback: if run blocks, record first blocking gate and minimal next repair without patching generated source.
- acceptance_test:
  - orchestrator commands
  - workflow/module/patch checks for metadata closure
- forbidden_bypass:
  - no manual generated source edits
  - no local template fallback
- user_visible_effect: user gets a concrete speed/quality result for the current generation pipeline.

## DoD Mapping

- [x] DoD-1: Fresh external run created.
- [x] DoD-2: Run advanced with timing evidence.
- [x] DoD-3: Final status/first blocker recorded.
- [x] DoD-4: Provider/source_generation evidence inspected when available.
- [x] DoD-5: Metadata closure checks pass or first failure recorded.

## Check/Contrast/Fix Loop Evidence

- check:
  - Previous live run reached API source_generation but generated source blocked at runtime self-checks.
  - The current test should show whether the latest generic validation and librarian metadata improve the concrete run.
- contrast:
  - A speed test is not a production code change.
  - Successful API usage does not equal successful deliverable unless run artifacts show a runnable generated project.
- fix:
  - If blocked, record the first blocker and minimal next repair task.
  - Do not repair generated code locally inside this test.

## Completion Criteria Evidence

- completion criteria evidence: prove `connected + accumulated + consumed`.
- connected: orchestrator creates and advances the run.
- accumulated: run_dir artifacts record timing, provider, and generation evidence.
- consumed: report summarizes the evidence into the next repair/test decision.

## Issue Memory Decision Evidence

- issue_memory_decision: required because the test reproduced repeated API-authored cross-file signature drift after prior prompt and validator hardening.

## Plan

1. Bind the speed-test task.
2. Create `voice-assistant-speed-20260508` run under `%TEMP%\ctcp_runs`.
3. Advance the run with measured wall time.
4. Inspect status and source/provider evidence.
5. Record result, blocker, and minimal next action.
6. Run metadata closure checks and archive the task/report.

## Acceptance

- [x] DoD written.
- [x] Code changes disallowed for this test.
- [x] Run created.
- [x] Run advanced.
- [x] Timing/result evidence recorded.
- [x] Metadata closure checks pass.

## Notes / Decisions

- Default choice made: use the concrete voice-assistant goal from prior testing so results are comparable.
- Skill decision: skillized: no, this is a one-off orchestrator speed test using the existing `ctcp-orchestrate-loop`.
- persona_lab_impact: none.

## Results

- Run ID: `voice-assistant-speed-20260508`
- Run dir: `%TEMP%\ctcp_runs\ctcp\voice-assistant-speed-20260508`
- `new-run`: exit 0, 0.603 seconds.
- `advance --max-steps 16`: exit 0, 1278.028 seconds.
- `status`: exit 0, 0.427 seconds.
- First status: blocked at `artifacts/source_generation_report.json`, reason `generic_validation.passed must be true`.
- Extra `advance --max-steps 4`: timed out after 604.069 seconds and was stopped to avoid unbounded API/time use.
- Provider evidence: `fallback_count=0`, `all_critical_steps_api=true`, `critical_api_step_count=17`, `source_generation_attempts=10`.
- Generated files: 29; missing required files: none.
- Result: not deliverable; `generic_validation.passed=false`, `readme_quality.passed=true`, `ux_validation.passed=false`.
- First concrete blocker: API-authored cross-file constructor mismatch:
  - startup/export: `VoiceAssistantService.__init__() missing 1 required positional argument: 'whitelist'`
  - generated tests: `CommandWhitelist.__init__() got an unexpected keyword argument 'commands'`
