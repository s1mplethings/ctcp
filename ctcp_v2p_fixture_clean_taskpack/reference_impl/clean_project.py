import argparse, pathlib, shutil, os

CACHE_DIRS = {".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache"}
TOP_LEVEL = {"out", "fixture", "runs"}

def safe_rmtree(p: pathlib.Path, root: pathlib.Path):
    p = p.resolve()
    root = root.resolve()
    if root not in p.parents and p != root:
        raise RuntimeError(f"Refusing to delete outside project root: {p}")
    if p.exists():
        shutil.rmtree(p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = pathlib.Path(args.root).resolve()

    for d in TOP_LEVEL:
        safe_rmtree(root / d, root)

    for dirpath, dirnames, filenames in os.walk(root):
        for name in list(dirnames):
            if name in CACHE_DIRS:
                safe_rmtree(pathlib.Path(dirpath) / name, root)
                dirnames.remove(name)

if __name__ == "__main__":
    main()
