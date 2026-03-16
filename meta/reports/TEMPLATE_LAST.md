# Demo Report - LAST

## Latest Report

- File: [`meta/reports/archive/YYYYMMDD-<topic>.md`](archive/YYYYMMDD-<topic>.md)
- Date: `YYYY-MM-DD`
- Topic: `<one line>`

### Readlist
- `<one file per line>`

### Plan
1) `<one step per line>`
2) `<one step per line>`
3) `<one step per line>`

### Changes
- `<one file per line>`

### Verify
- `<command>` -> `<exit code>`
- first failure point: `<PASS or first failure>`
- minimal fix strategy: `<one line>`

### Questions
- None.

### Demo
- verify summary: `meta/run_pointers/LAST_RUN.txt` or external run summary path
- trace: `${CTCP_RUNS_ROOT:-~/.ctcp/runs}/<repo_slug>/<run_id>/TRACE.md`

### Integration Proof
- upstream: `<one line>`
- current_module: `<one line>`
- downstream: `<one line>`
- source_of_truth: `<one line>`
- fallback: `<one line>`
- acceptance_test:
  - `<one command per line>`
- forbidden_bypass:
  - `<one line per bypass>`
- user_visible_effect: `<one line>`
