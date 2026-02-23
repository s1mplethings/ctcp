#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any


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


def call_openai_responses(
    *,
    prompt: str,
    model: str,
    timeout_sec: int,
    api_key: str | None = None,
    base_url: str | None = None,
) -> tuple[str, str]:
    token = (api_key or os.environ.get("OPENAI_API_KEY", "")).strip()
    if not token:
        reason = "OPENAI_API_KEY is required for OpenAI API mode"
        _append_api_call(model=model, status="ERR", error=reason)
        return "", reason

    root = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).strip()
    endpoint = root.rstrip("/") + "/responses"

    payload = {
        "model": model,
        "input": prompt,
    }
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
        _append_api_call(model=model, status="ERR", error=reason)
        return "", reason
    except Exception as exc:
        reason = f"OpenAI API request failed: {exc}"
        _append_api_call(model=model, status="ERR", error=reason)
        return "", reason

    try:
        doc = json.loads(body)
    except Exception as exc:
        reason = f"OpenAI API returned non-JSON response: {exc}"
        _append_api_call(model=model, status="ERR", error=reason)
        return "", reason
    if not isinstance(doc, dict):
        reason = "OpenAI API response is not a JSON object"
        _append_api_call(model=model, status="ERR", error=reason)
        return "", reason

    request_id = str(doc.get("id", "")).strip()
    text = extract_response_text(doc)
    if not text:
        preview = json.dumps(doc, ensure_ascii=False)[:2000]
        reason = f"OpenAI API response did not contain text output: {preview}"
        _append_api_call(model=model, status="ERR", request_id=request_id, error=reason)
        return "", reason

    _append_api_call(model=model, status="OK", request_id=request_id)
    return text, ""
