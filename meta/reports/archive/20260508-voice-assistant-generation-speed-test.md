# Report Archive - Voice Assistant Concrete Project Generation Speed Test

## Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-orchestrate-loop/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `scripts/ctcp_orchestrate.py`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`

## Plan

1. Bind `ADHOC-20260508-voice-assistant-generation-speed-test`.
2. Create `voice-assistant-speed-20260508`.
3. Advance the run with wall-time measurement.
4. Inspect final status and provider/source_generation evidence.
5. Record first blocker or delivery result.

## Changes

- Created external run `voice-assistant-speed-20260508`.
- Advanced the concrete generation chain and measured wall time.
- Inspected source_generation/provider evidence.
- Recorded repeated generated-source signature drift in issue memory.

## Verify

- `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id voice-assistant-speed-20260508 --goal <voice assistant goal>` -> exit 0, 0.603 seconds.
- `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 16` -> exit 0, 1278.028 seconds.
- `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>` -> exit 0, 0.427 seconds.
- second `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 4` -> timed out after 604.069 seconds and was stopped.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` -> exit 0, 25 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` -> exit 0, 3 tests OK.
- `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` -> exit 0, 3 tests OK.

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

## Questions

- None.

## Demo

Run dir:
- `%TEMP%\ctcp_runs\ctcp\voice-assistant-speed-20260508`

Result:
- not deliverable yet.

First concrete blocker:
- startup/export fails because `VoiceAssistantService.__init__()` still needs `whitelist`.
- generated tests fail because `CommandWhitelist.__init__()` does not accept `commands`.

## First Failure And Repair

- first failure point evidence: source_generation blocked at `generic_validation.passed must be true`.
- minimal fix strategy evidence: repair source_generation cross-file interface planning/validation, not local generated-source patching or local templates.

## Integration Proof

- connected: orchestrator created and advanced the external run.
- accumulated: run artifacts include `source_generation_report.json`, `provider_ledger_summary.json`, generated project files, and validation traces.
- consumed: this report turns the run evidence into the next repair decision.

## Issue Memory

- issue memory decision: required because the run reproduced repeated API-authored cross-file signature drift after prior prompt and validator hardening.
- issue memory record: `20260508_002`.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.

## Skill Decision

- skillized: no, this is a one-off orchestrator speed test using the existing `ctcp-orchestrate-loop`.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
