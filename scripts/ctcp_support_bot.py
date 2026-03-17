#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

PROMPT_TEMPLATE_PATH = ROOT / "agents" / "prompts" / "support_lead_reply.md"
SUPPORT_INBOX_REL_PATH = Path("artifacts") / "support_inbox.jsonl"
SUPPORT_PROMPT_REL_PATH = Path("artifacts") / "support_prompt_input.md"
SUPPORT_REPLY_PROVIDER_REL_PATH = Path("artifacts") / "support_reply.provider.json"
SUPPORT_REPLY_REL_PATH = Path("artifacts") / "support_reply.json"
SUPPORT_SESSION_STATE_REL_PATH = Path("artifacts") / "support_session_state.json"
SUPPORT_PUBLIC_DELIVERY_REL_PATH = Path("artifacts") / "support_public_delivery.json"
SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH = Path("artifacts") / "support_scaffold_materialization.json"
SUPPORT_EXPORTS_REL_DIR = Path("artifacts") / "support_exports"
DISPATCH_CONFIG_REL_PATH = Path("artifacts") / "dispatch_config.json"
SUPPORT_SCAFFOLD_STDOUT_REL_PATH = Path("logs") / "support_scaffold.stdout.log"
SUPPORT_SCAFFOLD_STDERR_REL_PATH = Path("logs") / "support_scaffold.stderr.log"
SUPPORT_SCAFFOLD_PROFILE = "standard"
SUPPORT_SCAFFOLD_SOURCE_MODE = "live-reference"
CTCP_SCAFFOLD_STRUCTURE_HINT = [
    "README.md",
    "docs/",
    "meta/",
    "scripts/",
    "workflow_registry/",
    "simlab/",
]

KNOWN_PROVIDERS = {"manual_outbox", "ollama_agent", "api_agent", "codex_agent", "mock_agent", "local_exec"}
PRIMARY_SUPPORT_PROVIDER = "api_agent"
LOCAL_SUPPORT_REPLY_PROVIDERS = ("ollama_agent",)
SUPPORT_REPLY_PROVIDERS = (PRIMARY_SUPPORT_PROVIDER,) + LOCAL_SUPPORT_REPLY_PROVIDERS
FORBIDDEN_REPLY_PATTERNS = (
    "trace.md",
    "trace:",
    "logs/",
    "logs\\",
    "stdout",
    "stderr",
    "outbox/",
    "outbox\\",
    "diff --git",
    "stack trace",
    "run_dir",
    "failure_bundle.zip",
)

SMALLTALK_PATTERNS_ZH = (
    re.compile(r"^\s*(你好|您好|嗨|哈喽|在吗|早上好|下午好|晚上好|谢谢|辛苦了)\s*[!！。.\?？]*\s*$"),
)
SMALLTALK_PATTERNS_EN = (
    re.compile(r"^\s*(hi|hello|hey|thanks|thank you)\s*[!.\?]*\s*$", re.IGNORECASE),
)
GREETING_PATTERNS_ZH = (
    re.compile(r"^\s*(你好|您好|嗨|哈喽|在吗|早上好|下午好|晚上好)\s*[!！。.\?？]*\s*$"),
)
GREETING_PATTERNS_EN = (
    re.compile(r"^\s*(hi|hello|hey)\s*[!.\?]*\s*$", re.IGNORECASE),
)
LOW_SIGNAL_PROJECT_REPLY_PATTERNS = (
    re.compile(r"^\s*(没有|没|暂无|暂时没有)\s*([，,。.!！ ]*(你)?\s*先\s*(做着?|继续|推进|开始))?\s*[吧吗呀呢]?\s*$"),
    re.compile(r"^\s*((你)?\s*先\s*(做着?|继续|推进|开始)|继续|先继续|先推进|先这样|就这样|可以|好的|好|行|嗯+)\s*[，,。.!！ ]*(吧|呀|呢|吗)?\s*$"),
    re.compile(r"^\s*(no|not yet|none yet|go ahead|keep going|continue|start first|you start)\s*[!.,? ]*\s*$", re.IGNORECASE),
)
PROJECT_GOAL_HINTS_ZH = ("项目", "剧情", "故事", "设定", "分支", "脚本", "游戏", "视觉小说", "VN", "vn", "角色", "世界观")
PROJECT_GOAL_HINTS_EN = (
    "project",
    "storyline",
    "story",
    "setting",
    "branch",
    "script",
    "game",
    "visual novel",
    "vn",
    "character",
    "worldbuilding",
)
IMPLEMENTATION_CONSTRAINT_HINTS_ZH = (
    "windows",
    "window开发",
    "qt",
    "qt6",
    "ui",
    "界面",
    "桌面",
    "平台",
    "框架",
    "技术栈",
    "c++",
    "python",
    "数据库",
    "前端",
    "后端",
)
IMPLEMENTATION_CONSTRAINT_HINTS_EN = (
    "windows",
    "qt",
    "qt6",
    "ui",
    "desktop",
    "platform",
    "framework",
    "tech stack",
    "c++",
    "python",
    "database",
    "frontend",
    "backend",
)
PROJECT_EXECUTION_FOLLOWUP_HINTS_ZH = (
    "先开始做",
    "先开始吧",
    "先做",
    "先做出",
    "做出第一版",
    "先出第一版",
    "先出一版",
    "开始做项目",
    "按这个做",
    "你先做",
    "你可以先开始",
    "后面我再补",
    "后面有了我再补",
    "我再调整",
    "后面再调整",
    "继续做",
    "继续推进",
)
PROJECT_EXECUTION_FOLLOWUP_HINTS_EN = (
    "go ahead and start",
    "start the project",
    "make a first draft",
    "make the first draft",
    "make a first version",
    "build the first version",
    "first version",
    "first draft",
    "first pass",
    "you can start first",
    "i'll adjust later",
    "i will adjust later",
    "keep building",
)
NON_PROJECT_SUPPORT_REPLY_MODES = {"GREETING", "SMALLTALK", "CAPABILITY_QUERY", "PROJECT_INTAKE"}
PROJECT_CONTEXT_LEAK_TOKENS_ZH = (
    "项目",
    "开发",
    "原型",
    "第一版",
    "设计",
    "实现",
    "功能模块",
    "需求",
    "方案",
    "架构",
    "部署",
    "框架",
    "代码",
)
PROJECT_CONTEXT_LEAK_TOKENS_EN = (
    "project",
    "prototype",
    "first version",
    "development",
    "implementation",
    "design",
    "feature module",
    "requirement",
    "architecture",
    "deployment",
    "framework",
    "codebase",
)
SUPPORT_AUTO_ADVANCE_INTERVAL_SEC = 20
SUPPORT_PROGRESS_PUSH_IDLE_INTERVAL_SEC = 6
PREVIOUS_OUTLINE_REQUEST_PATTERNS_ZH = (
    re.compile(r"之前.*大纲"),
    re.compile(r"(按|照).*(之前|原来).*(大纲|方案|项目)"),
    re.compile(r"(继续|接着|重做|重新做).*(之前|原来).*(项目|大纲|方案)"),
    re.compile(r"之前想要你做的项目"),
    re.compile(r"之前那个项目"),
)
PREVIOUS_OUTLINE_REQUEST_PATTERNS_EN = (
    re.compile(r"previous outline", re.IGNORECASE),
    re.compile(r"continue .*previous", re.IGNORECASE),
    re.compile(r"redo .*previous", re.IGNORECASE),
    re.compile(r"previous project", re.IGNORECASE),
)
PREVIOUS_PROJECT_STATUS_PATTERNS_ZH = (
    re.compile(r"(之前|原来).*(项目|方案|大纲).*(进度|状态|做到什么程度|做到哪|做到哪一步|做成什么样|做得怎么样|现在怎么样|现在什么情况)"),
    re.compile(r"(之前那个项目|之前的项目|原来的项目).*(做成什么样|做得怎么样|现在怎么样|进度|状态|做到哪|做到什么程度)"),
)
PREVIOUS_PROJECT_STATUS_PATTERNS_EN = (
    re.compile(
        r"\b(previous|earlier|old)\b.{0,24}\b(project|plan|outline)\b.{0,24}\b(status|progress|done|ready|finished|latest)\b",
        re.IGNORECASE,
    ),
)
SCREENSHOT_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
_WHITEBOARD_DISPATCH_RESULT_RE = re.compile(
    r"^(?P<role>[^/\s]+)/(?P<action>[^\s]+)\s+via\s+(?P<provider>[^\s]+)\s+=>\s+(?P<status>[^\s]+)\s+\((?P<target>[^)]+)\)(?:;\s*(?P<reason>.*))?$"
)


try:
    from tools.run_paths import get_repo_slug, get_runs_root
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug, get_runs_root

try:
    from tools.providers import api_agent, codex_agent, manual_outbox, mock_agent, ollama_agent
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.providers import api_agent, codex_agent, manual_outbox, mock_agent, ollama_agent

try:
    import ctcp_dispatch
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import ctcp_dispatch

try:
    import ctcp_front_bridge
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import ctcp_front_bridge

try:
    from frontend.conversation_mode_router import (
        has_sufficient_task_signal as frontend_has_sufficient_task_signal,
        is_capability_query as frontend_is_capability_query,
        is_greeting_only as frontend_is_greeting_only,
        is_status_query as frontend_is_status_query,
        route_conversation_mode as frontend_route_conversation_mode,
    )
    from frontend.response_composer import render_frontend_output
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from frontend.conversation_mode_router import (
        has_sufficient_task_signal as frontend_has_sufficient_task_signal,
        is_capability_query as frontend_is_capability_query,
        is_greeting_only as frontend_is_greeting_only,
        is_status_query as frontend_is_status_query,
        route_conversation_mode as frontend_route_conversation_mode,
    )
    from frontend.response_composer import render_frontend_output
except Exception:
    frontend_has_sufficient_task_signal = None  # type: ignore[assignment]
    frontend_is_capability_query = None  # type: ignore[assignment]
    frontend_is_greeting_only = None  # type: ignore[assignment]
    frontend_is_status_query = None  # type: ignore[assignment]
    frontend_route_conversation_mode = None  # type: ignore[assignment]
    render_frontend_output = None  # type: ignore[assignment]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_iso_ts(text: str) -> dt.datetime | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def seconds_since(text: str) -> float | None:
    stamp = parse_iso_ts(text)
    if stamp is None:
        return None
    now = dt.datetime.now(dt.timezone.utc)
    return max(0.0, (now - stamp.astimezone(dt.timezone.utc)).total_seconds())


def utf8_clean(text: str) -> str:
    return str(text or "").encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def _replacement_char_count(text: str) -> int:
    return str(text or "").count("\ufffd")


def clean_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return utf8_clean(value)
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            out[str(key)] = clean_json_value(item)
        return out
    return value


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(utf8_clean(text), encoding="utf-8")


def write_json(path: Path, doc: dict[str, Any]) -> None:
    write_text(path, json.dumps(clean_json_value(doc), ensure_ascii=False, indent=2) + "\n")


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_row = clean_json_value(row)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(safe_row, ensure_ascii=False) + "\n")


def append_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(utf8_clean(text))


def append_trace(run_dir: Path, text: str) -> None:
    append_log(run_dir / "TRACE.md", f"- {now_iso()} | support_bot: {text}\n")


def append_event(run_dir: Path, event: str, path: str = "", **extra: Any) -> None:
    row: dict[str, Any] = {
        "ts": now_iso(),
        "role": "support_bot",
        "event": event,
        "path": path,
    }
    for key, value in extra.items():
        row[key] = value
    append_jsonl(run_dir / "events.jsonl", row)
    if path:
        append_trace(run_dir, f"{event} ({path})")
    else:
        append_trace(run_dir, event)


def ensure_external_run_dir(run_dir: Path) -> None:
    try:
        run_dir.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return
    raise SystemExit(f"[ctcp_support_bot] run_dir must be outside repo root: {run_dir}")


def safe_session_id(chat_id: str | int) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(chat_id).strip())
    value = value.strip("-.")
    return value or "session"


def session_run_dir(chat_id: str | int) -> Path:
    run_dir = (get_runs_root() / get_repo_slug(ROOT) / "support_sessions" / safe_session_id(chat_id)).resolve()
    ensure_external_run_dir(run_dir)
    return run_dir


def ensure_layout(run_dir: Path) -> None:
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "outbox").mkdir(parents=True, exist_ok=True)


def default_support_dispatch_config() -> dict[str, Any]:
    return {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": "manual_outbox",
        "role_providers": {
            "support_lead": PRIMARY_SUPPORT_PROVIDER,
            "support_local_fallback": LOCAL_SUPPORT_REPLY_PROVIDERS[0],
            "patchmaker": "codex_agent",
            "fixer": "codex_agent",
        },
        "budgets": {"max_outbox_prompts": 20},
        "providers": {
            "codex_agent": {
                "enabled": False,
                "dry_run": True,
                "cmd": "codex",
                "model": "",
                "timeout_sec": 900,
                "fallback_to_manual_outbox": True,
            },
            "ollama_agent": {
                "base_url": "http://127.0.0.1:11434/v1",
                "api_key": "ollama",
                "model": "qwen2.5:7b-instruct",
                "auto_start": True,
                "start_timeout_sec": 20,
                "start_cmd": "ollama serve",
            },
        },
    }


def ensure_dispatch_config(run_dir: Path) -> Path:
    path = run_dir / DISPATCH_CONFIG_REL_PATH
    if not path.exists():
        write_json(path, default_support_dispatch_config())
    return path


def load_dispatch_config(run_dir: Path) -> tuple[dict[str, Any], str]:
    ensure_dispatch_config(run_dir)
    cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)
    if cfg is None:
        fallback = default_support_dispatch_config()
        write_json(run_dir / DISPATCH_CONFIG_REL_PATH, fallback)
        return fallback, f"fallback_to_default: {msg}"
    return cfg, msg


def resolve_support_provider(config: dict[str, Any], override: str = "") -> str:
    raw_override = str(override or "").strip().lower()
    if raw_override in KNOWN_PROVIDERS:
        return raw_override

    role_map = config.get("role_providers", {})
    if not isinstance(role_map, dict):
        role_map = {}
    provider = str(role_map.get("support_lead", config.get("mode", PRIMARY_SUPPORT_PROVIDER))).strip().lower()
    if provider not in KNOWN_PROVIDERS:
        return PRIMARY_SUPPORT_PROVIDER
    if provider == "local_exec":
        return PRIMARY_SUPPORT_PROVIDER
    if provider not in SUPPORT_REPLY_PROVIDERS:
        return PRIMARY_SUPPORT_PROVIDER
    return provider


def resolve_local_support_fallback(config: dict[str, Any]) -> str:
    role_map = config.get("role_providers", {})
    if not isinstance(role_map, dict):
        role_map = {}
    provider = str(role_map.get("support_local_fallback", "")).strip().lower()
    if provider == "local_exec":
        provider = LOCAL_SUPPORT_REPLY_PROVIDERS[0]
    if provider in LOCAL_SUPPORT_REPLY_PROVIDERS:
        return provider
    return LOCAL_SUPPORT_REPLY_PROVIDERS[0]


def support_provider_candidates(config: dict[str, Any], override: str = "") -> list[str]:
    preferred = resolve_support_provider(config, override=override)
    local_fallback = resolve_local_support_fallback(config)
    ordered: list[str] = []
    strict = str(override or "").strip().lower() in KNOWN_PROVIDERS

    def _add(raw: str) -> None:
        text = str(raw or "").strip().lower()
        if text == "local_exec":
            text = local_fallback
        if text in KNOWN_PROVIDERS and text not in ordered:
            ordered.append(text)

    _add(preferred)
    role_map = config.get("role_providers", {})
    if isinstance(role_map, dict):
        strict = strict or bool(role_map.get("support_lead_strict", False))
    if preferred == PRIMARY_SUPPORT_PROVIDER:
        _add(local_fallback)
        return ordered or [PRIMARY_SUPPORT_PROVIDER, local_fallback]
    if preferred in LOCAL_SUPPORT_REPLY_PROVIDERS:
        return ordered or [local_fallback]
    if strict:
        return ordered or [PRIMARY_SUPPORT_PROVIDER, local_fallback]
    _add(PRIMARY_SUPPORT_PROVIDER)
    _add(local_fallback)
    return ordered or [PRIMARY_SUPPORT_PROVIDER, local_fallback]


