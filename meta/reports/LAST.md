# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260508-voice-assistant-generation-speed-test.md`
- Date: `2026-05-08`
- Topic: `Voice Assistant Concrete Project Generation Speed Test`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-orchestrate-loop/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `scripts/ctcp_orchestrate.py`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`

### Plan
1. Bind `ADHOC-20260508-voice-assistant-generation-speed-test`.
2. Create `voice-assistant-speed-20260508`.
3. Advance the run with wall-time measurement.
4. Inspect final status and provider/source_generation evidence.
5. Record first blocker or delivery result.

### Changes
- Created external run `voice-assistant-speed-20260508`.
- Advanced the concrete generation chain and measured wall time.
- Inspected source_generation/provider evidence.
- Recorded repeated generated-source signature drift in issue memory.

### Verify
- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id voice-assistant-speed-20260508 --goal <voice assistant goal>` returned 0 in 0.603 seconds.
- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 16` returned 0 in 1278.028 seconds and blocked at source_generation validation.
- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>` returned 0 in 0.427 seconds.
- TIMEOUT: second `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 4` timed out after 604.069 seconds and was stopped to avoid unbounded API/time use.
- Provider evidence: `fallback_count=0`, `all_critical_steps_api=true`, `critical_api_step_count=17`, `source_generation_attempts=10`.
- Generated-project evidence: 29 generated files, no missing required files, `generic_validation.passed=false`, `readme_quality.passed=true`, `ux_validation.passed=false`.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.

### Questions
- None.

### Demo
- Run dir: `%TEMP%\ctcp_runs\ctcp\voice-assistant-speed-20260508`
- Result: not deliverable.
- First concrete blocker: startup/export fails because `VoiceAssistantService.__init__()` still needs `whitelist`, while generated tests fail because `CommandWhitelist.__init__()` does not accept `commands`.

### Integration Proof
- connected: orchestrator created and advanced the external run.
- accumulated: run artifacts include `source_generation_report.json`, `provider_ledger_summary.json`, generated project files, and validation traces.
- consumed: this report turns the run evidence into the next repair decision: source_generation still needs stronger cross-file API/signature consistency enforcement.

### Issue Memory
- issue memory decision: required because the run reproduced repeated API-authored cross-file signature drift after prior prompt and validator hardening.

### First Failure And Repair
- first failure point evidence: source_generation blocked at `generic_validation.passed must be true`.
- minimal fix strategy evidence: repair should target source_generation cross-file interface planning/validation, not local generated-source patching or local templates.

### Skill Decision
- skillized: no, this is a one-off orchestrator speed test using the existing `ctcp-orchestrate-loop`.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
