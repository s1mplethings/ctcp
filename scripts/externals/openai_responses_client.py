#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
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
        return "", "OPENAI_API_KEY is required for OpenAI API mode"

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
        return "", f"OpenAI API HTTP {exc.code}: {detail}"
    except Exception as exc:
        return "", f"OpenAI API request failed: {exc}"

    try:
        doc = json.loads(body)
    except Exception as exc:
        return "", f"OpenAI API returned non-JSON response: {exc}"
    if not isinstance(doc, dict):
        return "", "OpenAI API response is not a JSON object"

    text = extract_response_text(doc)
    if not text:
        preview = json.dumps(doc, ensure_ascii=False)[:2000]
        return "", f"OpenAI API response did not contain text output: {preview}"
    return text, ""
