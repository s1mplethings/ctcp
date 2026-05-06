#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_io import append_event, now_iso
from scripts.ctcp_support_bot_provider import (
    execute_provider,
    is_project_create_intent,
    load_inbox_history,
    log_provider_result,
    read_json_doc,
    sanitize_inline_text,
    support_provider_candidates,
    user_requests_project_package,
    user_requests_project_screenshot,
)
from scripts.ctcp_support_bot_session_state import current_project_brief


def _normalize_mode_name(raw: str) -> str:
    mode = sanitize_inline_text(str(raw or ""), max_chars=40).upper().strip()
    return mode if mode in SUPPORTED_CONVERSATION_MODES else ""


def _to_float(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except Exception:
        return default


def _mode_router_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("support_mode_router", {})
    if not isinstance(raw, dict):
        raw = {}
    min_confidence = _to_float(raw.get("min_confidence", 0.62), 0.62)
    max_history = int(raw.get("max_history", 8) or 8)
    return {
        "enabled": bool(raw.get("enabled", True)),
        "min_confidence": max(0.0, min(min_confidence, 1.0)),
        "max_history": max(2, min(max_history, 16)),
    }


def mode_router_provider_candidates(config: dict[str, Any], override: str = "") -> list[str]:
    ordered: list[str] = []
    for provider in support_provider_candidates(config, override=override):
        if provider in SUPPORT_REPLY_PROVIDERS and provider not in ordered:
            ordered.append(provider)
    if not ordered:
        ordered = [PRIMARY_SUPPORT_PROVIDER, LOCAL_SUPPORT_REPLY_PROVIDERS[0]]
    return ordered


def should_try_model_mode_router(*, user_text: str, detected_mode: str, session_state: dict[str, Any]) -> bool:
    mode = str(detected_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL"}:
        return False
    if not bool(str(session_state.get("bound_run_id", "")).strip()):
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw:
        return False
    if user_requests_project_package(raw) or user_requests_project_screenshot(raw):
        return False
    low = raw.lower()
    hint_hit = any(token in raw for token in MODE_ROUTER_HINTS_ZH) or any(token in low for token in MODE_ROUTER_HINTS_EN)
    question_like = raw.endswith(("?", "？")) or ("?" in raw) or ("？" in raw)
    if not (hint_hit or question_like):
        return False
    if is_project_create_intent(raw, mode):
        return False
    return True


def build_mode_router_prompt(
    *,
    run_dir: Path,
    user_text: str,
    detected_mode: str,
    session_state: dict[str, Any],
    source: str,
    max_history: int,
) -> str:
    history = load_inbox_history(run_dir, limit=max(2, max_history))
    context = {
        "schema_version": "ctcp-support-mode-router-context-v1",
        "ts": now_iso(),
        "source": sanitize_inline_text(source, max_chars=24),
        "detected_mode": _normalize_mode_name(detected_mode) or "SMALLTALK",
        "latest_user_message": sanitize_inline_text(user_text, max_chars=280),
        "has_bound_run": bool(str(session_state.get("bound_run_id", "")).strip()),
        "bound_run_id": sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80),
        "project_brief": sanitize_inline_text(current_project_brief(session_state), max_chars=280),
        "history": history,
        "allowed_modes": sorted(SUPPORTED_CONVERSATION_MODES),
    }
    instruction = {
        "schema_version": "ctcp-support-mode-router-request-v1",
        "task": "classify the latest user turn into one allowed conversation mode",
        "hard_rules": [
            "Return exactly one JSON object only.",
            "Mode must be one of allowed_modes.",
            "If user asks progress/status/explanation of existing run or delivery, prefer STATUS_QUERY.",
            "Do not invent new mode labels.",
        ],
        "output_schema": {"mode": "one_of_allowed_modes", "confidence": "0.0~1.0", "reason": "short string"},
    }
    return (
        "# Support Mode Router\n\n"
        + json.dumps(instruction, ensure_ascii=False, indent=2)
        + "\n\n# Context\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n"
    )


def make_mode_router_request(chat_id: str, user_text: str, prompt_text: str) -> dict[str, Any]:
    return {
        "role": "support_mode_router",
        "action": "classify_mode",
        "target_path": SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH.as_posix(),
        "missing_paths": [SUPPORT_INBOX_REL_PATH.as_posix()],
        "reason": prompt_text[-20000:] if len(prompt_text) > 20000 else prompt_text,
        "goal": f"support mode routing {chat_id}",
        "input_text": user_text,
    }


def parse_mode_router_doc(path: Path, *, min_confidence: float) -> tuple[str, str]:
    doc = read_json_doc(path)
    if not isinstance(doc, dict):
        return "", "mode router output missing/invalid json"
    mode = _normalize_mode_name(str(doc.get("mode", "")))
    if not mode:
        return "", "mode router output missing valid mode"
    confidence = _to_float(doc.get("confidence", 0.0), 0.0)
    if confidence < min_confidence:
        return "", f"mode router confidence too low: {confidence:.2f} < {min_confidence:.2f}"
    return mode, ""


def maybe_override_conversation_mode_with_model(
    *,
    run_dir: Path,
    chat_id: str,
    user_text: str,
    source: str,
    detected_mode: str,
    session_state: dict[str, Any],
    config: dict[str, Any],
    provider_override: str = "",
) -> str:
    fallback_mode = _normalize_mode_name(detected_mode) or "SMALLTALK"
    router_cfg = _mode_router_config(config)
    if not bool(router_cfg.get("enabled", True)):
        return fallback_mode
    if not should_try_model_mode_router(user_text=user_text, detected_mode=fallback_mode, session_state=session_state):
        return fallback_mode

    prompt_text = build_mode_router_prompt(
        run_dir=run_dir,
        user_text=user_text,
        detected_mode=fallback_mode,
        session_state=session_state,
        source=source,
        max_history=int(router_cfg.get("max_history", 8)),
    )
    output_path = run_dir / SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH
    try:
        output_path.unlink(missing_ok=True)
    except Exception:
        pass

    errors: list[str] = []
    request = make_mode_router_request(chat_id, user_text, prompt_text)
    for idx, provider in enumerate(mode_router_provider_candidates(config, override=provider_override), start=1):
        result = execute_provider(provider=provider, run_dir=run_dir, request=request, config=config)
        log_provider_result(run_dir, provider, result, f"mode_router_attempt_{idx}")
        if str(result.get("status", "")).strip().lower() != "executed":
            errors.append(f"{provider}:{sanitize_inline_text(str(result.get('reason', '')), max_chars=120)}")
            continue
        mode, reason = parse_mode_router_doc(output_path, min_confidence=float(router_cfg.get("min_confidence", 0.62)))
        if not mode:
            errors.append(f"{provider}:{reason}")
            continue
        if mode != fallback_mode:
            append_event(
                run_dir,
                "SUPPORT_MODE_ROUTER_APPLIED",
                SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH.as_posix(),
                from_mode=fallback_mode,
                to_mode=mode,
                provider=provider,
            )
        return mode

    append_event(
        run_dir,
        "SUPPORT_MODE_ROUTER_SKIPPED",
        SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH.as_posix(),
        from_mode=fallback_mode,
        reason=" | ".join(errors[-3:]) if errors else "no provider accepted mode arbitration",
    )
    return fallback_mode


__all__ = [
    "mode_router_provider_candidates",
    "should_try_model_mode_router",
    "build_mode_router_prompt",
    "make_mode_router_request",
    "parse_mode_router_doc",
    "maybe_override_conversation_mode_with_model",
]