def model_unavailable_reply_doc(result: dict[str, Any], *, lang_hint: str = "zh") -> dict[str, Any]:
    reason = sanitize_inline_text(str(result.get("reason", "")), max_chars=180)
    lang = str(lang_hint or "").strip().lower() or "zh"
    had_local = bool(str(result.get("local_provider", "")).strip())
    reason_kind = sanitize_inline_text(str(result.get("api_failure_kind", "")), max_chars=40).lower() or "unavailable"
    if lang == "en":
        if reason_kind == "invalid_reply":
            reply_text = "The API path did not produce a usable reply for this turn."
            if had_local:
                reply_text = "The API path did not produce a usable reply for this turn, and the local fallback is not reachable either."
        else:
            reply_text = "The API reply path is unavailable right now."
            if had_local:
                reply_text = "The API reply path is unavailable right now, and the local fallback is not reachable either."
        next_question = "Reply with \"continue\" and I will retry, or send me the error you are seeing."
    else:
        if reason_kind == "invalid_reply":
            reply_text = "这轮 API 没给到可直接发出的回复。"
            if had_local:
                reply_text = "这轮 API 没给到可直接发出的回复，本地回复也没接上。"
        else:
            reply_text = "现在 API 回复链路没连上。"
            if had_local:
                reply_text = "现在 API 回复链路没连上，本地回复也没接上。"
        next_question = "你回我“继续”我再重试一次，或者把你现在看到的报错发我。"
    return {
        "reply_text": reply_text,
        "next_question": next_question,
        "actions": [{"type": "request_file", "hint": "如有错误日志，可直接上传帮助定位"}],
        "debug_notes": reason or "model_unavailable",
    }


def deferred_support_reply_doc(provider: str, result: dict[str, Any]) -> dict[str, Any]:
    path_hint = sanitize_inline_text(str(result.get("path", "")), max_chars=180)
    notes = f"deferred:{provider}"
    if path_hint:
        notes += f" path={path_hint}"
    return {
        "reply_text": "这个回复通道现在还没给出可直接发出的结果，我先把你这轮内容挂上继续处理。",
        "next_question": "",
        "actions": [{"type": "request_file", "hint": "如果你手上有现成素材、日志或参考样例，可以直接发我"}],
        "debug_notes": notes,
    }


def load_inbox_history(run_dir: Path, limit: int = 8) -> list[dict[str, str]]:
    path = run_dir / SUPPORT_INBOX_REL_PATH
    if not path.exists():
        return []
    rows: list[dict[str, str]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
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
                "ts": str(doc.get("ts", "")).strip(),
                "source": str(doc.get("source", "")).strip() or "unknown",
                "text": str(doc.get("text", "")).strip(),
            }
        )
    return rows[-max(1, limit) :]


def default_support_session_state(chat_id: str) -> dict[str, Any]:
    return {
        "schema_version": "ctcp-support-session-state-v4",
        "chat_id": chat_id,
        "bound_run_id": "",
        "bound_run_dir": "",
        "task_summary": "",
        "latest_conversation_mode": "",
        "last_bridge_sync_ts": "",
        "latest_support_context": {},
        "session_profile": {
            "lang_hint": "",
            "last_source": "",
        },
        "project_memory": {
            "project_brief": "",
            "last_detail_turn": "",
            "last_detail_ts": "",
        },
        "project_constraints_memory": {
            "constraint_brief": "",
            "constraint_ts": "",
        },
        "execution_memory": {
            "latest_user_directive": "",
            "latest_user_directive_ts": "",
        },
        "turn_memory": {
            "latest_user_turn": "",
            "latest_user_turn_ts": "",
            "latest_conversation_mode": "",
            "latest_source": "",
        },
        "provider_runtime_buffer": {
            "preferred_provider": "",
            "attempted_providers": [],
            "last_provider": "",
            "last_provider_status": "",
            "last_provider_reason": "",
        },
        "notification_state": {
            "last_progress_hash": "",
            "last_progress_ts": "",
            "last_notified_run_id": "",
            "last_notified_phase": "",
            "last_auto_advance_ts": "",
        },
        "resume_state": {
            "last_resume_ts": "",
            "last_resume_source_dir": "",
            "last_resume_source_run_id": "",
            "last_resume_brief": "",
            "superseded_run_id": "",
        },
    }


def load_support_session_state(run_dir: Path, chat_id: str) -> dict[str, Any]:
    doc = read_json_doc(run_dir / SUPPORT_SESSION_STATE_REL_PATH)
    return normalize_support_session_state(doc, chat_id)


def save_support_session_state(run_dir: Path, state: dict[str, Any]) -> None:
    write_json(run_dir / SUPPORT_SESSION_STATE_REL_PATH, normalize_support_session_state(state, str(state.get("chat_id", "")).strip()))


def _state_zone(session_state: dict[str, Any], key: str) -> dict[str, Any]:
    zone = session_state.get(key)
    if not isinstance(zone, dict):
        zone = {}
        session_state[key] = zone
    return zone


def current_project_brief(session_state: dict[str, Any]) -> str:
    project_memory = _state_zone(session_state, "project_memory")
    text = str(project_memory.get("project_brief", "")).strip() or str(session_state.get("task_summary", "")).strip()
    return sanitize_inline_text(text, max_chars=280)


def latest_turn_memory(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "turn_memory")


def latest_provider_runtime(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "provider_runtime_buffer")


def latest_notification_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "notification_state")


def latest_resume_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "resume_state")


def normalize_support_session_state(doc: dict[str, Any] | None, chat_id: str) -> dict[str, Any]:
    state = default_support_session_state(chat_id)
    if isinstance(doc, dict):
        for key, value in doc.items():
            if key in {
                "session_profile",
                "project_memory",
                "project_constraints_memory",
                "execution_memory",
                "turn_memory",
                "provider_runtime_buffer",
                "notification_state",
                "resume_state",
                "latest_support_context",
            }:
                if isinstance(value, dict):
                    _state_zone(state, key).update(value)
                continue
            state[key] = value

    state["chat_id"] = chat_id
    project_memory = _state_zone(state, "project_memory")
    project_constraints_memory = _state_zone(state, "project_constraints_memory")
    execution_memory = _state_zone(state, "execution_memory")
    turn_memory = _state_zone(state, "turn_memory")
    session_profile = _state_zone(state, "session_profile")
    provider_runtime = _state_zone(state, "provider_runtime_buffer")
    notification_state = _state_zone(state, "notification_state")
    resume_state = _state_zone(state, "resume_state")
    latest_support_context = state.get("latest_support_context")
    if not isinstance(latest_support_context, dict):
        latest_support_context = {}
    state["latest_support_context"] = latest_support_context

    legacy_summary = sanitize_inline_text(str(state.get("task_summary", "")), max_chars=280)
    if not str(project_memory.get("project_brief", "")).strip() and legacy_summary:
        project_memory["project_brief"] = legacy_summary
    project_memory["project_brief"] = sanitize_inline_text(str(project_memory.get("project_brief", "")), max_chars=280)
    project_memory["last_detail_turn"] = sanitize_inline_text(str(project_memory.get("last_detail_turn", "")), max_chars=280)
    project_memory["last_detail_ts"] = sanitize_inline_text(str(project_memory.get("last_detail_ts", "")), max_chars=40)
    project_constraints_memory["constraint_brief"] = sanitize_inline_text(
        str(project_constraints_memory.get("constraint_brief", "")), max_chars=280
    )
    project_constraints_memory["constraint_ts"] = sanitize_inline_text(
        str(project_constraints_memory.get("constraint_ts", "")), max_chars=40
    )
    execution_memory["latest_user_directive"] = sanitize_inline_text(
        str(execution_memory.get("latest_user_directive", "")), max_chars=280
    )
    execution_memory["latest_user_directive_ts"] = sanitize_inline_text(
        str(execution_memory.get("latest_user_directive_ts", "")), max_chars=40
    )

    turn_memory["latest_user_turn"] = sanitize_inline_text(str(turn_memory.get("latest_user_turn", "")), max_chars=280)
    turn_memory["latest_user_turn_ts"] = sanitize_inline_text(str(turn_memory.get("latest_user_turn_ts", "")), max_chars=40)
    turn_memory["latest_conversation_mode"] = sanitize_inline_text(
        str(turn_memory.get("latest_conversation_mode", state.get("latest_conversation_mode", ""))), max_chars=40
    )
    turn_memory["latest_source"] = sanitize_inline_text(str(turn_memory.get("latest_source", "")), max_chars=40)

    session_profile["lang_hint"] = sanitize_inline_text(str(session_profile.get("lang_hint", "")), max_chars=12)
    session_profile["last_source"] = sanitize_inline_text(str(session_profile.get("last_source", "")), max_chars=40)

    attempted = provider_runtime.get("attempted_providers", [])
    if not isinstance(attempted, list):
        attempted = []
    provider_runtime["preferred_provider"] = sanitize_inline_text(str(provider_runtime.get("preferred_provider", "")), max_chars=40)
    provider_runtime["attempted_providers"] = [
        sanitize_inline_text(str(item), max_chars=40) for item in attempted if str(item).strip()
    ][-6:]
    provider_runtime["last_provider"] = sanitize_inline_text(str(provider_runtime.get("last_provider", "")), max_chars=40)
    provider_runtime["last_provider_status"] = sanitize_inline_text(
        str(provider_runtime.get("last_provider_status", "")), max_chars=40
    )
    provider_runtime["last_provider_reason"] = sanitize_inline_text(
        str(provider_runtime.get("last_provider_reason", "")), max_chars=220
    )
    notification_state["last_progress_hash"] = sanitize_inline_text(
        str(notification_state.get("last_progress_hash", "")), max_chars=80
    )
    notification_state["last_progress_ts"] = sanitize_inline_text(
        str(notification_state.get("last_progress_ts", "")), max_chars=40
    )
    notification_state["last_notified_run_id"] = sanitize_inline_text(
        str(notification_state.get("last_notified_run_id", "")), max_chars=80
    )
    notification_state["last_notified_phase"] = sanitize_inline_text(
        str(notification_state.get("last_notified_phase", "")), max_chars=80
    )
    notification_state["last_auto_advance_ts"] = sanitize_inline_text(
        str(notification_state.get("last_auto_advance_ts", "")), max_chars=40
    )
    resume_state["last_resume_ts"] = sanitize_inline_text(str(resume_state.get("last_resume_ts", "")), max_chars=40)
    resume_state["last_resume_source_dir"] = sanitize_inline_text(
        str(resume_state.get("last_resume_source_dir", "")), max_chars=260
    )
    resume_state["last_resume_source_run_id"] = sanitize_inline_text(
        str(resume_state.get("last_resume_source_run_id", "")), max_chars=80
    )
    resume_state["last_resume_brief"] = sanitize_inline_text(str(resume_state.get("last_resume_brief", "")), max_chars=280)
    resume_state["superseded_run_id"] = sanitize_inline_text(str(resume_state.get("superseded_run_id", "")), max_chars=80)

    state["task_summary"] = current_project_brief(state)
    state["latest_conversation_mode"] = sanitize_inline_text(
        str(turn_memory.get("latest_conversation_mode", state.get("latest_conversation_mode", ""))), max_chars=40
    )
    state["bound_run_id"] = sanitize_inline_text(str(state.get("bound_run_id", "")), max_chars=80)
    state["bound_run_dir"] = sanitize_inline_text(str(state.get("bound_run_dir", "")), max_chars=260)
    state["last_bridge_sync_ts"] = sanitize_inline_text(str(state.get("last_bridge_sync_ts", "")), max_chars=40)
    return state


def set_current_project_brief(session_state: dict[str, Any], text: str) -> None:
    project_memory = _state_zone(session_state, "project_memory")
    project_memory["project_brief"] = sanitize_inline_text(text, max_chars=280)
    session_state["task_summary"] = current_project_brief(session_state)


def set_project_constraints_brief(session_state: dict[str, Any], text: str) -> None:
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    project_constraints["constraint_brief"] = sanitize_inline_text(text, max_chars=280)
    project_constraints["constraint_ts"] = now_iso()


def set_execution_directive(session_state: dict[str, Any], text: str) -> None:
    execution_memory = _state_zone(session_state, "execution_memory")
    execution_memory["latest_user_directive"] = sanitize_inline_text(text, max_chars=280)
    execution_memory["latest_user_directive_ts"] = now_iso()


def record_turn_memory(session_state: dict[str, Any], *, user_text: str, source: str, conversation_mode: str) -> None:
    turn_memory = latest_turn_memory(session_state)
    turn_memory["latest_user_turn"] = sanitize_inline_text(user_text, max_chars=280)
    turn_memory["latest_user_turn_ts"] = now_iso()
    turn_memory["latest_conversation_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)
    turn_memory["latest_source"] = sanitize_inline_text(source, max_chars=40)

    session_profile = _state_zone(session_state, "session_profile")
    session_profile["lang_hint"] = detect_lang_hint(user_text)
    session_profile["last_source"] = sanitize_inline_text(source, max_chars=40)
    session_state["latest_conversation_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)


def record_provider_runtime(
    session_state: dict[str, Any],
    *,
    preferred_provider: str = "",
    attempted_provider: str = "",
    status: str = "",
    reason: str = "",
) -> None:
    provider_runtime = latest_provider_runtime(session_state)
    if preferred_provider:
        provider_runtime["preferred_provider"] = sanitize_inline_text(preferred_provider, max_chars=40)
    if attempted_provider:
        attempted = provider_runtime.get("attempted_providers", [])
        if not isinstance(attempted, list):
            attempted = []
        attempted.append(sanitize_inline_text(attempted_provider, max_chars=40))
        provider_runtime["attempted_providers"] = attempted[-6:]
        provider_runtime["last_provider"] = sanitize_inline_text(attempted_provider, max_chars=40)
    if status:
        provider_runtime["last_provider_status"] = sanitize_inline_text(status, max_chars=40)
    if reason:
        provider_runtime["last_provider_reason"] = sanitize_inline_text(reason, max_chars=220)


def support_active_task_state(session_state: dict[str, Any]) -> dict[str, Any]:
    summary = current_project_brief(session_state)
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    execution_memory = _state_zone(session_state, "execution_memory")
    return {
        "task_summary": summary,
        "user_goal": summary,
        "run_id": sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80),
        "has_bound_run": bool(str(session_state.get("bound_run_id", "")).strip()),
        "project_constraints": sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=280),
        "execution_directive": sanitize_inline_text(str(execution_memory.get("latest_user_directive", "")), max_chars=280),
    }


def is_previous_outline_request(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    if not raw:
        return False
    low = raw.lower()
    return any(p.search(raw) for p in PREVIOUS_OUTLINE_REQUEST_PATTERNS_ZH) or any(
        p.search(low) for p in PREVIOUS_OUTLINE_REQUEST_PATTERNS_EN
    )


def iter_archived_support_session_dirs(chat_id: str, current_run_dir: Path | None = None) -> list[Path]:
    sessions_root = session_run_dir(chat_id).parent
    if not sessions_root.exists():
        return []
    prefix = f"{safe_session_id(chat_id)}.backup-"
    current_resolved = current_run_dir.resolve() if current_run_dir is not None else None
    rows: list[Path] = []
    for path in sessions_root.iterdir():
        if not path.is_dir():
            continue
        if not path.name.startswith(prefix):
            continue
        if current_resolved is not None and path.resolve() == current_resolved:
            continue
        rows.append(path)
    return sorted(rows, key=lambda item: item.stat().st_mtime, reverse=True)


def resolve_archived_resume_candidate(
    *,
    chat_id: str,
    current_run_dir: Path,
    session_state: dict[str, Any],
) -> dict[str, str]:
    current_brief = current_project_brief(session_state)
    for session_dir in iter_archived_support_session_dirs(chat_id, current_run_dir=current_run_dir):
        archived_state = load_support_session_state(session_dir, chat_id)
        archived_brief = current_project_brief(archived_state)
        if not archived_brief:
            continue
        if archived_brief == current_brief:
            continue
        if is_previous_outline_request(archived_brief):
            continue
        return {
            "session_dir": str(session_dir),
            "project_brief": archived_brief,
            "bound_run_id": sanitize_inline_text(str(archived_state.get("bound_run_id", "")), max_chars=80),
        }
    return {}


def latest_resume_request_text(run_dir: Path, session_state: dict[str, Any]) -> str:
    latest_turn = sanitize_inline_text(str(latest_turn_memory(session_state).get("latest_user_turn", "")), max_chars=280)
    if latest_turn and is_previous_outline_request(latest_turn):
        return latest_turn
    execution_directive = sanitize_inline_text(
        str(_state_zone(session_state, "execution_memory").get("latest_user_directive", "")),
        max_chars=280,
    )
    if execution_directive and is_previous_outline_request(execution_directive):
        return execution_directive
    for item in reversed(load_inbox_history(run_dir, limit=12)):
        text = sanitize_inline_text(str(item.get("text", "")), max_chars=280)
        if text and is_previous_outline_request(text):
            return text
    return ""


def should_supersede_bound_run_for_resume(
    *,
    project_context: dict[str, Any] | None,
    current_goal_hint: str,
    recovered_brief: str,
) -> bool:
    current_goal = sanitize_inline_text(
        str(current_goal_hint or (project_context or {}).get("goal", "")),
        max_chars=280,
    )
    recovered = sanitize_inline_text(recovered_brief, max_chars=280)
    if not recovered:
        return False
    if current_goal == recovered:
        return False
    if not current_goal:
        return True
    if is_previous_outline_request(current_goal):
        return True
    status = project_context.get("status", {}) if isinstance(project_context, dict) else {}
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {}) if isinstance(status.get("gate", {}), dict) else {}
    run_status = str(status.get("run_status", "")).strip().lower()
    needs_user_decision = bool(status.get("needs_user_decision", False))
    gate_state = str(gate.get("state", "")).strip().lower()
    return run_status == "blocked" and gate_state == "blocked" and (not needs_user_decision)


