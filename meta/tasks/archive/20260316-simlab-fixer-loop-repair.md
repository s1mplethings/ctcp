# Task Archive - 2026-03-16 - SimLab fixer-loop 回归修复（S15 / S16）

Queue Item: `ADHOC-20260316-simlab-fixer-loop-repair`
Status: `doing`

## Summary

- Scoped code-repair task for the current canonical verify blockers in SimLab lite replay.
- Focuses only on `S15_lite_fail_produces_bundle` and `S16_lite_fixer_loop_pass`.
- Keeps the change inside dispatcher/orchestrator runtime, the two SimLab README fixture patches, plus issue-memory/meta evidence.

## Scope

- `scripts/ctcp_dispatch.py`
- `scripts/ctcp_orchestrate.py`
- `tests/fixtures/patches/lite_fail_bad_readme_link.patch`
- `tests/fixtures/patches/lite_fix_remove_bad_readme_link.patch`
- `ai_context/problem_registry.md`
- queue/current/report archive pointers

## Key Constraints

- do not widen into unrelated support/scaffold/runtime cleanup
- do not weaken dirty-repo protection for genuine user changes
- do not bypass patch-first; repair the stale fixture inputs instead
- canonical `verify_repo.ps1` must still be executed and recorded

## Acceptance

- fixer prompt preserves `failure_bundle.zip` input for failed/rejected patch paths
- managed `LAST_BUNDLE.txt` drift no longer blocks fixer reapply
- stale README fixture patches re-enter the intended verify/fixer-loop paths
- issue memory records the recurring regression and repair
- task closes with canonical verify evidence
