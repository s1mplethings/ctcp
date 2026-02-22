#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from tools.providers import manual_outbox


def _to_bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


def _sanitize(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "item"


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _first_non_empty_line(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _provider_cfg(config: dict[str, Any]) -> dict[str, Any]:
    providers = config.get("providers", {}) if isinstance(config, dict) else {}
    if not isinstance(providers, dict):
        providers = {}
    raw = providers.get("codex_agent", {})
    if not isinstance(raw, dict):
        raw = {}

    timeout_sec = 900
    try:
        timeout_sec = max(30, int(raw.get("timeout_sec", 900)))
    except Exception:
        timeout_sec = 900

    enabled = _to_bool(raw.get("enabled", False), False)
    env_toggle = os.environ.get("CTCP_CODEX_AGENT")
    if env_toggle is not None:
        enabled = _to_bool(env_toggle, enabled)

    return {
        "enabled": enabled,
        "dry_run": _to_bool(raw.get("dry_run", False), False),
        "cmd": str(raw.get("cmd", "codex") or "codex").strip() or "codex",
        "model": str(raw.get("model", "")).strip(),
        "timeout_sec": timeout_sec,
        "fallback_to_manual_outbox": _to_bool(raw.get("fallback_to_manual_outbox", True), True),
    }


def _prepare_workspace(repo_root: Path, run_dir: Path) -> Path:
    sandbox = run_dir / "sandbox"
    workspace = sandbox / "codex_ws"
    if workspace.exists():
        shutil.rmtree(workspace)
    sandbox.mkdir(parents=True, exist_ok=True)

    ignore = shutil.ignore_patterns(
        ".git",
        "runs",
        "build",
        "build_*",
        "dist",
        "__pycache__",
        "*.pyc",
        "*.pyo",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
    )
    shutil.copytree(repo_root, workspace, ignore=ignore)
    return workspace


def _render_codex_prompt(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> str:
    base = manual_outbox._render_prompt(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    target_rel = str(request.get("target_path", "")).strip()
    target_abs = (run_dir / target_rel).resolve()
    patch_rule = ""
    if target_rel.lower().endswith("diff.patch"):
        patch_rule = (
            "4. If target is artifacts/diff.patch, the first non-empty output line must be `diff --git`.\n"
        )
    return (
        f"{base}\n"
        "Codex CLI Execution Contract:\n"
        f"1. You may only write to this absolute target: `{target_abs}`.\n"
        "2. Do not modify repository files or any path outside run_dir.\n"
        "3. Artifact content must satisfy docs/30_artifact_contracts.md.\n"
        f"{patch_rule}"
    )


def _fallback_preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any], reason: str) -> dict[str, Any]:
    row = manual_outbox.preview(run_dir=run_dir, request=request, config=config)
    row["fallback_provider"] = "manual_outbox"
    row["reason"] = reason
    return row


def _fallback_execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
    reason: str,
) -> dict[str, Any]:
    row = manual_outbox.execute(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    row["fallback_provider"] = "manual_outbox"
    row["reason"] = reason
    return row


def preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    cfg = _provider_cfg(config)
    if not cfg["enabled"]:
        if cfg["fallback_to_manual_outbox"]:
            return _fallback_preview(
                run_dir=run_dir,
                request=request,
                config=config,
                reason="codex_agent disabled",
            )
        return {"status": "disabled", "reason": "codex_agent disabled"}
    if cfg["dry_run"]:
        if cfg["fallback_to_manual_outbox"]:
            return _fallback_preview(
                run_dir=run_dir,
                request=request,
                config=config,
                reason="codex_agent dry_run",
            )
        return {"status": "dry_run", "reason": "codex_agent dry_run"}
    if shutil.which(str(cfg["cmd"])) is None:
        if cfg["fallback_to_manual_outbox"]:
            return _fallback_preview(
                run_dir=run_dir,
                request=request,
                config=config,
                reason=f"codex command not found: {cfg['cmd']}",
            )
        return {"status": "disabled", "reason": f"codex command not found: {cfg['cmd']}"}
    return {"status": "can_exec"}


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Any]:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = logs_dir / "dispatch_codex_agent.stdout.log"
    stderr_log = logs_dir / "dispatch_codex_agent.stderr.log"

    cfg = _provider_cfg(config)
    if not cfg["enabled"]:
        if cfg["fallback_to_manual_outbox"]:
            return _fallback_execute(
                repo_root=repo_root,
                run_dir=run_dir,
                request=request,
                config=config,
                guardrails_budgets=guardrails_budgets,
                reason="codex_agent disabled",
            )
        return {"status": "disabled", "reason": "codex_agent disabled"}
    if cfg["dry_run"]:
        if cfg["fallback_to_manual_outbox"]:
            return _fallback_execute(
                repo_root=repo_root,
                run_dir=run_dir,
                request=request,
                config=config,
                guardrails_budgets=guardrails_budgets,
                reason="codex_agent dry_run",
            )
        return {"status": "dry_run", "reason": "codex_agent dry_run"}
    if shutil.which(str(cfg["cmd"])) is None:
        reason = f"codex command not found: {cfg['cmd']}"
        if cfg["fallback_to_manual_outbox"]:
            return _fallback_execute(
                repo_root=repo_root,
                run_dir=run_dir,
                request=request,
                config=config,
                guardrails_budgets=guardrails_budgets,
                reason=reason,
            )
        return {"status": "disabled", "reason": reason}
    if _is_within(run_dir, repo_root):
        reason = "run_dir must be external to repo_root for codex_agent"
        if cfg["fallback_to_manual_outbox"]:
            return _fallback_execute(
                repo_root=repo_root,
                run_dir=run_dir,
                request=request,
                config=config,
                guardrails_budgets=guardrails_budgets,
                reason=reason,
            )
        return {"status": "disabled", "reason": reason}

    target_rel = str(request.get("target_path", "")).strip()
    target_abs = (run_dir / target_rel).resolve()
    if not _is_within(target_abs, run_dir):
        return {"status": "exec_failed", "reason": f"target_path escapes run_dir: {target_rel}"}

    prompt_text = _render_codex_prompt(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    outbox = run_dir / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)
    prompt_path = outbox / f"CODEX_PROMPT_{_sanitize(str(request.get('role', '')))}_{_sanitize(str(request.get('action', '')))}.md"
    prompt_path.write_text(prompt_text, encoding="utf-8")

    workspace = _prepare_workspace(repo_root=repo_root, run_dir=run_dir)
    cmd = [
        str(cfg["cmd"]),
        "exec",
        "-",
        "--ask-for-approval",
        "never",
        "--skip-git-repo-check",
        "--cd",
        str(workspace),
        "--add-dir",
        str(run_dir),
    ]
    if cfg["model"]:
        cmd += ["--model", str(cfg["model"])]

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(run_dir),
            input=prompt_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=int(cfg["timeout_sec"]),
        )
    except subprocess.TimeoutExpired as exc:
        stdout_log.write_text((exc.stdout or ""), encoding="utf-8")
        stderr_log.write_text((exc.stderr or "") + "\n[ctcp_codex_agent] timeout\n", encoding="utf-8")
        return {
            "status": "exec_failed",
            "reason": f"codex exec timeout after {cfg['timeout_sec']}s",
            "cmd": " ".join(cmd),
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        }

    stdout_log.write_text(proc.stdout or "", encoding="utf-8")
    stderr_log.write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode != 0:
        return {
            "status": "exec_failed",
            "reason": f"codex exec failed rc={proc.returncode}",
            "cmd": " ".join(cmd),
            "rc": proc.returncode,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        }

    if not target_abs.exists() or not target_abs.is_file():
        return {
            "status": "exec_failed",
            "reason": f"target artifact missing: {target_rel}",
            "cmd": " ".join(cmd),
            "rc": proc.returncode,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        }

    payload = target_abs.read_text(encoding="utf-8", errors="replace")
    if not payload.strip():
        return {
            "status": "exec_failed",
            "reason": f"target artifact is empty: {target_rel}",
            "cmd": " ".join(cmd),
            "rc": proc.returncode,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        }

    if target_rel.lower().endswith("diff.patch"):
        first = _first_non_empty_line(payload)
        if not first.startswith("diff --git"):
            with stderr_log.open("a", encoding="utf-8") as fh:
                fh.write("\n[ctcp_codex_agent] patch validation failed: first non-empty line must start with diff --git\n")
            return {
                "status": "exec_failed",
                "reason": "patch output must start with diff --git",
                "cmd": " ".join(cmd),
                "rc": proc.returncode,
                "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
                "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
                "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
            }

    return {
        "status": "executed",
        "target_path": target_rel,
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
        "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        "workspace": workspace.relative_to(run_dir).as_posix(),
    }
