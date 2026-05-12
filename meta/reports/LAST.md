# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-05-12`
- Topic: `Pre-Source Analysis Timeout Repair`

### Readlist

- `AGENTS.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `meta/tasks/CURRENT.md`
- `ctcp_adapters/dispatch_request_mapper.py`
- `llm_core/providers/api_provider.py`
- `tools/analysis_stage_progress.py`
- `scripts/ctcp_orchestrate.py`
- `tests/concrete_project_benchmark/run_concrete_project_benchmark.py`

### Plan

1. Locate the `analysis.md` generation call chain from `new-run` through provider execution and artifact write.
2. Add analysis-stage progress artifacts and status output.
3. Add analysis provider timeout containment with process-tree kill on Windows.
4. Preserve raw provider output and normalized partial output when available.
5. Add resume from `analysis.raw.txt` before recalling the provider.
6. Add benchmark analysis evidence and focused tests.

### Changes

- Added `tools/analysis_stage_progress.py` for `analysis_progress.json`, raw/partial artifact paths, progress updates, and status formatting.
- Updated `llm_core/providers/api_provider.py` to trace analysis provider/parser/write phases, enforce `CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS` default `90`, kill timed-out provider process trees, avoid duplicate plan+agent provider calls for `analysis.md`, preserve raw/partial output, and resume from raw output.
- Updated `scripts/ctcp_orchestrate.py` status output to show analysis progress.
- Updated `tests/concrete_project_benchmark/run_concrete_project_benchmark.py` and generated report/summary to include analysis progress, timeout reason, provider model, raw/partial existence, and resume possibility.
- Added focused tests: `tests/test_analysis_stage_progress.py`, `tests/test_analysis_stage_timeout.py`, `tests/test_analysis_stage_resume.py`.
- Updated existing provider fallback tests to assert the new rule: failed analysis provider calls do not synthesize fake `analysis.md`.

### Verify

- PASS: `.venv\Scripts\python.exe tests\concrete_project_benchmark\run_concrete_project_benchmark.py`.
  - Status: `failed`, structured.
  - Elapsed: `92.645s`.
  - timeout_step: none.
  - Failed stage: `analysis`.
  - Reason: `analysis_provider_timeout`.
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_analysis_stage_progress -v` (`4` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_analysis_stage_timeout -v` (`2` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_analysis_stage_resume -v` (`3` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_generation_consistency -v` (`4` tests).
- PASS: `.venv\Scripts\python.exe -m unittest tests.test_convergence_performance_guards -v` (`6` tests).
- PASS: `.venv\Scripts\python.exe -m unittest discover tests -v` (`643` tests, `4` skipped).
- PASS: `.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v` (`643` tests, `4` skipped).
- PASS: `.venv\Scripts\python.exe scripts\workflow_checks.py`.
- PASS: `.venv\Scripts\python.exe scripts\module_protection_check.py --json`.
- PASS: `.venv\Scripts\python.exe scripts\patch_check.py`.
- PASS: `.venv\Scripts\python.exe scripts\code_health_check.py --enforce --changed-only --baseline-ref HEAD --scope-current-task`.
- PASS: `$env:CTCP_SKIP_LITE_REPLAY='1'; $env:CTCP_RUNS_ROOT='D:\.c_projects\adc\ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code`.

### Questions

- None.

### Demo

- Benchmark report: `tests/concrete_project_benchmark/benchmark_report.md`.
- Benchmark summary: `tests/concrete_project_benchmark/generated/issue_tracker_api/benchmark_summary.json`.
- Latest benchmark step timings:
  - `discovery`: `0.319s`, passed.
  - `new_run`: `0.566s`, passed.
  - `status_before_generation`: `0.344s`, passed.
  - `advance_1`: `91.087s`, passed command with structured analysis failure.
  - `status_after_advance`: `0.315s`, passed.
  - `generated_project_discovery`: `0.003s`, failed.
  - `report_write`: `0.005s`, passed.
- Analysis progress:
  - target: `artifacts/analysis.md`
  - progress artifact: `artifacts/analysis_progress.json`
  - status: `timeout`
  - last_event: `provider_call_timeout`
  - provider_model: `gpt-4.1-mini`
  - provider_timeout_seconds: `90`
  - raw_exists: `false`
  - partial_exists: `false`
  - resume_possible: `false`

### Call Chain

`new-run -> advance -> current_gate -> waiting artifacts/analysis.md -> dispatch_request_mapper role=chair action=plan_draft target=artifacts/analysis.md -> ctcp_dispatch.dispatch_once -> llm_core.dispatch.router -> llm_core.providers.api_provider.execute -> provider command -> normalize_target_payload(_normalize_analysis_md) -> artifact write`

### First Failure And Repair

- first failure repaired: benchmark no longer times out at `advance_1`.
- repair: analysis provider calls now have a bounded stage timeout and write structured progress before the provider call.
- current benchmark result: structured `failed` at analysis due provider timeout, not a runner timeout.
- minimal fix strategy: keep analysis bounded and observable first; next repair should target analysis prompt/provider latency or model behavior without widening benchmark timeout or faking `analysis.md`.
- generated project: not produced in the latest run because analysis timed out before source generation.
- HTTP API tests and SQLite validation: not reached in the latest run because project generation did not start.

### Repo Verification

```json
{
  "repo_verification": {
    "status": "passed",
    "reason": "verify_repo.ps1 -Profile code passed",
    "introduced_by_current_task": true
  }
}
```

### Issue Memory Decision Evidence

- issue memory decision evidence: no new issue-memory entry.
- reason: the current first failure is a bounded provider timeout with structured evidence, not an unclassified recurring production defect.

### Skill Decision Evidence

- skill used: `ctcp-workflow`.
- reason: Phase 6.2 required queue binding, scoped implementation, verification, and auditable report evidence.
- skillized: no.
- triplet runtime wiring command evidence: covered by full unittest discovery including `test_runtime_wiring_contract.py`.
- triplet issue memory command evidence: covered by full unittest discovery including `test_issue_memory_accumulation_contract.py`.
- triplet skill consumption command evidence: covered by full unittest discovery including `test_skill_consumption_contract.py`.
