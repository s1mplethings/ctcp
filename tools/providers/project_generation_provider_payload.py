from __future__ import annotations

import json
from typing import Any


def _extract_json_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        doc = json.loads(raw)
        return doc if isinstance(doc, dict) else None
    except Exception:
        pass
    fenced = _extract_fenced_json(raw)
    if fenced is not None:
        return fenced
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        doc = json.loads(raw[start : end + 1])
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


def _extract_fenced_json(raw: str) -> dict[str, Any] | None:
    marker = "```"
    start = raw.find(marker)
    while start >= 0:
        header_end = raw.find("\n", start + len(marker))
        if header_end < 0:
            return None
        end = raw.find(marker, header_end + 1)
        if end < 0:
            return None
        body = raw[header_end + 1 : end].strip()
        try:
            doc = json.loads(body)
            return doc if isinstance(doc, dict) else None
        except Exception:
            start = raw.find(marker, end + len(marker))
    return None


def _candidate_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[Any] = []
    for key in ("files", "provider_source_files", "generated_files", "project_files"):
        value = doc.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            candidates.extend({"path": path, "content": content} for path, content in value.items())
    bundle = doc.get("source_bundle")
    if isinstance(bundle, dict):
        value = bundle.get("files")
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            candidates.extend({"path": path, "content": content} for path, content in value.items())
    if "path" in doc and ("content" in doc or "content_lines" in doc):
        candidates.append(doc)
    return [dict(item) for item in candidates if isinstance(item, dict)]


def _content_from_row(row: dict[str, Any]) -> str | None:
    content = row.get("content")
    if isinstance(content, str):
        return content
    content_lines = row.get("content_lines")
    if isinstance(content_lines, list):
        lines = [str(item) for item in content_lines]
        return "\n".join(lines) + ("\n" if lines else "")
    return None


def normalize_provider_source_payload(value: Any) -> dict[str, Any]:
    doc = _extract_json_dict(value)
    if doc is None:
        return {
            "schema_version": "ctcp-provider-source-files-v1",
            "valid": False,
            "provider_source_files": [],
            "errors": ["provider output is not a JSON object"],
        }
    files: list[dict[str, str]] = []
    errors: list[str] = []
    seen: set[str] = set()
    for row in _candidate_rows(doc):
        path = str(row.get("path", "")).strip().replace("\\", "/").lstrip("/")
        content = _content_from_row(row)
        if not path:
            errors.append("file row missing path")
            continue
        if content is None:
            errors.append(f"file row missing content: {path}")
            continue
        if path in seen:
            continue
        seen.add(path)
        files.append({"path": path, "content": content})
    return {
        "schema_version": "ctcp-provider-source-files-v1",
        "valid": bool(files),
        "provider_source_files": files,
        "source_map": doc.get("source_map") if isinstance(doc.get("source_map"), dict) else {},
        "interfaces": doc.get("interfaces") if isinstance(doc.get("interfaces"), dict) else {},
        "chunked_source_generation": doc.get("chunked_source_generation") if isinstance(doc.get("chunked_source_generation"), dict) else {},
        "errors": errors,
    }


__all__ = ["normalize_provider_source_payload"]
