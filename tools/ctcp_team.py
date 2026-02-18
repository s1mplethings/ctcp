#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "meta" / "runs"
REPORTS = ROOT / "meta" / "reports"
TASK_CURRENT = ROOT / "meta" / "tasks" / "CURRENT.md"

def _slug(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "run"

def _now_stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")

def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")

def _append(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(text)

def _run_cmd(cmd: list[str]) -> tuple[int, str]:
    try:
        out = subprocess.check_output(cmd, cwd=ROOT, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as e:
        return e.returncode, e.output
    except Exception as e:
        return 1, str(e)

def _ensure_task(goal: str) -> None:
    assistant = ROOT / "tools" / "ctcp_assistant.py"
    if not assistant.exists():
        raise SystemExit("missing tools/ctcp_assistant.py")
    if not TASK_CURRENT.exists():
        rc, out = _run_cmd(["python", str(assistant), "init-task", goal])
        if rc != 0:
            raise SystemExit(out)

def _ensure_last_report(goal: str) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    last = REPORTS / "LAST.md"
    if last.exists():
        return last
    assistant = ROOT / "tools" / "ctcp_assistant.py"
    rc, out = _run_cmd(["python", str(assistant), "touch-report", goal])
    if rc != 0:
        raise SystemExit(out)
    return last

def _prompt_text(goal: str, run_rel: str) -> str:
    return f"""# CTCP Team Packet — PROMPT

## Goal
{goal}

## Your role
You are the internal coding team. Follow repo contract strictly.

## Hard rules
- Read: AGENTS.md, ai_context/00_AI_CONTRACT.md, README.md, BUILD.md, PATCH_README.md, ai_context/problem_registry.md, ai_context/decision_log.md
- Spec-first: docs/spec/meta before code
- Code changes only if meta/tasks/CURRENT.md ticks: [x] Code changes allowed
- Always run verify: scripts/verify_repo.* and paste key results into meta/reports/LAST.md
- If blocked, write questions ONLY to: {run_rel}/QUESTIONS.md

## Delivery
Prefer one patch per theme. Put patches under PATCHES/ (create if missing), and list them in meta/reports/LAST.md.

## Trace / Demo
Write a short running log to: {run_rel}/TRACE.md
Include:
- decisions
- commands run
- failures and fixes

## Expected finish state
- verify_repo passes
- README Doc Index is in sync (scripts/sync_doc_links.py --check passes)
- meta/reports/LAST.md updated and points to {run_rel}

"""

def start(goal: str) -> Path:
    RUNS.mkdir(parents=True, exist_ok=True)
    stamp = _now_stamp()
    run_dir = RUNS / f"{stamp}-{_slug(goal)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    _ensure_task(goal)
    last = _ensure_last_report(goal)

    rel = run_dir.relative_to(ROOT).as_posix()
    _write(run_dir / "PROMPT.md", _prompt_text(goal, rel))
    _write(run_dir / "QUESTIONS.md", "# Questions (only if blocking)\n\n-\n")
    _write(run_dir / "TRACE.md", f"# Trace — {stamp}\n\n## Goal\n{goal}\n\n")

    state = {
        "goal": goal,
        "created": stamp,
        "run_dir": rel,
        "status": "started",
    }
    _write(run_dir / "RUN.json", json.dumps(state, indent=2, ensure_ascii=False) + "\n")

    # Append pointers to LAST report (non-destructive)
    _append(last, f"\n\n---\n\n## CTCP Team Run\n- Run folder: `{rel}`\n- Prompt: `{rel}/PROMPT.md`\n- Trace: `{rel}/TRACE.md`\n- Questions: `{rel}/QUESTIONS.md`\n")
    return run_dir

def main() -> int:
    ap = argparse.ArgumentParser(prog="ctcp_team")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_start = sub.add_parser("start", help="create a new team run packet (prompt/questions/trace)")
    p_start.add_argument("goal")

    p_status = sub.add_parser("status", help="print latest run folder")

    args = ap.parse_args()

    if args.cmd == "start":
        run_dir = start(args.goal)
        rel = run_dir.relative_to(ROOT).as_posix()
        print(f"[ok] created run: {rel}")
        print(f"[next] feed the prompt to your coding agent: {rel}/PROMPT.md")
        print("[next] then run verify: scripts/verify_repo.*")
        return 0

    if args.cmd == "status":
        if not RUNS.exists():
            print("[status] no runs")
            return 0
        runs = sorted([p for p in RUNS.iterdir() if p.is_dir()])
        if not runs:
            print("[status] no runs")
            return 0
        latest = runs[-1]
        print(latest.relative_to(ROOT).as_posix())
        return 0

    return 1

if __name__ == "__main__":
    raise SystemExit(main())
