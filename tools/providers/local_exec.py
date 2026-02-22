#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

try:
    from tools import contract_guard
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools import contract_guard


def _run_librarian(repo_root: Path, run_dir: Path, target_path: str) -> dict[str, Any]:
    # BEHAVIOR_ID: B029
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


def _render_contract_review_md(review: dict[str, Any]) -> str:
    guard = review.get("contract_guard", {}) if isinstance(review, dict) else {}
    passed = bool(guard.get("pass", False))
    verdict = "APPROVE" if passed else "BLOCK"
    reasons = [str(x) for x in guard.get("reasons", []) if str(x).strip()]
    touched = [str(x) for x in guard.get("touched_files", []) if str(x).strip()]
    lines = [
        "# Contract Review",
        "",
        f"Verdict: {verdict}",
        "",
        "Blocking Reasons:",
    ]
    if reasons:
        for row in reasons:
            lines.append(f"- {row}")
    else:
        lines.append("- none")

    lines += [
        "",
        "Required Fix/Artifacts:",
    ]
    if passed:
        lines.append("- none")
    else:
        lines.append("- Keep changes inside contracts/allowed_changes.yaml scope.")
        lines.append("- Re-generate patch and rerun contract review.")

    lines += [
        "",
        "Touched Files:",
    ]
    if touched:
        for row in touched:
            lines.append(f"- {row}")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _run_contract_guardian(repo_root: Path, run_dir: Path, target_path: str) -> dict[str, Any]:
    # BEHAVIOR_ID: B030
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = logs_dir / "dispatch_local_exec_contract_guardian.stdout.log"
    stderr_log = logs_dir / "dispatch_local_exec_contract_guardian.stderr.log"

    policy_path = repo_root / "contracts" / "allowed_changes.yaml"
    review_json = run_dir / "reviews" / "contract_review.json"
    review_md = run_dir / target_path
    review_json.parent.mkdir(parents=True, exist_ok=True)
    review_md.parent.mkdir(parents=True, exist_ok=True)

    try:
        review = contract_guard.evaluate(
            repo_root,
            policy_path=policy_path,
            out_path=review_json,
        )
    except Exception as exc:
        stdout_log.write_text("", encoding="utf-8")
        stderr_log.write_text(str(exc) + "\n", encoding="utf-8")
        return {
            "status": "exec_failed",
            "reason": f"contract_guard execution failed: {exc}",
            "target_path": target_path,
            "cmd": "contract_guard.evaluate",
            "rc": 1,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        }

    review_md.write_text(_render_contract_review_md(review), encoding="utf-8")
    guard = review.get("contract_guard", {}) if isinstance(review, dict) else {}
    passed = bool(guard.get("pass", False))
    reasons = [str(x) for x in guard.get("reasons", []) if str(x).strip()]
    stdout_log.write_text(
        json.dumps(
            {
                "pass": passed,
                "reasons": reasons,
                "review_json": review_json.relative_to(run_dir).as_posix(),
                "review_md": review_md.relative_to(run_dir).as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    stderr_log.write_text("", encoding="utf-8")

    if passed:
        return {
            "status": "executed",
            "target_path": target_path,
            "cmd": "contract_guard.evaluate",
            "rc": 0,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        }

    return {
        "status": "exec_failed",
        "reason": "contract_guard failed: " + ("; ".join(reasons) if reasons else "policy violation"),
        "target_path": target_path,
        "cmd": "contract_guard.evaluate",
        "rc": 1,
        "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
        "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
    }


def execute(*, repo_root: Path, run_dir: Path, request: dict[str, Any]) -> dict[str, Any]:
    role = str(request.get("role", ""))
    action = str(request.get("action", ""))
    target_path = str(request.get("target_path", ""))

    if role == "librarian" and action == "context_pack":
        return _run_librarian(repo_root=repo_root, run_dir=run_dir, target_path=target_path)
    if role == "contract_guardian" and action == "review_contract":
        return _run_contract_guardian(repo_root=repo_root, run_dir=run_dir, target_path=target_path)
    return {
        "status": "forbidden",
        "reason": (
            "local_exec is restricted to role=librarian action=context_pack "
            "or role=contract_guardian action=review_contract"
        ),
    }
