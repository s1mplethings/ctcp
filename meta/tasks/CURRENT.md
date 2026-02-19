# Task - fail-bundle-and-fixer-loop-hard-regression

## Queue Binding
- Queue Item: `L2-FAIL-001`
- Layer/Priority: `L2 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context
- Complete the ADLC fail closure so verify failures always produce auditable evidence and can loop back to PASS in the same run.
- Keep contracts unchanged: resolver-first, `find_result.json` as final workflow decision input, and external `CTCP_RUNS_ROOT` run directories only.
- Scope this task to one queue item (`L2-FAIL-001`) and lock behavior with lite regressions.

## DoD Mapping (from execution_queue.json)
- [x] DoD-1: `verify fail writes FAIL report with failures[]`
- [x] DoD-2: `failure_bundle.zip has required minimum contents`
- [x] DoD-3: `fixer refill patch in same run can converge to VERIFY_PASSED and run pass`

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [ ] Research logged (if needed): N/A (repo-local orchestrator behavior)
- [x] Code changes allowed
- [x] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/spec sync first:
   - update artifact contract for verify report and failure bundle minimum.
2) Runtime hardening:
   - tighten orchestrator verify-fail path and fixer loop controls.
3) Regression lock:
   - keep S15/S16 behavior stable and fast under lite suite.
4) Verify and evidence:
   - run `sync_doc_links --check`, `simlab --suite lite`, `verify_repo`.
5) Report:
   - update `meta/reports/LAST.md` with demo pointers and command evidence.

## Notes / Decisions
- Current worktree is already dirty from prior tasks; this item only updates files tied to fail-loop closure and contract docs.

## Results
- `ctcp_orchestrate.py` now enforces hard fail evidence + fixer loop controls (iteration stop, verify_report paths, bundle validation, fixer outbox dispatch on fail).
- S15/S16 lite scenarios lock fail-bundle creation and fail->fix->pass closure.
- `docs/30_artifact_contracts.md` updated with final minimum contract fields/content lists.
- Verification and patch applyability checks passed.
