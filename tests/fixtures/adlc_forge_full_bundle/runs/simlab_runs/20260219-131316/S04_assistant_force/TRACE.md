# SimLab Trace — S04_assistant_force

- Name: assistant commands accept --force
- Started: 2026-02-19T13:13:30
- Sandbox: `D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260219-131316/S04_assistant_force/sandbox`

## Steps

### Step 1 run
- cmd: `python tools/ctcp_assistant.py init-task simlab-force --force`
- cwd: `.`
- rc: `0`
- expect_exit: `0`

### Step 2 run
- cmd: `python tools/ctcp_assistant.py init-externals simlab-force --force`
- cwd: `.`
- rc: `0`
- expect_exit: `0`

### Step 3 expect_path
- path: `meta/tasks/CURRENT.md`
- exists: `True`

## Result
- status: pass
