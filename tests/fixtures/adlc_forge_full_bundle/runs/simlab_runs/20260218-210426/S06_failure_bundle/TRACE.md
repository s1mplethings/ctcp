# SimLab Trace — S06_failure_bundle

- Name: failure should produce evidence bundle
- Started: 2026-02-18T21:04:40
- Sandbox: `D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-210426/S06_failure_bundle/sandbox`

## Steps

### Step 1 write
- path: `README.md`
- mode: `append`

## Failure
- Reason: bundle_on_nonzero: command exited 1

### Step 2 run
- cmd: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- cwd: `.`
- rc: `1`
- expect_exit: `nonzero`

### Step 3 expect_bundle
- path: `D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260218-210426/S06_failure_bundle/failure_bundle.zip`
- exists: `True`

## Result
- status: pass
