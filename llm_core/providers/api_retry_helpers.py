from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable


def append_agent_retry_log(logs_dir: Path, row: dict[str, Any]) -> None:
    path = logs_dir / "agent_retry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_agent_retry_succeeded(
    *,
    logs_dir: Path,
    run_dir: Path,
    request: dict[str, Any],
    attempt: int,
    max_attempts: int,
    attempt_stdout: Path,
    attempt_stderr: Path,
) -> None:
    append_agent_retry_log(
        logs_dir,
        {
            "event": "agent_retry_succeeded",
            "role": str(request.get("role", "")),
            "action": str(request.get("action", "")),
            "attempt": attempt,
            "max_attempts": max_attempts,
            "stdout_log": attempt_stdout.relative_to(run_dir).as_posix(),
            "stderr_log": attempt_stderr.relative_to(run_dir).as_posix(),
        },
    )


def handle_successful_agent_attempt(
    *,
    hooks: Any,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    proc: subprocess.CompletedProcess[str],
    attempt: int,
    max_attempts: int,
    base_delay: float,
    logs_dir: Path,
    attempt_stdout: Path,
    attempt_stderr: Path,
    retry_errors: list[dict[str, Any]],
    is_transient_transport_error: Callable[..., bool],
) -> tuple[str, str, bool]:
    target_payload, norm_err = hooks.normalize_target_payload(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        raw_text=(proc.stdout or "").rstrip(),
    )
    transient = bool(norm_err) and is_transient_transport_error(proc.stdout, proc.stderr, norm_err)
    if norm_err and transient:
        retry_errors.append(
            {
                "attempt": attempt,
                "rc": proc.returncode,
                "transient_transport_error": True,
                "normalization_error": norm_err,
                "stdout_log": attempt_stdout.relative_to(run_dir).as_posix(),
                "stderr_log": attempt_stderr.relative_to(run_dir).as_posix(),
            }
        )
        if attempt < max_attempts:
            append_agent_retry_log(
                logs_dir,
                {
                    "event": "agent_retry_scheduled",
                    "role": str(request.get("role", "")),
                    "action": str(request.get("action", "")),
                    "attempt": attempt,
                    "next_attempt": attempt + 1,
                    "max_attempts": max_attempts,
                    "reason": "transient_transport_error_after_empty_payload",
                    "delay_sec": base_delay * float(attempt),
                    "stdout_log": attempt_stdout.relative_to(run_dir).as_posix(),
                    "stderr_log": attempt_stderr.relative_to(run_dir).as_posix(),
                },
            )
            if base_delay > 0:
                time.sleep(base_delay * float(attempt))
            return target_payload, norm_err, True
    return target_payload, norm_err, False


def handle_failed_agent_attempt(
    *,
    proc: subprocess.CompletedProcess[str],
    attempt: int,
    max_attempts: int,
    base_delay: float,
    logs_dir: Path,
    run_dir: Path,
    request: dict[str, Any],
    attempt_stdout: Path,
    attempt_stderr: Path,
    retry_errors: list[dict[str, Any]],
    is_transient_transport_error: Callable[..., bool],
) -> bool:
    transient = is_transient_transport_error(proc.stdout, proc.stderr)
    retry_errors.append(
        {
            "attempt": attempt,
            "rc": proc.returncode,
            "transient_transport_error": transient,
            "stdout_log": attempt_stdout.relative_to(run_dir).as_posix(),
            "stderr_log": attempt_stderr.relative_to(run_dir).as_posix(),
        }
    )
    if not transient or attempt >= max_attempts:
        return False
    append_agent_retry_log(
        logs_dir,
        {
            "event": "agent_retry_scheduled",
            "role": str(request.get("role", "")),
            "action": str(request.get("action", "")),
            "attempt": attempt,
            "next_attempt": attempt + 1,
            "max_attempts": max_attempts,
            "reason": "transient_transport_error",
            "delay_sec": base_delay * float(attempt),
            "stdout_log": attempt_stdout.relative_to(run_dir).as_posix(),
            "stderr_log": attempt_stderr.relative_to(run_dir).as_posix(),
        },
    )
    if base_delay > 0:
        time.sleep(base_delay * float(attempt))
    return True
