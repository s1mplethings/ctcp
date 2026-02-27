import argparse, json, pathlib

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--semantics", action="store_true")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Minimal placeholder output
    (out / "cloud.ply").write_text(
        "ply\nformat ascii 1.0\n"
        "element vertex 1\n"
        "property float x\nproperty float y\nproperty float z\n"
        "end_header\n0 0 0\n",
        encoding="utf-8",
    )

    if args.semantics:
        (out / "cloud_sem.ply").write_text(
            "ply\nformat ascii 1.0\n"
            "element vertex 1\n"
            "property float x\nproperty float y\nproperty float z\n"
            "property uchar label\n"
            "end_header\n0 0 0 1\n",
            encoding="utf-8",
        )

    (out / "scorecard.json").write_text(json.dumps({"fps": 1.0, "points_down": 1}, indent=2), encoding="utf-8")
    (out / "eval.json").write_text(json.dumps({"voxel_fscore": 0.0}, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
