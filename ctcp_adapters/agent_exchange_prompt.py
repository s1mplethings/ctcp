from __future__ import annotations

import json
from typing import Any

from ctcp_adapters.dispatch_whiteboard import safe_agent_exchange_packet


def render_agent_exchange_md(request: dict[str, Any]) -> str:
    exchange = safe_agent_exchange_packet(request.get("agent_exchange"))
    if not exchange:
        wb = request.get("whiteboard")
        if isinstance(wb, dict):
            exchange = safe_agent_exchange_packet(wb.get("agent_exchange"))
    lines = ["# AGENT_EXCHANGE", ""]
    if not exchange:
        lines += ["- none", ""]
        return "\n".join(lines)

    for key in ("schema_version", "lane", "stage", "role", "goal"):
        value = str(exchange.get(key, "")).strip()
        if value:
            lines.append(f"- {key}: `{value}`")
    lines.append("")

    _append_list_sections(lines, exchange)
    _append_context_needs(lines, exchange)
    _append_handoff(lines, exchange)
    return "\n".join(lines)


def _append_list_sections(lines: list[str], exchange: dict[str, Any]) -> None:
    for title, key in (
        ("Input Refs", "input_refs"),
        ("Decisions", "decisions"),
        ("Assumptions", "assumptions"),
        ("Open Questions", "open_questions"),
        ("Risks", "risks"),
        ("Acceptance Hooks", "acceptance_hooks"),
        ("Evidence", "evidence"),
    ):
        rows = exchange.get(key)
        if isinstance(rows, list) and rows:
            lines.append(f"## {title}")
            lines.extend(f"- {row}" for row in rows[:8])
            lines.append("")


def _append_context_needs(lines: list[str], exchange: dict[str, Any]) -> None:
    needs = exchange.get("context_needs")
    if not isinstance(needs, list) or not needs:
        return
    lines.append("## Context Needs")
    for row in needs[:5]:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind", "")).strip() or "repo"
        query = str(row.get("query", "")).strip()
        reason = str(row.get("reason", "")).strip()
        budget = row.get("budget") if isinstance(row.get("budget"), dict) else {}
        budget_text = " budget=" + json.dumps(budget, ensure_ascii=False, sort_keys=True) if budget else ""
        lines.append(f"- kind={kind}; query={query}; reason={reason}{budget_text}")
    lines.append("")


def _append_handoff(lines: list[str], exchange: dict[str, Any]) -> None:
    handoff = exchange.get("handoff")
    if not isinstance(handoff, dict) or not handoff:
        return
    lines.append("## Handoff")
    for key in ("next_role", "next_required_artifact"):
        value = str(handoff.get(key, "")).strip()
        if value:
            lines.append(f"- {key}: `{value}`")
    for title, key in (("Must Preserve", "must_preserve"), ("Must Not Do", "must_not_do")):
        rows = handoff.get(key)
        if isinstance(rows, list) and rows:
            lines.append(f"- {title}:")
            lines.extend(f"  - {row}" for row in rows[:6])
    lines.append("")
