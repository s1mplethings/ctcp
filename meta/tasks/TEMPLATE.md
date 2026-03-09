# Task - <topic>

## Queue Binding

- Queue Item: `<Lx-XXX-000 | ADHOC-YYYYMMDD-<slug>>`
- Layer/Priority: `<Lx / Px>`
- Source Queue File: `meta/backlog/execution_queue.json`

Hard rule:
- `Queue Item: N/A` is invalid.
- If user request has no existing queue item, create `ADHOC-YYYYMMDD-<slug>` in `execution_queue.json` first, then bind here.

## Context

- Why this item now?
- Dependency check: list required `deps` and their status (`done` / `blocked`).
- Scope boundary: what is explicitly out-of-scope in this patch?

## DoD Mapping (from execution_queue.json)

- [ ] DoD-1: `<copy from queue item dod[0]>`
- [ ] DoD-2: `<copy from queue item dod[1]>`
- [ ] DoD-3: `<copy from queue item dod[2] or write "Not Applicable: <reason>">`

## Acceptance (must be checkable)

- [ ] DoD written (this file complete)
- [ ] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [ ] Code changes allowed (or explicitly "Docs-only, no code dirs touched")
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes (or first failure + minimal fix recorded)
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan

1) Docs/Spec first.
2) Implement minimal scoped changes.
3) Verify (`python scripts/sync_doc_links.py --check` + `scripts/verify_repo.*`).
4) Record decisions/problems if exceptions occurred.
5) Demo pointers (`meta/reports/LAST.md` + `meta/run_pointers/LAST_RUN.txt` when available).

## Notes / Decisions

- Default choices made:
- Alternatives considered:
- Any contract exception reference (must also log in `ai_context/decision_log.md`):

## Results

- Files changed:
- Verification summary:
- Queue status update suggestion (`todo/doing/done/blocked`):

## Minimal Example

- Queue Item: `L0-PLAN-001`
- Layer/Priority: `L0 / P0`
- Context: "Unify verify naming across docs and scripts; no product code changes."
- DoD-1: "README/doc index and contracts index aligned."
- Verify: "`python scripts/sync_doc_links.py --check` pass, `scripts/verify_repo.ps1` pass."
