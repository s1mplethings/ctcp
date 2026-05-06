# Task Archive - Worktree Cleanliness Discipline

- Queue Item: `ADHOC-20260506-worktree-cleanliness-discipline`
- Date: `2026-05-06`
- Lane: Delivery Lane
- Status: `done`

## Scope

Add a non-destructive way to keep the repository clean:

- document daily worktree cleanliness rules in `docs/cleanup_policy.md`
- add a read-only advisory inventory command at `scripts/worktree_cleanliness_report.py`
- add focused unit tests for status parsing and action-bucket classification
- record the current dirty state and next cleanup order without reverting user or previous task changes

## Results

- The advisory command reports the current dirty worktree without modifying files.
- Current dirty total before grouped commits: `162`.
- Current dirty total after grouped commits: `0`.
- Bucket counts:
  - `source_or_test_change`: `68`
  - `docs_contract_or_workflow_change`: `22`
  - `task_report_archive`: `68`
  - `task_report_meta`: `4`
  - `runtime_or_generated_output`: `0`
- Cleanup action completed: source/test, docs/meta, reports, and task archives were grouped into commits; there were no repo-local runtime outputs to delete first.

## Verification

- `.venv\Scripts\python.exe -m py_compile scripts\worktree_cleanliness_report.py tests\test_worktree_cleanliness_report.py` -> exit 0
- `.venv\Scripts\python.exe -m unittest tests.test_worktree_cleanliness_report -v` -> exit 0, 4 tests OK
- `.venv\Scripts\python.exe scripts\worktree_cleanliness_report.py --json` -> exit 0, dirty total 160
- `.venv\Scripts\python.exe scripts\workflow_checks.py` -> exit 0
- `.venv\Scripts\python.exe scripts\module_protection_check.py --json` -> exit 0
- lane regressions:
  - `test_project_turn_mainline_contract.py` -> exit 0
  - `test_support_to_production_path.py` -> exit 0
  - `test_backend_interface_contract_apis.py` -> exit 0
- `.venv\Scripts\python.exe scripts\sync_doc_links.py --check` -> exit 0
- `git diff --check -- <task files>` -> exit 0, CRLF warnings only
- `$env:CTCP_FORCE_PROVIDER=$null; $env:CTCP_RUNS_ROOT = Join-Path $env:TEMP 'ctcp_runs'; powershell -ExecutionPolicy Bypass -File scripts\verify_repo.ps1 -Profile code` -> exit 0

## Skill Decision

- skillized: no, because this is a repo-local hygiene helper; existing `ctcp-workflow` remains the reusable workflow.
