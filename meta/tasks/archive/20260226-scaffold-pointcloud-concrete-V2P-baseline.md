# Update 2026-02-26 - scaffold-pointcloud concrete V2P baseline

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

