#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]

try:
    from tools.providers import api_agent
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.providers import api_agent

DEFAULT_OLLAMA_BASE_URL = "http://127.0.0.1:11434/v1"
DEFAULT_OLLAMA_API_KEY = "ollama"
DEFAULT_OLLAMA_MODEL = "qwen2.5:7b-instruct"
DEFAULT_OLLAMA_START_CMD = "ollama serve"


def _as_bool(value: str, default: bool = False) -> bool:
    text = str(value).strip().lower()
    if not text:
        return default
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_int(value: str, default: int, minimum: int, maximum: int) -> int:
    try:
        out = int(str(value).strip())
    except Exception:
        return default
    if out < minimum:
        return minimum
    if out > maximum:
        return maximum
    return out


def _provider_cfg(config: dict[str, Any], request: dict[str, Any] | None = None) -> dict[str, Any]:
    providers = config.get("providers", {}) if isinstance(config, dict) else {}
    if not isinstance(providers, dict):
        providers = {}
    raw = providers.get("ollama_agent", {})
    if not isinstance(raw, dict):
        raw = {}
    librarian_request = _is_librarian_context_pack_request(request or {})

    librarian_base_url = str(raw.get("librarian_base_url", "")).strip() if librarian_request else ""
    librarian_api_key = str(raw.get("librarian_api_key", "")).strip() if librarian_request else ""
    librarian_model = str(raw.get("librarian_model", "")).strip() if librarian_request else ""
    librarian_env_base_url = str(os.environ.get("LIBRARIAN_BASE_URL", "")).strip() if librarian_request else ""
    librarian_env_api_key = str(os.environ.get("LIBRARIAN_API_KEY", "")).strip() if librarian_request else ""
    librarian_env_model = str(os.environ.get("LIBRARIAN_MODEL", "")).strip() if librarian_request else ""

    base_url = (
        librarian_base_url
        or librarian_env_base_url
        or
        str(raw.get("base_url", "")).strip()
        or str(os.environ.get("CTCP_OLLAMA_BASE_URL", "")).strip()
        or DEFAULT_OLLAMA_BASE_URL
    )
    api_key = (
        librarian_api_key
        or librarian_env_api_key
        or
        str(raw.get("api_key", "")).strip()
        or str(os.environ.get("CTCP_OLLAMA_API_KEY", "")).strip()
        or DEFAULT_OLLAMA_API_KEY
    )
    model = (
        librarian_model
        or librarian_env_model
        or
        str(raw.get("model", "")).strip()
        or str(os.environ.get("CTCP_OLLAMA_MODEL", "")).strip()
        or DEFAULT_OLLAMA_MODEL
    )
    auto_start = _as_bool(
        str(raw.get("auto_start", "")).strip() or str(os.environ.get("CTCP_OLLAMA_AUTO_START", "")).strip(),
        default=True,
    )
    start_timeout_sec = _safe_int(
        str(raw.get("start_timeout_sec", "")).strip()
        or str(os.environ.get("CTCP_OLLAMA_START_TIMEOUT_SEC", "")).strip(),
        default=20,
        minimum=3,
        maximum=120,
    )
    start_cmd = (
        str(raw.get("start_cmd", "")).strip()
        or str(os.environ.get("CTCP_OLLAMA_START_CMD", "")).strip()
        or DEFAULT_OLLAMA_START_CMD
    )
    return {
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
        "auto_start": auto_start,
        "start_timeout_sec": start_timeout_sec,
        "start_cmd": start_cmd,
    }


