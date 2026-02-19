#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


def execute(*, repo_root: Path, run_dir: Path, request: dict[str, Any]) -> dict[str, Any]:
    role = str(request.get("role", ""))
    action = str(request.get("action", ""))
    target_path = str(request.get("target_path", ""))
    if role != "librarian" or action != "context_pack":
        return {
            "status": "forbidden",
            "reason": "local_exec is restricted to role=librarian action=context_pack",
        }

    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = logs_dir / "dispatch_local_exec_librarian.stdout.log"
    stderr_log = logs_dir / "dispatch_local_exec_librarian.stderr.log"

    cmd = [sys.executable, str(repo_root / "scripts" / "ctcp_librarian.py"), "--run-dir", str(run_dir)]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout_log.write_text(proc.stdout, encoding="utf-8")
    stderr_log.write_text(proc.stderr, encoding="utf-8")

    target = run_dir / target_path
    if proc.returncode == 0 and target.exists():
        return {
            "status": "executed",
            "target_path": target_path,
            "cmd": " ".join(cmd),
            "rc": proc.returncode,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        }

    return {
        "status": "exec_failed",
        "reason": f"local_exec command failed rc={proc.returncode}",
        "target_path": target_path,
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
        "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
    }

