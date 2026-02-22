# B011 patch-check-scope-from-plan

## Reason
- Patch scope gate that binds allow/deny policy to PLAN.

## Behavior
- Trigger: CLI execution of scripts/patch_check.py.
- Inputs / Outputs: git changed files + PLAN scope/budgets -> scope verdict.
- Invariants: Patch gate must fail when PLAN is missing or cannot be parsed.

## Result
- Acceptance: Exit code is non-zero for out-of-scope changes.
- Evidence: scripts/patch_check.py,artifacts/PLAN.md
- Related Gates: patch_check

