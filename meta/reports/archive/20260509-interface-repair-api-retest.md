# Demo Report - LAST

## Latest Report

- File: `meta/reports/archive/20260509-interface-repair-api-retest.md`
- Date: `2026-05-09`
- Topic: `Live API Retest After Interface Repair Loop Hardening`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-orchestrate-loop/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/00_CORE.md`
- `docs/03_quality_gates.md`
- `scripts/ctcp_orchestrate.py`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `meta/reports/LAST.md`
- external run `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\voice-assistant-interface-repair-api-20260509`

### Plan
1. Bind `ADHOC-20260509-interface-repair-api-retest`.
2. Run preflight metadata/protection checks.
3. Create a fresh external API run for the phone-to-PC voice assistant goal.
4. Advance the run with bounded API usage.
5. Inspect source_generation and provider evidence.
6. Record first blocker or delivery result, then close metadata.

### Changes
- Bound a no-code API retest task.
- Recorded regression issue memory `20260509_003`.
- No production code changes.
- No generated project source edits.

### Verify
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0, no violations.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0.
- PASS: `git diff --check` returned 0.
- FIRST FAILURE: `.venv\Scripts\python.exe scripts\workflow_checks.py` initially returned 1 because this report did not yet include triplet evidence lines. Minimal repair: add triplet command evidence and rerun workflow checks.
- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py new-run --run-id voice-assistant-interface-repair-api-20260509 --goal <voice assistant goal>` returned 0 in 0.602s.
- PASS: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py status --run-dir <run_dir>` returned 0; initial state was blocked waiting for `artifacts/analysis.md`.
- FIRST API TEST FAILURE: `.venv\Scripts\python.exe scripts\ctcp_orchestrate.py advance --run-dir <run_dir> --max-steps 12` timed out after 1204.604s. Minimal repair for this test task: stop residual advance processes and inspect emitted run artifacts instead of continuing API spend.
- PASS: residual process cleanup stopped two `advance` processes for this run.
- PASS: final `status --run-dir <run_dir>` returned 0; run remained blocked waiting for `artifacts/source_generation_report.json`.
- PASS: provider ledger inspection showed `critical_step_count=7`, `critical_api_step_count=7`, `fallback_count=0`, and `all_critical_steps_api=true`.
- PASS: API call inspection showed 7 `source_generation` calls, model `gpt-4.1`, status `OK`.
- PASS: generated project `py_compile` over runtime Python files returned 0.
- PASS: generated project `scripts/run_project_web.py --help` returned 0.
- FAIL: generated project `scripts/run_project_web.py --serve` returned 1 because `--serve` was not implemented.
- FAIL: generated project `scripts/run_project_web.py --headless --goal test --project-name readme --out <out>` returned 1 with `AttributeError: 'dict' object has no attribute 'strip'`.
- FAIL: generated project `python -m unittest discover -s tests -v` returned 1 with 4 tests run, 1 failure, and 3 errors.
- Pending: final metadata/triplet checks after report update.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0, 25 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0, 3 tests OK.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json` returned 0 after issue-memory/report update.
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py` returned 0 after report evidence update.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py` returned 0 after report evidence update.
- PASS: issue memory JSONL parse check returned 0.
- PASS: `Remove-Item Env:CTCP_FORCE_PROVIDER -ErrorAction SilentlyContinue; Remove-Item Env:CTCP_FORMAL_API_ONLY -ErrorAction SilentlyContinue; $env:CTCP_SKIP_LITE_REPLAY='1'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` returned 0. It ran code profile, CMake lite build/ctest, workflow/module/prompt/plan/patch/behavior/contract/doc/code-health/triplet gates, and 525 Python unit tests OK with 4 skipped. Lite replay was skipped by `CTCP_SKIP_LITE_REPLAY=1`.

### Questions
- None.

### Demo
- External run: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\voice-assistant-interface-repair-api-20260509`.
- Result: not deliverable.
- API/source evidence:
  - The run used `api_agent/gpt-4.1` for all critical completed steps and had no local fallback.
  - The run made 7 successful `source_generation` API calls but did not write `artifacts/source_generation_report.json`.
  - Partial source was generated under `project_output/readme`.
- Generated project smoke evidence:
  - Python syntax parsed.
  - CLI help worked.
  - Required `--serve` mode was missing.
  - Headless export failed.
  - Generated tests failed.

### Integration Proof
- connected: `ctcp_orchestrate.py` invoked API-backed planning, review, output contract, and source_generation calls.
- accumulated: run artifacts captured `provider_ledger_summary.json`, `api_calls.jsonl`, prompt/output logs, and partial generated project files.
- consumed: first blocker is recorded as upstream intent/spec collapse plus stale prompt leakage, not a local-template or manual-source issue.

### Issue Memory
- issue memory decision: required and recorded as `20260509_003`.

### First Failure And Repair
- first failure point evidence: the run timed out before `artifacts/source_generation_report.json`; the partial generated project was not runnable because `--serve` was missing, headless export failed on dict-vs-string command samples, and generated tests disagreed with service APIs.
- minimal fix strategy evidence: fix upstream project intent/spec shaping and stale domain-specific prompt leakage before another live API retry. Do not add local deterministic templates and do not manually patch generated output.

### Skill Decision
- skillized: yes, using `ctcp-orchestrate-loop` because this task drives `scripts/ctcp_orchestrate.py` state.
- persona_lab_impact: none.
- runtime wiring command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v` returned 0.
- issue memory command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v` returned 0.
- skill consumption command evidence: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v` returned 0.
