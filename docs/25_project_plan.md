# Project Plan (Foundation-First)

This document defines project-level planning discipline only.
It does not redefine repository purpose or canonical execution flow.

Source map:

- Repo purpose: `docs/01_north_star.md`
- Canonical flow: `docs/04_execution_flow.md`
- Current task purpose/scope truth: `meta/tasks/CURRENT.md`

## 1) Three Planning Scopes

1. Project queue (long-horizon): `meta/backlog/execution_queue.json`
   - Source of truth for roadmap layers (`L0`..`L4`), dependencies, status, and DoD.
2. Current task card (single active work item): `meta/tasks/CURRENT.md`
   - One active queue item at a time.
   - Single source of truth for current task purpose/scope and allowed behavior changes.
   - Concrete plan + acceptance checklist for the current patch.
3. Run-level execution plan (external run_dir):
   - `${CTCP_RUNS_ROOT}/<repo_slug>/<run_id>/artifacts/PLAN.md`
   - Runtime execution contract for one ADLC loop.

## 2) Queue Binding Rule (Hard)

- `meta/tasks/CURRENT.md` MUST bind exactly one queue item id.
- `Queue Item: N/A` is forbidden.
- For a direct user request without an existing queue item:
  1. Add an `ADHOC-YYYYMMDD-<slug>` item into `meta/backlog/execution_queue.json`.
  2. Include `layer`, `priority`, `deps`, `dod`, and target artifacts.
  3. Bind `CURRENT.md` to that ADHOC id before implementation.

This keeps queue -> current task -> verify/report fully auditable.

## 3) Layering Model (Why Foundation First)

- `L0` Foundation: contracts, paths, gate semantics, planning scaffolding.
- `L1` Core execution plumbing: orchestrator, librarian, dispatcher/providers, lite regressions.
- `L2` Reliability closure: fail/bundle/fix/pass loop, evidence quality.
- `L3` Productization closure: release reporting, workflow history sedimentation.
- `L4` Optimization: parallelism, budget tuning, optional GUI/non-core improvements.

Execution should be dependency-safe: bottom-up by deps, top-down by urgency.

## 4) Agent Working Rule

0. Follow canonical execution flow from `docs/04_execution_flow.md`.
1. Read `meta/backlog/execution_queue.json`.
2. Pick the highest-priority item whose `deps` are all `done`.
3. Write/refresh `meta/tasks/CURRENT.md` for that exact item id.
4. Execute minimal scoped change.
5. Run `scripts/verify_repo.ps1` or `scripts/verify_repo.sh`.
6. Record evidence in `meta/reports/LAST.md` and update queue status.

If blocked, set queue status to `blocked` and record blocker details.

## 5) Unified DoD Rule

A queue item is complete only when all conditions hold:

- item `dod` entries are satisfied,
- `scripts/verify_repo.*` passes,
- evidence and reproducible command trace are recorded in `meta/reports/LAST.md`.

No evidence, no completion.

## 6) Minimal Reproduction Flow (Docs-Only Task)

1. Read contract baseline (`docs/00_CORE.md`, `docs/03_quality_gates.md`, `docs/30_artifact_contracts.md`).
2. Bind one queue item in `meta/tasks/CURRENT.md`.
3. Perform doc/spec/meta updates.
4. Run `python scripts/sync_doc_links.py --check`.
5. Run `scripts/verify_repo.ps1` (Windows) or `scripts/verify_repo.sh` (Unix).
6. Record Readlist/Plan/Changes/Verify/Demo in `meta/reports/LAST.md`.

## 7) Historical Notes

- `specs/templates/module_spec_template.md` is retained historically.
- Module analysis authority is `specs/modules/_template.md`.
- In-repo historical run outputs under `meta/runs/*` are intentionally not restored;
  run outputs must remain external under `CTCP_RUNS_ROOT`.
