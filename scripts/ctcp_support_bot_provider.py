#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_io import append_event, now_iso, write_json
from scripts.ctcp_support_bot_session_state import current_project_brief
from tools.formal_api_lock import formal_api_only_enabled

try:
    import ctcp_dispatch
except ModuleNotFoundError:
    import scripts.ctcp_dispatch as ctcp_dispatch  # type: ignore


def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def _host_attr(name: str) -> Any:
    module = _support_bot_host_module()
    return getattr(module, name, None) if module is not None else None


def sanitize_inline_text(text: str, max_chars: int = 220) -> str:
    candidate = _host_attr("sanitize_inline_text")
    if callable(candidate):
        return candidate(text, max_chars=max_chars)
    raw = str(text or "").strip()
    return raw[:max_chars].rstrip() if len(raw) > max_chars else raw


def execute_provider(**kwargs: Any) -> dict[str, Any]:
    candidate = _host_attr("execute_provider")
    if callable(candidate):
        return candidate(**kwargs)
    raise RuntimeError("support provider execution host is unavailable")


def log_provider_result(*args: Any, **kwargs: Any) -> None:
    candidate = _host_attr("log_provider_result")
    if callable(candidate):
        candidate(*args, **kwargs)


def read_json_doc(path: Path) -> dict[str, Any] | None:
    candidate = _host_attr("read_json_doc")
    if callable(candidate):
        return candidate(path)
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def user_requests_project_package(text: str) -> bool:
    candidate = _host_attr("user_requests_project_package")
    return bool(candidate(text)) if callable(candidate) else False


def user_requests_project_screenshot(text: str) -> bool:
    candidate = _host_attr("user_requests_project_screenshot")
    return bool(candidate(text)) if callable(candidate) else False


def is_project_create_intent(user_text: str, conversation_mode: str) -> bool:
    candidate = _host_attr("is_project_create_intent")
    return bool(candidate(user_text, conversation_mode)) if callable(candidate) else False


def _default_support_lead_provider() -> str:
    candidate = str(os.environ.get("CTCP_SUPPORT_LEAD_PROVIDER", "")).strip().lower()
    if candidate in SUPPORT_REPLY_PROVIDERS:
        return candidate
    return PRIMARY_SUPPORT_PROVIDER

def _default_support_local_fallback_provider() -> str:
    candidate = str(os.environ.get("CTCP_SUPPORT_LOCAL_FALLBACK_PROVIDER", "")).strip().lower()
    if candidate == "local_exec":
        candidate = LOCAL_SUPPORT_REPLY_PROVIDERS[0]
    if candidate in LOCAL_SUPPORT_REPLY_PROVIDERS:
        return candidate
    return LOCAL_SUPPORT_REPLY_PROVIDERS[0]

def _default_support_ollama_model() -> str:
    return str(os.environ.get("CTCP_SUPPORT_OLLAMA_MODEL", "")).strip() or "qwen2.5:7b-instruct"

def _support_model_looks_mini(model_name: str) -> bool:
    return "mini" in str(model_name or "").strip().lower()

def _normalize_support_openai_model(model_name: str) -> str:
    raw = sanitize_inline_text(str(model_name or ""), max_chars=80)
    if (not raw) or _support_model_looks_mini(raw):
        return DEFAULT_SUPPORT_OPENAI_MODEL
    return raw

def _default_support_openai_model() -> str:
    candidate = (
        str(os.environ.get("CTCP_SUPPORT_OPENAI_MODEL", "")).strip()
        or str(os.environ.get("CTCP_SUPPORT_LEAD_MODEL", "")).strip()
        or DEFAULT_SUPPORT_OPENAI_MODEL
    )
    return _normalize_support_openai_model(candidate)

def default_support_dispatch_config() -> dict[str, Any]:
    support_lead_provider = _default_support_lead_provider()
    local_fallback_provider = _default_support_local_fallback_provider()
    return {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": "manual_outbox",
        "public_delivery": {"mode": "telegram_live"},
        "role_providers": {
            "support_lead": support_lead_provider,
            "support_local_fallback": local_fallback_provider,
            "patchmaker": "codex_agent",
            "fixer": "codex_agent",
        },
        "budgets": {"max_outbox_prompts": 20},
        "providers": {
            "api_agent": {"support_model": _default_support_openai_model()},
            "codex_agent": {"enabled": False, "dry_run": True, "cmd": "codex", "model": "", "timeout_sec": 900, "fallback_to_manual_outbox": True},
            "ollama_agent": {"base_url": "http://127.0.0.1:11434/v1", "api_key": "ollama", "model": _default_support_ollama_model(), "auto_start": True, "start_timeout_sec": 20, "start_cmd": "ollama serve"},
        },
        "support_mode_router": {"enabled": True, "min_confidence": 0.62, "max_history": 8},
    }

def ensure_dispatch_config(run_dir: Path) -> Path:
    path = run_dir / DISPATCH_CONFIG_REL_PATH
    if not path.exists():
        write_json(path, default_support_dispatch_config())
    return path

def load_dispatch_config(run_dir: Path) -> tuple[dict[str, Any], str]:
    ensure_dispatch_config(run_dir)
    cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)
    if cfg is None:
        fallback = default_support_dispatch_config()
        write_json(run_dir / DISPATCH_CONFIG_REL_PATH, fallback)
        return fallback, f"fallback_to_default: {msg}"
    return cfg, msg

