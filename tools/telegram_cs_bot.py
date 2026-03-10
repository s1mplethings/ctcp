#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import urllib.error
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXTERNALS = ROOT / "scripts" / "externals"
SCRIPTS_DIR = ROOT / "scripts"
if str(EXTERNALS) not in sys.path:
    sys.path.insert(0, str(EXTERNALS))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
try:
    from openai_responses_client import call_openai_responses
except Exception:
    call_openai_responses = None  # type: ignore[assignment]
try:
    import ctcp_dispatch
except Exception:
    ctcp_dispatch = None  # type: ignore[assignment]
try:
    from tools.providers import api_agent, codex_agent, manual_outbox, mock_agent, ollama_agent
except Exception:
    api_agent = None  # type: ignore[assignment]
    codex_agent = None  # type: ignore[assignment]
    manual_outbox = None  # type: ignore[assignment]
    mock_agent = None  # type: ignore[assignment]
    ollama_agent = None  # type: ignore[assignment]
try:
    from tools import local_librarian
except Exception:
    local_librarian = None  # type: ignore[assignment]
try:
    from tools.stylebank import choose_variants_from_state
except Exception:
    choose_variants_from_state = None  # type: ignore[assignment]
try:
    from frontend.conversation_mode_router import is_greeting_only as frontend_is_greeting_only
    from frontend.message_sanitizer import sanitize_internal_text as frontend_sanitize_internal_text
    from frontend.missing_info_rewriter import (
        infer_missing_fields_from_text as frontend_infer_missing_fields_from_text,
    )
    from frontend.missing_info_rewriter import rewrite_missing_requirements as frontend_rewrite_missing_requirements
    from frontend.project_manager_mode import (
        build_project_manager_context as frontend_build_project_manager_context,
    )
    from frontend.project_manager_mode import is_generic_intake_question as frontend_is_generic_intake_question
    from frontend.response_composer import render_frontend_output as frontend_render_frontend_output
except Exception:
    frontend_is_greeting_only = None  # type: ignore[assignment]
    frontend_sanitize_internal_text = None  # type: ignore[assignment]
    frontend_infer_missing_fields_from_text = None  # type: ignore[assignment]
    frontend_rewrite_missing_requirements = None  # type: ignore[assignment]
    frontend_build_project_manager_context = None  # type: ignore[assignment]
    frontend_is_generic_intake_question = None  # type: ignore[assignment]
    frontend_render_frontend_output = None  # type: ignore[assignment]
try:
    from ctcp_front_bridge import (
        BridgeError as FrontBridgeError,
        ctcp_advance as bridge_ctcp_advance,
        ctcp_get_last_report as bridge_ctcp_get_last_report,
        ctcp_get_status as bridge_ctcp_get_status,
        ctcp_list_decisions_needed as bridge_ctcp_list_decisions_needed,
        ctcp_new_run as bridge_ctcp_new_run,
        ctcp_submit_decision as bridge_ctcp_submit_decision,
        ctcp_upload_artifact as bridge_ctcp_upload_artifact,
    )
except Exception:
    FrontBridgeError = RuntimeError  # type: ignore[assignment]
    bridge_ctcp_advance = None  # type: ignore[assignment]
    bridge_ctcp_get_last_report = None  # type: ignore[assignment]
    bridge_ctcp_get_status = None  # type: ignore[assignment]
    bridge_ctcp_list_decisions_needed = None  # type: ignore[assignment]
    bridge_ctcp_new_run = None  # type: ignore[assignment]
    bridge_ctcp_submit_decision = None  # type: ignore[assignment]
    bridge_ctcp_upload_artifact = None  # type: ignore[assignment]

DEFAULT_LANG = "zh"
MAX_MESSAGE_CHARS = 3800
MAX_OUTBOX_PUSH_PER_TICK = 3
MAX_AGENT_DISPATCH_PER_TICK = 1
TRACE_COOLDOWN_SECONDS = 10.0
AUTO_ADVANCE_STEPS_PER_TICK = 1
BLOCKED_ADVANCE_COOLDOWN_SECONDS = 180.0
SUPPORT_SESSION_STATE_REL = Path("artifacts") / "support_session_state.json"
SUPPORT_INBOX_REL = Path("artifacts") / "support_inbox.jsonl"
SUPPORT_ROUTER_TRACE_REL = Path("artifacts") / "support_router_trace.jsonl"
SUPPORT_ROUTER_LATEST_REL = Path("artifacts") / "support_router.latest.json"
SUPPORT_ROUTER_PROVIDER_REL = Path("artifacts") / "support_router.provider.json"
SUPPORT_REPLY_PROVIDER_REL = Path("artifacts") / "support_reply.provider.json"
SUPPORT_REPLY_PROMPT_REL = Path("artifacts") / "support_reply_prompt_input.md"
SUPPORT_ROUTER_PROMPT_REL = Path("artifacts") / "support_router_prompt_input.md"
SUPPORT_HANDOFF_TRACE_REL = Path("artifacts") / "support_handoff_trace.jsonl"
SUPPORT_WHITEBOARD_REL = Path("artifacts") / "support_whiteboard.json"
SUPPORT_WHITEBOARD_LOG_REL = Path("artifacts") / "support_whiteboard.md"
SUPPORT_WHITEBOARD_SCHEMA_VERSION = "ctcp-support-whiteboard-v1"
SUPPORT_ROUTER_PROMPT_PATH = ROOT / "agents" / "prompts" / "support_lead_router.md"
SUPPORT_REPLY_PROMPT_PATH = ROOT / "agents" / "prompts" / "support_lead_reply.md"
SUPPORT_KNOWN_PROVIDERS = {"manual_outbox", "ollama_agent", "api_agent", "codex_agent", "mock_agent"}
INTERNAL_SUPPORT_OUTBOX_TARGETS = {
    SUPPORT_ROUTER_PROVIDER_REL.as_posix().lower(),
    SUPPORT_REPLY_PROVIDER_REL.as_posix().lower(),
    SUPPORT_ROUTER_PROMPT_REL.as_posix().lower(),
    SUPPORT_REPLY_PROMPT_REL.as_posix().lower(),
}
INTERNAL_REPLY_MARKERS = (
    "trace",
    "trace.md",
    "outbox",
    "analysis.md",
    "plan_draft.md",
    "artifacts/",
    "logs/",
    "diff --git",
    "waiting for",
    "blocked_needs_input",
    "internal prompt",
    "raw prompt",
    "artifact",
    "patch",
    "run.json",
    "guardrails",
    "guardrails_written",
    "run_created",
    "run_dir",
    "orchestrator",
    "step",
    "support_router",
    "support_handoff",
    "support_session_state",
)
INTERNAL_WAITING_PATTERN = re.compile(r"\bwaiting\s+for\s+[^\s]+\.(?:md|json|patch)\b", flags=re.IGNORECASE)
TRACE_MILESTONES_ZH = {
    "guardrails_written": "已经了解了你的需求范围",
    "run_created": "已经开始为你处理了",
}
TRACE_MILESTONES_EN = {
    "guardrails_written": "I've understood your requirements.",
    "run_created": "I've started working on this for you.",
}
BACKTICK_FILE_RE = re.compile(r"`[^`\n]+\.(md|json|patch|txt|yaml|yml|log|zip|py)`", flags=re.IGNORECASE)
LIST_PREFIX_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+")
MECHANICAL_BAN_PHRASES = (
    "为了不耽误进度",
    "我记得你在推进",
    "当前重点是",
    "当前重点：",
    "需要补齐",
    "关键信息",
    "往前进了",
    "里程碑",
    "推进到下一",
    "自动推进",
    "默认路径",
    "安全默认",
    "可验证的小步",
    "对齐优先级",
)


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())


def parse_int(raw: str, default: int) -> int:
    try:
        n = int(str(raw).strip())
        return n if n > 0 else default
    except Exception:
        return default


def parse_bool(raw: str, default: bool) -> bool:
    x = str(raw or "").strip().lower()
    if not x:
        return default
    if x in {"1", "true", "yes", "on"}:
        return True
    if x in {"0", "false", "no", "off"}:
        return False
    return default


def _dedupe_text_list(items: list[str], *, limit: int) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max(1, int(limit)):
            break
    return out


def _suggest_temporary_project_name(task_text: str, lang: str) -> str:
    low = str(task_text or "").strip().lower()
    if not low:
        return ""
    if any(k in low for k in ("drone", "无人机", "uav", "航拍")) and any(
        k in low for k in ("point cloud", "点云", "建图", "mapping")
    ):
        return "SkyMap Flow"
    if any(k in low for k in ("point cloud", "点云", "reconstruction", "重建")):
        return "AeroCloud"
    if any(k in low for k in ("support bot", "客服bot", "customer support")):
        return "OperatorBridge"
    if str(lang).lower() == "en":
        return "Project Northline"
    return "北线计划"


def parse_allowlist(raw: str) -> set[int] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    out: set[int] = set()
    for p in text.split(","):
        t = p.strip()
        if not t:
            continue
        try:
            out.add(int(t))
        except Exception:
            continue
    return out or None


def short_tail(text: str, max_lines: int = 12, max_chars: int = 1400) -> str:
    lines = [x for x in (text or "").splitlines() if x.strip()]
    out = "\n".join(lines[-max_lines:])
    return out[-max_chars:] if len(out) > max_chars else out


def safe_relpath(raw: str) -> str:
    rel = str(raw or "").strip().replace("\\", "/")
    if not rel or rel.startswith("/") or re.match(r"^[A-Za-z]:[/\\]", rel):
        raise ValueError("bad path")
    parts = [p for p in rel.split("/") if p not in {"", "."}]
    if not parts or any(p == ".." for p in parts):
        raise ValueError("bad path")
    return "/".join(parts)


def ensure_within_run_dir(run_dir: Path, rel_path: str) -> Path:
    rel = safe_relpath(rel_path)
    base = run_dir.resolve()
    target = (base / rel).resolve()
    target.relative_to(base)
    return target


