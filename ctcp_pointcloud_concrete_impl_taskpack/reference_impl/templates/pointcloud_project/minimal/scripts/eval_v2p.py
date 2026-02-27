import argparse, json, pathlib
import numpy as np

def read_ply_xyz(path: pathlib.Path):
    lines = path.read_text(encoding="utf-8").splitlines()
    i = 0
    n = 0
    while i < len(lines):
        if lines[i].startswith("element vertex"):
            n = int(lines[i].split()[-1])
        if lines[i].strip() == "end_header":
            i += 1
            break
        i += 1
    data = []
    for j in range(i, min(i+n, len(lines))):
        parts = lines[j].split()
        if len(parts) >= 3:
            data.append([float(parts[0]), float(parts[1]), float(parts[2])])
    return np.asarray(data, dtype=np.float32)

def voxel_set(pts: np.ndarray, voxel: float):
    if pts.size == 0:
        return set()
    q = np.floor(pts / voxel).astype(np.int64)
    return set(map(tuple, q.tolist()))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cloud", default="out/cloud.ply")
    ap.add_argument("--ref", default="fixture/ref_cloud.ply")
    ap.add_argument("--out", default="out/eval.json")
    ap.add_argument("--voxel", type=float, default=0.02)
    args = ap.parse_args()

    cloud = read_ply_xyz(pathlib.Path(args.cloud))
    ref = read_ply_xyz(pathlib.Path(args.ref))

    A = voxel_set(cloud, float(args.voxel))
    B = voxel_set(ref, float(args.voxel))

    tp = len(A & B)
    fp = len(A - B)
    fn = len(B - A)

    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f = (2*prec*rec/(prec+rec)) if (prec+rec) > 0 else 0.0

    pathlib.Path(args.out).write_text(json.dumps({
        "voxel_fscore": float(f),
        "precision": float(prec),
        "recall": float(rec),
        "voxel": float(args.voxel),
        "tp": int(tp), "fp": int(fp), "fn": int(fn)
    }, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
