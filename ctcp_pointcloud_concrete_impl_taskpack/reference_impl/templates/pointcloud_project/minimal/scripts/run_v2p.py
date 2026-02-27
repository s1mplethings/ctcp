import argparse, json, pathlib, time
import numpy as np

def load_intrinsics(p: pathlib.Path):
    d = json.loads(p.read_text(encoding="utf-8"))
    return float(d["fx"]), float(d["fy"]), float(d["cx"]), float(d["cy"])

def write_ply_xyz(path: pathlib.Path, pts: np.ndarray):
    # pts: (N,3) float32/float64
    n = int(pts.shape[0])
    header = "\n".join([
        "ply",
        "format ascii 1.0",
        f"element vertex {n}",
        "property float x",
        "property float y",
        "property float z",
        "end_header",
        ""
    ])
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        for x,y,z in pts:
            f.write(f"{x:.6f} {y:.6f} {z:.6f}\n")

def write_ply_xyz_label(path: pathlib.Path, pts: np.ndarray, lbl: np.ndarray):
    n = int(pts.shape[0])
    header = "\n".join([
        "ply",
        "format ascii 1.0",
        f"element vertex {n}",
        "property float x",
        "property float y",
        "property float z",
        "property uchar label",
        "end_header",
        ""
    ])
    with path.open("w", encoding="utf-8") as f:
        f.write(header)
        for (x,y,z), l in zip(pts, lbl):
            f.write(f"{x:.6f} {y:.6f} {z:.6f} {int(l)}\n")

def voxel_downsample(pts: np.ndarray, voxel: float):
    if pts.size == 0:
        return pts
    q = np.floor(pts / voxel).astype(np.int64)
    # unique rows
    _, idx = np.unique(q, axis=0, return_index=True)
    return pts[idx]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default="fixture")
    ap.add_argument("--out", default="out")
    ap.add_argument("--voxel", type=float, default=0.02)
    ap.add_argument("--stride", type=int, default=1)
    ap.add_argument("--semantics", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    fixture = pathlib.Path(args.fixture)
    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)

    fx, fy, cx, cy = load_intrinsics(fixture / "intrinsics.json")
    depth = np.load(fixture / "depth.npy")   # (T,H,W) meters
    poses = np.load(fixture / "poses.npy")   # (T,4,4) world_T_cam
    T, H, W = depth.shape

    sem = None
    if args.semantics and (fixture / "sem.npy").exists():
        sem = np.load(fixture / "sem.npy")   # (T,H,W) uint8

    # Precompute camera rays in cam frame (normalized by intrinsics)
    xs = np.arange(W, dtype=np.float32)
    ys = np.arange(H, dtype=np.float32)
    grid_x, grid_y = np.meshgrid(xs, ys)
    x_cam = (grid_x - cx) / fx
    y_cam = (grid_y - cy) / fy
    ones = np.ones_like(x_cam)

    pts_all = []
    lbl_all = []

    frames = 0
    for i in range(0, T, max(1, args.stride)):
        z = depth[i].astype(np.float32)
        valid = z > 1e-6
        if not np.any(valid):
            continue

        # cam points
        X = x_cam[valid] * z[valid]
        Y = y_cam[valid] * z[valid]
        Z = z[valid]
        cam_pts = np.stack([X, Y, Z, np.ones_like(Z)], axis=0)  # (4,N)

        world = (poses[i].astype(np.float32) @ cam_pts)  # (4,N)
        pts = world[:3].T  # (N,3)
        pts_all.append(pts)

        if sem is not None:
            lbl_all.append(sem[i][valid].astype(np.uint8))

        frames += 1

    if pts_all:
        pts_all = np.concatenate(pts_all, axis=0)
    else:
        pts_all = np.zeros((0,3), dtype=np.float32)

    pts_down = voxel_downsample(pts_all, float(args.voxel))
    write_ply_xyz(out / "cloud.ply", pts_down)

    if sem is not None and lbl_all:
        lbl_all = np.concatenate(lbl_all, axis=0)
        # Downsample labels by nearest kept indices (simple: recompute keys)
        q_all = np.floor(pts_all / float(args.voxel)).astype(np.int64)
        _, idx = np.unique(q_all, axis=0, return_index=True)
        lbl_down = lbl_all[idx]
        write_ply_xyz_label(out / "cloud_sem.ply", pts_down, lbl_down)

    runtime = time.time() - t0
    score = {
        "fps": float(frames / runtime) if runtime > 1e-9 else 0.0,
        "points_down": int(pts_down.shape[0]),
        "runtime_sec": float(runtime),
        "num_frames": int(frames),
        "voxel": float(args.voxel),
        "stride": int(args.stride),
    }
    (out / "scorecard.json").write_text(json.dumps(score, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
