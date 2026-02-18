#!/usr/bin/env python3
"""
Fail fast when known temporary/debug redundancy patterns are committed.
"""

from __future__ import annotations

import fnmatch
import subprocess
import sys
from pathlib import Path, PurePosixPath


FORBIDDEN_EXACT = {
    "_tmp_patch.py",
    "patch_debug.txt",
}

FORBIDDEN_GLOBS = {
    "*.bak",
}

FORBIDDEN_REGEXES = (
    # Version-only text files at repo root are typically scratch notes, not source.
    r"^\d+\.\d+\.\d+\.txt$",
)


def list_tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files"], text=True, encoding="utf-8")
    return [line.strip().replace("\\", "/") for line in out.splitlines() if line.strip()]


def main() -> int:
    try:
        files = list_tracked_files()
    except Exception as exc:  # pragma: no cover
        print(f"[redundancy_guard] ERROR: failed to list tracked files: {exc}", file=sys.stderr)
        return 2

    import re

    violations: list[tuple[str, str]] = []
    for path in files:
        if not Path(path).exists():
            # File is deleted in working tree; allow cleanup patches to pass before commit.
            continue
        name = PurePosixPath(path).name
        if name in FORBIDDEN_EXACT:
            violations.append((path, f"forbidden exact filename: {name}"))
            continue

        if any(fnmatch.fnmatch(name, pat) for pat in FORBIDDEN_GLOBS):
            violations.append((path, f"forbidden glob filename: {name}"))
            continue

        if "/" not in path and any(re.match(rx, path) for rx in FORBIDDEN_REGEXES):
            violations.append((path, "forbidden root-level version-note filename"))

    if violations:
        print("[redundancy_guard] FAIL: redundant artifacts detected:")
        for p, why in violations:
            print(f"  - {p}: {why}")
        print("[redundancy_guard] Fix: remove these files or rename/move to a justified location.")
        return 1

    print("[redundancy_guard] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
