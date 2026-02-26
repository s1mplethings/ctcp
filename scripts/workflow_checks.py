#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TASK_CURRENT = ROOT / "meta" / "tasks" / "CURRENT.md"
AI_CONTRACT = ROOT / "ai_context" / "00_AI_CONTRACT.md"
AIDOC_TPL_DIR = ROOT / "ai_context" / "templates" / "aidoc"

CODE_DIR_PREFIXES = (
    "src/",
    "include/",
    "web/",
    "scripts/",
    "tools/",
)

CODE_FILES = (
    "CMakeLists.txt",
    "web/package.json",
    "web/package-lock.json",
)

ALLOW_RE = re.compile(r"\[\s*[xX]\s*\]\s*Code changes allowed")


def _run_git(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None


def _git_changed_files() -> list[str]:
    a = _run_git(["diff", "--name-only"]) or ""
    b = _run_git(["diff", "--cached", "--name-only"]) or ""
    files = {x.strip() for x in (a + "\n" + b).splitlines() if x.strip()}
    return sorted(files)


def _is_code_change(path: str) -> bool:
    if path in CODE_FILES:
        return True
    return any(path.startswith(p) for p in CODE_DIR_PREFIXES)


def main() -> int:
    # BEHAVIOR_ID: B034
    missing: list[str] = []
    if not AI_CONTRACT.exists():
        missing.append("ai_context/00_AI_CONTRACT.md")
    if not AIDOC_TPL_DIR.exists():
        missing.append("ai_context/templates/aidoc/")
    if not TASK_CURRENT.exists():
        missing.append("meta/tasks/CURRENT.md")
    if missing:
        print("[workflow_checks][error] missing required workflow files:")
        for m in missing:
            print(f"  - {m}")
        return 1

    changed = _git_changed_files()

    # If git is not available / not a git repo, we can't detect code changes reliably.
    # In that case we only enforce presence of CURRENT.md and contract files above.
    if not changed:
        print("[workflow_checks] ok (no git diff detected)")
        return 0

    code_changes = [p for p in changed if _is_code_change(p)]
    if not code_changes:
        print("[workflow_checks] ok (no code changes)")
        return 0

    text = TASK_CURRENT.read_text(encoding="utf-8", errors="replace")
    if not ALLOW_RE.search(text):
        print("[workflow_checks][error] code changes detected but CURRENT.md does not allow code edits.")
        print("Add and tick the checkbox in meta/tasks/CURRENT.md:")
        print("  - [x] Code changes allowed")
        print("Code changes:")
        for p in code_changes:
            print(f"  - {p}")
        return 1

    if "meta/reports/LAST.md" not in changed:
        print("[workflow_checks][error] code changes detected but meta/reports/LAST.md was not updated.")
        print("Please update meta/reports/LAST.md in the same patch when touching code directories.")
        print("Code changes:")
        for p in code_changes:
            print(f"  - {p}")
        return 1

    print("[workflow_checks] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
