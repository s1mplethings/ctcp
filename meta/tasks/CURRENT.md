# Task - md-contract-and-plan-refresh

## Queue Binding
- Queue Item: `N/A (user-directed markdown refresh)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- User requested a full Markdown-only refresh of constraints and plan.
- Scope is documentation/contract/task/report artifacts only.
- No new code changes are introduced by this task.

## DoD Mapping (from execution_queue.json)
- [ ] DoD-1: `Constraint wording is updated in contract markdown`
- [ ] DoD-2: `PLAN markdown is rewritten/updated for current gate expectations`
- [ ] DoD-3: `verify_repo gate result is captured in report`

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): N/A (repo-local)
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: rewrite markdown constraints and plan files.
2) Keep implementation scope markdown-only (`*.md`) and avoid code edits.
3) Verify with `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`.
4) Record readlist/plan/changes/verify/demo in `meta/reports/LAST.md`.

## Notes / Decisions
- Use existing workflow gates and run only repository acceptance entrypoint.
- If gate fails, record first failure and the minimal markdown repair path.

## Results
- FAIL: `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (exit 1)
  - First failure: `lite scenario replay`
  - Replay summary: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260226-113619/summary.json` (`passed=7`, `failed=4`)
