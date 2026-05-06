#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from typing import Any

from frontend.support_reply_policy import render_fallback_reply as frontend_render_fallback_reply
from scripts.ctcp_support_recovery import build_frontend_backend_truth_state
from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_delivery_actions import user_requests_project_package
from scripts.ctcp_support_bot_io import _replacement_char_count, utf8_clean
from scripts.ctcp_support_bot_progress import build_progress_binding
from scripts.ctcp_support_bot_provider import model_unavailable_reply_doc
from scripts.ctcp_support_bot_text_patterns import *  # noqa: F403


def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def is_greeting_only_message(text: str) -> bool:
    module = _support_bot_host_module()
    candidate = getattr(module, "is_greeting_only_message", None) if module is not None else None
    if callable(candidate):
        return bool(candidate(text))
    raw = str(text or "").strip().lower()
    return raw in {"hi", "hello", "hey", "你好", "您好"}

def failover_notice_text(*, lang: str, local_unavailable: bool = False) -> str:
    return failover_notice_text_with_kind(lang=lang, reason_kind="unavailable", local_unavailable=local_unavailable)

def failover_notice_text_with_kind(*, lang: str, reason_kind: str = "unavailable", local_unavailable: bool = False) -> str:
    code = str(reason_kind or "").strip().lower()
    use_en = str(lang or "").strip().lower().startswith("en")
    if local_unavailable:
        if use_en:
            return "The reply backend is unavailable right now, and both the API path and local fallback are down."
        return "当前回复后端暂时不可用，API 路径和本地兜底都不可用。"
    if code == "invalid_reply":
        if use_en:
            return "The formal reply path did not produce a customer-ready answer for this turn; only a lower-confidence fallback summary is available."
        return "这轮正式回复链没有产出可直接发送的结果，目前只有一份低置信度兜底说明。"
    if use_en:
        return "The formal reply path is unavailable right now; only a lower-confidence fallback summary is available."
    return "这轮正式回复链暂时不可用，目前只有一份低置信度兜底说明。"

def reply_mentions_failover(reply_text: str) -> bool:
    low = str(reply_text or "").lower()
    text = str(reply_text or "")
    return ("api" in low and ("local" in low or "本地" in text)) or ("回复链路没连上" in text) or ("没给到可直接发出的回复" in text)

def prepend_failover_notice(
    reply_text: str,
    *,
    lang: str,
    reason_kind: str = "unavailable",
    local_unavailable: bool = False,
) -> str:
    notice = failover_notice_text_with_kind(lang=lang, reason_kind=reason_kind, local_unavailable=local_unavailable)
    text = str(reply_text or "").strip()
    if not text:
        return notice
    if reply_mentions_failover(text):
        return text
    return f"{notice}\n\n{text}"

def unusable_provider_reply_reason(reply_text: str, *, expected_lang: str) -> str:
    reply = str(reply_text or "").strip()
    if not reply:
        return "empty reply_text"
    if contains_forbidden_reply(reply):
        return "forbidden reply_text"
    if looks_like_garbled_text(reply, expected_lang=expected_lang):
        return "garbled reply_text"
    return ""

def contains_forbidden_reply(text: str) -> bool:
    low = str(text or "").lower()
    if any(token in low for token in FORBIDDEN_REPLY_PATTERNS):
        return True
    if re.search(r"[a-zA-Z]:\\", text or ""):
        return True
    if re.search(r"/(users|home|tmp|var|opt)/", low):
        return True
    return False

def sanitize_inline_text(text: str, max_chars: int = 220) -> str:
    raw = str(text or "")
    raw = re.sub(r"```[\s\S]*?```", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) > max_chars:
        return raw[: max_chars - 1] + "..."
    return raw

def normalize_question(raw: str) -> str:
    q = sanitize_inline_text(raw, max_chars=140)
    if (not q) or contains_forbidden_reply(q):
        q = "你现在最希望我先解决的一个具体问题是什么"
    if not q.endswith(("?", "？")):
        q += "？"
    return q

