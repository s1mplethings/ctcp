#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "tests" / "cases"

REQUIRED = [
    "功能点",
    "操作",
    "预期",
    "证据",
]

def main() -> int:
    if not CASES.exists():
        print(f"[tests][error] missing: {CASES.relative_to(ROOT)}")
        return 1

    files = sorted(CASES.glob("*.md"))
    if not files:
        print("[tests][error] no cases found")
        return 1

    bad = []
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        miss = [k for k in REQUIRED if k not in txt]
        if miss:
            bad.append((f, miss))

    if bad:
        for f, miss in bad:
            print(f"[tests][error] {f.relative_to(ROOT)} missing sections: {', '.join(miss)}")
        return 1

    print(f"[tests] ok ({len(files)} cases)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
