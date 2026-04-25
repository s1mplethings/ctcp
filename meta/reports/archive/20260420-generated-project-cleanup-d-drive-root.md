# Archive Report - generated project cleanup + D drive runs root

- Archived on: `2026-04-20`
- Topic: `generated project cleanup + D drive runs root`
- Final acceptance snapshot:
  - `generated_projects/` was emptied
  - `%LOCALAPPDATA%\ctcp\runs` historical generated outputs were removed while support/session/runtime state was preserved under `%LOCALAPPDATA%\ctcp\runs\ctcp`
  - `D:\ctcp_runs` became the persisted default runs root through `CTCP_RUNS_ROOT`
  - isolated acceptance verify passed in `D:\.c_projects\adc\ctcp_cleanup_acceptance_20260420`
