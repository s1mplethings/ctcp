# {{PROJECT_NAME}}

3D video → point cloud workflow project scaffold (CTCP-aligned).

## Quickstart
- Build a deterministic synthetic fixture:
  - `python scripts/make_synth_fixture.py --out fixture --semantics`
- Run baseline V2P on fixture:
  - `python scripts/run_v2p.py --fixture fixture --out out --voxel 0.03 --semantics`
- Evaluate against fixture reference cloud:
  - `python scripts/eval_v2p.py --cloud out/cloud.ply --ref fixture/ref_cloud.ply --out out/eval.json --voxel 0.03`

Generated outputs:
- `out/cloud.ply`
- `out/cloud_sem.ply` (if `--semantics`)
- `out/scorecard.json`
- `out/eval.json`

## Verify
- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1`

## Clean
- `python scripts/clean_project.py`
