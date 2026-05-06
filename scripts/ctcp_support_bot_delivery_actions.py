#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_provider import sanitize_inline_text


def user_requests_project_package(text: str) -> bool:
    raw = str(text or "")
    low = raw.lower()
    return ("zip" in low) or ("打包" in raw) or ("压缩包" in raw) or ("发给我" in raw and "项目" in raw)


def user_confirms_package_delivery(text: str) -> bool:
    raw = sanitize_inline_text(str(text), max_chars=280)
    if not raw:
        return False
    compact = re.sub(r"\s+", "", raw.lower())
    if any(token in compact for token in ("可以发包", "可以发zip", "发zip", "发吧", "发我吧", "就这个发")):
        return True
    if any(token in compact for token in ("ok发", "oksend", "sendit", "looksgood")):
        return True
    return compact in {"可以", "行", "好的", "好", "ok", "okay", "没问题"}


def is_zip_confirmation_after_recent_package_request(user_messages: list[str]) -> bool:
    if len(user_messages) < 2:
        return False
    current = sanitize_inline_text(user_messages[-1], max_chars=280)
    if not user_confirms_package_delivery(current):
        return False
    for prev in reversed(user_messages[:-1][-3:]):
        prev_text = sanitize_inline_text(prev, max_chars=280)
        if not prev_text:
            continue
        return user_requests_project_package(prev_text)
    return False


def user_requests_project_screenshot(text: str) -> bool:
    raw = str(text or "")
    low = raw.lower()
    return any(token in raw for token in ("截图", "界面图", "效果图", "项目图")) or ("screenshot" in low)


def user_requests_test_screenshot(text: str) -> bool:
    raw = str(text or "")
    low = raw.lower()
    return any(token in raw for token in ("测试图", "测试截图", "测试结果图", "测试证据图", "qa图")) or any(
        token in low
        for token in (
            "test screenshot",
            "testing screenshot",
            "qa screenshot",
            "smoke screenshot",
            "acceptance screenshot",
            "validation screenshot",
            "replay screenshot",
        )
    )


def _has_test_screenshot_candidates(paths: Any) -> bool:
    if not isinstance(paths, list):
        return False
    for item in paths:
        name = Path(str(item or "")).name.lower()
        if name and any(marker in name for marker in _TEST_SCREENSHOT_NAME_HINTS):
            return True
    return False


def user_requests_project_video(text: str) -> bool:
    raw = str(text or "")
    low = raw.lower()
    return any(token in raw for token in ("视频", "测试视频", "演示视频", "运行视频")) or any(
        token in low for token in ("video", "demo video", "test video", "recording")
    )