def detect_lang_hint(*texts: str) -> str:
    merged = " ".join(str(x or "") for x in texts)
    if not merged.strip():
        return "zh"
    zh_count = sum(1 for ch in merged if "\u4e00" <= ch <= "\u9fff")
    en_count = sum(1 for ch in merged if ("a" <= ch.lower() <= "z"))
    return "zh" if zh_count >= max(1, en_count // 3) else "en"

def is_smalltalk_only_message(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    if is_greeting_only_message(raw):
        return True
    if any(p.match(raw) for p in SMALLTALK_PATTERNS_ZH):
        return True
    if any(p.match(raw) for p in SMALLTALK_PATTERNS_EN):
        return True
    return False

def user_explicitly_requests_code(text: str) -> bool:
    raw = sanitize_inline_text(str(text), max_chars=320)
    if not raw:
        return False
    low = raw.lower()
    return any(token in raw for token in CODE_REQUEST_HINTS_ZH) or any(token in low for token in CODE_REQUEST_HINTS_EN)

def _code_like_line_count(text: str) -> int:
    count = 0
    for raw_line in str(text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        low = line.lower()
        if line.startswith(
            (
                "def ",
                "class ",
                "import ",
                "from ",
                "const ",
                "let ",
                "var ",
                "function ",
                "public ",
                "private ",
                "protected ",
                "#include ",
            )
        ):
            count += 1
            continue
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*=\s*[^=].*$", line):
            count += 1
            continue
        if line.endswith(";") and len(line) >= 6:
            count += 1
            continue
        if any(token in line for token in ("=>", "::", "{", "}", "</", "/>", "__name__", "printf(", "console.log(")):
            count += 1
            continue
        if low.startswith(("if (", "for (", "while (", "switch (", "return ")):
            count += 1
            continue
    return count

def reply_looks_like_unsolicited_code(reply_text: str, *, user_text: str) -> bool:
    text = str(reply_text or "")
    if not text.strip():
        return False
    if user_explicitly_requests_code(user_text):
        return False
    if "```" in text:
        return True
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    code_like = _code_like_line_count(text)
    if code_like >= 4 and len(non_empty_lines) >= 5:
        return True
    if code_like >= 3 and any(token in text for token in ("def ", "class ", "import ", "{", "=>", "function ")):
        return True
    if len(non_empty_lines) <= 2:
        low = text.lower()
        token_hits = sum(
            1
            for token in ("def ", "class ", "import ", "return ", "for ", "if ", "__name__", "function ", "=>", "{", "}", ";")
            if token in low
        )
        if token_hits >= 4 and any(marker in text for marker in ("(", ")", "=", ":")):
            return True
    return False

def normalize_reply_text(raw_reply: str, next_question: str) -> str:
    raw = str(raw_reply or "").strip()
    raw = re.sub(r"```[\s\S]*?```", "", raw).strip()

    if raw and not contains_forbidden_reply(raw):
        return raw
    if not raw:
        if detect_lang_hint(raw, next_question).startswith("en"):
            return "I do not have a customer-ready reply yet."
        return "这边没拿到可直接发出的回复。"

    if frontend_render_fallback_reply is not None:
        try:
            rendered = frontend_render_fallback_reply(
                intent="guide_recovery",
                lang_hint=detect_lang_hint(raw, next_question) or "zh",
                project_context={},
                next_question=next_question,
                previous_reply_text="",
            )
            fallback_text = str(rendered.get("reply_text", "")).strip()
            fallback_question = normalize_question(str(rendered.get("next_question", "")).strip())
            if fallback_text and not contains_forbidden_reply(fallback_text):
                if fallback_question:
                    return f"{fallback_text}\n\n{fallback_question}"
                return fallback_text
        except Exception:
            pass

    conclusion = sanitize_inline_text(raw, max_chars=120)
    if (not conclusion) or contains_forbidden_reply(conclusion):
        conclusion = "这边没拿到可直接发出的回复。"

    question = normalize_question(next_question) if str(next_question or "").strip() else ""
    reply = conclusion
    if question:
        reply = f"{reply}\n\n{question}"
    if contains_forbidden_reply(reply):
        reply = "这边没拿到可直接发出的回复。"
        if question:
            reply = f"{reply}\n\n{question}"
    return reply

def fallback_reply_doc(result: dict[str, Any]) -> dict[str, Any]:
    return model_unavailable_reply_doc(result)

def sanitize_provider_doc(doc: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    clean = dict(doc)
    reply_text = utf8_clean(str(doc.get("reply_text", "")))
    next_question = utf8_clean(str(doc.get("next_question", "")))
    had_mojibake = _replacement_char_count(reply_text) >= 1 or _replacement_char_count(next_question) >= 1
    if had_mojibake:
        reply_text = reply_text.replace("\ufffd", "")
        next_question = next_question.replace("\ufffd", "")
        notes = sanitize_inline_text(str(doc.get("debug_notes", "")), max_chars=320)
        clean["debug_notes"] = f"{notes}; reply_sanitized=mojibake".strip("; ")
    clean["reply_text"] = reply_text.strip()
    clean["next_question"] = next_question.strip()
    return clean, had_mojibake

def looks_like_garbled_text(text: str, expected_lang: str = "") -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    if "\ufffd" in raw:
        return True

    zh_count = sum(1 for ch in raw if "\u4e00" <= ch <= "\u9fff")
    latin_count = sum(1 for ch in raw if ("a" <= ch.lower() <= "z"))
    suspicious_count = 0
    weird_script_count = 0
    for ch in raw:
        if ch.isdigit() or ch.isspace():
            continue
        if ch in ".,!?;:'\"()[]{}<>/\\-_+=@#$%^&*~`，。！？；：（）【】《》、":
            continue
        if "\u4e00" <= ch <= "\u9fff":
            continue
        if "a" <= ch.lower() <= "z":
            continue
        suspicious_count += 1
        code = ord(ch)
        if (0x00C0 <= code <= 0x024F) or (0x0370 <= code <= 0x052F) or (0x0600 <= code <= 0x06FF):
            weird_script_count += 1

    lang = str(expected_lang or "").strip().lower()
    if lang == "zh":
        if zh_count == 0 and suspicious_count >= max(4, len(raw) // 5):
            return True
        if zh_count == 0 and latin_count == 0 and suspicious_count >= 2:
            return True
        if zh_count == 0 and weird_script_count >= max(3, len(raw) // 8):
            return True
        if zh_count <= max(3, len(raw) // 10) and suspicious_count >= max(6, len(raw) // 3):
            return True
        if zh_count <= max(3, len(raw) // 10) and weird_script_count >= max(4, len(raw) // 4):
            return True
    if weird_script_count >= max(6, len(raw) // 6) and zh_count == 0 and latin_count <= max(2, len(raw) // 10):
        return True
    return False

def is_non_project_support_mode(conversation_mode: str) -> bool:
    return str(conversation_mode or "").strip().upper() in NON_PROJECT_SUPPORT_REPLY_MODES

def classify_api_failover_kind(*, status: str = "", reason: str = "") -> str:
    low_status = str(status or "").strip().lower()
    low_reason = str(reason or "").strip().lower()
    if low_status in {"outbox_created", "outbox_exists", "pending", "deferred", "disabled"}:
        return "unavailable"
    unavailable_tokens = (
        "connect",
        "timeout",
        "timed out",
        "401",
        "403",
        "token",
        "auth",
        "authentication",
        "base_url",
        "refused",
        "unreachable",
        "network",
        "dns",
        "ssl",
        "disabled",
        "not reachable",
        "connection reset",
    )
    if any(token in low_reason for token in unavailable_tokens):
        return "unavailable"
    return "invalid_reply"

def stale_project_context_reply_reason(reply_text: str, user_text: str, conversation_mode: str) -> str:
    if str(conversation_mode or "").strip().upper() not in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return ""
    reply = re.sub(r"\s+", " ", str(reply_text or "")).strip()
    user = re.sub(r"\s+", " ", str(user_text or "")).strip()
    if not reply:
        return ""
    reply_low = reply.lower()
    user_low = user.lower()
    leak_count = 0
    for token in PROJECT_CONTEXT_LEAK_TOKENS_ZH:
        if token in reply and token not in user:
            leak_count += 1
    for token in PROJECT_CONTEXT_LEAK_TOKENS_EN:
        if token in reply_low and token not in user_low:
            leak_count += 1
    if leak_count >= 2:
        return "stale project context on greeting reply"
    return ""

def validate_provider_reply_doc(
    *,
    doc: dict[str, Any],
    had_mojibake: bool,
    expected_lang: str,
    conversation_mode: str,
    user_text: str,
) -> tuple[str, str]:
    reply = str(doc.get("reply_text", "")).strip()
    if had_mojibake:
        return "invalid_reply", "mojibake reply_text"
    unusable_reason = unusable_provider_reply_reason(reply, expected_lang=expected_lang)
    if unusable_reason:
        return "invalid_reply", unusable_reason
    stale_reason = stale_project_context_reply_reason(reply, user_text, conversation_mode)
    if stale_reason:
        return "stale_context", stale_reason
    return "", ""

def append_delivery_preview_confirmation_note(
    reply_text: str,
    *,
    user_text: str,
    delivery_state: dict[str, Any] | None,
    actions: list[dict[str, Any]],
    zip_confirmation_intent: bool = False,
) -> str:
    if not isinstance(delivery_state, dict):
        return str(reply_text or "").strip()
    if bool(delivery_state.get("package_delivery_allowed", False)):
        return str(reply_text or "").strip()
    if not bool(delivery_state.get("screenshot_ready", False)):
        return str(reply_text or "").strip()
    if not (user_requests_project_package(user_text) or bool(zip_confirmation_intent)):
        return str(reply_text or "").strip()
    action_types = {str(item.get("type", "")).strip().lower() for item in actions if isinstance(item, dict)}
    if "send_project_screenshot" not in action_types:
        return str(reply_text or "").strip()
    note = "我先把当前效果给你看；你确认“可以发包”后，我会继续推进并在达到可交付状态时第一时间发 zip。"
    text = str(reply_text or "").strip()
    if note in text:
        return text
    if not text:
        return note
    return f"{text}\n\n{note}"

def build_frontend_backend_state(
    *,
    provider_result: dict[str, Any],
    raw_doc: dict[str, Any],
    project_context: dict[str, Any] | None,
    conversation_mode: str,
    has_user_msgs: bool,
    task_summary_hint: str = "",
) -> dict[str, Any]:
    return build_frontend_backend_truth_state(
        provider_result=provider_result,
        raw_doc=raw_doc,
        project_context=project_context,
        conversation_mode=conversation_mode,
        has_user_msgs=has_user_msgs,
        task_summary_hint=task_summary_hint,
        build_progress_binding=build_progress_binding,
    )

__all__ = [
    "failover_notice_text",
    "failover_notice_text_with_kind",
    "reply_mentions_failover",
    "prepend_failover_notice",
    "unusable_provider_reply_reason",
    "contains_forbidden_reply",
    "sanitize_inline_text",
    "normalize_question",
    "detect_lang_hint",
    "is_smalltalk_only_message",
    "user_explicitly_requests_code",
    "reply_looks_like_unsolicited_code",
    "normalize_reply_text",
    "fallback_reply_doc",
    "sanitize_provider_doc",
    "looks_like_garbled_text",
    "is_non_project_support_mode",
    "classify_api_failover_kind",
    "stale_project_context_reply_reason",
    "validate_provider_reply_doc",
    "append_delivery_preview_confirmation_note",
    "build_frontend_backend_state",
]
