#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_NOTES_PATH = ROOT / ".agent_private" / "NOTES.md"


def _collect_text_from_output(doc: dict[str, Any]) -> str:
    text_parts: list[str] = []
    output = doc.get("output")
    if not isinstance(output, list):
        return ""
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for chunk in content:
            if not isinstance(chunk, dict):
                continue
            ctype = str(chunk.get("type", ""))
            if ctype not in {"output_text", "text"}:
                continue
            text = chunk.get("text")
            if isinstance(text, str) and text:
                text_parts.append(text)
    return "\n".join(text_parts).strip()


def extract_response_text(doc: dict[str, Any]) -> str:
    direct = doc.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()

    output_text = _collect_text_from_output(doc)
    if output_text:
        return output_text

    choices = doc.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            message = first.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                if isinstance(content, list):
                    text_parts: list[str] = []
                    for item in content:
                        if not isinstance(item, dict):
                            continue
                        if str(item.get("type", "")).strip() == "text":
                            text = item.get("text")
                            if isinstance(text, str) and text:
                                text_parts.append(text)
                    if text_parts:
                        return "\n".join(text_parts).strip()
    return ""


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _short_error(text: str) -> str:
    value = str(text or "").strip().replace("\r", " ").replace("\n", " ")
    if len(value) > 400:
        return value[:400]
    return value


def _append_api_call(*, model: str, status: str, request_id: str = "", error: str = "") -> None:
    path_text = str(os.environ.get("CTCP_API_CALLS_PATH", "")).strip()
    if not path_text:
        return
    row = {
        "timestamp": _now_iso(),
        "role": str(os.environ.get("CTCP_API_ROLE", "")).strip(),
        "action": str(os.environ.get("CTCP_API_ACTION", "")).strip(),
        "request_id": str(request_id or "").strip(),
        "model": str(model or "").strip(),
        "status": str(status or "").strip(),
        "error": _short_error(error),
    }
    try:
        path = Path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        return


def _load_local_notes_defaults() -> dict[str, str]:
    path_text = str(os.environ.get("CTCP_LOCAL_NOTES_PATH", "")).strip()
    path = Path(path_text) if path_text else DEFAULT_LOCAL_NOTES_PATH
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    out: dict[str, str] = {}
    m_url = re.search(r"`(https?://[^`\s]+)`", text)
    if m_url:
        out["base_url"] = m_url.group(1).strip()
    m_key = re.search(r"`(sk-[^`\s]+)`", text)
    if m_key:
        out["api_key"] = m_key.group(1).strip()
    return out


def _safe_int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _safe_float_env(name: str, default: float, *, minimum: float, maximum: float) -> float:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except Exception:
        return default
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def _post_json(
    *,
    endpoint: str,
    payload: dict[str, Any],
    token: str,
    timeout_sec: int,
) -> tuple[dict[str, Any] | None, str, bool]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "OpenAI/Python",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        detail = detail.strip()[:2000]
        reason = f"OpenAI API HTTP {exc.code}: {detail}"
        retryable = int(exc.code) in {408, 409, 425, 429, 500, 502, 503, 504}
        return None, reason, retryable
    except (urllib.error.URLError, TimeoutError, ConnectionError, ConnectionResetError, ssl.SSLError) as exc:
        reason = f"OpenAI API request failed: {exc}"
        return None, reason, True
    except Exception as exc:
        reason = f"OpenAI API request failed: {exc}"
        return None, reason, False

    try:
        doc = json.loads(body)
    except Exception as exc:
        reason = f"OpenAI API returned non-JSON response: {exc}"
        return None, reason, False
    if not isinstance(doc, dict):
        return None, "OpenAI API response is not a JSON object", False
    return doc, "", False


def _call_with_retry(
    *,
    endpoint: str,
    payload: dict[str, Any],
    token: str,
    timeout_sec: int,
    max_attempts: int,
    base_delay_sec: float,
) -> tuple[dict[str, Any] | None, str]:
    last_reason = ""
    for attempt in range(1, max_attempts + 1):
        doc, reason, retryable = _post_json(
            endpoint=endpoint,
            payload=payload,
            token=token,
            timeout_sec=timeout_sec,
        )
        if doc is not None:
            return doc, ""
        last_reason = reason
        if not retryable or attempt >= max_attempts:
            break
        time.sleep(base_delay_sec * float(attempt))
    return None, (last_reason or "OpenAI API request failed")


def call_openai_responses(
    *,
    prompt: str,
    model: str,
    timeout_sec: int,
    api_key: str | None = None,
    base_url: str | None = None,
) -> tuple[str, str]:
    defaults = _load_local_notes_defaults()
    token = (
        api_key
        or os.environ.get("OPENAI_API_KEY", "")
        or os.environ.get("CTCP_OPENAI_API_KEY", "")
        or defaults.get("api_key", "")
    ).strip()
    if not token:
        reason = "OPENAI_API_KEY is required for OpenAI API mode"
        _append_api_call(model=model, status="ERR", error=reason)
        return "", reason

    root = (
        base_url
        or os.environ.get("OPENAI_BASE_URL", "")
        or defaults.get("base_url", "")
        or "https://api.openai.com/v1"
    ).strip()
    endpoint_mode = str(os.environ.get("SDDAI_OPENAI_ENDPOINT_MODE", "auto")).strip().lower() or "auto"
    max_attempts = _safe_int_env("SDDAI_OPENAI_MAX_ATTEMPTS", 3, minimum=1, maximum=6)
    base_delay_sec = _safe_float_env("SDDAI_OPENAI_RETRY_BASE_DELAY_SEC", 0.75, minimum=0.0, maximum=10.0)

    responses_endpoint = root.rstrip("/") + "/responses"
    responses_payload = {
        "model": model,
        "input": prompt,
    }
    doc: dict[str, Any] | None = None
    reason = ""

    if endpoint_mode in {"auto", "responses"}:
        doc, reason = _call_with_retry(
            endpoint=responses_endpoint,
            payload=responses_payload,
            token=token,
            timeout_sec=timeout_sec,
            max_attempts=max_attempts,
            base_delay_sec=base_delay_sec,
        )
        if doc is not None:
            request_id = str(doc.get("id", "")).strip()
            text = extract_response_text(doc)
            if text:
                _append_api_call(model=model, status="OK", request_id=request_id)
                return text, ""
            preview = json.dumps(doc, ensure_ascii=False)[:2000]
            reason = f"OpenAI API response did not contain text output: {preview}"

    if endpoint_mode in {"auto", "chat"}:
        chat_endpoint = root.rstrip("/") + "/chat/completions"
        chat_payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
        }
        chat_doc, chat_reason = _call_with_retry(
            endpoint=chat_endpoint,
            payload=chat_payload,
            token=token,
            timeout_sec=timeout_sec,
            max_attempts=max_attempts,
            base_delay_sec=base_delay_sec,
        )
        if chat_doc is not None:
            request_id = str(chat_doc.get("id", "")).strip()
            text = extract_response_text(chat_doc)
            if text:
                _append_api_call(model=model, status="OK", request_id=request_id)
                return text, ""
            preview = json.dumps(chat_doc, ensure_ascii=False)[:2000]
            chat_reason = f"OpenAI API response did not contain text output: {preview}"
        reason = chat_reason or reason

    reason = reason or "OpenAI API request failed"
    _append_api_call(model=model, status="ERR", error=reason)
    return "", reason
