#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.module_protection import evaluate_module_protection


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Enforce CURRENT.md write scope and frozen-kernel elevation against contracts/module_freeze.json")
    ap.add_argument("--root", type=Path, default=ROOT, help="repository root")
    ap.add_argument("--json", action="store_true", help="print JSON result")
    args = ap.parse_args(argv)

    doc = evaluate_module_protection(args.root.resolve())
    violations = list(doc.get("violations", []))
    if args.json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        print(
            f"[module_protection_check] ownership={doc.get('ownership', 'task-owned')} "
            f"changed={len(list(doc.get('changed_files', [])))} "
            f"ignored={len(list(doc.get('ignored_changed_files', [])))}"
        )
        for label in ("task_owned_files", "lane_owned_files", "frozen_kernel_files"):
            rows = list(doc.get(label, []))
            if rows:
                print(f"[module_protection_check] {label}={', '.join(rows)}")
        if violations:
            for item in violations:
                print(f"[module_protection_check][error] {item}")
        else:
            print("[module_protection_check] ok")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
