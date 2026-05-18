from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


SIDE_EFFECT_LEVELS = {"none", "low", "medium", "high"}
RUNTIME_ADAPTERS = {"local_deterministic", "web_search", "fetch_url", "unsupported", "external_blocked"}
WEB_RUNTIME_ADAPTERS = {"web_search", "fetch_url"}


def _request_text(payload: dict[str, Any]) -> str:
    for key in ("request", "text", "message", "goal"):
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
    seen = set()
    for root in roots:
        if root in seen:
            continue
        seen.add(root)
        candidate = root / "tests" / "fixtures" / "web_search_fixture.json"
        if candidate.exists():
            return candidate
    return None


def _load_web_fixture(context: dict[str, Any]) -> dict[str, Any]:
    if os.environ.get("CTCP_AGENT_WEB_PROVIDER", "").lower() != "fixture":
        raise RuntimeError("web_provider_unavailable")
    path = _fixture_path(context)
    if path is None:
        raise RuntimeError("web_provider_unavailable")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise RuntimeError("web_provider_unavailable")
    return doc


def _query_from_input(tool_input: dict[str, Any]) -> str:
    query = tool_input.get("query")
    if isinstance(query, str) and query.strip():
        return query.strip()
    return _request_text(tool_input)


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


class ToolAdapter:
    name = ""
    side_effect_level = "low"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class ClassifyInputAdapter(ToolAdapter):
    name = "classify_input"
    side_effect_level = "none"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        text = _request_text(tool_input).lower()
        labels = []
        for label, terms in {
            "incident": ("incident", "outage", "rollback", "deploy", "production"),
            "billing": ("billing", "refund", "charge", "invoice"),
            "medical": ("patient", "symptom", "clinician", "medical", "urgent"),
            "productivity": ("task", "priority", "summary", "reminder"),
        }.items():
            if any(term in text for term in terms):
                labels.append(label)
        return {"adapter": self.name, "labels": sorted(labels), "text_length": len(text)}


class ExtractFieldsAdapter(ToolAdapter):
    name = "extract_fields"
    side_effect_level = "none"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        text = _request_text(tool_input)
        words = [part.strip(".,:;!?()[]{}").lower() for part in text.split()]
        keywords = sorted({word for word in words if len(word) > 4})[:12]
        return {"adapter": self.name, "fields": {"keywords": keywords, "has_request": bool(text)}}


class SummarizeTextAdapter(ToolAdapter):
    name = "summarize_text"
    side_effect_level = "none"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        text = _request_text(tool_input)
        summary = text[:160]
        if len(text) > 160:
            summary += "..."
        return {"adapter": self.name, "summary": summary, "length": len(text)}


class CreateDraftAdapter(ToolAdapter):
    name = "create_draft"
    side_effect_level = "low"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        text = _request_text(tool_input) or "No request text provided."
        tool_name = str(context.get("tool_name", self.name))
        return {"adapter": self.name, "draft": f"Draft for {tool_name}: {text[:180]}"}


class WriteAuditEventAdapter(ToolAdapter):
    name = "write_audit_event"
    side_effect_level = "low"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"adapter": self.name, "event": "audit event prepared"}


class NoopResponseAdapter(ToolAdapter):
    name = "noop_response"
    side_effect_level = "none"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"adapter": self.name, "status": "noop"}


class WebSearchAdapter(ToolAdapter):
    name = "web_search"
    side_effect_level = "none"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        fixture = _load_web_fixture(context)
        query = _query_from_input(tool_input)
        max_results = tool_input.get("max_results", 3)
        try:
            limit = max(1, min(10, int(max_results)))
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


