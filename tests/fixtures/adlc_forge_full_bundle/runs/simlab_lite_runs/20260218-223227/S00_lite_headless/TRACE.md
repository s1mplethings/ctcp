# SimLab Trace — S00_lite_headless

- Name: lite headless sanity
- Started: 2026-02-18T22:32:29
- Sandbox: `D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_lite_runs/20260218-223227/S00_lite_headless/sandbox`

## Steps

### Step 1 run
- cmd: `python tools/ctcp_assistant.py init-task lite-headless --force`
- cwd: `.`
- rc: `0`
- expect_exit: `0`

### Step 2 expect_path
- path: `meta/tasks/CURRENT.md`
- exists: `True`

### Step 3 expect_text
- path: `meta/tasks/CURRENT.md`
- size: `614`

## Result
- status: pass
