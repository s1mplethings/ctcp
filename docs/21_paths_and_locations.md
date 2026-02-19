Paths and Locations (v0.1)
1. Runs Root

Runs MUST be stored outside repo.

Environment variable: CTCP_RUNS_ROOT

Default if unset:

Windows: %LOCALAPPDATA%\ctcp\runs

Linux: ~/.local/share/ctcp/runs

macOS: ~/Library/Application Support/ctcp/runs

2. Run Directory Layout

Run directory path pattern:
<CTCP_RUNS_ROOT>/<repo_slug>/<run_id>/

Must contain:

repo_ref.json

events.jsonl

artifacts/

reviews/

logs/

snapshot/

TRACE.md

failure_bundle.zip (only on failure)

3. Repo Pointers (only allowed run-related files inside repo)

Repo must contain:

meta/run_pointers/LAST_RUN.txt
Content: absolute path to the latest run directory.

Optional:

meta/run_pointers/LAST_BUNDLE.txt
Content: absolute path to latest failure bundle.

4. Repo Hygiene

The repo MUST NOT track:

build outputs (build*/, CMakeFiles/, Testing/, etc.)

run outputs (any run_dir, logs, snapshots)

SimLab runs inside repo

If violated, verify_repo MUST fail.
