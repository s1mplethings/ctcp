# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260510-vn-source-generation-retry-evidence.md`
- Date: `2026-05-10`
- Topic: `VN Source Generation Retry Evidence`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-failure-bundle/SKILL.md`
- `meta/tasks/CURRENT.md`
- `ctcp_adapters/source_generation_prompt.py`
- `tests/test_source_generation_prompt_leakage.py`
- `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b\TRACE.md`
- `D:\.c_projects\adc\ctcp_runs\ctcp\vn-project-generation-customer-20260510b\artifacts\source_generation_report.json`

### Plan
1. Read the live VN run records.
2. Identify the current first blocker after output_contract_freeze.
3. Add retry prompt evidence for the missing UX interaction details.
4. Run focused prompt tests and workflow gates.
5. Record the evidence chain and next retry condition.

### Changes
- Updated `ctcp_adapters/source_generation_prompt.py` to render `ux_validation.interaction_acceptance.reasons` as `ux_interaction` retry evidence.
- Added a focused VN retry prompt regression in `tests/test_source_generation_prompt_leakage.py`.
- Did not edit generated VN project source files.

### Verify
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

### Questions
- None.

### Demo
- Current finding: CTCP did generate provider-authored VN files, but source_generation validation blocked on cross-file API consistency and missing visual/interaction evidence.
- The next retry prompt now includes missing interaction controls, interaction trace, workspace snapshot, and export script evidence instead of only generic visual evidence wording.

### Integration Proof
- connected: blocked source_generation reports are read by `_previous_failure_lines`.
- accumulated: UX interaction acceptance reasons are converted into explicit retry lines.
- consumed: `api_agent._render_prompt()` includes those lines for the next source_generation API call.

### First Failure And Repair
- first failure point evidence: `source_generation_report.json` had concrete `interaction_acceptance.reasons` that were not rendered into the next retry prompt.
- minimal fix strategy evidence: add only retry evidence rendering and a focused prompt regression; do not patch generated source.

### Verify Failure Bundle
- command: `$env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`
- return code: timeout after 30 minutes.
- first failing/blocked gate: canonical verify did not return during `lite scenario replay`.
- evidence path: latest incomplete replay directory `D:\.c_projects\adc\ctcp_runs\ctcp\simlab_runs\20260510-194847`.
- minimal fix strategy: keep this task scoped to retry evidence; investigate replay duration/status-owner failures separately before claiming full canonical verify pass.

### Skill Decision
- skill used: `ctcp-workflow` and `ctcp-failure-bundle`.
- reason: this changed repo tests/code under queue discipline and used the live failure evidence chain.
- skillized: no.
- persona_lab_impact: none.
