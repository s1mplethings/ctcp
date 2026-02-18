# SimLab Trace — S00_lite_headless

- Name: lite headless sanity
- Started: 2026-02-18T22:21:05
- Sandbox: `D:/.c_projects/adc/ctcp/simlab/_runs/20260218-222104/S00_lite_headless/sandbox`

## Steps

### Step 1 run
- cmd: `python tools/ctcp_assistant.py init-task lite-headless --force`
- cwd: `.`
- rc: `1`
- expect_exit: `0`

## Failure
- Reason: step 1: expect_exit mismatch, rc=1, expect=0

## Result
- status: fail
- error: step 1: expect_exit mismatch, rc=1, expect=0
