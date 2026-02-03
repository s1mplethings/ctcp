#!/usr/bin/env python3
"""
Simple helper that copies an input file to an output path.
Usage: python tools/checks/case_echo.py <input> <output>
"""

import shutil
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 3:
        print("usage: python tools/checks/case_echo.py <input> <output>")
        return 1
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    if not src.exists():
        print(f"[err] input not found: {src}")
        return 2
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"[ok] copied {src} -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