def should_expose_delivery_context(conversation_mode: str, user_text: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return (
            user_requests_project_package(user_text)
            or user_requests_project_screenshot(user_text)
            or user_requests_project_video(user_text)
        )
    return True


def normalize_actions(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("type", "")).strip().lower()
        if action_type == "ctcp_advance":
            out.append({"type": "ctcp_advance", "max_steps": _bounded_int(item.get("max_steps", 1), default=1, low=1, high=8)})
        elif action_type == "request_file":
            hint = sanitize_inline_text(str(item.get("hint", "")), max_chars=180)
            out.append({"type": "request_file", "hint": hint or "请补充必要附件"})
        elif action_type == "send_project_package":
            fmt = sanitize_inline_text(str(item.get("format", "zip")), max_chars=12).lower() or "zip"
            out.append({"type": "send_project_package", "format": "zip" if fmt != "zip" else fmt})
        elif action_type == "send_project_screenshot":
            normalized_action: dict[str, Any] = {
                "type": "send_project_screenshot",
                "count": _bounded_int(item.get("count", 1), default=1, low=1, high=5),
            }
            profile = sanitize_inline_text(str(item.get("profile", "")), max_chars=24).lower()
            if profile in {"test_evidence"}:
                normalized_action["profile"] = profile
            out.append(normalized_action)
        elif action_type == "send_project_video":
            out.append({"type": "send_project_video", "count": _bounded_int(item.get("count", 1), default=1, low=1, high=2)})
    return out


def _bounded_int(raw: Any, *, default: int, low: int, high: int) -> int:
    try:
        value = int(raw)
    except Exception:
        value = default
    return max(low, min(value, high))


def _strip_unavailable_delivery_actions(
    actions: list[dict[str, Any]],
    *,
    package_delivery_allowed: bool,
    screenshot_ready: bool,
    video_ready: bool,
) -> list[dict[str, Any]]:
    blocked: set[str] = set()
    if not package_delivery_allowed:
        blocked.add("send_project_package")
    if not screenshot_ready:
        blocked.add("send_project_screenshot")
    if not video_ready:
        blocked.add("send_project_video")
    return [dict(item) for item in actions if str(item.get("type", "")).strip().lower() not in blocked]


def _upsert_screenshot_action(out: list[dict[str, Any]], *, count: int, profile: str = "") -> None:
    desired = max(1, min(int(count), 5))
    for row in out:
        if str(row.get("type", "")).strip().lower() != "send_project_screenshot":
            continue
        row["count"] = max(1, min(max(_bounded_int(row.get("count", 1), default=1, low=1, high=5), desired), 5))
        if profile:
            row["profile"] = profile
        return
    payload: dict[str, Any] = {"type": "send_project_screenshot", "count": desired}
    if profile:
        payload["profile"] = profile
    out.append(payload)


def synthesize_delivery_actions(
    *,
    actions: list[dict[str, Any]],
    user_text: str,
    delivery_state: dict[str, Any] | None,
    conversation_mode: str = "",
    zip_confirmation_intent: bool = False,
) -> list[dict[str, Any]]:
    out = [dict(item) for item in actions if isinstance(item, dict)]
    if not isinstance(delivery_state, dict) or not bool(delivery_state.get("channel_can_send_files", False)):
        return out

    package_delivery_allowed = bool(delivery_state.get("package_delivery_allowed", False))
    out = _strip_unavailable_delivery_actions(
        out,
        package_delivery_allowed=package_delivery_allowed,
        screenshot_ready=bool(delivery_state.get("screenshot_ready", False)),
        video_ready=bool(delivery_state.get("video_ready", False)),
    )
    if not should_expose_delivery_context(conversation_mode, user_text):
        return [
            dict(item)
            for item in out
            if str(item.get("type", "")).strip().lower() not in {"send_project_package", "send_project_screenshot", "send_project_video"}
        ]

    types = {str(item.get("type", "")).strip().lower() for item in out}
    zip_intent = user_requests_project_package(user_text) or bool(zip_confirmation_intent)
    if zip_intent and bool(delivery_state.get("package_ready", False)) and package_delivery_allowed and "send_project_package" not in types:
        out.append({"type": "send_project_package", "format": "zip"})
        types.add("send_project_package")

    screenshot_count = len([x for x in delivery_state.get("screenshot_files", []) if str(x).strip()])
    has_test_screenshots = _has_test_screenshot_candidates(delivery_state.get("screenshot_files", []))
    if zip_intent and (not package_delivery_allowed) and screenshot_count > 0:
        _upsert_screenshot_action(out, count=1, profile="test_evidence" if has_test_screenshots else "")
    test_screenshot_intent = user_requests_test_screenshot(user_text)
    if user_requests_project_screenshot(user_text) and screenshot_count > 0:
        requested_count = min(5, screenshot_count) if test_screenshot_intent else min(3, screenshot_count)
        _upsert_screenshot_action(out, count=requested_count, profile="test_evidence" if (test_screenshot_intent or has_test_screenshots) else "")
    if has_test_screenshots:
        for row in out:
            if str(row.get("type", "")).strip().lower() == "send_project_screenshot" and not str(row.get("profile", "")).strip():
                row["profile"] = "test_evidence"

    video_count = len([x for x in delivery_state.get("video_files", []) if str(x).strip()])
    if user_requests_project_video(user_text) and video_count > 0 and "send_project_video" not in types:
        out.append({"type": "send_project_video", "count": min(2, video_count)})
    return out


__all__ = [
    "user_requests_project_package",
    "user_confirms_package_delivery",
    "is_zip_confirmation_after_recent_package_request",
    "user_requests_project_screenshot",
    "user_requests_test_screenshot",
    "_has_test_screenshot_candidates",
    "user_requests_project_video",
    "should_expose_delivery_context",
    "normalize_actions",
    "synthesize_delivery_actions",
]