def resolve_support_provider(config: dict[str, Any], override: str = "") -> str:
    raw_override = str(override or "").strip().lower()
    if raw_override in KNOWN_PROVIDERS:
        return raw_override

    role_map = config.get("role_providers", {})
    if not isinstance(role_map, dict):
        role_map = {}
    provider = str(role_map.get("support_lead", config.get("mode", PRIMARY_SUPPORT_PROVIDER))).strip().lower()
    if provider not in KNOWN_PROVIDERS:
        return PRIMARY_SUPPORT_PROVIDER
    if provider == "local_exec":
        return PRIMARY_SUPPORT_PROVIDER
    if provider not in SUPPORT_REPLY_PROVIDERS:
        return PRIMARY_SUPPORT_PROVIDER
    return provider

def resolve_local_support_fallback(config: dict[str, Any]) -> str:
    role_map = config.get("role_providers", {})
    if not isinstance(role_map, dict):
        role_map = {}
    provider = str(role_map.get("support_local_fallback", "")).strip().lower()
    if provider == "local_exec":
        provider = LOCAL_SUPPORT_REPLY_PROVIDERS[0]
    if provider in LOCAL_SUPPORT_REPLY_PROVIDERS:
        return provider
    return LOCAL_SUPPORT_REPLY_PROVIDERS[0]

def support_provider_candidates(config: dict[str, Any], override: str = "") -> list[str]:
    if formal_api_only_enabled():
        return [PRIMARY_SUPPORT_PROVIDER]
    preferred = resolve_support_provider(config, override=override)
    local_fallback = resolve_local_support_fallback(config)
    ordered: list[str] = []
    strict = str(override or "").strip().lower() in KNOWN_PROVIDERS

    def _add(raw: str) -> None:
        text = str(raw or "").strip().lower()
        if text == "local_exec":
            text = local_fallback
        if text in KNOWN_PROVIDERS and text not in ordered:
            ordered.append(text)

    _add(preferred)
    role_map = config.get("role_providers", {})
    if isinstance(role_map, dict):
        strict = strict or bool(role_map.get("support_lead_strict", False))
    if preferred == PRIMARY_SUPPORT_PROVIDER:
        _add(local_fallback)
        return ordered or [PRIMARY_SUPPORT_PROVIDER, local_fallback]
    if preferred in LOCAL_SUPPORT_REPLY_PROVIDERS:
        return ordered or [local_fallback]
    if strict:
        return ordered or [PRIMARY_SUPPORT_PROVIDER, local_fallback]
    _add(PRIMARY_SUPPORT_PROVIDER)
    _add(local_fallback)
    return ordered or [PRIMARY_SUPPORT_PROVIDER, local_fallback]

def model_unavailable_reply_doc(result: dict[str, Any], *, lang_hint: str = "zh") -> dict[str, Any]:
    lang = str(lang_hint or "").strip().lower()
    use_en = lang.startswith("en")
    local_provider = str(result.get("local_provider", "")).strip()
    if local_provider:
        if use_en:
            reply_text = "The reply backend is unavailable right now, and neither the API path nor the local fallback produced a customer-ready reply for this turn."
        else:
            reply_text = "当前回复后端暂时不可用，API 路径和本地兜底都没有给出可直接发送的正式回复。"
    else:
        if use_en:
            reply_text = "The reply backend is unavailable right now, so there is no customer-ready reply for this turn yet."
        else:
            reply_text = "当前回复后端暂时不可用，所以这轮还没有可直接发送的正式回复。"
    return {
        "reply_text": reply_text,
        "next_question": "",
        "actions": [],
        "debug_notes": sanitize_inline_text(str(result.get("reason", "")), max_chars=180) or "model_unavailable",
    }

def deferred_support_reply_doc(provider: str, result: dict[str, Any]) -> dict[str, Any]:
    """Return empty reply when deferred - no internal debug messages to user."""
    path_hint = sanitize_inline_text(str(result.get("path", "")), max_chars=180)
    notes = f"deferred:{provider}"
    if path_hint:
        notes += f" path={path_hint}"
    return {
        "reply_text": "",
        "next_question": "",
        "actions": [],
        "debug_notes": notes,
    }

def load_inbox_history(run_dir: Path, limit: int = 8) -> list[dict[str, str]]:
    path = run_dir / SUPPORT_INBOX_REL_PATH
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            doc = json.loads(text)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        rows.append(
            {
                "ts": str(doc.get("ts", "")).strip(),
                "source": str(doc.get("source", "")).strip() or "unknown",
                "text": str(doc.get("text", "")).strip(),
            }
        )
    return rows[-max(1, limit) :]

def load_last_reply_text(run_dir: Path) -> str:
    path = run_dir / SUPPORT_REPLY_REL_PATH
    if not path.exists():
        return ""
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""
    if not isinstance(doc, dict):
        return ""
    return str(doc.get("reply_text", "")).strip()


__all__ = [
    "_default_support_openai_model",
    "_normalize_support_openai_model",
    "default_support_dispatch_config",
    "ensure_dispatch_config",
    "load_dispatch_config",
    "resolve_support_provider",
    "resolve_local_support_fallback",
    "support_provider_candidates",
    "model_unavailable_reply_doc",
    "deferred_support_reply_doc",
    "load_inbox_history",
    "load_last_reply_text",
]
