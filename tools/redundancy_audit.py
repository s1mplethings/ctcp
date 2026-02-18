#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {".git", "build", "dist", "node_modules", "__pycache__", ".pytest_cache"}

def sha1(p: Path) -> str:
    h = hashlib.sha1()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main() -> int:
    files = []
    for p in ROOT.rglob("*"):
        if p.is_dir():
            continue
        rel = p.relative_to(ROOT)
        if any(part in EXCLUDE_DIRS for part in rel.parts):
            continue
        if p.stat().st_size < 1024:
            continue
        files.append(p)

    by_hash: dict[str, list[Path]] = {}
    for p in files:
        try:
            h = sha1(p)
        except Exception:
            continue
        by_hash.setdefault(h, []).append(p)

    dups = [(h, ps) for h, ps in by_hash.items() if len(ps) > 1]
    dups.sort(key=lambda x: (-sum(p.stat().st_size for p in x[1]), x[0]))

    if not dups:
        print("[redundancy_audit] no duplicates found (>=1KB, excluding build/dist/node_modules)")
        return 0

    print("[redundancy_audit] duplicates:")
    for h, ps in dups[:50]:
        size = ps[0].stat().st_size
        print(f"- {size} bytes, sha1={h}")
        for p in ps:
            print(f"  - {p.relative_to(ROOT).as_posix()}")
    if len(dups) > 50:
        print(f"[redundancy_audit] ... {len(dups)-50} more groups")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
