# Task - <topic>

## Queue Binding
- Queue Item: `<Lx-XXX-000>`
- Layer/Priority: `<Lx / Px>`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context
- Why are we doing this item now?
- Confirm all deps for the queue item are done (or explain blocker).

## DoD Mapping (from execution_queue.json)
- [ ] DoD-1: `<copy from queue item dod[0]>`
- [ ] DoD-2: `<copy from queue item dod[1]>`
- [ ] DoD-3: `<copy from queue item dod[2] or N/A>`

## Acceptance (must be checkable)
- [ ] DoD written (this file complete)
- [ ] Research logged (if needed): `meta/externals/YYYYMMDD-<topic>.md`
- [ ] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes
- [ ] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first
2) Implement (code only if allowed)
3) Verify (`sync_doc_links --check` + `verify_repo`)
4) Record (problem/decision logs if needed)
5) Demo (`LAST.md` + run trace pointer)

## Notes / Decisions
-

## Results
-
