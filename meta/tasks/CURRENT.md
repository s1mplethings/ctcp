# Task - pointcloud-project-generator-and-dialogue-bench

## Queue Binding
- Queue Item: `N/A (user-requested task pack)`
- Layer/Priority: `L1 / P0`
- Source Queue File: `meta/backlog/execution_queue.json` (reference only)

## Context
- User requested a full CTCP task pack upgrade for point-cloud workflows:
  - `scaffold-pointcloud`: generate complete source project from templates into target `--out`
  - `cos-user-v2p`: run dialogue-driven external benchmark and copy outputs to fixed destination
- Scope:
  - add new CLI subcommand + template rendering + `meta/manifest.json`
  - enforce safety and doc-first run evidence (`SCAFFOLD_PLAN.md` / `USER_SIM_PLAN.md`)
  - ensure testkit execution is outside both CTCP repo and tested repo
  - add fixtures, SimLab scenario, behavior docs, and unit tests

## DoD Mapping (from request)
- [x] DoD-1: `scaffold-pointcloud` command generates required minimal/standard point-cloud project files.
- [x] DoD-2: `cos-user-v2p` runs benchmark with dialogue evidence and fixed output copy path.
- [x] DoD-3: both commands create run_dir doc-first evidence and auditable trace/report.
- [x] DoD-4: fixtures/tests/simlab/behavior docs are added and wired.

## Acceptance (must be checkable)
- [x] DoD written (this file complete)
- [x] Research logged (if needed): `N/A`
- [x] Code changes allowed
- [ ] Patch applies cleanly (`git apply ...`) OR overlay zip applies cleanly
- [x] `scripts/verify_repo.*` passes
- [x] Demo report updated: `meta/reports/LAST.md`

## Plan
1) Docs/Spec first: update task/report + behavior docs and index registration.
2) Implement `scaffold-pointcloud` in `scripts/ctcp_orchestrate.py`.
3) Strengthen `cos-user-v2p` + `tools/testkit_runner.py` location/verify defaults.
4) Add templates/fixtures/tests/simlab scenario.
5) Run targeted tests + full `scripts/verify_repo.ps1`.
6) Record final evidence in `meta/reports/LAST.md`.

## Notes / Decisions
- Reuse existing dialogue machinery in orchestrator for deterministic script/agent/default answer modes.
- Keep legacy `scaffold` command unchanged; add independent `scaffold-pointcloud` command.

## Update 2026-02-26 - scaffold-pointcloud concrete V2P baseline

### Context
- Upgrade generated `templates/pointcloud_project/minimal` project from placeholder `run_v2p.py` to concrete numpy-only baseline pipeline + deterministic synthetic fixture + voxel-Fscore evaluation.
- Keep CI deterministic/light and keep scope minimal (templates/tests/meta only).

### DoD Mapping (from request)
- [x] DoD-1: generated project includes concrete `scripts/run_v2p.py` depth backprojection + voxel downsample + PLY + scorecard.
- [x] DoD-2: generated project includes deterministic `scripts/make_synth_fixture.py` and `scripts/eval_v2p.py`.
- [x] DoD-3: generated project includes synth pipeline test `tests/test_pipeline_synth.py` with `voxel_fscore >= 0.8`.
- [x] DoD-4: generated project dependencies include `numpy`; semantics fixture produces `cloud_sem.ply`.

### Plan
1) Docs/Spec first: record task/report update for this run.
2) Implement template scripts and dependency updates.
3) Update template tests and scaffold expectations.
4) Run targeted unit tests and `scripts/verify_repo.ps1`.
5) Record verification evidence in `meta/reports/LAST.md`.

## Update 2026-02-27 - V2P fixture auto-acquire + cleanliness hardening

### Context
- Add deterministic fixture acquisition flow for `cos-user-v2p` (`auto|synth|path`) with discover-or-ask behavior.
- Harden pointcloud template/scaffold cleanliness to exclude caches and runtime artifacts from manifests and generated bundles.

### DoD Mapping (from request)
- [x] DoD-1: add `tools/v2p_fixtures.py` with discover + ensure flow and deterministic dialogue fallback.
- [x] DoD-2: wire fixture flow into `cos-user-v2p` args/plan/report and write `artifacts/fixture_meta.json`.
- [x] DoD-3: harden template hygiene + scaffold manifest exclusions + generated project clean utility.
- [x] DoD-4: add/adjust tests for fixture discovery and cos-user synth fixture flow.
- [x] DoD-5: add behavior doc/index entry for fixture acquisition + cleanliness.

### Plan
1) Doc-first update in task/report.
2) Implement fixture helper module and orchestrator/testkit integration.
3) Implement template hygiene and clean utility script/test.
4) Add CTCP tests and behavior catalog entry.
5) Run targeted tests and `scripts/verify_repo.ps1`; record first failure and minimal fix if needed.
