#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.checks.plan_contract import load_plan_contract


def _run_git(repo: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def _changed_files(repo: Path) -> list[str]:
    a = _run_git(repo, ["diff", "--name-only"])
    b = _run_git(repo, ["diff", "--cached", "--name-only"])
    c = _run_git(repo, ["ls-files", "--others", "--exclude-standard"])
    files = {x.strip().replace("\\", "/") for x in (a + "\n" + b + "\n" + c).splitlines() if x.strip()}
    return sorted(files)


def _path_in_root(path: str, root: str) -> bool:
    r = root.strip().replace("\\", "/").strip("/")
    p = path.strip().replace("\\", "/").strip("/")
    if not r:
        return False
    return p == r or p.startswith(r + "/")


def main() -> int:
    # BEHAVIOR_ID: B011
    ap = argparse.ArgumentParser(description="Patch scope gate enforced by artifacts/PLAN.md")
    ap.add_argument("--repo", default=".", help="repo root")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    plan_path = repo / "artifacts" / "PLAN.md"

    plan, errors = load_plan_contract(plan_path)
    if plan is None:
        for e in errors:
            print(f"[patch_check][error] {e}")
        print("[patch_check][error] patch_check requires parseable artifacts/PLAN.md")
        return 1

    try:
        changed = _changed_files(repo)
    except Exception as exc:
        print(f"[patch_check][error] {exc}")
        return 1

    max_files = int(plan.budgets.get("max_files", 0))
    if max_files > 0 and len(changed) > max_files:
        print(f"[patch_check][error] changed file count exceeds PLAN max_files ({len(changed)} > {max_files})")
        return 1

    scope_allow = list(plan.scope_allow)
    scope_deny = list(plan.scope_deny)
    for path in changed:
        if scope_allow and not any(_path_in_root(path, root) for root in scope_allow):
            print(f"[patch_check][error] out-of-scope path (Scope-Allow): {path}")
            return 1
        if any(_path_in_root(path, root) for root in scope_deny):
            print(f"[patch_check][error] denied path (Scope-Deny): {path}")
            return 1

    print(f"[patch_check] ok (changed_files={len(changed)} max_files={max_files})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
