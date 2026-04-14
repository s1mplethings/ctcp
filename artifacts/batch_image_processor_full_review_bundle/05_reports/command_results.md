# command_results.md

## Current Command Results
- `python scripts/workflow_checks.py` -> pass (`05_reports/workflow_checks.log`)
- `python scripts/smoke_test.py` in generated project -> pass (`05_reports/project_smoke.log`)
- `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json` -> pass (`05_reports/virtual_delivery_e2e.log`)
- `python simlab/run.py --suite lite` rerun -> pass (`05_reports/simlab_lite_rerun.log`, summary in `05_reports/simlab_lite_rerun_summary.json`)
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> pass (`05_reports/verify_repo.log`)

## Recorded Intermediate Failures
- Initial `python scripts/workflow_checks.py` after switching to the bundle task failed because `meta/tasks/CURRENT.md` missed the mandatory `Check / Contrast / Fix Loop Evidence` and `Completion Criteria Evidence` sections.
- Second `python scripts/workflow_checks.py` failed because `meta/reports/LAST.md` missed the mandatory triplet evidence entries.
- Initial `python simlab/run.py --suite lite` for the bundle task failed with:
  - `S00_lite_headless`: missing expected text `Code changes allowed`
  - `S16_lite_fixer_loop_pass`: `expect_exit mismatch, rc=1, expect=0`
- Those failures were resolved by restoring the exact `Code changes allowed` text in `CURRENT.md` and restoring the expected triplet workflow evidence in `LAST.md`.

## Delivery / Replay Status
- `support_public_delivery.json`: `errors == []`, `sent_types = [document, photo]`, `completion_gate.passed = true`
- `replay_report.json`: `startup_pass = true`, `minimal_flow_pass = true`, `overall_pass = true`
