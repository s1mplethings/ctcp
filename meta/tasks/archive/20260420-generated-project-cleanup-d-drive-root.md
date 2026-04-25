# Task Archive - generated-project-cleanup-d-drive-root

- Archived on: `2026-04-20`
- Queue Item: `ADHOC-20260420-generated-project-cleanup-d-drive-root`
- Summary:
  - repo-local `generated_projects/` outputs were deleted
  - `%LOCALAPPDATA%\ctcp\runs` historical generated outputs were cleared down to the retained `ctcp` runtime-state container
  - `D:\ctcp_runs` was prepared as the default future CTCP runs root
  - persisted user env `CTCP_RUNS_ROOT=D:\ctcp_runs` was verified through `tools.run_paths.get_runs_root()`
- Verify snapshot:
  - main workspace `python scripts/workflow_checks.py` -> `0`
  - main workspace `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> first failure `module protection check` on unrelated pre-existing dirty files
  - isolated workspace `D:\.c_projects\adc\ctcp_cleanup_acceptance_20260420` `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` -> `0`