def _native_chat_url(base_url: str) -> str:
    parsed = urlparse(str(base_url).strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/api/chat"
    raw = str(base_url).strip().rstrip("/")
    if raw.endswith("/v1"):
        raw = raw[:-3]
    return raw + "/api/chat"


def _is_support_reply_request(request: dict[str, Any]) -> bool:
    return (
        str(request.get("role", "")).strip().lower() == "support_lead"
        and str(request.get("action", "")).strip().lower() == "reply"
    )


def _is_librarian_context_pack_request(request: dict[str, Any]) -> bool:
    return (
        str(request.get("role", "")).strip().lower() == "librarian"
        and str(request.get("action", "")).strip().lower() == "context_pack"
    )


def _extract_json_dict(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        doc = json.loads(raw)
        if isinstance(doc, dict):
            return doc
    except Exception:
        pass

    for marker in ("```json", "```"):
        if marker not in raw:
            continue
        parts = raw.split(marker)
        for block in parts:
            snippet = block.replace("```", "").strip()
            if not snippet:
                continue
            try:
                doc = json.loads(snippet)
                if isinstance(doc, dict):
                    return doc
            except Exception:
                continue

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            doc = json.loads(raw[start : end + 1])
            if isinstance(doc, dict):
                return doc
        except Exception:
            return None
    return None


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _response_message_content(doc: dict[str, Any] | None) -> str:
    if not isinstance(doc, dict):
        return ""
    message = doc.get("message")
    if isinstance(message, dict):
        return str(message.get("content", "")).strip()
    return ""


def _support_timeout_sec() -> int:
    return _safe_int(
        str(os.environ.get("CTCP_OLLAMA_TIMEOUT_SEC", "")).strip()
        or str(os.environ.get("SDDAI_OPENAI_TIMEOUT_SEC", "")).strip(),
        default=180,
        minimum=10,
        maximum=600,
    )


def _call_ollama_chat(*, cfg: dict[str, Any], prompt: str, timeout_sec: int) -> tuple[dict[str, Any] | None, str]:
    payload = {
        "model": str(cfg.get("model", "")).strip(),
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    req = urllib.request.Request(
        _native_chat_url(str(cfg.get("base_url", "")).strip()),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()[:2000]
        return None, f"Ollama API HTTP {exc.code}: {detail}"
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        return None, f"Ollama API request failed: {exc}"
    except Exception as exc:
        return None, f"Ollama API request failed: {exc}"

    try:
        doc = json.loads(body)
    except Exception as exc:
        return None, f"Ollama API returned non-JSON response: {exc}"
    if not isinstance(doc, dict):
        return None, "Ollama API response is not a JSON object"
    return doc, ""


def _normalize_support_reply_doc(raw_text: str) -> dict[str, Any] | None:
    doc = _extract_json_dict(raw_text)
    if isinstance(doc, dict):
        return {
            "reply_text": str(doc.get("reply_text", "")).strip(),
            "next_question": str(doc.get("next_question", "")).strip(),
            "actions": doc.get("actions") if isinstance(doc.get("actions"), list) else [],
            "debug_notes": str(doc.get("debug_notes", "")).strip(),
        }
    text = str(raw_text or "").strip()
    if not text:
        return None
    return {
        "reply_text": text,
        "next_question": "",
        "actions": [],
        "debug_notes": "ollama_native_text_fallback",
    }


def _execute_native_support_reply(*, run_dir: Path, request: dict[str, Any], cfg: dict[str, Any]) -> dict[str, Any]:
    target_rel = str(request.get("target_path", "")).strip()
    target_path = (run_dir / target_rel).resolve()
    try:
        target_path.relative_to(run_dir.resolve())
    except ValueError:
        return {"status": "exec_failed", "reason": f"target_path escapes run_dir: {target_rel}"}

    prompt = str(request.get("reason", "")).strip() or str(request.get("input_text", "")).strip()
    timeout_sec = _support_timeout_sec()
    stdout_log = run_dir / "logs" / "ollama_support.stdout.log"
    stderr_log = run_dir / "logs" / "ollama_support.stderr.log"

    doc, err = _call_ollama_chat(cfg=cfg, prompt=prompt, timeout_sec=timeout_sec)
    if err:
        _write_text(stderr_log, err + "\n")
        return {
            "status": "exec_failed",
            "reason": err,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        }

    response_text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    _write_text(stdout_log, response_text)
    _write_text(stderr_log, "")
    content = _response_message_content(doc)
    if not content:
        return {
            "status": "exec_failed",
            "reason": "ollama support reply is empty",
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        }

    reply_doc = _normalize_support_reply_doc(content)
    if not isinstance(reply_doc, dict):
        return {
            "status": "exec_failed",
            "reason": "ollama support reply could not be normalized",
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        }

    _write_text(target_path, json.dumps(reply_doc, ensure_ascii=False, indent=2) + "\n")
    return {
        "status": "executed",
        "target_path": target_rel,
        "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
        "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
    }


def _render_librarian_prompt(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> tuple[str, str, str]:
    file_request_path = run_dir / "artifacts" / "file_request.json"
    if not file_request_path.exists():
        return "", "", f"missing artifacts/file_request.json: {file_request_path}"
    file_request_text = file_request_path.read_text(encoding="utf-8", errors="replace")
    evidence = api_agent._build_evidence_pack(  # type: ignore[attr-defined]
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    prompt = api_agent._render_prompt(  # type: ignore[attr-defined]
        run_dir=run_dir,
        repo_root=repo_root,
        request=request,
        evidence=evidence,
    )
    prompt += "\n## FILE_REQUEST\n```json\n" + file_request_text.strip() + "\n```\n"
    return (
        prompt.replace("Provider: api_agent", "Provider: ollama_agent", 1),
        (run_dir / "outbox" / "AGENT_PROMPT_librarian_context_pack.md").relative_to(run_dir).as_posix(),
        "",
    )


def _execute_native_librarian_context_pack(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    target_rel = str(request.get("target_path", "")).strip()
    target_path = (run_dir / target_rel).resolve()
    try:
        target_path.relative_to(run_dir.resolve())
    except ValueError:
        return {
            "status": "exec_failed",
            "reason": f"target_path escapes run_dir: {target_rel}",
            "provider_mode": "local",
            "model_name": str(cfg.get("model", "")).strip(),
            "fallback_blocked": True,
        }

    ready, reason = _ensure_ollama_ready(cfg, run_dir)
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = logs_dir / "ollama_librarian.stdout.log"
    stderr_log = logs_dir / "ollama_librarian.stderr.log"
    prompt_text, prompt_rel, prompt_err = _render_librarian_prompt(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    if prompt_err:
        _write_text(stdout_log, "")
        _write_text(stderr_log, prompt_err + "\n")
        return {
            "status": "exec_failed",
            "reason": prompt_err,
            "target_path": target_rel,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "provider_mode": "local",
            "model_name": str(cfg.get("model", "")).strip(),
            "fallback_blocked": True,
        }
    _write_text(run_dir / prompt_rel, prompt_text)
    if not ready:
        _write_text(stdout_log, "")
        _write_text(stderr_log, reason + "\n")
        return {
            "status": "exec_failed",
            "reason": f"librarian local model unavailable: {reason}",
            "target_path": target_rel,
            "prompt_path": prompt_rel,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "provider_mode": "local",
            "model_name": str(cfg.get("model", "")).strip(),
            "fallback_blocked": True,
        }

    timeout_sec = _support_timeout_sec()
    doc, err = _call_ollama_chat(cfg=cfg, prompt=prompt_text, timeout_sec=timeout_sec)
    if err:
        _write_text(stdout_log, "")
        _write_text(stderr_log, err + "\n")
        return {
            "status": "exec_failed",
            "reason": f"librarian local model request failed: {err}",
            "target_path": target_rel,
            "prompt_path": prompt_rel,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "provider_mode": "local",
            "model_name": str(cfg.get("model", "")).strip(),
            "fallback_blocked": True,
        }

    response_text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    _write_text(stdout_log, response_text)
    _write_text(stderr_log, "")
    content = _response_message_content(doc)
    if not content:
        return {
            "status": "exec_failed",
            "reason": "librarian local model returned empty content",
            "target_path": target_rel,
            "prompt_path": prompt_rel,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "provider_mode": "local",
            "model_name": str(cfg.get("model", "")).strip(),
            "fallback_blocked": True,
        }

    normalized, norm_err = api_agent._normalize_json_artifact(  # type: ignore[attr-defined]
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        raw_text=content,
    )
    if norm_err:
        _write_text(stderr_log, norm_err + "\n")
        return {
            "status": "exec_failed",
            "reason": f"librarian local model normalization failed: {norm_err}",
            "target_path": target_rel,
            "prompt_path": prompt_rel,
            "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
            "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
            "provider_mode": "local",
            "model_name": str(cfg.get("model", "")).strip(),
            "fallback_blocked": True,
        }

    _write_text(target_path, normalized)
    return {
        "status": "executed",
        "target_path": target_rel,
        "prompt_path": prompt_rel,
        "stdout_log": stdout_log.relative_to(run_dir).as_posix(),
        "stderr_log": stderr_log.relative_to(run_dir).as_posix(),
        "provider_mode": "local",
        "model_name": str(cfg.get("model", "")).strip(),
        "fallback_blocked": True,
    }


@contextmanager
def _with_env(overrides: dict[str, str]) -> Iterator[None]:
    sentinel = object()
    prev: dict[str, object] = {}
    for key, value in overrides.items():
        prev[key] = os.environ.get(key, sentinel)
        os.environ[key] = value
    try:
        yield
    finally:
        for key, old in prev.items():
            if old is sentinel:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(old)


def _ollama_env(cfg: dict[str, Any]) -> dict[str, str]:
    model = str(cfg.get("model", "")).strip()
    return {
        "OPENAI_BASE_URL": str(cfg.get("base_url", "")).strip(),
        "OPENAI_API_KEY": str(cfg.get("api_key", "")).strip(),
        "CTCP_OPENAI_API_KEY": str(cfg.get("api_key", "")).strip(),
        "SDDAI_OPENAI_MODEL": model,
        "SDDAI_OPENAI_AGENT_MODEL": model,
        "SDDAI_OPENAI_PLAN_MODEL": model,
        "SDDAI_OPENAI_PATCH_MODEL": model,
    }


def _health_url(base_url: str) -> str:
    parsed = urlparse(str(base_url).strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/api/tags"
    raw = str(base_url).strip().rstrip("/")
    if raw.endswith("/v1"):
        raw = raw[:-3]
    return raw + "/api/tags"


def _check_ollama_ready(base_url: str, timeout_sec: int = 2) -> bool:
    url = _health_url(base_url)
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec):
            return True
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False
    except Exception:
        return False


def _start_ollama_service(*, cmd: str, run_dir: Path) -> tuple[bool, str]:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "ollama_serve.log"
    creationflags = 0
    if os.name == "nt":
        creationflags = int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)) | int(
            getattr(subprocess, "DETACHED_PROCESS", 0)
        )
    try:
        if os.name == "nt":
            log_path.write_text(
                "ollama service bootstrap started in detached mode; "
                "stdout/stderr redirected to os.devnull to avoid locking the run directory on Windows.\n",
                encoding="utf-8",
            )
            subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                start_new_session=False,
            )
        else:
            with log_path.open("a", encoding="utf-8") as fh:
                subprocess.Popen(
                    cmd,
                    cwd=str(ROOT),
                    shell=True,
                    stdout=fh,
                    stderr=fh,
                    creationflags=creationflags,
                    start_new_session=True,
                )
    except Exception as exc:
        return False, f"failed to start ollama service: {exc}"
    return True, ""


def _should_bootstrap_ollama() -> bool:
    return not any(
        str(os.environ.get(name, "")).strip() for name in ("SDDAI_AGENT_CMD", "SDDAI_PLAN_CMD", "SDDAI_PATCH_CMD")
    )


def _ensure_ollama_ready(cfg: dict[str, Any], run_dir: Path) -> tuple[bool, str]:
    base_url = str(cfg.get("base_url", "")).strip()
    if _check_ollama_ready(base_url):
        return True, ""
    if not bool(cfg.get("auto_start", True)):
        return False, "ollama is not running and auto_start is disabled"
    ok, err = _start_ollama_service(cmd=str(cfg.get("start_cmd", DEFAULT_OLLAMA_START_CMD)), run_dir=run_dir)
    if not ok:
        return False, err

    timeout_sec = int(cfg.get("start_timeout_sec", 20))
    deadline = time.time() + float(timeout_sec)
    while time.time() < deadline:
        if _check_ollama_ready(base_url):
            return True, ""
        time.sleep(0.5)
    return False, f"ollama did not become ready within {timeout_sec}s"


def preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    cfg = _provider_cfg(config, request=request)
    if _is_librarian_context_pack_request(request):
        ready, reason = _ensure_ollama_ready(cfg, run_dir)
        if not ready:
            return {
                "status": "disabled",
                "reason": reason,
                "runtime": "ollama",
                "provider_mode": "local",
                "model_name": cfg["model"],
                "fallback_blocked": True,
                "ollama_base_url": cfg["base_url"],
                "ollama_model": cfg["model"],
            }
        return {
            "status": "can_exec",
            "runtime": "ollama",
            "provider_mode": "local",
            "model_name": cfg["model"],
            "fallback_blocked": True,
            "ollama_base_url": cfg["base_url"],
            "ollama_model": cfg["model"],
        }
    if _is_support_reply_request(request):
        ready, reason = _ensure_ollama_ready(cfg, run_dir)
        if not ready:
            return {
                "status": "disabled",
                "reason": reason,
                "runtime": "ollama",
                "ollama_base_url": cfg["base_url"],
                "ollama_model": cfg["model"],
            }
        return {
            "status": "can_exec",
            "runtime": "ollama",
            "ollama_base_url": cfg["base_url"],
            "ollama_model": cfg["model"],
        }
    if _should_bootstrap_ollama():
        ready, reason = _ensure_ollama_ready(cfg, run_dir)
        if not ready:
            return {
                "status": "disabled",
                "reason": reason,
                "runtime": "ollama",
                "ollama_base_url": cfg["base_url"],
                "ollama_model": cfg["model"],
            }
    with _with_env(_ollama_env(cfg)):
        out = dict(api_agent.preview(run_dir=run_dir, request=request, config=config))
    out["runtime"] = "ollama"
    out["ollama_base_url"] = cfg["base_url"]
    out["ollama_model"] = cfg["model"]
    return out


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Any]:
    # BEHAVIOR_ID: B035
    cfg = _provider_cfg(config, request=request)
    if _is_librarian_context_pack_request(request):
        out = _execute_native_librarian_context_pack(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=guardrails_budgets,
            cfg=cfg,
        )
        out["runtime"] = "ollama"
        out["ollama_base_url"] = cfg["base_url"]
        out["ollama_model"] = cfg["model"]
        return out
    if _is_support_reply_request(request):
        ready, reason = _ensure_ollama_ready(cfg, run_dir)
        if not ready:
            return {
                "status": "exec_failed",
                "reason": reason,
                "runtime": "ollama",
                "ollama_base_url": cfg["base_url"],
                "ollama_model": cfg["model"],
            }
        out = _execute_native_support_reply(run_dir=run_dir, request=request, cfg=cfg)
        out["runtime"] = "ollama"
        out["ollama_base_url"] = cfg["base_url"]
        out["ollama_model"] = cfg["model"]
        return out
    if _should_bootstrap_ollama():
        ready, reason = _ensure_ollama_ready(cfg, run_dir)
        if not ready:
            return {
                "status": "exec_failed",
                "reason": reason,
                "runtime": "ollama",
                "ollama_base_url": cfg["base_url"],
                "ollama_model": cfg["model"],
            }
    with _with_env(_ollama_env(cfg)):
        out = dict(
            api_agent.execute(
                repo_root=repo_root,
                run_dir=run_dir,
                request=request,
                config=config,
                guardrails_budgets=guardrails_budgets,
            )
        )
    out["runtime"] = "ollama"
    out["ollama_base_url"] = cfg["base_url"]
    out["ollama_model"] = cfg["model"]
    return out
