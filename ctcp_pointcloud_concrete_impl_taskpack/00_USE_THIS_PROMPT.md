# CTCP Task Pack: Make scaffold-pointcloud generate a CONCRETE V2P pipeline (not just placeholder)

You are a programming agent working on the CTCP repository.
Right now, the generated project `scripts/run_v2p.py` is a placeholder.
Upgrade CTCP so the generated pointcloud project contains a REAL baseline pipeline and evaluation,
while keeping CI deterministic and light.

## Goal
When CTCP runs:
  python scripts/ctcp_orchestrate.py scaffold-pointcloud --profile minimal --out <dir>

The created project should be immediately runnable on a synthetic fixture and produce:
- out/cloud.ply
- out/scorecard.json (fps, points_down, runtime, num_frames)
- out/eval.json (voxel_fscore vs a ref cloud generated from the same fixture)

The pipeline should support semantics optionally:
- if a semantics mask exists, also write out/cloud_sem.ply with a label column

## Constraints
- No heavy dependencies required for CI. Use numpy only.
- Input format in the generated project: a fixture folder containing .npy arrays and JSON intrinsics/poses.
- Video reading is optional and may be best-effort (cv2/pillow optional), but CI must not require it.

## Required changes
A) Update CTCP templates under templates/pointcloud_project/minimal/:
1) Replace scripts/run_v2p.py with a real baseline that can:
   - read fixture/rgb.npy (H,W,3 uint8) or rgb_frames.npy (T,H,W,3)
   - read fixture/depth.npy (T,H,W float32, meters)
   - read fixture/intrinsics.json (fx,fy,cx,cy)
   - read fixture/poses.npy (T,4,4) world_T_cam
   - optionally read fixture/sem.npy (T,H,W uint8 labels)
   - generate a point cloud by backprojecting depth for each frame into world coordinates using poses
   - voxel downsample (simple grid hash)
   - write PLY (ascii) with x y z (and optional label)
   - compute scorecard metrics (fps, points_down, runtime_sec, num_frames)

2) Add scripts/make_synth_fixture.py to generate a deterministic synthetic fixture:
   - Create a simple planar scene / cube points projected into depth for T frames
   - Save rgb_frames.npy, depth.npy, poses.npy, intrinsics.json
   - If semantics enabled, save sem.npy
   - Also save ref_cloud.ply (ground-truth point set) for evaluation

3) Add scripts/eval_v2p.py:
   - Read out/cloud.ply and fixture/ref_cloud.ply
   - Compute voxel-Fscore (occupancy-based) at a given voxel size (default 0.02)
   - Write out/eval.json with voxel_fscore

4) Update tests:
   - Add tests/test_pipeline_synth.py that:
     - runs make_synth_fixture.py to a temp dir
     - runs run_v2p.py on that fixture to temp out
     - runs eval_v2p.py
     - asserts outputs exist and voxel_fscore >= 0.8

5) Update pyproject.toml to include numpy dependency.

B) Keep verify_repo.ps1 as pytest runner (OK). Ensure tests pass.

C) Update meta/manifest.json generation remains unchanged (CTCP generates it), but new files must be in manifest.

## Acceptance
- scaffold-pointcloud (minimal) project passes its own scripts/verify_repo.ps1 on a fresh machine with python + numpy.
- run_v2p produces the required outputs on the synthetic fixture.
- cloud_sem.ply is produced when semantics is enabled.

Patch-first. Minimal changes outside templates and tests. No unrelated refactors.
