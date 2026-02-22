#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "workflow_registry" / "index.json"

try:
    import resolve_workflow
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT / "scripts"))
    import resolve_workflow


def _load_index(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_workflow_id(repo_root: Path, goal: str, workflow: str) -> str:
    explicit = workflow.strip()
    if explicit:
        return explicit
    result = resolve_workflow.resolve(goal=goal, repo=repo_root)
    selected = str(result.get("selected_workflow_id", "")).strip()
    if selected:
        return selected
    index = _load_index(INDEX_PATH)
    fallback = str(index.get("resolver_policy", {}).get("fallback_workflow_id", "")).strip()
    return fallback or "wf_minimal_patch_verify"


def _dispatch_command(
    *,
    workflow_id: str,
    repo_root: Path,
    goal: str,
    max_rounds: int,
    plan_cmd: str,
    patch_cmd: str,
    verify_cmd: str,
    require_external_plan: str,
    require_external_patch: str,
    allow_local: bool,
    no_mechanical_fallback: bool,
) -> list[str]:
    if workflow_id == "adlc_self_improve_core":
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "workflows" / "adlc_self_improve_core.py"),
            "--repo",
            str(repo_root),
            "--goal",
            goal,
            "--max-rounds",
            str(max_rounds),
            "--require-external-plan",
            require_external_plan,
            "--require-external-patch",
            require_external_patch,
        ]
        if plan_cmd.strip():
            cmd += ["--plan-cmd", plan_cmd]
        if patch_cmd.strip():
            cmd += ["--patch-cmd", patch_cmd]
        if verify_cmd.strip():
            cmd += ["--verify-cmd", verify_cmd]
        if allow_local:
            cmd += ["--allow-local"]
        if no_mechanical_fallback:
            cmd += ["--no-mechanical-fallback"]
        return cmd

    if workflow_id == "wf_minimal_patch_verify":
        cmd = [
            sys.executable,
            str(ROOT / "scripts" / "adlc_run.py"),
            "--goal",
            goal,
        ]
        if verify_cmd.strip():
            cmd += ["--verify-cmd", verify_cmd]
        return cmd

    raise SystemExit(f"[workflow_dispatch] unsupported workflow: {workflow_id}")


def main() -> int:
    # BEHAVIOR_ID: B014
    ap = argparse.ArgumentParser(description="Dispatch workflow by workflow_registry id")
    ap.add_argument("--workflow", default="")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--goal", required=True)
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--plan-cmd", default="")
    ap.add_argument("--patch-cmd", default="")
    ap.add_argument("--verify-cmd", default="")
    ap.add_argument("--require-external-plan", default="true")
    ap.add_argument("--require-external-patch", default="true")
    ap.add_argument("--allow-local", action="store_true")
    ap.add_argument("--no-mechanical-fallback", action="store_true")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve()
    workflow_id = _resolve_workflow_id(repo_root, args.goal, args.workflow)
    _ = _load_index(INDEX_PATH)
    cmd = _dispatch_command(
        workflow_id=workflow_id,
        repo_root=repo_root,
        goal=str(args.goal),
        max_rounds=max(1, int(args.max_rounds)),
        plan_cmd=str(args.plan_cmd),
        patch_cmd=str(args.patch_cmd),
        verify_cmd=str(args.verify_cmd),
        require_external_plan=str(args.require_external_plan),
        require_external_patch=str(args.require_external_patch),
        allow_local=bool(args.allow_local),
        no_mechanical_fallback=bool(args.no_mechanical_fallback),
    )
    print(f"[workflow_dispatch] workflow={workflow_id}")
    print(f"[workflow_dispatch] cmd={' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(repo_root))
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
