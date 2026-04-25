# Archived Report - Unified default mainline run_manifest

- Date: `2026-04-21`
- Topic: `Unified default mainline run_manifest`
- Result: `done`
- Summary: `docs/02_workflow.md` now defines the default mainline, runtime write points update `artifacts/run_manifest.json`, and the focused integration test proves same-run co-presence of librarian, ADLC, whiteboard, bridge, final status, and first failure.
- Key Verify:
  - `python -m unittest discover -s tests/integration -p "test_mainline_run_contract.py" -v` => `0`
  - `python scripts/workflow_checks.py` => `0`
  - isolated `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` in `D:\.c_projects\cqa` => `0`

