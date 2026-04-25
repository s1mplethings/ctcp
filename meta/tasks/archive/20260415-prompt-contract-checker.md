# Task - prompt-contract-checker

## Archive Note

- This archive topic records the 2026-04-15 addition of a runnable prompt/contract checker for the Virtual Team Lane governance landing.
- The checker is scoped to the key markdown and prompt authorities requested by the user and is intended as the smallest closed loop before any broader verify integration.

## Closure Summary

- `scripts/prompt_contract_check.py` landed and the real repo passed all 32 configured checks.
- `tests/test_prompt_contract_check.py` landed and passed after one local fix-loop repair to the unittest entrypoint/module-loading path.
- Canonical `verify_repo.ps1 -Profile code` still failed first at `plan_check` because root `artifacts/PLAN.md` is missing in the current dirty worktree outside this task's scoped changes.
