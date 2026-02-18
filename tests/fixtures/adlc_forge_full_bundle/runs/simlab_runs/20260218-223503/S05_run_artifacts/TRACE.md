# SimLab Trace — S05_run_artifacts

- Name: verify run should keep report artifact sections available
- Started: 2026-02-18T22:35:17
- Sandbox: `D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-223503/S05_run_artifacts/sandbox`

## Steps

### Step 1 run
- cmd: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- cwd: `.`
- rc: `1`
- expect_exit: `0`

## Failure
- Reason: step 1: expect_exit mismatch, rc=1, expect=0

## Result
- status: fail
- error: step 1: expect_exit mismatch, rc=1, expect=0
