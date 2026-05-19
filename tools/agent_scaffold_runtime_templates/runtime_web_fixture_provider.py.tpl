from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _request_text(payload: dict[str, Any]) -> str:
    for key in ("query", "request", "text", "message", "goal"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return " ".join(str(value) for value in payload.values() if isinstance(value, str)).strip()


def _fixture_path(context: dict[str, Any]) -> Path | None:
    configured = os.environ.get("CTCP_AGENT_WEB_FIXTURE_PATH")
    if configured:
        path = Path(configured)
        if path.exists():
            return path
    roots: list[Path] = []
    for raw in (context.get("root"), Path.cwd()):
        if raw:
            try:
                roots.append(Path(raw))
            except TypeError:
                pass
    for root in list(roots):
        roots.extend(root.parents)
    seen: set[Path] = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        candidate = root / "tests" / "fixtures" / "web_search_fixture.json"
        if candidate.exists():
            return candidate
    return None


def _load_fixture(context: dict[str, Any]) -> dict[str, Any]:
    path = _fixture_path(context)
    if path is None:
        raise RuntimeError("web_provider_unavailable")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise RuntimeError("web_provider_unavailable")
    return doc


def _url_from_input_or_context(tool_input: dict[str, Any], context: dict[str, Any]) -> str:
    url = tool_input.get("url")
    if isinstance(url, str) and url.strip():
        return url.strip()
    for result in context.get("previous_results", []) or []:
        if not isinstance(result, dict):
            continue
        output = result.get("output") or {}
        if not isinstance(output, dict):
            continue
        for source in output.get("sources", []) or []:
            if isinstance(source, dict) and source.get("url"):
                return str(source["url"])
        source = output.get("source")
        if isinstance(source, dict) and source.get("url"):
            return str(source["url"])
    return ""


def execute_web_search(tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    fixture = _load_fixture(context)
    query = _request_text(tool_input)
    try:
        limit = max(1, min(10, int(tool_input.get("max_results", 3))))
    except (TypeError, ValueError):
        limit = 3
    tokens = {part.lower() for part in query.split() if len(part) > 2}
    rows = fixture.get("search_index", [])
    matches = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        haystack = " ".join(str(row.get(key, "")) for key in ("title", "snippet", "text_excerpt", "body")).lower()
        score = sum(1 for token in tokens if token in haystack)
        if score or not tokens:
            matches.append((score, row))
    if not matches:
        matches = [(0, row) for row in rows if isinstance(row, dict)]
    matches = sorted(matches, key=lambda item: (-item[0], str(item[1].get("title", ""))))[:limit]
    results = []
    sources = []
    for index, (_score, row) in enumerate(matches, start=1):
        source_id = f"source_{index}"
        result = {
            "title": str(row.get("title", "")),
            "url": str(row.get("url", "")),
            "snippet": str(row.get("snippet", row.get("text_excerpt", ""))),
            "source_id": source_id,
        }
        results.append(result)
        sources.append({"source_id": source_id, "url": result["url"], "title": result["title"]})
    return {"query": query, "results": results, "sources": sources}


def execute_fetch_url(tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    fixture = _load_fixture(context)
    url = _url_from_input_or_context(tool_input, context)
    pages = fixture.get("pages", {})
    page = pages.get(url) if isinstance(pages, dict) else None
    if not isinstance(page, dict):
        page = {}
    title = str(page.get("title") or url)
    excerpt = str(page.get("text_excerpt") or page.get("body") or "")[:500]
    status_code = int(page.get("status_code", 200 if page else 404))
    output: dict[str, Any] = {
        "url": url,
        "title": title,
        "text_excerpt": excerpt,
        "status_code": status_code,
    }
    if url and page:
        output["source"] = {"source_id": "source_1", "url": url, "title": title}
    return output
