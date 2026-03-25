from __future__ import annotations

from typing import Any

from shared.errors import ValidationContractError

PROHIBITED_FULL_HISTORY_FIELDS = {
    "chat_history",
    "full_chat_history",
    "conversation_history",
    "raw_chat_history",
    "raw_messages",
    "full_messages",
}


def _find_prohibited_history_field(value: Any) -> str:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key or "").strip()
            if key_text in PROHIBITED_FULL_HISTORY_FIELDS:
                return key_text
            hit = _find_prohibited_history_field(child)
            if hit:
                return hit
        return ""
    if isinstance(value, list):
        for item in value:
            hit = _find_prohibited_history_field(item)
            if hit:
                return hit
    return ""


def require_dict(payload: Any, *, field: str = "payload") -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ValidationContractError(f"{field} must be an object")
    return dict(payload)


def require_non_empty_string(payload: dict[str, Any], key: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise ValidationContractError(f"{key} is required")
    return value


def optional_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValidationContractError(f"{key} must be an object")
    return dict(value)


def optional_string_list(payload: dict[str, Any], key: str) -> list[str]:
    value = payload.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValidationContractError(f"{key} must be a list")
    out: list[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            out.append(text)
    return out


def ensure_no_full_chat_history(payload: dict[str, Any]) -> None:
    hit = _find_prohibited_history_field(payload)
    if hit:
        raise ValidationContractError(
            f"backend input must be structured requirement only; full chat history is forbidden ({hit})"
        )


def validate_protocol_version(version: str) -> str:
    text = str(version or "").strip()
    if not text:
        raise ValidationContractError("protocol_version is required")
    return text
