# Demo Report - prompt-contract-gate-integration

## Latest Report

- File: `meta/reports/archive/20260415-prompt-contract-gate-integration.md`
- Date: `2026-04-15`
- Topic: `Integrate the Virtual Team prompt-contract checker into verify_repo and quality gates`

### Readlist
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- `docs/03_quality_gates.md`
- `scripts/prompt_contract_check.py`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- user request to continue the checker work in finer-grained form

### Plan
1. Wire the prompt-contract checker into both verify entrypoints.
2. Update the quality-gates contract doc to name the new gate.
3. Run the checker, its tests, workflow checks, and canonical verify.
4. Record the first failing gate and minimal follow-up.

### Changes
- `scripts/verify_repo.ps1`
- `scripts/verify_repo.sh`
- `docs/03_quality_gates.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/ARCHIVE_INDEX.md`
- `meta/tasks/archive/20260415-prompt-contract-gate-integration.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260415-prompt-contract-gate-integration.md`

### Verify
- `python scripts/prompt_contract_check.py` -> `0`
- `python -m unittest discover -s tests -p "test_prompt_contract_check.py" -v` -> `0`
- `python scripts/workflow_checks.py` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `1`
- `bash scripts/verify_repo.sh --profile code` -> `1` (local WSL/bash environment failed before the script body)
- first failure point: `plan_check` failed because root `artifacts/PLAN.md` is missing in the current dirty worktree, but only after the new `prompt contract check` gate ran successfully in PowerShell verify
- minimal fix strategy: `restore or regenerate the required root plan artifacts (`artifacts/PLAN.md`, `artifacts/REASONS.md`, and `artifacts/EXPECTED_RESULTS.md` if they are intentionally part of the current verify surface), then rerun code-profile verify; for Unix runtime evidence on this machine, repair the local WSL/bash mount environment first`

### Questions
- None.

### Demo
- `scripts/verify_repo.ps1` now runs `prompt contract check` immediately after `workflow gate` and before `plan check`.
- `scripts/verify_repo.sh` was patched at the same gate position.
- `docs/03_quality_gates.md` now lists `python scripts/prompt_contract_check.py` in the verify sequence and gives the gate a named lint class with its authority surface.
- Real PowerShell verify output now shows the new gate running and passing before the preexisting `plan_check` failure.
- A real Unix verify attempt was made, but the local bash/WSL environment failed before entering the script, so Unix runtime evidence is environment-blocked rather than silently assumed.
