#!/usr/bin/env python3
from __future__ import annotations

import locale
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from tools.formal_api_lock import formal_api_only_enabled, requires_formal_api

ROOT = Path(__file__).resolve().parents[2]


def _sanitize(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "item"


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", (text or "").strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "goal"


def _read_text(path: Path, limit: int = 20000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > limit:
        return text[:limit] + "\n\n[truncated]"
    return text


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _first_non_empty_line(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _default_plan_cmd(repo_root: Path) -> str:
    script = repo_root / "scripts" / "externals" / "openai_plan_api.py"
    return (
        f'"{sys.executable}" "{script}" '
        '"{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}" '
        '"{GOAL}" "{ROUND}" "{REPO_ROOT}"'
    )


def _default_patch_cmd(repo_root: Path) -> str:
    script = repo_root / "scripts" / "externals" / "openai_patch_api.py"
    return (
        f'"{sys.executable}" "{script}" '
        '"{PLAN_PATH}" "{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}" '
        '"{GOAL}" "{ROUND}" "{REPO_ROOT}"'
    )


def _default_agent_cmd(repo_root: Path) -> str:
    script = repo_root / "scripts" / "externals" / "openai_agent_api.py"
    return f'"{sys.executable}" "{script}"'


def _format_cmd_template(template: str, values: dict[str, str]) -> tuple[str, str]:
    text = (template or "").strip()
    if not text:
        return "", "empty command template"
    if "{" not in text:
        return text, ""
    try:
        return text.format(**values), ""
    except Exception as exc:
        return "", f"command template formatting failed: {exc}"


def _shell_safe_template_text(value: Any) -> str:
    text = str(value or "").replace('"', "'")
    return re.sub(r"\s+", " ", text).strip()


def _decode_subprocess_score(text: str) -> tuple[int, int, int, int]:
    raw = str(text or "")
    replacement = raw.count("\ufffd")
    cjk = 0
    suspicious = 0
    weird_script = 0
    for ch in raw:
        if "\u4e00" <= ch <= "\u9fff":
            cjk += 1
            continue
        if ch.isascii() or ch.isspace():
            continue
        if ch in ".,!?;:'\"()[]{}<>/\\-_+=@#$%^&*~`|，。！？；：（）【】《》、":
            continue
        suspicious += 1
        code = ord(ch)
        if (0x00C0 <= code <= 0x024F) or (0x0370 <= code <= 0x052F) or (0x0600 <= code <= 0x06FF):
            weird_script += 1
    return (replacement, 0 if cjk else 1, suspicious + weird_script - (cjk * 2), -cjk)


def _decode_subprocess_text(data: bytes) -> str:
    if not data:
        return ""

    encodings: list[str] = ["utf-8", "utf-8-sig"]
    preferred = str(locale.getpreferredencoding(False) or "").strip()
    known = {enc.lower() for enc in encodings}
    for item in (preferred, "gb18030", "gbk", "cp936", "latin-1"):
        low = item.lower()
        if item and low not in known:
            encodings.append(item)
            known.add(low)

    best_text = data.decode("utf-8", errors="replace")
    best_score = _decode_subprocess_score(best_text)
    for encoding in encodings[1:]:
        try:
            candidate = data.decode(encoding, errors="replace")
        except Exception:
            continue
        score = _decode_subprocess_score(candidate)
        if score < best_score:
            best_text = candidate
            best_score = score
        if score[0] == 0 and score[1] == 0 and score[2] <= 0:
            return candidate
    return best_text


def _run_command(
    cmd: str,
    *,
    cwd: Path,
    stdin_text: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    if extra_env:
        for key, value in extra_env.items():
            env[str(key)] = str(value)
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        env=env,
        input=str(stdin_text or "").encode("utf-8"),
        capture_output=True,
        text=False,
    )
    return subprocess.CompletedProcess(
        args=proc.args,
        returncode=proc.returncode,
        stdout=_decode_subprocess_text(proc.stdout or b""),
        stderr=_decode_subprocess_text(proc.stderr or b""),
    )


def resolve_templates(
    repo_root: Path,
    request: dict[str, Any],
    *,
    needs_plan: Callable[[dict[str, Any]], bool],
    needs_patch: Callable[[dict[str, Any]], bool],
    agent_tpl: str,
    plan_tpl: str,
    patch_tpl: str,
    is_api_env_ready: Callable[[], tuple[bool, str]],
    default_plan_cmd: Callable[[Path], str] = _default_plan_cmd,
    default_patch_cmd: Callable[[Path], str] = _default_patch_cmd,
    default_agent_cmd: Callable[[Path], str] = _default_agent_cmd,
) -> tuple[dict[str, str], str]:
    wants_plan = needs_plan(request)
    wants_patch = needs_patch(request)

    templates: dict[str, str] = {}
    if wants_plan:
        templates["plan"] = str(plan_tpl or agent_tpl).strip()
    if wants_patch:
        templates["patch"] = str(patch_tpl or agent_tpl).strip()

    missing_cmd = (wants_plan and not templates.get("plan")) or (wants_patch and not templates.get("patch"))
    if missing_cmd:
        ready, reason = is_api_env_ready()
        if not ready:
            return {}, reason
        if wants_plan and not templates.get("plan"):
            templates["plan"] = default_plan_cmd(repo_root)
        if wants_patch and not templates.get("patch"):
            templates["patch"] = default_patch_cmd(repo_root)

    if not wants_plan and not wants_patch:
        if str(agent_tpl).strip():
            templates["agent"] = str(agent_tpl).strip()
            return templates, ""
        ready, reason = is_api_env_ready()
        if not ready:
            return {}, reason
        templates["agent"] = default_agent_cmd(repo_root)

    if wants_plan and not wants_patch and "plan" in templates and "agent" not in templates:
        templates["agent"] = templates["plan"]

    return templates, ""


def preview(
    *,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    resolve_templates_fn: Callable[[Path, dict[str, Any]], tuple[dict[str, str], str]],
    needs_patch_fn: Callable[[dict[str, Any]], bool],
    repo_root: Path | None = None,
) -> dict[str, Any]:
    _ = (run_dir, config)
    templates, reason = resolve_templates_fn(repo_root or ROOT, request)
    if not templates:
        return {"status": "disabled", "reason": reason}
    if needs_patch_fn(request):
        return {"status": "can_exec", "writes": ["outbox/PLAN.md", "outbox/diff.patch"]}
    return {"status": "can_exec"}


@dataclass(frozen=True)
class ApiProviderHooks:
    resolve_templates: Callable[[Path, dict[str, Any]], tuple[dict[str, str], str]]
    build_evidence_pack: Callable[..., dict[str, Path]]
    render_prompt: Callable[..., str]
    record_failure_review: Callable[[Path, str], Path]
    needs_patch: Callable[[dict[str, Any]], bool]
    normalize_patch_payload: Callable[[str], tuple[str, str]]
    normalize_target_payload: Callable[..., tuple[str, str]]


def _failure_result(
    *,
    run_dir: Path,
    review_path: Path,
    reason: str,
    cmd: str = "",
    rc: int | None = None,
    stdout_log: Path | None = None,
    stderr_log: Path | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "exec_failed",
        "reason": reason,
        "review": review_path.relative_to(run_dir).as_posix(),
    }
    if cmd:
        result["cmd"] = cmd
    if rc is not None:
        result["rc"] = rc
    if stdout_log is not None:
        result["stdout_log"] = stdout_log.relative_to(run_dir).as_posix()
    if stderr_log is not None:
        result["stderr_log"] = stderr_log.relative_to(run_dir).as_posix()
    return result


def _build_placeholders(
    *,
    prompt_path: Path,
    plan_out: Path,
    patch_out: Path,
    target_path: Path,
    evidence: dict[str, Path],
    request: dict[str, Any],
    repo_root: Path,
    run_dir: Path,
) -> dict[str, str]:
    role = str(request.get("role", ""))
    action = str(request.get("action", ""))
    return {
        "PROMPT_PATH": str(prompt_path),
        "PLAN_PATH": str(plan_out),
        "PATCH_PATH": str(patch_out),
        "TARGET_PATH": str(target_path),
        "CONTEXT_PATH": str(evidence["context"]),
        "CONSTRAINTS_PATH": str(evidence["constraints"]),
        "FIX_BRIEF_PATH": str(evidence["fix_brief"]),
        "EXTERNALS_PATH": str(evidence["externals"]),
        "GOAL": _shell_safe_template_text(request.get("goal", "")),
        "REASON": _shell_safe_template_text(request.get("reason", "")),
        "ROLE": role,
        "ACTION": action,
        "RUN_DIR": str(run_dir),
        "REPO_ROOT": str(repo_root),
        "ROUND": "1",
    }


def _build_api_call_env(*, run_dir: Path, request: dict[str, Any]) -> dict[str, str]:
    return {
        "CTCP_API_CALLS_PATH": str(run_dir / "api_calls.jsonl"),
        "CTCP_API_ROLE": str(request.get("role", "")),
        "CTCP_API_ACTION": str(request.get("action", "")),
    }


def _safe_int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return max(minimum, min(maximum, value))


def _safe_float_env(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except Exception:
        return default
    return max(minimum, min(maximum, value))


def _is_chair_deliver_request(request: dict[str, Any]) -> bool:
    return (
        str(request.get("role", "")).strip().lower() == "chair"
        and str(request.get("action", "")).strip().lower() == "deliver"
    )


_TRANSIENT_TRANSPORT_MARKERS = (
    "ssl:",
    "tls",
    "protocol_version",
    "wrong version number",
    "bad record mac",
    "remote end closed",
    "connection reset",
    "connection aborted",
    "connection refused",
    "temporarily unavailable",
    "timed out",
    "timeout",
    "read operation timed out",
    "connection timed out",
    "urlerror",
)


def _is_transient_transport_error(*texts: str) -> bool:
    combined = "\n".join(str(text or "") for text in texts).lower()
    if not combined:
        return False
    return any(marker in combined for marker in _TRANSIENT_TRANSPORT_MARKERS)


def _agent_retry_policy(request: dict[str, Any]) -> tuple[int, float]:
    if not _is_chair_deliver_request(request):
        return 1, 0.0
    attempts = _safe_int_env("CTCP_DELIVER_API_MAX_ATTEMPTS", 4, minimum=1, maximum=8)
    base_delay = _safe_float_env("CTCP_DELIVER_API_RETRY_BASE_DELAY_SEC", 1.5, minimum=0.0, maximum=30.0)
    return attempts, base_delay


def _write_agent_attempt_logs(logs_dir: Path, attempt: int, stdout: str, stderr: str) -> tuple[Path, Path]:
    stdout_path = logs_dir / f"agent.attempt_{attempt:02d}.stdout"
    stderr_path = logs_dir / f"agent.attempt_{attempt:02d}.stderr"
    _write_text(stdout_path, stdout)
    _write_text(stderr_path, stderr)
    return stdout_path, stderr_path


def _append_agent_retry_log(logs_dir: Path, row: dict[str, Any]) -> None:
    path = logs_dir / "agent_retry.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _fallback_plan_payload(*, hooks: ApiProviderHooks, repo_root: Path, run_dir: Path, request: dict[str, Any]) -> str:
    target_rel = str(request.get("target_path", "")).strip().lower()
    fallback_request = dict(request)
    fallback_target = "artifacts/PLAN.md" if target_rel.endswith("artifacts/plan.md") else "artifacts/PLAN_draft.md"
    fallback_request["target_path"] = fallback_target
    payload, _err = hooks.normalize_target_payload(
        repo_root=repo_root,
        run_dir=run_dir,
        request=fallback_request,
        raw_text="",
    )
    return payload if payload.endswith("\n") else (payload + "\n")


def _fallback_target_result(
    *,
    hooks: ApiProviderHooks,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    target_path: Path,
    target_rel: str,
    prompt_path: Path,
    logs_dir: Path,
    phase: str,
    reason: str,
) -> dict[str, Any]:
    role = str(request.get("role", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    if formal_api_only_enabled() and requires_formal_api(role, action):
        blocked_reason = f"formal_api_only blocked local fallback for role={role} action={action}: {reason}"
        review = hooks.record_failure_review(run_dir, blocked_reason)
        return _failure_result(
            run_dir=run_dir,
            review_path=review,
            reason=blocked_reason,
            stdout_log=logs_dir / f"{phase}.stdout",
            stderr_log=logs_dir / f"{phase}.stderr",
        )
    if role in {"contract_guardian", "cost_controller"} or action.startswith("review_") or "review" in action:
        blocked_reason = f"review provider fallback blocked: {reason}"
        review = hooks.record_failure_review(run_dir, blocked_reason)
        return _failure_result(
            run_dir=run_dir,
            review_path=review,
            reason=blocked_reason,
            stdout_log=logs_dir / f"{phase}.stdout",
            stderr_log=logs_dir / f"{phase}.stderr",
        )
    payload, norm_err = hooks.normalize_target_payload(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        raw_text="",
    )
    if norm_err:
        review = hooks.record_failure_review(run_dir, norm_err)
        return _failure_result(run_dir=run_dir, review_path=review, reason=norm_err)
    _write_text(target_path, payload if payload.endswith("\n") else (payload + "\n"))
    return {
        "status": "executed",
        "target_path": target_rel,
        "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        "stdout_log": (logs_dir / f"{phase}.stdout").relative_to(run_dir).as_posix(),
        "stderr_log": (logs_dir / f"{phase}.stderr").relative_to(run_dir).as_posix(),
        "fallback_used": True,
        "fallback_reason": reason,
        "local_function_used": "llm_core.providers.api_provider._fallback_target_result",
    }


def _run_plan_phase(
    *,
    template: str,
    placeholders: dict[str, str],
    repo_root: Path,
    run_dir: Path,
    logs_dir: Path,
    prompt_text: str,
    api_call_env: dict[str, str],
    hooks: ApiProviderHooks,
    plan_out: Path,
    request: dict[str, Any],
) -> dict[str, Any] | None:
    cmd, fmt_err = _format_cmd_template(template, placeholders)
    if fmt_err:
        review = hooks.record_failure_review(run_dir, fmt_err)
        return _failure_result(run_dir=run_dir, review_path=review, reason=fmt_err)

    proc = _run_command(cmd, cwd=repo_root, stdin_text=prompt_text, extra_env=api_call_env)
    plan_stdout = logs_dir / "plan_agent.stdout"
    plan_stderr = logs_dir / "plan_agent.stderr"
    _write_text(plan_stdout, proc.stdout)
    _write_text(plan_stderr, proc.stderr)
    if proc.returncode != 0:
        if not hooks.needs_patch(request):
            if formal_api_only_enabled() and requires_formal_api(str(request.get("role", "")), str(request.get("action", ""))):
                reason = f"formal_api_only blocked local plan fallback rc={proc.returncode}"
                review = hooks.record_failure_review(run_dir, reason)
                return _failure_result(
                    run_dir=run_dir,
                    review_path=review,
                    reason=reason,
                    cmd=cmd,
                    rc=proc.returncode,
                    stdout_log=plan_stdout,
                    stderr_log=plan_stderr,
                )
            _write_text(plan_out, _fallback_plan_payload(hooks=hooks, repo_root=repo_root, run_dir=run_dir, request=request))
            placeholders["PLAN_PATH"] = str(plan_out)
            return None
        reason = f"plan agent command failed rc={proc.returncode}"
        review = hooks.record_failure_review(run_dir, reason)
        return _failure_result(
            run_dir=run_dir,
            review_path=review,
            reason=reason,
            cmd=cmd,
            rc=proc.returncode,
            stdout_log=plan_stdout,
            stderr_log=plan_stderr,
        )
    plan_text = (proc.stdout or "").strip()
    if not plan_text:
        if not hooks.needs_patch(request):
            if formal_api_only_enabled() and requires_formal_api(str(request.get("role", "")), str(request.get("action", ""))):
                reason = "formal_api_only blocked empty-output local plan fallback"
                review = hooks.record_failure_review(run_dir, reason)
                return _failure_result(
                    run_dir=run_dir,
                    review_path=review,
                    reason=reason,
                    cmd=cmd,
                    stdout_log=plan_stdout,
                    stderr_log=plan_stderr,
                )
            _write_text(plan_out, _fallback_plan_payload(hooks=hooks, repo_root=repo_root, run_dir=run_dir, request=request))
            placeholders["PLAN_PATH"] = str(plan_out)
            return None
        reason = "plan agent output is empty"
        review = hooks.record_failure_review(run_dir, reason)
        return _failure_result(
            run_dir=run_dir,
            review_path=review,
            reason=reason,
            cmd=cmd,
            stdout_log=plan_stdout,
            stderr_log=plan_stderr,
        )
    _write_text(plan_out, plan_text + "\n")
    placeholders["PLAN_PATH"] = str(plan_out)
    return None


def _run_patch_phase(
    *,
    template: str,
    placeholders: dict[str, str],
    repo_root: Path,
    run_dir: Path,
    logs_dir: Path,
    prompt_text: str,
    api_call_env: dict[str, str],
    hooks: ApiProviderHooks,
    plan_out: Path,
    patch_out: Path,
    target_path: Path,
    target_rel: str,
    prompt_path: Path,
) -> dict[str, Any] | None:
    cmd, fmt_err = _format_cmd_template(template, placeholders)
    if fmt_err:
        review = hooks.record_failure_review(run_dir, fmt_err)
        return _failure_result(run_dir=run_dir, review_path=review, reason=fmt_err)

    proc = _run_command(cmd, cwd=repo_root, stdin_text=prompt_text, extra_env=api_call_env)
    patch_stdout = logs_dir / "patch_agent.stdout"
    patch_stderr = logs_dir / "patch_agent.stderr"
    _write_text(patch_stdout, proc.stdout)
    _write_text(patch_stderr, proc.stderr)
    if proc.returncode != 0:
        reason = f"patch agent command failed rc={proc.returncode}"
        review = hooks.record_failure_review(run_dir, reason)
        return _failure_result(
            run_dir=run_dir,
            review_path=review,
            reason=reason,
            cmd=cmd,
            rc=proc.returncode,
            stdout_log=patch_stdout,
            stderr_log=patch_stderr,
        )
    patch_text, patch_norm_err = hooks.normalize_patch_payload(proc.stdout or "")
    if patch_norm_err:
        review = hooks.record_failure_review(run_dir, patch_norm_err)
        return _failure_result(
            run_dir=run_dir,
            review_path=review,
            reason=patch_norm_err,
            cmd=cmd,
            stdout_log=patch_stdout,
            stderr_log=patch_stderr,
        )
    first = _first_non_empty_line(patch_text)
    if first != "" and not first.startswith("diff --git"):
        reason = "patch output must start with diff --git"
        review = hooks.record_failure_review(run_dir, reason)
        return _failure_result(
            run_dir=run_dir,
            review_path=review,
            reason=reason,
            cmd=cmd,
            stdout_log=patch_stdout,
            stderr_log=patch_stderr,
        )
    patch_payload = patch_text if patch_text.endswith("\n") else (patch_text + "\n")
    _write_text(patch_out, patch_payload)
    _write_text(target_path, patch_payload)
    return {
        "status": "executed",
        "target_path": target_rel or "artifacts/diff.patch",
        "plan_path": plan_out.relative_to(run_dir).as_posix(),
        "patch_path": patch_out.relative_to(run_dir).as_posix(),
        "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        "stdout_log": patch_stdout.relative_to(run_dir).as_posix(),
        "stderr_log": patch_stderr.relative_to(run_dir).as_posix(),
    }


def _run_agent_phase(
    *,
    template: str,
    placeholders: dict[str, str],
    repo_root: Path,
    run_dir: Path,
    logs_dir: Path,
    prompt_text: str,
    api_call_env: dict[str, str],
    hooks: ApiProviderHooks,
    request: dict[str, Any],
    target_path: Path,
    target_rel: str,
    prompt_path: Path,
) -> dict[str, Any]:
    cmd, fmt_err = _format_cmd_template(template, placeholders)
    if fmt_err:
        review = hooks.record_failure_review(run_dir, fmt_err)
        return _failure_result(run_dir=run_dir, review_path=review, reason=fmt_err)

    agent_stdout = logs_dir / "agent.stdout"
    agent_stderr = logs_dir / "agent.stderr"
    max_attempts, base_delay = _agent_retry_policy(request)
    retry_errors: list[dict[str, Any]] = []

    proc: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, max_attempts + 1):
        proc = _run_command(cmd, cwd=repo_root, stdin_text=prompt_text, extra_env=api_call_env)
        attempt_stdout, attempt_stderr = _write_agent_attempt_logs(logs_dir, attempt, proc.stdout, proc.stderr)
        _write_text(agent_stdout, proc.stdout)
        _write_text(agent_stderr, proc.stderr)
        if proc.returncode == 0:
            if attempt > 1:
                _append_agent_retry_log(
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
            break

        transient = _is_transient_transport_error(proc.stdout, proc.stderr)
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
            break
        _append_agent_retry_log(
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

    if proc is None:
        proc = subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="agent command was not executed")

    if proc.returncode != 0:
        result = _fallback_target_result(
            hooks=hooks,
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            target_path=target_path,
            target_rel=target_rel,
            prompt_path=prompt_path,
            logs_dir=logs_dir,
            phase="agent",
            reason=f"agent command failed rc={proc.returncode}",
        )
        if retry_errors:
            result["api_retry_attempts"] = len(retry_errors)
            result["api_retry_errors"] = retry_errors
            result["api_retry_log"] = (logs_dir / "agent_retry.jsonl").relative_to(run_dir).as_posix()
        return result

    target_payload, norm_err = hooks.normalize_target_payload(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        raw_text=(proc.stdout or "").rstrip(),
    )
    if norm_err:
        result = _fallback_target_result(
            hooks=hooks,
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            target_path=target_path,
            target_rel=target_rel,
            prompt_path=prompt_path,
            logs_dir=logs_dir,
            phase="agent",
            reason=norm_err,
        )
        if retry_errors:
            result["api_retry_attempts"] = len(retry_errors)
            result["api_retry_errors"] = retry_errors
            result["api_retry_log"] = (logs_dir / "agent_retry.jsonl").relative_to(run_dir).as_posix()
        return result
    _write_text(target_path, target_payload)
    result = {
        "status": "executed",
        "target_path": target_rel,
        "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        "stdout_log": agent_stdout.relative_to(run_dir).as_posix(),
        "stderr_log": agent_stderr.relative_to(run_dir).as_posix(),
    }
    if max_attempts > 1:
        result["api_retry_attempts"] = (len(retry_errors) + 1) if retry_errors else 1
        result["api_retry_max_attempts"] = max_attempts
    if retry_errors:
        result["api_retry_errors"] = retry_errors
        result["api_retry_log"] = (logs_dir / "agent_retry.jsonl").relative_to(run_dir).as_posix()
    return result


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
    hooks: ApiProviderHooks,
) -> dict[str, Any]:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    templates, reason = hooks.resolve_templates(repo_root, request)
    if not templates:
        review = hooks.record_failure_review(run_dir, reason)
        return {
            "status": "disabled",
            "reason": reason,
            "review": review.relative_to(run_dir).as_posix(),
        }

    evidence = hooks.build_evidence_pack(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    prompt_text = hooks.render_prompt(run_dir=run_dir, repo_root=repo_root, request=request, evidence=evidence)

    role = str(request.get("role", ""))
    action = str(request.get("action", ""))
    prompt_path = run_dir / "outbox" / f"AGENT_PROMPT_{_sanitize(role)}_{_sanitize(action)}.md"
    _write_text(prompt_path, prompt_text)

    plan_out = run_dir / "outbox" / "PLAN.md"
    patch_out = run_dir / "outbox" / "diff.patch"
    target_rel = str(request.get("target_path", "")).strip()
    target_path = (run_dir / target_rel).resolve() if target_rel else run_dir / "artifacts" / "diff.patch"

    placeholders = _build_placeholders(
        prompt_path=prompt_path,
        plan_out=plan_out,
        patch_out=patch_out,
        target_path=target_path,
        evidence=evidence,
        request=request,
        repo_root=repo_root,
        run_dir=run_dir,
    )
    api_call_env = _build_api_call_env(run_dir=run_dir, request=request)

    if "plan" in templates:
        failure = _run_plan_phase(
            template=templates["plan"],
            placeholders=placeholders,
            repo_root=repo_root,
            run_dir=run_dir,
            logs_dir=logs_dir,
            prompt_text=prompt_text,
            api_call_env=api_call_env,
            hooks=hooks,
            plan_out=plan_out,
            request=request,
        )
        if failure:
            return failure

    if "patch" in templates:
        patch_result = _run_patch_phase(
            template=templates["patch"],
            placeholders=placeholders,
            repo_root=repo_root,
            run_dir=run_dir,
            logs_dir=logs_dir,
            prompt_text=prompt_text,
            api_call_env=api_call_env,
            hooks=hooks,
            plan_out=plan_out,
            patch_out=patch_out,
            target_path=target_path,
            target_rel=target_rel,
            prompt_path=prompt_path,
        )
        if patch_result:
            return patch_result

    agent_tpl = templates.get("agent") or templates.get("plan")
    if not agent_tpl:
        available_keys = ", ".join(sorted(templates.keys())) or "(none)"
        reason = (
            "missing agent template "
            f"(role={role}, action={action}, plan={bool('plan' in templates)}, "
            f"patch={bool('patch' in templates)}, keys={available_keys})"
        )
        review = hooks.record_failure_review(run_dir, reason)
        return {
            "status": "exec_failed",
            "reason": reason,
            "review": review.relative_to(run_dir).as_posix(),
        }

    return _run_agent_phase(
        template=agent_tpl,
        placeholders=placeholders,
        repo_root=repo_root,
        run_dir=run_dir,
        logs_dir=logs_dir,
        prompt_text=prompt_text,
        api_call_env=api_call_env,
        hooks=hooks,
        request=request,
        target_path=target_path,
        target_rel=target_rel,
        prompt_path=prompt_path,
    )


__all__ = [
    "ApiProviderHooks",
    "_decode_subprocess_score",
    "_decode_subprocess_text",
    "_default_agent_cmd",
    "_default_patch_cmd",
    "_default_plan_cmd",
    "_first_non_empty_line",
    "_format_cmd_template",
    "_read_text",
    "_run_command",
    "_sanitize",
    "_shell_safe_template_text",
    "_slug",
    "_write_text",
    "execute",
    "preview",
    "resolve_templates",
]
