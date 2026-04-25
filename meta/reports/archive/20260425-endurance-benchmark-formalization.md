# Demo Report - LAST

## Latest Report

- File: `meta/reports/LAST.md`
- Date: `2026-04-25`
- Topic: `Endurance Benchmark Formalization`
- Mode: `formal benchmark entry + golden archive standardization`

### Readlist
- `AGENTS.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `ai_context/00_AI_CONTRACT.md`
- `docs/03_quality_gates.md`
- `docs/25_project_plan.md`
- `meta/tasks/CURRENT.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/ARCHIVE_INDEX.md`
- `scripts/formal_benchmark_runner.py`
- `scripts/run_formal_basic_benchmark.ps1`
- `scripts/run_formal_hq_benchmark.ps1`
- `docs/45_formal_benchmarks.md`
- `docs/46_benchmark_pass_contracts.md`
- `templates/benchmark_summary_template.json`
- existing formal benchmark goldens under `artifacts/benchmark_goldens/`
- external PASS endurance support/run artifacts under `%TEMP%\\ctcp_runs\\ctcp\\support_sessions\\indie-studio-endurance-sanitized-20260424` and `%TEMP%\\ctcp_runs\\ctcp\\20260424-200630-107859-orchestrate`

### Plan
1. Archive the previous package-name repair task/report and bind the endurance benchmark formalization task.
2. Extend the formal benchmark runner with an `endurance` profile, stable summary fields, and focused golden-copy rules.
3. Add the PowerShell endurance wrapper and update the benchmark docs/template.
4. Add focused runner tests.
5. Run the new endurance wrapper in summarize/archive-golden mode against the PASS run.
6. Run repo verification gates and record the final formalization verdict.

### Changes
- Archived the previous active task/report to:
  - `meta/tasks/archive/20260424-project-package-name-sanitization-repair.md`
  - `meta/reports/archive/20260424-project-package-name-sanitization-repair.md`
- Bound the new queue item:
  - `ADHOC-20260425-endurance-benchmark-formalization`
- Updated:
  - `meta/backlog/execution_queue.json`
  - `meta/tasks/ARCHIVE_INDEX.md`
  - `meta/tasks/CURRENT.md`
  - `meta/reports/LAST.md`
  - `scripts/formal_benchmark_runner.py`
  - `scripts/run_formal_endurance_benchmark.ps1`
  - `docs/45_formal_benchmarks.md`
  - `docs/46_benchmark_pass_contracts.md`
  - `templates/benchmark_summary_template.json`
  - `tests/test_formal_benchmark_runner.py`
- New golden archive:
  - `artifacts/benchmark_goldens/endurance_indie_studio_hub/`

### Formalization Summary

- Formal entry:
  - added `scripts/run_formal_endurance_benchmark.ps1`
  - extended `scripts/formal_benchmark_runner.py` with `endurance` profile support for `run`, `summarize`, and `archive-golden`
  - endurance summary now emits both JSON and Markdown:
    - `benchmark_endurance_summary.json`
    - `benchmark_endurance_summary.md`
- Summary surface:
  - prints `run_dir`, `support_session_dir`, `workflow_id`, `project_domain`, `project_type`, `project_archetype`, `package_name`
  - prints `internal_runtime_status`, `user_acceptance_status`, verify/delivery/replay state, and final/evidence bundle paths
- Golden archive:
  - preserves focused PASS artifacts only instead of copying the full run dir
  - includes:
    - `output_contract_freeze.json`
    - `source_generation_report.json`
    - `project_manifest.json`
    - `deliverable_index.json`
    - `support_public_delivery.json`
    - `verify_report.json`
    - `final_project_bundle.zip`
    - `intermediate_evidence_bundle.zip`
    - `api_calls.jsonl`
    - `formal_transcript.md`
    - `screenshots/*.png`
    - `benchmark_endurance_summary.json`
    - `benchmark_endurance_summary.md`
    - `golden_manifest.json`

### Verify
- PASS: `python -m unittest discover -s tests -p "test_formal_benchmark_runner.py" -v`
- PASS: `powershell -ExecutionPolicy Bypass -File scripts/run_formal_endurance_benchmark.ps1 -Mode summarize -RunDir C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate`
- PASS: `powershell -ExecutionPolicy Bypass -File scripts/run_formal_endurance_benchmark.ps1 -Mode archive-golden -RunDir C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate`
- PASS: `python scripts/module_protection_check.py`
- PASS: triplet runtime wiring command evidence via `$env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; python -m unittest discover -s tests -p "test_runtime_wiring_contract.py" -v`
- PASS: triplet issue memory command evidence via `python -m unittest discover -s tests -p "test_issue_memory_accumulation_contract.py" -v`
- PASS: triplet skill consumption command evidence via `python -m unittest discover -s tests -p "test_skill_consumption_contract.py" -v`
- PASS: `python scripts/workflow_checks.py`
- PASS: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile doc-only`
- first failure point:
  - `python scripts/workflow_checks.py` initially failed because `meta/reports/LAST.md` did not yet contain mandatory `first failure point`, `minimal fix strategy`, and triplet evidence lines for this task
- minimal fix strategy:
  - add the missing workflow evidence to `meta/reports/LAST.md`, run the three triplet regressions, then rerun `workflow_checks.py` and canonical doc-only verify

### Questions
- None.

### Demo
- Golden source run:
  - support session dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\support_sessions\indie-studio-endurance-sanitized-20260424`
  - run dir: `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate`
- summarize output:
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate\benchmark_endurance_summary.json`
  - `C:\Users\sunom\AppData\Local\Temp\ctcp_runs\ctcp\20260424-200630-107859-orchestrate\benchmark_endurance_summary.md`
- archive output:
  - `artifacts/benchmark_goldens/endurance_indie_studio_hub/`
- formalized verdict:
  - `workflow_id = wf_project_generation_manifest`
  - `project_domain = indie_studio_production_hub`
  - `project_type = indie_studio_hub`
  - `project_archetype = indie_studio_hub_web`
  - `package_name = project_5_20_bug`
  - `internal_runtime_status = PASS`
  - `user_acceptance_status = PASS`
  - `final_verdict = PASS`
