#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TASKS_DIR = ROOT / "meta" / "tasks"
EXTERNALS_DIR = ROOT / "meta" / "externals"
REPORTS_DIR = ROOT / "meta" / "reports"

TASK_TEMPLATE = TASKS_DIR / "TEMPLATE.md"
EXTERNALS_TEMPLATE = EXTERNALS_DIR / "TEMPLATE.md"
REPORT_TEMPLATE = REPORTS_DIR / "TEMPLATE_LAST.md"

CURRENT = TASKS_DIR / "CURRENT.md"

def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "task"

def ensure_dirs() -> None:
    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    EXTERNALS_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def init_task(goal: str, force: bool = False) -> Path:
    ensure_dirs()
    if not TASK_TEMPLATE.exists():
        raise SystemExit(f"missing template: {TASK_TEMPLATE}")
    if CURRENT.exists() and not force:
        raise SystemExit("meta/tasks/CURRENT.md already exists; use --force to overwrite")
    text = TASK_TEMPLATE.read_text(encoding="utf-8")
    text = text.replace("<topic>", goal)
    now = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = TASKS_DIR / f"{now}-{_slug(goal)}.md"
    path.write_text(text, encoding="utf-8")
    CURRENT.write_text(text, encoding="utf-8")
    return path

def init_externals(goal: str, force: bool = False) -> Path:
    ensure_dirs()
    if not EXTERNALS_TEMPLATE.exists():
        raise SystemExit(f"missing template: {EXTERNALS_TEMPLATE}")
    text = EXTERNALS_TEMPLATE.read_text(encoding="utf-8")
    now = _dt.datetime.now().strftime("%Y%m%d")
    path = EXTERNALS_DIR / f"{now}-{_slug(goal)}.md"
    if path.exists() and not force:
        raise SystemExit(f"{path.relative_to(ROOT)} already exists; use --force to overwrite")
    path.write_text(text.replace("— ", f"— {goal} "), encoding="utf-8")
    return path

def touch_last_report(goal: str) -> Path:
    ensure_dirs()
    target = REPORTS_DIR / "LAST.md"
    if target.exists():
        return target
    if REPORT_TEMPLATE.exists():
        text = REPORT_TEMPLATE.read_text(encoding="utf-8")
    else:
        text = "# Demo Report — LAST\n\n## Goal\n-\n"
    text = text.replace("## Goal\n-", f"## Goal\n- {goal}")
    target.write_text(text, encoding="utf-8")
    return target

def print_prompt() -> None:
    print("## Required reading order")
    print("1) AGENTS.md")
    print("2) ai_context/00_AI_CONTRACT.md")
    print("3) README.md")
    print("4) BUILD.md")
    print("5) PATCH_README.md")
    print("6) TREE.md")
    print("")
    print("## Mandatory output format")
    print("1) Readlist summary")
    print("2) Plan")
    print("3) Files changed")
    print("4) Verify results")
    print("5) Registry updates")
    print("")

    contract = ROOT / "ai_context" / "00_AI_CONTRACT.md"
    agents = ROOT / "AGENTS.md"
    parts = []
    for p in [agents, contract]:
        if p.exists():
            parts.append(f"# {p.as_posix()}\n\n" + p.read_text(encoding="utf-8", errors="replace"))
    if parts:
        print("\n\n---\n\n".join(parts))
    else:
        print("[warn] contract files not found")

def main() -> int:
    ap = argparse.ArgumentParser(prog="ctcp_assistant")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("init-task", help="create meta/tasks/CURRENT.md and a timestamped task file")
    p1.add_argument("goal")
    p1.add_argument("--force", action="store_true", help="overwrite meta/tasks/CURRENT.md if it already exists")

    p2 = sub.add_parser("init-externals", help="create meta/externals/<date>-<goal>.md")
    p2.add_argument("goal")
    p2.add_argument("--force", action="store_true", help="overwrite file if already exists")

    p3 = sub.add_parser("touch-report", help="create meta/reports/LAST.md if missing")
    p3.add_argument("goal")

    sub.add_parser("print-prompt", help="print merged agent contract for external tools")

    args = ap.parse_args()
    if args.cmd == "init-task":
        path = init_task(args.goal, force=args.force)
        touch_last_report(args.goal)
        print(f"[ok] task: {path.relative_to(ROOT)}")
        print(f"[ok] current: {CURRENT.relative_to(ROOT)}")
        return 0
    if args.cmd == "init-externals":
        path = init_externals(args.goal, force=args.force)
        print(f"[ok] externals: {path.relative_to(ROOT)}")
        return 0
    if args.cmd == "touch-report":
        path = touch_last_report(args.goal)
        print(f"[ok] report: {path.relative_to(ROOT)}")
        return 0
    if args.cmd == "print-prompt":
        print_prompt()
        return 0
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
