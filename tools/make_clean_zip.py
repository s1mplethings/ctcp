#!/usr/bin/env python3
"""
Create a clean zip of the repository that excludes build artifacts and caches.
Default output: dist/clean_repo.zip
"""

import argparse
from pathlib import Path
import zipfile

EXCLUDE_DIRS = {"build", "dist", "runs", ".git", "__pycache__"}
EXCLUDE_FILES = {"patch_debug.txt"}
EXCLUDE_SUFFIXES = {".log", ".tmp"}


def should_skip(rel_path: Path, output_path: Path) -> bool:
    # Skip the output file itself
    if rel_path == output_path:
        return True
    parts = rel_path.parts
    if any(part in EXCLUDE_DIRS for part in parts):
        return True
    if rel_path.name in EXCLUDE_FILES:
        return True
    if rel_path.suffix.lower() in EXCLUDE_SUFFIXES:
        return True
    return False


def make_clean_zip(root: Path, out: Path) -> Path:
    root = root.resolve()
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    rel_out = out.relative_to(root) if out.is_relative_to(root) else None

    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in root.rglob("*"):
            if path.is_dir():
                continue
            rel = path.relative_to(root)
            if rel_out is not None and rel == rel_out:
                continue
            if should_skip(rel, rel_out or Path("")):
                continue
            zf.write(path, rel.as_posix())
    return out


def main():
    parser = argparse.ArgumentParser(description="Create a clean zip without build/dist/runs/git artifacts.")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument("--out", default="dist/clean_repo.zip", help="output zip path (default: dist/clean_repo.zip)")
    args = parser.parse_args()

    root = Path(args.root)
    out = Path(args.out)

    if not root.exists():
        parser.error(f"root does not exist: {root}")

    result = make_clean_zip(root, out)
    print(f"[ok] wrote {result}")


if __name__ == "__main__":
    main()
