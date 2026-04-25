# Demo Report - prompt-contract-checker

## Latest Report

- File: `meta/reports/archive/20260415-prompt-contract-checker.md`
- Date: `2026-04-15`
- Topic: `Add a runnable prompt/contract checker for the Virtual Team Lane governance landing`

### Readlist
- `AGENTS.md`
- `ai_context/00_AI_CONTRACT.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`
- `docs/03_quality_gates.md`
- `PATCH_README.md`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `scripts/workflow_checks.py`
- `tests/test_workflow_checks.py`
- user request describing the required checker scope and run-log output

### Plan
1. Bind a new queue item for the Virtual Team Lane prompt/contract checker.
2. Implement a minimal checker script with declarative required/forbidden markers.
3. Add unit tests for a passing repository case and explicit failing fixtures.
4. Run the checker, its tests, workflow checks, and canonical verify.
5. Record exact commands, outputs, and the first failing gate if any.

### Changes
- `scripts/prompt_contract_check.py`
- `tests/test_prompt_contract_check.py`
- `meta/backlog/execution_queue.json`
- `meta/tasks/CURRENT.md`
- `meta/tasks/ARCHIVE_INDEX.md`
- `meta/tasks/archive/20260415-prompt-contract-checker.md`
- `meta/reports/LAST.md`
- `meta/reports/archive/20260415-prompt-contract-checker.md`

### Verify
- `python scripts/prompt_contract_check.py` -> `0`
- `python -m unittest tests.test_prompt_contract_check -v` -> `1` (initial command used non-package import path; fixed in the local check/fix loop)
- `python -m unittest discover -s tests -p "test_prompt_contract_check.py" -v` -> `0`
- `python scripts/workflow_checks.py` -> `0`
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1 -Profile code` -> `1`
- first failure point: `plan_check` failed because root `artifacts/PLAN.md` is missing in the current dirty worktree
- minimal fix strategy: `restore or regenerate the required root plan artifacts (`artifacts/PLAN.md`, `artifacts/REASONS.md`, and `artifacts/EXPECTED_RESULTS.md` if they are intentionally part of the current verify surface), then rerun code-profile verify without changing this task's checker/test patch`

### Questions
- None.

### Demo
- `scripts/prompt_contract_check.py` now validates 32 Virtual Team Lane governance markers across the key md/prompt authorities.
- The current repo passes the checker with `passed=32` and `failed=0`.
- `tests/test_prompt_contract_check.py` covers a real-repo pass case plus two explicit failing cases: missing `docs/12_virtual_team_contract.md` and the forbidden `patch-first coding agent` phrase.
- The local fix loop corrected the unit-test entrypoint from a non-package module import to the repo-standard `unittest discover` command and registered the dynamically loaded module safely.
