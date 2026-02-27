from __future__ import annotations

import argparse
import json
import pathlib
import time

import numpy as np


def _load_intrinsics(path: pathlib.Path) -> tuple[float, float, float, float]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    return float(doc["fx"]), float(doc["fy"]), float(doc["cx"]), float(doc["cy"])


def _load_rgb_sequence(
    fixture: pathlib.Path,
    num_frames: int,
    height: int,
    width: int,
) -> np.ndarray | None:
    rgb_frames_path = fixture / "rgb_frames.npy"
    rgb_single_path = fixture / "rgb.npy"

    if rgb_frames_path.exists():
        rgb = np.load(rgb_frames_path)
        if rgb.ndim != 4:
            raise ValueError("rgb_frames.npy must have shape (T,H,W,3)")
        if rgb.shape[0] != num_frames:
            raise ValueError("rgb_frames.npy frame count does not match depth.npy")
        if rgb.shape[1] != height or rgb.shape[2] != width or rgb.shape[3] != 3:
            raise ValueError("rgb_frames.npy spatial shape must match depth.npy and channel=3")
        return rgb

    if rgb_single_path.exists():
        rgb = np.load(rgb_single_path)
        if rgb.ndim != 3 or rgb.shape[0] != height or rgb.shape[1] != width or rgb.shape[2] != 3:
            raise ValueError("rgb.npy must have shape (H,W,3) that matches depth.npy")
        return np.repeat(rgb[None, ...], num_frames, axis=0)

    return None


def _voxel_downsample(points: np.ndarray, voxel: float) -> tuple[np.ndarray, np.ndarray]:
    if points.size == 0:
        return points.reshape(0, 3), np.zeros((0,), dtype=np.int64)
    keys = np.floor(points / float(voxel)).astype(np.int64)
    _, idx = np.unique(keys, axis=0, return_index=True)
    idx = np.sort(idx)
    return points[idx], idx


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


def _write_ply_xyz_label(path: pathlib.Path, points: np.ndarray, labels: np.ndarray) -> None:
    n = int(points.shape[0])
    header = "\n".join(
        [
            "ply",
            "format ascii 1.0",
            f"element vertex {n}",
            "property float x",
            "property float y",
            "property float z",
            "property uchar label",
            "end_header",
            "",
        ]
    )
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        for (x, y, z), label in zip(points, labels):
            f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(label)}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Numpy baseline V2P pipeline on .npy fixture inputs.")
    parser.add_argument("--fixture", default="fixture", help="Fixture directory with depth/poses/intrinsics arrays.")
    parser.add_argument("--out", default="out", help="Output directory.")
    parser.add_argument("--voxel", type=float, default=0.02, help="Voxel size in meters for downsampling.")
    parser.add_argument("--stride", type=int, default=1, help="Frame stride.")
    parser.add_argument("--semantics", action="store_true", help="Prefer semantics output if sem.npy exists.")
    args = parser.parse_args()

    t0 = time.perf_counter()
    fixture = pathlib.Path(args.fixture)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    fx, fy, cx, cy = _load_intrinsics(fixture / "intrinsics.json")
    depth = np.load(fixture / "depth.npy").astype(np.float32)  # (T,H,W)
    poses = np.load(fixture / "poses.npy").astype(np.float32)  # (T,4,4) world_T_cam
    if depth.ndim != 3:
        raise ValueError("depth.npy must have shape (T,H,W)")
    if poses.ndim != 3 or poses.shape[1:] != (4, 4):
        raise ValueError("poses.npy must have shape (T,4,4)")

    t, h, w = depth.shape
    if poses.shape[0] != t:
        raise ValueError("poses.npy frame count does not match depth.npy")

    # RGB is optional for this baseline, but we support both expected fixture formats.
    _ = _load_rgb_sequence(fixture, t, h, w)

    sem_path = fixture / "sem.npy"
    sem: np.ndarray | None = None
    if sem_path.exists():
        sem = np.load(sem_path)
        if sem.shape != depth.shape:
            raise ValueError("sem.npy must have shape (T,H,W) that matches depth.npy")
        sem = sem.astype(np.uint8)

    xs = np.arange(w, dtype=np.float32)
    ys = np.arange(h, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)
    ray_x = (grid_x - cx) / fx
    ray_y = (grid_y - cy) / fy

    pts_all: list[np.ndarray] = []
    labels_all: list[np.ndarray] = []
    frames_used = 0
    stride = max(1, int(args.stride))

    for i in range(0, t, stride):
        z = depth[i]
        valid = np.isfinite(z) & (z > 1e-6)
        if not np.any(valid):
            continue

        x = ray_x[valid] * z[valid]
        y = ray_y[valid] * z[valid]
        z_valid = z[valid]
        cam_h = np.stack([x, y, z_valid, np.ones_like(z_valid)], axis=0)  # (4,N)
        world_h = poses[i] @ cam_h
        pts_all.append(world_h[:3].T.astype(np.float32))
        if sem is not None:
            labels_all.append(sem[i][valid].astype(np.uint8))
        frames_used += 1

    if pts_all:
        points = np.concatenate(pts_all, axis=0)
    else:
        points = np.zeros((0, 3), dtype=np.float32)
    points_down, keep_idx = _voxel_downsample(points, float(args.voxel))
    _write_ply_xyz(out / "cloud.ply", points_down)

    semantics_enabled = sem is not None and (bool(args.semantics) or sem_path.exists())
    if semantics_enabled and labels_all:
        labels = np.concatenate(labels_all, axis=0)
        labels_down = labels[keep_idx] if keep_idx.size else labels[:0]
        _write_ply_xyz_label(out / "cloud_sem.ply", points_down, labels_down)

    runtime = float(time.perf_counter() - t0)
    fps = float(frames_used / runtime) if runtime > 1e-9 else 0.0
    score = {
        "fps": fps,
        "points_down": int(points_down.shape[0]),
        "runtime_sec": runtime,
        "num_frames": int(frames_used),
        "voxel": float(args.voxel),
        "stride": int(stride),
    }
    (out / "scorecard.json").write_text(json.dumps(score, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
