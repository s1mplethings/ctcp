from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def _safe_rmtree(path: Path, root: Path) -> bool:
    if not path.exists():
        return False
    resolved = path.resolve()
    if not _is_within(resolved, root):
        raise RuntimeError(f"refusing to delete path outside root: {resolved}")
    if resolved == root:
        raise RuntimeError(f"refusing to delete project root: {root}")
    shutil.rmtree(resolved)
    return True


def clean_project(root: Path) -> dict[str, int]:
    removed = 0
    for rel in ("out", "fixture", "runs"):
        target = (root / rel).resolve()
        if _safe_rmtree(target, root):
            removed += 1

    candidates = sorted(root.rglob("*"), key=lambda p: len(p.parts), reverse=True)
    for node in candidates:
        if not node.is_dir():
            continue
        if node.name not in {"__pycache__", ".pytest_cache"}:
            continue
        if _safe_rmtree(node, root):
            removed += 1

    return {"removed_dirs": removed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean runtime/cache artifacts under project root.")
    parser.add_argument("--root", default="", help="Project root (default: script parent).")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve() if str(args.root or "").strip() else Path(__file__).resolve().parents[1]
    result = clean_project(root)
    print(f"cleaned_dirs={result['removed_dirs']}")


if __name__ == "__main__":
    main()
