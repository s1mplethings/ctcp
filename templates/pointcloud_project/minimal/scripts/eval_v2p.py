from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np


def _read_ply_xyz(path: pathlib.Path) -> np.ndarray:
    lines = path.read_text(encoding="utf-8").splitlines()
    idx = 0
    n = 0
    while idx < len(lines):
        row = lines[idx].strip()
        if row.startswith("element vertex"):
            n = int(row.split()[-1])
        if row == "end_header":
            idx += 1
            break
        idx += 1
    rows: list[list[float]] = []
    for line in lines[idx : idx + n]:
        parts = line.split()
        if len(parts) >= 3:
            rows.append([float(parts[0]), float(parts[1]), float(parts[2])])
    if not rows:
        return np.zeros((0, 3), dtype=np.float32)
    return np.asarray(rows, dtype=np.float32)


def _voxel_set(points: np.ndarray, voxel: float) -> set[tuple[int, int, int]]:
    if points.size == 0:
        return set()
    keys = np.floor(points / float(voxel)).astype(np.int64)
    return set(map(tuple, keys.tolist()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Voxel occupancy F-score for V2P output cloud.")
    parser.add_argument("--cloud", default="out/cloud.ply")
    parser.add_argument("--ref", default="fixture/ref_cloud.ply")
    parser.add_argument("--out", default="out/eval.json")
    parser.add_argument("--voxel", type=float, default=0.02)
    args = parser.parse_args()

    cloud = _read_ply_xyz(pathlib.Path(args.cloud))
    ref = _read_ply_xyz(pathlib.Path(args.ref))
    a = _voxel_set(cloud, float(args.voxel))
    b = _voxel_set(ref, float(args.voxel))

    tp = len(a & b)
    fp = len(a - b)
    fn = len(b - a)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fscore = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    out_doc = {
        "voxel_fscore": float(fscore),
        "precision": float(precision),
        "recall": float(recall),
        "voxel": float(args.voxel),
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
    }
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
