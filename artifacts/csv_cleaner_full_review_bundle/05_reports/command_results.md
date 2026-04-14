# Command Results

- `python scripts/workflow_checks.py` -> `0` (pass)
- `python tests/support_virtual_delivery_e2e_runner.py --json-out artifacts/_virtual_delivery_e2e_check.json` -> `0` (pass)
- `python simlab/run.py --suite lite` -> `1` (fail)
  - summary: `passed=14`, `failed=1`
  - first failed scenario in summary: `S16_lite_fixer_loop_pass`
  - recorded error: `step 5: expect_exit mismatch, rc=1, expect=0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `1` (fail)
  - first failed gate: `lite scenario replay`
  - upstream cause: same SimLab lite failure (`S16_lite_fixer_loop_pass`)
