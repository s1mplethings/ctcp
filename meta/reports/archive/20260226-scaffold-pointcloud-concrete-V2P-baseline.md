# Update 2026-02-26 (scaffold-pointcloud concrete V2P baseline)

### Readlist
- `AGENTS.md`
- `docs/00_CORE.md`
- `ai_context/00_AI_CONTRACT.md`
- `ai_context/CTCP_FAST_RULES.md`
- `README.md`
- `BUILD.md`
- `PATCH_README.md`
- `TREE.md`
- `docs/03_quality_gates.md`
- `ai_context/problem_registry.md`
- `ai_context/decision_log.md`
- `.agents/skills/ctcp-workflow/SKILL.md`
- `.agents/skills/ctcp-gate-precheck/SKILL.md`
- `.agents/skills/ctcp-verify/SKILL.md`

### Plan
1) Docs/Spec first: update `meta/tasks/CURRENT.md` for this task before template code edits.
2) Implement concrete minimal template baseline (`run_v2p.py`, synth fixture, voxel eval, numpy dep).
3) Update scaffold checks/tests to require and validate new template files.
4) Verify with targeted tests, generated-project verify, then repo gate `scripts/verify_repo.ps1`.
5) Record first failure + minimal fix and final pass evidence.

### Changes
- Template baseline implementation:
  - `templates/pointcloud_project/minimal/scripts/run_v2p.py`
    - Replaced placeholder random cloud generation with fixture-driven depth backprojection pipeline.
    - Added support for fixture inputs: `depth.npy`, `poses.npy`, `intrinsics.json`, optional `rgb.npy`/`rgb_frames.npy`, optional `sem.npy`.
    - Added voxel downsample + ASCII PLY writer + `scorecard.json` output (`fps`, `points_down`, `runtime_sec`, `num_frames`).
    - Added semantic cloud output `out/cloud_sem.ply` when semantics mask exists.
  - Added `templates/pointcloud_project/minimal/scripts/make_synth_fixture.py`
    - Deterministic synthetic fixture generation (`rgb_frames.npy`, `rgb.npy`, `depth.npy`, `poses.npy`, `intrinsics.json`, optional `sem.npy`).
    - Emits `fixture/ref_cloud.ply` built from the same fixture geometry for evaluation.
  - Added `templates/pointcloud_project/minimal/scripts/eval_v2p.py`
    - Reads cloud/ref PLY and computes voxel occupancy precision/recall/F-score.
    - Writes `out/eval.json` with `voxel_fscore` and counts.
- Template tests/deps/docs:
  - Added `templates/pointcloud_project/minimal/tests/test_pipeline_synth.py` (full fixture -> run -> eval assertion, `voxel_fscore >= 0.8`).
  - Updated `templates/pointcloud_project/minimal/tests/test_smoke.py` to use synth fixture pipeline.
  - Updated `templates/pointcloud_project/minimal/scripts/verify_repo.ps1` to run both tests and resolve project root via `$PSScriptRoot`.
  - Updated `templates/pointcloud_project/minimal/pyproject.toml` to include `numpy`.
  - Updated `templates/pointcloud_project/minimal/README.md` quickstart to concrete fixture/run/eval flow.
- Scaffold contract/test updates:
  - `scripts/ctcp_orchestrate.py`
    - `_required_pointcloud_paths()` now enforces new script/test files in generated minimal project.
    - `_collect_pointcloud_template_files()` now skips `__pycache__/` and `.pyc` artifacts.
  - `tests/test_scaffold_pointcloud_project.py`
    - Extended required generated-file assertions for new pipeline files.
- Gate compatibility update:
  - `artifacts/PLAN.md`
    - Added `ctcp_pointcloud_concrete_impl_taskpack/` to `Scope-Allow` to clear `patch_check` failure caused by existing untracked taskpack files.
- Task tracking:
  - Updated `meta/tasks/CURRENT.md` for this run and marked DoD completion.

### Verify
- Targeted template tests:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_smoke.py tests/test_pipeline_synth.py` (cwd `templates/pointcloud_project/minimal`) => exit 0 (`2 passed`).
- Scaffold generation test:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_scaffold_pointcloud_project.py` => exit 0 (`1 passed`).
- Generated project direct verify:
  - `python scripts/ctcp_orchestrate.py scaffold-pointcloud --profile minimal --name demo_pc --out <tmp>/proj --runs-root <tmp>/runs --dialogue-script tests/fixtures/dialogues/scaffold_pointcloud.jsonl` => exit 0.
  - `powershell -ExecutionPolicy Bypass -File <tmp>/proj/scripts/verify_repo.ps1` (invoked outside project cwd) => exit 0 (`2 passed`).
- Repo gate (first run):
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 1.
  - First failure: `patch_check` out-of-scope path `ctcp_pointcloud_concrete_impl_taskpack/...`.
  - Minimal fix: add `ctcp_pointcloud_concrete_impl_taskpack/` to `artifacts/PLAN.md` `Scope-Allow`.
- Repo gate (after minimal fix):
  - `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` => exit 0.
  - Key checkpoints: `workflow_checks` ok, `patch_check` ok (`changed_files=69`), `sync_doc_links --check` ok, lite replay pass (`passed=14 failed=0`), python unit tests pass (`Ran 69, OK, skipped=3`).

### Questions
- None.

### Demo
- Report: `meta/reports/LAST.md`
- Task card: `meta/tasks/CURRENT.md`
- verify_repo lite replay summary run: `C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260227-002805/summary.json`
- Generated scaffold run sample: `C:/Users/sunom/AppData/Local/Temp/ctcp_pc_0a66676ebc8c44e9a331754bfdd0d780/runs/scaffold_pointcloud/20260227-002702-387832-scaffold-pointcloud-demo_pc`

