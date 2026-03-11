# Task - markdown-contract-drift-fix

## Queue Binding
- Queue Item: `L0-PLAN-001`
- Layer/Priority: `L0 / P0`
- Source Queue File: `meta/backlog/execution_queue.json`

## Context
- Goal: fix Markdown contract drift with contract-first, script-aligned rules.
- Scope:
  - unify verify naming and authority across core docs,
  - align headless mainline narrative and downgrade GUI to optional path,
  - normalize maintainable markdown structure for core contract docs,
  - repair doc index / contracts index coverage and queue-discipline linkage.
- Out of scope:
  - product behavior refactor,
  - runtime/orchestrator feature changes.

## DoD Mapping (from queue + current request)
- [x] DoD-1: verify entrypoint + verify artifact naming are unified and script-aligned across required docs.
- [x] DoD-2: README/00_CORE/02_workflow/12_modules_index share one headless-first mainline; GUI is optional path.
- [x] DoD-3: doc index and contracts index cover required key documents/artifacts.
- [x] DoD-4: project plan/task template/current binding removes `N/A` escape and forms queue-task-report closure.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A (repo-local contract sync)`
- [x] Code changes allowed: `N/A (docs/meta/scripts for doc index only)`
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [ ] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: unify verify contract + headless mainline narrative.
2) Update index contracts (`sync_doc_links.py`, README index block, contracts index).
3) Fix planning-discipline links across project plan/template/current/queue.
4) Run `python scripts/sync_doc_links.py --check` and `scripts/verify_repo.ps1`.
5) Record readlist/plan/changes/verify/demo in `meta/reports/LAST.md`.

## Notes / Decisions
- Canonical verify artifact is `artifacts/verify_report.json`; `proof.json` is downgraded to compatibility.
- `verify_repo.*` remains the only DoD gate entrypoint.
- Direct user request without queue item should be modeled as `ADHOC-YYYYMMDD-<slug>`, not `N/A`.
- Current verify status is blocked by environment/test failures outside this docs-only patch scope (recorded in `meta/reports/LAST.md`).

