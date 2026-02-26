#!/usr/bin/env python3
from __future__ import annotations

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
DEFAULT_OLLAMA_MODEL = "qwen2.5:12b"
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


def _provider_cfg(config: dict[str, Any]) -> dict[str, Any]:
    providers = config.get("providers", {}) if isinstance(config, dict) else {}
    if not isinstance(providers, dict):
        providers = {}
    raw = providers.get("ollama_agent", {})
    if not isinstance(raw, dict):
        raw = {}

    base_url = (
        str(raw.get("base_url", "")).strip()
        or str(os.environ.get("CTCP_OLLAMA_BASE_URL", "")).strip()
        or DEFAULT_OLLAMA_BASE_URL
    )
    api_key = (
        str(raw.get("api_key", "")).strip()
        or str(os.environ.get("CTCP_OLLAMA_API_KEY", "")).strip()
        or DEFAULT_OLLAMA_API_KEY
    )
    model = (
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
        with log_path.open("a", encoding="utf-8") as fh:
            subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                shell=True,
                stdout=fh,
                stderr=fh,
                creationflags=creationflags,
                start_new_session=(os.name != "nt"),
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
    cfg = _provider_cfg(config)
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
    cfg = _provider_cfg(config)
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
