# SimLab Trace — S05_run_artifacts

- Name: verify run should keep report artifact sections available
- Started: 2026-02-19T13:12:37
- Sandbox: `D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260219-131220/S05_run_artifacts/sandbox`

## Steps

### Step 1 run
- cmd: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`
- cwd: `.`
- rc: `0`
- expect_exit: `0`

### Step 2 expect_path
- path: `meta/reports/LAST.md`
- exists: `True`

### Step 3 expect_text
- path: `meta/reports/LAST.md`
- size: `6715`

## Result
- status: pass