def is_greeting_only_message(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    if frontend_is_greeting_only is not None:
        try:
            if frontend_is_greeting_only(raw):
                return True
        except Exception:
            pass
    if any(p.match(raw) for p in GREETING_PATTERNS_ZH):
        return True
    if any(p.match(raw) for p in GREETING_PATTERNS_EN):
        return True
    return False


def is_low_signal_project_followup(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return True
    return any(p.match(raw) for p in LOW_SIGNAL_PROJECT_REPLY_PATTERNS)


def has_project_goal_markers(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    low = raw.lower()
    return any(token in raw for token in PROJECT_GOAL_HINTS_ZH) or any(token in low for token in PROJECT_GOAL_HINTS_EN)


def has_implementation_constraint_markers(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    low = raw.lower()
    return any(token in raw for token in IMPLEMENTATION_CONSTRAINT_HINTS_ZH) or any(
        token in low for token in IMPLEMENTATION_CONSTRAINT_HINTS_EN
    )


def is_project_execution_followup(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    if not raw:
        return False
    if is_low_signal_project_followup(raw):
        return True
    low = raw.lower()
    return any(token in raw for token in PROJECT_EXECUTION_FOLLOWUP_HINTS_ZH) or any(
        token in low for token in PROJECT_EXECUTION_FOLLOWUP_HINTS_EN
    )


def is_previous_project_status_followup(text: str) -> bool:
    raw = sanitize_inline_text(text, max_chars=280)
    if not raw:
        return False
    if frontend_is_status_query is not None:
        try:
            if frontend_is_status_query(raw):
                return True
        except Exception:
            pass
    low = raw.lower()
    return any(pattern.search(raw) for pattern in PREVIOUS_PROJECT_STATUS_PATTERNS_ZH) or any(
        pattern.search(low) for pattern in PREVIOUS_PROJECT_STATUS_PATTERNS_EN
    )


def should_refresh_project_brief(user_text: str, conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw or is_low_signal_project_followup(raw):
        return False
    if is_previous_project_status_followup(raw):
        return False
    if is_project_execution_followup(raw):
        return False
    if not has_project_goal_markers(raw):
        return False
    if frontend_has_sufficient_task_signal is not None:
        try:
            if frontend_has_sufficient_task_signal([raw], threshold=2.0):
                return True
        except Exception:
            pass
    return len(raw) >= 12


def should_capture_project_constraints(user_text: str, conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw or is_low_signal_project_followup(raw) or is_project_execution_followup(raw):
        return False
    if should_refresh_project_brief(raw, mode):
        return False
    return has_implementation_constraint_markers(raw)


def should_force_project_detail(user_text: str, session_state: dict[str, Any]) -> bool:
    if not bool(str(session_state.get("bound_run_id", "")).strip()):
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw or is_greeting_only_message(raw) or is_smalltalk_only_message(raw):
        return False
    return is_project_execution_followup(raw)


def detect_conversation_mode(run_dir: Path, user_text: str, session_state: dict[str, Any]) -> str:
    active_state = support_active_task_state(session_state)
    has_bound_run = bool(str(session_state.get("bound_run_id", "")).strip())
    if frontend_route_conversation_mode is not None:
        try:
            mode = str(frontend_route_conversation_mode([user_text], user_text, active_state)).strip().upper() or "SMALLTALK"
            if has_bound_run and mode in {"PROJECT_INTAKE", "PROJECT_DETAIL"} and is_previous_project_status_followup(user_text):
                return "STATUS_QUERY"
            if mode == "PROJECT_INTAKE" and current_project_brief(session_state) and not should_refresh_project_brief(user_text, mode):
                return "PROJECT_DETAIL"
            if mode == "SMALLTALK" and should_force_project_detail(user_text, session_state):
                return "PROJECT_DETAIL"
            return mode
        except Exception:
            pass
    if is_greeting_only_message(user_text):
        return "GREETING"
    if frontend_is_capability_query is not None:
        try:
            if frontend_is_capability_query(user_text):
                return "CAPABILITY_QUERY"
        except Exception:
            pass
    if is_smalltalk_only_message(user_text):
        return "SMALLTALK"
    if has_bound_run and is_previous_project_status_followup(user_text):
        return "STATUS_QUERY"
    if should_force_project_detail(user_text, session_state):
        return "PROJECT_DETAIL"
    if active_state.get("task_summary"):
        return "PROJECT_DETAIL"
    return "PROJECT_INTAKE"


def should_use_project_bridge(conversation_mode: str, session_state: dict[str, Any]) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    has_run = bool(str(session_state.get("bound_run_id", "")).strip())
    if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return True
    if mode == "STATUS_QUERY" and has_run:
        return True
    return False


def _project_prompt_context(project_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    decisions = project_context.get("decisions", {})
    if not isinstance(decisions, dict):
        decisions = {}
    rows = decisions.get("decisions", [])
    if not isinstance(rows, list):
        rows = []
    return {
        "run_id": sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80),
        "goal": sanitize_inline_text(str(project_context.get("goal", "")), max_chars=260),
        "status": {
            "run_status": sanitize_inline_text(str(status.get("run_status", "")), max_chars=40),
            "verify_result": sanitize_inline_text(str(status.get("verify_result", "")), max_chars=20),
            "gate": {
                "state": sanitize_inline_text(str(gate.get("state", "")), max_chars=40),
                "owner": sanitize_inline_text(str(gate.get("owner", "")), max_chars=60),
                "reason": sanitize_inline_text(str(gate.get("reason", "")), max_chars=220),
            },
            "needs_user_decision": bool(status.get("needs_user_decision", False)),
            "decisions_needed_count": int(status.get("decisions_needed_count", 0) or 0),
        },
        "whiteboard": project_context.get("whiteboard", {}),
        "decisions_preview": [
            {
                "decision_id": sanitize_inline_text(str(item.get("decision_id", "")), max_chars=80),
                "role": sanitize_inline_text(str(item.get("role", "")), max_chars=40),
                "action": sanitize_inline_text(str(item.get("action", "")), max_chars=40),
                "question_hint": sanitize_inline_text(str(item.get("question_hint", "")), max_chars=220),
            }
            for item in rows[:2]
            if isinstance(item, dict)
        ],
    }


def _progress_step_label(*, action: str = "", target_path: str = "", role: str = "", reason: str = "") -> str:
    action_l = str(action or "").strip().lower()
    path_l = str(target_path or "").strip().lower()
    role_l = str(role or "").strip().lower()
    reason_l = str(reason or "").strip().lower()
    if "review_contract" in action_l or "review_contract" in path_l or "review_contract" in reason_l or "contract" in role_l:
        return "合同评审"
    if "review_cost" in action_l or "review_cost" in path_l or "review_cost" in reason_l or "cost" in role_l:
        return "成本评审"
    if "lookup" in action_l or "context_pack" in path_l or "librarian" in role_l:
        return "资料检索"
    if "analysis" in action_l or "analysis.md" in path_l:
        return "需求分析"
    if "plan" in action_l or "plan" in path_l:
        return "方案整理"
    if "patch" in action_l or "diff.patch" in path_l:
        return "实现修复"
    if "verify" in action_l or "verify" in path_l or "verifier" in role_l:
        return "验收检查"
    return ""


def _append_progress_item(items: list[str], text: str, *, limit: int = 3) -> None:
    normalized = sanitize_inline_text(text, max_chars=120)
    if not normalized or normalized in items:
        return
    if len(items) >= max(1, limit):
        return
    items.append(normalized)


def _whiteboard_snapshot_entries(project_context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(project_context, dict):
        return []
    whiteboard = project_context.get("whiteboard", {})
    if not isinstance(whiteboard, dict):
        return []
    snapshot = whiteboard.get("snapshot", {})
    if not isinstance(snapshot, dict):
        return []
    entries = snapshot.get("entries", [])
    if not isinstance(entries, list):
        return []
    return [item for item in entries if isinstance(item, dict)]


def build_progress_binding(*, project_context: dict[str, Any] | None, task_summary_hint: str = "") -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}

    status = project_context.get("status", {})
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    decisions = project_context.get("decisions", {})
    if not isinstance(decisions, dict):
        decisions = {}

    run_id = sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)
    task_goal = sanitize_inline_text(
        str(task_summary_hint or project_context.get("goal", "")).strip(),
        max_chars=260,
    )
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    gate_reason = sanitize_inline_text(str(gate.get("reason", "")), max_chars=220)
    gate_owner = sanitize_inline_text(str(gate.get("owner", "")), max_chars=120)
    gate_path = sanitize_inline_text(str(gate.get("path", "")), max_chars=180)
    gate_label = _progress_step_label(target_path=gate_path, role=gate_owner, reason=gate_reason)

    done_items: list[str] = []
    if run_id:
        _append_progress_item(done_items, "项目已接到后台流程")

    for entry in _whiteboard_snapshot_entries(project_context):
        kind = str(entry.get("kind", "")).strip().lower()
        text = str(entry.get("text", "")).strip()
        low = text.lower()
        if kind in {"dispatch_lookup", "support_lookup"} and "lookup completed" in low:
            _append_progress_item(done_items, "资料检索已跑过一轮")
            continue
        if kind != "dispatch_result":
            continue
        match = _WHITEBOARD_DISPATCH_RESULT_RE.match(text)
        if not match:
            continue
        result_status = str(match.group("status") or "").strip().lower()
        if result_status != "executed":
            continue
        label = _progress_step_label(
            action=str(match.group("action") or ""),
            target_path=str(match.group("target") or ""),
            role=str(match.group("role") or ""),
            reason=str(match.group("reason") or ""),
        )
        if not label:
            continue
        if label == "资料检索":
            _append_progress_item(done_items, "资料检索已跑过一轮")
        else:
            _append_progress_item(done_items, f"{label}已跑过一轮")

    decision_rows = decisions.get("decisions", [])
    if not isinstance(decision_rows, list):
        decision_rows = []
    decision_question = ""
    for item in decision_rows:
        if not isinstance(item, dict):
            continue
        question_hint = sanitize_inline_text(str(item.get("question_hint", "")), max_chars=220)
        if question_hint:
            decision_question = question_hint
            break

    decision_count = int(status.get("decisions_needed_count", decisions.get("count", 0) or 0) or 0)
    current_phase = ""
    current_blocker = "none"
    next_action = "继续往下一步推进，有新的结果或阻塞会直接同步给你"
    question_needed = "no"
    message_purpose = "progress"

    if verify_result == "PASS" or run_status in {"pass", "done", "completed"}:
        current_phase = "结果整理/交付"
        current_blocker = "none"
        next_action = "把这一轮结果和可交付内容整理给你"
        message_purpose = "delivery"
    elif decision_count > 0:
        current_phase = gate_label or "等待关键决定"
        current_blocker = "等你先确认一个关键决定"
        next_action = "先等你拍板这个点，一拿到答复就继续往下推"
        question_needed = "yes"
    elif run_status == "blocked":
        current_phase = gate_label or "当前评审"
        if gate_label:
            current_blocker = f"{gate_label}这一步还没过，后面的推进先停在这里"
            next_action = f"先处理{gate_label}卡住的点，过掉这一步再继续往下推"
        else:
            current_blocker = "当前评审这一步还没过，后面的推进先停在这里"
            next_action = "先把当前卡点处理掉，再继续往下推"
    elif run_status in {"running", "in_progress", "working"}:
        current_phase = gate_label or "执行推进"
        current_blocker = "none"
    else:
        current_phase = gate_label or "处理中"
        current_blocker = "none"

    return {
        "current_task_goal": task_goal,
        "current_phase": current_phase,
        "last_confirmed_items": done_items,
        "current_blocker": current_blocker,
        "message_purpose": message_purpose,
        "question_needed": question_needed,
        "next_action": sanitize_inline_text(next_action, max_chars=220),
        "blocking_question": decision_question,
        "proof_refs": [f"run_id={run_id}"] if run_id else [],
    }


def build_progress_digest(*, project_context: dict[str, Any] | None, task_summary_hint: str = "") -> tuple[str, dict[str, Any]]:
    if not isinstance(project_context, dict):
        return "", {}
    binding = build_progress_binding(project_context=project_context, task_summary_hint=task_summary_hint)
    if not binding:
        return "", {}
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    payload = {
        "run_id": sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80),
        "run_status": sanitize_inline_text(str(status.get("run_status", "")), max_chars=40),
        "verify_result": sanitize_inline_text(str(status.get("verify_result", "")), max_chars=20),
        "gate_state": sanitize_inline_text(str(gate.get("state", "")), max_chars=40),
        "gate_reason": sanitize_inline_text(str(gate.get("reason", "")), max_chars=220),
        "progress_binding": binding,
    }
    raw = json.dumps(clean_json_value(payload), ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest(), binding


def remember_progress_notification(
    session_state: dict[str, Any],
    *,
    project_context: dict[str, Any] | None,
    task_summary_hint: str = "",
    ts: str = "",
) -> None:
    if not isinstance(project_context, dict):
        return
    run_id = sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)
    if not run_id:
        return
    digest, binding = build_progress_digest(project_context=project_context, task_summary_hint=task_summary_hint)
    if not digest:
        return
    notification_state = latest_notification_state(session_state)
    notification_state["last_progress_hash"] = digest
    notification_state["last_progress_ts"] = sanitize_inline_text(ts or now_iso(), max_chars=40)
    notification_state["last_notified_run_id"] = run_id
    notification_state["last_notified_phase"] = sanitize_inline_text(str(binding.get("current_phase", "")), max_chars=80)


def should_auto_advance_project_context(session_state: dict[str, Any], project_context: dict[str, Any] | None) -> bool:
    if not isinstance(project_context, dict):
        return False
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        return False
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    gate_state = str(gate.get("state", "")).strip().lower()
    if verify_result == "PASS" or run_status in {"pass", "done", "completed", "fail", "failed", "error"}:
        return False
    if bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0:
        return False
    if gate_state == "blocked":
        return False
    elapsed = seconds_since(str(latest_notification_state(session_state).get("last_auto_advance_ts", "")))
    if elapsed is not None and elapsed < SUPPORT_AUTO_ADVANCE_INTERVAL_SEC:
        return False
    return run_status in {"running", "in_progress", "working"} or gate_state in {"", "open", "ready"}


def remember_resume_recovery(
    session_state: dict[str, Any],
    *,
    candidate: dict[str, str],
    superseded_run_id: str = "",
) -> None:
    resume_state = latest_resume_state(session_state)
    resume_state["last_resume_ts"] = now_iso()
    resume_state["last_resume_source_dir"] = sanitize_inline_text(str(candidate.get("session_dir", "")), max_chars=260)
    resume_state["last_resume_source_run_id"] = sanitize_inline_text(str(candidate.get("bound_run_id", "")), max_chars=80)
    resume_state["last_resume_brief"] = sanitize_inline_text(str(candidate.get("project_brief", "")), max_chars=280)
    resume_state["superseded_run_id"] = sanitize_inline_text(superseded_run_id, max_chars=80)


def maybe_recover_previous_outline_context(
    *,
    run_dir: Path,
    chat_id: str,
    user_text: str,
    source: str,
    conversation_mode: str,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
    allow_history_resume: bool,
) -> tuple[dict[str, Any] | None, dict[str, Any], dict[str, Any] | None]:
    request_text = sanitize_inline_text(user_text, max_chars=280)
    if not is_previous_outline_request(request_text) and allow_history_resume:
        request_text = latest_resume_request_text(run_dir, session_state)
    if not request_text:
        return project_context, session_state, None

    candidate = resolve_archived_resume_candidate(chat_id=chat_id, current_run_dir=run_dir, session_state=session_state)
    recovered_brief = sanitize_inline_text(str(candidate.get("project_brief", "")), max_chars=280)
    if not recovered_brief:
        return project_context, session_state, None

    bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
    current_goal_hint = sanitize_inline_text(
        str((project_context or {}).get("goal", "") if isinstance(project_context, dict) else current_project_brief(session_state)),
        max_chars=280,
    ) or current_project_brief(session_state)
    if bound_run_id and (not should_supersede_bound_run_for_resume(
        project_context=project_context,
        current_goal_hint=current_goal_hint,
        recovered_brief=recovered_brief,
    )):
        return project_context, session_state, None

    created = ctcp_front_bridge.ctcp_new_run(goal=recovered_brief)
    new_run_id = sanitize_inline_text(str(created.get("run_id", "")), max_chars=80)
    session_state["bound_run_id"] = new_run_id
    session_state["bound_run_dir"] = sanitize_inline_text(str(created.get("run_dir", "")), max_chars=260)
    set_current_project_brief(session_state, recovered_brief)
    project_memory = _state_zone(session_state, "project_memory")
    project_memory["last_detail_turn"] = recovered_brief
    project_memory["last_detail_ts"] = now_iso()
    remember_resume_recovery(session_state, candidate=candidate, superseded_run_id=bound_run_id)
    append_event(
        run_dir,
        "SUPPORT_PREVIOUS_OUTLINE_RECOVERED",
        SUPPORT_SESSION_STATE_REL_PATH.as_posix(),
        old_run_id=bound_run_id,
        new_run_id=new_run_id,
        source_run_id=str(candidate.get("bound_run_id", "")),
    )

    recorded = ctcp_front_bridge.ctcp_record_support_turn(
        new_run_id,
        text=request_text,
        source=source,
        chat_id=chat_id,
        conversation_mode=conversation_mode,
    )
    refreshed = ctcp_front_bridge.ctcp_get_support_context(new_run_id)
    advanced: dict[str, Any] | None = None
    status = refreshed.get("status", {}) if isinstance(refreshed, dict) else {}
    if (
        str(conversation_mode or "").strip().upper() in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY", "STATUS_QUERY"}
        and isinstance(status, dict)
        and (not bool(status.get("needs_user_decision", False)))
    ):
        advanced = ctcp_front_bridge.ctcp_advance(new_run_id, max_steps=4 if not bound_run_id else 2)
        refreshed = ctcp_front_bridge.ctcp_get_support_context(new_run_id)
    if not isinstance(refreshed, dict):
        refreshed = {}
    refreshed["created"] = created
    refreshed["recorded_turn"] = recorded or {}
    refreshed["advance"] = advanced or {}
    session_state["last_bridge_sync_ts"] = now_iso()
    session_state["latest_support_context"] = {
        "run_id": str(refreshed.get("run_id", "")),
        "status": refreshed.get("status", {}),
        "whiteboard": refreshed.get("whiteboard", {}),
    }
    return refreshed, session_state, candidate


def sync_project_context(
    *,
    run_dir: Path,
    chat_id: str,
    user_text: str,
    source: str,
    conversation_mode: str,
    session_state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    project_context: dict[str, Any] = {}
    mode = str(conversation_mode or "").strip().upper()
    if not should_use_project_bridge(mode, session_state):
        return project_context, session_state

    bound_run_id = str(session_state.get("bound_run_id", "")).strip()
    created: dict[str, Any] | None = None
    recorded: dict[str, Any] | None = None
    advanced: dict[str, Any] | None = None
    recovered_candidate: dict[str, Any] | None = None
    bridge_error = ""

    try:
        if bound_run_id:
            project_context = ctcp_front_bridge.ctcp_get_support_context(bound_run_id)

        project_context, session_state, recovered_candidate = maybe_recover_previous_outline_context(
            run_dir=run_dir,
            chat_id=chat_id,
            user_text=user_text,
            source=source,
            conversation_mode=mode if mode != "STATUS_QUERY" else "PROJECT_DETAIL",
            session_state=session_state,
            project_context=project_context,
            allow_history_resume=(mode == "STATUS_QUERY"),
        )
        if recovered_candidate is not None:
            bound_run_id = str(session_state.get("bound_run_id", "")).strip()
            created = project_context.get("created", {}) if isinstance(project_context, dict) else {}
            recorded = project_context.get("recorded_turn", {}) if isinstance(project_context, dict) else {}
            advanced = project_context.get("advance", {}) if isinstance(project_context, dict) else {}

        if not bound_run_id and mode != "STATUS_QUERY":
            created = ctcp_front_bridge.ctcp_new_run(goal=user_text)
            bound_run_id = str(created.get("run_id", "")).strip()
            session_state["bound_run_id"] = bound_run_id
            session_state["bound_run_dir"] = str(created.get("run_dir", "")).strip()
            if should_refresh_project_brief(user_text, mode):
                set_current_project_brief(session_state, user_text)
            append_event(run_dir, "SUPPORT_RUN_BOUND", "", run_id=bound_run_id)

        if not bound_run_id:
            return {}, session_state

        if recovered_candidate is None:
            recorded = ctcp_front_bridge.ctcp_record_support_turn(
                bound_run_id,
                text=user_text,
                source=source,
                chat_id=chat_id,
                conversation_mode=mode,
            )
            project_context = ctcp_front_bridge.ctcp_get_support_context(bound_run_id)
            if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL"}:
                status = project_context.get("status", {})
                if isinstance(status, dict) and not bool(status.get("needs_user_decision", False)):
                    steps = 4 if created is not None else 2
                    advanced = ctcp_front_bridge.ctcp_advance(bound_run_id, max_steps=steps)
                    project_context = ctcp_front_bridge.ctcp_get_support_context(bound_run_id)

        project_context["created"] = created or {}
        project_context["recorded_turn"] = recorded or {}
        project_context["advance"] = advanced or {}
        session_state["bound_run_id"] = bound_run_id
        session_state["bound_run_dir"] = str(project_context.get("run_dir", "") or session_state.get("bound_run_dir", "")).strip()
        if should_refresh_project_brief(user_text, mode):
            set_current_project_brief(session_state, user_text)
            project_memory = _state_zone(session_state, "project_memory")
            project_memory["last_detail_turn"] = sanitize_inline_text(user_text, max_chars=280)
            project_memory["last_detail_ts"] = now_iso()
        if should_capture_project_constraints(user_text, mode):
            set_project_constraints_brief(session_state, user_text)
        if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"} and is_project_execution_followup(user_text):
            set_execution_directive(session_state, user_text)
        elif not current_project_brief(session_state) and str(project_context.get("goal", "")).strip():
            set_current_project_brief(session_state, str(project_context.get("goal", "")))
        session_state["last_bridge_sync_ts"] = now_iso()
        session_state["latest_support_context"] = {
            "run_id": str(project_context.get("run_id", "")),
            "status": project_context.get("status", {}),
            "whiteboard": project_context.get("whiteboard", {}),
        }
    except Exception as exc:
        bridge_error = sanitize_inline_text(str(exc), max_chars=220) or "bridge failed"
        append_log(run_dir / "logs" / "support_bot.debug.log", f"[{now_iso()}] bridge sync failed: {bridge_error}\n")
        if bound_run_id and "run_id not found" in bridge_error.lower():
            session_state["bound_run_id"] = ""
            session_state["bound_run_dir"] = ""
        project_context = {"error": bridge_error}

    if bridge_error:
        project_context["error"] = bridge_error
    return project_context, session_state


def _existing_path(raw: str) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = (ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if candidate.exists():
        return candidate
    return None


def _append_unique_path(paths: list[Path], candidate: Path | None) -> None:
    if candidate is None:
        return
    resolved = candidate.resolve()
    if resolved not in paths:
        paths.append(resolved)


def _parse_scope_allow_roots(plan_path: Path) -> list[Path]:
    roots: list[Path] = []
    if not plan_path.exists():
        return roots
    for raw in plan_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.lower().startswith("scope-allow:"):
            continue
        payload = line.split(":", 1)[1]
        for item in payload.split(","):
            rel = item.strip()
            if not rel or rel in {".", "./"}:
                continue
            _append_unique_path(roots, _existing_path(rel))
    return roots


def _generated_project_roots_from_patch_apply(bound_run_dir: Path) -> list[Path]:
    roots: list[Path] = []
    doc = read_json_doc(bound_run_dir / "artifacts" / "patch_apply.json")
    touched = doc.get("touched_files", []) if isinstance(doc, dict) else []
    if not isinstance(touched, list):
        touched = []
    for item in touched:
        rel = str(item or "").strip().replace("\\", "/")
        if not rel:
            continue
        parts = [part for part in rel.split("/") if part]
        if len(parts) >= 2 and parts[0] == "generated_projects":
            _append_unique_path(roots, _existing_path("/".join(parts[:2])))
    return roots


def _delivery_project_slug(raw: str) -> str:
    text = str(raw or "").strip().lower().replace("\\", "/")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:64] or "project"


def _top_level_structure_hint(root: Path, max_items: int = 8) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    items: list[str] = []
    for node in sorted(root.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        items.append(node.name + ("/" if node.is_dir() else ""))
        if len(items) >= max(1, int(max_items)):
            break
    return items


def _looks_like_ctcp_project_dir(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    required = (
        root / "README.md",
        root / "docs",
        root / "meta",
        root / "scripts",
        root / "manifest.json",
    )
    return all(path.exists() for path in required)


def _looks_like_placeholder_project_dir(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    top_files = {node.name.lower() for node in root.iterdir() if node.is_file()}
    top_dirs = {node.name.lower() for node in root.iterdir() if node.is_dir()}
    if {"docs", "meta", "scripts"} & top_dirs:
        return False
    if "manifest.json" in top_files:
        return False
    total_files = sum(1 for node in root.rglob("*") if node.is_file())
    return total_files <= 4 and bool({"main.py", "app.py", "readme.md"} & top_files)


def _delivery_project_name_hint(
    *,
    session_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    package_source_dirs: list[Path],
) -> str:
    for path in package_source_dirs:
        name = _delivery_project_slug(path.name)
        if name:
            return name
    if isinstance(project_context, dict):
        for key in ("goal", "run_id"):
            value = _delivery_project_slug(str(project_context.get(key, "")).strip())
            if value and value != "project":
                return value
    if isinstance(session_state, dict):
        brief = _delivery_project_slug(current_project_brief(session_state))
        if brief and brief != "project":
            return brief
        run_id = _delivery_project_slug(str(session_state.get("bound_run_id", "")).strip())
        if run_id and run_id != "project":
            return run_id
    return "project"


def can_channel_send_files(source: str) -> bool:
    return str(source or "").strip().lower() == "telegram"


def collect_public_delivery_state(
    *,
    session_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    source: str,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "channel": str(source or "").strip().lower(),
        "channel_can_send_files": can_channel_send_files(source),
        "bound_run_id": "",
        "bound_run_dir": "",
        "package_source_dirs": [],
        "ctcp_package_source_dirs": [],
        "placeholder_package_source_dirs": [],
        "existing_package_files": [],
        "screenshot_files": [],
        "project_name_hint": "project",
        "package_delivery_mode": "",
        "package_structure_hint": [],
        "package_ready": False,
        "screenshot_ready": False,
    }
    bound_run_dir: Path | None = None
    bound_run_id = ""
    if isinstance(project_context, dict):
        bound_run_id = str(project_context.get("run_id", "")).strip()
        bound_run_dir = _existing_path(str(project_context.get("run_dir", "")).strip())
    if bound_run_dir is None and isinstance(session_state, dict):
        bound_run_id = bound_run_id or str(session_state.get("bound_run_id", "")).strip()
        bound_run_dir = _existing_path(str(session_state.get("bound_run_dir", "")).strip())
    if bound_run_dir is None or (not bound_run_dir.is_dir()):
        return state

    state["bound_run_id"] = bound_run_id
    state["bound_run_dir"] = str(bound_run_dir)

    package_source_dirs: list[Path] = []
    for candidate in _generated_project_roots_from_patch_apply(bound_run_dir):
        _append_unique_path(package_source_dirs, candidate if candidate.is_dir() else None)
    for candidate in _parse_scope_allow_roots(bound_run_dir / "artifacts" / "PLAN.md"):
        if candidate.is_dir():
            _append_unique_path(package_source_dirs, candidate)
    ctcp_package_source_dirs = [path for path in package_source_dirs if _looks_like_ctcp_project_dir(path)]
    placeholder_package_source_dirs = [path for path in package_source_dirs if _looks_like_placeholder_project_dir(path)]

    existing_package_files: list[Path] = []
    search_roots = list(package_source_dirs)
    artifacts_dir = bound_run_dir / "artifacts"
    if artifacts_dir.exists():
        search_roots.append(artifacts_dir)
    for root in search_roots:
        for candidate in sorted(root.rglob("*.zip")):
            if candidate.name.lower() == "failure_bundle.zip":
                continue
            _append_unique_path(existing_package_files, candidate)

    screenshot_files: list[Path] = []
    screenshot_roots = list(package_source_dirs)
    if artifacts_dir.exists():
        screenshot_roots.append(artifacts_dir)
    for root in screenshot_roots:
        for candidate in sorted(root.rglob("*")):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in SCREENSHOT_SUFFIXES:
                continue
            _append_unique_path(screenshot_files, candidate)

    state["package_source_dirs"] = [str(path) for path in package_source_dirs]
    state["ctcp_package_source_dirs"] = [str(path) for path in ctcp_package_source_dirs]
    state["placeholder_package_source_dirs"] = [str(path) for path in placeholder_package_source_dirs]
    state["existing_package_files"] = [str(path) for path in existing_package_files]
    state["screenshot_files"] = [str(path) for path in screenshot_files]
    state["project_name_hint"] = _delivery_project_name_hint(
        session_state=session_state,
        project_context=project_context,
        package_source_dirs=package_source_dirs,
    )
    if existing_package_files:
        state["package_delivery_mode"] = "existing_package"
    elif ctcp_package_source_dirs:
        state["package_delivery_mode"] = "zip_existing_ctcp_project"
    elif placeholder_package_source_dirs:
        state["package_delivery_mode"] = "materialize_ctcp_scaffold"
    elif package_source_dirs:
        state["package_delivery_mode"] = "zip_existing_project"
    if state["package_delivery_mode"] == "materialize_ctcp_scaffold":
        state["package_structure_hint"] = list(CTCP_SCAFFOLD_STRUCTURE_HINT)
    elif ctcp_package_source_dirs:
        state["package_structure_hint"] = _top_level_structure_hint(ctcp_package_source_dirs[0]) or list(
            CTCP_SCAFFOLD_STRUCTURE_HINT
        )
    elif package_source_dirs:
        state["package_structure_hint"] = _top_level_structure_hint(package_source_dirs[0])
    state["package_ready"] = bool(package_source_dirs or existing_package_files)
    state["screenshot_ready"] = bool(screenshot_files)
    return state


def public_delivery_prompt_context(delivery_state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(delivery_state, dict):
        return {}
    package_source_dirs = [Path(str(x)).name for x in delivery_state.get("package_source_dirs", []) if str(x).strip()]
    existing_packages = [Path(str(x)).name for x in delivery_state.get("existing_package_files", []) if str(x).strip()]
    screenshot_count = len([x for x in delivery_state.get("screenshot_files", []) if str(x).strip()])
    return {
        "channel": str(delivery_state.get("channel", "")).strip(),
        "channel_can_send_files": bool(delivery_state.get("channel_can_send_files", False)),
        "package_ready": bool(delivery_state.get("package_ready", False)),
        "package_sources": package_source_dirs[:3],
        "existing_package_files": existing_packages[:3],
        "project_name_hint": sanitize_inline_text(str(delivery_state.get("project_name_hint", "")), max_chars=64),
        "package_delivery_mode": sanitize_inline_text(str(delivery_state.get("package_delivery_mode", "")), max_chars=48),
        "package_structure_hint": [
            sanitize_inline_text(str(x), max_chars=48) for x in delivery_state.get("package_structure_hint", [])[:8]
        ],
        "screenshot_ready": bool(delivery_state.get("screenshot_ready", False)),
        "screenshot_count": int(screenshot_count),
    }


def default_prompt_template() -> str:
    return (
        "You are CTCP Support Lead. Return JSON only.\n"
        "Keys: reply_text,next_question,actions,debug_notes.\n"
        "Design goal: mechanical safeguards decide the boundary; the agent decides the phrasing.\n"
        "Primary support reply path is api_agent; local model reply exists only as a failover path.\n"
        "All customer-visible turns, including greetings and smalltalk, are model-authored.\n"
        "There are no preset opening or fallback customer sentences in this lane; each turn must be authored fresh from the latest user message.\n"
        "Keep the reply in the user's current primary language unless the user clearly switches.\n"
        "When session context contains an active project brief, keep it as memory only.\n"
        "On greeting, capability, or smalltalk turns, do not mention existing project memory unless the latest user message explicitly asks to continue it.\n"
        "When the current channel can send files directly, do not ask for email or off-platform transfer.\n"
        "Only promise package/screenshot delivery when the prompt context says public delivery is ready for this turn.\n"
        "If public delivery says package_delivery_mode is materialize_ctcp_scaffold, describe the package honestly as a CTCP-style scaffold using the provided structure hint.\n"
        "Do not describe a scaffold package as feature-complete business logic unless the prompt context explicitly says the implementation already exists.\n"
        "Short follow-up turns like 'continue', 'go ahead', or '没有，你先做着' refine execution and must not erase or pause the project unless the user explicitly says stop.\n"
        "If the prompt includes provider failover context, say plainly that the API reply path is unavailable and that you are temporarily continuing from the local path.\n"
        "reply_text must be customer-facing only and never include logs, file paths, or stack traces.\n"
        "reply_text must be natural conversational prose (no rigid section labels).\n"
        "The safeguards define leakage, actionability, and question-count boundaries only; they do not require a fixed reply template.\n"
        "Ask at most one high-leverage follow-up question when route-changing details are missing.\n"
        "If package/screenshot delivery should happen now, use actions only: send_project_package(format=zip) and send_project_screenshot(count=1-3).\n"
    )


def should_expose_existing_project_context(conversation_mode: str, user_text: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return False
    return True


def should_expose_delivery_context(conversation_mode: str, user_text: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return user_requests_project_package(user_text) or user_requests_project_screenshot(user_text)
    return True


def load_prompt_template() -> str:
    if PROMPT_TEMPLATE_PATH.exists():
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
    return default_prompt_template()


def build_support_prompt(
    run_dir: Path,
    chat_id: str,
    user_text: str,
    *,
    source: str = "",
    conversation_mode: str = "",
    session_state: dict[str, Any] | None = None,
    project_context: dict[str, Any] | None = None,
    delivery_state: dict[str, Any] | None = None,
) -> str:
    history = load_inbox_history(run_dir)
    mode = str(conversation_mode or "").strip().upper()
    expose_project_context = should_expose_existing_project_context(mode, user_text)
    expose_delivery_context = should_expose_delivery_context(mode, user_text)
    if not expose_project_context and history:
        history = history[-1:]
    context = {
        "schema_version": "ctcp-support-context-v1",
        "chat_id": chat_id,
        "ts": now_iso(),
        "history": history,
        "latest_user_message": user_text,
        "source": sanitize_inline_text(source, max_chars=24),
        "conversation_mode": mode,
        "reply_guard": {
            "preset_customer_reply_allowed": False,
            "allow_existing_project_reference": expose_project_context,
            "latest_turn_only": not expose_project_context,
        },
    }
    if isinstance(session_state, dict):
        project_brief = current_project_brief(session_state)
        turn_memory = latest_turn_memory(session_state)
        session_profile = _state_zone(session_state, "session_profile")
        project_constraints = _state_zone(session_state, "project_constraints_memory")
        execution_memory = _state_zone(session_state, "execution_memory")
        context["session_state"] = {
            "bound_run_id": sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
            if expose_project_context
            else "",
            "task_summary": project_brief if expose_project_context else "",
            "project_brief": project_brief if expose_project_context else "",
            "project_constraints": sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=260)
            if expose_project_context
            else "",
            "latest_execution_directive": sanitize_inline_text(str(execution_memory.get("latest_user_directive", "")), max_chars=260)
            if expose_project_context
            else "",
            "latest_user_turn": sanitize_inline_text(str(turn_memory.get("latest_user_turn", "")), max_chars=260),
            "latest_turn_mode": sanitize_inline_text(str(turn_memory.get("latest_conversation_mode", "")), max_chars=40),
            "lang_hint": sanitize_inline_text(str(session_profile.get("lang_hint", "")), max_chars=12),
            "last_bridge_sync_ts": sanitize_inline_text(str(session_state.get("last_bridge_sync_ts", "")), max_chars=40),
        }
    project_prompt = _project_prompt_context(project_context)
    if expose_project_context and project_prompt:
        context["project_run"] = project_prompt
    delivery_prompt = public_delivery_prompt_context(delivery_state)
    if expose_delivery_context and delivery_prompt:
        context["public_delivery"] = delivery_prompt
    prompt = (
        load_prompt_template().rstrip()
        + "\n\n# Session Context (JSON)\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n"
    )
    write_text(run_dir / SUPPORT_PROMPT_REL_PATH, prompt)
    return prompt


def build_failover_prompt(
    prompt_text: str,
    *,
    failed_provider: str,
    failed_reason: str,
    local_provider: str,
    failover_kind: str = "unavailable",
) -> str:
    payload = {
        "schema_version": "ctcp-support-provider-failover-v1",
        "failed_provider": failed_provider,
        "failed_reason": sanitize_inline_text(failed_reason, max_chars=220),
        "failed_kind": sanitize_inline_text(failover_kind, max_chars=40) or "unavailable",
        "local_provider": local_provider,
        "required_user_visible_effect": (
            "Be explicit that the API reply path is unavailable right now and that this turn is continuing from the local fallback path."
            if str(failover_kind or "").strip().lower() != "invalid_reply"
            else "Be explicit that the API path did not yield a usable customer-ready reply for this turn and that this turn is continuing from the local fallback path."
        ),
    }
    return (
        prompt_text.rstrip()
        + "\n\n# Provider Failover (JSON)\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n"
    )


def build_reply_repair_prompt(
    prompt_text: str,
    *,
    conversation_mode: str,
    user_text: str,
    failed_reply: str,
) -> str:
    payload = {
        "schema_version": "ctcp-support-reply-repair-v1",
        "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
        "latest_user_message": sanitize_inline_text(user_text, max_chars=220),
        "failed_reply_excerpt": sanitize_inline_text(failed_reply, max_chars=220),
        "required_repair": (
            "The previous draft mentioned project context that the latest user message did not mention. "
            "Rewrite for only the latest user turn. Do not mention existing project memory unless the latest user message explicitly asks to continue it."
        ),
        "style_rule": "Do not use preset greeting shells. Write one natural customer-facing reply for this exact turn.",
    }
    return (
        prompt_text.rstrip()
        + "\n\n# Reply Repair (JSON)\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n"
    )


def make_support_request(
    chat_id: str,
    user_text: str,
    prompt_text: str,
    *,
    project_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reason = prompt_text
    if len(reason) > 20000:
        reason = reason[-20000:]
    request = {
        "role": "support_lead",
        "action": "reply",
        "target_path": SUPPORT_REPLY_PROVIDER_REL_PATH.as_posix(),
        "missing_paths": [SUPPORT_PROMPT_REL_PATH.as_posix(), SUPPORT_INBOX_REL_PATH.as_posix()],
        "reason": reason,
        "goal": f"support session {chat_id}",
        "input_text": user_text,
    }
    if isinstance(project_context, dict):
        whiteboard = project_context.get("whiteboard")
        if isinstance(whiteboard, dict):
            request["whiteboard"] = whiteboard
        status = project_context.get("status")
        if isinstance(status, dict):
            request["project_run"] = {
                "run_id": str(project_context.get("run_id", "")).strip(),
                "goal": str(project_context.get("goal", "")).strip(),
                "status": status,
            }
            run_id = str(project_context.get("run_id", "")).strip()
            if run_id:
                request["goal"] = str(project_context.get("goal", "")).strip() or f"support session {chat_id} -> {run_id}"
    return request


def failover_notice_text(*, lang: str, local_unavailable: bool = False) -> str:
    return failover_notice_text_with_kind(lang=lang, reason_kind="unavailable", local_unavailable=local_unavailable)


def failover_notice_text_with_kind(*, lang: str, reason_kind: str = "unavailable", local_unavailable: bool = False) -> str:
    kind = str(reason_kind or "").strip().lower() or "unavailable"
    if str(lang or "").strip().lower() == "en":
        if kind == "invalid_reply":
            if local_unavailable:
                return "The API path did not yield a usable reply for this turn, and the local fallback is not reachable either."
            return "The API path did not yield a usable reply for this turn, so I'm continuing from the local fallback path."
        if local_unavailable:
            return "The API reply path is unavailable right now, and the local fallback is not reachable either."
        return "The API reply path is unavailable right now, so I'm continuing from the local fallback path."
    if kind == "invalid_reply":
        if local_unavailable:
            return "这轮 API 没给到可直接发出的回复，本地回复也没接上。"
        return "这轮 API 没给到可直接发出的回复，我先切到本地继续接住你这轮。"
    if local_unavailable:
        return "现在 API 回复链路没连上，本地回复也没接上。"
    return "现在 API 回复链路没连上，我先切到本地继续接住你这轮。"


def reply_mentions_failover(reply_text: str) -> bool:
    low = str(reply_text or "").lower()
    text = str(reply_text or "")
    return ("api" in low and ("local" in low or "本地" in text)) or ("回复链路没连上" in text) or ("没给到可直接发出的回复" in text)


def prepend_failover_notice(
    reply_text: str,
    *,
    lang: str,
    reason_kind: str = "unavailable",
    local_unavailable: bool = False,
) -> str:
    notice = failover_notice_text_with_kind(lang=lang, reason_kind=reason_kind, local_unavailable=local_unavailable)
    text = str(reply_text or "").strip()
    if not text:
        return notice
    if reply_mentions_failover(text):
        return text
    return f"{notice}\n\n{text}"


def unusable_provider_reply_reason(reply_text: str, *, expected_lang: str) -> str:
    reply = str(reply_text or "").strip()
    if not reply:
        return "empty reply_text"
    if contains_forbidden_reply(reply):
        return "forbidden reply_text"
    if looks_like_garbled_text(reply, expected_lang=expected_lang):
        return "garbled reply_text"
    return ""


def execute_provider(
    *,
    provider: str,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    if provider == "manual_outbox":
        return manual_outbox.execute(
            repo_root=ROOT,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets={},
        )
    if provider == "ollama_agent":
        return ollama_agent.execute(
            repo_root=ROOT,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets={},
        )
    if provider == "api_agent":
        return api_agent.execute(
            repo_root=ROOT,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets={},
        )
    if provider == "codex_agent":
        return codex_agent.execute(
            repo_root=ROOT,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets={},
        )
    if provider == "mock_agent":
        return mock_agent.execute(
            repo_root=ROOT,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets={},
        )
    return {
        "status": "exec_failed",
        "reason": f"unsupported provider: {provider}",
    }


def _tail_text(path: Path, max_lines: int = 24, max_chars: int = 3000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    payload = "\n".join(lines[-max(1, max_lines) :])
    return payload[-max_chars:] if len(payload) > max_chars else payload


def log_provider_result(run_dir: Path, provider: str, result: dict[str, Any], label: str) -> None:
    row = {
        "ts": now_iso(),
        "label": label,
        "provider": provider,
        "status": str(result.get("status", "")),
        "reason": str(result.get("reason", "")),
        "cmd": str(result.get("cmd", "")),
        "rc": int(result.get("rc", 0) or 0),
        "stdout_log": str(result.get("stdout_log", "")),
        "stderr_log": str(result.get("stderr_log", "")),
        "prompt_path": str(result.get("prompt_path", "")),
        "target_path": str(result.get("target_path", "")),
    }
    append_jsonl(run_dir / "logs" / "support_bot.provider.log", row)

    for key, sink in (("stdout_log", "support_bot.stdout.log"), ("stderr_log", "support_bot.stderr.log")):
        rel = str(result.get(key, "")).strip()
        if not rel:
            continue
        src = run_dir / rel
        tail = _tail_text(src)
        if not tail:
            continue
        append_log(
            run_dir / "logs" / sink,
            f"[{now_iso()}] {label} provider={provider} {key}={rel}\n{tail}\n\n",
        )

    append_trace(run_dir, f"provider_{label} provider={provider} status={row['status']}")


def read_json_doc(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    if not isinstance(doc, dict):
        return None
    return doc


def contains_forbidden_reply(text: str) -> bool:
    low = str(text or "").lower()
    if any(token in low for token in FORBIDDEN_REPLY_PATTERNS):
        return True
    if re.search(r"[a-zA-Z]:\\", text or ""):
        return True
    if re.search(r"/(users|home|tmp|var|opt)/", low):
        return True
    return False


def sanitize_inline_text(text: str, max_chars: int = 220) -> str:
    raw = str(text or "")
    raw = re.sub(r"```[\s\S]*?```", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    if len(raw) > max_chars:
        return raw[: max_chars - 1] + "..."
    return raw


def normalize_question(raw: str) -> str:
    q = sanitize_inline_text(raw, max_chars=140)
    if (not q) or contains_forbidden_reply(q):
        q = "你现在最希望我先解决的一个具体问题是什么"
    if not q.endswith(("?", "？")):
        q += "？"
    return q


def detect_lang_hint(*texts: str) -> str:
    merged = " ".join(str(x or "") for x in texts)
    if not merged.strip():
        return "zh"
    zh_count = sum(1 for ch in merged if "\u4e00" <= ch <= "\u9fff")
    en_count = sum(1 for ch in merged if ("a" <= ch.lower() <= "z"))
    return "zh" if zh_count >= max(1, en_count // 3) else "en"


def is_smalltalk_only_message(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    if is_greeting_only_message(raw):
        return True
    if any(p.match(raw) for p in SMALLTALK_PATTERNS_ZH):
        return True
    if any(p.match(raw) for p in SMALLTALK_PATTERNS_EN):
        return True
    return False


def user_requests_project_package(text: str) -> bool:
    raw = str(text or "")
    low = raw.lower()
    return ("zip" in low) or ("打包" in raw) or ("压缩包" in raw) or ("发给我" in raw and "项目" in raw)


def user_requests_project_screenshot(text: str) -> bool:
    raw = str(text or "")
    low = raw.lower()
    return any(token in raw for token in ("截图", "界面图", "效果图", "项目图")) or ("screenshot" in low)


def normalize_actions(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        action_type = str(item.get("type", "")).strip().lower()
        if action_type == "ctcp_advance":
            try:
                max_steps = int(item.get("max_steps", 1))
            except Exception:
                max_steps = 1
            out.append({"type": "ctcp_advance", "max_steps": max(1, min(max_steps, 8))})
            continue
        if action_type == "request_file":
            hint = sanitize_inline_text(str(item.get("hint", "")), max_chars=180)
            out.append({"type": "request_file", "hint": hint or "请补充必要附件"})
            continue
        if action_type == "send_project_package":
            fmt = sanitize_inline_text(str(item.get("format", "zip")), max_chars=12).lower() or "zip"
            if fmt != "zip":
                fmt = "zip"
            out.append({"type": "send_project_package", "format": fmt})
            continue
        if action_type == "send_project_screenshot":
            try:
                count = int(item.get("count", 1))
            except Exception:
                count = 1
            out.append({"type": "send_project_screenshot", "count": max(1, min(count, 3))})
    return out


def synthesize_delivery_actions(
    *,
    actions: list[dict[str, Any]],
    user_text: str,
    delivery_state: dict[str, Any] | None,
    conversation_mode: str = "",
) -> list[dict[str, Any]]:
    out = [dict(item) for item in actions if isinstance(item, dict)]
    if not isinstance(delivery_state, dict):
        return out
    if not bool(delivery_state.get("channel_can_send_files", False)):
        return out
    allow_delivery_actions = should_expose_delivery_context(conversation_mode, user_text)
    if not allow_delivery_actions:
        out = [
            dict(item)
            for item in out
            if str(item.get("type", "")).strip().lower() not in {"send_project_package", "send_project_screenshot"}
        ]
    types = {str(item.get("type", "")).strip().lower() for item in out}
    if user_requests_project_package(user_text) and bool(delivery_state.get("package_ready", False)) and "send_project_package" not in types:
        out.append({"type": "send_project_package", "format": "zip"})
        types.add("send_project_package")
    screenshot_count = len([x for x in delivery_state.get("screenshot_files", []) if str(x).strip()])
    if user_requests_project_screenshot(user_text) and screenshot_count > 0 and "send_project_screenshot" not in types:
        out.append({"type": "send_project_screenshot", "count": min(3, screenshot_count)})
    return out


def normalize_reply_text(raw_reply: str, next_question: str) -> str:
    raw = str(raw_reply or "").strip()
    raw = re.sub(r"```[\s\S]*?```", "", raw).strip()

    if raw and not contains_forbidden_reply(raw):
        return raw

    conclusion = sanitize_inline_text(raw, max_chars=120)
    if (not conclusion) or contains_forbidden_reply(conclusion):
        conclusion = "这边没拿到可直接发出的回复。"

    question = normalize_question(next_question) if str(next_question or "").strip() else ""
    reply = conclusion
    if question:
        reply = f"{reply}\n\n{question}"
    if contains_forbidden_reply(reply):
        reply = "这边没拿到可直接发出的回复。"
        if question:
            reply = f"{reply}\n\n{question}"
    return reply


def fallback_reply_doc(result: dict[str, Any]) -> dict[str, Any]:
    return model_unavailable_reply_doc(result)


def sanitize_provider_doc(doc: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    clean = dict(doc)
    reply_text = utf8_clean(str(doc.get("reply_text", "")))
    next_question = utf8_clean(str(doc.get("next_question", "")))
    had_mojibake = _replacement_char_count(reply_text) >= 1 or _replacement_char_count(next_question) >= 1
    if had_mojibake:
        reply_text = reply_text.replace("\ufffd", "")
        next_question = next_question.replace("\ufffd", "")
        notes = sanitize_inline_text(str(doc.get("debug_notes", "")), max_chars=320)
        clean["debug_notes"] = f"{notes}; reply_sanitized=mojibake".strip("; ")
    clean["reply_text"] = reply_text.strip()
    clean["next_question"] = next_question.strip()
    return clean, had_mojibake


def looks_like_garbled_text(text: str, expected_lang: str = "") -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    if "\ufffd" in raw:
        return True

    zh_count = sum(1 for ch in raw if "\u4e00" <= ch <= "\u9fff")
    latin_count = sum(1 for ch in raw if ("a" <= ch.lower() <= "z"))
    suspicious_count = 0
    weird_script_count = 0
    for ch in raw:
        if ch.isdigit() or ch.isspace():
            continue
        if ch in ".,!?;:'\"()[]{}<>/\\-_+=@#$%^&*~`，。！？；：（）【】《》、":
            continue
        if "\u4e00" <= ch <= "\u9fff":
            continue
        if "a" <= ch.lower() <= "z":
            continue
        suspicious_count += 1
        code = ord(ch)
        if (0x00C0 <= code <= 0x024F) or (0x0370 <= code <= 0x052F) or (0x0600 <= code <= 0x06FF):
            weird_script_count += 1

    lang = str(expected_lang or "").strip().lower()
    if lang == "zh":
        if zh_count == 0 and suspicious_count >= max(4, len(raw) // 5):
            return True
        if zh_count == 0 and latin_count == 0 and suspicious_count >= 2:
            return True
        if zh_count == 0 and weird_script_count >= max(3, len(raw) // 8):
            return True
        if zh_count <= max(3, len(raw) // 10) and suspicious_count >= max(6, len(raw) // 3):
            return True
        if zh_count <= max(3, len(raw) // 10) and weird_script_count >= max(4, len(raw) // 4):
            return True
    if weird_script_count >= max(6, len(raw) // 6) and zh_count == 0 and latin_count <= max(2, len(raw) // 10):
        return True
    return False


def is_non_project_support_mode(conversation_mode: str) -> bool:
    return str(conversation_mode or "").strip().upper() in NON_PROJECT_SUPPORT_REPLY_MODES


def classify_api_failover_kind(*, status: str = "", reason: str = "") -> str:
    low_status = str(status or "").strip().lower()
    low_reason = str(reason or "").strip().lower()
    if low_status in {"outbox_created", "outbox_exists", "pending", "deferred", "disabled"}:
        return "unavailable"
    unavailable_tokens = (
        "connect",
        "timeout",
        "timed out",
        "401",
        "403",
        "token",
        "auth",
        "authentication",
        "base_url",
        "refused",
        "unreachable",
        "network",
        "dns",
        "ssl",
        "disabled",
        "not reachable",
        "connection reset",
    )
    if any(token in low_reason for token in unavailable_tokens):
        return "unavailable"
    return "invalid_reply"


def stale_project_context_reply_reason(reply_text: str, user_text: str, conversation_mode: str) -> str:
    if str(conversation_mode or "").strip().upper() not in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return ""
    reply = re.sub(r"\s+", " ", str(reply_text or "")).strip()
    user = re.sub(r"\s+", " ", str(user_text or "")).strip()
    if not reply:
        return ""
    reply_low = reply.lower()
    user_low = user.lower()
    leak_count = 0
    for token in PROJECT_CONTEXT_LEAK_TOKENS_ZH:
        if token in reply and token not in user:
            leak_count += 1
    for token in PROJECT_CONTEXT_LEAK_TOKENS_EN:
        if token in reply_low and token not in user_low:
            leak_count += 1
    if leak_count >= 2:
        return "stale project context on greeting reply"
    return ""


def validate_provider_reply_doc(
    *,
    doc: dict[str, Any],
    had_mojibake: bool,
    expected_lang: str,
    conversation_mode: str,
    user_text: str,
) -> tuple[str, str]:
    reply = str(doc.get("reply_text", "")).strip()
    if had_mojibake:
        return "invalid_reply", "mojibake reply_text"
    unusable_reason = unusable_provider_reply_reason(reply, expected_lang=expected_lang)
    if unusable_reason:
        return "invalid_reply", unusable_reason
    stale_reason = stale_project_context_reply_reason(reply, user_text, conversation_mode)
    if stale_reason:
        return "stale_context", stale_reason
    return "", ""


def align_reply_with_delivery_actions(reply_text: str, *, actions: list[dict[str, Any]], source_hint: str) -> str:
    text = str(reply_text or "").strip()
    if str(source_hint or "").strip().lower() != "telegram":
        return text
    action_types = {str(item.get("type", "")).strip().lower() for item in actions if isinstance(item, dict)}
    if not ({"send_project_package", "send_project_screenshot"} & action_types):
        return text
    low = text.lower()
    if any(token in text for token in ("邮箱", "邮件")) or ("email" in low) or ("mail" in low):
        note = "文件我会直接发到当前对话，不用再留邮箱。"
        if note not in text:
            text = f"{text}\n\n{note}" if text else note
    return text


def build_frontend_backend_state(
    *,
    provider_result: dict[str, Any],
    raw_doc: dict[str, Any],
    project_context: dict[str, Any] | None,
    conversation_mode: str,
    has_user_msgs: bool,
    task_summary_hint: str = "",
) -> dict[str, Any]:
    status_text = str(provider_result.get("status", "")).strip().lower()
    reason_text = str(provider_result.get("reason", "")).strip()
    is_executed = status_text == "executed"
    is_deferred = status_text in {"outbox_created", "outbox_exists", "pending", "deferred"}
    is_hard_failure = status_text in {"exec_failed", "failed", "error"} or any(
        token in reason_text.lower() for token in ("traceback", "stack trace", "command failed", "exception")
    )
    if is_executed:
        stage = "support_provider_executed"
    elif is_deferred:
        stage = "support_provider_deferred"
    else:
        stage = "support_provider_failed"

    backend_state: dict[str, Any] = {
        "stage": stage,
        "run_status": "",
        "reason": reason_text,
        "missing_fields": raw_doc.get("missing_fields", []),
        "blocked_needs_input": bool(is_hard_failure),
        "needs_input": bool(str(raw_doc.get("next_question", "")).strip()) or bool(is_hard_failure),
        "has_actionable_goal": has_user_msgs,
        "first_pass_understood": has_user_msgs,
    }

    if not isinstance(project_context, dict):
        return backend_state

    status = project_context.get("status", {})
    if not isinstance(status, dict):
        return backend_state
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    decisions = project_context.get("decisions", {})
    if not isinstance(decisions, dict):
        decisions = {}

    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    gate_state = str(gate.get("state", "")).strip().lower()
    decision_count = int(status.get("decisions_needed_count", decisions.get("count", 0) or 0) or 0)
    waiting_for_decision = decision_count > 0

    # Distinguish internal-agent blocking from user-facing blocking.
    # ALL gate owners (Chair/Planner, Fixer, Local Orchestrator,
    # Local Verifier, Researcher, Local Librarian, Contract Guardian,
    # Cost Controller, PatchMaker, …) are internal system agents.
    # User decisions are tracked separately via decisions_needed_count,
    # so every gate block without a pending decision is internal.
    gate_blocked_on_internal = gate_state == "blocked" and not waiting_for_decision
    gate_blocked_on_user = gate_state == "blocked" and waiting_for_decision

    if verify_result == "PASS" or run_status in {"pass", "done", "completed"}:
        stage = "done"
    elif waiting_for_decision:
        stage = "decision_needed"
    elif gate_blocked_on_user:
        stage = "advance_blocked"
    elif gate_blocked_on_internal:
        stage = "executing"
    elif str(conversation_mode or "").strip().upper() == "STATUS_QUERY":
        stage = "status_reply"
    elif run_status in {"running", "in_progress", "working"}:
        stage = "executing"
    elif project_context.get("advance"):
        stage = "advance_success"
    else:
        stage = backend_state["stage"]

    backend_state.update(
        {
            "stage": stage,
            "run_status": run_status,
            "verify_result": verify_result,
            "reason": str(gate.get("reason", "")).strip() or reason_text,
            "waiting_for_decision": waiting_for_decision,
            "decisions_count": decision_count,
            "needs_input": waiting_for_decision or gate_blocked_on_user,
            "blocked_needs_input": gate_blocked_on_user,
            "has_actionable_goal": True,
            "first_pass_understood": True,
            "progress_binding": build_progress_binding(
                project_context=project_context,
                task_summary_hint=task_summary_hint,
            ),
        }
    )
    return backend_state


def build_final_reply_doc(
    *,
    run_dir: Path,
    provider: str,
    provider_result: dict[str, Any],
    provider_doc: dict[str, Any] | None,
    project_context: dict[str, Any] | None = None,
    source_hint: str = "",
    conversation_mode: str = "",
    task_summary_hint: str = "",
    lang_hint: str = "",
    delivery_state: dict[str, Any] | None = None,
    latest_user_message_override: str = "",
) -> dict[str, Any]:
    raw_doc = provider_doc if isinstance(provider_doc, dict) else fallback_reply_doc(provider_result)
    raw_reply_text = str(raw_doc.get("reply_text", ""))
    raw_next_question = str(raw_doc.get("next_question", ""))
    history = load_inbox_history(run_dir, limit=12)
    user_msgs = [str(item.get("text", "")).strip() for item in history if str(item.get("text", "")).strip()]
    preferred_lang = sanitize_inline_text(str(lang_hint or ""), max_chars=12).lower()
    expected_lang = preferred_lang or detect_lang_hint(*(user_msgs[-3:] or [task_summary_hint or raw_reply_text or raw_next_question]))
    lang = expected_lang or detect_lang_hint(raw_reply_text, raw_next_question, str(raw_doc.get("debug_notes", "")))
    if looks_like_garbled_text(raw_reply_text, expected_lang=expected_lang):
        raw_reply_text = ""
    if looks_like_garbled_text(raw_next_question, expected_lang=expected_lang):
        raw_next_question = ""

    pipeline_state: dict[str, Any] | None = None
    rendered_used = False
    rendered_visible_state = ""
    reply_text = ""
    next_question = ""
    latest_user_message_for_render = sanitize_inline_text(latest_user_message_override, max_chars=280)
    if not latest_user_message_for_render:
        latest_user_message_for_render = user_msgs[-1] if user_msgs else task_summary_hint
    if render_frontend_output is not None and not is_non_project_support_mode(conversation_mode):
        try:
            summary_text = task_summary_hint.strip() or (user_msgs[-1] if user_msgs else raw_reply_text)
            backend_state = build_frontend_backend_state(
                provider_result=provider_result,
                raw_doc=raw_doc,
                project_context=project_context,
                conversation_mode=conversation_mode,
                has_user_msgs=bool(user_msgs),
                task_summary_hint=summary_text,
            )
            rendered = render_frontend_output(
                raw_backend_state=backend_state,
                task_summary=summary_text,
                raw_reply_text=raw_reply_text,
                raw_next_question=raw_next_question,
                notes={
                    "lang": lang,
                    "max_questions": 2,
                    "recent_user_messages": user_msgs,
                    "latest_user_message": latest_user_message_for_render,
                    "active_task_state": {
                        "task_summary": summary_text,
                        "run_id": str(project_context.get("run_id", "")).strip() if isinstance(project_context, dict) else "",
                    },
                },
            )
            reply_text = str(getattr(rendered, "reply_text", "")).strip()
            followups = list(getattr(rendered, "followup_questions", ()) or [])
            if followups:
                next_question = normalize_question(str(followups[0]))
            rendered_visible_state = str(getattr(rendered, "visible_state", "")).strip()
            pipeline_state = getattr(rendered, "pipeline_state", None)
            rendered_used = True
            if (not rendered_visible_state) and isinstance(pipeline_state, dict):
                rendered_visible_state = str(pipeline_state.get("visible_state", "")).strip()
        except Exception as exc:
            append_log(run_dir / "logs" / "support_bot.debug.log", f"[{now_iso()}] frontend render failed: {exc}\n")
            pipeline_state = {"error": str(exc)}

    if rendered_used:
        if not next_question:
            if rendered_visible_state in {
                "NEEDS_ONE_OR_TWO_DETAILS",
                "WAITING_FOR_DECISION",
                "BLOCKED_NEEDS_INPUT",
            }:
                next_question = normalize_question(raw_next_question)
            elif rendered_visible_state in {"UNDERSTOOD", "EXECUTING", "DONE"}:
                next_question = ""
            else:
                next_question = normalize_question(raw_next_question)
    elif not next_question:
        next_question = normalize_question(raw_next_question)
    if not reply_text:
        reply_text = normalize_reply_text(raw_reply_text, next_question)
    if str(provider_result.get("degraded_from", "")).strip().lower() == PRIMARY_SUPPORT_PROVIDER:
        reply_text = prepend_failover_notice(
            reply_text,
            lang=lang,
            reason_kind=str(provider_result.get("degraded_kind", "")),
        )

    latest_user_text = user_msgs[-1] if user_msgs else task_summary_hint
    actions = synthesize_delivery_actions(
        actions=normalize_actions(raw_doc.get("actions")),
        user_text=latest_user_text,
        delivery_state=delivery_state,
        conversation_mode=conversation_mode,
    )
    reply_text = align_reply_with_delivery_actions(reply_text, actions=actions, source_hint=source_hint)

    debug_notes = sanitize_inline_text(str(raw_doc.get("debug_notes", "")), max_chars=400)
    provider_status = str(provider_result.get("status", "")).strip()
    provider_reason = sanitize_inline_text(str(provider_result.get("reason", "")), max_chars=220)
    debug_combined = f"provider={provider}; status={provider_status}; reason={provider_reason}"
    degraded_from = sanitize_inline_text(str(provider_result.get("degraded_from", "")), max_chars=40)
    degraded_reason = sanitize_inline_text(str(provider_result.get("degraded_reason", "")), max_chars=180)
    degraded_kind = sanitize_inline_text(str(provider_result.get("degraded_kind", "")), max_chars=40)
    if degraded_from:
        debug_combined += f"; degraded_from={degraded_from}"
    if degraded_reason:
        debug_combined += f"; degraded_reason={degraded_reason}"
    if degraded_kind:
        debug_combined += f"; degraded_kind={degraded_kind}"
    if debug_notes:
        debug_combined += f"; notes={debug_notes}"
    if isinstance(pipeline_state, dict):
        selected = sanitize_inline_text(str(pipeline_state.get("selected_requirement_source", "")), max_chars=160)
        visible = sanitize_inline_text(str(pipeline_state.get("visible_state", "")), max_chars=60)
        if selected:
            debug_combined += f"; selected_requirement={selected}"
        if visible:
            debug_combined += f"; visible_state={visible}"
    if isinstance(project_context, dict):
        run_id = sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)
        if run_id:
            debug_combined += f"; run_id={run_id}"
        whiteboard = project_context.get("whiteboard", {})
        if isinstance(whiteboard, dict):
            hit_count = len(list(whiteboard.get("hits", []))) if isinstance(whiteboard.get("hits", []), list) else 0
            if hit_count:
                debug_combined += f"; whiteboard_hits={hit_count}"

    append_log(run_dir / "logs" / "support_bot.debug.log", f"[{now_iso()}] {debug_combined}\n")

    return {
        "schema_version": "ctcp-support-reply-v1",
        "ts": now_iso(),
        "provider": provider,
        "provider_status": provider_status,
        "reply_text": reply_text,
        "next_question": next_question,
        "actions": actions,
        "debug_notes": debug_combined,
    }


def process_message(
    *,
    chat_id: str,
    user_text: str,
    source: str,
    provider_override: str = "",
) -> tuple[dict[str, Any], Path]:
    user_text = utf8_clean(user_text)
    run_dir = session_run_dir(chat_id)
    ensure_layout(run_dir)
    session_state = load_support_session_state(run_dir, chat_id)

    append_jsonl(
        run_dir / SUPPORT_INBOX_REL_PATH,
        {
            "ts": now_iso(),
            "chat_id": chat_id,
            "source": source,
            "text": user_text,
        },
    )
    append_event(run_dir, "SUPPORT_MESSAGE_RECEIVED", SUPPORT_INBOX_REL_PATH.as_posix(), source=source)

    conversation_mode = detect_conversation_mode(run_dir, user_text, session_state)
    record_turn_memory(session_state, user_text=user_text, source=source, conversation_mode=conversation_mode)

    project_context, session_state = sync_project_context(
        run_dir=run_dir,
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
    )
    save_support_session_state(run_dir, session_state)
    delivery_state = collect_public_delivery_state(session_state=session_state, project_context=project_context, source=source)

    prompt_text = build_support_prompt(
        run_dir,
        chat_id,
        user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
        project_context=project_context,
        delivery_state=delivery_state,
    )
    config, cfg_msg = load_dispatch_config(run_dir)
    append_log(run_dir / "logs" / "support_bot.dispatch.log", f"[{now_iso()}] load_dispatch_config: {cfg_msg}\n")

    candidates = support_provider_candidates(config, override=provider_override)
    record_provider_runtime(session_state, preferred_provider=(candidates[0] if candidates else PRIMARY_SUPPORT_PROVIDER))
    request = make_support_request(chat_id, user_text, prompt_text, project_context=project_context)
    provider_output = run_dir / SUPPORT_REPLY_PROVIDER_REL_PATH
    provider = candidates[0]
    result: dict[str, Any] = {"status": "exec_failed", "reason": "model providers not executed"}
    provider_doc: dict[str, Any] | None = None
    attempt_errors: list[str] = []
    expected_lang = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
    if not expected_lang:
        expected_lang = detect_lang_hint(user_text, current_project_brief(session_state))
    api_failover: dict[str, str] | None = None
    api_repair_attempted = False
    for idx, candidate in enumerate(candidates, start=1):
        provider = candidate
        append_event(run_dir, "SUPPORT_PROVIDER_SELECTED", "", provider=provider, attempt=idx)
        if provider_output.exists():
            try:
                provider_output.unlink()
            except Exception:
                pass
        current_request = request
        if api_failover and provider in LOCAL_SUPPORT_REPLY_PROVIDERS:
            failover_prompt = build_failover_prompt(
                prompt_text,
                failed_provider=str(api_failover.get("failed_provider", PRIMARY_SUPPORT_PROVIDER)),
                failed_reason=str(api_failover.get("failed_reason", "")),
                local_provider=provider,
                failover_kind=str(api_failover.get("failed_kind", "unavailable")),
            )
            write_text(run_dir / SUPPORT_PROMPT_REL_PATH, failover_prompt)
            current_request = make_support_request(chat_id, user_text, failover_prompt, project_context=project_context)
            current_request["provider_failover"] = {
                "failed_provider": str(api_failover.get("failed_provider", PRIMARY_SUPPORT_PROVIDER)),
                "failed_reason": str(api_failover.get("failed_reason", "")),
                "failed_kind": str(api_failover.get("failed_kind", "unavailable")),
                "local_provider": provider,
            }
        current = execute_provider(provider=provider, run_dir=run_dir, request=current_request, config=config)
        result = current
        log_provider_result(run_dir, provider, current, f"attempt_{idx}")
        record_provider_runtime(
            session_state,
            attempted_provider=provider,
            status=str(current.get("status", "")),
            reason=str(current.get("reason", "")),
        )

        status = str(current.get("status", "")).strip()
        if status in {"outbox_created", "outbox_exists", "pending", "deferred"}:
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": str(current.get("reason", "")).strip() or status,
                    "failed_kind": classify_api_failover_kind(status=status, reason=str(current.get("reason", "")).strip() or status),
                }
                attempt_errors.append(f"{provider} {status}")
                continue
            if provider in LOCAL_SUPPORT_REPLY_PROVIDERS:
                attempt_errors.append(f"{provider} {status}")
                continue
            provider_doc = deferred_support_reply_doc(provider, current)
            break
        if status != "executed":
            reason = str(current.get("reason", "")).strip() or f"{provider} execution failed"
            attempt_errors.append(reason)
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": reason,
                    "failed_kind": classify_api_failover_kind(status=status, reason=reason),
                }
            continue

        doc = read_json_doc(provider_output)
        if not isinstance(doc, dict):
            reason = f"{provider} output missing/invalid json"
            attempt_errors.append(reason)
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": reason,
                    "failed_kind": "invalid_reply",
                }
            continue
        doc, had_mojibake = sanitize_provider_doc(doc)

        validation_kind, validation_reason = validate_provider_reply_doc(
            doc=doc,
            had_mojibake=had_mojibake,
            expected_lang=expected_lang,
            conversation_mode=conversation_mode,
            user_text=user_text,
        )
        if validation_kind:
            reason = f"{provider} {validation_reason}"
            attempt_errors.append(reason)
            if (
                provider == PRIMARY_SUPPORT_PROVIDER
                and validation_kind == "stale_context"
                and is_non_project_support_mode(conversation_mode)
                and not api_repair_attempted
            ):
                api_repair_attempted = True
                repair_prompt = build_reply_repair_prompt(
                    prompt_text,
                    conversation_mode=conversation_mode,
                    user_text=user_text,
                    failed_reply=str(doc.get("reply_text", "")),
                )
                write_text(run_dir / SUPPORT_PROMPT_REL_PATH, repair_prompt)
                repair_request = make_support_request(chat_id, user_text, repair_prompt, project_context=project_context)
                repair_request["reply_guard"] = {
                    "guard_reason": validation_reason,
                    "conversation_mode": conversation_mode,
                    "latest_turn_only": True,
                }
                repaired = execute_provider(provider=provider, run_dir=run_dir, request=repair_request, config=config)
                result = repaired
                log_provider_result(run_dir, provider, repaired, f"attempt_{idx}_repair")
                record_provider_runtime(
                    session_state,
                    attempted_provider=provider,
                    status=str(repaired.get("status", "")),
                    reason=str(repaired.get("reason", "")),
                )
                repair_status = str(repaired.get("status", "")).strip()
                if repair_status == "executed":
                    repaired_doc = read_json_doc(provider_output)
                    if isinstance(repaired_doc, dict):
                        repaired_doc, repaired_had_mojibake = sanitize_provider_doc(repaired_doc)
                        repair_kind, repair_reason = validate_provider_reply_doc(
                            doc=repaired_doc,
                            had_mojibake=repaired_had_mojibake,
                            expected_lang=expected_lang,
                            conversation_mode=conversation_mode,
                            user_text=user_text,
                        )
                        if not repair_kind:
                            current = repaired
                            result = current
                            provider_doc = repaired_doc
                            break
                        reason = f"{provider} {repair_reason}"
                    else:
                        reason = f"{provider} output missing/invalid json after repair"
                else:
                    reason = str(repaired.get("reason", "")).strip() or f"{provider} repair execution failed"
                attempt_errors.append(reason)
            if provider == PRIMARY_SUPPORT_PROVIDER:
                api_failover = {
                    "failed_provider": provider,
                    "failed_reason": reason,
                    "failed_kind": "invalid_reply",
                }
            continue
        if provider in LOCAL_SUPPORT_REPLY_PROVIDERS and api_failover:
            current["degraded_from"] = str(api_failover.get("failed_provider", PRIMARY_SUPPORT_PROVIDER))
            current["degraded_reason"] = str(api_failover.get("failed_reason", ""))
            current["degraded_kind"] = str(api_failover.get("failed_kind", "unavailable"))
        provider_doc = doc
        break

    if not isinstance(provider_doc, dict):
        joined = " | ".join(attempt_errors[-3:])
        result = {
            "status": "exec_failed",
            "reason": joined or str(result.get("reason", "")).strip() or "model providers unavailable",
        }
        if api_failover and resolve_local_support_fallback(config):
            result["local_provider"] = resolve_local_support_fallback(config)
            result["api_failure_kind"] = str(api_failover.get("failed_kind", "unavailable"))
        provider_doc = model_unavailable_reply_doc(result, lang_hint=expected_lang)

    final_doc = build_final_reply_doc(
        run_dir=run_dir,
        provider=provider,
        provider_result=result,
        provider_doc=provider_doc,
        project_context=project_context,
        source_hint=source,
        conversation_mode=conversation_mode,
        task_summary_hint=current_project_brief(session_state),
        lang_hint=str(_state_zone(session_state, "session_profile").get("lang_hint", "")),
        delivery_state=delivery_state,
    )
    write_json(run_dir / SUPPORT_REPLY_REL_PATH, final_doc)
    remember_progress_notification(
        session_state,
        project_context=project_context,
        task_summary_hint=current_project_brief(session_state),
    )
    session_state["latest_support_context"] = {
        "run_id": str(project_context.get("run_id", "")) if isinstance(project_context, dict) else "",
        "provider_status": str(final_doc.get("provider_status", "")),
        "conversation_mode": conversation_mode,
        "package_ready": bool(delivery_state.get("package_ready", False)),
        "package_delivery_mode": str(delivery_state.get("package_delivery_mode", "")).strip(),
        "package_structure_hint": list(delivery_state.get("package_structure_hint", [])),
        "screenshot_ready": bool(delivery_state.get("screenshot_ready", False)),
    }
    save_support_session_state(run_dir, session_state)
    append_event(run_dir, "SUPPORT_REPLY_WRITTEN", SUPPORT_REPLY_REL_PATH.as_posix(), provider=provider)
    return final_doc, run_dir


def parse_allowlist(raw: str) -> set[int] | None:
    text = str(raw or "").strip()
    if not text:
        return None
    out: set[int] = set()
    for part in text.split(","):
        item = part.strip()
        if not item:
            continue
        try:
            out.add(int(item))
        except Exception:
            continue
    return out or None


def _zip_directory(source_dir: Path, archive_path: Path) -> Path:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(source_dir.rglob("*")):
            if not item.is_file():
                continue
            arcname = (Path(source_dir.name) / item.relative_to(source_dir)).as_posix()
            zf.write(item, arcname)
    return archive_path


def _parse_scaffold_run_dir(text: str) -> str:
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if "run_dir=" not in line:
            continue
        return line.split("run_dir=", 1)[1].strip()
    return ""


def _materialize_support_scaffold_project(
    *,
    run_dir: Path,
    delivery_state: dict[str, Any],
) -> Path | None:
    project_name = _delivery_project_slug(str(delivery_state.get("project_name_hint", "")).strip())
    out_dir = (run_dir / SUPPORT_EXPORTS_REL_DIR / f"{project_name}_ctcp_project").resolve()
    scaffold_runs_root = (run_dir / "artifacts" / "support_scaffold_runs").resolve()

    if _looks_like_ctcp_project_dir(out_dir):
        write_json(
            run_dir / SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH,
            {
                "schema_version": "ctcp-support-scaffold-materialization-v1",
                "ts": now_iso(),
                "project_name": project_name,
                "profile": SUPPORT_SCAFFOLD_PROFILE,
                "source_mode": SUPPORT_SCAFFOLD_SOURCE_MODE,
                "out_dir": str(out_dir),
                "run_dir": "",
                "reused_existing": True,
                "exit_code": 0,
                "stdout_log": "",
                "stderr_log": "",
                "error": "",
            },
        )
        append_event(
            run_dir,
            "SUPPORT_SCAFFOLD_READY",
            SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH.as_posix(),
            reused_existing=True,
            project_name=project_name,
        )
        return out_dir

    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "ctcp_orchestrate.py"),
        "scaffold",
        "--profile",
        SUPPORT_SCAFFOLD_PROFILE,
        "--source-mode",
        SUPPORT_SCAFFOLD_SOURCE_MODE,
        "--out",
        str(out_dir),
        "--name",
        project_name,
        "--runs-root",
        str(scaffold_runs_root),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    write_text(run_dir / SUPPORT_SCAFFOLD_STDOUT_REL_PATH, proc.stdout)
    write_text(run_dir / SUPPORT_SCAFFOLD_STDERR_REL_PATH, proc.stderr)
    scaffold_run_dir = _parse_scaffold_run_dir(proc.stdout)
    error_text = ""
    if proc.returncode != 0:
        error_text = sanitize_inline_text(proc.stderr or proc.stdout, max_chars=260) or "scaffold command failed"
    elif not _looks_like_ctcp_project_dir(out_dir):
        error_text = "scaffold output missing CTCP project structure"
    write_json(
        run_dir / SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH,
        {
            "schema_version": "ctcp-support-scaffold-materialization-v1",
            "ts": now_iso(),
            "project_name": project_name,
            "profile": SUPPORT_SCAFFOLD_PROFILE,
            "source_mode": SUPPORT_SCAFFOLD_SOURCE_MODE,
            "out_dir": str(out_dir),
            "run_dir": scaffold_run_dir,
            "reused_existing": False,
            "exit_code": int(proc.returncode),
            "stdout_log": SUPPORT_SCAFFOLD_STDOUT_REL_PATH.as_posix(),
            "stderr_log": SUPPORT_SCAFFOLD_STDERR_REL_PATH.as_posix(),
            "error": error_text,
        },
    )
    if error_text:
        append_event(
            run_dir,
            "SUPPORT_SCAFFOLD_FAILED",
            SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH.as_posix(),
            project_name=project_name,
            reason=error_text,
        )
        return None
    append_event(
        run_dir,
        "SUPPORT_SCAFFOLD_READY",
        SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH.as_posix(),
        reused_existing=False,
        project_name=project_name,
    )
    return out_dir


def resolve_public_delivery_plan(
    *,
    run_dir: Path,
    actions: list[dict[str, Any]] | None,
    delivery_state: dict[str, Any] | None,
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "schema_version": "ctcp-support-public-delivery-v1",
        "ts": now_iso(),
        "requested_actions": [dict(item) for item in actions or [] if isinstance(item, dict)],
        "deliveries": [],
        "errors": [],
    }
    if not isinstance(delivery_state, dict):
        return plan

    package_source_dirs = [Path(str(x)).resolve() for x in delivery_state.get("package_source_dirs", []) if str(x).strip()]
    ctcp_package_source_dirs = [
        Path(str(x)).resolve() for x in delivery_state.get("ctcp_package_source_dirs", []) if str(x).strip()
    ]
    placeholder_package_source_dirs = [
        Path(str(x)).resolve() for x in delivery_state.get("placeholder_package_source_dirs", []) if str(x).strip()
    ]
    existing_packages = [Path(str(x)).resolve() for x in delivery_state.get("existing_package_files", []) if str(x).strip()]
    screenshot_files = [Path(str(x)).resolve() for x in delivery_state.get("screenshot_files", []) if str(x).strip()]
    export_dir = run_dir / SUPPORT_EXPORTS_REL_DIR

    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("type", "")).strip().lower()
        if action_type == "send_project_package":
            chosen: Path | None = None
            if existing_packages:
                chosen = sorted(existing_packages, key=lambda item: item.stat().st_mtime, reverse=True)[0]
            elif ctcp_package_source_dirs:
                source_dir = ctcp_package_source_dirs[0]
                chosen = _zip_directory(source_dir, export_dir / f"{source_dir.name}.zip")
            elif placeholder_package_source_dirs:
                scaffold_dir = _materialize_support_scaffold_project(run_dir=run_dir, delivery_state=delivery_state)
                if scaffold_dir is not None and scaffold_dir.exists():
                    chosen = _zip_directory(scaffold_dir, export_dir / f"{scaffold_dir.name}.zip")
                else:
                    plan["errors"].append("package requested but scaffold materialization did not succeed")
                    continue
            elif package_source_dirs:
                source_dir = package_source_dirs[0]
                chosen = _zip_directory(source_dir, export_dir / f"{source_dir.name}.zip")
            if chosen is None or (not chosen.exists()):
                plan["errors"].append("package requested but no package source is available")
                continue
            plan["deliveries"].append(
                {
                    "type": "document",
                    "path": str(chosen),
                    "caption": "按你刚才确认的格式，这里是当前项目 zip 包。",
                }
            )
            continue
        if action_type == "send_project_screenshot":
            try:
                count = int(action.get("count", 1))
            except Exception:
                count = 1
            selected = screenshot_files[: max(1, min(count, 3))]
            if not selected:
                plan["errors"].append("screenshot requested but no screenshot artifact is available")
                continue
            for idx, path in enumerate(selected, start=1):
                plan["deliveries"].append(
                    {
                        "type": "photo",
                        "path": str(path),
                        "caption": "这是当前项目可直接发送的截图。" if idx == 1 else "",
                    }
                )
    return plan


class TelegramClient:
    def __init__(self, token: str, timeout_sec: int) -> None:
        self.base = f"https://api.telegram.org/bot{token}"
        self.timeout_sec = max(1, int(timeout_sec))

    def _post(self, method: str, params: dict[str, Any]) -> Any:
        url = f"{self.base}/{method}"
        data = urllib.parse.urlencode({k: str(v) for k, v in params.items()}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=self.timeout_sec + 15) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
        doc = json.loads(payload)
        if not isinstance(doc, dict) or not bool(doc.get("ok")):
            raise RuntimeError(f"telegram api error: {payload}")
        return doc.get("result")

    def _post_multipart(self, method: str, params: dict[str, Any], file_field: str, file_path: Path) -> Any:
        url = f"{self.base}/{method}"
        boundary = f"ctcp-{uuid.uuid4().hex}"
        body = bytearray()
        for key, value in params.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
            body.extend(str(value).encode("utf-8"))
            body.extend(b"\r\n")
        mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
        body.extend(file_path.read_bytes())
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))
        req = urllib.request.Request(url, data=bytes(body), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=self.timeout_sec + 30) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
        doc = json.loads(payload)
        if not isinstance(doc, dict) or not bool(doc.get("ok")):
            raise RuntimeError(f"telegram api error: {payload}")
        return doc.get("result")

    def get_updates(self, offset: int) -> list[dict[str, Any]]:
        result = self._post(
            "getUpdates",
            {
                "timeout": self.timeout_sec,
                "offset": offset,
                "allowed_updates": json.dumps(["message"]),
            },
        )
        return result if isinstance(result, list) else []

    def send_message(self, chat_id: int, text: str) -> None:
        self._post("sendMessage", {"chat_id": chat_id, "text": text[:3800]})

    def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> None:
        params = {"chat_id": chat_id}
        if caption:
            params["caption"] = caption[:900]
        self._post_multipart("sendDocument", params, "document", file_path)

    def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> None:
        params = {"chat_id": chat_id}
        if caption:
            params["caption"] = caption[:900]
        self._post_multipart("sendPhoto", params, "photo", file_path)


def emit_public_message(tg: TelegramClient, chat_id: int, text: str) -> None:
    # Single public-output gate for this support bot script.
    tg.send_message(chat_id, str(text or ""))


def emit_public_delivery(
    tg: TelegramClient,
    *,
    chat_id: int,
    run_dir: Path,
    actions: list[dict[str, Any]] | None,
    delivery_state: dict[str, Any] | None,
) -> dict[str, Any]:
    plan = resolve_public_delivery_plan(run_dir=run_dir, actions=actions, delivery_state=delivery_state)
    sent: list[dict[str, Any]] = []
    errors = list(plan.get("errors", [])) if isinstance(plan.get("errors", []), list) else []
    for item in plan.get("deliveries", []):
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "")).strip()).resolve()
        caption = sanitize_inline_text(str(item.get("caption", "")), max_chars=300)
        if not path.exists() or not path.is_file():
            errors.append(f"delivery file missing: {path}")
            continue
        delivery_type = str(item.get("type", "")).strip().lower()
        if delivery_type == "document":
            tg.send_document(chat_id, path, caption=caption)
        elif delivery_type == "photo":
            tg.send_photo(chat_id, path, caption=caption)
        else:
            errors.append(f"unsupported delivery type: {delivery_type}")
            continue
        sent.append({"type": delivery_type, "path": str(path), "caption": caption})
    plan["sent"] = sent
    plan["errors"] = errors
    write_json(run_dir / SUPPORT_PUBLIC_DELIVERY_REL_PATH, plan)
    if sent:
        append_event(run_dir, "SUPPORT_PUBLIC_DELIVERY_SENT", SUPPORT_PUBLIC_DELIVERY_REL_PATH.as_posix(), count=len(sent))
    elif errors:
        append_event(run_dir, "SUPPORT_PUBLIC_DELIVERY_SKIPPED", SUPPORT_PUBLIC_DELIVERY_REL_PATH.as_posix(), errors=len(errors))
    return plan


def iter_telegram_support_chat_ids(allowlist: set[int] | None) -> list[int]:
    if allowlist is not None:
        return sorted(int(item) for item in allowlist)
    sessions_root = session_run_dir("telegram").parent
    if not sessions_root.exists():
        return []
    out: list[int] = []
    for path in sessions_root.iterdir():
        if not path.is_dir() or ".backup-" in path.name:
            continue
        try:
            out.append(int(path.name))
        except Exception:
            continue
    return sorted(set(out))


def build_grounded_status_reply_doc(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
) -> dict[str, Any]:
    delivery_state = collect_public_delivery_state(session_state=session_state, project_context=project_context, source="telegram")
    lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
    synthetic_status_turn = "what's the latest progress?" if lang_hint.startswith("en") else "现在做到什么程度了"
    doc = build_final_reply_doc(
        run_dir=run_dir,
        provider="support_runtime",
        provider_result={"status": "executed", "reason": "proactive_progress"},
        provider_doc={"reply_text": "", "next_question": "", "actions": [], "debug_notes": "proactive_progress"},
        project_context=project_context,
        source_hint="telegram",
        conversation_mode="STATUS_QUERY",
        task_summary_hint=current_project_brief(session_state),
        lang_hint=lang_hint,
        delivery_state=delivery_state,
        latest_user_message_override=synthetic_status_turn,
    )
    return doc


def run_proactive_support_cycle(tg: TelegramClient, allowlist: set[int] | None) -> None:
    for chat_id in iter_telegram_support_chat_ids(allowlist):
        run_dir = session_run_dir(chat_id)
        state_path = run_dir / SUPPORT_SESSION_STATE_REL_PATH
        if not state_path.exists():
            continue
        session_state = load_support_session_state(run_dir, str(chat_id))
        bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
        if not bound_run_id:
            continue

        project_context = ctcp_front_bridge.ctcp_get_support_context(bound_run_id)
        project_context, session_state, recovered_candidate = maybe_recover_previous_outline_context(
            run_dir=run_dir,
            chat_id=str(chat_id),
            user_text="",
            source="telegram_auto_resume",
            conversation_mode="PROJECT_DETAIL",
            session_state=session_state,
            project_context=project_context,
            allow_history_resume=True,
        )
        if not isinstance(project_context, dict):
            continue

        auto_advanced = False
        if should_auto_advance_project_context(session_state, project_context):
            bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
            if bound_run_id:
                ctcp_front_bridge.ctcp_advance(bound_run_id, max_steps=2)
                latest_notification_state(session_state)["last_auto_advance_ts"] = now_iso()
                project_context = ctcp_front_bridge.ctcp_get_support_context(bound_run_id)
                auto_advanced = True

        digest, binding = build_progress_digest(
            project_context=project_context,
            task_summary_hint=current_project_brief(session_state),
        )
        if not digest:
            continue
        notification_state = latest_notification_state(session_state)
        if digest == str(notification_state.get("last_progress_hash", "")).strip():
            if recovered_candidate is not None:
                save_support_session_state(run_dir, session_state)
            continue

        doc = build_grounded_status_reply_doc(run_dir=run_dir, session_state=session_state, project_context=project_context)
        reply_text = str(doc.get("reply_text", "")).strip()
        if not reply_text:
            continue
        emit_public_message(tg, chat_id, reply_text)
        write_json(run_dir / SUPPORT_REPLY_REL_PATH, doc)
        session_state["latest_support_context"] = {
            "run_id": str(project_context.get("run_id", "")),
            "provider_status": str(doc.get("provider_status", "")),
            "conversation_mode": "STATUS_QUERY",
            "package_ready": False,
            "package_delivery_mode": "",
            "package_structure_hint": [],
            "screenshot_ready": False,
        }
        remember_progress_notification(
            session_state,
            project_context=project_context,
            task_summary_hint=current_project_brief(session_state),
        )
        save_support_session_state(run_dir, session_state)
        append_event(
            run_dir,
            "SUPPORT_PROGRESS_PUSHED",
            SUPPORT_REPLY_REL_PATH.as_posix(),
            run_id=str(project_context.get("run_id", "")),
            auto_advanced=auto_advanced,
            recovered=bool(recovered_candidate),
            phase=str(binding.get("current_phase", "")),
        )


def resolve_telegram_token(raw: str) -> str:
    text = str(raw or "").strip()
    if text:
        return text
    for key in ("CTCP_TG_TOKEN", "TELEGRAM_BOT_TOKEN"):
        value = str(os.environ.get(key, "")).strip()
        if value:
            return value
    return ""


def run_stdin_mode(chat_id: str, provider_override: str = "") -> int:
    user_text = utf8_clean(sys.stdin.read()).strip()
    if not user_text:
        print("[ctcp_support_bot] stdin message is empty", file=sys.stderr)
        return 1
    doc, _ = process_message(chat_id=chat_id, user_text=user_text, source="stdin", provider_override=provider_override)
    print(str(doc.get("reply_text", "")).strip())
    return 0


def run_telegram_mode(token: str, poll_seconds: int, allowlist_raw: str, provider_override: str = "") -> int:
    tg = TelegramClient(token=token, timeout_sec=poll_seconds)
    allowlist = parse_allowlist(allowlist_raw)

    offset = 0
    while True:
        try:
            updates = tg.get_updates(offset)
        except Exception as exc:
            print(f"[ctcp_support_bot] telegram getUpdates error: {exc}", file=sys.stderr)
            time.sleep(1.0)
            continue

        if not updates:
            try:
                run_proactive_support_cycle(tg, allowlist)
            except Exception as exc:
                print(f"[ctcp_support_bot] proactive progress error: {exc}", file=sys.stderr)
            continue

        for upd in updates:
            try:
                uid = int(upd.get("update_id", 0))
                if uid >= offset:
                    offset = uid + 1

                msg = upd.get("message", {})
                if not isinstance(msg, dict):
                    continue
                chat = msg.get("chat", {})
                if not isinstance(chat, dict):
                    continue
                chat_id = int(chat.get("id", 0))
                if not chat_id:
                    continue
                if allowlist is not None and chat_id not in allowlist:
                    continue

                user_text = str(msg.get("text", "")).strip()
                if not user_text:
                    continue

                if user_text.startswith("/start"):
                    emit_public_message(
                        tg,
                        chat_id,
                        "欢迎使用 CTCP Support Bot。你把这轮最想推进的目标发我，我现在就开始处理。",
                    )
                    continue

                doc, support_run_dir = process_message(
                    chat_id=str(chat_id),
                    user_text=user_text,
                    source="telegram",
                    provider_override=provider_override,
                )
                emit_public_message(tg, chat_id, str(doc.get("reply_text", "")).strip())
                session_state = load_support_session_state(support_run_dir, str(chat_id))
                delivery_state = collect_public_delivery_state(
                    session_state=session_state,
                    project_context=None,
                    source="telegram",
                )
                emit_public_delivery(
                    tg,
                    chat_id=chat_id,
                    run_dir=support_run_dir,
                    actions=list(doc.get("actions", []) or []),
                    delivery_state=delivery_state,
                )
            except Exception as exc:
                print(f"[ctcp_support_bot] telegram update error: {exc}", file=sys.stderr)
                continue


def run_selftest() -> int:
    chat_id = f"selftest-{int(time.time())}"
    message = "请帮我像 CEO 一样安排客服推进节奏。"

    doc, run_dir = process_message(
        chat_id=chat_id,
        user_text=message,
        source="selftest",
        provider_override="ollama_agent",
    )

    reply_path = run_dir / SUPPORT_REPLY_REL_PATH
    if not reply_path.exists():
        raise AssertionError(f"missing {reply_path}")

    payload = read_json_doc(reply_path)
    if payload is None:
        raise AssertionError("support_reply.json is not valid json object")

    for key in ("reply_text", "next_question", "actions"):
        if key not in payload:
            raise AssertionError(f"missing key: {key}")

    reply_text = str(payload.get("reply_text", ""))
    lower = reply_text.lower()
    banned = ("trace", "logs/", "logs\\", "outbox/", "outbox\\", "diff --git")
    for token in banned:
        if token in lower:
            raise AssertionError(f"reply_text contains forbidden token: {token}")

    print(f"[ctcp_support_bot][selftest] PASS run_dir={run_dir}")
    print(f"[ctcp_support_bot][selftest] reply={sanitize_inline_text(str(doc.get('reply_text', '')), max_chars=200)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="CTCP Support Bot (dual-channel customer output + run_dir logs)")
    ap.add_argument("--stdin", action="store_true", help="Read one user message from stdin and print reply_text to stdout")
    ap.add_argument("--chat-id", default="stdin", help="Session id used with --stdin mode")
    ap.add_argument("--selftest", action="store_true", help="Run selftest using model-only support reply path")
    ap.add_argument("--provider", default="", help="Optional provider override for support_lead")

    sub = ap.add_subparsers(dest="mode")
    p_tg = sub.add_parser("telegram", help="Run Telegram long-poll loop")
    p_tg.add_argument("--token", default="", help="Telegram bot token (or use CTCP_TG_TOKEN / TELEGRAM_BOT_TOKEN)")
    p_tg.add_argument("--poll-seconds", type=int, default=2, help="Telegram long-poll timeout seconds")
    p_tg.add_argument("--allowlist", default="", help="Optional chat id allowlist: id1,id2")

    args = ap.parse_args()

    override = str(args.provider or "").strip()
    if args.selftest:
        return run_selftest()
    if bool(args.stdin):
        return run_stdin_mode(chat_id=str(args.chat_id), provider_override=override)
    if args.mode == "telegram":
        token = resolve_telegram_token(str(args.token))
        if not token:
            print("[ctcp_support_bot] telegram token missing; pass --token or set CTCP_TG_TOKEN", file=sys.stderr)
            return 1
        return run_telegram_mode(
            token=token,
            poll_seconds=int(args.poll_seconds),
            allowlist_raw=str(args.allowlist),
            provider_override=override,
        )

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
