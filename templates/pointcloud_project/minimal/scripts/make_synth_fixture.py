from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np


def _write_ply_xyz(path: pathlib.Path, points: np.ndarray) -> None:
    n = int(points.shape[0])
    header = "\n".join(
        [
            "ply",
            "format ascii 1.0",
            f"element vertex {n}",
            "property float x",
            "property float y",
            "property float z",
            "end_header",
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        for x, y, z in points:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")


def _backproject_all(
    depth: np.ndarray,
    poses: np.ndarray,
    fx: float,
    fy: float,
    cx: float,
    cy: float,
) -> np.ndarray:
    t, h, w = depth.shape
    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)
    ray_x = (grid_x - cx) / fx
    ray_y = (grid_y - cy) / fy
    clouds: list[np.ndarray] = []
    for i in range(t):
        z = depth[i]
        valid = np.isfinite(z) & (z > 1e-6)
        if not np.any(valid):
            continue
        x = ray_x[valid] * z[valid]
        y = ray_y[valid] * z[valid]
        z_valid = z[valid]
        cam_h = np.stack([x, y, z_valid, np.ones_like(z_valid)], axis=0)
        world_h = poses[i] @ cam_h
        clouds.append(world_h[:3].T.astype(np.float32))
    if not clouds:
        return np.zeros((0, 3), dtype=np.float32)
    return np.concatenate(clouds, axis=0)


def _voxel_downsample(points: np.ndarray, voxel: float) -> np.ndarray:
    if points.size == 0:
        return points.reshape(0, 3)
    keys = np.floor(points / float(voxel)).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    idx = np.sort(idx)
    return points[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create deterministic synthetic fixture for baseline V2P testing.")
    parser.add_argument("--out", default="fixture")
    parser.add_argument("--T", type=int, default=16)
    parser.add_argument("--H", type=int, default=96)
    parser.add_argument("--W", type=int, default=128)
    parser.add_argument("--semantics", action="store_true")
    args = parser.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    t = max(1, int(args.T))
    h = max(8, int(args.H))
    w = max(8, int(args.W))
    fx = float(w * 0.9)
    fy = float(w * 0.9)
    cx = float((w - 1) / 2.0)
    cy = float((h - 1) / 2.0)
    intrinsics = {"fx": fx, "fy": fy, "cx": cx, "cy": cy}
    (out / "intrinsics.json").write_text(json.dumps(intrinsics, indent=2), encoding="utf-8")

    yy, xx = np.mgrid[0:h, 0:w]
    norm_x = (xx.astype(np.float32) - cx) / max(1.0, float(w - 1))
    norm_y = (yy.astype(np.float32) - cy) / max(1.0, float(h - 1))
    base = (2.0 + 0.12 * norm_x + 0.08 * norm_y).astype(np.float32)
    bump = ((xx - cx) ** 2 + (yy - cy) ** 2) <= int((min(h, w) * 0.18) ** 2)

    depth = np.repeat(base[None, :, :], t, axis=0)
    for i in range(t):
        # Keep the scene deterministic but non-trivial across frames.
        depth[i, bump] = np.float32(1.60 + 0.01 * i)

    poses = np.zeros((t, 4, 4), dtype=np.float32)
    for i in range(t):
        pose = np.eye(4, dtype=np.float32)
        pose[0, 3] = np.float32((i - (t - 1) * 0.5) * 0.012)
        pose[1, 3] = np.float32(np.sin(i * 0.15) * 0.005)
        poses[i] = pose

    rgb_frames = np.zeros((t, h, w, 3), dtype=np.uint8)
    x_u8 = np.clip((xx / max(1, w - 1)) * 255.0, 0, 255).astype(np.uint8)
    y_u8 = np.clip((yy / max(1, h - 1)) * 255.0, 0, 255).astype(np.uint8)
    for i in range(t):
        rgb_frames[i, :, :, 0] = x_u8
        rgb_frames[i, :, :, 1] = y_u8
        rgb_frames[i, :, :, 2] = np.uint8((i * 9) % 255)

    np.save(out / "depth.npy", depth)
    np.save(out / "poses.npy", poses)
    np.save(out / "rgb_frames.npy", rgb_frames)
    np.save(out / "rgb.npy", rgb_frames[0])

    if args.semantics:
        sem = np.zeros((t, h, w), dtype=np.uint8)
        sem[:, bump] = 1
        sem[:, xx > cx] = np.maximum(sem[:, xx > cx], 2)
        np.save(out / "sem.npy", sem)

    ref_points = _backproject_all(depth=depth, poses=poses, fx=fx, fy=fy, cx=cx, cy=cy)
    ref_points = _voxel_downsample(ref_points, voxel=0.01)
    _write_ply_xyz(out / "ref_cloud.ply", ref_points)


if __name__ == "__main__":
    main()
