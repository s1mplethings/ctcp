# Task Archive - Voice Assistant Concrete Project Generation Speed Test

## Queue Binding

- Queue Item: `ADHOC-20260508-voice-assistant-generation-speed-test`
- Layer/Priority: `L1 / P0`
- Status: `done`
- Lane: Delivery Lane

## Scope

Run and measure one concrete generated-project attempt for a phone-to-PC voice assistant. This task did not patch generated project source and did not add local templates.

## Run

- Run ID: `voice-assistant-speed-20260508`
- Run dir: `%TEMP%\ctcp_runs\ctcp\voice-assistant-speed-20260508`
- Goal: phone connects to computer over LAN, web/voice or text command input, whitelist-only local command execution, README, startup entrypoint, core code, tests, sample data, and runnable verification.

## Results

- `new-run` -> exit 0, 0.603 seconds.
- `advance --max-steps 16` -> exit 0, 1278.028 seconds.
- `status` -> exit 0, 0.427 seconds.
- extra `advance --max-steps 4` -> timed out after 604.069 seconds and was stopped.
- Final status: blocked at `artifacts/source_generation_report.json`.
- Reason: `generic_validation.passed must be true`.

Provider evidence:
- `fallback_count=0`
- `all_critical_steps_api=true`
- `critical_api_step_count=17`
- `source_generation_attempts=10`

Generated-project evidence:
- generated files: 29
- missing required files: none
- `generic_validation.passed=false`
- `readme_quality.passed=true`
- `ux_validation.passed=false`

First concrete blocker:
- startup/export: `VoiceAssistantService.__init__() missing 1 required positional argument: 'whitelist'`
- generated tests: `CommandWhitelist.__init__() got an unexpected keyword argument 'commands'`

## Verify

- `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id voice-assistant-speed-20260508 --goal <voice assistant goal>` -> exit 0.
- `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 16` -> exit 0.
- `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>` -> exit 0.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> exit 0.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> exit 0.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> exit 0.

## First Failure And Repair

- first failure point evidence: source_generation blocked at `generic_validation.passed must be true`.
- minimal fix strategy evidence: repair source_generation cross-file interface planning/validation; do not patch generated source manually and do not reintroduce local templates.

## Integration Proof

- connected: orchestrator created and advanced the external run.
- accumulated: run artifacts include source_generation report, provider ledger, generated project files, and validation traces.
- consumed: report and issue memory convert the speed test into the next source_generation repair decision.

## Issue Memory

- issue memory decision: required because the run reproduced repeated API-authored cross-file signature drift after prior prompt and validator hardening.
- issue memory record: `20260508_002`.

## Skill Decision

- skillized: no, this is a one-off orchestrator speed test using the existing `ctcp-orchestrate-loop`.
