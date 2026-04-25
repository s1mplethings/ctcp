# Archived Task - unified-mainline-run-manifest

- Queue Item: `ADHOC-20260421-unified-mainline-run-manifest`
- Status: `done`
- Archived On: `2026-04-21`
- Summary: unified librarian, ADLC, whiteboard, and frontend bridge into the default runtime mainline with `<run_dir>/artifacts/run_manifest.json` as the run-level truth source.
- Evidence:
  - `tests/integration/test_mainline_run_contract.py`
  - `docs/architecture/contracts/run_manifest_contract.md`
  - `tools/run_manifest.py`
  - isolated canonical verify in `D:\.c_projects\cqa` returned exit `0`.