def safe_agent_name(raw: str) -> str:
    name = str(raw or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", name):
        raise ValueError("invalid agent")
    return name


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp.{uuid.uuid4().hex}")
    tmp.write_bytes(payload)
    os.replace(str(tmp), str(path))


def atomic_write_text(path: Path, text: str) -> None:
    atomic_write_bytes(path, text.encode("utf-8"))


def append_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def parse_key_line(text: str, key: str) -> str:
    pat = re.compile(rf"^{re.escape(key)}\s*:\s*(.*)$", re.IGNORECASE)
    for ln in (text or "").splitlines():
        m = pat.match(ln.strip())
        if m:
            return m.group(1).strip()
    return ""


def load_seen(raw: str) -> list[str]:
    try:
        doc = json.loads(raw or "[]")
        if isinstance(doc, list):
            return [str(x) for x in doc if str(x).strip()]
    except Exception:
        pass
    return []


def save_seen(items: list[str]) -> str:
    return json.dumps(sorted(set(items)), ensure_ascii=False)


def _normalize_rel_for_match(raw: str) -> str:
    text = str(raw or "").strip().replace("\\", "/")
    text = re.sub(r"/+", "/", text)
    return text.lstrip("./").lower()


def _is_internal_support_target_path(path: str) -> bool:
    norm = _normalize_rel_for_match(path)
    if not norm:
        return False
    if norm in INTERNAL_SUPPORT_OUTBOX_TARGETS:
        return True
    # Keep a defensive fallback for slightly different prompt headers/path prefixes.
    return ("support_router.provider" in norm) or ("support_reply.provider" in norm)


def parse_api_json(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    raw = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        doc = json.loads(raw)
        return doc if isinstance(doc, dict) else None
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return None
    try:
        doc = json.loads(m.group(0))
        return doc if isinstance(doc, dict) else None
    except Exception:
        return None


def _safe_float(raw: Any, default: float = 0.0) -> float:
    try:
        value = float(str(raw).strip())
    except Exception:
        return default
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def _safe_str_list(raw: Any, max_items: int = 8, max_chars: int = 120) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    for item in raw:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        out.append(text[:max_chars])
        if len(out) >= max_items:
            break
    return out


def _safe_memory_slots(raw: Any) -> dict[str, str]:
    keys = ("customer_name", "preferred_style", "current_topic", "last_request")
    out = {k: "" for k in keys}
    if not isinstance(raw, dict):
        return out
    for key in keys:
        text = re.sub(r"\s+", " ", str(raw.get(key, "")).strip())
        out[key] = text[:220]
    return out


def _is_retryable_telegram_error(exc: Exception) -> bool:
    text = str(exc or "").lower()
    retry_markers = (
        "unexpected_eof_while_reading",
        "eof occurred in violation of protocol",
        "timed out",
        "timeout",
        "temporary failure",
        "connection reset",
        "connection aborted",
        "ssl:",
    )
    if any(marker in text for marker in retry_markers):
        return True
    return isinstance(exc, (urllib.error.URLError, TimeoutError, ConnectionResetError, ConnectionAbortedError))


def _next_action_from_goal(goal_text: str, lang: str) -> str:
    goal = re.sub(r"\s+", " ", str(goal_text or "").strip())
    if not goal:
        if str(lang).lower() == "en":
            return "Let me understand what you need most, then I'll get started right away."
        return "先确认你最需要帮忙的是什么，然后马上处理。"
    low = goal.lower()
    if any(k in goal for k in ("客服", "bot", "机器人")) or any(k in low for k in ("support bot", "customer service", "chatbot")):
        if str(lang).lower() == "en":
            return "Let me understand what you'd like changed, then I'll make it happen."
        return "先了解一下你想要改成什么样，然后帮你调整。"
    if any(k in goal for k in ("修复", "改", "优化", "调整", "重构")) or any(k in low for k in ("fix", "improve", "optimize", "refactor")):
        if str(lang).lower() == "en":
            return "Let me find the specific issue and fix it for you right away."
        return "先帮你找到具体问题在哪里，然后马上修复。"
    if str(lang).lower() == "en":
        return "Let me understand what you need, then I'll get started."
    return "先了解一下你的需求，然后马上开始帮你处理。"


def _extract_memory_slots(text: str, lang: str, existing: dict[str, str] | None = None) -> dict[str, str]:
    slots = _safe_memory_slots(existing or {})
    raw = str(text or "").strip()
    low = raw.lower()
    if not raw:
        return slots

    zh_name = re.search(r"(?:我叫|叫我|你可以叫我|称呼我)\s*([A-Za-z0-9_\-\u4e00-\u9fa5]{1,20})", raw)
    en_name = re.search(r"(?:my name is|call me)\s+([A-Za-z][A-Za-z0-9_-]{0,20})", low, flags=re.IGNORECASE)
    if zh_name:
        slots["customer_name"] = zh_name.group(1).strip()[:40]
    elif en_name:
        slots["customer_name"] = en_name.group(1).strip()[:40]

    if any(k in raw for k in ("简短", "简洁", "短一点", "直接点", "别太长")) or any(k in low for k in ("brief", "concise", "short")):
        slots["preferred_style"] = "concise"
    elif any(k in raw for k in ("详细", "具体一点", "展开", "多一些细节")) or any(
        k in low for k in ("detailed", "more detail", "in depth")
    ):
        slots["preferred_style"] = "detailed"

    if not is_smalltalk_only_message(raw):
        slots["current_topic"] = _brief_text(raw, max_chars=140)
    slots["last_request"] = _brief_text(raw, max_chars=180)
    return slots


def default_support_session_state() -> dict[str, Any]:
    return {
        "session_summary": "",
        "user_goal": "",
        "execution_goal": "",
        "execution_next_action": "",
        "collab_role": "support_lead",
        "confirmed": [],
        "open_questions": [],
        "last_actions": "",
        "last_action_taken": "",
        "turn_index": 0,
        "last_intent": "",
        "last_style_seed": "",
        "style_seed": "",
        "router_low_conf_streak": 0,
        "blocked_signature": "",
        "blocked_since_ts": 0.0,
        "auto_advance_pause_until_ts": 0.0,
        "memory_slots": _safe_memory_slots({}),
    }


def load_support_session_state(run_dir: Path) -> dict[str, Any]:
    state = default_support_session_state()
    path = run_dir / SUPPORT_SESSION_STATE_REL
    if not path.exists():
        return state
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return state
    if not isinstance(doc, dict):
        return state
    state["session_summary"] = re.sub(r"\s+", " ", str(doc.get("session_summary", "")).strip())[:600]
    state["user_goal"] = re.sub(r"\s+", " ", str(doc.get("user_goal", "")).strip())[:220]
    state["execution_goal"] = re.sub(r"\s+", " ", str(doc.get("execution_goal", "")).strip())[:260]
    state["execution_next_action"] = re.sub(r"\s+", " ", str(doc.get("execution_next_action", "")).strip())[:260]
    state["collab_role"] = _normalize_collab_role(str(doc.get("collab_role", "support_lead")))
    state["confirmed"] = _safe_str_list(doc.get("confirmed"), max_items=10, max_chars=120)
    state["open_questions"] = _safe_str_list(doc.get("open_questions"), max_items=3, max_chars=140)
    last_action = re.sub(
        r"\s+",
        " ",
        str(doc.get("last_action_taken", doc.get("last_actions", ""))).strip(),
    )[:220]
    state["last_actions"] = last_action
    state["last_action_taken"] = last_action
    try:
        state["turn_index"] = max(0, int(doc.get("turn_index", 0) or 0))
    except Exception:
        state["turn_index"] = 0
    state["last_intent"] = re.sub(r"\s+", " ", str(doc.get("last_intent", "")).strip())[:80]
    state["last_style_seed"] = re.sub(r"\s+", " ", str(doc.get("last_style_seed", doc.get("style_seed", ""))).strip())[:80]
    state["style_seed"] = state["last_style_seed"]
    try:
        state["router_low_conf_streak"] = max(0, int(doc.get("router_low_conf_streak", 0) or 0))
    except Exception:
        state["router_low_conf_streak"] = 0
    state["blocked_signature"] = re.sub(r"\s+", " ", str(doc.get("blocked_signature", "")).strip())[:220]
    try:
        state["blocked_since_ts"] = max(0.0, float(doc.get("blocked_since_ts", 0.0) or 0.0))
    except Exception:
        state["blocked_since_ts"] = 0.0
    try:
        state["auto_advance_pause_until_ts"] = max(0.0, float(doc.get("auto_advance_pause_until_ts", 0.0) or 0.0))
    except Exception:
        state["auto_advance_pause_until_ts"] = 0.0
    state["memory_slots"] = _safe_memory_slots(doc.get("memory_slots"))
    return state


def save_support_session_state(run_dir: Path, state: dict[str, Any]) -> None:
    current = default_support_session_state()
    current.update(state if isinstance(state, dict) else {})
    try:
        blocked_since = max(0.0, float(current.get("blocked_since_ts", 0.0) or 0.0))
    except Exception:
        blocked_since = 0.0
    try:
        auto_pause_until = max(0.0, float(current.get("auto_advance_pause_until_ts", 0.0) or 0.0))
    except Exception:
        auto_pause_until = 0.0
    payload = {
        "session_summary": re.sub(r"\s+", " ", str(current.get("session_summary", "")).strip())[:600],
        "user_goal": re.sub(r"\s+", " ", str(current.get("user_goal", "")).strip())[:220],
        "execution_goal": re.sub(r"\s+", " ", str(current.get("execution_goal", "")).strip())[:260],
        "execution_next_action": re.sub(r"\s+", " ", str(current.get("execution_next_action", "")).strip())[:260],
        "collab_role": _normalize_collab_role(str(current.get("collab_role", "support_lead"))),
        "confirmed": _safe_str_list(current.get("confirmed"), max_items=10, max_chars=120),
        "open_questions": _safe_str_list(current.get("open_questions"), max_items=3, max_chars=140),
        "last_actions": re.sub(
            r"\s+",
            " ",
            str(current.get("last_action_taken", current.get("last_actions", ""))).strip(),
        )[:220],
        "last_action_taken": re.sub(
            r"\s+",
            " ",
            str(current.get("last_action_taken", current.get("last_actions", ""))).strip(),
        )[:220],
        "turn_index": max(0, int(current.get("turn_index", 0) or 0)),
        "last_intent": re.sub(r"\s+", " ", str(current.get("last_intent", "")).strip())[:80],
        "last_style_seed": re.sub(r"\s+", " ", str(current.get("last_style_seed", current.get("style_seed", ""))).strip())[:80],
        "style_seed": re.sub(
            r"\s+",
            " ",
            str(current.get("last_style_seed", current.get("style_seed", ""))).strip(),
        )[:80],
        "router_low_conf_streak": max(0, int(current.get("router_low_conf_streak", 0) or 0)),
        "blocked_signature": re.sub(r"\s+", " ", str(current.get("blocked_signature", "")).strip())[:220],
        "blocked_since_ts": blocked_since,
        "auto_advance_pause_until_ts": auto_pause_until,
        "memory_slots": _safe_memory_slots(current.get("memory_slots")),
    }
    atomic_write_text(run_dir / SUPPORT_SESSION_STATE_REL, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def default_support_whiteboard_state() -> dict[str, Any]:
    return {
        "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
        "entries": [],
    }


def _safe_whiteboard_hits(rows: Any, *, max_items: int = 5) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for item in rows:
        if not isinstance(item, dict):
            continue
        path = re.sub(r"\s+", " ", str(item.get("path", "")).strip())[:240]
        snippet = _brief_text(str(item.get("snippet", "")), max_chars=220)
        try:
            start_line = max(1, int(item.get("start_line", 1) or 1))
        except Exception:
            start_line = 1
        if not path:
            continue
        out.append(
            {
                "path": path,
                "start_line": start_line,
                "snippet": snippet,
            }
        )
        if len(out) >= max(1, int(max_items)):
            break
    return out


def _safe_whiteboard_entries(rows: Any, *, max_items: int = 60) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    limit = max(1, int(max_items))
    for item in rows[-limit:]:
        if not isinstance(item, dict):
            continue
        role = re.sub(r"\s+", " ", str(item.get("role", "")).strip().lower())[:32] or "unknown"
        kind = re.sub(r"\s+", " ", str(item.get("kind", "")).strip().lower())[:48] or "note"
        text = _brief_text(str(item.get("text", "")).strip(), max_chars=260)
        query = _brief_text(str(item.get("query", "")).strip(), max_chars=180)
        question = _brief_text(str(item.get("question", "")).strip(), max_chars=180)
        entry = {
            "ts": re.sub(r"\s+", " ", str(item.get("ts", now_iso())).strip())[:40],
            "role": role,
            "kind": kind,
            "text": text,
        }
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


def load_support_whiteboard_state(run_dir: Path) -> dict[str, Any]:
    state = default_support_whiteboard_state()
    path = run_dir / SUPPORT_WHITEBOARD_REL
    if not path.exists():
        return state
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return state
    if not isinstance(doc, dict):
        return state
    state["entries"] = _safe_whiteboard_entries(doc.get("entries", []), max_items=60)
    return state


def save_support_whiteboard_state(run_dir: Path, state: dict[str, Any]) -> None:
    payload = {
        "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
        "entries": _safe_whiteboard_entries((state or {}).get("entries", []), max_items=60),
    }
    atomic_write_text(run_dir / SUPPORT_WHITEBOARD_REL, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _fallback_style_choice(chat_id: int, turn_index: int, lang: str) -> dict[str, str]:
    turn = max(1, int(turn_index))
    if str(lang).lower() == "en":
        return {
            "opener": "I have your request and I'm on it.",
            "transition": "I'm working on the next step for you now.",
            "closer": "Just to make sure,",
            "question_style": "Could you confirm something for me?",
            "intent": "general",
            "style_seed": "fallback-en",
            "seed": f"fallback-{chat_id}-{turn}",
        }
    return {
        "opener": "我收到你的需求了。",
        "transition": "我马上帮你处理下一步。",
        "closer": "还想确认一下，",
        "question_style": "你方便确认一下这个吗？",
        "intent": "general",
        "style_seed": "fallback-zh",
        "seed": f"fallback-{chat_id}-{turn}",
    }


def choose_style(
    *,
    chat_id: int,
    turn_index: int,
    lang: str,
    state: dict[str, Any] | None = None,
    route_doc: dict[str, Any] | None = None,
) -> dict[str, str]:
    if choose_variants_from_state is not None:
        try:
            return choose_variants_from_state(
                chat_id=chat_id,
                turn_index=max(1, int(turn_index)),
                route_doc=route_doc,
                state=state,
                lang=lang,
            )
        except Exception:
            pass
    return _fallback_style_choice(chat_id=chat_id, turn_index=turn_index, lang=lang)


def is_explicit_continuation_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    zh_patterns = (
        r"(继续|接着).{0,8}(上次|之前|原来|那个).{0,8}(项目|任务|会话)",
        r"(上次|之前|原来).{0,8}(项目|任务|会话).{0,8}(继续|接着)",
        r"(我的|之前的).{0,8}(项目|任务).{0,8}(还在|还剩|继续)",
        r"还有.{0,8}(我的|之前的)?.{0,8}(项目|任务)",
    )
    if any(re.search(p, raw) for p in zh_patterns):
        return True
    en_hits = (
        "continue previous project",
        "continue last project",
        "pick up where we left off",
        "still have my project",
        "continue my project",
        "previous run",
    )
    if any(k in low for k in en_hits):
        return True
    return False


def detect_intent(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    low = raw.lower()
    if is_cleanup_project_request(raw):
        return ("cancel_run", raw)
    if any(k in raw for k in ("查看进度", "看进度", "调试")) or re.search(r"\bdebug\b", low):
        return ("debug", "")
    if "英文" in raw or re.search(r"\benglish\b|\ben\b", low):
        return ("lang", "en")
    if "中文" in raw or re.search(r"\bchinese\b|\bzh\b", low):
        return ("lang", "zh")
    if is_explicit_continuation_request(raw):
        return ("status", "")
    if any(
        k in raw
        for k in (
            "现在有在进行的项目",
            "有在进行的项目",
            "现在在进行什么",
            "现在在做什么",
            "正在做什么",
            "有在跑的项目",
            "当前项目",
            "进行中",
            "在进行",
        )
    ) or any(k in low for k in ("active run", "what is running", "what are you doing now")):
        return ("status", "")
    if any(k in raw for k in ("进度", "状态", "卡点", "阻塞")) or any(
        k in low for k in ("progress", "status", "stuck", "blocked")
    ):
        return ("status", "")
    if any(k in raw for k in ("继续", "推进", "重试")) or any(k in low for k in ("continue", "advance", "retry")):
        return ("advance", "1")
    if any(k in raw for k in ("bundle", "失败包", "故障包")) or "failure bundle" in low:
        return ("bundle", "")
    if any(k in raw for k in ("报告", "验收", "验证报告")) or any(k in low for k in ("report", "verify")):
        return ("report", "")
    if (
        any(k in raw for k in ("需要我决定", "需要我确认", "要我决定", "要我确认", "有没有需要我", "我要决定什么", "我需要决定什么"))
        or any(k in low for k in ("need me to decide", "need my decision", "need me to confirm", "anything for me to decide"))
    ):
        return ("decision", "")
    if "outbox" in low or any(k in raw for k in ("待办", "问题", "提问")):
        return ("outbox", "")
    return ("note", raw)


def looks_like_new_goal(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    low = raw.lower()
    explicit = (
        "新建" in raw
        or "重新开始" in raw
        or "开一个新的项目" in raw
        or "新的项目" in raw
        or "新任务" in raw
        or "之前的不要了" in raw
        or "旧的不要了" in raw
        or "不要旧的" in raw
        or "new run" in low
        or "new project" in low
        or "new task" in low
        or "old one not needed" in low
        or "drop the old" in low
        or "start over" in low
        or "from scratch" in low
    )
    if explicit:
        return True
    cn_starts = ("我想要", "我要做", "帮我做", "请帮我", "需求是", "目标是", "我需要")
    en_starts = ("i want", "i need", "build ", "create ", "make ", "help me build")
    if any(raw.startswith(x) for x in cn_starts) and len(raw) >= 10:
        return True
    if any(low.startswith(x) for x in en_starts) and len(low) >= 16:
        return True
    return False


def is_smalltalk_only_message(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    if frontend_is_greeting_only is not None:
        try:
            if frontend_is_greeting_only(raw):
                return True
        except Exception:
            pass
    exact = {
        "你好",
        "嗨",
        "哈喽",
        "在吗",
        "早",
        "早安",
        "午安",
        "晚上好",
        "hello",
        "hi",
        "hey",
        "test",
        "?",
        "？",
        "thanks",
        "thank you",
        "thx",
        "谢谢",
        "感谢",
        "你是谁",
        "你能做什么",
        "怎么用",
        "who are you",
        "what can you do",
    }
    if raw in exact or low in exact:
        return True
    if len(raw) <= 12 and any(raw.startswith(x) for x in ("你好", "嗨", "哈喽", "谢谢", "感谢")):
        return True
    if len(low) <= 24 and any(low.startswith(x) for x in ("hello", "hi", "hey", "thanks", "thank")):
        return True
    if len(raw) <= 18 and ("你能做什么" in raw or "你是谁" in raw):
        return True
    if len(low) <= 40 and ("what can you do" in low or "who are you" in low):
        return True
    return False


def is_project_creation_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    zh_hits = (
        "创建一个项目",
        "创建项目",
        "做一个项目",
        "做个项目",
        "建一个项目",
        "新建项目",
        "搞一个项目",
        "起一个项目",
    )
    en_hits = (
        "create a project",
        "create project",
        "start a project",
        "start project",
        "new project",
        "build a project",
        "set up a project",
    )
    if any(k in raw for k in zh_hits):
        return True
    if any(k in low for k in en_hits):
        return True
    return False


def is_cleanup_project_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    if raw in {"先清理", "清理一下", "先清理下", "先清理一下", "先清除", "先删掉"}:
        return True
    verbs_zh = (
        "清除",
        "删除",
        "删",
        "删掉",
        "删了",
        "重置",
        "清空",
        "清理",
        "停掉",
        "不要继续",
        "不想继续",
        "不想要继续",
        "不继续",
        "取消",
    )
    nouns_zh = ("项目", "任务", "run", "run_dir", "会话", "路径", "目录", "旧的", "之前那个", "之前的", "当前")
    verbs_en = ("clear", "delete", "reset", "cancel", "stop", "drop")
    nouns_en = ("project", "task", "run", "session", "previous")
    zh_hit = any(v in raw for v in verbs_zh) and any(n in raw for n in nouns_zh)
    en_hit = any(v in low for v in verbs_en) and any(n in low for n in nouns_en)
    if zh_hit or en_hit:
        return True
    # Handle more natural Chinese phrasings, e.g. "不想要继续之前那个项目，先清理一下"
    if re.search(r"(不(?:想|要).{0,3}继续).{0,16}(项目|任务|run|会话|之前)", raw):
        return True
    if re.search(r"(清理|清空|删除|重置).{0,16}(项目|任务|run|会话|之前)", raw):
        return True
    if re.search(r"^(先)?(清理|清空|清除|删除).{0,6}$", raw):
        return True
    if re.search(r"(删除|删掉|删了).{0,20}(run_dir|路径|目录)", raw):
        return True
    if re.search(r"(彻底删除|永久删除|现在就删|先删|删了然后继续)", raw):
        return True
    if ("删" in raw or "删除" in raw) and any(k in raw for k in ("旧的", "之前", "项目", "run", "会话")):
        return True
    return False


def _project_kickoff_reply(lang: str) -> tuple[str, str]:
    if str(lang).lower() == "en":
        ask = "Could you tell me more about what kind of project you have in mind?"
        reply = "\n\n".join(
            [
                "Sure, I'd be happy to help you with a project!",
                f"To get started, I just need a bit more information. {ask}",
            ]
        )
        return reply, ask
    ask = "方便告诉我你想做什么类型的项目吗？"
    reply = "\n\n".join(
        [
            "当然可以，我很乐意帮你！",
            f"我先了解一下你的需求，这样能更好地帮到你。{ask}",
        ]
    )
    return reply, ask


def _cleanup_project_reply(lang: str) -> tuple[str, str, list[dict[str, Any]]]:
    if str(lang).lower() == "en":
        ask = ""
        reply = "Got it. The old records were removed, and I'll continue with the new project."
    else:
        ask = ""
        reply = "收到，旧记录已按你的要求删除，后续按新项目继续。"
    actions: list[dict[str, Any]] = [
        {"type": "delete_old_session_and_unbind", "scope": "session", "mode": "delete"}
    ]
    return reply, ask, actions


def _prompt_topic_for_customer(prompt_text: str, target_path: str, lang: str) -> str:
    raw = _brief_text(prompt_text, max_chars=180)
    cleaned = re.sub(r"```[\s\S]*?```", " ", raw)
    cleaned = cleaned.replace("`", " ")
    cleaned = re.sub(r"[{}\[\]<>\"']", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,:;|")
    low = cleaned.lower()
    if (
        (not cleaned)
        or low in {"none", "null", "string", "object", "array"}
        or " - none" in low
        or re.search(r"\b(string|none|null|object|array)\b", low)
    ):
        cleaned = ""
    # If symbol ratio is too high, this is likely a malformed internal fragment.
    if cleaned:
        symbols = sum(1 for ch in cleaned if not (ch.isalnum() or ("\u4e00" <= ch <= "\u9fff") or ch.isspace()))
        if symbols / max(1, len(cleaned)) > 0.35:
            cleaned = ""
    if cleaned:
        return cleaned[:120]
    base = Path(str(target_path or "")).name
    base = re.sub(r"\.[A-Za-z0-9]+$", "", base)
    base = re.sub(r"[_\-]+", " ", base).strip()
    if not base or base.lower() in {"none", "string", "unknown"}:
        return "some additional details" if str(lang).lower() == "en" else "一些补充信息"
    return _brief_text(base, max_chars=80)


def _sanitize_internal_for_customer(text: str, lang: str, fallback: str = "") -> str:
    raw = str(text or "").strip()
    if not raw:
        return str(fallback or "").strip()
    if frontend_sanitize_internal_text is not None:
        try:
            sanitized = frontend_sanitize_internal_text(raw)
            cleaned = str(getattr(sanitized, "text", "") or "").strip()
            if cleaned:
                return cleaned
        except Exception:
            pass
    cleaned, _removed = sanitize_customer_reply_text(raw, lang)
    cleaned = rewrite_mechanical_phrases(cleaned, lang)
    cleaned = re.sub(r"\s+", " ", str(cleaned or "").strip())
    if cleaned:
        return cleaned
    return str(fallback or "").strip()


def _rewrite_missing_questions_for_customer(*, raw_text: str, task_summary: str, lang: str, max_questions: int = 2) -> list[str]:
    if frontend_infer_missing_fields_from_text is None or frontend_rewrite_missing_requirements is None:
        return []
    try:
        fields = frontend_infer_missing_fields_from_text(raw_text)
    except Exception:
        return []
    if not fields:
        return []
    try:
        questions = frontend_rewrite_missing_requirements(
            fields,
            {
                "lang": lang,
                "task_summary": task_summary,
                "max_questions": max_questions,
            },
        )
    except Exception:
        return []
    out: list[str] = []
    limit = max(1, int(max_questions or 1))
    for item in questions:
        question = _sanitize_internal_for_customer(str(item or "").strip(), lang)
        if not question:
            continue
        if question not in out:
            out.append(question)
        if len(out) >= limit:
            break
    return out


def _is_generic_progress_reply(text: str, lang: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if not raw:
        return True
    low = raw.lower()
    if str(lang).lower() == "en":
        patterns = (
            "moved to the next milestone",
            "keep execution going",
            "advanced to the next stage",
        )
        return any(p in low for p in patterns)
    patterns_zh = ("推进到下一里程碑", "继续执行", "推进到下一阶段", "我正在继续帮你处理", "我马上帮你处理")
    return any(p in raw for p in patterns_zh)


def smalltalk_reply(text: str, lang: str, state: dict[str, Any] | None = None) -> str:
    raw = str(text or "").strip()
    low = raw.lower()
    if not raw:
        return ""
    slots = _safe_memory_slots((state or {}).get("memory_slots"))
    topic_hint = (
        str(slots.get("current_topic", "")).strip()
        or str((state or {}).get("execution_goal", "")).strip()
        or str((state or {}).get("user_goal", "")).strip()
    )
    if topic_hint and is_smalltalk_only_message(topic_hint):
        topic_hint = ""

    def _customer_topic_label(topic: str, cur_lang: str) -> str:
        t = _brief_text(str(topic or "").strip(), max_chars=80)
        if not t or is_smalltalk_only_message(t):
            return ""
        low_t = t.lower()
        zh_goal_markers = ("我想", "我要", "帮我", "请帮我", "我需要", "目标是")
        en_goal_markers = ("i want", "i need", "help me", "goal is", "could you", "can you")
        too_goal_like = len(t) > 22 or any(k in t for k in zh_goal_markers) or any(k in low_t for k in en_goal_markers)
        if not too_goal_like:
            return t
        if str(cur_lang).lower() == "en":
            if any(k in low_t for k in ("support", "customer service", "chatbot", "bot")):
                return "the support bot request"
            if "project" in low_t:
                return "the project request"
            return "your request"
        if any(k in t for k in ("客服", "机器人", "bot", "chatbot")):
            return "客服机器人需求"
        if "项目" in t:
            return "项目需求"
        return "当前需求"

    topic_label = _customer_topic_label(topic_hint, lang)
    greetings = {"你好", "嗨", "哈喽", "在吗", "早", "早安", "午安", "晚上好", "hello", "hi", "hey"}
    if raw in greetings or low in greetings:
        if str(lang).lower() == "en":
            return "Hi! How can I help you today?"
        return "你好！请问有什么可以帮到你的吗？"
    if any(x in raw for x in ("谢谢", "感谢")) or "thank" in low or "thx" in low:
        if str(lang).lower() == "en":
            return "You're welcome! Let me know if there's anything else I can help with."
        return "不客气！如果还有其他问题随时告诉我。"
    if any(x in raw for x in ("你是谁", "你能做什么", "怎么用")) or "what can you do" in low or "who are you" in low:
        if str(lang).lower() == "en":
            return (
                "I'm your customer service assistant. I can help you with product questions, "
                "order inquiries, troubleshooting, and feedback. "
                "What can I help you with today?"
            )
        return (
            "我是你的客服助手。我可以帮你查询订单、解答产品问题、处理售后，也可以转接人工客服。请问你需要什么帮助？"
        )
    return ""


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    raw = str(text or "").lower()
    return any(k.lower() in raw for k in keywords)


def _extract_single_question(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    for ln in raw.splitlines():
        line = ln.strip()
        if not line:
            continue
        line = re.sub(r"^(下一步|next)\s*[:：]\s*", "", line, flags=re.IGNORECASE).strip()
        if "？" in line or "?" in line:
            q = re.split(r"[?？]", line, maxsplit=1)[0].strip()
            if q:
                return q
    return ""


def _default_plan_rows(lang: str, context_text: str) -> list[str]:
    if str(lang).lower() == "en":
        return [
            "Let me look into this for you right away.",
            "I'll get back to you as soon as I have the details.",
        ]
    return [
        "我马上帮你查一下。",
        "有结果了第一时间告诉你。",
    ]


def _default_next_question(lang: str) -> str:
    if str(lang).lower() == "en":
        return "Is there anything else I can help you with?"
    return "还有什么我可以帮到你的吗？"


def _default_task_entry_question(lang: str, continuation_hint: bool = False) -> str:
    if str(lang).lower() == "en":
        if continuation_hint:
            return "Should I stay on the existing project path, or switch to a new issue first?"
        return "Which should I handle first: existing project path, new requirement, or error troubleshooting?"
    if continuation_hint:
        return "你希望沿用之前的项目路径，还是先切到新问题？"
    return "你现在更需要哪类处理：现有项目延续 / 新需求 / 报错排查？"


def _normalize_collab_role(value: str) -> str:
    raw = re.sub(r"\s+", "_", str(value or "").strip().lower())
    if raw in {"team_manager", "manager", "project_manager"}:
        return "team_manager"
    return "support_lead"


def is_team_manager_role_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    zh_hits = (
        "团队经理",
        "项目经理",
        "经理模式",
        "经理角色",
        "经理口吻",
    )
    en_hits = (
        "team manager",
        "project manager",
        "manager mode",
        "manager role",
    )
    if any(k in raw for k in zh_hits):
        return True
    if any(k in low for k in en_hits):
        return True
    return False


def is_support_lead_role_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    zh_hits = (
        "普通客服模式",
        "客服模式",
        "恢复客服",
        "取消经理模式",
    )
    en_hits = (
        "support mode",
        "customer support mode",
        "disable manager mode",
    )
    if any(k in raw for k in zh_hits):
        return True
    if any(k in low for k in en_hits):
        return True
    return False


def _role_switch_ack(lang: str, role: str) -> tuple[str, str]:
    final_role = _normalize_collab_role(role)
    if str(lang).lower() == "en":
        if final_role == "team_manager":
            return (
                "Understood. I will switch to team-manager mode and drive execution proactively. I will also ask you targeted questions only at key decision points.",
                "What is the single highest priority for this round: speed, quality, or cost?",
            )
        return (
            "Understood. I have switched back to support mode.",
            "What should I handle first this round?",
        )
    if final_role == "team_manager":
        return (
            "收到，我已切换到团队经理模式。后续我会主动推进执行，并只在关键决策点向你提一个最关键问题。",
            "这一轮你的唯一最高优先级是哪个：速度、质量、还是成本？",
        )
    return (
        "收到，我已切回普通客服模式。",
        "这轮你希望我先处理什么？",
    )


def _has_actionable_goal_details(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    if is_smalltalk_only_message(raw) or is_explicit_continuation_request(raw):
        return False
    if looks_like_new_goal(raw):
        return True
    zh_keywords = (
        "目标",
        "需求",
        "工作流",
        "流程",
        "生成",
        "优化",
        "速度",
        "精度",
        "质量",
        "成本",
        "无人机",
        "点云",
        "视频",
        "语义",
    )
    en_keywords = (
        "goal",
        "requirement",
        "workflow",
        "pipeline",
        "generate",
        "optimize",
        "speed",
        "latency",
        "quality",
        "cost",
        "drone",
        "point cloud",
        "video",
        "semantic",
    )
    score = sum(1 for k in zh_keywords if k in raw) + sum(1 for k in en_keywords if k in low)
    return score >= 2 or len(raw) >= 48


def _is_generic_followup_question(text: str, lang: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if not raw:
        return True
    norm = _normalize_next_question(raw, lang).rstrip("？?").lower()
    default_norm = _normalize_next_question(_default_next_question(lang), lang).rstrip("？?").lower()
    if norm == default_norm:
        return True
    low = raw.lower()
    generic_en = ("anything else", "help with", "provide a bit more detail", "could you provide this now")
    generic_zh = ("还有其他", "补充一些细节", "你现在方便提供吗", "请确认一下")
    if str(lang).lower() == "en":
        return any(k in low for k in generic_en)
    return any(k in raw for k in generic_zh)


def _replacement_char_count(text: str) -> int:
    return str(text or "").count("\ufffd")


def _normalize_next_question(text: str, lang: str) -> str:
    raw = re.sub(r"\s+", " ", str(text or "").strip()).replace("\ufffd", "").strip()
    if not raw:
        raw = _default_next_question(lang)
    # If question text already contains decoding replacement chars, fall back to
    # a safe default question rather than exposing mojibake to customers.
    if _replacement_char_count(str(text or "").strip()) > 0:
        raw = _default_next_question(lang)
    low = raw.lower()
    engineering_tokens = (
        "patch 路径",
        "patch路径",
        "可交付 patch",
        "run verify",
        "verify_repo",
        "run_dir",
        "outbox",
        "analysis.md",
        "plan_draft.md",
        "waiting for",
        "blocked_needs_input",
        "internal prompt",
        "raw prompt",
        "artifact",
        "patch",
        "trace",
        "diff --git",
        "artifacts/",
    )
    if any(token in low for token in engineering_tokens) or INTERNAL_WAITING_PATTERN.search(low):
        raw = _default_next_question(lang)
    head = re.split(r"[?？]", raw, maxsplit=1)[0].strip()
    if head:
        raw = head
    suffix = "?" if str(lang).lower() == "en" else "？"
    if not raw.endswith(("?", "？")):
        raw += suffix
    return raw


def _compose_three_part_reply(
    *,
    lang: str,
    conclusion: str,
    plans: list[str] | tuple[str, ...],
    next_question: str,
) -> str:
    plan_rows = [re.sub(r"\s+", " ", str(p).strip()) for p in plans if str(p).strip()]
    if not plan_rows:
        if str(lang).lower() == "en":
            plan_rows = ["I'll take care of this for you right away."]
        else:
            plan_rows = ["我这就帮你处理。"]
    plan_rows = plan_rows[:2]
    question = _normalize_next_question(next_question, lang)

    # Natural conversational format: conclusion sentence, plan sentence(s), optional question.
    parts: list[str] = []
    parts.append(re.sub(r"\s+", " ", str(conclusion).strip()))
    parts.append(" ".join(plan_rows))
    if question:
        parts.append(question)
    return "\n\n".join(p for p in parts if p)


def _line_has_internal_marker(line: str) -> bool:
    text = str(line or "").strip()
    if not text:
        return False
    low = text.lower()
    if any(marker in low for marker in INTERNAL_REPLY_MARKERS):
        return True
    if INTERNAL_WAITING_PATTERN.search(low):
        return True
    # Only filter backtick-wrapped file references (internal artifact paths),
    # not bare file extensions the customer might mention (e.g. "我要导出 .json").
    if BACKTICK_FILE_RE.search(text):
        return True
    # Only filter lines that look like internal file paths (contain path separators
    # plus internal directory names), not casual mentions of file formats.
    if "/" in text and re.search(r"(artifacts|outbox|logs|trace)\b", low):
        return True
    return False


def _split_paragraphs(text: str) -> list[str]:
    chunks = re.split(r"\n\s*\n", str(text or "").strip())
    out: list[str] = []
    for c in chunks:
        t = re.sub(r"\s+", " ", c.strip())
        if t:
            out.append(t)
    return out


def _contains_list_block(text: str) -> bool:
    rows = [ln for ln in str(text or "").splitlines() if ln.strip()]
    if not rows:
        return False
    streak = 0
    for ln in rows:
        if LIST_PREFIX_RE.match(ln):
            streak += 1
            if streak >= 2:
                return True
        else:
            streak = 0
    return False


def rewrite_to_paragraphs(text: str, lang: str) -> str:
    rows = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    bullets: list[str] = []
    plain: list[str] = []
    for ln in rows:
        if LIST_PREFIX_RE.match(ln):
            bullets.append(LIST_PREFIX_RE.sub("", ln).strip())
        else:
            plain.append(ln)
    merged: list[str] = []
    merged.extend([x for x in plain if x])
    if bullets:
        if str(lang).lower() == "en":
            merged.append("Here's what I'll take care of: " + "; ".join(bullets) + ".")
        else:
            merged.append("我会帮你处理这些：" + "；".join(bullets) + "。")
    if not merged:
        if str(lang).lower() == "en":
            merged = ["I'm working on it and will update you shortly."]
        else:
            merged = ["我在处理了，稍后告诉你进展。"]
    if len(merged) == 1:
        return merged[0]
    return "\n\n".join(merged[:4])


def _default_assumption_sentence(lang: str, assumption: str = "", style_seed: str = "") -> str:
    extra = re.sub(r"\s+", " ", str(assumption or "").strip())
    seed = f"{str(lang).lower()}|{style_seed}|{extra}"
    digest = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()
    if str(lang).lower() == "en":
        templates = [
            "I'll keep working on this and update you shortly.",
            "I'll continue from here and let you know if anything comes up.",
            "I'll take care of this and get back to you soon.",
            "I'll handle this for you — feel free to reach out anytime.",
        ]
        idx = int(digest[0:8], 16) % len(templates)
        if extra:
            return f"If there's nothing else, I'll go ahead with: {extra}."
        return templates[idx]
    templates_zh = [
        "我继续帮你处理，有新消息会及时告诉你。",
        "我先帮你处理着，有什么情况会第一时间跟你说。",
        "我这边继续处理，有结果马上通知你。",
        "我来处理，你有任何问题随时找我。",
    ]
    idx = int(digest[0:8], 16) % len(templates_zh)
    if extra:
        return f"如果没有其他补充，我就按这个方向帮你处理了：{extra}。"
    return templates_zh[idx]


def _progress_push_sentence(lang: str, question_needed: bool, assumption: str = "") -> str:
    if str(lang).lower() == "en":
        if question_needed:
            return "I'll continue processing right after your confirmation."
        return _default_assumption_sentence(lang, assumption, "")
    if question_needed:
        return "确认之后我马上帮你继续处理。"
    return _default_assumption_sentence(lang, assumption, "")


def _extract_section_value(text: str, labels: tuple[str, ...]) -> str:
    lines = [ln.strip() for ln in str(text or "").splitlines() if ln.strip()]
    for ln in lines:
        for label in labels:
            if ln.lower().startswith(label.lower()):
                value = ln[len(label) :].strip()
                if value:
                    return value
    return ""


def sanitize_customer_reply_text(text: str, lang: str) -> tuple[str, list[str]]:
    # Label prefixes that the LLM may emit despite instructions — strip them so
    # the output reads as natural prose rather than a report.
    _SECTION_LABELS = re.compile(
        r"^(结论[：:]|方案[：:]|下一步[：:]|计划[：:]|行动[：:]|"
        r"Conclusion:\s*|Plan:\s*|Next:\s*|Summary:\s*|Action:\s*)",
        re.IGNORECASE,
    )
    lines = str(text or "").splitlines()
    kept_raw: list[str] = []
    removed: list[str] = []
    for ln in lines:
        item = ln.rstrip()
        if not item.strip():
            if kept_raw and kept_raw[-1] != "":
                kept_raw.append("")
            continue
        if _line_has_internal_marker(item):
            removed.append(item.strip())
            continue
        # Drop lines with heavy replacement chars (mojibake), otherwise strip
        # the residual replacement chars to preserve readable content.
        if _replacement_char_count(item) >= 2:
            removed.append(item.strip())
            continue
        # Strip report-style section labels from line starts
        item = _SECTION_LABELS.sub("", item.strip()).strip()
        item = item.replace("\ufffd", "").strip()
        if not item:
            continue
        kept_raw.append(item)
    while kept_raw and kept_raw[0] == "":
        kept_raw.pop(0)
    while kept_raw and kept_raw[-1] == "":
        kept_raw.pop()
    kept: list[str] = []
    for ln in kept_raw:
        if ln == "":
            if kept and kept[-1] != "":
                kept.append("")
            continue
        kept.append(ln)
    if not kept:
        if str(lang).lower() == "en":
            kept = ["I'm looking into this for you now."]
        else:
            kept = ["我正在帮你处理中。"]
    return "\n".join(kept), removed


def rewrite_mechanical_phrases(text: str, lang: str) -> str:
    raw = str(text or "")
    if not raw:
        return ""
    # No longer rewrite customer-service phrases into project jargon.
    # Only strip banned phrases that leak internal/engineering language.
    replacements: dict[str, str] = {}
    out = raw
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    # Final hard strip in case variants still survive after replacement.
    for phrase in MECHANICAL_BAN_PHRASES:
        out = out.replace(phrase, "")
    # Normalize accidental double punctuation/spacing after removals.
    rows = [re.sub(r"\s+", " ", ln).strip() for ln in out.splitlines()]
    cleaned_rows: list[str] = []
    for ln in rows:
        if not ln:
            if cleaned_rows and cleaned_rows[-1] != "":
                cleaned_rows.append("")
            continue
        ln = re.sub(r"([。！？!?])\1+", r"\1", ln)
        cleaned_rows.append(ln)
    while cleaned_rows and cleaned_rows[0] == "":
        cleaned_rows.pop(0)
    while cleaned_rows and cleaned_rows[-1] == "":
        cleaned_rows.pop()
    return "\n".join(cleaned_rows)


def build_user_reply_payload(
    *,
    reply_text: str,
    next_question: str,
    lang: str,
    ops_status: dict[str, Any] | None = None,
    style_hint: dict[str, str] | None = None,
    default_assumption: str = "",
) -> dict[str, Any]:
    cleaned, removed = sanitize_customer_reply_text(reply_text, lang)
    if frontend_sanitize_internal_text is not None:
        try:
            sanitized = frontend_sanitize_internal_text(cleaned)
            safe_cleaned = str(getattr(sanitized, "text", "") or "").strip()
            if safe_cleaned:
                cleaned = safe_cleaned
            redactions = int(getattr(sanitized, "redactions", 0) or 0)
            if redactions > 0:
                removed.append(f"[frontend_redactions]={redactions}")
        except Exception:
            pass
    cleaned = rewrite_mechanical_phrases(cleaned, lang)
    src_text = str((ops_status or {}).get("source_text", "")).strip()
    if is_project_creation_request(src_text) and _is_generic_progress_reply(cleaned, lang):
        project_reply, project_q = _project_kickoff_reply(lang)
        cleaned = project_reply
        if not str(next_question or "").strip():
            next_question = project_q
    keep_structured_questions = any(
        marker in cleaned
        for marker in (
            "不过有两个点会直接影响方案路线",
            "Two points can change the technical route",
        )
    )
    if _contains_list_block(cleaned) and not keep_structured_questions:
        cleaned = rewrite_to_paragraphs(cleaned, lang)

    # Minimal-template mode: keep the LLM text as-is after safety sanitization.
    # Only keep an explicit follow-up question when it is clearly provided.
    extracted_question = ""
    user_q_raw = str(next_question or "").strip()
    if user_q_raw and frontend_sanitize_internal_text is not None:
        try:
            user_q_raw = str(getattr(frontend_sanitize_internal_text(user_q_raw), "text", "") or "").strip()
        except Exception:
            pass
    if not user_q_raw and (cleaned.count("?") + cleaned.count("？")) > 0:
        extracted_question = _extract_single_question(cleaned)
    desired_question_raw = user_q_raw or extracted_question
    default_q = _normalize_next_question(_default_next_question(lang), lang)
    question = ""
    if desired_question_raw:
        normalized_q = _normalize_next_question(desired_question_raw, lang)
        # If normalization had to coerce the text into generic default wording
        # (e.g. mojibake/engineering tokens), do not force that question out.
        if normalized_q and not (
            normalized_q == default_q and re.sub(r"\s+", " ", desired_question_raw).strip().lower() != default_q.lower()
        ):
            question = normalized_q
    question_needed = bool(question)

    style = dict(style_hint or {})
    closer = str(style.get("closer", "")).strip()

    # Pass through the cleaned LLM text as-is (natural conversational style).
    # Only append one explicit question when needed.
    final_text = cleaned
    if question_needed and question:
        q_line = question
        # Only append if the question isn't already at the end of the text
        if q_line.lower().rstrip("?？") not in final_text.lower():
            final_text = final_text.rstrip() + "\n\n" + (closer + q_line).strip()
    final_text = rewrite_mechanical_phrases(final_text, lang)

    if not str(final_text or "").strip():
        final_text = "I'm on it and will update you shortly." if str(lang).lower() == "en" else "我在处理了，有结果马上告诉你。"

    ops = dict(ops_status or {})
    ops["raw_reply_text"] = str(reply_text or "")
    if removed:
        ops["removed_internal_lines"] = removed
    if style:
        ops["style_hint"] = {
            k: str(v)
            for k, v in style.items()
            if k in {"opener", "transition", "closer", "question_style", "seed", "intent", "style_seed"}
        }
    if question_needed:
        ops["followup_question"] = question
    return {
        "reply_text": final_text,
        "next_question": question if question_needed else "",
        "ops_status": ops,
    }


def _event_milestone_text(event_key: str, lang: str) -> str:
    key = str(event_key or "").strip().lower()
    if str(lang).lower() == "en":
        if key in TRACE_MILESTONES_EN:
            return TRACE_MILESTONES_EN[key]
        return "Your request is being processed."
    if key in TRACE_MILESTONES_ZH:
        return TRACE_MILESTONES_ZH[key]
    return "你的请求正在处理中。"


def build_employee_note_reply(text: str, lang: str, collab_role: str = "support_lead") -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    role = _normalize_collab_role(collab_role)
    brief = _brief_text(raw, max_chars=70) or raw[:70]
    brief_clean = brief.rstrip("。！？?!;；，,．.")
    # If the message is just a greeting with no substantive goal,
    # just greet and ask what they need help with.
    _greetings = {"你好", "嗨", "哈喽", "在吗", "早", "早安", "午安", "晚上好", "hello", "hi", "hey", "喂"}
    if raw.lower() in _greetings or raw in _greetings:
        if str(lang).lower() == "en":
            if role == "team_manager":
                return "Hi, I will work as your team manager and drive this forward with you. Share your target for this round and I'll start now."
            return "Hi there! I'm here to help. You can ask me about products, orders, or any issues you're experiencing. What do you need?"
        if role == "team_manager":
            return "你好，我会以团队经理方式和你协作推进。你把这轮目标发我，我现在就开工。"
        return "你好！我是你的客服助手，可以帮你查询订单、解答产品问题、处理售后。请问有什么可以帮到你的？"
    continuation_hint = is_explicit_continuation_request(raw)
    if str(lang).lower() == "en":
        if role == "team_manager":
            if continuation_hint:
                parts = [
                    "Got it. I will continue this as your team manager.",
                    "I'll push the current execution path and ask you only one targeted question at each key decision point.",
                    "For this round, should I prioritize speed, quality, or cost?",
                ]
                return "\n\n".join(parts)
            if _has_actionable_goal_details(raw):
                parts = [f"Got it. I will drive this as your team manager: {brief_clean}."]
                parts.append("I'll start execution now and send you the first concrete plan with clear milestones.")
                parts.append("If you have no extra constraints, I will prioritize speed first.")
                return "\n\n".join(parts)
            parts = [
                "Got it. I will take this over as your team manager.",
                "To start immediately, tell me the single top priority for this round: speed, quality, or cost.",
            ]
            return "\n\n".join(parts)
        if continuation_hint:
            parts = [
                "Got it. This looks like a continuation request.",
                "Please send the module name, current error text, or the exact goal to continue, and I will pick it up immediately.",
            ]
            parts.append("Should I stay on the existing project path, or switch to a new issue first?")
            return "\n\n".join(parts)
        parts = [f"Got it. I can start on: {brief_clean}."]
        parts.append("To route this correctly, tell me which lane you want first: existing project path, new requirement, or error troubleshooting.")
        parts.append("You can also paste the exact goal or error directly, and I will proceed right away.")
        return "\n\n".join(parts)
    if role == "team_manager":
        if continuation_hint:
            parts = [
                "收到，我会以团队经理方式继续接管这个项目。",
                "我会先推进当前执行主线，并在关键决策点只向你提一个关键问题。",
                "这轮你希望我优先保速度、保质量，还是先控成本？",
            ]
            return "\n\n".join(parts)
        if _has_actionable_goal_details(raw):
            parts = [f"收到，我会以团队经理方式推进：{brief_clean}。"]
            parts.append("我现在就启动执行，并先给你首轮可落地方案和里程碑。")
            parts.append("如果没有额外限制，我先按速度优先推进。")
            return "\n\n".join(parts)
        parts = [
            "收到，我先接管这件事并按团队经理方式推进。",
            "为了马上开工，你先告诉我这一轮唯一最高优先级（速度 / 质量 / 成本）。",
        ]
        return "\n\n".join(parts)
    if continuation_hint:
        parts = [
            "收到，这是继续处理的请求。",
            "你直接发模块名、当前报错，或本轮要先推进的目标，我会按这条线马上接着处理。",
            "你希望沿用之前的项目路径，还是先切到新问题？",
        ]
        return "\n\n".join(parts)
    if _has_actionable_goal_details(raw):
        parts = [f"收到，目标很清晰：{brief_clean}。"]
        parts.append("我会直接进入处理，并先给你一版可执行的首轮方案。")
        parts.append("如果你有硬优先级（速度 / 质量 / 成本），直接告诉我，我会先按这个方向推进。")
        return "\n\n".join(parts)
    parts = [f"收到，我可以先处理：{brief_clean}。"]
    parts.append("为了直接进入处理入口，你现在更需要哪类：现有项目延续 / 新需求 / 报错排查？")
    parts.append("你也可以直接贴目标或报错，我会马上按步骤推进。")
    return "\n\n".join(parts)


def last_trace_event(trace_text: str) -> str:
    for ln in reversed((trace_text or "").splitlines()):
        s = ln.strip()
        if s.startswith("- "):
            return s[2:].strip()
    return ""


def _role_label(role: str, lang: str) -> str:
    key = str(role or "").strip().lower()
    if str(lang).lower() == "en":
        mapping = {
            "chair": "planner",
            "contract_guardian": "contract review",
            "cost_controller": "cost review",
            "librarian": "research",
            "patchmaker": "patch",
            "fixer": "fixer",
            "local orchestrator": "orchestrator",
            "local verifier": "verifier",
        }
        return mapping.get(key, key or "module")
    mapping = {
        "chair": "规划环节",
        "contract_guardian": "规范审查",
        "cost_controller": "成本审查",
        "librarian": "资料整理",
        "patchmaker": "补丁生成",
        "fixer": "修复环节",
        "local orchestrator": "编排器",
        "local verifier": "验收器",
    }
    return mapping.get(key, key or "模块")


def _brief_text(raw: str, max_chars: int = 140) -> str:
    lines = []
    for ln in (raw or "").splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if re.match(r"^[A-Za-z][A-Za-z0-9_-]*\s*:", s):
            continue
        # Skip JSON key-value lines like `"key": ...` (quoted keys) to prevent
        # internal prompt metadata (style_hint, format_hint, seed, etc.) leaking
        # into user-facing messages.
        if re.match(r'^"[A-Za-z0-9_]+"\s*:', s):
            continue
        # Skip bare JSON structural tokens
        if s in ("{", "}", "[", "]") or s.startswith("{}") or s.startswith("[]"):
            continue
        if s.startswith("```"):
            continue
        lines.append(s)
    # If all lines were filtered (e.g. pure JSON metadata), return empty string
    # rather than falling back to short_tail which would re-expose the raw content.
    text = " ".join(lines) if lines else ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _is_whiteboard_or_librarian_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    if not raw:
        return False
    keywords = ("白板", "librarian", "whiteboard", "资料检索", "查资料", "找信息", "knowledge")
    return any(k in raw for k in keywords) or any(k in low for k in keywords)


def _whiteboard_area_label(*, path: str, snippet: str, lang: str) -> str:
    low = (str(path or "") + " " + str(snippet or "")).lower()
    if "telegram_cs_bot" in low or "support" in low:
        return "customer support flow" if str(lang).lower() == "en" else "客服流程"
    if "response_composer" in low or "conversation_mode_router" in low or "frontend" in low:
        return "intake and reply flow" if str(lang).lower() == "en" else "intake与回复流程"
    if "ctcp_front_bridge" in low or "ctcp_front_api" in low or "bridge" in low:
        return "execution bridge flow" if str(lang).lower() == "en" else "执行桥接流程"
    if "librarian" in low or "context_pack" in low:
        return "librarian retrieval flow" if str(lang).lower() == "en" else "librarian检索流程"
    return "related implementation" if str(lang).lower() == "en" else "相关实现"


def _looks_like_support_project_linking_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    has_support = ("客服" in raw) or any(k in low for k in ("support", "customer service"))
    has_project = ("项目" in raw) or any(k in low for k in ("project", "design", "intake"))
    has_link = any(k in raw for k in ("连在一起", "打通", "串起来", "协同")) or any(
        k in low for k in ("connect", "link", "integrate", "bridge")
    )
    return (has_support and has_project) or (has_link and (has_support or has_project))


def _humanize_trace_event_line(line: str, lang: str) -> str:
    s = str(line or "").strip()
    if not s.startswith("- "):
        return ""
    body = s[2:].strip()
    m = re.search(r"\|\s*([^:]+):\s*([A-Za-z0-9_]+)\s*\(([^)]+)\)", body)
    if m:
        evt = m.group(2).strip().lower()
        return f"- {_event_milestone_text(evt, lang)}"
    if str(lang).lower() == "en":
        if "run already PASS" in body:
            return "- Workflow verification has passed."
        if "blocked:" in body:
            return "- Waiting for one required input before continuing."
    else:
        if "run already PASS" in body:
            return "- 你的请求已经处理完成。"
        if "blocked:" in body:
            return "- 需要你补充一些信息才能继续。"
    return ""


def _humanize_trace_delta(delta: str, lang: str) -> str:
    lines = []
    for ln in (delta or "").splitlines():
        text = _humanize_trace_event_line(ln, lang)
        if text:
            lines.append(text)
    dedup: list[str] = []
    seen: set[str] = set()
    for ln in lines:
        if ln in seen:
            continue
        seen.add(ln)
        dedup.append(ln)
    if not dedup:
        if str(lang).lower() == "en":
            return _compose_three_part_reply(
                lang=lang,
                conclusion="Progress is continuing normally.",
                plans=["I'm continuing to work on your request."],
                next_question=_default_next_question(lang),
            )
        return _compose_three_part_reply(
            lang=lang,
            conclusion="一切进展正常。",
            plans=["我正在继续帮你处理。"],
            next_question=_default_next_question(lang),
        )
    picked = dedup[-4:]
    compact = [x[2:].strip().replace("`", "") if x.startswith("- ") else x.replace("`", "") for x in picked]
    if str(lang).lower() == "en":
        done = [x for x in compact if any(k in x.lower() for k in ("completed", "passed", "workflow completed"))]
        issues = [x for x in compact if any(k in x.lower() for k in ("failed", "blocked", "waiting"))]
        doing = [x for x in compact if any(k in x.lower() for k in ("started", "in progress"))]
        conclusion = done[-1] if done else "Things are moving along."
        plan_rows = [doing[-1] if doing else "I'm working on the next step now."]
        if issues:
            plan_rows.append(f"There's something I need to sort out: {issues[-1]}")
        return _compose_three_part_reply(
            lang=lang,
            conclusion=conclusion,
            plans=plan_rows,
            next_question=_default_next_question(lang),
        )
    done = [x for x in compact if any(k in x for k in ("已完成", "验收通过", "流程已完成"))]
    issues = [x for x in compact if any(k in x for k in ("失败", "拦截", "等待"))]
    doing = [x for x in compact if any(k in x for k in ("已开始", "进行中"))]
    conclusion = done[-1] if done else "处理进展正常。"
    plan_rows = [doing[-1] if doing else "我正在处理下一步。"]
    if issues:
        plan_rows.append(f"有一个地方需要确认一下：{issues[-1]}")
    return _compose_three_part_reply(
        lang=lang,
        conclusion=conclusion,
        plans=plan_rows,
        next_question=_default_next_question(lang),
    )


def describe_artifact_for_customer(path: str, lang: str) -> str:
    p = str(path or "").strip().replace("\\", "/")
    low = p.lower()
    if str(lang).lower() == "en":
        if low.endswith("artifacts/plan_draft.md"):
            return "project plan draft"
        if low.endswith("reviews/review_contract.md"):
            return "contract review"
        if low.endswith("reviews/review_cost.md"):
            return "cost review"
        if low.endswith("artifacts/plan.md"):
            return "signed execution plan"
        if low.endswith("artifacts/diff.patch"):
            return "code change patch"
        if low.endswith("artifacts/verify_report.json"):
            return "verification report"
        return "pending task"
    if low.endswith("artifacts/plan_draft.md"):
        return "项目方案草稿"
    if low.endswith("reviews/review_contract.md"):
        return "规范审查结果"
    if low.endswith("reviews/review_cost.md"):
        return "成本审查结果"
    if low.endswith("artifacts/plan.md"):
        return "签署后的执行计划"
    if low.endswith("artifacts/diff.patch"):
        return "代码改动包"
    if low.endswith("artifacts/verify_report.json"):
        return "验收报告"
    return "待处理的事项"


def describe_reason_for_customer(reason: str, path: str, lang: str) -> str:
    r = str(reason or "").strip()
    if not r:
        if str(lang).lower() == "en":
            return "Waiting for required input."
        return "等待必要输入。"
    low = r.lower()
    missing_questions = _rewrite_missing_questions_for_customer(
        raw_text=r,
        task_summary=describe_artifact_for_customer(path, lang),
        lang=lang,
        max_questions=1,
    )
    if missing_questions:
        return missing_questions[0]
    if any(
        token in low
        for token in (
            "command failed",
            "plan agent",
            "patch agent",
            "rc=",
            "stderr",
            "stdout",
            "traceback",
            "stack trace",
            "context + constraints + externals",
            "use context + constraints",
        )
    ):
        if str(lang).lower() == "en":
            return "I hit a temporary internal processing issue while preparing the first plan."
        return "我这边在整理首轮方案时遇到一次内部处理异常。"
    p = describe_artifact_for_customer(path, lang)
    if "plan_draft" in low:
        if str(lang).lower() == "en":
            return f"Waiting for {p} to be prepared."
        return f"等待{p}产出。"
    if "review_contract" in low:
        if str(lang).lower() == "en":
            return f"Waiting for {p}."
        return f"等待{p}。"
    if "review_cost" in low:
        if str(lang).lower() == "en":
            return f"Waiting for {p}."
        return f"等待{p}。"
    safe_reason = _sanitize_internal_for_customer(r, lang)
    if safe_reason:
        return safe_reason
    if str(lang).lower() == "en":
        return "Waiting for required input."
    return "等待必要输入。"


def parse_orchestrate_output(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for ln in (text or "").splitlines():
        s = ln.strip()
        if not s.startswith("[ctcp_orchestrate]"):
            continue
        body = s[len("[ctcp_orchestrate]") :].strip()
        if not body:
            continue
        m_eq = re.match(r"^([A-Za-z0-9_\- ]+?)=(.+)$", body)
        if m_eq:
            out[m_eq.group(1).strip().lower()] = m_eq.group(2).strip()
            continue
        m_col = re.match(r"^([A-Za-z0-9_\- ]+?)\s*:\s*(.+)$", body)
        if m_col:
            out[m_col.group(1).strip().lower()] = m_col.group(2).strip()
    return out


def _normalize_provider_name(raw: str, default: str = "manual_outbox") -> str:
    text = str(raw or "").strip().lower()
    if text not in SUPPORT_KNOWN_PROVIDERS:
        return default
    return text


def _read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        return doc if isinstance(doc, dict) else None
    except Exception:
        pass
    text = path.read_text(encoding="utf-8", errors="replace")
    doc2 = parse_api_json(text)
    return doc2 if isinstance(doc2, dict) else None


def _load_prompt_text(path: Path, fallback: str) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return fallback


def _summarize_history_for_session(run_dir: Path, lang: str, max_rows: int = 6) -> str:
    path = run_dir / SUPPORT_INBOX_REL
    if not path.exists():
        return ""
    rows: list[dict[str, str]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = raw.strip()
        if not text:
            continue
        try:
            doc = json.loads(text)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        rows.append(
            {
                "role": str(doc.get("role", "")).strip().lower(),
                "text": re.sub(r"\s+", " ", str(doc.get("text", "")).strip()),
            }
        )
    rows = [r for r in rows if r.get("text")]
    if not rows:
        return ""
    picked = rows[-max(2, max_rows) :]
    user_tail = [r["text"] for r in picked if r.get("role") == "user"][-2:]
    bot_tail = [r["text"] for r in picked if r.get("role") == "assistant"][-2:]
    if str(lang).lower() == "en":
        parts: list[str] = []
        if user_tail:
            parts.append("Latest user focus: " + " | ".join(_brief_text(x, max_chars=120) for x in user_tail))
        if bot_tail:
            parts.append("Recent support progress: " + " | ".join(_brief_text(x, max_chars=120) for x in bot_tail))
        return " ".join(parts)[:580]
    parts = []
    if user_tail:
        parts.append("最近用户重点：" + " | ".join(_brief_text(x, max_chars=120) for x in user_tail))
    if bot_tail:
        parts.append("最近处理进展：" + " | ".join(_brief_text(x, max_chars=120) for x in bot_tail))
    return " ".join(parts)[:580]


def _load_recent_user_messages(run_dir: Path, max_rows: int = 12) -> list[str]:
    path = run_dir / SUPPORT_INBOX_REL
    if not path.exists():
        return []
    rows: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = raw.strip()
        if not text:
            continue
        try:
            doc = json.loads(text)
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        role = str(doc.get("role", "")).strip().lower()
        if role != "user":
            continue
        msg = re.sub(r"\s+", " ", str(doc.get("text", "")).strip())
        if not msg:
            continue
        rows.append(msg)
    if len(rows) <= max_rows:
        return rows
    return rows[-max_rows:]


@dataclass(frozen=True)
class Config:
    token: str
    allowlist: set[int] | None
    repo_root: Path
    state_db: Path
    poll_seconds: int
    tick_seconds: int
    auto_advance: bool
    api_enabled: bool
    api_model: str
    api_timeout_sec: int
    note_ack_path: bool
    progress_push_enabled: bool

    @staticmethod
    def load() -> "Config":
        token = os.environ.get("CTCP_TG_BOT_TOKEN", "").strip()
        if not token:
            raise SystemExit("missing env CTCP_TG_BOT_TOKEN")
        repo_root = (
            Path(os.environ.get("CTCP_REPO_ROOT", "")).expanduser().resolve()
            if os.environ.get("CTCP_REPO_ROOT", "").strip()
            else ROOT
        )
        state_db = (
            Path(os.environ.get("CTCP_TG_STATE_DB", "")).expanduser().resolve()
            if os.environ.get("CTCP_TG_STATE_DB", "").strip()
            else Path.home() / ".ctcp" / "telegram_bot" / "state.sqlite3"
        )
        state_db.parent.mkdir(parents=True, exist_ok=True)
        return Config(
            token=token,
            allowlist=parse_allowlist(os.environ.get("CTCP_TG_ALLOWLIST", "")),
            repo_root=repo_root,
            state_db=state_db,
            poll_seconds=parse_int(os.environ.get("CTCP_TG_POLL_SECONDS", "2"), 2),
            tick_seconds=parse_int(os.environ.get("CTCP_TG_TICK_SECONDS", "2"), 2),
            # Full-auto mode is mandatory: the bot keeps advancing whenever no user decision is pending.
            auto_advance=True,
            api_enabled=parse_bool(os.environ.get("CTCP_TG_API_ENABLED", "1"), True),
            api_model=(
                os.environ.get("CTCP_TG_API_MODEL", "")
                or os.environ.get("SDDAI_OPENAI_AGENT_MODEL", "")
                or os.environ.get("SDDAI_OPENAI_MODEL", "")
                or "gpt-4.1-mini"
            ).strip(),
            api_timeout_sec=parse_int(os.environ.get("CTCP_TG_API_TIMEOUT_SEC", "60"), 60),
            note_ack_path=parse_bool(os.environ.get("CTCP_TG_NOTE_ACK_PATH", "0"), False),
            progress_push_enabled=parse_bool(os.environ.get("CTCP_TG_PROGRESS_PUSH", "0"), False),
        )


class StateDB:
    def __init__(self, path: Path) -> None:
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        cur = self.conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS sessions(chat_id INTEGER PRIMARY KEY,run_dir TEXT NOT NULL DEFAULT '',lang TEXT NOT NULL DEFAULT 'zh',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS cursors(chat_id INTEGER PRIMARY KEY,seen_outbox TEXT NOT NULL DEFAULT '[]',seen_questions TEXT NOT NULL DEFAULT '[]',trace_offset INTEGER NOT NULL DEFAULT 0,last_bundle_mtime REAL NOT NULL DEFAULT 0,cooldown_ts REAL NOT NULL DEFAULT 0,updated_at TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS outbox_map(chat_id INTEGER NOT NULL,prompt_msg_id INTEGER NOT NULL,run_dir TEXT NOT NULL,target_path TEXT NOT NULL,prompt_path TEXT NOT NULL,kind TEXT NOT NULL,qid TEXT NOT NULL DEFAULT '',options_json TEXT NOT NULL DEFAULT '[]',created_at TEXT NOT NULL,PRIMARY KEY(chat_id,prompt_msg_id))")
        cur.execute("CREATE TABLE IF NOT EXISTS kv_state(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS agent_pending(run_dir TEXT NOT NULL,prompt_path TEXT NOT NULL,req_id TEXT NOT NULL,agent_name TEXT NOT NULL,target_path TEXT NOT NULL,chat_id INTEGER NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(run_dir,prompt_path))")
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def _ensure_chat(self, chat_id: int) -> None:
        now = now_iso()
        self.conn.execute("INSERT INTO sessions(chat_id,run_dir,lang,created_at,updated_at) VALUES(?, '', ?, ?, ?) ON CONFLICT(chat_id) DO NOTHING", (chat_id, DEFAULT_LANG, now, now))
        self.conn.execute("INSERT INTO cursors(chat_id,seen_outbox,seen_questions,trace_offset,last_bundle_mtime,cooldown_ts,updated_at) VALUES(?, '[]', '[]', 0, 0, 0, ?) ON CONFLICT(chat_id) DO NOTHING", (chat_id, now))
        self.conn.commit()

    def _update(self, table: str, key_col: str, key_val: int, fields: dict[str, Any]) -> None:
        if not fields:
            return
        ks = sorted(fields.keys())
        assigns = ", ".join(f"{k}=?" for k in ks)
        vals = [fields[k] for k in ks] + [key_val]
        self.conn.execute(f"UPDATE {table} SET {assigns} WHERE {key_col}=?", vals)
        self.conn.commit()

    def get_session(self, chat_id: int) -> dict[str, Any]:
        self._ensure_chat(chat_id)
        row = self.conn.execute("SELECT s.chat_id,s.run_dir,s.lang,s.created_at,s.updated_at,c.seen_outbox,c.seen_questions,c.trace_offset,c.last_bundle_mtime,c.cooldown_ts FROM sessions s JOIN cursors c ON c.chat_id=s.chat_id WHERE s.chat_id=?", (chat_id,)).fetchone()
        return dict(row) if row else {}

    def list_bound_sessions(self) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT s.chat_id,s.run_dir,s.lang,s.created_at,s.updated_at,c.seen_outbox,c.seen_questions,c.trace_offset,c.last_bundle_mtime,c.cooldown_ts FROM sessions s JOIN cursors c ON c.chat_id=s.chat_id WHERE s.run_dir <> ''").fetchall()
        return [dict(r) for r in rows]

    def bind_run(self, chat_id: int, run_dir: Path) -> None:
        now = now_iso()
        self._ensure_chat(chat_id)
        self._update("sessions", "chat_id", chat_id, {"run_dir": str(run_dir.resolve()), "updated_at": now})
        self._update("cursors", "chat_id", chat_id, {"seen_outbox": "[]", "seen_questions": "[]", "trace_offset": 0, "last_bundle_mtime": 0.0, "cooldown_ts": 0.0, "updated_at": now})

    def clear_run(self, chat_id: int) -> None:
        self._ensure_chat(chat_id)
        now = now_iso()
        self._update("sessions", "chat_id", chat_id, {"run_dir": "", "updated_at": now})
        self._update("cursors", "chat_id", chat_id, {"seen_outbox": "[]", "seen_questions": "[]", "trace_offset": 0, "last_bundle_mtime": 0.0, "cooldown_ts": 0.0, "updated_at": now})

    def clear_maps_for_chat(self, chat_id: int) -> None:
        self._ensure_chat(chat_id)
        self.conn.execute("DELETE FROM outbox_map WHERE chat_id=?", (chat_id,))
        self.conn.commit()

    def clear_pending_for_run(self, run_dir: str) -> None:
        self.conn.execute("DELETE FROM agent_pending WHERE run_dir=?", (str(run_dir),))
        self.conn.commit()

    def set_lang(self, chat_id: int, lang: str) -> None:
        self._ensure_chat(chat_id)
        self._update("sessions", "chat_id", chat_id, {"lang": lang, "updated_at": now_iso()})

    def update_cursors(self, chat_id: int, **fields: Any) -> None:
        self._ensure_chat(chat_id)
        fields["updated_at"] = now_iso()
        self._update("cursors", "chat_id", chat_id, fields)

    def get_offset(self) -> int:
        row = self.conn.execute("SELECT value FROM kv_state WHERE key='tg_update_offset'").fetchone()
        if not row:
            return 0
        try:
            return int(str(row["value"]).strip())
        except Exception:
            return 0

    def set_offset(self, offset: int) -> None:
        self.conn.execute("INSERT INTO kv_state(key,value) VALUES('tg_update_offset', ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(int(offset)),))
        self.conn.commit()

    def save_map(self, *, chat_id: int, msg_id: int, run_dir: str, target_path: str, prompt_path: str, kind: str, qid: str, options: list[str]) -> None:
        self.conn.execute("INSERT OR REPLACE INTO outbox_map(chat_id,prompt_msg_id,run_dir,target_path,prompt_path,kind,qid,options_json,created_at) VALUES(?,?,?,?,?,?,?,?,?)", (chat_id, msg_id, run_dir, target_path, prompt_path, kind, qid, json.dumps(options, ensure_ascii=False), now_iso()))
        self.conn.commit()

    def get_map(self, chat_id: int, msg_id: int) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM outbox_map WHERE chat_id=? AND prompt_msg_id=?", (chat_id, msg_id)).fetchone()
        return dict(row) if row else None

    def del_map(self, chat_id: int, msg_id: int) -> None:
        self.conn.execute("DELETE FROM outbox_map WHERE chat_id=? AND prompt_msg_id=?", (chat_id, msg_id))
        self.conn.commit()

    def upsert_pending(self, *, run_dir: str, prompt_path: str, req_id: str, agent_name: str, target_path: str, chat_id: int, status: str) -> None:
        now = now_iso()
        self.conn.execute("INSERT INTO agent_pending(run_dir,prompt_path,req_id,agent_name,target_path,chat_id,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(run_dir,prompt_path) DO UPDATE SET req_id=excluded.req_id,agent_name=excluded.agent_name,target_path=excluded.target_path,chat_id=excluded.chat_id,status=excluded.status,updated_at=excluded.updated_at", (run_dir, prompt_path, req_id, agent_name, target_path, chat_id, status, now, now))
        self.conn.commit()

    def get_pending(self, run_dir: str, prompt_path: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM agent_pending WHERE run_dir=? AND prompt_path=?", (run_dir, prompt_path)).fetchone()
        return dict(row) if row else None

    def list_pending(self, run_dir: str) -> list[dict[str, Any]]:
        rows = self.conn.execute("SELECT * FROM agent_pending WHERE run_dir=? AND status='pending' ORDER BY created_at ASC", (run_dir,)).fetchall()
        return [dict(r) for r in rows]

    def del_pending(self, run_dir: str, prompt_path: str) -> None:
        self.conn.execute("DELETE FROM agent_pending WHERE run_dir=? AND prompt_path=?", (run_dir, prompt_path))
        self.conn.commit()


class TgAPI:
    def __init__(self, token: str) -> None:
        self.token = token
        self.base = f"https://api.telegram.org/bot{token}/"
        self._json_headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Connection": "close",
            "User-Agent": "ctcp-telegram-bot/2.7",
        }

    def _post_with_retry(
        self,
        *,
        method: str,
        payload_bytes: bytes,
        headers: dict[str, str],
        timeout_sec: int,
        max_retries: int,
    ) -> dict[str, Any]:
        last_exc: Exception | None = None
        retries = max(1, int(max_retries))
        for attempt in range(1, retries + 1):
            req = urllib.request.Request(
                self.base + method,
                data=payload_bytes,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                    return json.loads(resp.read().decode("utf-8", errors="replace"))
            except Exception as exc:
                last_exc = exc
                if (attempt >= retries) or (not _is_retryable_telegram_error(exc)):
                    break
                time.sleep(min(1.5 * attempt, 4.0))
        if last_exc is not None:
            raise last_exc
        raise RuntimeError(f"telegram {method} failed without explicit error")

    def _json(self, method: str, payload: dict[str, Any]) -> Any:
        timeout_sec = 70 if method == "getUpdates" else 60
        max_retries = 4 if method == "getUpdates" else 2
        doc = self._post_with_retry(
            method=method,
            payload_bytes=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers=self._json_headers,
            timeout_sec=timeout_sec,
            max_retries=max_retries,
        )
        if not doc.get("ok", False):
            raise RuntimeError(f"telegram {method} failed: {doc.get('description', 'unknown')}")
        return doc.get("result")

    def updates(self, offset: int, timeout: int) -> list[dict[str, Any]]:
        result = self._json("getUpdates", {"offset": offset, "timeout": timeout, "allowed_updates": ["message", "callback_query"]})
        return result if isinstance(result, list) else []

    def send(self, *, chat_id: int, text: str, reply_to: int | None = None, markup: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": (text or "")[:MAX_MESSAGE_CHARS], "disable_web_page_preview": True}
        if reply_to is not None:
            payload["reply_to_message_id"] = int(reply_to)
        if markup is not None:
            payload["reply_markup"] = markup
        return self._json("sendMessage", payload)

    def edit(self, *, chat_id: int, msg_id: int, text: str) -> None:
        self._json("editMessageText", {"chat_id": chat_id, "message_id": msg_id, "text": (text or "")[:MAX_MESSAGE_CHARS]})

    def answer_cb(self, cb_id: str, text: str = "") -> None:
        payload = {"callback_query_id": cb_id}
        if text:
            payload["text"] = text[:180]
        self._json("answerCallbackQuery", payload)

    def _multipart(self, method: str, fields: dict[str, str], file_field: str, file_path: Path) -> Any:
        boundary = "----ctcpbot" + uuid.uuid4().hex
        chunks: list[bytes] = []
        for k, v in fields.items():
            chunks += [f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode(), str(v).encode("utf-8"), b"\r\n"]
        chunks += [f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode(), b"Content-Type: application/octet-stream\r\n\r\n", file_path.read_bytes(), b"\r\n", f"--{boundary}--\r\n".encode()]
        doc = self._post_with_retry(
            method=method,
            payload_bytes=b"".join(chunks),
            headers={
                "Content-Type": f"multipart/form-data; boundary={boundary}",
                "Connection": "close",
                "User-Agent": "ctcp-telegram-bot/2.7",
            },
            timeout_sec=120,
            max_retries=2,
        )
        if not doc.get("ok", False):
            raise RuntimeError(f"telegram {method} failed: {doc.get('description', 'unknown')}")
        return doc.get("result")

    def send_doc(self, *, chat_id: int, path: Path, caption: str = "", reply_to: int | None = None) -> dict[str, Any]:
        fields = {"chat_id": str(chat_id)}
        if caption:
            fields["caption"] = caption[:900]
        if reply_to is not None:
            fields["reply_to_message_id"] = str(int(reply_to))
        return self._multipart("sendDocument", fields, "document", path)

    def download(self, file_id: str) -> bytes:
        info = self._json("getFile", {"file_id": file_id})
        fpath = str(info.get("file_path", "")).strip()
        if not fpath:
            raise RuntimeError("getFile missing file_path")
        url = f"https://api.telegram.org/file/bot{self.token}/{urllib.parse.quote(fpath, safe='/')}"
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=120) as resp:
            return resp.read()


@dataclass
class PromptItem:
    rel_prompt_path: str
    target_path: str
    prompt_type: str
    recipient: str
    qid: str
    prompt_text: str
    options: list[str]
    raw_text: str


@dataclass
class ApiDecision:
    intent: str
    reply: str
    note: str
    summary: str
    steps: int
    follow_up: str


def _is_internal_support_prompt_item(item: PromptItem) -> bool:
    if _is_internal_support_target_path(item.target_path):
        return True
    rel_prompt = _normalize_rel_for_match(item.rel_prompt_path)
    rel_name = Path(rel_prompt).name
    if rel_name.startswith("agent_prompt_"):
        # Internal orchestration prompt; never customer-facing.
        return True
    if any(token in rel_prompt for token in ("support_lead_router", "support_lead_reply", "support_lead_handoff")):
        return True
    text = f"{item.prompt_text}\n{item.raw_text}".lower()
    if "# api agent prompt" in text and "target-path:" in text and "hard rules:" in text:
        return True
    if "target-path: artifacts/support_router.provider.json" in text:
        return True
    if "target-path: artifacts/support_reply.provider.json" in text:
        return True
    if "role: support_lead_router" in text:
        return True
    if "role: support_lead_reply" in text:
        return True
    if "role: support_lead_handoff" in text:
        return True
    return False


def parse_outbox_prompt(run_dir: Path, prompt_path: Path) -> PromptItem | None:
    text = prompt_path.read_text(encoding="utf-8", errors="replace")
    target = parse_key_line(text, "Target-Path")
    if not target:
        return None
    ptype = parse_key_line(text, "Type").strip().lower()
    recipient = parse_key_line(text, "Recipient").strip()
    qid = parse_key_line(text, "QID").strip()
    prompt = parse_key_line(text, "Prompt").strip()
    options_raw = parse_key_line(text, "Options")
    options = [x.strip() for x in options_raw.split("|") if x.strip()] if options_raw else []
    if not prompt:
        prompt = short_tail(text, max_lines=10, max_chars=1200)
    rel = prompt_path.relative_to(run_dir).as_posix()
    return PromptItem(rel_prompt_path=rel, target_path=target, prompt_type=ptype, recipient=recipient, qid=qid, prompt_text=prompt, options=options, raw_text=text)


def prompt_pending(run_dir: Path, item: PromptItem, prompt_abs: Path) -> bool:
    try:
        target = ensure_within_run_dir(run_dir, item.target_path)
    except Exception:
        return False
    if not target.exists():
        return True
    return target.stat().st_mtime < prompt_abs.stat().st_mtime


def i18n(lang: str, key: str) -> str:
    zh = {
        "help": "CTCP Telegram CS Bot\n未绑定时直接发一句目标；绑定后直接聊天补充需求。\n高级命令：/status /advance [n] /outbox /get <path> /bundle /reset",
        "need_run": "当前未绑定 run。先直接发一句目标。",
        "saved_note": "已记录到 USER_NOTES",
        "write_ok": "已写入",
        "write_fail": "写入失败",
        "unsafe": "路径不安全，已拒绝。",
        "missing": "文件不存在",
    }
    en = {
        "help": "CTCP Telegram CS Bot\nSend one goal when unbound; keep chatting to add hints when bound.\nAdvanced: /status /advance [n] /outbox /get <path> /bundle /reset",
        "need_run": "No bound run. Send one goal first.",
        "saved_note": "Saved to USER_NOTES",
        "write_ok": "Wrote",
        "write_fail": "Write failed",
        "unsafe": "Unsafe path denied.",
        "missing": "File not found",
    }
    return (zh if str(lang).lower() == "zh" else en).get(key, key)


class Bot:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db = StateDB(cfg.state_db)
        self.tg = TgAPI(cfg.token)

    def close(self) -> None:
        self.db.close()

    def allowed(self, chat_id: int) -> bool:
        return self.cfg.allowlist is None or chat_id in self.cfg.allowlist

    def _bridge_ready(self) -> bool:
        return all(
            callable(fn)
            for fn in (
                bridge_ctcp_new_run,
                bridge_ctcp_get_status,
                bridge_ctcp_advance,
                bridge_ctcp_get_last_report,
                bridge_ctcp_list_decisions_needed,
                bridge_ctcp_submit_decision,
                bridge_ctcp_upload_artifact,
            )
        )

    def _bridge_run_id(self, run_dir: Path | str) -> str:
        return Path(str(run_dir)).resolve().name

    def _status_to_orchestrate_lines(self, status_doc: dict[str, Any]) -> str:
        run_status = str(status_doc.get("run_status", "")).strip().lower()
        gate = status_doc.get("gate", {})
        if not isinstance(gate, dict):
            gate = {}
        gate_state = str(gate.get("state", "")).strip().lower()
        needs_decision = bool(status_doc.get("needs_user_decision", False))
        next_step = "blocked" if (gate_state in {"blocked", "waiting", "decision"} or needs_decision) else gate_state
        if not next_step:
            next_step = "running" if run_status in {"running", "in_progress", "working"} else "unknown"
        owner = str(gate.get("owner", "")).strip()
        path = str(gate.get("path", "")).strip()
        reason = str(gate.get("reason", "")).strip()
        iterations = status_doc.get("iterations", {})
        if not isinstance(iterations, dict):
            iterations = {}
        itr = str(iterations.get("current", "")).strip()
        lines = [
            f"[ctcp_orchestrate] run_status={run_status}",
            f"[ctcp_orchestrate] next={next_step}",
        ]
        if owner:
            lines.append(f"[ctcp_orchestrate] owner={owner}")
        if path:
            lines.append(f"[ctcp_orchestrate] path={path}")
        if reason:
            lines.append(f"[ctcp_orchestrate] reason={reason}")
        if itr:
            lines.append(f"[ctcp_orchestrate] iterations={itr}")
        return "\n".join(lines)

    def _resolve_run_id_from_args(self, args: list[str]) -> str:
        if "--run-id" in args:
            idx = args.index("--run-id")
            if idx + 1 < len(args):
                return str(args[idx + 1]).strip()
        if "--run-dir" in args:
            idx = args.index("--run-dir")
            if idx + 1 < len(args):
                return self._bridge_run_id(args[idx + 1])
        return ""

    def _run_orchestrate(self, args: list[str]) -> tuple[int, str, str]:
        if not self._bridge_ready():
            return 1, "", "frontend bridge unavailable"
        if not args:
            return 1, "", "missing command"
        cmd = str(args[0]).strip().lower()
        try:
            if cmd == "new-run":
                if "--goal" not in args:
                    return 1, "", "new-run requires --goal"
                gidx = args.index("--goal")
                if gidx + 1 >= len(args):
                    return 1, "", "new-run requires non-empty --goal value"
                goal = str(args[gidx + 1]).strip()
                result = bridge_ctcp_new_run(goal=goal, constraints={}, attachments=[])  # type: ignore[misc]
                status_doc = result.get("status", {}) if isinstance(result, dict) else {}
                if not isinstance(status_doc, dict):
                    status_doc = {}
                lines = [
                    f"[ctcp_orchestrate] run_id={str(result.get('run_id', '')).strip()}",
                    f"[ctcp_orchestrate] run_dir={str(result.get('run_dir', '')).strip()}",
                ]
                status_lines = self._status_to_orchestrate_lines(status_doc)
                if status_lines:
                    lines.append(status_lines)
                return 0, "\n".join(lines), ""
            if cmd == "advance":
                run_id = self._resolve_run_id_from_args(args)
                steps = 1
                if "--max-steps" in args:
                    sidx = args.index("--max-steps")
                    if sidx + 1 < len(args):
                        steps = parse_int(args[sidx + 1], 1)
                result = bridge_ctcp_advance(run_id, max_steps=max(1, steps))  # type: ignore[misc]
                status_doc = result.get("status", {}) if isinstance(result, dict) else {}
                if not isinstance(status_doc, dict):
                    status_doc = {}
                return 0, self._status_to_orchestrate_lines(status_doc), ""
            if cmd == "status":
                run_id = self._resolve_run_id_from_args(args)
                status_doc = bridge_ctcp_get_status(run_id)  # type: ignore[misc]
                if not isinstance(status_doc, dict):
                    status_doc = {}
                return 0, self._status_to_orchestrate_lines(status_doc), ""
            return 1, "", f"unsupported bridge command: {cmd}"
        except FrontBridgeError as exc:
            return 1, "", str(exc)
        except Exception as exc:
            return 1, "", f"bridge command failed: {exc}"

    def _read_last_run(self) -> str:
        ptr = self.cfg.repo_root / "meta" / "run_pointers" / "LAST_RUN.txt"
        if not ptr.exists():
            return ""
        return ptr.read_text(encoding="utf-8", errors="replace").strip()

    def _append_note(self, run_dir: Path, note: str) -> Path:
        path = run_dir / "artifacts" / "USER_NOTES.md"
        append_text(path, f"- {now_iso()} | {note.strip()}\n")
        return path

    def _append_summary(self, run_dir: Path, user_text: str, summary: str, intent: str) -> tuple[Path, Path]:
        s_path = run_dir / "artifacts" / "API_BOT_SUMMARY.md"
        append_text(
            s_path,
            "\n".join(
                [
                    f"- {now_iso()} | intent={intent}",
                    f"  - user: {user_text.strip()}",
                    f"  - summary: {summary.strip()}",
                ]
            )
            + "\n",
        )
        req_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        req_path = run_dir / "inbox" / "apibot" / "requests" / f"REQ_{req_id}.json"
        atomic_write_text(req_path, json.dumps({"type": "apibot_summary", "req_id": req_id, "run_dir": str(run_dir), "summary": summary.strip(), "source_text": user_text.strip(), "created_at": now_iso()}, ensure_ascii=False, indent=2) + "\n")
        return s_path, req_path

    def _append_ops_status(self, run_dir: Path, stage: str, payload: dict[str, Any]) -> None:
        row = {
            "ts": now_iso(),
            "stage": stage,
            "payload": payload,
        }
        append_text(run_dir / "logs" / "telegram_cs_bot.ops.jsonl", json.dumps(row, ensure_ascii=False) + "\n")

    def _emit_public_reply(self, *, chat_id: int, text: str) -> None:
        # Single public-output gate for customer-facing support replies.
        self.tg.send(chat_id=chat_id, text=str(text or ""))

    def _append_support_inbox(self, run_dir: Path, role: str, text: str, lang: str) -> None:
        row = {
            "ts": now_iso(),
            "role": str(role or "").strip().lower() or "user",
            "lang": str(lang or DEFAULT_LANG),
            "text": str(text or "").strip(),
        }
        append_text(run_dir / SUPPORT_INBOX_REL, json.dumps(row, ensure_ascii=False) + "\n")

    def _support_whiteboard_snapshot(self, run_dir: Path, lang: str, *, max_entries: int = 4) -> dict[str, Any]:
        board = load_support_whiteboard_state(run_dir)
        entries = board.get("entries", [])
        if not isinstance(entries, list):
            entries = []
        latest: list[dict[str, Any]] = []
        for item in entries[-max(1, int(max_entries)) :]:
            if not isinstance(item, dict):
                continue
            row: dict[str, Any] = {
                "ts": str(item.get("ts", "")),
                "role": str(item.get("role", "")),
                "kind": str(item.get("kind", "")),
                "text": _brief_text(str(item.get("text", "")), max_chars=180),
            }
            query = _brief_text(str(item.get("query", "")), max_chars=140)
            if query:
                row["query"] = query
            question = _brief_text(str(item.get("question", "")), max_chars=160)
            if question:
                row["question"] = question
            hit_count = int(item.get("hit_count", 0) or 0)
            if hit_count > 0:
                row["hit_count"] = hit_count
            hits = _safe_whiteboard_hits(item.get("hits"), max_items=3)
            if hits:
                row["areas"] = _dedupe_text_list(
                    [
                        _whiteboard_area_label(
                            path=str(h.get("path", "")),
                            snippet=str(h.get("snippet", "")),
                            lang=lang,
                        )
                        for h in hits
                    ],
                    limit=3,
                )
            latest.append(row)
        return {
            "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
            "entry_count": len(entries),
            "latest": latest,
        }

    def _support_librarian_whiteboard_exchange(
        self,
        *,
        run_dir: Path,
        lang: str,
        user_text: str,
        route_doc: dict[str, Any],
    ) -> dict[str, Any]:
        raw = re.sub(r"\s+", " ", str(user_text or "").strip())
        if not raw:
            return {}
        route_intent = str(route_doc.get("intent", "")).strip().lower()
        asked_whiteboard = _is_whiteboard_or_librarian_request(raw)
        actionable = _has_actionable_goal_details(raw) or is_project_creation_request(raw)
        if (not asked_whiteboard) and (not actionable):
            return {}
        if route_intent in {"cleanup_project", "smalltalk", "cancel_run"} and (not asked_whiteboard):
            return {}

        board = load_support_whiteboard_state(run_dir)
        entries = list(board.get("entries", [])) if isinstance(board.get("entries", []), list) else []
        query = _brief_text(raw, max_chars=180)
        entries.append(
            {
                "ts": now_iso(),
                "role": "user",
                "kind": "question",
                "text": query,
            }
        )

        last_librarian_query = ""
        for item in reversed(entries[:-1]):
            if not isinstance(item, dict):
                continue
            if str(item.get("role", "")).strip().lower() != "librarian":
                continue
            q = _brief_text(str(item.get("query", "")).strip(), max_chars=180)
            if q:
                last_librarian_query = q
                break
        should_lookup = bool(query) and (asked_whiteboard or (query.lower() != last_librarian_query.lower()))
        hits: list[dict[str, Any]] = []
        lookup_error = ""
        if should_lookup:
            if local_librarian is not None:
                try:
                    rows = local_librarian.search(repo_root=self.cfg.repo_root, query=query, k=4)
                    hits = _safe_whiteboard_hits(rows, max_items=4)
                except Exception as exc:
                    lookup_error = str(exc)
            else:
                lookup_error = "local_librarian unavailable"

        areas = _dedupe_text_list(
            [
                _whiteboard_area_label(path=str(h.get("path", "")), snippet=str(h.get("snippet", "")), lang=lang)
                for h in hits
            ],
            limit=3,
        )
        question = ""
        if _looks_like_support_project_linking_request(raw):
            if str(lang).lower() == "en":
                question = "To connect this quickly, should I prioritize support intake wiring first, or librarian whiteboard Q&A first?"
            else:
                question = "为了先打通主链路，你希望我先做“客服 intake 接线”，还是先做“librarian 白板问答回路”？"
        elif asked_whiteboard and (not hits):
            question = (
                "Which topic should I search first on the whiteboard?"
                if str(lang).lower() == "en"
                else "你希望我先在白板上检索哪个主题？"
            )

        note_text = ""
        if should_lookup:
            if str(lang).lower() == "en":
                if hits:
                    scope = ", ".join(areas) if areas else "related implementation"
                    note_text = f"I have synced your request to the whiteboard and librarian found {len(hits)} clues around {scope}."
                elif asked_whiteboard:
                    note_text = "I synced your request to the whiteboard and queued librarian lookup."
            else:
                if hits:
                    scope = "、".join(areas) if areas else "相关实现"
                    note_text = f"我已把你的需求同步到白板，librarian 找到了 {len(hits)} 条与{scope}有关的线索。"
                elif asked_whiteboard:
                    note_text = "我已把你的问题写到白板，并安排 librarian 继续检索相关线索。"
            entry: dict[str, Any] = {
                "ts": now_iso(),
                "role": "librarian",
                "kind": "lookup",
                "text": note_text or (
                    "librarian lookup completed" if str(lang).lower() == "en" else "librarian 检索完成"
                ),
                "query": query,
                "hits": hits,
                "hit_count": len(hits),
            }
            if question:
                entry["question"] = question
            if lookup_error:
                entry["lookup_error"] = _brief_text(lookup_error, max_chars=180)
            entries.append(entry)
            append_text(run_dir / SUPPORT_WHITEBOARD_LOG_REL, f"- {now_iso()} | user: {query}\n")
            append_text(
                run_dir / SUPPORT_WHITEBOARD_LOG_REL,
                f"- {now_iso()} | librarian: query={query} | hits={len(hits)}"
                + (f" | question={question}" if question else "")
                + "\n",
            )
        board["entries"] = entries[-60:]
        save_support_whiteboard_state(run_dir, board)

        return {
            "public_note": note_text,
            "question": question,
            "ops": {
                "query": query,
                "hit_count": len(hits),
                "areas": areas,
                "lookup_error": lookup_error,
                "whiteboard_path": SUPPORT_WHITEBOARD_REL.as_posix(),
            },
        }

    def _default_support_dispatch_config(self) -> dict[str, Any]:
        return {
            "schema_version": "ctcp-dispatch-config-v1",
            "mode": "manual_outbox",
            "role_providers": {
                "support_lead_router": "ollama_agent",
                "support_lead_reply": "ollama_agent",
                "support_lead_handoff": "api_agent",
                "support_lead": "ollama_agent",
            },
            "providers": {
                "ollama_agent": {
                    "base_url": "http://127.0.0.1:11434/v1",
                    "api_key": "ollama",
                    "model": "qwen2.5:7b-instruct",
                    "auto_start": True,
                    "start_timeout_sec": 20,
                    "start_cmd": "ollama serve",
                },
                "api_agent": {"enabled": True},
            },
            "budgets": {"max_outbox_prompts": 20},
        }

    def _load_support_dispatch_config(self, run_dir: Path) -> tuple[dict[str, Any], str]:
        path = run_dir / "artifacts" / "dispatch_config.json"
        if ctcp_dispatch is not None:
            cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)  # type: ignore[union-attr]
            if cfg is not None:
                return cfg, msg
        fallback = self._default_support_dispatch_config()
        if not path.exists():
            atomic_write_text(path, json.dumps(fallback, ensure_ascii=False, indent=2) + "\n")
            return fallback, "created default support dispatch config"
        return fallback, "fallback to support defaults"

    def _resolve_support_provider(self, config: dict[str, Any], role: str, fallback: str) -> str:
        role_map = config.get("role_providers", {})
        if not isinstance(role_map, dict):
            role_map = {}
        provider = str(role_map.get(role, "")).strip() or str(role_map.get("support_lead", "")).strip() or fallback
        normalized = _normalize_provider_name(provider, default=fallback)
        if normalized == "local_exec":
            return "manual_outbox"
        return normalized

    def _execute_support_provider(
        self,
        *,
        provider: str,
        run_dir: Path,
        request: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        guardrails: dict[str, str] = {}
        if (not self.cfg.api_enabled) and provider in {"ollama_agent", "api_agent", "codex_agent"}:
            return {"status": "exec_failed", "reason": f"{provider} disabled by CTCP_TG_API_ENABLED=0"}
        try:
            if provider == "manual_outbox" and manual_outbox is not None:
                return manual_outbox.execute(
                    repo_root=self.cfg.repo_root,
                    run_dir=run_dir,
                    request=request,
                    config=config,
                    guardrails_budgets=guardrails,
                )
            if provider == "ollama_agent" and ollama_agent is not None:
                return ollama_agent.execute(
                    repo_root=self.cfg.repo_root,
                    run_dir=run_dir,
                    request=request,
                    config=config,
                    guardrails_budgets=guardrails,
                )
            if provider == "api_agent" and api_agent is not None:
                return api_agent.execute(
                    repo_root=self.cfg.repo_root,
                    run_dir=run_dir,
                    request=request,
                    config=config,
                    guardrails_budgets=guardrails,
                )
            if provider == "codex_agent" and codex_agent is not None:
                return codex_agent.execute(
                    repo_root=self.cfg.repo_root,
                    run_dir=run_dir,
                    request=request,
                    config=config,
                    guardrails_budgets=guardrails,
                )
            if provider == "mock_agent" and mock_agent is not None:
                return mock_agent.execute(
                    repo_root=self.cfg.repo_root,
                    run_dir=run_dir,
                    request=request,
                    config=config,
                    guardrails_budgets=guardrails,
                )
            return {"status": "exec_failed", "reason": f"provider unavailable: {provider}"}
        except Exception as exc:
            return {"status": "exec_failed", "reason": str(exc)}

    def _log_support_provider_result(self, run_dir: Path, role: str, provider: str, result: dict[str, Any]) -> None:
        row = {
            "ts": now_iso(),
            "role": role,
            "provider": provider,
            "status": str(result.get("status", "")),
            "reason": str(result.get("reason", "")),
            "target_path": str(result.get("target_path", "")),
        }
        append_text(run_dir / "logs" / "telegram_cs_bot.support_provider.jsonl", json.dumps(row, ensure_ascii=False) + "\n")

    def _build_router_prompt(self, run_dir: Path, lang: str, user_text: str, state: dict[str, Any]) -> str:
        template = _load_prompt_text(
            SUPPORT_ROUTER_PROMPT_PATH,
            "You are CTCP support router. Return JSON with route/intent/confidence/followup_question/style_seed/risk_flags.",
        )
        context = {
            "schema_version": "ctcp-support-router-v1",
            "ts": now_iso(),
            "lang": lang,
            "latest_user_message": user_text,
            "session_state": state,
            "session_summary_fallback": _summarize_history_for_session(run_dir, lang),
            "constraints": {
                "user_channel_clean": True,
                "ops_logs_internal_only": True,
                "one_key_question_max": True,
            },
            "output_schema": {
                "route": "local|api|need_more_info|handoff_human",
                "intent": "string",
                "reason": "string",
                "followup_question": "string_or_empty",
                "style_seed": "string_or_empty",
                "handoff_brief": "string",
                "risk_flags": ["string"],
                "confidence": 0.0,
            },
        }
        prompt = template.rstrip() + "\n\n# Session Context (JSON)\n" + json.dumps(context, ensure_ascii=False, indent=2) + "\n"
        atomic_write_text(run_dir / SUPPORT_ROUTER_PROMPT_REL, prompt)
        return prompt

    def _heuristic_route(self, user_text: str, state: dict[str, Any], lang: str) -> dict[str, Any]:
        raw = str(user_text or "").strip()
        low = raw.lower()
        flags: list[str] = []
        intent = "general_support"
        followup_question = ""

        human_triggers = (
            "转人工",
            "人工客服",
            "投诉",
            "升级投诉",
            "律师",
            "监管",
            "法律",
            "human agent",
            "escalate",
            "complaint",
            "legal",
            "refund now",
        )
        if any(k in raw for k in ("转人工", "人工客服", "投诉", "升级投诉", "律师", "监管", "法律")) or any(
            k in low for k in ("human agent", "escalate", "complaint", "legal", "refund now")
        ):
            flags.append("needs_human_escalation")
            intent = "escalation"

        session_goal = " ".join(
            [
                str(state.get("user_goal", "")).strip(),
                str(state.get("session_summary", "")).strip(),
            ]
        ).strip()
        if is_cleanup_project_request(raw) or (
            raw in {"先清理", "清理一下", "先清理下", "先清除"}
            and any(k in session_goal for k in ("项目", "run", "任务", "会话", "project"))
        ):
            intent = "cleanup_project"
            return {
                "route": "local",
                "intent": intent,
                "reason": "cleanup request requires direct delete path",
                "followup_question": "",
                "style_seed": "cleanup-direct-delete",
                "handoff_brief": "",
                "risk_flags": ["destructive_request"],
                "confidence": 0.84,
            }

        if is_project_creation_request(raw):
            flags.append("project_creation")
            intent = "project_creation"

        if any(k in raw for k in ("改代码", "出 patch", "修 bug", "生成计划", "多文件", "架构", "失败复盘", "回归测试")) or any(
            k in low
            for k in (
                "patch",
                "run verify",
                "verify",
                "bug",
                "plan",
                "multiple files",
                "architecture",
                "refactor",
                "regression",
                "multi-step",
            )
        ):
            flags.append("needs_api_reasoning")
            if intent == "general_support":
                intent = "complex_execution"

        if not flags and (
            raw in {"帮我处理", "看一下", "继续", "安排一下", "处理一下"}
            or any(k in low for k in ("help", "please handle", "can you do this"))
        ):
            intent = "task_entry_clarify"
            if str(lang).lower() == "en":
                followup_question = "To start right away, should I handle existing project path, new requirement, or error troubleshooting first?"
            else:
                followup_question = "为了马上开始处理，你这轮希望我先做哪类：现有项目延续 / 新需求 / 报错排查？"
            route = "need_more_info"
            confidence = 0.61
            return {
                "route": route,
                "intent": intent,
                "reason": "task lane must be selected before execution",
                "followup_question": followup_question,
                "style_seed": _brief_text(intent, max_chars=40),
                "handoff_brief": "",
                "risk_flags": ["missing_key_detail"],
                "confidence": confidence,
            }

        low_streak = int(state.get("router_low_conf_streak", 0) or 0)
        if low_streak >= 2:
            flags.append("router_low_confidence_streak")

        if "needs_human_escalation" in flags:
            route = "handoff_human"
            reason = "customer asked for human escalation or sensitive handling"
            confidence = 0.83
        elif any(tag in flags for tag in ("needs_api_reasoning", "project_creation", "router_low_confidence_streak")):
            route = "api"
            reason = "request needs deeper reasoning or higher quality handoff"
            confidence = 0.74
        else:
            route = "local"
            reason = "local support response is sufficient for this turn"
            confidence = 0.67

        if route in {"api", "handoff_human"} and str(lang).lower() == "en":
            followup_question = ""
        elif route in {"api", "handoff_human"}:
            followup_question = ""

        return {
            "route": route,
            "intent": intent,
            "reason": reason,
            "followup_question": followup_question,
            "style_seed": _brief_text(f"{intent}-{route}", max_chars=48),
            "handoff_brief": "",
            "risk_flags": flags,
            "confidence": confidence,
        }

    def _build_handoff_brief(
        self,
        *,
        state: dict[str, Any],
        user_text: str,
        lang: str,
        route_reason: str,
    ) -> str:
        summary = str(state.get("session_summary", "")).strip()
        if not summary:
            summary = " ".join(
                [x for x in [str(state.get("user_goal", "")).strip(), _brief_text(user_text, max_chars=180)] if x]
            )
        confirmed = ", ".join(_safe_str_list(state.get("confirmed"), max_items=4, max_chars=80))
        open_q = ", ".join(_safe_str_list(state.get("open_questions"), max_items=3, max_chars=100))
        if str(lang).lower() == "en":
            lines = [
                f"Session summary: {summary or '(none)'}",
                f"Latest user message: {user_text.strip()}",
                f"Confirmed choices: {confirmed or '(none)'}",
                f"Open questions: {open_q or '(none)'}",
                f"Handoff reason: {route_reason}",
                "Hard constraints: keep user channel free of internal logs/paths; natural 2-4 paragraphs; max one key question.",
            ]
            return "\n".join(lines)
        lines = [
            f"会话摘要：{summary or '（暂无）'}",
            f"用户新消息：{user_text.strip()}",
            f"已确认：{confirmed or '（暂无）'}",
            f"待确认：{open_q or '（暂无）'}",
            f"移交原因：{route_reason}",
            "硬约束：用户通道不得出现内部日志/路径；回复为 2-4 段自然对话；最多一个关键问题。",
        ]
        return "\n".join(lines)

    def _route_with_local_router(self, chat_id: int, lang: str, run_dir: Path, user_text: str, state: dict[str, Any]) -> dict[str, Any]:
        fallback = self._heuristic_route(user_text, state, lang)
        config, cfg_msg = self._load_support_dispatch_config(run_dir)
        provider = self._resolve_support_provider(config, "support_lead_router", "ollama_agent")
        prompt = self._build_router_prompt(run_dir, lang, user_text, state)
        request = {
            "role": "support_lead_router",
            "action": "route",
            "target_path": SUPPORT_ROUTER_PROVIDER_REL.as_posix(),
            "missing_paths": [SUPPORT_ROUTER_PROMPT_REL.as_posix(), SUPPORT_SESSION_STATE_REL.as_posix()],
            "reason": prompt[-20000:] if len(prompt) > 20000 else prompt,
            "goal": f"support router chat {chat_id}",
            "input_text": user_text,
        }
        result = self._execute_support_provider(provider=provider, run_dir=run_dir, request=request, config=config)
        self._log_support_provider_result(run_dir, "support_lead_router", provider, result)
        provider_doc = _read_json_object(run_dir / SUPPORT_ROUTER_PROVIDER_REL)
        router_error = ""
        if str(result.get("status", "")) != "executed":
            router_error = str(result.get("reason", "")).strip() or "router provider execution failed"
        if not isinstance(provider_doc, dict):
            if not router_error:
                router_error = "router provider output missing/invalid json"
            provider_doc = {}

        route_raw = str(provider_doc.get("route", fallback.get("route", "local"))).strip().lower()
        route = route_raw
        if route not in {"local", "api", "need_more_info", "handoff_human"}:
            route = str(fallback.get("route", "local")).strip().lower() or "local"
        reason = re.sub(r"\s+", " ", str(provider_doc.get("reason", "")).strip())[:260] or str(fallback.get("reason", ""))
        intent = re.sub(r"\s+", " ", str(provider_doc.get("intent", "")).strip())[:80] or str(fallback.get("intent", "general_support"))
        followup_question = re.sub(
            r"\s+",
            " ",
            str(provider_doc.get("followup_question", "")).strip(),
        )[:180]
        if not followup_question:
            followup_question = str(fallback.get("followup_question", ""))
        style_seed = re.sub(r"\s+", " ", str(provider_doc.get("style_seed", "")).strip())[:80] or str(
            fallback.get("style_seed", "")
        )
        risk_flags = _safe_str_list(provider_doc.get("risk_flags"), max_items=6, max_chars=60) or _safe_str_list(
            fallback.get("risk_flags"), max_items=6, max_chars=60
        )
        confidence = _safe_float(provider_doc.get("confidence", fallback.get("confidence", 0.5)), 0.5)

        # Hard rules override provider route when trigger words indicate deeper execution.
        forced = self._heuristic_route(user_text, state, lang)
        forced_route = str(forced.get("route", "")).strip().lower()
        if forced_route in {"api", "handoff_human"} and route == "local":
            route = forced_route
            reason = (reason + "; forced by heuristic trigger").strip("; ")
            risk_flags = sorted(set(risk_flags + _safe_str_list(forced.get("risk_flags"), max_items=6, max_chars=60)))
            confidence = max(confidence, _safe_float(forced.get("confidence", 0.65), 0.65))
            if not style_seed:
                style_seed = str(forced.get("style_seed", ""))
            if not intent:
                intent = str(forced.get("intent", intent))
        if forced_route == "need_more_info" and route == "local" and not followup_question:
            route = "need_more_info"
            followup_question = str(forced.get("followup_question", "")).strip()
            risk_flags = sorted(set(risk_flags + ["missing_key_detail"]))

        handoff_brief = re.sub(r"\s+", " ", str(provider_doc.get("handoff_brief", "")).strip())
        if route in {"api", "handoff_human"} and not handoff_brief:
            handoff_brief = self._build_handoff_brief(state=state, user_text=user_text, lang=lang, route_reason=reason)

        if confidence < 0.45 and route == "local":
            route = "api"
            reason = (reason + "; escalated because router confidence is low").strip("; ")
            risk_flags = sorted(set(risk_flags + ["low_confidence"]))
            if not handoff_brief:
                handoff_brief = self._build_handoff_brief(state=state, user_text=user_text, lang=lang, route_reason=reason)

        if route == "need_more_info" and not followup_question:
            followup_question = (
                "Could you share the single most important goal for this round?"
                if str(lang).lower() == "en"
                else "你先告诉我这一轮最重要的目标是什么，可以吗？"
            )

        low_streak = int(state.get("router_low_conf_streak", 0) or 0)
        if router_error or confidence < 0.55:
            low_streak += 1
        else:
            low_streak = 0

        decision = {
            "route": route,
            "intent": intent or "general_support",
            "reason": reason,
            "followup_question": followup_question,
            "style_seed": style_seed or str(state.get("last_style_seed", "")),
            "handoff_brief": handoff_brief,
            "risk_flags": risk_flags,
            "confidence": confidence,
            "provider": provider,
            "provider_status": str(result.get("status", "")),
            "provider_reason": str(result.get("reason", "")),
            "router_error": router_error,
            "dispatch_config_note": cfg_msg,
            "router_low_conf_streak": low_streak,
        }
        atomic_write_text(run_dir / SUPPORT_ROUTER_LATEST_REL, json.dumps(decision, ensure_ascii=False, indent=2) + "\n")
        append_text(run_dir / SUPPORT_ROUTER_TRACE_REL, json.dumps({"ts": now_iso(), "chat_id": chat_id, **decision}, ensure_ascii=False) + "\n")
        state["router_low_conf_streak"] = low_streak
        save_support_session_state(run_dir, state)
        return decision

    def _build_support_reply_prompt(
        self,
        *,
        chat_id: int,
        lang: str,
        run_dir: Path,
        user_text: str,
        state: dict[str, Any],
        route_doc: dict[str, Any],
        style_hint: dict[str, str],
    ) -> str:
        template = _load_prompt_text(
            SUPPORT_REPLY_PROMPT_PATH,
            "You are CTCP Support Lead. Return one JSON object with reply_text,next_question,actions,debug_notes.",
        )
        context = {
            "schema_version": "ctcp-support-reply-input-v2",
            "ts": now_iso(),
            "chat_id": chat_id,
            "lang": lang,
            "route": route_doc,
            "latest_user_message": user_text,
            "session_state": state,
            "execution_focus": {
                "goal": str(state.get("execution_goal", "")).strip() or str(state.get("user_goal", "")).strip(),
                "next_action": str(state.get("execution_next_action", "")).strip() or _next_action_from_goal(user_text, lang),
            },
            "session_summary_fallback": _summarize_history_for_session(run_dir, lang),
            "whiteboard_snapshot": self._support_whiteboard_snapshot(run_dir, lang),
            "style_hint": {
                k: str(style_hint.get(k, ""))
                for k in ("opener", "transition", "closer", "question_style", "seed", "intent", "style_seed")
            },
            "collab_role": _normalize_collab_role(str(state.get("collab_role", "support_lead"))),
            "persona_hint": (
                "Team manager mode: proactively drive execution, checkpoint milestones, ask only one targeted question when blocked."
                if _normalize_collab_role(str(state.get("collab_role", "support_lead"))) == "team_manager"
                else "Support lead mode: keep concise service tone and ask one bounded question only when needed."
            ),
            "format_hint": "Natural customer-service reply, concise and clear. No rigid section template.",
            "progress_hint": "Ask at most one key question only when needed; otherwise continue naturally.",
            "channel_contract": "Never expose TRACE/outbox/artifacts/logs/RUN.json/guardrails/diff --git in user-facing reply_text.",
        }
        prompt = template.rstrip() + "\n\n# Session Context (JSON)\n" + json.dumps(context, ensure_ascii=False, indent=2) + "\n"
        atomic_write_text(run_dir / SUPPORT_REPLY_PROMPT_REL, prompt)
        return prompt

    def _fallback_support_reply(
        self,
        lang: str,
        user_text: str,
        critical_question: str,
        reason: str,
        collab_role: str = "support_lead",
    ) -> dict[str, Any]:
        if is_project_creation_request(user_text):
            reply, ask = _project_kickoff_reply(lang)
            return {
                "reply_text": reply,
                "next_question": ask,
                "actions": [],
                "debug_notes": reason,
            }
        role = _normalize_collab_role(collab_role)
        continuation_hint = is_explicit_continuation_request(user_text)
        actionable_goal = _has_actionable_goal_details(user_text)
        ask = re.sub(r"\s+", " ", str(critical_question or "").strip())
        if _is_generic_followup_question(ask, lang):
            if actionable_goal:
                ask = ""
            else:
                ask = _default_task_entry_question(lang, continuation_hint=continuation_hint)
        if str(lang).lower() == "en":
            if role == "team_manager":
                if actionable_goal:
                    parts = [
                        "Got it. I have enough context and I will proceed as your team manager now.",
                        "I will send the first actionable plan and milestone checkpoints in the next step.",
                    ]
                else:
                    parts = [
                        "Got it. I will take ownership as your team manager.",
                        "Share the one top priority and I will start executing immediately.",
                    ]
                if ask:
                    parts.append(ask)
                reply = "\n\n".join(parts)
                return {
                    "reply_text": reply,
                    "next_question": ask,
                    "actions": [],
                    "debug_notes": reason,
                }
            if actionable_goal:
                parts = [
                    "Got it. The goal is clear and I can proceed now.",
                    "I'll move directly into execution and send the first concrete plan in the next step.",
                ]
            else:
                parts = [
                    "Got it. I will handle this now.",
                    "Please share the module name, exact goal, or current error text, and I will move to the next step immediately.",
                ]
            if ask:
                parts.append(ask)
            reply = "\n\n".join(parts)
        else:
            if role == "team_manager":
                if actionable_goal:
                    parts = [
                        "收到，信息已足够，我会以团队经理方式马上推进。",
                        "下一步我会给你首轮可执行方案，并按里程碑同步进展。",
                    ]
                else:
                    parts = [
                        "收到，我先以团队经理方式接管推进。",
                        "你告诉我这一轮唯一最高优先级，我就立刻开工。",
                    ]
                if ask:
                    parts.append(ask)
                reply = "\n\n".join(parts)
                return {
                    "reply_text": reply,
                    "next_question": ask,
                    "actions": [],
                    "debug_notes": reason,
                }
            if actionable_goal:
                parts = [
                    "收到，目标信息已经足够，我现在就开始处理。",
                    "我会先给你首轮可执行方案，并按你的优先级继续推进。",
                ]
            else:
                parts = [
                    "收到，我来处理。",
                    "你直接发模块名、目标，或当前报错文本，我会立刻进入下一步。",
                ]
            if ask:
                parts.append(ask)
            reply = "\n\n".join(parts)
        return {
            "reply_text": reply,
            "next_question": ask,
            "actions": [],
            "debug_notes": reason,
        }

    def _generate_support_reply(
        self,
        *,
        chat_id: int,
        lang: str,
        run_dir: Path,
        user_text: str,
        state: dict[str, Any],
        route_doc: dict[str, Any],
        style_hint: dict[str, str],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        config, _msg = self._load_support_dispatch_config(run_dir)
        collab_role = _normalize_collab_role(str(state.get("collab_role", "support_lead")))
        route = str(route_doc.get("route", "")).strip().lower()
        route_intent = str(route_doc.get("intent", "")).strip().lower()

        if route_intent == "cleanup_project":
            reply_text, ask, actions = _cleanup_project_reply(lang)
            return (
                {
                    "reply_text": reply_text,
                    "next_question": ask,
                    "actions": actions,
                    "debug_notes": "cleanup_project_local_policy",
                },
                {
                    "provider": "none",
                    "provider_status": "skipped_cleanup_policy_direct_delete",
                    "provider_reason": "",
                    "provider_error": "",
                    "role": "support_lead_reply",
                    "handoff_brief": "",
                },
            )

        if route == "need_more_info":
            ask = str(route_doc.get("followup_question", "")).strip()
            fallback = self._fallback_support_reply(
                lang,
                user_text,
                ask,
                "router needs one key detail",
                collab_role=collab_role,
            )
            return (
                {
                    "reply_text": str(fallback.get("reply_text", "")),
                    "next_question": str(fallback.get("next_question", "")),
                    "actions": fallback.get("actions", []),
                    "debug_notes": str(fallback.get("debug_notes", "")),
                },
                {
                    "provider": "none",
                    "provider_status": "skipped_need_more_info",
                    "provider_reason": "",
                    "provider_error": "",
                    "role": "support_lead_reply",
                    "handoff_brief": "",
                },
            )

        role = "support_lead_handoff" if route in {"api", "handoff_human"} else "support_lead_reply"
        fallback_provider = "api_agent" if role == "support_lead_handoff" else "ollama_agent"
        provider = self._resolve_support_provider(config, role, fallback_provider)
        prompt = self._build_support_reply_prompt(
            chat_id=chat_id,
            lang=lang,
            run_dir=run_dir,
            user_text=user_text,
            state=state,
            route_doc=route_doc,
            style_hint=style_hint,
        )
        request = {
            "role": role,
            "action": "reply",
            "target_path": SUPPORT_REPLY_PROVIDER_REL.as_posix(),
            "missing_paths": [SUPPORT_REPLY_PROMPT_REL.as_posix(), SUPPORT_SESSION_STATE_REL.as_posix()],
            "reason": prompt[-24000:] if len(prompt) > 24000 else prompt,
            "goal": f"support reply chat {chat_id}",
            "input_text": user_text,
        }
        result = self._execute_support_provider(provider=provider, run_dir=run_dir, request=request, config=config)
        self._log_support_provider_result(run_dir, role, provider, result)
        provider_doc = _read_json_object(run_dir / SUPPORT_REPLY_PROVIDER_REL)

        critical_question = str(route_doc.get("followup_question", "")).strip()
        provider_error = ""
        if str(result.get("status", "")) != "executed":
            provider_error = str(result.get("reason", "")).strip() or "reply provider execution failed"
        if not isinstance(provider_doc, dict):
            if not provider_error:
                provider_error = "reply provider output missing/invalid json"
            provider_doc = self._fallback_support_reply(
                lang,
                user_text,
                critical_question,
                provider_error,
                collab_role=collab_role,
            )

        reply_text = str(provider_doc.get("reply_text", "")).strip()
        next_question = str(provider_doc.get("next_question", "")).strip()
        if not next_question and critical_question:
            next_question = critical_question
        if _replacement_char_count(reply_text) >= 2:
            provider_error = provider_error or "reply_text contains mojibake"
            fallback_doc = self._fallback_support_reply(
                lang,
                user_text,
                next_question,
                provider_error,
                collab_role=collab_role,
            )
            reply_text = str(fallback_doc.get("reply_text", ""))
            next_question = str(fallback_doc.get("next_question", ""))
            provider_doc = fallback_doc
        elif is_project_creation_request(user_text) and _is_generic_progress_reply(reply_text, lang):
            fallback_doc = self._fallback_support_reply(
                lang,
                user_text,
                next_question,
                provider_error or "reply_text too generic",
                collab_role=collab_role,
            )
            reply_text = str(fallback_doc.get("reply_text", ""))
            next_question = str(fallback_doc.get("next_question", ""))
            provider_doc = fallback_doc
        if not reply_text:
            fallback_doc = self._fallback_support_reply(
                lang,
                user_text,
                next_question,
                provider_error or "empty reply_text",
                collab_role=collab_role,
            )
            reply_text = str(fallback_doc.get("reply_text", ""))
            next_question = str(fallback_doc.get("next_question", ""))
            provider_doc = fallback_doc

        if route in {"api", "handoff_human"}:
            handoff_row = {
                "ts": now_iso(),
                "chat_id": chat_id,
                "provider": provider,
                "status": str(result.get("status", "")),
                "reason": str(result.get("reason", "")),
                "handoff_brief": str(route_doc.get("handoff_brief", "")),
                "target_path": str(request.get("target_path", "")),
            }
            append_text(run_dir / SUPPORT_HANDOFF_TRACE_REL, json.dumps(handoff_row, ensure_ascii=False) + "\n")

        ops_meta = {
            "provider": provider,
            "provider_status": str(result.get("status", "")),
            "provider_reason": str(result.get("reason", "")),
            "provider_error": provider_error,
            "role": role,
            "handoff_brief": str(route_doc.get("handoff_brief", "")),
        }
        return {
            "reply_text": reply_text,
            "next_question": next_question,
            "actions": provider_doc.get("actions", []),
            "debug_notes": str(provider_doc.get("debug_notes", "")),
        }, ops_meta

    def _purge_old_session_records(self, run_dir: Path) -> None:
        rel_targets = (
            SUPPORT_SESSION_STATE_REL,
            SUPPORT_INBOX_REL,
            SUPPORT_ROUTER_TRACE_REL,
            SUPPORT_ROUTER_LATEST_REL,
            SUPPORT_ROUTER_PROVIDER_REL,
            SUPPORT_REPLY_PROVIDER_REL,
            SUPPORT_REPLY_PROMPT_REL,
            SUPPORT_ROUTER_PROMPT_REL,
            SUPPORT_HANDOFF_TRACE_REL,
            SUPPORT_WHITEBOARD_REL,
            SUPPORT_WHITEBOARD_LOG_REL,
            Path("artifacts") / "support_actions.jsonl",
            Path("artifacts") / "USER_NOTES.md",
            Path("artifacts") / "API_BOT_SUMMARY.md",
            Path("logs") / "telegram_cs_bot.support_provider.jsonl",
            Path("logs") / "telegram_cs_bot.ops.jsonl",
        )
        for rel in rel_targets:
            path = run_dir / rel
            try:
                if path.exists() and path.is_file():
                    path.unlink()
            except Exception:
                continue

    def _hard_reset_old_support_state(
        self,
        *,
        chat_id: int,
        run_dir: Path,
        reason: str,
        purge_records: bool,
    ) -> None:
        if run_dir.exists():
            try:
                self._clear_blocked_hold(run_dir)
            except Exception:
                pass
            if purge_records:
                self._purge_old_session_records(run_dir)
            else:
                try:
                    save_support_session_state(run_dir, default_support_session_state())
                except Exception:
                    pass
                try:
                    self._append_note(run_dir, f"support/hard_reset {reason}")
                except Exception:
                    pass
        try:
            self.db.clear_pending_for_run(str(run_dir))
        except Exception:
            pass
        try:
            self.db.clear_maps_for_chat(chat_id)
        except Exception:
            pass
        self.db.clear_run(chat_id)

    def _apply_support_actions(
        self,
        *,
        chat_id: int,
        run_dir: Path,
        actions: Any,
        lang: str,
    ) -> dict[str, Any]:
        if not isinstance(actions, list) or not actions:
            return {}
        applied: list[dict[str, Any]] = []
        hard_reset_after_reply = False
        hard_reset_reason = ""
        for item in actions:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("type", "")).strip()
            if kind in {"delete_old_session_and_unbind", "direct_delete_old_session", "clear_old_session_state"}:
                marker = {
                    "ts": now_iso(),
                    "type": kind,
                    "scope": str(item.get("scope", "")),
                    "mode": str(item.get("mode", "delete")),
                    "lang": lang,
                }
                append_text(run_dir / "artifacts" / "support_actions.jsonl", json.dumps(marker, ensure_ascii=False) + "\n")
                self._append_note(run_dir, f"support/action {kind}")
                hard_reset_after_reply = True
                hard_reset_reason = kind
                applied.append({"type": kind, "status": "applied"})
            else:
                applied.append({"type": kind or "unknown", "status": "ignored"})
        if not applied:
            return {}
        out: dict[str, Any] = {"applied_actions": applied}
        if hard_reset_after_reply:
            out["hard_reset_after_reply"] = True
            out["hard_reset_reason"] = hard_reset_reason or "delete_old_session_and_unbind"
        return out

    def _handle_support_turn(self, chat_id: int, lang: str, run_dir: Path, text: str) -> bool:
        try:
            self._clear_auto_advance_pause(run_dir)
            state = load_support_session_state(run_dir)
            current_role = _normalize_collab_role(str(state.get("collab_role", "support_lead")))
            requested_role = ""
            if is_team_manager_role_request(text):
                requested_role = "team_manager"
            elif is_support_lead_role_request(text):
                requested_role = "support_lead"
            if requested_role and requested_role != current_role:
                state["collab_role"] = requested_role
                save_support_session_state(run_dir, state)
                if not _has_actionable_goal_details(text):
                    ack_text, ack_question = _role_switch_ack(lang, requested_role)
                    self._append_support_inbox(run_dir, "user", text, lang)
                    self._append_note(run_dir, f"telegram/role_switch {requested_role}")
                    payload = self._send_customer_reply(
                        chat_id=chat_id,
                        lang=lang,
                        run_dir=run_dir,
                        stage="support_role_switched",
                        reply_text=ack_text,
                        next_question=ack_question,
                        ops_status={"source_text": text, "collab_role": requested_role},
                    )
                    self._append_support_inbox(run_dir, "assistant", str(payload.get("reply_text", "")), lang)
                    return True
                state = load_support_session_state(run_dir)
            if str(text or "").strip():
                open_q = state.get("open_questions")
                if isinstance(open_q, list) and open_q:
                    state["open_questions"] = []
                    save_support_session_state(run_dir, state)
            self._append_support_inbox(run_dir, "user", text, lang)
            self._clear_blocked_hold(run_dir)
            route_doc = self._route_with_local_router(chat_id, lang, run_dir, text, state)
            turn_index = int(state.get("turn_index", 0) or 0) + 1
            style_hint = choose_style(
                chat_id=chat_id,
                turn_index=turn_index,
                lang=lang,
                state=state,
                route_doc=route_doc,
            )
            reply_doc, provider_meta = self._generate_support_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                user_text=text,
                state=state,
                route_doc=route_doc,
                style_hint=style_hint,
            )
            route_now = str(route_doc.get("route", "")).strip().lower()
            if (
                route_now == "need_more_info"
                and (str(route_doc.get("router_error", "")).strip() or str(provider_meta.get("provider_error", "")).strip())
                and not str(reply_doc.get("next_question", "")).strip()
            ):
                reply_doc["next_question"] = (
                    str(route_doc.get("followup_question", "")).strip()
                    or ("Could you confirm the top priority first?" if str(lang).lower() == "en" else "你先确认最高优先级目标可以吗？")
                )
            whiteboard_meta = self._support_librarian_whiteboard_exchange(
                run_dir=run_dir,
                lang=lang,
                user_text=text,
                route_doc=route_doc,
            )
            whiteboard_note = _brief_text(str(whiteboard_meta.get("public_note", "")).strip(), max_chars=260)
            if whiteboard_note:
                base_reply = str(reply_doc.get("reply_text", "")).strip()
                if whiteboard_note.lower() not in base_reply.lower():
                    reply_doc["reply_text"] = f"{base_reply}\n\n{whiteboard_note}" if base_reply else whiteboard_note
            if not str(reply_doc.get("next_question", "")).strip():
                wb_q = str(whiteboard_meta.get("question", "")).strip()
                if wb_q:
                    reply_doc["next_question"] = wb_q
            note_path = self._append_note(run_dir, f"telegram/note {text}")
            ops_payload: dict[str, Any] = {
                "source_text": text,
                "route_doc": route_doc,
                "reply_meta": provider_meta,
            }
            if isinstance(whiteboard_meta.get("ops"), dict):
                ops_payload["whiteboard"] = dict(whiteboard_meta.get("ops", {}))
            action_meta = self._apply_support_actions(
                chat_id=chat_id,
                run_dir=run_dir,
                actions=reply_doc.get("actions", []),
                lang=lang,
            )
            hard_reset_after_reply = bool(action_meta.get("hard_reset_after_reply", False)) if action_meta else False
            hard_reset_reason = str(action_meta.get("hard_reset_reason", "")).strip() if action_meta else ""
            if action_meta:
                ops_payload.update(action_meta)
            if self.cfg.note_ack_path:
                ops_payload["notes_path"] = note_path.relative_to(run_dir).as_posix()
            payload = self._send_customer_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                stage=f"support_turn_{route_doc.get('route', 'local')}",
                reply_text=str(reply_doc.get("reply_text", "")),
                next_question=str(reply_doc.get("next_question", "")),
                style_hint=style_hint,
                ops_status=ops_payload,
            )
            if hard_reset_after_reply:
                self._hard_reset_old_support_state(
                    chat_id=chat_id,
                    run_dir=run_dir,
                    reason=hard_reset_reason or "cleanup_project_post_reply",
                    purge_records=True,
                )
            else:
                self._append_support_inbox(run_dir, "assistant", str(payload.get("reply_text", "")), lang)
            return True
        except Exception as exc:
            state = load_support_session_state(run_dir)
            fallback = self._fallback_support_reply(
                lang,
                text,
                "",
                f"support turn fallback: {exc}",
                collab_role=str(state.get("collab_role", "support_lead")),
            )
            self._send_customer_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                stage="support_turn_fallback_exception",
                reply_text=str(fallback.get("reply_text", "")),
                next_question=str(fallback.get("next_question", "")),
                ops_status={"source_text": text, "error": str(exc)},
            )
            return True

    def _update_support_session_state(
        self,
        *,
        run_dir: Path,
        chat_id: int,
        lang: str,
        payload: dict[str, Any],
        ops_status: dict[str, Any] | None,
    ) -> None:
        state = load_support_session_state(run_dir)
        state["turn_index"] = int(state.get("turn_index", 0) or 0) + 1
        style = payload.get("ops_status", {}).get("style_hint", {})
        if isinstance(style, dict):
            state["last_style_seed"] = str(style.get("style_seed", style.get("seed", ""))).strip()
            state["style_seed"] = state["last_style_seed"]
        source_text = ""
        if isinstance(ops_status, dict):
            source_text = re.sub(r"\s+", " ", str(ops_status.get("source_text", "")).strip())
            role_hint = str(ops_status.get("collab_role", "")).strip()
            if role_hint:
                state["collab_role"] = _normalize_collab_role(role_hint)
            confirmed = ops_status.get("confirmed")
            if isinstance(confirmed, list):
                state["confirmed"] = _safe_str_list(confirmed, max_items=10, max_chars=120)
            route_doc = ops_status.get("route_doc")
            if isinstance(route_doc, dict):
                route_intent = re.sub(r"\s+", " ", str(route_doc.get("intent", "")).strip())
                if route_intent:
                    state["last_intent"] = route_intent[:80]
                seed = re.sub(r"\s+", " ", str(route_doc.get("style_seed", "")).strip())
                if seed:
                    state["last_style_seed"] = seed[:80]
                    state["style_seed"] = state["last_style_seed"]
        slots = _safe_memory_slots(state.get("memory_slots"))
        if source_text:
            slots = _extract_memory_slots(source_text, lang, slots)
        state["memory_slots"] = slots
        if source_text:
            existing_goal = str(state.get("user_goal", "")).strip()
            if not is_smalltalk_only_message(source_text):
                normalized_goal = _brief_text(source_text, max_chars=220)
                picked_goal = normalized_goal
                if frontend_build_project_manager_context is not None:
                    try:
                        history_user = _load_recent_user_messages(run_dir, max_rows=10)
                        if source_text and (not history_user or history_user[-1] != source_text):
                            history_user.append(source_text)
                        ctx = frontend_build_project_manager_context(history_user, lang=lang, max_questions=2)
                        picked = _brief_text(str(getattr(ctx, "requirement_summary", "")).strip(), max_chars=220)
                        score = float(getattr(ctx, "signal_score", 0.0) or 0.0)
                        if picked and score >= 2.2:
                            picked_goal = picked
                    except Exception:
                        picked_goal = normalized_goal
                if (not existing_goal or is_smalltalk_only_message(existing_goal)) and normalized_goal:
                    state["user_goal"] = picked_goal
                current_execution = str(state.get("execution_goal", "")).strip()
                if not current_execution or is_smalltalk_only_message(current_execution):
                    state["execution_goal"] = picked_goal
                else:
                    merged_goal = _brief_text(current_execution + " | " + picked_goal, max_chars=260)
                    state["execution_goal"] = picked_goal if len(picked_goal) >= len(_brief_text(current_execution, max_chars=220)) else merged_goal
                state["execution_next_action"] = _next_action_from_goal(str(state.get("execution_goal", "")), lang)
        question = str(payload.get("next_question", "")).strip()
        state["open_questions"] = [question] if question else []
        reply_brief = _brief_text(str(payload.get("reply_text", "")), max_chars=160)
        state["last_actions"] = reply_brief
        state["last_action_taken"] = reply_brief
        history_summary = _summarize_history_for_session(run_dir, lang)
        manual_summary = str(state.get("session_summary", "")).strip()
        pieces = [x for x in [manual_summary, history_summary, f"last_action={reply_brief}" if reply_brief else ""] if x]
        state["session_summary"] = _brief_text(" ".join(pieces), max_chars=560)
        save_support_session_state(run_dir, state)

    def _send_customer_reply(
        self,
        *,
        chat_id: int,
        lang: str,
        run_dir: Path,
        stage: str,
        reply_text: str,
        next_question: str = "",
        ops_status: dict[str, Any] | None = None,
        style_hint: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        state = load_support_session_state(run_dir)
        next_turn = int(state.get("turn_index", 0) or 0) + 1
        style = style_hint or choose_style(
            chat_id=chat_id,
            turn_index=next_turn,
            lang=lang,
            state=state,
            route_doc=(ops_status or {}).get("route_doc") if isinstance(ops_status, dict) else None,
        )
        stage_key = str(stage or "").strip().lower()
        ops = dict(ops_status or {})
        normalized_next = _normalize_next_question(next_question, lang) if str(next_question or "").strip() else ""
        existing_open = ""
        open_questions = state.get("open_questions")
        if isinstance(open_questions, list) and open_questions:
            existing_open = _normalize_next_question(str(open_questions[0]), lang)
        if normalized_next and existing_open:
            if normalized_next.rstrip("？?").lower() == existing_open.rstrip("？?").lower():
                normalized_next = ""
        effective_reply_text = str(reply_text or "")
        effective_next_question = normalized_next

        source_text = re.sub(r"\s+", " ", str(ops.get("source_text", "")).strip())
        route_intent = ""
        route_doc_raw = ops.get("route_doc")
        if isinstance(route_doc_raw, dict):
            route_intent = str(route_doc_raw.get("intent", "")).strip().lower()
        if not route_intent:
            route_intent = str(ops.get("intent", "")).strip().lower()
        task_summary_seed = _brief_text(
            source_text
            or str(state.get("execution_goal", "")).strip()
            or str(state.get("user_goal", "")).strip(),
            max_chars=260,
        )
        actionable_goal_seed = _has_actionable_goal_details(source_text or task_summary_seed) or is_project_creation_request(
            source_text or task_summary_seed
        )
        recent_user_messages = _load_recent_user_messages(run_dir, max_rows=10)
        if source_text and (not recent_user_messages or recent_user_messages[-1] != source_text):
            recent_user_messages.append(source_text)

        manager_ctx: Any = None
        manager_known_facts: dict[str, Any] = {}
        manager_assumptions: dict[str, Any] = {}
        manager_questions: list[str] = []
        manager_project_name = ""
        skip_manager_intents = {"cleanup_project", "smalltalk", "cancel_run", "task_entry_clarify"}
        if stage_key in {"api_note_reply", "note_reply", "smalltalk_reply", "smalltalk_fast_path", "api_follow_up", "api_note_saved_ack", "note_saved_ack"}:
            actionable_goal_seed = False
        manager_mode_candidate = bool(actionable_goal_seed or bool(ops.get("has_actionable_goal", False)))
        if frontend_build_project_manager_context is not None and manager_mode_candidate and route_intent not in skip_manager_intents:
            try:
                manager_ctx = frontend_build_project_manager_context(
                    recent_user_messages,
                    lang=lang,
                    max_questions=2,
                )
            except Exception:
                manager_ctx = None
        if manager_ctx is not None:
            manager_summary = _brief_text(str(getattr(manager_ctx, "requirement_summary", "")).strip(), max_chars=260)
            manager_signal = float(getattr(manager_ctx, "signal_score", 0.0) or 0.0)
            if manager_summary and manager_signal >= 2.2:
                task_summary_seed = manager_summary
            manager_known_facts = dict(getattr(manager_ctx, "known_facts", {}) or {})
            manager_assumptions = dict(getattr(manager_ctx, "assumptions", {}) or {})
            manager_questions = [str(x).strip() for x in list(getattr(manager_ctx, "high_leverage_questions", ()) or []) if str(x).strip()]
            manager_project_name = str(getattr(manager_ctx, "project_name", "")).strip()
            if manager_questions and stage_key.startswith("support_turn_"):
                # In PM mode, avoid forwarding generic provider intake questions.
                effective_next_question = ""
            if effective_next_question and frontend_is_generic_intake_question is not None:
                try:
                    if frontend_is_generic_intake_question(effective_next_question, lang):
                        effective_next_question = ""
                except Exception:
                    pass

        task_summary = task_summary_seed
        actionable_goal = _has_actionable_goal_details(source_text or task_summary) or is_project_creation_request(source_text or task_summary)
        try:
            decisions_count = int(str(ops.get("decisions_count", 0) or 0).strip())
        except Exception:
            decisions_count = 0
        try:
            question_count = int(str(ops.get("question_count", 0) or 0).strip())
        except Exception:
            question_count = 0
        run_status = str(ops.get("run_status", "")).strip().lower()
        if not run_status:
            if stage_key.startswith("support_turn_") or stage_key in {
                "new_run_created",
                "api_note_reply",
                "note_reply",
                "smalltalk_reply",
                "smalltalk_fast_path",
                "api_follow_up",
                "api_note_saved_ack",
                "note_saved_ack",
                "support_role_switched",
            }:
                run_status = ""
            else:
                run_status = self._run_status(run_dir)
        raw_backend_state: dict[str, Any] = {
            "stage": stage_key,
            "run_status": run_status,
            "next_step": str(ops.get("next_step", ops.get("next", ""))).strip(),
            "verify_result": str(ops.get("verify_result", "")).strip(),
            "waiting_for_decision": bool(ops.get("waiting_for_decision", False)),
            "decisions_count": decisions_count,
            "question_count": question_count,
            "blocked_needs_input": bool(ops.get("blocked_needs_input", False)) or stage_key == "advance_blocked",
            "needs_input": bool(effective_next_question),
            "is_executing": bool(ops.get("is_executing", False))
            or stage_key in {"advance_success", "status_reply", "trace_progress_push", "new_run_created"},
            "has_actionable_goal": bool(ops.get("has_actionable_goal", False)) or actionable_goal,
            "first_pass_understood": bool(ops.get("first_pass_understood", False)) or actionable_goal,
            "reason": str(ops.get("reason", "")).strip(),
            "missing_fields": ops.get("missing_fields", []),
        }
        if manager_known_facts:
            raw_backend_state["known_facts"] = manager_known_facts
        if raw_backend_state["decisions_count"] <= 0 and stage_key in {"decision_reply", "api_decision", "fallback_decision"}:
            raw_backend_state["decisions_count"] = 1
        if raw_backend_state["question_count"] <= 0 and str(ops.get("pending_prompts", "")).isdigit():
            raw_backend_state["question_count"] = int(str(ops.get("pending_prompts", "")).strip() or "0")
        notes: dict[str, Any] = {
            "lang": lang,
            "max_questions": 2,
            "recent_user_messages": recent_user_messages,
        }
        if stage_key in {"api_note_reply", "note_reply", "api_follow_up", "smalltalk_fast_path"}:
            notes["prefer_explicit_next_question"] = True
        if stage_key in {"smalltalk_reply", "smalltalk_fast_path", "api_note_reply", "note_reply", "api_note_saved_ack", "note_saved_ack", "status_reply"}:
            notes["prefer_raw_reply_text"] = True
        if manager_known_facts:
            notes["known_facts"] = manager_known_facts
        if manager_assumptions:
            notes["assumptions"] = manager_assumptions
        if manager_questions:
            notes["manager_questions"] = manager_questions
        if manager_assumptions:
            semantic_plan = str(manager_assumptions.get("semantic_plan", "")).strip()
            if str(lang).lower() == "en":
                if semantic_plan == "integrate_semantic_in_v1":
                    notes["execution_direction"] = (
                        "I will prioritize speed, land a runnable main pipeline first, "
                        "and integrate semantic capability directly in V1."
                    )
                else:
                    notes["execution_direction"] = (
                        "I will prioritize speed, land a runnable main pipeline first, "
                        "and keep semantic capability as a follow-on or parallel extension."
                    )
            else:
                if semantic_plan == "integrate_semantic_in_v1":
                    notes["execution_direction"] = "接下来我会先按“优先速度、先跑通主流程、语义能力第一版直接接入”的方向整理第一版方案。"
                else:
                    notes["execution_direction"] = "接下来我会先按“优先速度、先跑通主流程、语义能力后接入或并联”的方向整理第一版方案，不先让你补一堆非关键细节。"
        project_name = manager_project_name or _suggest_temporary_project_name(task_summary or source_text, lang)
        if project_name:
            notes["project_name"] = project_name

        # Always run user-facing output through the frontend reply pipeline.
        force_raw_reply = bool(ops.get("force_raw_reply", False))
        skip_frontend_stages = {"status_reply", "decision_reply", "api_decision", "fallback_decision", "api_no_pending_input"}
        if frontend_render_frontend_output is not None and not (
            force_raw_reply
            or stage_key in skip_frontend_stages
            or stage_key.startswith("command_")
            or stage_key.startswith("fallback_")
            or route_intent == "cleanup_project"
        ):
            try:
                rendered = frontend_render_frontend_output(
                    raw_backend_state=raw_backend_state,
                    task_summary=task_summary,
                    raw_reply_text=effective_reply_text,
                    raw_next_question=effective_next_question,
                    notes=notes,
                )
                rendered_reply = str(getattr(rendered, "reply_text", "") or "").strip()
                rendered_visible_state = str(getattr(rendered, "visible_state", "")).strip()
                if rendered_reply:
                    effective_reply_text = rendered_reply
                rendered_questions = list(getattr(rendered, "followup_questions", ()) or [])
                if rendered_questions:
                    effective_next_question = _normalize_next_question(str(rendered_questions[0]), lang)
                elif rendered_visible_state in {"UNDERSTOOD", "EXECUTING", "DONE"}:
                    # Avoid leaking stale/raw provider questions when the reviewed pipeline
                    # already decided no follow-up is needed for this turn.
                    effective_next_question = ""
                if effective_next_question and existing_open:
                    if effective_next_question.rstrip("？?").lower() == existing_open.rstrip("？?").lower():
                        effective_next_question = ""
                ops["visible_state"] = rendered_visible_state
                ops["frontend_redactions"] = int(getattr(rendered, "redactions", 0) or 0)
                missing = list(getattr(rendered, "missing_fields", ()) or [])
                if missing:
                    ops["missing_fields"] = missing
                if manager_known_facts:
                    ops["known_facts"] = manager_known_facts
                if manager_assumptions:
                    ops["default_assumptions"] = manager_assumptions
                if manager_questions:
                    ops["manager_questions"] = manager_questions
                if project_name:
                    ops["project_name"] = project_name
                pipeline_state = getattr(rendered, "pipeline_state", None)
                if isinstance(pipeline_state, dict):
                    ops["reply_pipeline"] = {
                        "selected_requirement_source": str(pipeline_state.get("selected_requirement_source", "")).strip(),
                        "visible_state": str(pipeline_state.get("visible_state", "")).strip(),
                        "review_flags": list(pipeline_state.get("review_flags", []) or []),
                        "redactions": int(pipeline_state.get("redactions", 0) or 0),
                    }
            except Exception as exc:
                ops["frontend_render_error"] = str(exc)
        payload = build_user_reply_payload(
            reply_text=effective_reply_text,
            next_question=effective_next_question,
            lang=lang,
            ops_status=ops,
            style_hint=style,
            default_assumption=str(ops.get("default_assumption", "")),
        )
        self._append_ops_status(run_dir, stage, payload.get("ops_status", {}))
        self._emit_public_reply(chat_id=chat_id, text=str(payload.get("reply_text", "")))
        self._update_support_session_state(run_dir=run_dir, chat_id=chat_id, lang=lang, payload=payload, ops_status=ops)
        return payload

    def _run_status(self, run_dir: Path) -> str:
        run_id = self._bridge_run_id(run_dir)
        if callable(bridge_ctcp_get_status):
            try:
                status_doc = bridge_ctcp_get_status(run_id)  # type: ignore[misc]
                if isinstance(status_doc, dict):
                    bridge_status = str(status_doc.get("run_status", "")).strip().lower()
                    if bridge_status:
                        return bridge_status
            except Exception:
                pass
        p = run_dir / "RUN.json"
        if not p.exists():
            return ""
        try:
            doc = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            return str(doc.get("status", "")).strip().lower()
        except Exception:
            return ""

    def _blocked_signature(self, *, owner: str, path: str, reason: str) -> str:
        body = " | ".join(
            [
                re.sub(r"\s+", " ", str(owner or "").strip().lower()),
                re.sub(r"\s+", " ", str(path or "").strip().lower()),
                re.sub(r"\s+", " ", str(reason or "").strip().lower()),
            ]
        ).strip()
        return body[:220]

    def _clear_blocked_hold(self, run_dir: Path) -> None:
        state = load_support_session_state(run_dir)
        had_hold = bool(str(state.get("blocked_signature", "")).strip()) or float(state.get("blocked_since_ts", 0.0) or 0.0) > 0.0
        if not had_hold:
            return
        state["blocked_signature"] = ""
        state["blocked_since_ts"] = 0.0
        save_support_session_state(run_dir, state)

    def _mark_blocked_hold(self, run_dir: Path, signature: str) -> None:
        state = load_support_session_state(run_dir)
        state["blocked_signature"] = str(signature or "").strip()[:220]
        state["blocked_since_ts"] = float(time.time())
        save_support_session_state(run_dir, state)

    def _is_blocked_hold_active(self, run_dir: Path, signature: str = "") -> bool:
        state = load_support_session_state(run_dir)
        last_sig = str(state.get("blocked_signature", "")).strip()
        if not last_sig:
            return False
        want_sig = str(signature or "").strip()
        if want_sig and last_sig != want_sig:
            return False
        try:
            since = float(state.get("blocked_since_ts", 0.0) or 0.0)
        except Exception:
            since = 0.0
        if since <= 0.0:
            return False
        return (time.time() - since) < BLOCKED_ADVANCE_COOLDOWN_SECONDS

    def _set_auto_advance_pause(self, run_dir: Path, seconds: float = 180.0) -> None:
        state = load_support_session_state(run_dir)
        state["auto_advance_pause_until_ts"] = max(time.time() + max(0.0, float(seconds or 0.0)), 0.0)
        save_support_session_state(run_dir, state)

    def _clear_auto_advance_pause(self, run_dir: Path) -> None:
        state = load_support_session_state(run_dir)
        if float(state.get("auto_advance_pause_until_ts", 0.0) or 0.0) <= 0.0:
            return
        state["auto_advance_pause_until_ts"] = 0.0
        save_support_session_state(run_dir, state)

    def _is_auto_advance_paused(self, run_dir: Path) -> bool:
        state = load_support_session_state(run_dir)
        try:
            until_ts = float(state.get("auto_advance_pause_until_ts", 0.0) or 0.0)
        except Exception:
            until_ts = 0.0
        return until_ts > time.time()

    def _first_failure_text(self, run_dir: Path) -> str:
        vr = run_dir / "artifacts" / "verify_report.json"
        if not vr.exists():
            return ""
        try:
            doc = json.loads(vr.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return ""
        fails = doc.get("failures", [])
        if isinstance(fails, list) and fails and isinstance(fails[0], dict):
            return str(fails[0].get("message", "")).strip()
        return ""

    def _customer_done_text(self, trace_text: str, lang: str) -> str:
        rows: list[str] = []
        for ln in (trace_text or "").splitlines():
            t = _humanize_trace_event_line(ln, lang)
            if not t:
                continue
            body = t[2:].strip().replace("`", "") if t.startswith("- ") else t.strip().replace("`", "")
            rows.append(body)
        rows = rows[-8:]
        if str(lang).lower() == "en":
            done = [x for x in rows if any(k in x.lower() for k in ("completed", "passed", "workflow completed"))]
            return done[-1] if done else "No confirmed progress updates yet."
        done = [x for x in rows if any(k in x for k in ("已完成", "验收通过", "流程已完成", "已经了解", "已经开始"))]
        return done[-1] if done else "目前还没有新的进展更新。"

    def _customer_next_plan_text(self, run_dir: Path, prompts: list[tuple[Path, PromptItem]], run_state: str, lang: str) -> str:
        state = load_support_session_state(run_dir)
        task_summary = _brief_text(
            str(state.get("execution_goal", "")).strip() or str(state.get("user_goal", "")).strip(),
            max_chars=220,
        )
        for _p, item in prompts:
            if item.prompt_type == "question":
                rewritten = _rewrite_missing_questions_for_customer(
                    raw_text=item.prompt_text,
                    task_summary=task_summary,
                    lang=lang,
                    max_questions=1,
                )
                brief = rewritten[0] if rewritten else _sanitize_internal_for_customer(_brief_text(item.prompt_text, max_chars=80), lang)
                if str(lang).lower() == "en":
                    return f"Waiting for your input: {brief or 'a quick confirmation'}."
                return f"等你确认一下：{brief or '一个选项'}。"
        for _p, item in prompts:
            if item.prompt_type == "agent_request" and item.recipient:
                brief = _sanitize_internal_for_customer(_brief_text(item.prompt_text, max_chars=80), lang)
                if str(lang).lower() == "en":
                    return f"Working on: {brief or 'your request'}."
                return f"正在处理：{brief or '你的请求'}。"
        for _p, item in prompts:
            rewritten = _rewrite_missing_questions_for_customer(
                raw_text=item.prompt_text,
                task_summary=task_summary,
                lang=lang,
                max_questions=1,
            )
            brief = rewritten[0] if rewritten else _sanitize_internal_for_customer(_brief_text(item.prompt_text, max_chars=80), lang)
            if str(lang).lower() == "en":
                return f"Need a bit more info: {brief or 'some details from you'}."
            return f"需要你补充一下：{brief or '一些细节'}。"
        state = str(run_state or "").strip().lower()
        if str(lang).lower() == "en":
            if state in {"pass", "done"}:
                return "Wrapping things up for you."
            if state in {"blocked", "failed", "error"}:
                return "Looking into the issue and working on a fix."
            return "Continuing to work on your request."
        if state in {"pass", "done"}:
            return "正在帮你整理结果。"
        if state in {"blocked", "failed", "error"}:
            return "正在排查问题并修复中。"
        return "继续帮你处理中。"

    def _require_run(self, chat_id: int, lang: str) -> Path | None:
        s = self.db.get_session(chat_id)
        raw = str(s.get("run_dir", "")).strip()
        if not raw:
            self.tg.send(chat_id=chat_id, text=i18n(lang, "need_run"))
            return None
        run_dir = Path(raw).expanduser().resolve()
        if not run_dir.exists():
            self.db.clear_run(chat_id)
            self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'need_run')} (run dir missing)")
            return None
        return run_dir

    def _create_run(self, chat_id: int, lang: str, goal: str) -> None:
        goal = goal.strip()
        if not goal:
            self.tg.send(chat_id=chat_id, text="Please send a non-empty goal.")
            return
        rc, out, err = self._run_orchestrate(["new-run", "--goal", goal])
        if rc != 0:
            self.tg.send(
                chat_id=chat_id,
                text=_compose_three_part_reply(
                    lang=lang,
                    conclusion="当前初始化未成功完成。",
                    plans=["我会先检查失败原因并立即重试。"],
                    next_question="你希望我继续自动重试，还是先把关键报错摘要发你确认？",
                ),
            )
            return
        run_dir = ""
        for ln in (out or "").splitlines():
            m = re.search(r"run_dir=(.+)$", ln.strip())
            if m:
                run_dir = m.group(1).strip()
                break
        if not run_dir:
            run_dir = self._read_last_run()
        if not run_dir:
            self.tg.send(chat_id=chat_id, text="new-run finished but run_dir not found")
            return
        resolved = Path(run_dir).expanduser().resolve()
        self.db.bind_run(chat_id, resolved)
        self.db.set_lang(chat_id, lang)
        state = default_support_session_state()
        if is_team_manager_role_request(goal):
            state["collab_role"] = "team_manager"
        state["user_goal"] = _brief_text(goal, max_chars=180)
        state["session_summary"] = _brief_text(goal, max_chars=240)
        save_support_session_state(resolved, state)
        self._append_support_inbox(resolved, "user", goal, lang)
        self._append_note(resolved, f"telegram/goal {goal}")
        ack = build_employee_note_reply(goal, lang, collab_role=str(state.get("collab_role", "support_lead")))
        payload = self._send_customer_reply(
            chat_id=chat_id,
            lang=lang,
            run_dir=resolved,
            stage="new_run_created",
            reply_text=ack,
            next_question="",
            ops_status={"goal": goal, "run_created": True},
        )
        self._append_support_inbox(resolved, "assistant", str(payload.get("reply_text", "")), lang)

    def _collect_prompts(self, run_dir: Path) -> list[tuple[Path, PromptItem]]:
        run_id = self._bridge_run_id(run_dir)
        if callable(bridge_ctcp_list_decisions_needed):
            try:
                decisions_doc = bridge_ctcp_list_decisions_needed(run_id)  # type: ignore[misc]
            except Exception:
                decisions_doc = {}
            decisions = decisions_doc.get("decisions", []) if isinstance(decisions_doc, dict) else []
            if isinstance(decisions, list):
                bridge_rows: list[tuple[Path, PromptItem]] = []
                for row in decisions:
                    if not isinstance(row, dict):
                        continue
                    if str(row.get("kind", "")).strip() != "outbox_prompt":
                        continue
                    prompt_rel = str(row.get("prompt_path", "")).strip()
                    if not prompt_rel:
                        continue
                    try:
                        prompt_abs = ensure_within_run_dir(run_dir, prompt_rel)
                    except Exception:
                        continue
                    if (not prompt_abs.exists()) or (not prompt_abs.is_file()):
                        continue
                    item = parse_outbox_prompt(run_dir, prompt_abs)
                    if not item:
                        continue
                    if _is_internal_support_prompt_item(item):
                        continue
                    if prompt_pending(run_dir, item, prompt_abs):
                        bridge_rows.append((prompt_abs, item))
                if bridge_rows:
                    return bridge_rows
        outbox = run_dir / "outbox"
        if not outbox.exists():
            return []
        rows: list[tuple[Path, PromptItem]] = []
        for p in sorted(outbox.glob("*.md")):
            if not p.is_file():
                continue
            item = parse_outbox_prompt(run_dir, p)
            if item and _is_internal_support_prompt_item(item):
                continue
            if item and prompt_pending(run_dir, item, p):
                rows.append((p, item))
        return rows

    def _render_prompt(self, run_dir: Path, item: PromptItem, lang: str) -> str:
        state = load_support_session_state(run_dir)
        task_summary = _brief_text(
            str(state.get("execution_goal", "")).strip() or str(state.get("user_goal", "")).strip(),
            max_chars=220,
        )
        brief = _sanitize_internal_for_customer(_prompt_topic_for_customer(item.prompt_text, item.target_path, lang), lang)
        prompt_line = _sanitize_internal_for_customer(parse_key_line(item.raw_text, "Prompt"), lang)
        rewritten_questions = _rewrite_missing_questions_for_customer(
            raw_text="\n".join([item.prompt_text, item.raw_text]),
            task_summary=task_summary,
            lang=lang,
            max_questions=2,
        )
        sanitized_options: list[str] = []
        for raw_opt in item.options:
            clean_opt = _sanitize_internal_for_customer(str(raw_opt), lang)
            if clean_opt:
                sanitized_options.append(clean_opt)
        if item.prompt_type == "question":
            ask = rewritten_questions[0] if rewritten_questions else (prompt_line or brief or "Please choose an option.")
            ask = _normalize_next_question(ask, lang)
            if str(lang).lower() == "en":
                lines = ["A decision is needed before we can continue.", ask]
                if sanitized_options:
                    lines.append("Options: " + " / ".join(sanitized_options))
                lines.append("Reply to this message (text/file) if needed.")
                return "\n".join(lines)
            lines = ["继续之前需要你做一个选择。", ask]
            if sanitized_options:
                lines.append("可选项：" + " / ".join(sanitized_options))
            lines.append("如需补充，可直接回复这条消息（文本/文件都可以）。")
            return "\n".join(lines)
        brief = rewritten_questions[0] if rewritten_questions else brief
        if str(lang).lower() == "en":
            return (
                "I need one piece of input from you to continue.\n"
                f"Topic: {brief}\n"
                "Reply to this message with text or a file; I will write it to the correct place."
            )
        return (
            "我需要你补充一条信息才能继续帮你处理。\n"
            f"主题：{brief}\n"
            "请直接回复这条消息（文本或文件都可以），我会自动写到对应位置。"
        )

    def _send_prompt(self, chat_id: int, run_dir: Path, item: PromptItem, kind: str) -> int:
        markup = None
        if kind == "question" and item.options:
            btns = [{"text": opt, "callback_data": f"q:{i}"} for i, opt in enumerate(item.options)]
            markup = {"inline_keyboard": [btns[i : i + 3] for i in range(0, len(btns), 3)]}
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        sent = self.tg.send(chat_id=chat_id, text=self._render_prompt(run_dir, item, lang), markup=markup)
        msg_id = int(sent.get("message_id", 0))
        self.db.save_map(chat_id=chat_id, msg_id=msg_id, run_dir=str(run_dir), target_path=item.target_path, prompt_path=item.rel_prompt_path, kind=kind, qid=item.qid, options=item.options)
        return msg_id

    def _status_text(self, run_dir: Path, lang: str) -> str:
        prompts = self._collect_prompts(run_dir)
        q = sum(1 for _, i in prompts if i.prompt_type == "question")
        a = sum(1 for _, i in prompts if i.prompt_type == "agent_request" and i.recipient)
        n = len(prompts) - q - a
        run_state = self._run_status(run_dir) or ("unknown" if str(lang).lower() == "en" else "未知")
        trace = run_dir / "TRACE.md"
        t = ""
        if trace.exists():
            t = trace.read_text(encoding="utf-8", errors="replace")
        done_text = self._customer_done_text(t, lang)
        plan_text = self._customer_next_plan_text(run_dir, prompts, run_state, lang)
        fail_text = self._first_failure_text(run_dir)
        if fail_text:
            issue_text = _sanitize_internal_for_customer(fail_text, lang)
            if not issue_text:
                issue_text = (
                    "I hit a temporary internal issue and I'm isolating it now."
                    if str(lang).lower() == "en"
                    else "我遇到一个内部处理异常，正在排查。"
                )
        elif q > 0:
            if str(lang).lower() == "en":
                issue_text = "Waiting for your decision on a key choice."
            else:
                issue_text = "等待你确认一个选项。"
        else:
            issue_text = "none" if str(lang).lower() == "en" else "暂无明显阻塞"
        if str(lang).lower() == "en":
            return _compose_three_part_reply(
                lang=lang,
                conclusion=f"Here's where things stand: {run_state}.",
                plans=[
                    f"Currently working on: {plan_text}",
                    f"Latest progress: {done_text}; Note: {issue_text}",
                ],
                next_question="Would you like me to keep going, or pause for your input first?",
            )
        return _compose_three_part_reply(
            lang=lang,
            conclusion=f"目前的处理状态是：{run_state}。",
            plans=[
                f"我正在处理：{plan_text}",
                f"最新进展：{done_text}；备注：{issue_text}",
            ],
            next_question="我继续帮你处理，还是先等你确认一下？",
        )

    def _decision_text(self, run_dir: Path, lang: str) -> str:
        prompts = self._collect_prompts(run_dir)
        user_items: list[PromptItem] = []
        for _p, item in prompts:
            if item.prompt_type == "question":
                user_items.append(item)
                continue
            if item.prompt_type == "agent_request" and item.recipient:
                continue
            user_items.append(item)
        if not user_items:
            if str(lang).lower() == "en":
                return _compose_three_part_reply(
                    lang=lang,
                    conclusion="No decision is needed from you right now.",
                    plans=["I will continue to push execution automatically."],
                    next_question="Would you like me to pause only when a key decision appears?",
                )
            return _compose_three_part_reply(
                lang=lang,
                conclusion="目前没有需要你拍板的事项。",
                plans=["我会继续帮你处理。"],
                next_question="是否仅在需要你确认时再提醒你？",
            )
        state = load_support_session_state(run_dir)
        task_summary = _brief_text(
            str(state.get("execution_goal", "")).strip() or str(state.get("user_goal", "")).strip(),
            max_chars=220,
        )
        top_briefs: list[str] = []
        for item in user_items[:2]:
            rewritten = _rewrite_missing_questions_for_customer(
                raw_text=item.prompt_text,
                task_summary=task_summary,
                lang=lang,
                max_questions=1,
            )
            candidate = rewritten[0] if rewritten else short_tail(item.prompt_text, max_lines=1, max_chars=80).replace("\n", " / ")
            safe = _sanitize_internal_for_customer(candidate, lang)
            if safe:
                top_briefs.append(safe)
        if not top_briefs:
            top_briefs = ["需要你确认一个选择" if str(lang).lower() != "en" else "A decision needs your input."]
        if str(lang).lower() == "en":
            return _compose_three_part_reply(
                lang=lang,
                conclusion=f"{len(user_items)} item(s) need your decision.",
                plans=[f"Top pending topic: {top_briefs[0]}"],
                next_question="Should I prioritize this decision now?",
            )
        return _compose_three_part_reply(
            lang=lang,
            conclusion=f"当前有 {len(user_items)} 项需要你确认。",
            plans=[f"最关键的待确认事项：{top_briefs[0]}"],
            next_question="你希望我先处理这一项吗？",
        )

    def _send_status(self, chat_id: int, run_dir: Path) -> None:
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        self._send_customer_reply(
            chat_id=chat_id,
            lang=lang,
            run_dir=run_dir,
            stage="status_reply",
            reply_text=self._status_text(run_dir, lang),
            next_question="你希望我继续处理还是先等你确认？" if str(lang).lower() != "en" else "After this update, should I keep working or wait for your input?",
            ops_status={"run_status": self._run_status(run_dir), "pending_prompts": len(self._collect_prompts(run_dir))},
        )

    def _send_file(self, chat_id: int, lang: str, run_dir: Path, rel_path: str, caption: str = "") -> None:
        try:
            p = ensure_within_run_dir(run_dir, rel_path)
        except Exception:
            self.tg.send(chat_id=chat_id, text=i18n(lang, "unsafe"))
            return
        if not p.exists() or not p.is_file():
            self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'missing')}: {rel_path}")
            return
        self.tg.send_doc(chat_id=chat_id, path=p, caption=caption or rel_path)

    def _send_verify(self, chat_id: int, run_dir: Path) -> None:
        p = run_dir / "artifacts" / "verify_report.json"
        run_id = self._bridge_run_id(run_dir)
        if callable(bridge_ctcp_get_last_report):
            try:
                report_doc = bridge_ctcp_get_last_report(run_id)  # type: ignore[misc]
            except Exception:
                report_doc = {}
            if isinstance(report_doc, dict):
                maybe_path = str(report_doc.get("verify_report_path", "")).strip()
                if maybe_path:
                    p = Path(maybe_path).expanduser()
        if p.exists():
            self.tg.send_doc(chat_id=chat_id, path=p, caption="verify_report.json")
        else:
            self.tg.send(chat_id=chat_id, text="verify_report.json not found")

    def _send_bundle(self, chat_id: int, run_dir: Path, with_actions: bool) -> None:
        bundle = run_dir / "failure_bundle.zip"
        if not bundle.exists():
            self.tg.send(chat_id=chat_id, text="当前没有失败包。")
            return
        summary = "verify_report.json missing"
        vr = run_dir / "artifacts" / "verify_report.json"
        if vr.exists():
            try:
                doc = json.loads(vr.read_text(encoding="utf-8", errors="replace"))
                summary = f"verify={doc.get('result', '')}"
                fails = doc.get("failures", [])
                if isinstance(fails, list) and fails and isinstance(fails[0], dict):
                    msg = str(fails[0].get("message", "")).strip()
                    if msg:
                        summary += f"; first_failure={msg}"
            except Exception:
                summary = "failed to parse verify_report.json"
        markup = None
        if with_actions:
            markup = {"inline_keyboard": [[{"text": "Retry", "callback_data": "fb:retry"}, {"text": "Stop", "callback_data": "fb:stop"}, {"text": "Relax", "callback_data": "fb:relax"}]]}
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        if str(lang).lower() == "en":
            self.tg.send(chat_id=chat_id, text=f"A failure bundle is available.\nSummary: {summary}", markup=markup)
        else:
            self.tg.send(chat_id=chat_id, text=f"检测到失败证据包。\n摘要：{summary}", markup=markup)
        self.tg.send_doc(chat_id=chat_id, path=bundle, caption="failure_bundle.zip")

    def _write_reply(self, *, chat_id: int, lang: str, mapping: dict[str, Any], text: str | None, file_id: str | None) -> None:
        run_dir = Path(str(mapping.get("run_dir", ""))).expanduser().resolve()
        run_id = self._bridge_run_id(run_dir)
        rel = str(mapping.get("target_path", "")).strip()
        prompt_path = str(mapping.get("prompt_path", "")).strip()
        try:
            _target = ensure_within_run_dir(run_dir, rel)
        except Exception as exc:
            self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'write_fail')}: {exc}")
            return
        if not self._bridge_ready():
            self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'write_fail')}: frontend bridge unavailable")
            return
        try:
            if file_id:
                payload_bytes = self.tg.download(file_id)
                tmp_path = ""
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".telegram-upload") as tmp:
                        tmp.write(payload_bytes)
                        tmp_path = tmp.name
                    bridge_ctcp_upload_artifact(  # type: ignore[misc]
                        run_id,
                        {
                            "source_path": tmp_path,
                            "dest_rel": rel,
                        },
                    )
                finally:
                    if tmp_path:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass
            else:
                payload = str(text or "")
                if not payload.endswith("\n"):
                    payload += "\n"
                bridge_ctcp_submit_decision(  # type: ignore[misc]
                    run_id,
                    {
                        "prompt_path": prompt_path,
                        "target_path": rel,
                        "content": payload,
                    },
                )
        except Exception as exc:
            self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'write_fail')}: {exc}")
            return
        self.db.del_map(chat_id, int(mapping["prompt_msg_id"]))
        if prompt_path:
            self.db.del_pending(str(run_dir), prompt_path)
        self._clear_blocked_hold(run_dir)
        self._send_customer_reply(
            chat_id=chat_id,
            lang=lang,
            run_dir=run_dir,
            stage="write_reply_ok",
            reply_text=(
                "Got it, noted. I'll feed this into the next step right away."
                if str(lang).lower() == "en"
                else "收到了，已记录。这条信息我会直接带入下一步执行。"
            ),
            next_question=_default_next_question(lang),
            ops_status={"target_path": rel, "prompt_path": prompt_path},
        )

    def _detect_api_auth_failure_source(self, run_dir: Path) -> str:
        scan_files = (
            "logs/plan_agent.stderr",
            "logs/patch_agent.stderr",
            "logs/agent.stderr",
            "logs/plan_agent.stdout",
            "logs/patch_agent.stdout",
            "logs/agent.stdout",
        )
        auth_tokens = (
            "token is invalid",
            "http 401",
            "status code: 401",
            "unauthorized",
            "invalid api key",
            "incorrect api key",
            "authentication failed",
            "error code: 401",
        )
        for rel in scan_files:
            path = run_dir / rel
            if not path.exists() or not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            low = text.lower()
            if any(token in low for token in auth_tokens):
                return rel
        return ""

    def _blocked_issue_override(self, run_dir: Path, *, reason: str, path: str, lang: str) -> tuple[str, str]:
        reason_low = str(reason or "").strip().lower()
        path_low = str(path or "").strip().replace("\\", "/").lower()
        if ("analysis.md" not in path_low) and ("plan_draft.md" not in path_low) and ("waiting for analysis.md" not in reason_low):
            return "", ""
        source = self._detect_api_auth_failure_source(run_dir)
        if not source:
            return "", ""
        if str(lang).lower() == "en":
            return (
                'API authentication failed (401/token invalid). Please update OPENAI_API_KEY (or CTCP_OPENAI_API_KEY), then reply "continue" and I will retry right away.',
                source,
            )
        return (
            '检测到 API 鉴权失败（401 / token invalid）。请更新 OPENAI_API_KEY（或 CTCP_OPENAI_API_KEY），然后回复“继续”，我会立即重试。',
            source,
        )

    def _advance_once(self, chat_id: int, run_dir: Path, steps: int) -> None:
        rc, out, err = self._run_orchestrate(["advance", "--max-steps", str(max(1, steps)), "--run-dir", str(run_dir)])
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        merged = (out or "") + "\n" + (err or "")
        parsed = parse_orchestrate_output(merged)
        status = parsed.get("run_status", "")
        next_step = parsed.get("next", "")
        owner = parsed.get("owner", "")
        path = parsed.get("path", "")
        reason = parsed.get("reason", "") or parsed.get("blocked", "")
        iterations = parsed.get("iterations", "")
        is_blocked = (next_step == "blocked") or ("blocked" in parsed and bool(parsed.get("blocked", "")))
        if rc == 0 and is_blocked:
            item_name = describe_artifact_for_customer(path, lang)
            owner_name = _role_label(owner, lang) if owner else ("N/A" if str(lang).lower() == "en" else "未给出")
            issue_text = describe_reason_for_customer(reason, path, lang)
            issue_override, auth_hint_source = self._blocked_issue_override(run_dir, reason=reason, path=path, lang=lang)
            if issue_override:
                issue_text = issue_override
            blocked_sig = self._blocked_signature(owner=owner, path=path, reason=reason or issue_text)
            if blocked_sig and self._is_blocked_hold_active(run_dir, blocked_sig):
                self._append_ops_status(
                    run_dir,
                    "advance_blocked_suppressed",
                    {
                        "rc": rc,
                        "owner": owner_name,
                        "next_step": next_step,
                        "reason": reason,
                        "path": path,
                        "blocked_signature": blocked_sig,
                    },
                )
                return
            self._mark_blocked_hold(run_dir, blocked_sig)
            if str(lang).lower() == "en":
                msg = _compose_three_part_reply(
                    lang=lang,
                    conclusion="I need a bit of information from you before I can continue.",
                    plans=[f"Regarding: {item_name}", f"What I need: {issue_text}"],
                    next_question="Could you provide this now?",
                )
            else:
                msg = _compose_three_part_reply(
                    lang=lang,
                    conclusion="我这边需要你补充一些信息才能继续帮你处理。",
                    plans=[f"关于：{item_name}", f"需要的信息：{issue_text}"],
                    next_question="你现在方便提供吗？",
                )
            self._send_customer_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                stage="advance_blocked",
                reply_text=msg,
                next_question="",
                ops_status={
                    "rc": rc,
                    "owner": owner_name,
                    "next_step": next_step,
                    "reason": reason,
                    "path": path,
                    "force_raw_reply": bool(issue_override),
                    **({"auth_hint_source": auth_hint_source} if auth_hint_source else {}),
                },
            )
            return
        self._clear_blocked_hold(run_dir)
        if rc == 0:
            item_name = describe_artifact_for_customer(path or next_step, lang)
            if str(lang).lower() == "en":
                msg = f"Got it, I've made some progress. Now working on: {item_name}."
            else:
                msg = f"已经有进展了，我正在帮你处理：{item_name}。"
            self._send_customer_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                stage="advance_success",
                reply_text=msg,
                next_question=_default_next_question(lang),
                ops_status={"rc": rc, "next_step": next_step, "owner": owner, "iterations": iterations},
            )
            return
        detail = short_tail(merged, max_lines=16, max_chars=1400)
        if str(lang).lower() == "en":
            msg = _compose_three_part_reply(
                lang=lang,
                conclusion="Sorry, I ran into an issue while processing your request.",
                plans=["I'm looking into what went wrong and will try to fix it."],
                next_question="Would you like me to keep trying?",
            )
        else:
            msg = _compose_three_part_reply(
                lang=lang,
                conclusion="抱歉，处理过程中遇到了一点问题。",
                plans=["我正在排查原因，会尽快帮你解决。"],
                next_question="需要我继续尝试吗？",
            )
        self._send_customer_reply(
            chat_id=chat_id,
            lang=lang,
            run_dir=run_dir,
            stage="advance_failed",
            reply_text=msg,
            next_question=_default_next_question(lang),
            ops_status={"rc": rc, "stdout_stderr_tail": detail, "parsed": parsed},
        )

    def _allow_auto_advance(self, run_dir: Path) -> bool:
        if self._is_auto_advance_paused(run_dir):
            return False
        session_state = load_support_session_state(run_dir)
        open_q = session_state.get("open_questions")
        if isinstance(open_q, list) and any(str(x).strip() for x in open_q):
            return False
        if self._is_blocked_hold_active(run_dir):
            return False
        prompts = self._collect_prompts(run_dir)
        return (not prompts) or (not any(i.prompt_type == "question" for _p, i in prompts))

    def _is_terminal_status(self, status: str) -> bool:
        return str(status or "").strip().lower() in {
            "pass",
            "failed",
            "error",
            "done",
            "stopped",
            "cancelled",
        }

    def _push_question(self, chat_id: int, run_dir: Path, prompts: list[tuple[Path, PromptItem]], seen_q: list[str]) -> bool:
        for _p, item in prompts:
            if item.prompt_type != "question":
                continue
            if item.rel_prompt_path in seen_q:
                continue
            self._send_prompt(chat_id, run_dir, item, "question")
            seen_q.append(item.rel_prompt_path)
            self.db.update_cursors(chat_id, seen_questions=save_seen(seen_q))
            return True
        return False

    def _dispatch_agents(self, chat_id: int, run_dir: Path, lang: str, prompts: list[tuple[Path, PromptItem]], seen_outbox: list[str]) -> int:
        count = 0
        for _p, item in prompts:
            if item.prompt_type != "agent_request" or not item.recipient:
                continue
            if item.rel_prompt_path in seen_outbox:
                continue
            exist = self.db.get_pending(str(run_dir), item.rel_prompt_path)
            if exist and str(exist.get("status", "")) == "pending":
                continue
            if count >= MAX_AGENT_DISPATCH_PER_TICK:
                break
            try:
                agent = safe_agent_name(item.recipient)
                req_id = f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
                target = safe_relpath(item.target_path)
                req_path = run_dir / "inbox" / agent / "requests" / f"REQ_{req_id}.json"
                notes_tail = ""
                npath = run_dir / "artifacts" / "USER_NOTES.md"
                if npath.exists():
                    notes_tail = short_tail(npath.read_text(encoding="utf-8", errors="replace"), max_lines=20, max_chars=1600)
                summary_tail = ""
                spath = run_dir / "artifacts" / "API_BOT_SUMMARY.md"
                if spath.exists():
                    summary_tail = short_tail(spath.read_text(encoding="utf-8", errors="replace"), max_lines=20, max_chars=1600)
                payload_text = item.raw_text
                if notes_tail:
                    payload_text += "\n\n--- USER_NOTES tail ---\n" + notes_tail + "\n"
                if summary_tail:
                    payload_text += "\n\n--- API_BOT_SUMMARY tail ---\n" + summary_tail + "\n"
                req = {"type": "agent_request", "req_id": req_id, "run_dir": str(run_dir), "prompt_path": item.rel_prompt_path, "target_path": target, "payload": {"text": payload_text, "lang": lang if lang in {"zh", "en"} else DEFAULT_LANG}}
                atomic_write_text(req_path, json.dumps(req, ensure_ascii=False, indent=2) + "\n")
                self.db.upsert_pending(run_dir=str(run_dir), prompt_path=item.rel_prompt_path, req_id=req_id, agent_name=agent, target_path=target, chat_id=chat_id, status="pending")
                seen_outbox.append(item.rel_prompt_path)
                self.db.update_cursors(chat_id, seen_outbox=save_seen(seen_outbox))
                if str(lang).lower() == "en":
                    self.tg.send(chat_id=chat_id, text=f"Dispatched to internal agent `{agent}`. I will notify you once result is back.")
                else:
                    self.tg.send(chat_id=chat_id, text=f"已安排内部处理 `{agent}`，有结果我会第一时间通知你。")
                count += 1
            except Exception as exc:
                if str(lang).lower() == "en":
                    self.tg.send(chat_id=chat_id, text=f"Agent dispatch failed, switched to manual reply mode: {exc}")
                else:
                    self.tg.send(chat_id=chat_id, text=f"内部处理失败，已切换为人工处理模式：{exc}")
                self._send_prompt(chat_id, run_dir, item, "prompt")
                seen_outbox.append(item.rel_prompt_path)
                self.db.update_cursors(chat_id, seen_outbox=save_seen(seen_outbox))
                count += 1
            if count >= MAX_AGENT_DISPATCH_PER_TICK:
                break
        return count

    def _fallback_agent(self, chat_id: int, run_dir: Path, row: dict[str, Any], reason: str) -> None:
        prompt_rel = str(row.get("prompt_path", "")).strip()
        self.db.del_pending(str(run_dir), prompt_rel)
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        if str(lang).lower() == "en":
            self.tg.send(chat_id=chat_id, text=f"Agent result failed. Switched to manual fill.\n{reason}")
        else:
            self.tg.send(chat_id=chat_id, text=f"代理返回异常，已切换为人工补充。\n{reason}")
        if not prompt_rel:
            return
        try:
            p = run_dir / safe_relpath(prompt_rel)
        except Exception:
            return
        if not p.exists():
            return
        item = parse_outbox_prompt(run_dir, p)
        if item:
            self._send_prompt(chat_id, run_dir, item, "prompt")

    def _consume_results(self, chat_id: int, run_dir: Path) -> int:
        done = 0
        for row in self.db.list_pending(str(run_dir)):
            try:
                agent = safe_agent_name(str(row.get("agent_name", "")))
                req_id = str(row.get("req_id", "")).strip()
                if not req_id:
                    raise ValueError("missing req_id")
            except Exception as exc:
                self._fallback_agent(chat_id, run_dir, row, str(exc))
                continue
            rpath = run_dir / "inbox" / agent / "results" / f"REQ_{req_id}.json"
            if not rpath.exists():
                continue
            try:
                doc = json.loads(rpath.read_text(encoding="utf-8", errors="replace"))
                if str(doc.get("type", "")) != "agent_result":
                    raise ValueError("type must be agent_result")
                if str(doc.get("req_id", "")) != req_id:
                    raise ValueError("req_id mismatch")
                status = str(doc.get("status", "")).strip().lower()
                if status not in {"ok", "error"}:
                    raise ValueError("status must be ok|error")
                req_target = safe_relpath(str(row.get("target_path", "")))
                res_target = safe_relpath(str(doc.get("target_path", "")))
                if req_target != res_target:
                    raise ValueError("target_path mismatch")
                if status == "error":
                    raise ValueError(str(doc.get("log", "")).strip() or "agent returned status=error")
                target_abs = ensure_within_run_dir(run_dir, req_target)
                mode = str(doc.get("write_mode", "")).strip().lower()
                if mode == "inline_text":
                    content = str(doc.get("content", ""))
                    if not content.endswith("\n"):
                        content += "\n"
                    atomic_write_text(target_abs, content)
                elif mode == "payload_path":
                    payload_rel = safe_relpath(str(doc.get("payload_path", "")))
                    payload_abs = ensure_within_run_dir(run_dir, payload_rel)
                    if not payload_abs.exists() or not payload_abs.is_file():
                        raise ValueError(f"payload_path not found: {payload_rel}")
                    atomic_write_bytes(target_abs, payload_abs.read_bytes())
                else:
                    raise ValueError("write_mode must be inline_text|payload_path")
            except Exception as exc:
                self._fallback_agent(chat_id, run_dir, row, str(exc))
                continue
            self.db.del_pending(str(run_dir), str(row.get("prompt_path", "")))
            lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
            if str(lang).lower() == "en":
                self.tg.send(chat_id=chat_id, text="Internal agent result received and applied.")
            else:
                self.tg.send(chat_id=chat_id, text="已收到处理结果，已自动更新到对应位置。")
            done += 1
            if self.cfg.auto_advance and self._allow_auto_advance(run_dir):
                self._advance_once(chat_id, run_dir, 1)
        return done

    def _push_normals(self, chat_id: int, run_dir: Path, prompts: list[tuple[Path, PromptItem]], seen_outbox: list[str]) -> int:
        sent = 0
        for _p, item in prompts:
            if item.prompt_type == "question":
                continue
            if item.prompt_type == "agent_request" and item.recipient:
                continue
            if item.rel_prompt_path in seen_outbox:
                continue
            self._send_prompt(chat_id, run_dir, item, "prompt")
            seen_outbox.append(item.rel_prompt_path)
            sent += 1
            if sent >= MAX_OUTBOX_PUSH_PER_TICK:
                break
        if sent:
            self.db.update_cursors(chat_id, seen_outbox=save_seen(seen_outbox))
        return sent

    def _push_bundle_if_new(self, chat_id: int, run_dir: Path, session: dict[str, Any]) -> None:
        bundle = run_dir / "failure_bundle.zip"
        if not bundle.exists():
            return
        mtime = bundle.stat().st_mtime
        last = float(session.get("last_bundle_mtime", 0.0) or 0.0)
        if mtime <= last:
            return
        self._send_bundle(chat_id, run_dir, True)
        self.db.update_cursors(chat_id, last_bundle_mtime=mtime)

    def _push_trace_delta(self, chat_id: int, run_dir: Path, session: dict[str, Any]) -> None:
        if not self.cfg.progress_push_enabled:
            return
        trace = run_dir / "TRACE.md"
        if not trace.exists():
            return
        size = trace.stat().st_size
        offset = int(session.get("trace_offset", 0) or 0)
        if offset < 0 or offset > size:
            offset = 0
        if size <= offset:
            return
        with trace.open("rb") as f:
            f.seek(offset)
            delta = f.read().decode("utf-8", errors="replace")
        lines = [x for x in delta.splitlines() if x.strip()]
        if len(lines) < 4 and len(delta) < 240:
            return
        now_ts = time.time()
        cool = float(session.get("cooldown_ts", 0.0) or 0.0)
        if now_ts - cool < TRACE_COOLDOWN_SECONDS:
            return
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        self._send_customer_reply(
            chat_id=chat_id,
            lang=lang,
            run_dir=run_dir,
            stage="trace_progress_push",
            reply_text=_humanize_trace_delta(delta, lang),
            next_question=_default_next_question(lang),
            ops_status={"trace_delta_tail": short_tail(delta, max_lines=20, max_chars=1800)},
        )
        self.db.update_cursors(chat_id, trace_offset=size, cooldown_ts=now_ts)

    def _scan_push(self, chat_id: int, run_dir: Path, allow_auto_advance: bool = True) -> dict[str, int]:
        s = self.db.get_session(chat_id)
        lang = str(s.get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        done = self._consume_results(chat_id, run_dir)
        prompts = self._collect_prompts(run_dir)
        seen_outbox = load_seen(str(s.get("seen_outbox", "[]")))
        seen_q = load_seen(str(s.get("seen_questions", "[]")))
        if self._push_question(chat_id, run_dir, prompts, seen_q):
            return {"questions": 1, "agent_dispatch": 0, "normal": 0, "agent_results": done}
        dispatch = self._dispatch_agents(chat_id, run_dir, lang, prompts, seen_outbox)
        if dispatch > 0:
            return {"questions": 0, "agent_dispatch": dispatch, "normal": 0, "agent_results": done}
        normal = self._push_normals(chat_id, run_dir, prompts, seen_outbox)
        self._push_bundle_if_new(chat_id, run_dir, s)
        self._push_trace_delta(chat_id, run_dir, s)
        if allow_auto_advance and self.cfg.auto_advance:
            run_status = self._run_status(run_dir)
            pending_now = self._collect_prompts(run_dir)
            if (
                not self._is_terminal_status(run_status)
                and str(run_status).strip().lower() != "blocked"
                and self._allow_auto_advance(run_dir)
                and not pending_now
            ):
                self._advance_once(chat_id, run_dir, AUTO_ADVANCE_STEPS_PER_TICK)
                # One extra scan so newly produced prompts/results are pushed immediately.
                s2 = self.db.get_session(chat_id)
                self._push_bundle_if_new(chat_id, run_dir, s2)
                self._push_trace_delta(chat_id, run_dir, s2)
        return {"questions": 0, "agent_dispatch": 0, "normal": normal, "agent_results": done}

    def run_tick(self) -> None:
        for s in self.db.list_bound_sessions():
            chat_id = int(s["chat_id"])
            if not self.allowed(chat_id):
                continue
            run_dir = Path(str(s.get("run_dir", "")).strip()).expanduser().resolve()
            if run_dir.exists():
                if self._is_auto_advance_paused(run_dir):
                    continue
                self._scan_push(chat_id, run_dir)

    def _api_route(self, run_dir: Path, lang: str, user_text: str) -> ApiDecision | None:
        if not self.cfg.api_enabled or call_openai_responses is None:
            return None
        prompts = self._collect_prompts(run_dir)
        q = sum(1 for _, i in prompts if i.prompt_type == "question")
        a = sum(1 for _, i in prompts if i.prompt_type == "agent_request" and i.recipient)
        n = len(prompts) - q - a
        notes_tail = ""
        notes = run_dir / "artifacts" / "USER_NOTES.md"
        if notes.exists():
            notes_tail = short_tail(notes.read_text(encoding="utf-8", errors="replace"), max_lines=12, max_chars=800)
        trace_tail = ""
        trace = run_dir / "TRACE.md"
        if trace.exists():
            trace_tail = short_tail(trace.read_text(encoding="utf-8", errors="replace"), max_lines=10, max_chars=1000)
        prompt = (
            "You are a customer service message router. Return JSON only.\n"
            "The user is a CUSTOMER — they may have zero technical knowledge.\n"
            "Speak like a warm, professional customer service agent: acknowledge their concern, help them, and ask one clear follow-up if needed.\n"
            "NEVER use engineering jargon, internal system terms, or assume the customer is technical.\n"
            "If key info is missing, ask at most one clarification question in follow_up.\n"
            "Keys: intent,reply,note,agent_summary,advance_steps,follow_up.\n"
            "intent in: note,status,advance,outbox,bundle,report,decision,lang_zh,lang_en.\n"
            "Use concise, friendly reply. note should be concise summary of customer need. agent_summary <=180 chars.\n"
            f"lang={lang}\n"
            f"user_message:\n{user_text.strip()}\n"
        )
        try:
            text, err = call_openai_responses(prompt=prompt, model=self.cfg.api_model, timeout_sec=self.cfg.api_timeout_sec)  # type: ignore[misc]
            if err:
                return None
            doc = parse_api_json(text)
            if not doc:
                return None
            intent = str(doc.get("intent", "note")).strip().lower()
            if intent not in {"note", "status", "advance", "outbox", "bundle", "report", "decision", "lang_zh", "lang_en"}:
                intent = "note"
            return ApiDecision(
                intent=intent,
                reply=str(doc.get("reply", "")).strip(),
                note=str(doc.get("note", "")).strip(),
                summary=str(doc.get("agent_summary", "")).strip(),
                steps=max(1, min(3, parse_int(str(doc.get("advance_steps", "1")), 1))),
                follow_up=str(doc.get("follow_up", "")).strip(),
            )
        except Exception:
            return None

    def _handle_bound_api(self, chat_id: int, lang: str, run_dir: Path, text: str) -> bool:
        d = self._api_route(run_dir, lang, text)
        if d is None:
            return False
        note = d.note.strip() or text.strip()
        summary = d.summary.strip()
        follow_up_consumed = False
        if len(summary) > 180:
            summary = summary[:180]
        if d.intent == "lang_zh":
            self.db.set_lang(chat_id, "zh")
            self._append_note(run_dir, "telegram/lang zh (api)")
            self._send_customer_reply(
                chat_id=chat_id,
                lang="zh",
                run_dir=run_dir,
                stage="api_lang_zh",
                reply_text=d.reply or _compose_three_part_reply(
                    lang="zh",
                    conclusion="语言已切换为中文。",
                    plans=["后续我会继续用中文和你沟通。"],
                    next_question="还有其他需要我帮忙的吗？",
                ),
                next_question=_default_next_question("zh"),
                ops_status={"intent": d.intent},
            )
        elif d.intent == "lang_en":
            self.db.set_lang(chat_id, "en")
            self._append_note(run_dir, "telegram/lang en (api)")
            self._send_customer_reply(
                chat_id=chat_id,
                lang="en",
                run_dir=run_dir,
                stage="api_lang_en",
                reply_text=d.reply
                or _compose_three_part_reply(
                    lang="en",
                    conclusion="Language switched to English.",
                    plans=["I will continue updates and execution in English."],
                    next_question="Should I keep auto-advancing this run?",
                ),
                next_question=_default_next_question("en"),
                ops_status={"intent": d.intent},
            )
        elif d.intent == "status":
            if d.reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_preface_status",
                    reply_text=d.reply,
                    next_question=_default_next_question(lang),
                    ops_status={"intent": d.intent},
                )
            self._send_status(chat_id, run_dir)
        elif d.intent == "advance":
            self._clear_auto_advance_pause(run_dir)
            self._append_note(run_dir, f"telegram/advance request(api): {text}")
            if d.reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_preface_advance",
                    reply_text=d.reply,
                    next_question=_default_next_question(lang),
                    ops_status={"intent": d.intent},
                )
            self._advance_once(chat_id, run_dir, d.steps)
            self._scan_push(chat_id, run_dir, allow_auto_advance=False)
        elif d.intent == "outbox":
            if d.reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_preface_outbox",
                    reply_text=d.reply,
                    next_question=_default_next_question(lang),
                    ops_status={"intent": d.intent},
                )
            stats = self._scan_push(chat_id, run_dir)
            if stats["questions"] + stats["agent_dispatch"] + stats["normal"] + stats["agent_results"] == 0:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_no_pending_input",
                    reply_text=_compose_three_part_reply(
                        lang=lang,
                        conclusion="当前没有待确认事项。",
                        plans=["我会继续帮你处理下一步。"],
                        next_question="还有其他需要我帮忙的吗？",
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"intent": d.intent},
                )
        elif d.intent == "bundle":
            if d.reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_preface_bundle",
                    reply_text=d.reply,
                    next_question=_default_next_question(lang),
                    ops_status={"intent": d.intent},
                )
            self._send_bundle(chat_id, run_dir, True)
        elif d.intent == "report":
            if d.reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_preface_report",
                    reply_text=d.reply,
                    next_question=_default_next_question(lang),
                    ops_status={"intent": d.intent},
                )
            self._send_verify(chat_id, run_dir)
        elif d.intent == "decision":
            if d.reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_preface_decision",
                    reply_text=d.reply,
                    next_question=_default_next_question(lang),
                    ops_status={"intent": d.intent},
                )
            self._send_customer_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                stage="api_decision",
                reply_text=self._decision_text(run_dir, lang),
                next_question=_default_next_question(lang),
                ops_status={"intent": d.intent},
            )
        else:
            current_state = load_support_session_state(run_dir)
            chat_reply = d.reply or smalltalk_reply(text, lang, current_state) or build_employee_note_reply(
                note,
                lang,
                collab_role=str(current_state.get("collab_role", "support_lead")),
            )
            if chat_reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_note_reply",
                    reply_text=chat_reply,
                    next_question=d.follow_up or _default_next_question(lang),
                    ops_status={"intent": d.intent, "source_text": text},
                )
                follow_up_consumed = bool(str(d.follow_up or "").strip())
            p = self._append_note(run_dir, f"telegram/note {note}")
            if self.cfg.note_ack_path:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="api_note_saved_ack",
                    reply_text=(
                        "Noted, I've saved that and factored it into the next step."
                        if str(lang).lower() == "en"
                        else "记下了，已带入下一步。"
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"notes_path": p.relative_to(run_dir).as_posix()},
                )
        if d.follow_up and not follow_up_consumed:
            self._send_customer_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                stage="api_follow_up",
                reply_text=d.follow_up,
                next_question=_default_next_question(lang),
                ops_status={"intent": d.intent},
            )
        if summary:
            self._append_summary(run_dir, text, summary, d.intent)
        return True

    def _handle_bound_fallback(self, chat_id: int, lang: str, run_dir: Path, text: str) -> None:
        intent, val = detect_intent(text)
        if intent == "lang":
            nxt = val if val in {"zh", "en"} else lang
            self.db.set_lang(chat_id, nxt)
            self._append_note(run_dir, f"telegram/lang {nxt}")
            self._send_customer_reply(
                chat_id=chat_id,
                lang=nxt,
                run_dir=run_dir,
                stage="fallback_lang_switch",
                reply_text=_compose_three_part_reply(
                    lang=nxt,
                    conclusion=("Language switched." if nxt == "en" else "语言已切换。"),
                    plans=[("I will continue in this language." if nxt == "en" else "后续我会继续用这个语言和你沟通。")],
                    next_question=("Is there anything else I can help with?" if nxt == "en" else "还有其他需要我帮忙的吗？"),
                ),
                next_question=_default_next_question(nxt),
                ops_status={"intent": intent, "lang": nxt},
            )
        elif intent == "debug":
            self._send_status(chat_id, run_dir)
        elif intent == "status":
            self._send_status(chat_id, run_dir)
        elif intent == "advance":
            self._clear_auto_advance_pause(run_dir)
            self._append_note(run_dir, f"telegram/advance request: {text}")
            self._advance_once(chat_id, run_dir, 1)
            self._scan_push(chat_id, run_dir, allow_auto_advance=False)
        elif intent == "bundle":
            self._send_bundle(chat_id, run_dir, True)
        elif intent == "report":
            self._send_verify(chat_id, run_dir)
        elif intent == "decision":
            self._send_customer_reply(
                chat_id=chat_id,
                lang=lang,
                run_dir=run_dir,
                stage="fallback_decision",
                reply_text=self._decision_text(run_dir, lang),
                next_question=_default_next_question(lang),
                ops_status={"source_text": text},
            )
        elif intent == "outbox":
            stats = self._scan_push(chat_id, run_dir)
            if stats["questions"] + stats["agent_dispatch"] + stats["normal"] + stats["agent_results"] == 0:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="fallback_no_pending_input",
                    reply_text=(
                        "Nothing pending right now — I'm still running in the background."
                        if str(lang).lower() == "en"
                        else "目前没有待确认的事项，我会继续帮你处理。"
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"source_text": text},
                )
        else:
            chat_reply = smalltalk_reply(text, lang, load_support_session_state(run_dir))
            if chat_reply:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="smalltalk_reply",
                    reply_text=chat_reply,
                    next_question=_default_next_question(lang),
                    ops_status={"source_text": text},
                )
            else:
                current_state = load_support_session_state(run_dir)
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="note_reply",
                    reply_text=build_employee_note_reply(
                        text,
                        lang,
                        collab_role=str(current_state.get("collab_role", "support_lead")),
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"source_text": text},
                )
                p = self._append_note(run_dir, f"telegram/note {text}")
                if self.cfg.note_ack_path:
                    self._send_customer_reply(
                        chat_id=chat_id,
                        lang=lang,
                        run_dir=run_dir,
                        stage="note_saved_ack",
                        reply_text=_compose_three_part_reply(
                            lang=lang,
                            conclusion="我已记录你的补充信息。",
                            plans=["信息已记录，我会继续帮你处理。"],
                            next_question="还有其他需要补充的吗？",
                        ),
                        next_question=_default_next_question(lang),
                        ops_status={"notes_path": p.relative_to(run_dir).as_posix()},
                    )

    def _handle_cb(self, query: dict[str, Any]) -> None:
        msg = query.get("message", {}) or {}
        chat_id = int((msg.get("chat", {}) or {}).get("id", 0))
        if not self.allowed(chat_id):
            return
        cb_id = str(query.get("id", ""))
        data = str(query.get("data", "")).strip()
        if data.startswith("fb:"):
            action = data.split(":", 1)[1].strip().lower()
            s = self.db.get_session(chat_id)
            lang = str(s.get("lang", DEFAULT_LANG) or DEFAULT_LANG)
            run_dir = self._require_run(chat_id, lang)
            if run_dir is None:
                self.tg.answer_cb(cb_id, text="run not bound")
                return
            if action == "retry":
                self._clear_auto_advance_pause(run_dir)
                self._append_note(run_dir, "telegram/failure_action retry")
                self._advance_once(chat_id, run_dir, 1)
                self._scan_push(chat_id, run_dir, allow_auto_advance=False)
                self.tg.answer_cb(cb_id, text="retry triggered")
                return
            if action == "stop":
                self._append_note(run_dir, "telegram/failure_action stop")
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="failure_action_stop",
                    reply_text=_compose_three_part_reply(
                        lang=lang,
                        conclusion="我已记录你的暂停指令。",
                        plans=["处理会先暂停，等待你的下一步指示。"],
                        next_question="你希望我什么时候继续？",
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"action": action},
                )
                self.tg.answer_cb(cb_id, text="stop recorded")
                return
            if action == "relax":
                ap = run_dir / "artifacts" / "answers" / "RELAX_LIMITS.md"
                append_text(ap, f"- {now_iso()} | chat_id={chat_id} | relax_limits\n")
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="failure_action_relax",
                    reply_text=_compose_three_part_reply(
                        lang=lang,
                        conclusion="我已记录你放宽限制的请求。",
                        plans=["我会按新的要求继续帮你处理。"],
                        next_question="确认后我继续帮你处理可以吗？",
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"action": action, "answer_path": ap.relative_to(run_dir).as_posix()},
                )
                self.tg.answer_cb(cb_id, text="relax recorded")
                return
            self.tg.answer_cb(cb_id, text="unknown action")
            return
        msg_id = int(msg.get("message_id", 0))
        mapping = self.db.get_map(chat_id, msg_id)
        if not mapping:
            self.tg.answer_cb(cb_id, text="No active prompt mapping.")
            return
        if not data.startswith("q:"):
            self.tg.answer_cb(cb_id, text="Unsupported callback.")
            return
        try:
            idx = int(data.split(":", 1)[1])
            options = json.loads(str(mapping.get("options_json", "[]")))
            if not isinstance(options, list) or idx < 0 or idx >= len(options):
                raise ValueError("invalid option index")
            choice = str(options[idx]).strip()
            if not choice:
                raise ValueError("empty option")
        except Exception:
            self.tg.answer_cb(cb_id, text="Invalid option.")
            return
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        self._write_reply(chat_id=chat_id, lang=lang, mapping=mapping, text=choice, file_id=None)
        try:
            old = str(msg.get("text", ""))
            if old:
                self.tg.edit(chat_id=chat_id, msg_id=msg_id, text=f"{old}\n\nSelected: {choice}")
        except Exception:
            pass
        self.tg.answer_cb(cb_id, text=f"Selected: {choice}")

    def _handle_command(self, chat_id: int, lang: str, text: str) -> None:
        parts = text.strip().split(maxsplit=1)
        cmd = parts[0].split("@", 1)[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""
        if cmd in {"/start", "/help"}:
            self.tg.send(chat_id=chat_id, text=i18n(lang, "help"))
            return
        if cmd == "/reset":
            self.db.clear_run(chat_id)
            self.tg.send(chat_id=chat_id, text="session reset; send a new goal to start another run.")
            return
        if cmd == "/new":
            self._create_run(chat_id, lang, arg)
            return
        run_dir = self._require_run(chat_id, lang)
        if run_dir is None:
            return
        if cmd == "/status":
            self._send_status(chat_id, run_dir)
        elif cmd == "/debug":
            self._send_status(chat_id, run_dir)
        elif cmd == "/advance":
            self._clear_auto_advance_pause(run_dir)
            n = parse_int(arg or "1", 1)
            self._advance_once(chat_id, run_dir, n)
            self._scan_push(chat_id, run_dir, allow_auto_advance=False)
        elif cmd == "/outbox":
            stats = self._scan_push(chat_id, run_dir)
            if stats["questions"] + stats["agent_dispatch"] + stats["normal"] + stats["agent_results"] == 0:
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="command_no_pending_input",
                    reply_text=_compose_three_part_reply(
                        lang=lang,
                        conclusion="当前没有新的待确认事项。",
                        plans=["我会继续帮你处理。"],
                        next_question="还有其他需要我帮忙的吗？",
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"command": "/outbox"},
                )
        elif cmd == "/get":
            if not arg:
                self.tg.send(chat_id=chat_id, text="/get <relpath>")
            else:
                self._send_file(chat_id, lang, run_dir, arg, arg)
        elif cmd == "/bundle":
            self._send_bundle(chat_id, run_dir, True)
        elif cmd == "/lang":
            val = arg.lower()
            if val not in {"zh", "en"}:
                self.tg.send(chat_id=chat_id, text="/lang zh|en")
            else:
                self.db.set_lang(chat_id, val)
                self._append_note(run_dir, f"telegram/lang {val}")
                self.tg.send(chat_id=chat_id, text=f"language={val}")
        elif cmd == "/note":
            if not arg:
                self.tg.send(chat_id=chat_id, text="/note <text>")
            else:
                self._clear_blocked_hold(run_dir)
                p = self._append_note(run_dir, f"telegram/note {arg}")
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="command_note_saved",
                    reply_text=_compose_three_part_reply(
                        lang=lang,
                        conclusion="我已记录这条备注。",
                        plans=["已记录，我会继续帮你处理。"],
                        next_question="还有其他需要补充的吗？",
                    ),
                    next_question=_default_next_question(lang),
                    ops_status={"command": "/note", "notes_path": p.relative_to(run_dir).as_posix()},
                )
        else:
            self.tg.send(chat_id=chat_id, text=i18n(lang, "help"))

    def _handle_message(self, msg: dict[str, Any]) -> None:
        chat_id = int((msg.get("chat", {}) or {}).get("id", 0))
        if not self.allowed(chat_id):
            return
        s = self.db.get_session(chat_id)
        lang = str(s.get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        reply_to = msg.get("reply_to_message", {}) or {}
        if reply_to:
            mapping = self.db.get_map(chat_id, int(reply_to.get("message_id", 0)))
            if mapping:
                text = msg.get("text")
                file_id = str((msg.get("document", {}) or {}).get("file_id", "")).strip() or None
                if text is None and file_id is None:
                    self.tg.send(chat_id=chat_id, text="请回复文本或 document 文件。")
                    return
                self._write_reply(chat_id=chat_id, lang=lang, mapping=mapping, text=str(text) if text is not None else None, file_id=file_id)
                return
        text = str(msg.get("text", "")).strip()
        if text.startswith("/"):
            self._handle_command(chat_id, lang, text)
            return
        run_raw = str(s.get("run_dir", "")).strip()
        if not run_raw:
            if text:
                if is_smalltalk_only_message(text):
                    base_state = default_support_session_state()
                    role = "team_manager" if is_team_manager_role_request(text) else str(base_state.get("collab_role", "support_lead"))
                    self.tg.send(
                        chat_id=chat_id,
                        text=smalltalk_reply(text, lang, base_state)
                        or build_employee_note_reply(text, lang, collab_role=role),
                    )
                    return
                direct_intent, _ = detect_intent(text)
                if direct_intent == "cancel_run":
                    self.tg.send(
                        chat_id=chat_id,
                        text=(
                            "当前没有进行中的项目需要清理。你发我一个新目标，我就从零开始。"
                            if str(lang).lower() != "en"
                            else "There is no active run to clean up. Share your new goal and I will start from scratch."
                        ),
                    )
                elif direct_intent in {"debug", "status", "outbox", "advance", "bundle", "report", "decision"}:
                    self.tg.send(
                        chat_id=chat_id,
                        text=(
                            "当前还没有进行中的项目。你发我一个明确目标，我就马上开始。"
                            if str(lang).lower() != "en"
                            else "There is no active run yet. Share a clear goal and I will start immediately."
                        ),
                    )
                else:
                    self._create_run(chat_id, lang, text)
            else:
                self.tg.send(chat_id=chat_id, text=i18n(lang, "need_run"))
            return
        run_dir = Path(run_raw).expanduser().resolve()
        if not run_dir.exists():
            self.db.clear_run(chat_id)
            self.tg.send(chat_id=chat_id, text="当前会话已失效，请发一个新目标重新开始。")
            return
        if msg.get("document"):
            self.tg.send(chat_id=chat_id, text="请先回复我上一条待确认消息，再上传文件。")
            return
        if text:
            if looks_like_new_goal(text) and not is_explicit_continuation_request(text):
                self._hard_reset_old_support_state(
                    chat_id=chat_id,
                    run_dir=run_dir,
                    reason="new_goal_intake_reset",
                    purge_records=True,
                )
                self._create_run(chat_id, lang, text)
                return
            direct_intent, _ = detect_intent(text)
            if direct_intent == "cancel_run":
                if self._handle_support_turn(chat_id, lang, run_dir, text):
                    return
                return
            if direct_intent == "note":
                if is_smalltalk_only_message(text):
                    state = load_support_session_state(run_dir)
                    chat_reply = smalltalk_reply(text, lang, state)
                    if chat_reply:
                        self._set_auto_advance_pause(run_dir, seconds=180.0)
                        self._append_support_inbox(run_dir, "user", text, lang)
                        payload = self._send_customer_reply(
                            chat_id=chat_id,
                            lang=lang,
                            run_dir=run_dir,
                            stage="smalltalk_fast_path",
                            reply_text=chat_reply,
                            next_question="",
                            ops_status={"source_text": text, "intent": "smalltalk"},
                        )
                        self._append_support_inbox(run_dir, "assistant", str(payload.get("reply_text", "")), lang)
                        return
                if self._handle_support_turn(chat_id, lang, run_dir, text):
                    return
            if direct_intent == "decision":
                self._send_customer_reply(
                    chat_id=chat_id,
                    lang=lang,
                    run_dir=run_dir,
                    stage="decision_reply",
                    reply_text=self._decision_text(run_dir, lang),
                    next_question="你是否现在就要我先处理这项决策？" if str(lang).lower() != "en" else "Should I prioritize this decision now?",
                    ops_status={"source_text": text},
                )
                return
            if direct_intent == "debug":
                self._send_status(chat_id, run_dir)
                return
            if self._handle_bound_api(chat_id, lang, run_dir, text):
                return
            self._handle_bound_fallback(chat_id, lang, run_dir, text)

    def process_update(self, upd: dict[str, Any]) -> None:
        if "callback_query" in upd:
            self._handle_cb(upd.get("callback_query", {}) or {})
            return
        if "message" in upd:
            self._handle_message(upd.get("message", {}) or {})

    def run_forever(self) -> None:
        offset = self.db.get_offset()
        last_tick = 0.0
        poll_error_streak = 0
        while True:
            now = time.time()
            if now - last_tick >= float(self.cfg.tick_seconds):
                try:
                    self.run_tick()
                except Exception as exc:
                    print(f"[telegram_cs_bot] tick error: {exc}", file=sys.stderr)
                last_tick = now
            try:
                updates = self.tg.updates(offset=offset, timeout=self.cfg.poll_seconds)
                poll_error_streak = 0
            except Exception as exc:
                print(f"[telegram_cs_bot] getUpdates error: {exc}", file=sys.stderr)
                poll_error_streak = min(poll_error_streak + 1, 6)
                time.sleep(min(2 ** poll_error_streak, 20))
                continue
            max_seen = offset
            for upd in updates:
                try:
                    self.process_update(upd)
                except Exception as exc:
                    print(f"[telegram_cs_bot] update error: {exc}", file=sys.stderr)
                uid = int(upd.get("update_id", 0))
                if uid >= max_seen:
                    max_seen = uid + 1
            if max_seen != offset:
                offset = max_seen
                self.db.set_offset(offset)


def main() -> int:
    bot = Bot(Config.load())
    try:
        bot.run_forever()
    finally:
        bot.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
