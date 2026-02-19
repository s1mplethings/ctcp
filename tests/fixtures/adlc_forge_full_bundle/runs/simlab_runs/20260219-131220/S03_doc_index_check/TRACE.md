# SimLab Trace — S03_doc_index_check

- Name: doc index check should pass and markers must exist
- Started: 2026-02-19T13:12:32
- Sandbox: `D:/.c_projects/adc/ctcp/tests/fixtures/adlc_forge_full_bundle/runs/simlab_runs/20260219-131220/S03_doc_index_check/sandbox`

## Steps

### Step 1 run
- cmd: `python scripts/sync_doc_links.py --check`
- cwd: `.`
- rc: `0`
- expect_exit: `0`

### Step 2 expect_text
- path: `README.md`
- size: `3167`

## Result
- status: pass
