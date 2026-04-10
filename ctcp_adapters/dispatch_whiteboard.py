from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPPORT_WHITEBOARD_REL = Path("artifacts") / "support_whiteboard.json"
SUPPORT_WHITEBOARD_LOG_REL = Path("artifacts") / "support_whiteboard.md"
SUPPORT_WHITEBOARD_SCHEMA_VERSION = "ctcp-support-whiteboard-v1"

try:
    from tools import local_librarian
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools import local_librarian


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _brief_text(value: str, *, max_chars: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    limit = max(8, int(max_chars))
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _safe_whiteboard_hits(rows: Any, *, max_items: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for item in rows:
        if not isinstance(item, dict):
            continue
        path = _brief_text(str(item.get("path", "")), max_chars=240)
        if not path:
            continue
        try:
            start_line = max(1, int(item.get("start_line", 1) or 1))
        except Exception:
            start_line = 1
        out.append(
            {
                "path": path,
                "start_line": start_line,
                "snippet": _brief_text(str(item.get("snippet", "")), max_chars=220),
            }
        )
        if len(out) >= max(1, int(max_items)):
            break
    return out


def _safe_whiteboard_entries(rows: Any, *, max_items: int = 120) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    limit = max(1, int(max_items))
    for item in rows[-limit:]:
        if not isinstance(item, dict):
            continue
        role = _brief_text(str(item.get("role", "")).lower(), max_chars=32) or "unknown"
        kind = _brief_text(str(item.get("kind", "")).lower(), max_chars=48) or "note"
        entry: dict[str, Any] = {
            "ts": _brief_text(str(item.get("ts", _now_iso())), max_chars=40),
            "role": role,
            "kind": kind,
            "text": _brief_text(str(item.get("text", "")), max_chars=260),
        }
        query = _brief_text(str(item.get("query", "")), max_chars=220)
        question = _brief_text(str(item.get("question", "")), max_chars=220)
        if query:
            entry["query"] = query
        if question:
            entry["question"] = question
        hits = _safe_whiteboard_hits(item.get("hits"), max_items=5)
        if hits:
            entry["hits"] = hits
            entry["hit_count"] = len(hits)
        out.append(entry)
    return out


def _load_support_whiteboard(run_dir: Path) -> dict[str, Any]:
    path = run_dir / SUPPORT_WHITEBOARD_REL
    state: dict[str, Any] = {
        "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
        "entries": [],
    }
    if not path.exists():
        return state
    try:
        doc = _read_json(path)
    except Exception:
        return state
    if not isinstance(doc, dict):
        return state
    state["entries"] = _safe_whiteboard_entries(doc.get("entries", []), max_items=120)
    return state


def _save_support_whiteboard(run_dir: Path, state: dict[str, Any]) -> None:
    payload = {
        "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
        "entries": _safe_whiteboard_entries((state or {}).get("entries", []), max_items=120),
    }
    _write_json(run_dir / SUPPORT_WHITEBOARD_REL, payload)


def _append_support_whiteboard_log(run_dir: Path, line: str) -> None:
    path = run_dir / SUPPORT_WHITEBOARD_LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"- {_now_iso()} | {_brief_text(line, max_chars=420)}\n")


def _compact_whiteboard_snapshot(state: dict[str, Any], *, max_entries: int = 5) -> dict[str, Any]:
    entries = _safe_whiteboard_entries(state.get("entries", []), max_items=120)
    tail = entries[-max(1, int(max_entries)) :]
    summary_entries: list[dict[str, Any]] = []
    for item in tail:
        row: dict[str, Any] = {
            "ts": str(item.get("ts", "")),
            "role": str(item.get("role", "")),
            "kind": str(item.get("kind", "")),
            "text": _brief_text(str(item.get("text", "")), max_chars=180),
        }
        query = _brief_text(str(item.get("query", "")), max_chars=180)
        if query:
            row["query"] = query
        hits = _safe_whiteboard_hits(item.get("hits"), max_items=3)
        if hits:
            row["hits"] = hits
            row["hit_count"] = len(hits)
        summary_entries.append(row)
    return {
        "path": SUPPORT_WHITEBOARD_REL.as_posix(),
        "entry_count": len(entries),
        "entries": summary_entries,
    }


def _latest_librarian_context(entries: list[dict[str, Any]]) -> dict[str, Any]:
    query = ""
    lookup_error = ""
    hits: list[dict[str, Any]] = []
    for item in reversed(entries):
        kind = str(item.get("kind", "")).strip().lower()
        if kind not in {"support_lookup", "dispatch_lookup"}:
            continue
        if not query:
            query = _brief_text(str(item.get("query", "")), max_chars=220)
        if not hits:
            hits = _safe_whiteboard_hits(item.get("hits"), max_items=4)
        if not lookup_error:
            text = str(item.get("text", "")).strip()
            if text.lower().startswith("lookup error:"):
                lookup_error = _brief_text(text.split(":", 1)[1], max_chars=180)
        if query or hits or lookup_error:
            break
    return {
        "query": query,
        "hits": hits,
        "lookup_error": lookup_error,
    }


def get_support_whiteboard_context(run_dir: Path) -> dict[str, Any]:
    board = _load_support_whiteboard(run_dir)
    entries = _safe_whiteboard_entries(board.get("entries", []), max_items=120)
    latest = _latest_librarian_context(entries)
    return {
        "path": SUPPORT_WHITEBOARD_REL.as_posix(),
        "query": str(latest.get("query", "")),
        "hits": list(latest.get("hits", [])),
        "lookup_error": str(latest.get("lookup_error", "")),
        "snapshot": _compact_whiteboard_snapshot(board, max_entries=5),
    }


def _dispatch_whiteboard_query(request: dict[str, Any]) -> str:
    goal = _brief_text(str(request.get("goal", "")), max_chars=220)
    reason = _brief_text(str(request.get("reason", "")), max_chars=220)
    role = _brief_text(str(request.get("role", "")), max_chars=32)
    action = _brief_text(str(request.get("action", "")), max_chars=48)
    if goal:
        return goal
    if reason:
        return reason
    return _brief_text(f"{role} {action}".strip(), max_chars=120)


def _last_librarian_query(entries: list[dict[str, Any]]) -> str:
    for item in reversed(entries):
        kind = str(item.get("kind", "")).strip().lower()
        if kind not in {"support_lookup", "dispatch_lookup"}:
            continue
        query = str(item.get("query", "")).strip()
        if query:
            return query
    return ""


def record_support_turn_whiteboard(
    *,
    run_dir: Path,
    repo_root: Path,
    text: str,
    source: str,
    conversation_mode: str,
    chat_id: str = "",
) -> dict[str, Any]:
    board = _load_support_whiteboard(run_dir)
    entries = _safe_whiteboard_entries(board.get("entries", []), max_items=120)
    query = _brief_text(str(text or ""), max_chars=220)
    last_query = _last_librarian_query(entries)
    should_lookup = bool(query) and query.lower() != last_query.lower()
    hits: list[dict[str, Any]] = []
    lookup_error = ""
    if should_lookup:
        try:
            rows = local_librarian.search(repo_root=repo_root, query=query, k=4)
            hits = _safe_whiteboard_hits(rows, max_items=4)
        except Exception as exc:
            lookup_error = _brief_text(str(exc), max_chars=180) or "lookup failed"

    note = _brief_text(f"{source or 'support'} {conversation_mode or 'project_turn'}: {text}", max_chars=260)
    entry: dict[str, Any] = {
        "ts": _now_iso(),
        "role": "support",
        "kind": "support_turn",
        "text": note,
        "query": query,
    }
    if chat_id:
        entry["question"] = _brief_text(f"chat_id={chat_id}", max_chars=220)
    entries.append(entry)

    if should_lookup:
        librarian_entry: dict[str, Any] = {
            "ts": _now_iso(),
            "role": "local_search",
            "kind": "support_lookup",
            "text": f"lookup error: {lookup_error}" if lookup_error else f"lookup completed with {len(hits)} hits",
            "query": query,
        }
        if hits:
            librarian_entry["hits"] = hits
            librarian_entry["hit_count"] = len(hits)
        entries.append(librarian_entry)
        _append_support_whiteboard_log(
            run_dir,
            f"support lookup source={source or 'support'} mode={conversation_mode or 'project_turn'} "
            f"query={query} hits={len(hits)} err={lookup_error or 'none'}",
        )

    board["entries"] = entries
    _save_support_whiteboard(run_dir, board)
    context = get_support_whiteboard_context(run_dir)
    context["query"] = query
    context["hits"] = hits if should_lookup else list(context.get("hits", []))
    context["lookup_error"] = lookup_error or str(context.get("lookup_error", ""))
    return context


def prepare_dispatch_whiteboard_context(
    *,
    run_dir: Path,
    repo_root: Path,
    request: dict[str, Any],
) -> dict[str, Any]:
    board = _load_support_whiteboard(run_dir)
    entries = _safe_whiteboard_entries(board.get("entries", []), max_items=120)
    role = _brief_text(str(request.get("role", "")).lower(), max_chars=32) or "agent"
    action = _brief_text(str(request.get("action", "")), max_chars=48)
    target_path = _brief_text(str(request.get("target_path", "")), max_chars=140)
    reason = _brief_text(str(request.get("reason", "")), max_chars=220)
    query = _dispatch_whiteboard_query(request)
    last_query = _last_librarian_query(entries)
    should_lookup = bool(query) and query.lower() != last_query.lower()
    hits: list[dict[str, Any]] = []
    lookup_error = ""
    if should_lookup:
        try:
            rows = local_librarian.search(repo_root=repo_root, query=query, k=4)
            hits = _safe_whiteboard_hits(rows, max_items=4)
        except Exception as exc:
            lookup_error = _brief_text(str(exc), max_chars=180) or "lookup failed"

    dispatch_text = _brief_text(f"{role}/{action} -> {target_path}; {reason or 'dispatch requested'}", max_chars=260)
    entries.append({"ts": _now_iso(), "role": role, "kind": "dispatch_request", "text": dispatch_text, "query": query})

    if should_lookup:
        librarian_entry: dict[str, Any] = {
            "ts": _now_iso(),
            "role": "local_search",
            "kind": "dispatch_lookup",
            "text": f"lookup error: {lookup_error}" if lookup_error else f"lookup completed with {len(hits)} hits",
            "query": query,
        }
        if hits:
            librarian_entry["hits"] = hits
            librarian_entry["hit_count"] = len(hits)
        entries.append(librarian_entry)
        _append_support_whiteboard_log(
            run_dir,
            f"dispatch lookup role={role} action={action} query={query} hits={len(hits)} err={lookup_error or 'none'}",
        )

    board["entries"] = entries
    _save_support_whiteboard(run_dir, board)
    return {
        "path": SUPPORT_WHITEBOARD_REL.as_posix(),
        "query": query,
        "hits": hits,
        "lookup_error": lookup_error,
        "snapshot": _compact_whiteboard_snapshot(board, max_entries=5),
    }


def append_dispatch_result_whiteboard(
    *,
    run_dir: Path,
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    board = _load_support_whiteboard(run_dir)
    entries = _safe_whiteboard_entries(board.get("entries", []), max_items=120)
    role = _brief_text(str(request.get("role", "")).lower(), max_chars=32) or "agent"
    action = _brief_text(str(request.get("action", "")), max_chars=48)
    provider = _brief_text(str(result.get("provider", "")), max_chars=40) or "unknown"
    status = _brief_text(str(result.get("status", "")), max_chars=40) or "unknown"
    reason = _brief_text(str(result.get("reason", "")), max_chars=180)
    target_path = _brief_text(str(request.get("target_path", "")), max_chars=140)
    text = f"{role}/{action} via {provider} => {status} ({target_path})"
    if reason:
        text += f"; {reason}"
    entries.append({"ts": _now_iso(), "role": role, "kind": "dispatch_result", "text": _brief_text(text, max_chars=260)})
    board["entries"] = entries
    _save_support_whiteboard(run_dir, board)
    _append_support_whiteboard_log(run_dir, text)
    return _compact_whiteboard_snapshot(board, max_entries=5)
