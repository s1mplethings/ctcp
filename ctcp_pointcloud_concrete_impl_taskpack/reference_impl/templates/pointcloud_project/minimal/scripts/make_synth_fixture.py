import argparse, json, pathlib
import numpy as np

def write_ply_xyz(path: pathlib.Path, pts: np.ndarray):
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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fixture")
    ap.add_argument("--T", type=int, default=20)
    ap.add_argument("--H", type=int, default=120)
    ap.add_argument("--W", type=int, default=160)
    ap.add_argument("--semantics", action="store_true")
    args = ap.parse_args()

    out = pathlib.Path(args.out); out.mkdir(parents=True, exist_ok=True)

    # Intrinsics (simple pinhole)
    fx = args.W * 0.9
    fy = args.W * 0.9
    cx = (args.W - 1) / 2.0
    cy = (args.H - 1) / 2.0
    (out / "intrinsics.json").write_text(json.dumps({"fx":fx,"fy":fy,"cx":cx,"cy":cy}, indent=2), encoding="utf-8")

    # Create a simple plane z=2.0 with a small bump region (to create structure)
    T,H,W = args.T, args.H, args.W
    depth = np.full((T,H,W), 2.0, dtype=np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    bump = ((xx - cx)**2 + (yy - cy)**2) < (min(H,W)*0.15)**2
    for i in range(T):
        depth[i, bump] = 1.7 + 0.02*i  # slight variation across frames

    # Poses: small translation around origin
    poses = np.zeros((T,4,4), dtype=np.float32)
    for i in range(T):
        p = np.eye(4, dtype=np.float32)
        p[0,3] = (i - T/2) * 0.01
        p[1,3] = 0.0
        p[2,3] = 0.0
        poses[i] = p

    # RGB frames (not used by baseline, but included for future)
    rgb = np.zeros((T,H,W,3), dtype=np.uint8)
    rgb[...,0] = (xx / max(1,W-1) * 255).astype(np.uint8)
    rgb[...,1] = (yy / max(1,H-1) * 255).astype(np.uint8)
    rgb[...,2] = 64

    np.save(out / "depth.npy", depth)
    np.save(out / "poses.npy", poses)
    np.save(out / "rgb_frames.npy", rgb)

    if args.semantics:
        sem = np.zeros((T,H,W), dtype=np.uint8)
        sem[:, bump] = 1
        np.save(out / "sem.npy", sem)

    # Build a simple reference cloud by sampling center frame backprojection
    # (consistent with the pipeline)
    i0 = T//2
    z = depth[i0]
    valid = z > 1e-6
    xs = np.arange(W, dtype=np.float32)
    ys = np.arange(H, dtype=np.float32)
    gx, gy = np.meshgrid(xs, ys)
    X = (gx[valid]-cx)/fx * z[valid]
    Y = (gy[valid]-cy)/fy * z[valid]
    Z = z[valid]
    cam = np.stack([X,Y,Z,np.ones_like(Z)], axis=0)
    world = poses[i0] @ cam
    pts = world[:3].T
    # Thin to manageable size
    pts = pts[::10]
    write_ply_xyz(out / "ref_cloud.ply", pts)

if __name__ == "__main__":
    main()
