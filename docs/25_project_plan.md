# Project Plan (Foundation-First)

This document defines the project-level execution model for CTCP.
Authoritative contract precedence remains:
`docs/00_CORE.md` > other docs.

## Three Planning Scopes

1. Project queue (long-horizon): `meta/backlog/execution_queue.json`
- Single source of truth for layered roadmap (`L0`..`L4`), dependencies, status, and DoD.
- Used to choose what should be worked on next at project scale.

2. Current task card (single work item): `meta/tasks/CURRENT.md`
- One active queue item at a time.
- Holds the concrete implementation/verification plan for this turn.
- Must map to exactly one queue item id.

3. Run-level execution plan (external run_dir): `${CTCP_RUNS_ROOT}/<repo_slug>/<run_id>/artifacts/PLAN.md`
- Runtime plan for one ADLC execution loop.
- Must follow run artifact contract and review gates.

## Layering (Why Foundation First)

- `L0` Foundation:
  contracts, paths, gate semantics, project planning scaffolding.
- `L1` Core execution plumbing:
  orchestrator, librarian, dispatcher/providers, base lite regressions.
- `L2` Reliability closure:
  fail/bundle/fix/pass loop and contrast evidence quality.
- `L3` Productization closure:
  release reporting, workflow registry sedimentation from successful runs.
- `L4` Optimization:
  parallelism, budget policy tuning, optional GUI/non-core improvements.

Working top-down by urgency but bottom-up by dependencies avoids unstable upper-layer work.

## Agent Working Rule

- Read `meta/backlog/execution_queue.json`.
- Select the highest-priority item whose `deps` are all `done`.
- Work exactly one queue item in `meta/tasks/CURRENT.md`.
- If blocked, record blocker and keep queue status accurate (`blocked`).

## Unified DoD Rule

Every queue item is considered complete only when:
- defined `dod` entries are satisfied,
- `scripts/verify_repo.*` passes,
- evidence is written to `meta/reports/LAST.md` with reproducible pointers.

No evidence, no completion.

## Minimal Documentation-Only Reproduction Flow

1. Read `docs/00_CORE.md` (contract baseline).
2. Read `docs/12_modules_index.md` (module map and dependencies).
3. Read `meta/backlog/execution_queue.json` (choose next queue item).
4. Fill `meta/tasks/CURRENT.md` for exactly one queue item.
5. Run `scripts/verify_repo.ps1` (Windows) or `scripts/verify_repo.sh` (Unix).
6. Write evidence and replay pointers into `meta/reports/LAST.md`.

## Historical Structure Recovery Notes

- Historical planning/template file `specs/templates/module_spec_template.md` is retained,
  but module-analysis authority is moved to `specs/modules/_template.md`.
- In-repo historical run plan artifacts under `meta/runs/*` are not restored by design,
  because run outputs must remain external under `CTCP_RUNS_ROOT`.
