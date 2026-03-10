#!/usr/bin/env python3
"""Classify repository changes into a verification profile.

Profiles:
  doc-only   - markdown/docs/index/meta/report/archive/cleanup only
  contract   - authoritative governance/workflow/runtime contract sources
  code       - any code/integration/script/runtime/test/build change

Usage:
  python scripts/classify_change_profile.py          # prints profile name
  python scripts/classify_change_profile.py --json   # prints JSON detail
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# --- path classification (aligned with workflow_checks.py) ---

CODE_DIR_PREFIXES = (
    "src/",
    "include/",
    "web/",
    "scripts/",
    "tools/",
    "tests/",
    "simlab/",
    "executor/",
    "frontend/",
    "ctcp/",
)

CODE_FILES = (
    "CMakeLists.txt",
    "web/package.json",
    "web/package-lock.json",
    "requirements-dev.txt",
    "build_v6.cmd",
)

CONTRACT_CORE_FILES = (
    "docs/00_CORE.md",
    "docs/04_execution_flow.md",
    "docs/03_quality_gates.md",
    "AGENTS.md",
    "ai_context/00_AI_CONTRACT.md",
    "ai_context/CTCP_FAST_RULES.md",
)

CONTRACT_DIR_PREFIXES = (
    "contracts/",
)


def _run_git(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        )
    except Exception:
        return None


def _git_changed_files() -> list[str]:
    a = _run_git(["diff", "--name-only"]) or ""
    b = _run_git(["diff", "--cached", "--name-only"]) or ""
    c = _run_git(["ls-files", "--others", "--exclude-standard"]) or ""
    files = {x.strip() for x in (a + "\n" + b + "\n" + c).splitlines() if x.strip()}
    return sorted(files)


def _is_code_path(path: str) -> bool:
    if path in CODE_FILES:
        return True
    return any(path.startswith(p) for p in CODE_DIR_PREFIXES)


def _is_contract_path(path: str) -> bool:
    if path in CONTRACT_CORE_FILES:
        return True
    return any(path.startswith(p) for p in CONTRACT_DIR_PREFIXES)


def classify(changed_files: list[str]) -> tuple[str, list[str], list[str]]:
    """Return (profile, code_files, contract_files)."""
    code_files = [p for p in changed_files if _is_code_path(p)]
    contract_files = [p for p in changed_files if _is_contract_path(p)]

    if code_files:
        return "code", code_files, contract_files
    if contract_files:
        return "contract", code_files, contract_files
    return "doc-only", code_files, contract_files


def main() -> int:
    use_json = "--json" in sys.argv

    changed = _git_changed_files()
    if not changed:
        profile = "doc-only"
        code_files: list[str] = []
        contract_files: list[str] = []
    else:
        profile, code_files, contract_files = classify(changed)

    if use_json:
        print(json.dumps({
            "profile": profile,
            "changed_count": len(changed),
            "code_files": code_files,
            "contract_files": contract_files,
        }))
    else:
        print(profile)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