class FetchUrlAdapter(ToolAdapter):
    name = "fetch_url"
    side_effect_level = "none"

    def execute(self, tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        fixture = _load_web_fixture(context)
        url = _url_from_input_or_context(tool_input, context)
        pages = fixture.get("pages", {})
        page = pages.get(url) if isinstance(pages, dict) else None
        if not isinstance(page, dict):
            page = {}
        title = str(page.get("title") or url)
        excerpt = str(page.get("text_excerpt") or page.get("body") or "")[:500]
        status_code = int(page.get("status_code", 200 if page else 404))
        output = {
            "url": url,
            "title": title,
            "text_excerpt": excerpt,
            "status_code": status_code,
        }
        if url and page:
            output["source"] = {"source_id": "source_1", "url": url, "title": title}
        return output


ADAPTERS: dict[str, ToolAdapter] = {
    "classify_input": ClassifyInputAdapter(),
    "extract_fields": ExtractFieldsAdapter(),
    "summarize_text": SummarizeTextAdapter(),
    "create_draft": CreateDraftAdapter(),
    "write_audit_event": WriteAuditEventAdapter(),
    "noop_response": NoopResponseAdapter(),
    "web_search": WebSearchAdapter(),
    "fetch_url": FetchUrlAdapter(),
}

EXACT_TOOL_ADAPTERS = {
    "classify_input": "classify_input",
    "extract_fields": "extract_fields",
    "summarize_text": "summarize_text",
    "create_draft": "create_draft",
    "write_audit_event": "write_audit_event",
    "noop_response": "noop_response",
    "audit_log.write": "write_audit_event",
    "logs.query": "classify_input",
    "metrics.query": "classify_input",
    "deployment.history": "classify_input",
    "postmortem.write": "create_draft",
    "slack.draft": "create_draft",
    "daily_summary.write": "create_draft",
    "reminder.draft": "create_draft",
    "task.intake": "extract_fields",
    "task.prioritize": "classify_input",
    "symptom.collect": "extract_fields",
    "medical_history.collect": "extract_fields",
    "urgent_symptom.screen": "classify_input",
    "clinical_summary.draft": "create_draft",
    "source_summary": "summarize_text",
    "citation_builder": "create_draft",
    "feedback.collect": "extract_fields",
    "feedback.classify": "classify_input",
    "feedback.trend.summarize": "summarize_text",
    "weekly_report.write": "create_draft",
    "support.intake": "extract_fields",
    "support.classify": "classify_input",
    "customer.reply.draft": "create_draft",
}

EXTERNAL_TOOL_TERMS = ("http", "external")


def normalize_tool_contract(tool: dict[str, Any]) -> dict[str, Any]:
    name = str(tool.get("tool_name") or tool.get("name") or "")
    side_effect_level = str(tool.get("side_effect_level", "high")).lower()
    if side_effect_level not in SIDE_EFFECT_LEVELS:
        side_effect_level = "high"
    adapter_name = str(tool.get("adapter_name", "") or "")
    if not adapter_name and name in EXACT_TOOL_ADAPTERS:
        adapter_name = EXACT_TOOL_ADAPTERS[name]

    if "runtime_adapter" in tool:
        runtime_adapter = str(tool.get("runtime_adapter") or "unsupported")
    elif adapter_name in ADAPTERS:
        runtime_adapter = "local_deterministic"
    elif any(term in name.lower() for term in EXTERNAL_TOOL_TERMS):
        runtime_adapter = "external_blocked"
    else:
        runtime_adapter = "unsupported"
    if runtime_adapter not in RUNTIME_ADAPTERS:
        runtime_adapter = "unsupported"
    if runtime_adapter in WEB_RUNTIME_ADAPTERS and name != runtime_adapter:
        runtime_adapter = "unsupported"
    if runtime_adapter in WEB_RUNTIME_ADAPTERS:
        adapter_name = runtime_adapter

    return {
        "tool_name": name,
        "description": str(tool.get("description", "")),
        "side_effect_level": side_effect_level,
        "requires_approval": bool(tool.get("requires_approval", True)),
        "allowed_callers": list(tool.get("allowed_callers") or []),
        "audit_log_required": bool(tool.get("audit_log_required", True)),
        "input_schema": dict(tool.get("input_schema") or {}),
        "output_schema": dict(tool.get("output_schema") or {}),
        "runtime_adapter": runtime_adapter,
        "adapter_name": adapter_name if runtime_adapter in {"local_deterministic", "web_search", "fetch_url"} and adapter_name in ADAPTERS else "",
    }


def build_tool_registry(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    registry = {}
    for tool in manifest.get("tools", []):
        if isinstance(tool, dict):
            normalized = normalize_tool_contract(tool)
            registry[normalized["tool_name"]] = normalized
    return registry


def get_adapter(tool: dict[str, Any]) -> ToolAdapter | None:
    normalized = normalize_tool_contract(tool)
    if normalized.get("runtime_adapter") not in {"local_deterministic", "web_search", "fetch_url"}:
        return None
    return ADAPTERS.get(str(normalized.get("adapter_name", "")))


def supported_local_tool_names() -> list[str]:
    return sorted(name for name in ADAPTERS if name not in WEB_RUNTIME_ADAPTERS)


def supported_web_tool_names() -> list[str]:
    return sorted(WEB_RUNTIME_ADAPTERS)
