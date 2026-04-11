#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import socket
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from frontend.delivery_reply_actions import align_reply_with_delivery_actions, delivery_plan_failed, inject_ready_delivery_actions, prioritize_screenshot_files
from frontend.progress_reply import humanize_progress_runtime_text
from frontend.telegram_http_client import telegram_post_form, telegram_post_multipart
PROMPT_TEMPLATE_PATH = ROOT / "agents" / "prompts" / "support_lead_reply.md"
SUPPORT_INBOX_REL_PATH = Path("artifacts") / "support_inbox.jsonl"
SUPPORT_PROMPT_REL_PATH = Path("artifacts") / "support_prompt_input.md"
SUPPORT_REPLY_PROVIDER_REL_PATH = Path("artifacts") / "support_reply.provider.json"
SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH = Path("artifacts") / "support_mode_router.provider.json"
SUPPORT_REPLY_REL_PATH = Path("artifacts") / "support_reply.json"
SUPPORT_SESSION_STATE_REL_PATH = Path("artifacts") / "support_session_state.json"
SUPPORT_PUBLIC_DELIVERY_REL_PATH = Path("artifacts") / "support_public_delivery.json"
SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH = Path("artifacts") / "support_scaffold_materialization.json"
SUPPORT_EXPORTS_REL_DIR = Path("artifacts") / "support_exports"
DISPATCH_CONFIG_REL_PATH = Path("artifacts") / "dispatch_config.json"
SUPPORT_SCAFFOLD_STDOUT_REL_PATH = Path("logs") / "support_scaffold.stdout.log"
SUPPORT_SCAFFOLD_STDERR_REL_PATH = Path("logs") / "support_scaffold.stderr.log"
SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH = Path("artifacts") / "support_t2p_state_machine_report.json"
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
_TASK_PROGRESS_STATUS_MARKERS_ZH = (
    "当前",
    "目前",
    "状态",
    "阶段",
    "进展",
    "卡点",
    "阻塞",
    "已完成",
)
_TASK_PROGRESS_STATUS_MARKERS_EN = (
    "current",
    "status",
    "phase",
    "progress",
    "blocked",
    "completed",
)
_TASK_PROGRESS_NEXT_ACTION_MARKERS_ZH = ("下一步", "接下来", "我会", "我先", "先把", "继续处理")
_TASK_PROGRESS_NEXT_ACTION_MARKERS_EN = ("next", "next step", "next action", "i will", "i'll", "start by")
_TASK_PROGRESS_LOW_INFO_ACKS_ZH = ("我在", "好的", "明白了", "收到", "稍等", "继续处理中")
_TASK_PROGRESS_LOW_INFO_ACKS_EN = ("got it", "okay", "understood", "on it", "processing")
_TASK_PROGRESS_TRANSITION_MARKERS_ZH = ("进入", "切换到", "从", "转到")
_TASK_PROGRESS_TRANSITION_MARKERS_EN = ("transition", "moved to", "state changed", "switched to")
_TASK_PROGRESS_REASON_MARKERS_ZH = ("原因", "因为", "触发")
_TASK_PROGRESS_REASON_MARKERS_EN = ("because", "reason", "triggered by", "due to")
_TASK_PROGRESS_OWNER_MARKERS_ZH = ("我会", "我先", "由我", "由你", "你只需要", "系统会")
_TASK_PROGRESS_OWNER_MARKERS_EN = ("i will", "i'll", "you need to", "system will", "owned by")
_TASK_PROGRESS_COMPLETION_CLAIMS_ZH = ("已完成", "已经完成", "可交付", "准备好了", "已经做好")
_TASK_PROGRESS_COMPLETION_CLAIMS_EN = ("completed", "done", "ready to deliver", "delivery ready")
_FINAL_READY_RUN_STATUSES = {"pass", "done", "completed", "success"}
_PROACTIVE_INTERNAL_GATE_LEAK_TOKENS = (
    "contract guardian",
    "cost controller",
    "chair/planner",
    "review_contract",
    "review_cost",
    "verdict=",
    "gate owner",
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
PROJECT_GOAL_HINTS_ZH = ("项目", "剧情", "故事", "设定", "分支", "脚本", "游戏", "叙事", "分镜", "角色", "世界观")
PROJECT_GOAL_HINTS_EN = (
    "project",
    "storyline",
    "story",
    "setting",
    "branch",
    "script",
    "game",
    "narrative design",
    "storyboard",
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
PROJECT_CREATE_INTENT_HINTS_ZH = (
    "创建项目",
    "创建一个项目",
    "帮我创建",
    "帮我做一个项目",
    "搭建项目",
    "生成项目",
    "做一个工具",
    "做个工具",
    "开发一个工具",
)
PROJECT_CREATE_INTENT_HINTS_EN = (
    "create a project",
    "build a project",
    "generate a project",
    "start the project",
    "make a tool",
    "build a tool",
)
NON_PROJECT_SUPPORT_REPLY_MODES = {"GREETING", "SMALLTALK", "CAPABILITY_QUERY", "PROJECT_INTAKE"}
SUPPORTED_CONVERSATION_MODES = {
    "GREETING",
    "SMALLTALK",
    "CAPABILITY_QUERY",
    "PROJECT_INTAKE",
    "PROJECT_DETAIL",
    "PROJECT_DECISION_REPLY",
    "STATUS_QUERY",
}
SUPPORT_ACTIVE_STAGES = (
    "INTAKE",
    "CLARIFY",
    "PLAN",
    "EXECUTE",
    "VERIFY",
    "RETRYING",
    "RECOVERY_NEEDED",
    "EXEC_FAILED",
    "BLOCKED_HARD",
    "WAIT_USER_DECISION",
    "FINALIZE",
    "DELIVER",
    "RECOVER",
    "DELIVERED",
)
SUPPORT_STAGE_EXIT_RULES: dict[str, str] = {
    "INTAKE": "goal_and_scope_bound",
    "CLARIFY": "blocking_detail_collected_or_default_applied",
    "PLAN": "minimal_execution_path_locked",
    "EXECUTE": "execution_step_change_or_verify_trigger",
    "VERIFY": "verification_result_recorded_or_blocker_identified",
    "RETRYING": "retry_attempt_recorded_or_gate_truth_changed",
    "RECOVERY_NEEDED": "explicit_recovery_action_bound",
    "EXEC_FAILED": "failed_execution_path_reconciled",
    "BLOCKED_HARD": "non_retryable_blocker_reconciled",
    "WAIT_USER_DECISION": "required_user_decision_received",
    "FINALIZE": "delivery_payload_ready",
    "DELIVER": "result_shared_with_user",
    "RECOVER": "first_failure_mitigated_or_escalated",
    "DELIVERED": "new_task_or_explicit_followup",
}
SUPPORT_MESSAGE_INTENTS = (
    "continue",
    "clarify",
    "constraint_update",
    "new_task",
    "small_talk",
    "status_check",
)
SUPPORT_HISTORY_RAW_TURN_LIMIT = 60
SUPPORT_HISTORY_PROMPT_RECENT_LIMIT = 8
MODE_ROUTER_HINTS_ZH = (
    "为什么",
    "为何",
    "为啥",
    "怎么会",
    "凭什么",
    "依据",
    "刚让你做",
)
MODE_ROUTER_HINTS_EN = (
    "why",
    "how come",
    "how is it that",
    "why did",
    "reason",
    "basis",
)
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
SUPPORT_NOTIFICATION_COOLDOWN_SEC = 45
# 0 means "disable periodic no-change proactive progress push".
SUPPORT_EXECUTION_KEEPALIVE_INTERVAL_SEC = 0
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
SUPPORT_PACKAGE_MIN_QUALITY_SCORE = 70
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
    from llm_core.providers import runtime as provider_runtime
    from tools.providers import api_agent, codex_agent, manual_outbox, mock_agent, ollama_agent
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from llm_core.providers import runtime as provider_runtime
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
    import ctcp_support_controller
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
import ctcp_support_controller
from ctcp_support_recovery import (
    authoritative_stage_for_runtime as authoritative_stage_for_runtime_impl,
    annotate_plan_draft_recovery,
    build_frontend_backend_truth_state,
    build_stale_bound_run_context,
    inject_provider_truth_context,
    is_missing_plan_draft_context,
    latest_known_project_goal,
    plan_draft_recovery_hint,
    resolve_new_run_goal,
    runtime_phase_to_support_stage as runtime_phase_to_support_stage_impl,
    should_auto_advance_project_context as should_auto_advance_project_context_impl,
)

try:
    from frontend.conversation_mode_router import (
        has_sufficient_task_signal as frontend_has_sufficient_task_signal,
        is_capability_query as frontend_is_capability_query,
        is_greeting_only as frontend_is_greeting_only,
        is_status_query as frontend_is_status_query,
        route_conversation_mode as frontend_route_conversation_mode,
    )
    from frontend.frontdesk_state_machine import (
        derive_frontdesk_state as frontend_derive_frontdesk_state,
        normalize_frontdesk_state as frontend_normalize_frontdesk_state,
        prompt_context_from_frontdesk_state as frontend_prompt_context_from_frontdesk_state,
        reply_strategy_from_frontdesk_state as frontend_reply_strategy_from_frontdesk_state,
    )
    from frontend.support_reply_policy import (
        default_reply_dedupe_memory as frontend_default_reply_dedupe_memory,
        enforce_reply_policy as frontend_enforce_reply_policy,
        normalize_reply_dedupe_memory as frontend_normalize_reply_dedupe_memory,
        render_fallback_reply as frontend_render_fallback_reply,
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
    from frontend.frontdesk_state_machine import (
        derive_frontdesk_state as frontend_derive_frontdesk_state,
        normalize_frontdesk_state as frontend_normalize_frontdesk_state,
        prompt_context_from_frontdesk_state as frontend_prompt_context_from_frontdesk_state,
        reply_strategy_from_frontdesk_state as frontend_reply_strategy_from_frontdesk_state,
    )
    from frontend.support_reply_policy import (
        default_reply_dedupe_memory as frontend_default_reply_dedupe_memory,
        enforce_reply_policy as frontend_enforce_reply_policy,
        normalize_reply_dedupe_memory as frontend_normalize_reply_dedupe_memory,
        render_fallback_reply as frontend_render_fallback_reply,
    )
    from frontend.response_composer import render_frontend_output
except Exception:
    frontend_has_sufficient_task_signal = None  # type: ignore[assignment]
    frontend_is_capability_query = None  # type: ignore[assignment]
    frontend_is_greeting_only = None  # type: ignore[assignment]
    frontend_is_status_query = None  # type: ignore[assignment]
    frontend_route_conversation_mode = None  # type: ignore[assignment]
    frontend_derive_frontdesk_state = None  # type: ignore[assignment]
    frontend_normalize_frontdesk_state = None  # type: ignore[assignment]
    frontend_prompt_context_from_frontdesk_state = None  # type: ignore[assignment]
    frontend_reply_strategy_from_frontdesk_state = None  # type: ignore[assignment]
    frontend_default_reply_dedupe_memory = None  # type: ignore[assignment]
    frontend_enforce_reply_policy = None  # type: ignore[assignment]
    frontend_normalize_reply_dedupe_memory = None  # type: ignore[assignment]
    frontend_render_fallback_reply = None  # type: ignore[assignment]
    render_frontend_output = None  # type: ignore[assignment]

try:
    from bridge.state_store import SharedStateStore
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        from bridge.state_store import SharedStateStore
    except Exception:
        SharedStateStore = None  # type: ignore[assignment]
except Exception:
    SharedStateStore = None  # type: ignore[assignment]

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

def _telegram_lock_path(token: str) -> Path:
    token_hash = hashlib.sha1(str(token or "").encode("utf-8", errors="ignore")).hexdigest()[:16]
    return (get_runs_root() / get_repo_slug(ROOT) / "support_bot_locks" / f"telegram_poll_{token_hash}.lock").resolve()

def acquire_telegram_poll_lock(token: str) -> tuple[Path, Any]:
    lock_path = _telegram_lock_path(token)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("a+", encoding="utf-8")
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt  # type: ignore

            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl  # type: ignore

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        owner = ""
        try:
            fh.seek(0)
            owner = fh.read().strip()
        except Exception:
            owner = ""
        try:
            fh.close()
        except Exception:
            pass
        hint = f" (owner={owner})" if owner else ""
        raise RuntimeError(f"telegram poll lock busy: {lock_path}{hint}")

    try:
        fh.seek(0)
        fh.truncate(0)
        fh.write(f"pid={os.getpid()} ts={now_iso()}\n")
        fh.flush()
    except Exception:
        pass
    return lock_path, fh

def release_telegram_poll_lock(lock_path: Path, fh: Any) -> None:
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt  # type: ignore

            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl  # type: ignore

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        fh.close()
    except Exception:
        pass
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass

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
        "support_mode_router": {
            "enabled": True,
            "min_confidence": 0.62,
            "max_history": 8,
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

def _normalize_mode_name(raw: str) -> str:
    mode = sanitize_inline_text(str(raw or ""), max_chars=40).upper().strip()
    return mode if mode in SUPPORTED_CONVERSATION_MODES else ""

def _to_float(raw: Any, default: float) -> float:
    try:
        return float(raw)
    except Exception:
        return default

def _mode_router_config(config: dict[str, Any]) -> dict[str, Any]:
    raw = config.get("support_mode_router", {})
    if not isinstance(raw, dict):
        raw = {}
    enabled = bool(raw.get("enabled", True))
    min_confidence = _to_float(raw.get("min_confidence", 0.62), 0.62)
    min_confidence = max(0.0, min(min_confidence, 1.0))
    max_history = int(raw.get("max_history", 8) or 8)
    max_history = max(2, min(max_history, 16))
    return {
        "enabled": enabled,
        "min_confidence": min_confidence,
        "max_history": max_history,
    }

def mode_router_provider_candidates(config: dict[str, Any], override: str = "") -> list[str]:
    ordered: list[str] = []
    for provider in support_provider_candidates(config, override=override):
        if provider in SUPPORT_REPLY_PROVIDERS and provider not in ordered:
            ordered.append(provider)
    if not ordered:
        ordered = [PRIMARY_SUPPORT_PROVIDER, LOCAL_SUPPORT_REPLY_PROVIDERS[0]]
    return ordered

def should_try_model_mode_router(*, user_text: str, detected_mode: str, session_state: dict[str, Any]) -> bool:
    mode = str(detected_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL"}:
        return False
    if not bool(str(session_state.get("bound_run_id", "")).strip()):
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw:
        return False
    if user_requests_project_package(raw) or user_requests_project_screenshot(raw):
        return False
    low = raw.lower()
    hint_hit = any(token in raw for token in MODE_ROUTER_HINTS_ZH) or any(token in low for token in MODE_ROUTER_HINTS_EN)
    question_like = raw.endswith(("?", "？")) or ("?" in raw) or ("？" in raw)
    if not (hint_hit or question_like):
        return False
    if is_project_create_intent(raw, mode):
        return False
    return True

def build_mode_router_prompt(
    *,
    run_dir: Path,
    user_text: str,
    detected_mode: str,
    session_state: dict[str, Any],
    source: str,
    max_history: int,
) -> str:
    history = load_inbox_history(run_dir, limit=max(2, max_history))
    allowed_modes = sorted(SUPPORTED_CONVERSATION_MODES)
    context = {
        "schema_version": "ctcp-support-mode-router-context-v1",
        "ts": now_iso(),
        "source": sanitize_inline_text(source, max_chars=24),
        "detected_mode": _normalize_mode_name(detected_mode) or "SMALLTALK",
        "latest_user_message": sanitize_inline_text(user_text, max_chars=280),
        "has_bound_run": bool(str(session_state.get("bound_run_id", "")).strip()),
        "bound_run_id": sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80),
        "project_brief": sanitize_inline_text(current_project_brief(session_state), max_chars=280),
        "history": history,
        "allowed_modes": allowed_modes,
    }
    instruction = {
        "schema_version": "ctcp-support-mode-router-request-v1",
        "task": "classify the latest user turn into one allowed conversation mode",
        "hard_rules": [
            "Return exactly one JSON object only.",
            "Mode must be one of allowed_modes.",
            "If user asks progress/status/explanation of existing run or delivery, prefer STATUS_QUERY.",
            "Do not invent new mode labels.",
        ],
        "output_schema": {
            "mode": "one_of_allowed_modes",
            "confidence": "0.0~1.0",
            "reason": "short string",
        },
    }
    return (
        "# Support Mode Router\n\n"
        + json.dumps(instruction, ensure_ascii=False, indent=2)
        + "\n\n# Context\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n"
    )

def make_mode_router_request(chat_id: str, user_text: str, prompt_text: str) -> dict[str, Any]:
    reason = prompt_text[-20000:] if len(prompt_text) > 20000 else prompt_text
    return {
        "role": "support_mode_router",
        "action": "classify_mode",
        "target_path": SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH.as_posix(),
        "missing_paths": [SUPPORT_INBOX_REL_PATH.as_posix()],
        "reason": reason,
        "goal": f"support mode routing {chat_id}",
        "input_text": user_text,
    }

def parse_mode_router_doc(path: Path, *, min_confidence: float) -> tuple[str, str]:
    doc = read_json_doc(path)
    if not isinstance(doc, dict):
        return "", "mode router output missing/invalid json"
    mode = _normalize_mode_name(str(doc.get("mode", "")))
    if not mode:
        return "", "mode router output missing valid mode"
    confidence = _to_float(doc.get("confidence", 0.0), 0.0)
    if confidence < min_confidence:
        return "", f"mode router confidence too low: {confidence:.2f} < {min_confidence:.2f}"
    return mode, ""

def maybe_override_conversation_mode_with_model(
    *,
    run_dir: Path,
    chat_id: str,
    user_text: str,
    source: str,
    detected_mode: str,
    session_state: dict[str, Any],
    config: dict[str, Any],
    provider_override: str = "",
) -> str:
    fallback_mode = _normalize_mode_name(detected_mode) or "SMALLTALK"
    router_cfg = _mode_router_config(config)
    if not bool(router_cfg.get("enabled", True)):
        return fallback_mode
    if not should_try_model_mode_router(user_text=user_text, detected_mode=fallback_mode, session_state=session_state):
        return fallback_mode

    prompt_text = build_mode_router_prompt(
        run_dir=run_dir,
        user_text=user_text,
        detected_mode=fallback_mode,
        session_state=session_state,
        source=source,
        max_history=int(router_cfg.get("max_history", 8)),
    )
    request = make_mode_router_request(chat_id, user_text, prompt_text)
    output_path = run_dir / SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH
    try:
        output_path.unlink(missing_ok=True)
    except Exception:
        pass
    errors: list[str] = []

    for idx, provider in enumerate(mode_router_provider_candidates(config, override=provider_override), start=1):
        result = execute_provider(provider=provider, run_dir=run_dir, request=request, config=config)
        log_provider_result(run_dir, provider, result, f"mode_router_attempt_{idx}")
        if str(result.get("status", "")).strip().lower() != "executed":
            errors.append(f"{provider}:{sanitize_inline_text(str(result.get('reason', '')), max_chars=120)}")
            continue
        mode, reason = parse_mode_router_doc(
            output_path,
            min_confidence=float(router_cfg.get("min_confidence", 0.62)),
        )
        if not mode:
            errors.append(f"{provider}:{reason}")
            continue
        if mode != fallback_mode:
            append_event(
                run_dir,
                "SUPPORT_MODE_ROUTER_APPLIED",
                SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH.as_posix(),
                from_mode=fallback_mode,
                to_mode=mode,
                provider=provider,
            )
        return mode

    append_event(
        run_dir,
        "SUPPORT_MODE_ROUTER_SKIPPED",
        SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH.as_posix(),
        from_mode=fallback_mode,
        reason=" | ".join(errors[-3:]) if errors else "no provider accepted mode arbitration",
    )
    return fallback_mode

def model_unavailable_reply_doc(result: dict[str, Any], *, lang_hint: str = "zh") -> dict[str, Any]:
    lang = str(lang_hint or "").strip().lower()
    use_en = lang.startswith("en")
    local_provider = str(result.get("local_provider", "")).strip()
    if local_provider:
        if use_en:
            reply_text = "The reply backend is unavailable right now, and neither the API path nor the local fallback produced a customer-ready reply for this turn."
        else:
            reply_text = "当前回复后端暂时不可用，API 路径和本地兜底都没有给出可直接发送的正式回复。"
    else:
        if use_en:
            reply_text = "The reply backend is unavailable right now, so there is no customer-ready reply for this turn yet."
        else:
            reply_text = "当前回复后端暂时不可用，所以这轮还没有可直接发送的正式回复。"
    return {
        "reply_text": reply_text,
        "next_question": "",
        "actions": [],
        "debug_notes": sanitize_inline_text(str(result.get("reason", "")), max_chars=180) or "model_unavailable",
    }

def deferred_support_reply_doc(provider: str, result: dict[str, Any]) -> dict[str, Any]:
    """Return empty reply when deferred - no internal debug messages to user."""
    path_hint = sanitize_inline_text(str(result.get("path", "")), max_chars=180)
    notes = f"deferred:{provider}"
    if path_hint:
        notes += f" path={path_hint}"
    return {
        "reply_text": "",
        "next_question": "",
        "actions": [],
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

def load_last_reply_text(run_dir: Path) -> str:
    path = run_dir / SUPPORT_REPLY_REL_PATH
    if not path.exists():
        return ""
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return ""
    if not isinstance(doc, dict):
        return ""
    return str(doc.get("reply_text", "")).strip()

def default_support_session_state(chat_id: str) -> dict[str, Any]:
    frontdesk_state: dict[str, Any] = {}
    if frontend_normalize_frontdesk_state is not None:
        try:
            frontdesk_state = frontend_normalize_frontdesk_state({}, "")
        except Exception:
            frontdesk_state = {}
    return {
        "schema_version": "ctcp-support-session-state-v7",
        "chat_id": chat_id,
        "bound_run_id": "",
        "bound_run_dir": "",
        "task_summary": "",
        "active_task_id": "",
        "active_run_id": "",
        "active_goal": "",
        "active_stage": "INTAKE",
        "active_stage_reason": "default_initialized",
        "active_stage_exit_condition": SUPPORT_STAGE_EXIT_RULES["INTAKE"],
        "active_blocker": "none",
        "active_next_action": "",
        "latest_message_intent": "continue",
        "latest_conversation_mode": "",
        "last_bridge_sync_ts": "",
        "latest_support_context": {},
        "frontdesk_state": frontdesk_state,
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
        "history_layers": {
            "raw_turns": [],
            "working_memory": {
                "current_goal": "",
                "current_constraints": "",
                "current_stage": "INTAKE",
                "pending_decision": "",
                "completed_results": [],
                "last_failure_reason": "",
                "next_action": "",
                "active_task_id": "",
                "active_run_id": "",
                "active_blocker": "none",
                "latest_message_intent": "continue",
            },
            "task_summary": {
                "task_goal": "",
                "confirmed_requirements": [],
                "completed_steps": [],
                "pending_steps": [],
                "current_risks": [],
                "result_location": "",
                "last_compaction_ts": "",
            },
            "user_preferences": {
                "language": "auto",
                "tone": "task_progressive",
                "initiative": "balanced",
                "verbosity": "normal",
                "avoid_mechanical": False,
                "prefer_push_to_delivery": False,
                "prefer_less_questions": False,
                "prefer_owner_report_style": True,
            },
        },
        "provider_runtime_buffer": {
            "preferred_provider": "",
            "attempted_providers": [],
            "last_provider": "",
            "last_provider_status": "",
            "last_provider_reason": "",
        },
        "reply_dedupe_memory": (
            frontend_default_reply_dedupe_memory(max_entries=48)
            if frontend_default_reply_dedupe_memory is not None
            else {"schema_version": "ctcp-reply-dedupe-memory-v1", "turn_index": 0, "max_entries": 48, "by_intent": {}}
        ),
        "notification_state": {
            "last_progress_hash": "",
            "last_progress_ts": "",
            "last_notified_run_id": "",
            "last_notified_phase": "",
            "last_auto_advance_ts": "",
            "last_seen_status_hash": "",
            "last_sent_message_hash": "",
            "last_sent_kind": "",
            "last_decision_prompt_hash": "",
            "cooldown_until_ts": "",
        },
        "controller_state": {
            "current": "BOOTSTRAP",
            "last_transition_ts": "",
            "last_reason": "",
        },
        "outbound_queue": {
            "pending_ids": [],
            "jobs": [],
        },
        "resume_state": {
            "last_resume_ts": "",
            "last_resume_source_dir": "",
            "last_resume_source_run_id": "",
            "last_resume_brief": "",
            "superseded_run_id": "",
        },
        "generation_state": {
            "current_state": "T0_PLAN",
            "last_trigger_text": "",
            "last_trigger_ts": "",
            "last_mode": "",
            "last_test_mode": "",
            "last_pass_fail": "",
            "last_failure_stage": "",
            "last_concise_reason": "",
            "last_command_or_entry": "",
            "last_out_dir": "",
            "last_run_dir": "",
            "last_generated_project_dir": "",
            "last_report_ts": "",
            "last_report_path": SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix(),
            "state_history": [],
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

def latest_reply_dedupe_memory(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "reply_dedupe_memory")

def latest_notification_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "notification_state")

def latest_controller_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "controller_state")

def latest_outbound_queue(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "outbound_queue")

def latest_resume_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "resume_state")

def latest_generation_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "generation_state")

def history_layers_state(session_state: dict[str, Any]) -> dict[str, Any]:
    return _state_zone(session_state, "history_layers")

def _append_history_turn(
    session_state: dict[str, Any],
    *,
    role: str,
    text: str,
    source: str,
    conversation_mode: str,
    message_intent: str = "",
    ts: str = "",
) -> None:
    sanitized_text = sanitize_inline_text(text, max_chars=360)
    if not sanitized_text:
        return
    layers = history_layers_state(session_state)
    rows = layers.get("raw_turns", [])
    if not isinstance(rows, list):
        rows = []
    row = {
        "ts": sanitize_inline_text(ts or now_iso(), max_chars=40),
        "role": sanitize_inline_text(role, max_chars=16) or "user",
        "source": sanitize_inline_text(source, max_chars=40),
        "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
        "message_intent": sanitize_inline_text(message_intent, max_chars=24),
        "text": sanitized_text,
    }
    rows.append(row)
    layers["raw_turns"] = rows[-SUPPORT_HISTORY_RAW_TURN_LIMIT:]

def _classify_message_intent(
    *,
    user_text: str,
    conversation_mode: str,
    frontdesk_state: dict[str, Any] | None,
    has_active_task: bool,
) -> str:
    mode = sanitize_inline_text(conversation_mode, max_chars=40).upper()
    if mode == "STATUS_QUERY":
        return "status_check"
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return "small_talk"
    interrupt = sanitize_inline_text(str((frontdesk_state or {}).get("interrupt_kind", "")), max_chars=24).lower()
    if interrupt == "clarify":
        return "clarify"
    if interrupt in {"override", "redirect", "sidequest"}:
        return "constraint_update"
    if mode == "PROJECT_INTAKE":
        if has_active_task and should_refresh_project_brief(user_text, mode) and (not is_project_execution_followup(user_text)):
            return "new_task"
        return "continue" if has_active_task else "new_task"
    if mode in {"PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return "continue" if has_active_task else "new_task"
    return "continue"

def _project_runtime_state(project_context: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(project_context, dict):
        return {}
    runtime_state = project_context.get("runtime_state", {})
    return runtime_state if isinstance(runtime_state, dict) else {}

def _runtime_phase_to_support_stage(phase: str) -> str:
    return runtime_phase_to_support_stage_impl(phase)

def _derive_active_stage(
    *,
    conversation_mode: str,
    frontdesk_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    delivery_state: dict[str, Any] | None,
    provider_result: dict[str, Any] | None,
) -> tuple[str, str]:
    mode = sanitize_inline_text(conversation_mode, max_chars=40).upper()
    state_name = sanitize_inline_text(str((frontdesk_state or {}).get("state", "")), max_chars=40).lower()
    runtime_state = _project_runtime_state(project_context)
    render_snapshot = {}
    if isinstance(project_context, dict):
        render_snapshot = project_context.get("render_snapshot", {}) or project_context.get("render_state_snapshot", {})
    if not isinstance(render_snapshot, dict):
        render_snapshot = {}
    runtime_phase = sanitize_inline_text(str(runtime_state.get("phase", "")), max_chars=40).upper()
    status = (project_context or {}).get("status", {}) if isinstance(project_context, dict) else {}
    if not isinstance(status, dict):
        status = {}
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    run_status = sanitize_inline_text(
        str(runtime_state.get("run_status", "")).strip() or str(status.get("run_status", "")).strip(),
        max_chars=40,
    ).lower()
    verify_result = sanitize_inline_text(
        str(runtime_state.get("verify_result", "")).strip() or str(status.get("verify_result", "")).strip(),
        max_chars=20,
    ).upper()
    gate_state = sanitize_inline_text(str(gate.get("state", "")), max_chars=40).lower()
    gate_owner = sanitize_inline_text(str(gate.get("owner", "")), max_chars=80).lower()
    gate_reason = sanitize_inline_text(str(gate.get("reason", "")), max_chars=220).lower()
    visible_state = sanitize_inline_text(str(render_snapshot.get("visible_state", "")), max_chars=40).upper()
    decision_cards = render_snapshot.get("decision_cards", [])
    if not isinstance(decision_cards, list):
        decision_cards = []
    needs_decision = bool(runtime_state.get("needs_user_decision", False)) or bool(decision_cards) or visible_state == "WAITING_FOR_DECISION"
    if not needs_decision:
        needs_decision = bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0
    provider_status = sanitize_inline_text(str((provider_result or {}).get("status", "")), max_chars=32).lower()
    provider_error = provider_status in {"exec_failed", "failed", "error"}
    runtime_error = runtime_state.get("error", {})
    if not isinstance(runtime_error, dict):
        runtime_error = {}
    run_error = bool(runtime_error.get("has_error", False)) or run_status in {"fail", "failed", "error", "aborted"} or gate_state in {"error", "failed"}
    final_ready = verify_result == "PASS" and run_status in _FINAL_READY_RUN_STATUSES and (not needs_decision)
    delivery_ready = bool((delivery_state or {}).get("package_ready", False) or (delivery_state or {}).get("screenshot_ready", False))
    runtime_stage = _runtime_phase_to_support_stage(runtime_phase)
    if runtime_stage in {"RETRYING", "RECOVERY_NEEDED", "EXEC_FAILED", "BLOCKED_HARD"}:
        return runtime_stage, f"canonical_phase:{runtime_phase.lower()}"

    if provider_error or run_error or bool((project_context or {}).get("error")):
        return "RECOVER", "runtime_or_provider_failure"
    if runtime_stage:
        if runtime_stage == "DELIVER" and (not delivery_ready) and state_name != "showing_result":
            return "FINALIZE", f"canonical_phase:{runtime_phase.lower()}_pending_delivery"
        return runtime_stage, f"canonical_phase:{runtime_phase.lower()}"
    if needs_decision or state_name == "showing_decision":
        return "WAIT_USER_DECISION", "decision_required"
    if final_ready and (delivery_ready or state_name == "showing_result"):
        return "DELIVER", "final_ready_for_delivery"
    if final_ready:
        return "FINALIZE", "final_ready_pending_delivery_payload"
    if state_name == "waiting_user_reply":
        return "CLARIFY", "frontdesk_clarify_state"
    if state_name in {"collecting_input", "idle"} or mode in {"PROJECT_INTAKE", "GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        return "INTAKE", "intake_or_non_project_turn"
    if state_name == "showing_error":
        return "RECOVER", "frontdesk_error_state"
    if state_name == "showing_progress":
        if gate_state == "blocked" and ("review" in gate_owner or "review" in gate_reason or "verify" in gate_reason):
            return "VERIFY", "gate_blocked_on_review_verify_step"
        return "EXECUTE", "active_execution_state"
    if state_name == "showing_result":
        return "FINALIZE", "result_packaging_state"
    if run_status in {"running", "in_progress", "working"}:
        return "EXECUTE", "run_status_running"
    return "INTAKE", "default_stage"

def _sync_history_preferences_from_style(
    session_state: dict[str, Any],
    *,
    user_text: str,
    frontdesk_state: dict[str, Any] | None,
) -> None:
    layers = history_layers_state(session_state)
    prefs = _state_zone(layers, "user_preferences")
    style_profile = (frontdesk_state or {}).get("user_style_profile", {})
    if isinstance(style_profile, dict):
        language = sanitize_inline_text(str(style_profile.get("language", "")), max_chars=12).lower()
        tone = sanitize_inline_text(str(style_profile.get("tone", "")), max_chars=40).lower()
        initiative = sanitize_inline_text(str(style_profile.get("initiative", "")), max_chars=24).lower()
        verbosity = sanitize_inline_text(str(style_profile.get("verbosity", "")), max_chars=24).lower()
        if language:
            prefs["language"] = language
        if tone:
            prefs["tone"] = tone
        if initiative:
            prefs["initiative"] = initiative
        if verbosity:
            prefs["verbosity"] = verbosity
    raw = sanitize_inline_text(user_text, max_chars=280).lower()
    if any(token in raw for token in ("别机械", "不要机械", "not so mechanical", "natural")):
        prefs["avoid_mechanical"] = True
    if any(token in raw for token in ("一次推进到底", "继续推进", "push to delivery", "继续做")):
        prefs["prefer_push_to_delivery"] = True
    if any(token in raw for token in ("少确认", "少问", "ask only when needed", "less proactive")):
        prefs["prefer_less_questions"] = True
    if any(token in raw for token in ("像负责人", "负责人汇报", "owner-style", "manager")):
        prefs["prefer_owner_report_style"] = True

def sync_active_task_truth(
    session_state: dict[str, Any],
    *,
    user_text: str,
    source: str,
    conversation_mode: str,
    frontdesk_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    delivery_state: dict[str, Any] | None = None,
    provider_result: dict[str, Any] | None = None,
    assistant_reply_text: str = "",
    rewrite_latest_user_turn: bool = True,
) -> None:
    previous_goal = sanitize_inline_text(str(session_state.get("active_goal", "")), max_chars=280)
    previous_task_id = sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80)
    previous_run_id = sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80)
    current_goal = sanitize_inline_text(
        str((frontdesk_state or {}).get("current_goal", "")).strip() or current_project_brief(session_state),
        max_chars=280,
    )
    run_id = sanitize_inline_text(
        str(session_state.get("bound_run_id", "")).strip()
        or str((project_context or {}).get("run_id", "")).strip()
        or previous_run_id,
        max_chars=80,
    )
    has_active_task = bool(previous_task_id or previous_goal or current_goal or run_id)
    message_intent = _classify_message_intent(
        user_text=user_text,
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        has_active_task=has_active_task,
    )
    stage, stage_reason = _derive_active_stage(
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
        delivery_state=delivery_state,
        provider_result=provider_result,
    )
    if assistant_reply_text and stage == "DELIVER":
        stage = "DELIVERED"
        stage_reason = "delivery_reply_emitted"

    binding = build_progress_binding(project_context=project_context, task_summary_hint=current_goal)
    blocker = sanitize_inline_text(
        str(binding.get("current_blocker", "")).strip() if isinstance(binding, dict) else "",
        max_chars=220,
    ) or sanitize_inline_text(str((frontdesk_state or {}).get("blocked_reason", "")), max_chars=220) or "none"
    next_action = sanitize_inline_text(
        str(binding.get("next_action", "")).strip() if isinstance(binding, dict) else "",
        max_chars=220,
    )
    if not next_action:
        next_action = sanitize_inline_text(str((frontdesk_state or {}).get("waiting_for", "")), max_chars=220)
    if not next_action:
        next_action = "继续按当前主任务推进，并在阶段变化时同步。"

    if message_intent != "new_task":
        if not current_goal:
            current_goal = previous_goal
        if not run_id:
            run_id = previous_run_id
    active_task_id = run_id or previous_task_id
    if (message_intent == "new_task") and current_goal and (not active_task_id):
        digest = hashlib.sha1(current_goal.encode("utf-8", errors="replace")).hexdigest()[:10]
        active_task_id = f"task-{digest}"

    session_state["active_task_id"] = active_task_id
    session_state["active_run_id"] = run_id
    session_state["active_goal"] = current_goal
    session_state["active_stage"] = stage
    session_state["active_stage_reason"] = stage_reason
    session_state["active_stage_exit_condition"] = SUPPORT_STAGE_EXIT_RULES.get(stage, "")
    session_state["active_blocker"] = blocker
    session_state["active_next_action"] = next_action
    session_state["latest_message_intent"] = message_intent

    layers = history_layers_state(session_state)
    working_memory = _state_zone(layers, "working_memory")
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    execution_memory = _state_zone(session_state, "execution_memory")
    working_memory["current_goal"] = current_goal
    working_memory["current_constraints"] = sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=280)
    working_memory["current_stage"] = stage
    working_memory["pending_decision"] = sanitize_inline_text(str((frontdesk_state or {}).get("waiting_for", "")), max_chars=220)
    completed_items = binding.get("last_confirmed_items", []) if isinstance(binding, dict) else []
    if not isinstance(completed_items, list):
        completed_items = []
    working_memory["completed_results"] = [sanitize_inline_text(str(x), max_chars=220) for x in completed_items if str(x).strip()][:6]
    working_memory["last_failure_reason"] = sanitize_inline_text(str((project_context or {}).get("error", "")), max_chars=220)
    working_memory["next_action"] = next_action
    working_memory["active_task_id"] = active_task_id
    working_memory["active_run_id"] = run_id
    working_memory["active_blocker"] = blocker
    working_memory["latest_message_intent"] = message_intent

    summary = _state_zone(layers, "task_summary")
    summary["task_goal"] = current_goal
    confirmed_requirements = [
        sanitize_inline_text(str(project_constraints.get("constraint_brief", "")), max_chars=220),
        sanitize_inline_text(str(execution_memory.get("latest_user_directive", "")), max_chars=220),
    ]
    summary["confirmed_requirements"] = [x for x in confirmed_requirements if x][:6]
    summary["completed_steps"] = [sanitize_inline_text(str(x), max_chars=220) for x in completed_items if str(x).strip()][:6]
    summary["pending_steps"] = [next_action] if next_action else []
    summary["current_risks"] = [] if blocker in {"", "none"} else [blocker]
    summary["result_location"] = sanitize_inline_text(str(session_state.get("bound_run_dir", "")), max_chars=260) or run_id
    summary["last_compaction_ts"] = now_iso()

    _sync_history_preferences_from_style(session_state, user_text=user_text, frontdesk_state=frontdesk_state)
    rows = layers.get("raw_turns", [])
    if rewrite_latest_user_turn and isinstance(rows, list):
        for item in reversed(rows):
            if not isinstance(item, dict):
                continue
            if sanitize_inline_text(str(item.get("role", "")), max_chars=16).lower() != "user":
                continue
            item["message_intent"] = message_intent
            item["conversation_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)
            break
    if assistant_reply_text:
        _append_history_turn(
            session_state,
            role="assistant",
            text=assistant_reply_text,
            source=source,
            conversation_mode=conversation_mode,
            message_intent=message_intent,
        )

def _shared_task_id(
    *,
    chat_id: str,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
) -> str:
    run_id = sanitize_inline_text(str((project_context or {}).get("run_id", "")), max_chars=80)
    if run_id:
        return run_id
    active_task_id = sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80)
    if active_task_id:
        return active_task_id
    safe_chat = sanitize_inline_text(chat_id, max_chars=80)
    if safe_chat:
        return f"support-{safe_chat}"
    return ""

def _to_authoritative_stage(
    *,
    runtime_phase: str,
    session_stage: str,
    run_status: str,
    verify_result: str,
    needs_user_decision: bool,
) -> str:
    return authoritative_stage_for_runtime_impl(
        runtime_phase=runtime_phase,
        session_stage=session_stage,
        run_status=run_status,
        verify_result=verify_result,
        needs_user_decision=needs_user_decision,
        final_ready_statuses=_FINAL_READY_RUN_STATUSES,
    )

def sync_shared_state_workspace(
    *,
    chat_id: str,
    user_text: str,
    source: str,
    conversation_mode: str,
    session_state: dict[str, Any],
    frontdesk_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
) -> dict[str, Any]:
    if SharedStateStore is None:
        return {}
    try:
        store = SharedStateStore()
    except Exception:
        return {}
    task_id = _shared_task_id(chat_id=chat_id, session_state=session_state, project_context=project_context)
    if not task_id:
        return {}
    status = (project_context or {}).get("status", {}) if isinstance(project_context, dict) else {}
    if not isinstance(status, dict):
        status = {}
    runtime_state = _project_runtime_state(project_context)
    runtime_phase = sanitize_inline_text(str(runtime_state.get("phase", "")), max_chars=40)
    run_status = sanitize_inline_text(str(status.get("run_status", "")), max_chars=24).lower()
    verify_result = sanitize_inline_text(str(status.get("verify_result", "")), max_chars=16).upper()
    if not run_status:
        run_status = sanitize_inline_text(str(runtime_state.get("run_status", "")), max_chars=24).lower()
    if not verify_result:
        verify_result = sanitize_inline_text(str(runtime_state.get("verify_result", "")), max_chars=16).upper()
    needs_user_decision = bool(runtime_state.get("needs_user_decision", False))
    if not needs_user_decision:
        needs_user_decision = bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0
    progress = build_progress_binding(
        project_context=project_context if isinstance(project_context, dict) else None,
        task_summary_hint=current_project_brief(session_state),
    )
    authoritative_stage = _to_authoritative_stage(
        runtime_phase=runtime_phase,
        session_stage=str(session_state.get("active_stage", "")),
        run_status=run_status,
        verify_result=verify_result,
        needs_user_decision=needs_user_decision,
    )
    frontend_source = "frontdesk" if str(source or "").strip().lower() in {"telegram", "stdin", "selftest"} else "frontend"
    runtime_payload = {
        "current_task_goal": sanitize_inline_text(str(progress.get("current_task_goal", "")), max_chars=260),
        "last_confirmed_items": list(progress.get("last_confirmed_items", [])) if isinstance(progress.get("last_confirmed_items", []), list) else [],
        "current_blocker": sanitize_inline_text(str(progress.get("current_blocker", "none")), max_chars=220),
        "blocking_question": sanitize_inline_text(str(progress.get("blocking_question", "")), max_chars=220),
        "next_action": sanitize_inline_text(str(progress.get("next_action", "")), max_chars=220),
        "proof_refs": list(progress.get("proof_refs", [])) if isinstance(progress.get("proof_refs", []), list) else [],
        "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
    }
    try:
        store.append_event(
            task_id=task_id,
            event_type="user_message",
            source=frontend_source,
            payload={
                "text": sanitize_inline_text(user_text, max_chars=600),
                "current_task_goal": sanitize_inline_text(str(session_state.get("active_goal", "")), max_chars=260),
            },
        )
        store.append_event(
            task_id=task_id,
            event_type="conversation_mode_detected",
            source=frontend_source,
            payload={"conversation_mode_guess": sanitize_inline_text(conversation_mode, max_chars=40)},
        )
        if str(conversation_mode or "").strip().upper() == "PROJECT_DECISION_REPLY":
            store.append_event(
                task_id=task_id,
                event_type="user_decision_recorded",
                source=frontend_source,
                payload={"user_decision": sanitize_inline_text(user_text, max_chars=280)},
            )
        store.append_event(
            task_id=task_id,
            event_type="authoritative_stage_changed",
            source="runtime",
            payload={
                "authoritative_stage": authoritative_stage,
                "execution_status": run_status or sanitize_inline_text(str(status.get("gate", "")), max_chars=24),
            },
        )
        store.append_event(
            task_id=task_id,
            event_type="runtime_progress_recorded",
            source="runtime",
            payload=runtime_payload,
        )
        store.append_event(
            task_id=task_id,
            event_type="blocker_changed",
            source="runtime",
            payload={
                "current_blocker": runtime_payload["current_blocker"] or "none",
                "blocking_question": runtime_payload["blocking_question"],
            },
        )
        store.append_event(
            task_id=task_id,
            event_type="next_action_set",
            source="runtime",
            payload={"next_action": runtime_payload["next_action"] or "继续推进当前任务"},
        )
        if verify_result:
            verify_payload = {
                "verify_result": verify_result,
                "proof_refs": runtime_payload["proof_refs"],
            }
            store.append_event(
                task_id=task_id,
                event_type="verification_result_recorded",
                source="runtime",
                payload=verify_payload,
            )
        current = store.rebuild_current(task_id)
        render = store.refresh_render(task_id, source="runtime", emit_event=True)
        return {
            "task_id": task_id,
            "current": current,
            "render": render,
            "workspace_root": str(store.workspace_root),
        }
    except Exception as exc:
        append_log(session_run_dir(chat_id) / "logs" / "support_bot.debug.log", f"[{now_iso()}] shared state sync failed: {exc}\n")
        return {}

def current_frontdesk_state(session_state: dict[str, Any]) -> dict[str, Any]:
    raw = session_state.get("frontdesk_state")
    if not isinstance(raw, dict):
        raw = {}
    if frontend_normalize_frontdesk_state is not None:
        try:
            normalized = frontend_normalize_frontdesk_state(
                raw,
                sanitize_inline_text(str(_state_zone(session_state, "session_profile").get("lang_hint", "")), max_chars=12).lower(),
            )
            session_state["frontdesk_state"] = normalized
            return normalized
        except Exception:
            pass
    session_state["frontdesk_state"] = raw
    return raw

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
                "history_layers",
                "provider_runtime_buffer",
                "reply_dedupe_memory",
                "notification_state",
                "controller_state",
                "outbound_queue",
                "resume_state",
                "generation_state",
                "latest_support_context",
                "frontdesk_state",
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
    history_layers = _state_zone(state, "history_layers")
    session_profile = _state_zone(state, "session_profile")
    provider_runtime = _state_zone(state, "provider_runtime_buffer")
    reply_dedupe_memory = _state_zone(state, "reply_dedupe_memory")
    notification_state = _state_zone(state, "notification_state")
    controller_state = _state_zone(state, "controller_state")
    outbound_queue = _state_zone(state, "outbound_queue")
    resume_state = _state_zone(state, "resume_state")
    generation_state = _state_zone(state, "generation_state")
    frontdesk_state = state.get("frontdesk_state")
    if not isinstance(frontdesk_state, dict):
        frontdesk_state = {}
    state["frontdesk_state"] = frontdesk_state
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

    raw_turns = history_layers.get("raw_turns", [])
    if not isinstance(raw_turns, list):
        raw_turns = []
    normalized_raw_turns: list[dict[str, Any]] = []
    for item in raw_turns[-SUPPORT_HISTORY_RAW_TURN_LIMIT:]:
        if not isinstance(item, dict):
            continue
        text = sanitize_inline_text(str(item.get("text", "")), max_chars=360)
        if not text:
            continue
        normalized_raw_turns.append(
            {
                "ts": sanitize_inline_text(str(item.get("ts", "")), max_chars=40),
                "role": sanitize_inline_text(str(item.get("role", "user")), max_chars=16) or "user",
                "source": sanitize_inline_text(str(item.get("source", "")), max_chars=40),
                "conversation_mode": sanitize_inline_text(str(item.get("conversation_mode", "")), max_chars=40),
                "message_intent": sanitize_inline_text(str(item.get("message_intent", "")), max_chars=24),
                "text": text,
            }
        )
    history_layers["raw_turns"] = normalized_raw_turns

    working_memory = _state_zone(history_layers, "working_memory")
    working_memory["current_goal"] = sanitize_inline_text(str(working_memory.get("current_goal", "")), max_chars=280)
    working_memory["current_constraints"] = sanitize_inline_text(str(working_memory.get("current_constraints", "")), max_chars=280)
    working_memory["current_stage"] = sanitize_inline_text(str(working_memory.get("current_stage", "INTAKE")), max_chars=32)
    if working_memory["current_stage"] not in SUPPORT_ACTIVE_STAGES:
        working_memory["current_stage"] = "INTAKE"
    working_memory["pending_decision"] = sanitize_inline_text(str(working_memory.get("pending_decision", "")), max_chars=220)
    completed_results = working_memory.get("completed_results", [])
    if not isinstance(completed_results, list):
        completed_results = []
    working_memory["completed_results"] = [sanitize_inline_text(str(x), max_chars=220) for x in completed_results if str(x).strip()][:6]
    working_memory["last_failure_reason"] = sanitize_inline_text(str(working_memory.get("last_failure_reason", "")), max_chars=220)
    working_memory["next_action"] = sanitize_inline_text(str(working_memory.get("next_action", "")), max_chars=220)
    working_memory["active_task_id"] = sanitize_inline_text(str(working_memory.get("active_task_id", "")), max_chars=80)
    working_memory["active_run_id"] = sanitize_inline_text(str(working_memory.get("active_run_id", "")), max_chars=80)
    working_memory["active_blocker"] = sanitize_inline_text(str(working_memory.get("active_blocker", "none")), max_chars=220) or "none"
    working_memory["latest_message_intent"] = sanitize_inline_text(
        str(working_memory.get("latest_message_intent", "continue")),
        max_chars=24,
    )
    if working_memory["latest_message_intent"] not in SUPPORT_MESSAGE_INTENTS:
        working_memory["latest_message_intent"] = "continue"

    task_summary_layer = _state_zone(history_layers, "task_summary")
    task_summary_layer["task_goal"] = sanitize_inline_text(str(task_summary_layer.get("task_goal", "")), max_chars=280)
    confirmed_requirements = task_summary_layer.get("confirmed_requirements", [])
    if not isinstance(confirmed_requirements, list):
        confirmed_requirements = []
    task_summary_layer["confirmed_requirements"] = [
        sanitize_inline_text(str(x), max_chars=220) for x in confirmed_requirements if str(x).strip()
    ][:8]
    completed_steps = task_summary_layer.get("completed_steps", [])
    if not isinstance(completed_steps, list):
        completed_steps = []
    task_summary_layer["completed_steps"] = [sanitize_inline_text(str(x), max_chars=220) for x in completed_steps if str(x).strip()][:8]
    pending_steps = task_summary_layer.get("pending_steps", [])
    if not isinstance(pending_steps, list):
        pending_steps = []
    task_summary_layer["pending_steps"] = [sanitize_inline_text(str(x), max_chars=220) for x in pending_steps if str(x).strip()][:8]
    current_risks = task_summary_layer.get("current_risks", [])
    if not isinstance(current_risks, list):
        current_risks = []
    task_summary_layer["current_risks"] = [sanitize_inline_text(str(x), max_chars=220) for x in current_risks if str(x).strip()][:6]
    task_summary_layer["result_location"] = sanitize_inline_text(str(task_summary_layer.get("result_location", "")), max_chars=260)
    task_summary_layer["last_compaction_ts"] = sanitize_inline_text(str(task_summary_layer.get("last_compaction_ts", "")), max_chars=40)

    user_preferences = _state_zone(history_layers, "user_preferences")
    user_preferences["language"] = sanitize_inline_text(str(user_preferences.get("language", "auto")), max_chars=12) or "auto"
    user_preferences["tone"] = sanitize_inline_text(str(user_preferences.get("tone", "task_progressive")), max_chars=40) or "task_progressive"
    user_preferences["initiative"] = sanitize_inline_text(
        str(user_preferences.get("initiative", "balanced")),
        max_chars=24,
    ) or "balanced"
    user_preferences["verbosity"] = sanitize_inline_text(str(user_preferences.get("verbosity", "normal")), max_chars=24) or "normal"
    user_preferences["avoid_mechanical"] = bool(user_preferences.get("avoid_mechanical", False))
    user_preferences["prefer_push_to_delivery"] = bool(user_preferences.get("prefer_push_to_delivery", False))
    user_preferences["prefer_less_questions"] = bool(user_preferences.get("prefer_less_questions", False))
    user_preferences["prefer_owner_report_style"] = bool(user_preferences.get("prefer_owner_report_style", True))

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
    if frontend_normalize_reply_dedupe_memory is not None:
        try:
            state["reply_dedupe_memory"] = frontend_normalize_reply_dedupe_memory(reply_dedupe_memory, max_entries=48)
        except Exception:
            state["reply_dedupe_memory"] = {
                "schema_version": "ctcp-reply-dedupe-memory-v1",
                "turn_index": 0,
                "max_entries": 48,
                "by_intent": {},
            }
    else:
        reply_dedupe_memory["schema_version"] = sanitize_inline_text(
            str(reply_dedupe_memory.get("schema_version", "ctcp-reply-dedupe-memory-v1")),
            max_chars=64,
        ) or "ctcp-reply-dedupe-memory-v1"
        reply_dedupe_memory["turn_index"] = int(reply_dedupe_memory.get("turn_index", 0) or 0)
        reply_dedupe_memory["max_entries"] = max(12, min(200, int(reply_dedupe_memory.get("max_entries", 48) or 48)))
        if not isinstance(reply_dedupe_memory.get("by_intent"), dict):
            reply_dedupe_memory["by_intent"] = {}
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
    notification_state["last_seen_status_hash"] = sanitize_inline_text(
        str(notification_state.get("last_seen_status_hash", "")), max_chars=80
    )
    notification_state["last_sent_message_hash"] = sanitize_inline_text(
        str(notification_state.get("last_sent_message_hash", "")), max_chars=80
    )
    notification_state["last_sent_kind"] = sanitize_inline_text(
        str(notification_state.get("last_sent_kind", "")), max_chars=24
    )
    notification_state["last_decision_prompt_hash"] = sanitize_inline_text(
        str(notification_state.get("last_decision_prompt_hash", "")), max_chars=80
    )
    notification_state["cooldown_until_ts"] = sanitize_inline_text(
        str(notification_state.get("cooldown_until_ts", "")), max_chars=40
    )
    controller_state["current"] = (
        sanitize_inline_text(str(controller_state.get("current", "BOOTSTRAP")), max_chars=40) or "BOOTSTRAP"
    )
    controller_state["last_transition_ts"] = sanitize_inline_text(
        str(controller_state.get("last_transition_ts", "")), max_chars=40
    )
    controller_state["last_reason"] = sanitize_inline_text(str(controller_state.get("last_reason", "")), max_chars=220)
    pending_ids = outbound_queue.get("pending_ids", [])
    if not isinstance(pending_ids, list):
        pending_ids = []
    outbound_queue["pending_ids"] = [
        sanitize_inline_text(str(item), max_chars=120)
        for item in pending_ids
        if sanitize_inline_text(str(item), max_chars=120)
    ][-64:]
    jobs = outbound_queue.get("jobs", [])
    if not isinstance(jobs, list):
        jobs = []
    normalized_jobs: list[dict[str, Any]] = []
    for item in jobs[-32:]:
        if not isinstance(item, dict):
            continue
        normalized_jobs.append(
            {
                "id": sanitize_inline_text(str(item.get("id", "")), max_chars=120),
                "kind": sanitize_inline_text(str(item.get("kind", "")), max_chars=24),
                "run_id": sanitize_inline_text(str(item.get("run_id", "")), max_chars=80),
                "status_hash": sanitize_inline_text(str(item.get("status_hash", "")), max_chars=80),
                "reason": sanitize_inline_text(str(item.get("reason", "")), max_chars=220),
                "message_hash": sanitize_inline_text(str(item.get("message_hash", "")), max_chars=80),
                "decision_prompt": sanitize_inline_text(str(item.get("decision_prompt", "")), max_chars=280),
                "decision_prompt_hash": sanitize_inline_text(str(item.get("decision_prompt_hash", "")), max_chars=80),
                "created_ts": sanitize_inline_text(str(item.get("created_ts", "")), max_chars=40),
            }
        )
    outbound_queue["jobs"] = normalized_jobs
    resume_state["last_resume_ts"] = sanitize_inline_text(str(resume_state.get("last_resume_ts", "")), max_chars=40)
    resume_state["last_resume_source_dir"] = sanitize_inline_text(
        str(resume_state.get("last_resume_source_dir", "")), max_chars=260
    )
    resume_state["last_resume_source_run_id"] = sanitize_inline_text(
        str(resume_state.get("last_resume_source_run_id", "")), max_chars=80
    )
    resume_state["last_resume_brief"] = sanitize_inline_text(str(resume_state.get("last_resume_brief", "")), max_chars=280)
    resume_state["superseded_run_id"] = sanitize_inline_text(str(resume_state.get("superseded_run_id", "")), max_chars=80)
    generation_state["current_state"] = sanitize_inline_text(str(generation_state.get("current_state", "T0_PLAN")), max_chars=32) or "T0_PLAN"
    generation_state["last_trigger_text"] = sanitize_inline_text(
        str(generation_state.get("last_trigger_text", "")), max_chars=280
    )
    generation_state["last_trigger_ts"] = sanitize_inline_text(str(generation_state.get("last_trigger_ts", "")), max_chars=40)
    generation_state["last_mode"] = sanitize_inline_text(str(generation_state.get("last_mode", "")), max_chars=40)
    generation_state["last_test_mode"] = sanitize_inline_text(str(generation_state.get("last_test_mode", "")), max_chars=40)
    generation_state["last_pass_fail"] = sanitize_inline_text(str(generation_state.get("last_pass_fail", "")), max_chars=12)
    generation_state["last_failure_stage"] = sanitize_inline_text(
        str(generation_state.get("last_failure_stage", "")), max_chars=40
    )
    generation_state["last_concise_reason"] = sanitize_inline_text(
        str(generation_state.get("last_concise_reason", "")), max_chars=220
    )
    generation_state["last_command_or_entry"] = sanitize_inline_text(
        str(generation_state.get("last_command_or_entry", "")), max_chars=120
    )
    generation_state["last_out_dir"] = sanitize_inline_text(str(generation_state.get("last_out_dir", "")), max_chars=320)
    generation_state["last_run_dir"] = sanitize_inline_text(str(generation_state.get("last_run_dir", "")), max_chars=320)
    generation_state["last_generated_project_dir"] = sanitize_inline_text(
        str(generation_state.get("last_generated_project_dir", "")), max_chars=320
    )
    generation_state["last_report_ts"] = sanitize_inline_text(str(generation_state.get("last_report_ts", "")), max_chars=40)
    generation_state["last_report_path"] = sanitize_inline_text(
        str(generation_state.get("last_report_path", SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix())),
        max_chars=220,
    )
    state_history = generation_state.get("state_history", [])
    if not isinstance(state_history, list):
        state_history = []
    normalized_history: list[dict[str, Any]] = []
    for item in state_history[-24:]:
        if not isinstance(item, dict):
            continue
        normalized_history.append(
            {
                "state": sanitize_inline_text(str(item.get("state", "")), max_chars=32),
                "ts": sanitize_inline_text(str(item.get("ts", "")), max_chars=40),
                "note": sanitize_inline_text(str(item.get("note", "")), max_chars=220),
            }
        )
    generation_state["state_history"] = normalized_history

    if frontend_normalize_frontdesk_state is not None:
        try:
            state["frontdesk_state"] = frontend_normalize_frontdesk_state(
                frontdesk_state,
                sanitize_inline_text(str(session_profile.get("lang_hint", "")), max_chars=12).lower(),
            )
        except Exception:
            state["frontdesk_state"] = frontdesk_state

    state["task_summary"] = current_project_brief(state)
    state["active_task_id"] = sanitize_inline_text(str(state.get("active_task_id", "")), max_chars=80)
    state["active_run_id"] = sanitize_inline_text(str(state.get("active_run_id", "")), max_chars=80)
    state["active_goal"] = sanitize_inline_text(str(state.get("active_goal", "")), max_chars=280)
    state["active_stage"] = sanitize_inline_text(str(state.get("active_stage", "INTAKE")), max_chars=32) or "INTAKE"
    if state["active_stage"] not in SUPPORT_ACTIVE_STAGES:
        state["active_stage"] = "INTAKE"
    state["active_stage_reason"] = sanitize_inline_text(str(state.get("active_stage_reason", "")), max_chars=220)
    state["active_stage_exit_condition"] = sanitize_inline_text(
        str(state.get("active_stage_exit_condition", SUPPORT_STAGE_EXIT_RULES.get(str(state["active_stage"]), ""))),
        max_chars=120,
    ) or SUPPORT_STAGE_EXIT_RULES.get(str(state["active_stage"]), "")
    state["active_blocker"] = sanitize_inline_text(str(state.get("active_blocker", "none")), max_chars=220) or "none"
    state["active_next_action"] = sanitize_inline_text(str(state.get("active_next_action", "")), max_chars=220)
    state["latest_message_intent"] = sanitize_inline_text(str(state.get("latest_message_intent", "continue")), max_chars=24) or "continue"
    if state["latest_message_intent"] not in SUPPORT_MESSAGE_INTENTS:
        state["latest_message_intent"] = "continue"
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
    _append_history_turn(
        session_state,
        role="user",
        text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        message_intent=sanitize_inline_text(str(session_state.get("latest_message_intent", "")), max_chars=24),
    )

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
    frontdesk_state = current_frontdesk_state(session_state)
    summary = sanitize_inline_text(
        str(session_state.get("active_goal", "")).strip()
        or str(frontdesk_state.get("current_goal", "")).strip()
        or current_project_brief(session_state),
        max_chars=280,
    )
    project_constraints = _state_zone(session_state, "project_constraints_memory")
    execution_memory = _state_zone(session_state, "execution_memory")
    active_task_id = sanitize_inline_text(
        str(session_state.get("active_task_id", "")).strip()
        or str(frontdesk_state.get("active_task_id", "")).strip()
        or str(session_state.get("bound_run_id", "")).strip(),
        max_chars=80,
    )
    active_run_id = sanitize_inline_text(
        str(session_state.get("active_run_id", "")).strip() or str(session_state.get("bound_run_id", "")).strip(),
        max_chars=80,
    )
    return {
        "task_summary": summary,
        "user_goal": summary,
        "run_id": active_run_id,
        "active_task_id": active_task_id,
        "active_run_id": active_run_id,
        "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
        "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220) or "none",
        "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
        "latest_message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
        "has_bound_run": bool(active_run_id),
        "current_scope": sanitize_inline_text(str(frontdesk_state.get("current_scope", "")), max_chars=280),
        "waiting_for": sanitize_inline_text(str(frontdesk_state.get("waiting_for", "")), max_chars=220),
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

def recover_invalid_bound_run(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    stale_run_id: str,
    error_text: str,
    trigger: str,
) -> dict[str, Any]:
    recovered = build_stale_bound_run_context(
        session_state=session_state,
        stale_run_id=stale_run_id,
        error_text=error_text,
    )
    session_state["bound_run_id"] = ""
    session_state["bound_run_dir"] = ""
    session_state["last_bridge_sync_ts"] = now_iso()
    session_state["latest_support_context"] = {
        "run_id": "",
        "goal": str(recovered.get("goal", "")),
        "status": recovered.get("status", {}),
        "runtime_state": recovered.get("runtime_state", {}),
        "whiteboard": {},
        "error": str(recovered.get("error", "")),
        "recovery": recovered.get("support_recovery", {}),
    }
    session_state["active_stage"] = "RECOVER"
    session_state["active_stage_reason"] = "stale_bound_run_cleared"
    session_state["active_stage_exit_condition"] = SUPPORT_STAGE_EXIT_RULES.get("RECOVER", "")
    session_state["active_blocker"] = sanitize_inline_text(str(recovered.get("error", "")), max_chars=220) or "none"
    session_state["active_next_action"] = sanitize_inline_text(
        str(dict(recovered.get("support_recovery", {})).get("hint", "")),
        max_chars=220,
    )
    working_memory = _state_zone(history_layers_state(session_state), "working_memory")
    working_memory["last_failure_reason"] = sanitize_inline_text(str(recovered.get("error", "")), max_chars=220)
    working_memory["next_action"] = sanitize_inline_text(session_state.get("active_next_action", ""), max_chars=220)
    append_event(
        run_dir,
        "SUPPORT_STALE_RUN_RECOVERED",
        SUPPORT_SESSION_STATE_REL_PATH.as_posix(),
        trigger=sanitize_inline_text(trigger, max_chars=40),
        stale_run_id=sanitize_inline_text(stale_run_id, max_chars=80),
        preserved_goal=sanitize_inline_text(str(recovered.get("goal", "")), max_chars=280),
    )
    append_log(
        run_dir / "logs" / "support_bot.debug.log",
        f"[{now_iso()}] stale bound run cleared trigger={trigger} run_id={stale_run_id} reason={error_text}\n",
    )
    return recovered

def fetch_support_context_with_recovery(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    bound_run_id: str,
    trigger: str,
) -> tuple[dict[str, Any], bool]:
    try:
        context = ctcp_front_bridge.ctcp_get_support_context(bound_run_id)
        return context if isinstance(context, dict) else {}, False
    except Exception as exc:
        error_text = sanitize_inline_text(str(exc), max_chars=220) or "bridge failed"
        if "run_id not found" not in error_text.lower():
            raise
        recovered = recover_invalid_bound_run(
            run_dir=run_dir,
            session_state=session_state,
            stale_run_id=bound_run_id,
            error_text=error_text,
            trigger=trigger,
        )
        return recovered, True

def is_project_create_intent(user_text: str, conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    if mode not in {"PROJECT_INTAKE", "PROJECT_DETAIL", "PROJECT_DECISION_REPLY"}:
        return False
    raw = sanitize_inline_text(user_text, max_chars=280)
    if not raw:
        return False
    low = raw.lower()
    if any(token in raw for token in PROJECT_CREATE_INTENT_HINTS_ZH):
        return True
    if any(token in low for token in PROJECT_CREATE_INTENT_HINTS_EN):
        return True
    if has_project_goal_markers(raw) and (
        ("创建" in raw)
        or ("搭建" in raw)
        or ("生成" in raw)
        or ("做一个" in raw)
        or ("create" in low)
        or ("build" in low)
        or ("generate" in low)
        or ("make a" in low)
    ):
        return True
    return False

def should_trigger_t2p_state_machine(
    *,
    session_state: dict[str, Any],
    user_text: str,
    source: str,
    conversation_mode: str,
) -> bool:
    # Single-mainline policy:
    # project turns must only progress through bridge-backed CTCP run state,
    # and must not trigger the support-side fast scaffold path.
    _ = (session_state, user_text, source, conversation_mode)
    return False


def interactive_reply_advance_steps(*, created: bool) -> int:
    return 2 if created else 1

def _record_generation_state(
    generation_state: dict[str, Any],
    *,
    state_code: str,
    note: str = "",
) -> None:
    generation_state["current_state"] = sanitize_inline_text(state_code, max_chars=32) or "T0_PLAN"
    history = generation_state.get("state_history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "state": sanitize_inline_text(state_code, max_chars=32),
            "ts": now_iso(),
            "note": sanitize_inline_text(note, max_chars=220),
        }
    )
    generation_state["state_history"] = history[-24:]

def _locate_latest_scaffold_report(run_dir: Path, scaffold_run_dir: Path | None) -> Path | None:
    candidates: list[Path] = []
    if scaffold_run_dir is not None:
        for name in ("scaffold_report.json", "scaffold_pointcloud_report.json"):
            path = scaffold_run_dir / "artifacts" / name
            if path.exists() and path.is_file():
                candidates.append(path.resolve())
    root = run_dir / "artifacts" / "support_scaffold_runs"
    if root.exists():
        for name in ("scaffold_report.json", "scaffold_pointcloud_report.json"):
            for path in root.rglob(name):
                if path.is_file():
                    candidates.append(path.resolve())
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]

def _verify_t2p_chain_artifacts(
    *,
    support_run_dir: Path,
    out_dir: Path,
    scaffold_run_dir: Path | None,
    source: str,
) -> tuple[list[dict[str, str]], str, str, str]:
    checked: list[dict[str, str]] = []
    first_failure_stage = "none"
    first_failure_reason = ""

    def record(path_label: str, ok: bool, *, stage_on_fail: str, na: bool = False, reason: str = "") -> None:
        nonlocal first_failure_stage, first_failure_reason
        status = "N/A" if na else ("PASS" if ok else "FAIL")
        row: dict[str, str] = {"path": path_label, "status": status}
        if reason:
            row["reason"] = sanitize_inline_text(reason, max_chars=220)
        checked.append(row)
        if (not na) and (not ok) and first_failure_stage == "none":
            first_failure_stage = stage_on_fail
            first_failure_reason = sanitize_inline_text(reason or f"missing {path_label}", max_chars=220)

    record(str(out_dir), out_dir.exists() and out_dir.is_dir(), stage_on_fail="scaffold failure", reason="output project directory")

    manifest_root = out_dir / "manifest.json"
    manifest_meta = out_dir / "meta" / "manifest.json"
    manifest_ok = manifest_root.exists() or manifest_meta.exists()
    record(
        "manifest.json|meta/manifest.json",
        manifest_ok,
        stage_on_fail="artifact missing",
        reason="project manifest",
    )

    if SUPPORT_SCAFFOLD_SOURCE_MODE == "live-reference":
        ref_src = out_dir / "meta" / "reference_source.json"
        record(
            "meta/reference_source.json",
            ref_src.exists(),
            stage_on_fail="artifact missing",
            reason="reference source metadata",
        )
    else:
        record("meta/reference_source.json", ok=True, stage_on_fail="artifact missing", na=True)

    record(str(support_run_dir), support_run_dir.exists() and support_run_dir.is_dir(), stage_on_fail="orchestration failure")
    record("TRACE.md", (support_run_dir / "TRACE.md").exists(), stage_on_fail="artifact missing")
    record("events.jsonl", (support_run_dir / "events.jsonl").exists(), stage_on_fail="artifact missing")

    dialogue_enabled = str(source or "").strip().lower() in {"telegram", "stdin", "selftest"}
    inbox_path = support_run_dir / SUPPORT_INBOX_REL_PATH
    if dialogue_enabled:
        record(
            SUPPORT_INBOX_REL_PATH.as_posix(),
            inbox_path.exists(),
            stage_on_fail="artifact missing",
            reason="dialogue capture artifact",
        )
    else:
        record(SUPPORT_INBOX_REL_PATH.as_posix(), ok=True, stage_on_fail="artifact missing", na=True)

    scaffold_report = _locate_latest_scaffold_report(support_run_dir, scaffold_run_dir)
    report_label = (
        str(scaffold_report)
        if scaffold_report is not None
        else "artifacts/scaffold_report.json|artifacts/scaffold_pointcloud_report.json"
    )
    record(
        report_label,
        scaffold_report is not None,
        stage_on_fail="artifact missing",
        reason="scaffold report artifact",
    )

    core_exists = (
        (out_dir / "README.md").exists()
        or (out_dir / "src").exists()
        or (out_dir / "main.py").exists()
        or (out_dir / "main.ts").exists()
        or (out_dir / "index.js").exists()
    )
    record(
        "README.md|src/|main entry",
        core_exists,
        stage_on_fail="invalid output",
        reason="core generated file",
    )

    pass_fail = "PASS" if first_failure_stage == "none" else "FAIL"
    concise_reason = "Ingress accepted and scaffold artifacts are complete." if pass_fail == "PASS" else first_failure_reason
    return checked, pass_fail, first_failure_stage, concise_reason

def run_t2p_state_machine(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    user_text: str,
    source: str,
    conversation_mode: str,
    delivery_state: dict[str, Any] | None,
) -> dict[str, Any]:
    generation_state = latest_generation_state(session_state)
    trigger_text = sanitize_inline_text(user_text, max_chars=280)
    generation_state["last_trigger_text"] = trigger_text
    generation_state["last_trigger_ts"] = now_iso()
    generation_state["last_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)

    _record_generation_state(generation_state, state_code="T0_PLAN", note="bind sanity task + out_dir")
    project_name_hint = _delivery_project_slug(
        str((delivery_state or {}).get("project_name_hint", "")).strip() or current_project_brief(session_state)
    )
    out_dir = (run_dir / SUPPORT_EXPORTS_REL_DIR / f"{project_name_hint}_ctcp_project").resolve()
    input_message = trigger_text or "Generate a minimal runnable project scaffold."

    _record_generation_state(generation_state, state_code="T1_INPUT", note="capture one minimal input")
    mode = "telegram_ingress_sanity" if str(source or "").strip().lower() == "telegram" else "fallback_generation"
    command_or_entry = "telegram_message_ingress" if mode == "telegram_ingress_sanity" else "ctcp_orchestrate scaffold entry"
    generation_state["last_test_mode"] = mode
    generation_state["last_command_or_entry"] = sanitize_inline_text(command_or_entry, max_chars=120)
    generation_state["last_out_dir"] = str(out_dir)

    _record_generation_state(generation_state, state_code="T2_ROUTE", note=mode)
    _record_generation_state(generation_state, state_code="T3_EXECUTE", note="trigger scaffold generation")

    execute_error = ""
    scaffold_dir: Path | None = None
    try:
        exec_delivery_state = dict(delivery_state) if isinstance(delivery_state, dict) else {}
        exec_delivery_state["project_name_hint"] = project_name_hint
        scaffold_dir = _materialize_support_scaffold_project(run_dir=run_dir, delivery_state=exec_delivery_state)
    except Exception as exc:
        execute_error = sanitize_inline_text(str(exc), max_chars=220) or "state machine execute failed"
        scaffold_dir = None

    materialization_doc = read_json_doc(run_dir / SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH) or {}
    scaffold_run_dir_text = str(materialization_doc.get("run_dir", "")).strip()
    scaffold_run_dir = _existing_path(scaffold_run_dir_text) if scaffold_run_dir_text else None
    generation_state["last_run_dir"] = scaffold_run_dir_text or str(run_dir)

    _record_generation_state(generation_state, state_code="T4_VERIFY", note="verify required artifacts")
    checked_artifacts: list[dict[str, str]] = []
    pass_fail = "FAIL"
    failure_stage = "scaffold failure"
    concise_reason = execute_error or sanitize_inline_text(str(materialization_doc.get("error", "")), max_chars=220)
    target_out_dir = scaffold_dir if isinstance(scaffold_dir, Path) else out_dir
    if scaffold_dir is not None and scaffold_dir.exists():
        checked_artifacts, pass_fail, failure_stage, concise_reason = _verify_t2p_chain_artifacts(
            support_run_dir=run_dir,
            out_dir=target_out_dir,
            scaffold_run_dir=scaffold_run_dir,
            source=source,
        )
    elif not concise_reason:
        concise_reason = "scaffold output directory missing"

    _record_generation_state(generation_state, state_code="T5_REPORT", note=f"{pass_fail}:{failure_stage}")
    report = {
        "schema_version": "ctcp-support-t2p-state-machine-report-v1",
        "ts": now_iso(),
        "test_name": "Low-token Telegram-to-Project Sanity Test",
        "state_machine": "T0->T1->T2->T3->T4->T5",
        "mode": mode,
        "input_message": input_message,
        "command_or_entry": command_or_entry,
        "out_dir": str(target_out_dir),
        "run_dir": scaffold_run_dir_text or str(run_dir),
        "checked_artifacts": checked_artifacts,
        "pass_fail": pass_fail,
        "failure_stage": failure_stage if pass_fail == "FAIL" else "none",
        "concise_reason": concise_reason or ("Ingress accepted and scaffold artifacts are complete." if pass_fail == "PASS" else ""),
        "trigger": {
            "source": sanitize_inline_text(source, max_chars=20),
            "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
            "user_text": trigger_text,
        },
        "materialization": {
            "out_dir": sanitize_inline_text(str(materialization_doc.get("out_dir", "")), max_chars=320),
            "run_dir": sanitize_inline_text(scaffold_run_dir_text, max_chars=320),
            "reused_existing": bool(materialization_doc.get("reused_existing", False)),
            "exit_code": int(materialization_doc.get("exit_code", 0) or 0),
            "error": sanitize_inline_text(str(materialization_doc.get("error", "")), max_chars=220),
        },
        "state_history": list(generation_state.get("state_history", [])),
    }
    write_json(run_dir / SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH, report)
    append_event(
        run_dir,
        "SUPPORT_T2P_STATE_MACHINE_REPORTED",
        SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix(),
        pass_fail=pass_fail,
        failure_stage=str(report.get("failure_stage", "")),
    )

    generation_state["last_report_ts"] = now_iso()
    generation_state["last_report_path"] = SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix()
    generation_state["last_pass_fail"] = pass_fail
    generation_state["last_failure_stage"] = str(report.get("failure_stage", ""))
    generation_state["last_concise_reason"] = sanitize_inline_text(str(report.get("concise_reason", "")), max_chars=220)
    generation_state["last_generated_project_dir"] = str(target_out_dir if target_out_dir.exists() else "")
    return report

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

    runtime_state = _project_runtime_state(project_context)
    runtime_latest = runtime_state.get("latest_result", {})
    if not isinstance(runtime_latest, dict):
        runtime_latest = {}
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        status = {}
    gate = runtime_state.get("gate", {})
    if (not isinstance(gate, dict)) or (not gate):
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
    run_status = str(runtime_state.get("run_status", "")).strip().lower() or str(status.get("run_status", "")).strip().lower()
    verify_result = (
        str(runtime_state.get("verify_result", "")).strip().upper()
        or str(runtime_latest.get("verify_result", "")).strip().upper()
        or str(status.get("verify_result", "")).strip().upper()
    )
    runtime_phase = sanitize_inline_text(str(runtime_state.get("phase", "")), max_chars=40).upper()
    gate_state = str(gate.get("state", "")).strip().lower()
    gate_reason = sanitize_inline_text(
        str(runtime_state.get("blocking_reason", "")).strip() or str(gate.get("reason", "")).strip(),
        max_chars=220,
    )
    gate_owner = sanitize_inline_text(str(gate.get("owner", "")), max_chars=120)
    gate_path = sanitize_inline_text(str(gate.get("path", "")), max_chars=180)
    gate_label = _progress_step_label(target_path=gate_path, role=gate_owner, reason=gate_reason)
    watchdog_status = sanitize_inline_text(str(gate.get("watchdog_status", "")), max_chars=40).lower()
    recovery = runtime_state.get("recovery", {})
    if not isinstance(recovery, dict):
        recovery = {}
    support_recovery = project_context.get("support_recovery", {})
    if not isinstance(support_recovery, dict):
        support_recovery = {}
    expected_artifact = sanitize_inline_text(
        str(gate.get("expected_artifact", "") or recovery.get("expected_artifact", "") or support_recovery.get("expected_artifact", "")),
        max_chars=180,
    )
    recovery_action = sanitize_inline_text(
        str(gate.get("recovery_action", "") or recovery.get("recovery_action", "") or support_recovery.get("recovery_action", "")),
        max_chars=220,
    )
    retry_count = int(gate.get("retry_count", recovery.get("retry_count", support_recovery.get("retry_count", 0) or 0)) or 0)
    max_retries = int(gate.get("max_retries", recovery.get("max_retries", support_recovery.get("max_retries", 0) or 0)) or 0)
    recovery_needed = bool(recovery.get("needed", False) or support_recovery.get("needed", False))
    recovery_hint = sanitize_inline_text(
        str(support_recovery.get("hint", "") or recovery.get("hint", "")),
        max_chars=220,
    )
    recovery_attempt = sanitize_inline_text(
        str(support_recovery.get("last_attempt", "") or recovery.get("last_attempt", "")),
        max_chars=160,
    )
    missing_plan_draft = is_missing_plan_draft_context(project_context)

    done_items: list[str] = []
    if run_id:
        _append_progress_item(done_items, "我这边已经接手到后台流程")

    for entry in _whiteboard_snapshot_entries(project_context):
        kind = str(entry.get("kind", "")).strip().lower()
        text = str(entry.get("text", "")).strip()
        low = text.lower()
        if kind in {"dispatch_lookup", "support_lookup"} and "lookup completed" in low:
            _append_progress_item(done_items, "资料检索已完成")
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
            _append_progress_item(done_items, "资料检索已完成")
        else:
            _append_progress_item(done_items, f"{label}已完成")

    decision_rows = runtime_state.get("pending_decisions", [])
    if not isinstance(decision_rows, list) or not decision_rows:
        decision_rows = decisions.get("decisions", [])
    if not isinstance(decision_rows, list):
        decision_rows = []
    decision_question = ""
    pending_count = 0
    submitted_count = 0
    for item in decision_rows:
        if not isinstance(item, dict):
            continue
        status_text = sanitize_inline_text(str(item.get("status", "")), max_chars=24).lower()
        question_hint = sanitize_inline_text(str(item.get("question", "") or item.get("question_hint", "")), max_chars=220)
        if status_text == "pending":
            pending_count += 1
            if question_hint and (not decision_question):
                decision_question = question_hint
        elif status_text == "submitted":
            submitted_count += 1
            if question_hint and (not decision_question):
                decision_question = question_hint
        elif question_hint and (not decision_question):
            decision_question = question_hint

    decision_count = int(runtime_state.get("decisions_needed_count", pending_count) or pending_count)
    waiting_for_decision = bool(runtime_state.get("needs_user_decision", False))
    if not waiting_for_decision:
        waiting_for_decision = bool(status.get("needs_user_decision", False)) or decision_count > 0
    submitted_waiting = submitted_count > 0 and (not waiting_for_decision)
    gate_blocked_on_internal = gate_state == "blocked" and (not waiting_for_decision)
    current_phase = ""
    current_blocker = "none"
    next_action = "继续对齐最新 gate truth，并在阶段变化时马上同步你"
    question_needed = "no"
    message_purpose = "progress"
    active_stage = _runtime_phase_to_support_stage(runtime_phase) or "PLAN"
    stage_reason = f"canonical_phase:{runtime_phase.lower()}" if runtime_phase else "default_from_status"
    phase_labels = {
        "INTAKE": "需求确认",
        "CLARIFY": "需求澄清",
        "PLAN": "方案规划",
        "EXECUTE": "执行推进",
        "VERIFY": "验证收敛",
        "RETRYING": "自动恢复重试",
        "RECOVERY_NEEDED": "等待明确恢复",
        "EXEC_FAILED": "执行失败",
        "BLOCKED_HARD": "硬阻塞",
        "WAIT_USER_DECISION": "等待你的决定",
        "FINALIZE": "结果整理/交付",
        "DELIVER": "结果整理/交付",
        "DELIVERED": "结果已回传",
        "RECOVER": "异常恢复",
    }

    if verify_result == "PASS" and run_status in {"pass", "done", "completed", "success"}:
        current_phase = "结果整理/交付"
        current_blocker = "none"
        next_action = "把这一轮结果和可交付内容整理给你"
        message_purpose = "delivery"
        active_stage = "FINALIZE"
        stage_reason = "verify_pass_or_final_run_status"
    elif waiting_for_decision:
        current_phase = phase_labels.get("WAIT_USER_DECISION", "等待关键决定")
        current_blocker = "等你先确认一个关键决定"
        next_action = "等你拍板这个点，一收到答复我就马上继续推进"
        question_needed = "yes"
        active_stage = "WAIT_USER_DECISION"
        stage_reason = "decision_required"
    elif submitted_waiting:
        current_phase = phase_labels.get("EXECUTE", "执行推进")
        current_blocker = "你的决策已提交，正在等待后端消费确认"
        next_action = "我会继续轮询后端消费状态，一旦确认推进就马上同步你"
        active_stage = "EXECUTE"
        stage_reason = "decision_submitted_waiting_consume"
    elif runtime_phase in {"RETRYING", "RECOVERY_NEEDED", "EXEC_FAILED", "BLOCKED_HARD"}:
        current_phase = phase_labels.get(runtime_phase, "异常恢复")
        if runtime_phase == "EXEC_FAILED":
            current_blocker = gate_reason or "provider 已报告执行，但目标产物仍未落地"
            next_action = recovery_action or "先核对 provider 执行证据，再重跑失败 gate"
            active_stage = "EXEC_FAILED"
            stage_reason = "watchdog_exec_failed"
        elif runtime_phase == "RECOVERY_NEEDED":
            current_blocker = gate_reason or f"{gate_label or '当前 gate'} 自动恢复已耗尽"
            next_action = recovery_action or "进入明确恢复处理，先检查 gate truth 与产物落地原因"
            active_stage = "RECOVERY_NEEDED"
            stage_reason = "watchdog_retry_exhausted"
        elif runtime_phase == "BLOCKED_HARD":
            current_blocker = gate_reason or f"{gate_label or '当前 gate'} 缺少可自动恢复的目标产物"
            next_action = recovery_action or "先人工对齐 blocker truth，再决定恢复路径"
            active_stage = "BLOCKED_HARD"
            stage_reason = "watchdog_non_retryable_block"
        else:
            artifact_name = expected_artifact.rsplit("/", 1)[-1] if expected_artifact else ""
            current_blocker = gate_reason or (f"当前缺的是 {artifact_name}" if artifact_name else "当前 gate 已进入自动恢复重试")
            next_action = recovery_action or "继续自动重试当前 stalled gate，并确认目标产物是否落地"
            active_stage = "RETRYING"
            stage_reason = "watchdog_retrying"
        if retry_count > 0 and max_retries > 0:
            retry_prefix = sanitize_inline_text(f"已自动重试 {retry_count}/{max_retries} 次", max_chars=120)
            next_action = sanitize_inline_text(f"{retry_prefix}；下一步：{next_action}", max_chars=220)
    elif run_status == "blocked" or gate_blocked_on_internal:
        current_phase = gate_label or phase_labels.get(active_stage, "") or "当前评审"
        if missing_plan_draft:
            current_phase = gate_label or "方案整理"
            current_blocker = gate_reason or "方案整理这一步还卡着，当前缺的是 PLAN_draft.md"
            next_action = recovery_hint or plan_draft_recovery_hint(attempted=bool(recovery_attempt))
        elif gate_label:
            current_blocker = f"{gate_label}这一步还卡着，后续推进要先等这个点处理掉"
            next_action = recovery_action or f"先把{gate_label}卡点处理掉，再重新对齐最新 gate truth"
        else:
            current_blocker = gate_reason or "当前评审这一步还卡着，后续推进要先等这个点处理掉"
            next_action = recovery_action or "先把当前卡点处理掉，再重新对齐最新 gate truth"
        if recovery_needed and recovery_hint and not missing_plan_draft:
            next_action = recovery_hint
            if recovery_attempt:
                next_action = sanitize_inline_text(f"{recovery_attempt}；下一步：{recovery_hint}", max_chars=220)
        active_stage = "VERIFY" if gate_blocked_on_internal else "RECOVER"
        stage_reason = "blocked_state_detected"
    elif run_status in {"running", "in_progress", "working"}:
        current_phase = phase_labels.get(active_stage, "") or gate_label or "执行推进"
        current_blocker = "none"
        active_stage = "EXECUTE"
        stage_reason = "run_status_running"
    else:
        current_phase = phase_labels.get(active_stage, "") or gate_label or "处理中"
        current_blocker = "none"
        if not runtime_phase:
            active_stage = "PLAN"
            stage_reason = "status_pending_execution"

    if current_blocker == "none" and gate_reason and gate_reason.lower() not in {"none", "n/a"} and active_stage in {"RECOVER", "VERIFY"}:
        current_blocker = gate_reason

    proof_refs: list[str] = []
    if run_id:
        proof_refs.append(f"run_id={run_id}")
    runtime_proof_refs = runtime_latest.get("proof_refs", [])
    if isinstance(runtime_proof_refs, list):
        for item in runtime_proof_refs:
            ref = sanitize_inline_text(str(item), max_chars=180)
            if ref and ref not in proof_refs:
                proof_refs.append(ref)
                if len(proof_refs) >= 4:
                    break

    return {
        "current_task_goal": task_goal,
        "current_phase": current_phase,
        "active_stage": active_stage,
        "stage_reason": stage_reason,
        "stage_exit_condition": SUPPORT_STAGE_EXIT_RULES.get(active_stage, ""),
        "last_confirmed_items": done_items,
        "current_blocker": current_blocker,
        "message_purpose": message_purpose,
        "question_needed": question_needed,
        "next_action": sanitize_inline_text(next_action, max_chars=220),
        "blocking_question": decision_question,
        "proof_refs": proof_refs,
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
    runtime_state = _project_runtime_state(project_context)
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    runtime_gate = runtime_state.get("gate", {})
    if isinstance(runtime_gate, dict) and runtime_gate:
        gate = runtime_gate
    payload = {
        "run_id": sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80),
        "phase": sanitize_inline_text(str(runtime_state.get("phase", "")), max_chars=40),
        "run_status": sanitize_inline_text(
            str(runtime_state.get("run_status", "")).strip() or str(status.get("run_status", "")).strip(),
            max_chars=40,
        ),
        "verify_result": sanitize_inline_text(
            str(runtime_state.get("verify_result", "")).strip() or str(status.get("verify_result", "")).strip(),
            max_chars=20,
        ),
        "gate_state": sanitize_inline_text(str(gate.get("state", "")), max_chars=40),
        "gate_reason": sanitize_inline_text(
            str(runtime_state.get("blocking_reason", "")).strip() or str(gate.get("reason", "")).strip(),
            max_chars=220,
        ),
        "needs_user_decision": bool(runtime_state.get("needs_user_decision", False) or status.get("needs_user_decision", False)),
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
    status_hash: str = "",
) -> None:
    if not isinstance(project_context, dict):
        return
    run_id = sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)
    if not run_id:
        return
    digest, binding = build_progress_digest(project_context=project_context, task_summary_hint=task_summary_hint)
    stable_hash = sanitize_inline_text(status_hash, max_chars=80) or digest
    if not stable_hash:
        return
    notification_state = latest_notification_state(session_state)
    notification_state["last_progress_hash"] = stable_hash
    notification_state["last_progress_ts"] = sanitize_inline_text(ts or now_iso(), max_chars=40)
    notification_state["last_notified_run_id"] = run_id
    notification_state["last_notified_phase"] = sanitize_inline_text(str(binding.get("current_phase", "")), max_chars=80)

def should_auto_advance_project_context(session_state: dict[str, Any], project_context: dict[str, Any] | None) -> bool:
    return should_auto_advance_project_context_impl(
        project_context,
        last_auto_advance_ts=str(latest_notification_state(session_state).get("last_auto_advance_ts", "")),
        interval_sec=SUPPORT_AUTO_ADVANCE_INTERVAL_SEC,
        seconds_since=seconds_since,
    )

def evaluate_package_delivery_gate(project_context: dict[str, Any] | None) -> tuple[bool, str]:
    if not isinstance(project_context, dict):
        return False, "missing project context"
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        return False, "missing run status"
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    gate_state = str(gate.get("state", "")).strip().lower()
    needs_user_decision = bool(status.get("needs_user_decision", False))
    decisions_needed_count = int(status.get("decisions_needed_count", 0) or 0)

    if verify_result != "PASS":
        return False, "verify_result is not PASS"
    if run_status not in {"pass", "done", "completed", "success"}:
        return False, f"run_status not final: {run_status or 'unknown'}"
    if gate_state in {"blocked", "error", "failed"}:
        return False, f"gate_state not deliverable: {gate_state}"
    if needs_user_decision or decisions_needed_count > 0:
        return False, "pending user decision"
    return True, ""

def should_attempt_delivery_unblock_advance(*, project_context: dict[str, Any] | None, user_text: str) -> bool:
    if not user_requests_project_package(user_text):
        return False
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
    needs_user_decision = bool(status.get("needs_user_decision", False))
    decisions_needed_count = int(status.get("decisions_needed_count", 0) or 0)

    if needs_user_decision or decisions_needed_count > 0:
        return False
    if verify_result == "PASS" and run_status in {"pass", "done", "completed", "success"}:
        return False
    if run_status in {"fail", "failed", "error", "aborted"}:
        return False
    if gate_state in {"error", "failed"}:
        return False
    return True

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
        advanced = ctcp_front_bridge.ctcp_advance(
            new_run_id,
            max_steps=interactive_reply_advance_steps(created=(not bound_run_id)),
        )
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
            project_context, recovered_stale_bound = fetch_support_context_with_recovery(
                run_dir=run_dir,
                session_state=session_state,
                bound_run_id=bound_run_id,
                trigger="interactive_sync",
            )
            if recovered_stale_bound:
                bound_run_id = ""

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

        create_goal = resolve_new_run_goal(
            user_text=user_text,
            conversation_mode=mode,
            session_state=session_state,
            should_refresh_project_brief=should_refresh_project_brief,
            is_low_signal_project_followup=is_low_signal_project_followup,
            is_project_execution_followup=is_project_execution_followup,
        )
        if not bound_run_id and mode != "STATUS_QUERY" and create_goal:
            created = ctcp_front_bridge.ctcp_new_run(goal=create_goal)
            bound_run_id = str(created.get("run_id", "")).strip()
            session_state["bound_run_id"] = bound_run_id
            session_state["bound_run_dir"] = str(created.get("run_dir", "")).strip()
            if should_refresh_project_brief(user_text, mode):
                set_current_project_brief(session_state, user_text)
            elif not current_project_brief(session_state):
                set_current_project_brief(session_state, create_goal)
            append_event(run_dir, "SUPPORT_RUN_BOUND", "", run_id=bound_run_id)

        if not bound_run_id:
            return project_context if isinstance(project_context, dict) else {}, session_state

        if recovered_candidate is None:
            recorded = ctcp_front_bridge.ctcp_record_support_turn(
                bound_run_id,
                text=user_text,
                source=source,
                chat_id=chat_id,
                conversation_mode=mode,
            )
            project_context, recovered_stale_bound = fetch_support_context_with_recovery(
                run_dir=run_dir,
                session_state=session_state,
                bound_run_id=bound_run_id,
                trigger="interactive_post_turn",
            )
            if recovered_stale_bound:
                project_context["created"] = created or {}
                project_context["recorded_turn"] = recorded or {}
                project_context["advance"] = advanced or {}
                return project_context, session_state
            if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL"}:
                status = project_context.get("status", {})
                if isinstance(status, dict) and not bool(status.get("needs_user_decision", False)):
                    steps = interactive_reply_advance_steps(created=(created is not None))
                    advanced = ctcp_front_bridge.ctcp_advance(bound_run_id, max_steps=steps)
                    project_context, recovered_stale_bound = fetch_support_context_with_recovery(
                        run_dir=run_dir,
                        session_state=session_state,
                        bound_run_id=bound_run_id,
                        trigger="interactive_post_advance",
                    )
                    if recovered_stale_bound:
                        project_context["created"] = created or {}
                        project_context["recorded_turn"] = recorded or {}
                        project_context["advance"] = advanced or {}
                        return project_context, session_state
            if should_attempt_delivery_unblock_advance(project_context=project_context, user_text=user_text):
                status_for_delivery = project_context.get("status", {}) if isinstance(project_context, dict) else {}
                gate_for_delivery = status_for_delivery.get("gate", {}) if isinstance(status_for_delivery, dict) else {}
                gate_state = str(gate_for_delivery.get("state", "")).strip().lower() if isinstance(gate_for_delivery, dict) else ""
                extra_steps = 6 if gate_state == "blocked" else 4
                advanced = ctcp_front_bridge.ctcp_advance(bound_run_id, max_steps=extra_steps)
                project_context, recovered_stale_bound = fetch_support_context_with_recovery(
                    run_dir=run_dir,
                    session_state=session_state,
                    bound_run_id=bound_run_id,
                    trigger="interactive_delivery_unblock",
                )
                if recovered_stale_bound:
                    project_context["created"] = created or {}
                    project_context["recorded_turn"] = recorded or {}
                    project_context["advance"] = advanced or {}
                    return project_context, session_state
                append_event(
                    run_dir,
                    "SUPPORT_DELIVERY_UNBLOCK_ADVANCE",
                    "",
                    run_id=bound_run_id,
                    max_steps=extra_steps,
                    reason="package_requested",
                )
            annotate_plan_draft_recovery(project_context, attempted=bool(advanced))

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

def sync_frontdesk_state(
    session_state: dict[str, Any],
    *,
    user_text: str,
    conversation_mode: str,
    project_context: dict[str, Any] | None = None,
    delivery_state: dict[str, Any] | None = None,
    provider_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if frontend_derive_frontdesk_state is None:
        return current_frontdesk_state(session_state)
    try:
        derived = frontend_derive_frontdesk_state(
            user_text=user_text,
            conversation_mode=conversation_mode,
            session_state=session_state,
            project_context=project_context,
            delivery_state=delivery_state,
            provider_result=provider_result,
        )
        session_state["frontdesk_state"] = derived
        return current_frontdesk_state(session_state)
    except Exception:
        return current_frontdesk_state(session_state)

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


_REPO_INTERNAL_DELIVERY_ROOTS = {
    ".git",
    ".github",
    ".agent_private",
    ".agents",
    "agents",
    "ai_context",
    "apps",
    "artifacts",
    "bridge",
    "build",
    "build_lite",
    "build_verify",
    "contracts",
    "ctcp_adapters",
    "docs",
    "llm_core",
    "meta",
    "scripts",
    "simlab",
    "tests",
    "tools",
    "web",
    "workflow_registry",
}


def _is_public_delivery_source_dir(candidate: Path) -> bool:
    if not candidate.exists() or not candidate.is_dir():
        return False
    resolved = candidate.resolve()
    if _looks_like_ctcp_project_dir(resolved) or _looks_like_placeholder_project_dir(resolved):
        return True
    try:
        rel = resolved.relative_to(ROOT.resolve())
    except Exception:
        return True
    parts = [part for part in rel.parts if part]
    if not parts:
        return False
    head = parts[0].lower()
    if head == "generated_projects":
        return True
    return head not in _REPO_INTERNAL_DELIVERY_ROOTS

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

def _declared_project_root_from_context(bound_run_dir: Path, project_context: dict[str, Any] | None) -> Path | None:
    if not isinstance(project_context, dict):
        return None
    manifest = project_context.get("project_manifest", {})
    if not isinstance(manifest, dict):
        return None
    rel = str(manifest.get("project_root", "")).strip()
    if not rel:
        return None
    candidate = (bound_run_dir / Path(rel)).resolve()
    try:
        candidate.relative_to(bound_run_dir.resolve())
    except Exception:
        return None
    if not candidate.exists() or not candidate.is_dir():
        return None
    return candidate

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

def _has_any_file(root: Path, pattern: str) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    for path in root.rglob(pattern):
        if path.is_file():
            return True
    return False

def _has_screenshot_or_reason(artifacts_dir: Path) -> bool:
    screenshots_dir = artifacts_dir / "screenshots"
    if screenshots_dir.exists() and screenshots_dir.is_dir():
        for path in screenshots_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in SCREENSHOT_SUFFIXES:
                return True
    reason_file = artifacts_dir / "screenshots_not_available_reason.txt"
    if reason_file.exists() and reason_file.is_file():
        return True
    demo_trace = artifacts_dir / "demo_trace.md"
    if demo_trace.exists() and demo_trace.is_file():
        low = demo_trace.read_text(encoding="utf-8", errors="replace").lower()
        if "screenshots_not_available_reason" in low:
            return True
    return False

def _score_delivery_project_quality(root: Path) -> dict[str, Any]:
    artifacts_dir = root / "artifacts"
    checks = [
        ("readme", (root / "README.md").exists(), 10),
        ("manifest", (root / "manifest.json").exists() or (root / "meta" / "manifest.json").exists(), 10),
        ("docs_dir", (root / "docs").is_dir(), 8),
        ("meta_dir", (root / "meta").is_dir(), 8),
        ("scripts_dir", (root / "scripts").is_dir(), 8),
        ("verify_entry", (root / "scripts" / "verify_repo.ps1").exists() or (root / "scripts" / "verify_repo.sh").exists(), 8),
        ("tests_dir", (root / "tests").is_dir(), 10),
        ("test_case_file", _has_any_file(root / "tests", "test_*.py"), 8),
        (
            "showcase_core",
            (artifacts_dir / "test_plan.json").exists()
            and (artifacts_dir / "test_cases.json").exists()
            and (artifacts_dir / "test_summary.md").exists()
            and (artifacts_dir / "demo_trace.md").exists(),
            15,
        ),
        ("showcase_visual", _has_screenshot_or_reason(artifacts_dir), 15),
    ]
    score = sum(weight for _, ok, weight in checks if ok)
    tier = "low"
    if score >= 85:
        tier = "high"
    elif score >= SUPPORT_PACKAGE_MIN_QUALITY_SCORE:
        tier = "medium"
    elif score >= 50:
        tier = "scaffold"
    missing = [check_id for check_id, ok, _ in checks if not ok]
    return {
        "root": str(root),
        "score": int(score),
        "tier": tier,
        "missing_checks": missing,
    }

def _evaluate_delivery_quality_gate(
    *,
    package_source_dirs: list[Path],
    existing_package_files: list[Path],
) -> tuple[bool, str, int, str, str]:
    if existing_package_files and (not package_source_dirs):
        return True, "", 100, "trusted_existing_package", ""
    if not package_source_dirs:
        return False, "package source missing", 0, "unknown", ""
    reports = [_score_delivery_project_quality(path) for path in package_source_dirs if path.exists() and path.is_dir()]
    if not reports:
        return False, "package source missing", 0, "unknown", ""
    best = max(reports, key=lambda item: int(item.get("score", 0)))
    score = int(best.get("score", 0))
    tier = str(best.get("tier", "unknown"))
    subject = str(best.get("root", ""))
    if score < SUPPORT_PACKAGE_MIN_QUALITY_SCORE:
        return (
            False,
            f"package quality score {score} < {SUPPORT_PACKAGE_MIN_QUALITY_SCORE}; need fuller implementation evidence",
            score,
            tier,
            subject,
        )
    return True, "", score, tier, subject

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
    support_run_dir: Path | None = None,
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
        "package_delivery_allowed": False,
        "package_blocked_reason": "",
        "package_quality_ready": False,
        "package_quality_score": 0,
        "package_quality_tier": "unknown",
        "package_quality_subject": "",
        "package_quality_reason": "",
        "screenshot_ready": False,
    }
    package_source_dirs: list[Path] = []
    existing_package_files: list[Path] = []
    screenshot_files: list[Path] = []
    bound_run_dir: Path | None = None
    artifacts_dir: Path | None = None
    bound_run_id = ""
    if isinstance(project_context, dict):
        bound_run_id = str(project_context.get("run_id", "")).strip()
        bound_run_dir = _existing_path(str(project_context.get("run_dir", "")).strip())
    if bound_run_dir is None and isinstance(session_state, dict):
        bound_run_id = bound_run_id or str(session_state.get("bound_run_id", "")).strip()
        bound_run_dir = _existing_path(str(session_state.get("bound_run_dir", "")).strip())
    if bound_run_dir is not None and bound_run_dir.is_dir():
        state["bound_run_id"] = bound_run_id
        state["bound_run_dir"] = str(bound_run_dir)
        declared_project_root = _declared_project_root_from_context(bound_run_dir, project_context)
        if _is_public_delivery_source_dir(declared_project_root) if declared_project_root is not None else False:
            _append_unique_path(package_source_dirs, declared_project_root)
        for candidate in _generated_project_roots_from_patch_apply(bound_run_dir):
            _append_unique_path(package_source_dirs, candidate if _is_public_delivery_source_dir(candidate) else None)
        for candidate in _parse_scope_allow_roots(bound_run_dir / "artifacts" / "PLAN.md"):
            if _is_public_delivery_source_dir(candidate):
                _append_unique_path(package_source_dirs, candidate)
        artifacts_dir = bound_run_dir / "artifacts"

    exports_root: Path | None = None
    if isinstance(support_run_dir, Path):
        exports_root = (support_run_dir / SUPPORT_EXPORTS_REL_DIR).resolve()
    elif bound_run_dir is not None and bound_run_dir.is_dir():
        candidate = bound_run_dir / SUPPORT_EXPORTS_REL_DIR
        if candidate.exists():
            exports_root = candidate.resolve()

    if exports_root is not None and exports_root.exists() and exports_root.is_dir():
        for node in sorted(exports_root.iterdir()):
            if node.is_dir():
                _append_unique_path(package_source_dirs, node)
        for candidate in sorted(exports_root.rglob("*.zip")):
            if candidate.name.lower() == "failure_bundle.zip":
                continue
            _append_unique_path(existing_package_files, candidate)
        for candidate in sorted(exports_root.rglob("*")):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in SCREENSHOT_SUFFIXES:
                continue
            _append_unique_path(screenshot_files, candidate)

    search_roots = list(package_source_dirs)
    if artifacts_dir is not None and artifacts_dir.exists():
        search_roots.append(artifacts_dir)
    for root in search_roots:
        for candidate in sorted(root.rglob("*.zip")):
            if candidate.name.lower() == "failure_bundle.zip":
                continue
            _append_unique_path(existing_package_files, candidate)
    screenshot_roots = list(package_source_dirs)
    if artifacts_dir is not None and artifacts_dir.exists():
        screenshot_roots.append(artifacts_dir)
    for root in screenshot_roots:
        for candidate in sorted(root.rglob("*")):
            if not candidate.is_file():
                continue
            if candidate.suffix.lower() not in SCREENSHOT_SUFFIXES:
                continue
            _append_unique_path(screenshot_files, candidate)

    ctcp_package_source_dirs = [path for path in package_source_dirs if _looks_like_ctcp_project_dir(path)]
    placeholder_package_source_dirs = [path for path in package_source_dirs if _looks_like_placeholder_project_dir(path)]

    state["package_source_dirs"] = [str(path) for path in package_source_dirs]
    state["ctcp_package_source_dirs"] = [str(path) for path in ctcp_package_source_dirs]
    state["placeholder_package_source_dirs"] = [str(path) for path in placeholder_package_source_dirs]
    state["existing_package_files"] = [str(path) for path in existing_package_files]
    state["screenshot_files"] = [str(path) for path in prioritize_screenshot_files(screenshot_files)]
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
    package_artifact_ready = bool(package_source_dirs or existing_package_files)
    gate_allowed, gate_block_reason = evaluate_package_delivery_gate(project_context)
    quality_ready, quality_reason, quality_score, quality_tier, quality_subject = _evaluate_delivery_quality_gate(
        package_source_dirs=package_source_dirs,
        existing_package_files=existing_package_files,
    )
    state["package_quality_ready"] = bool(quality_ready)
    state["package_quality_score"] = int(quality_score)
    state["package_quality_tier"] = sanitize_inline_text(quality_tier, max_chars=24) or "unknown"
    state["package_quality_subject"] = sanitize_inline_text(quality_subject, max_chars=320)
    state["package_quality_reason"] = sanitize_inline_text(quality_reason, max_chars=180)
    state["package_delivery_allowed"] = bool(package_artifact_ready and gate_allowed and quality_ready)
    if not package_artifact_ready:
        state["package_blocked_reason"] = "package artifact not ready"
    elif not gate_allowed:
        state["package_blocked_reason"] = sanitize_inline_text(gate_block_reason, max_chars=120)
    elif not quality_ready:
        state["package_blocked_reason"] = sanitize_inline_text(quality_reason, max_chars=120)
    state["package_ready"] = bool(state["package_delivery_allowed"])
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
        "package_delivery_allowed": bool(delivery_state.get("package_delivery_allowed", False)),
        "package_blocked_reason": sanitize_inline_text(str(delivery_state.get("package_blocked_reason", "")), max_chars=120),
        "package_quality_ready": bool(delivery_state.get("package_quality_ready", False)),
        "package_quality_score": int(delivery_state.get("package_quality_score", 0) or 0),
        "package_quality_tier": sanitize_inline_text(str(delivery_state.get("package_quality_tier", "")), max_chars=24),
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
        "send_project_package is allowed only when public_delivery.package_delivery_allowed is true.\n"
        "If public_delivery.package_quality_ready is false, do not ask for package confirmation; explain that quality evidence is not complete yet.\n"
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
    recent_layered_turns: list[dict[str, Any]] = []
    mode = str(conversation_mode or "").strip().upper()
    frontdesk_state = current_frontdesk_state(session_state or {}) if isinstance(session_state, dict) else {}
    frontdesk_strategy: dict[str, Any] = {}
    if frontend_reply_strategy_from_frontdesk_state is not None:
        try:
            frontdesk_strategy = frontend_reply_strategy_from_frontdesk_state(
                frontdesk_state,
                conversation_mode=mode,
            )
        except Exception:
            frontdesk_strategy = {}
    expose_project_context = bool(frontdesk_strategy.get("allow_existing_project_reference", False)) or should_expose_existing_project_context(mode, user_text)
    expose_delivery_context = should_expose_delivery_context(mode, user_text)
    if isinstance(session_state, dict):
        layers = history_layers_state(session_state)
        raw_turns = layers.get("raw_turns", [])
        if isinstance(raw_turns, list):
            for item in raw_turns[-SUPPORT_HISTORY_PROMPT_RECENT_LIMIT:]:
                if not isinstance(item, dict):
                    continue
                text = sanitize_inline_text(str(item.get("text", "")), max_chars=360)
                if not text:
                    continue
                recent_layered_turns.append(
                    {
                        "ts": sanitize_inline_text(str(item.get("ts", "")), max_chars=40),
                        "role": sanitize_inline_text(str(item.get("role", "user")), max_chars=16) or "user",
                        "source": sanitize_inline_text(str(item.get("source", "")), max_chars=40),
                        "conversation_mode": sanitize_inline_text(str(item.get("conversation_mode", "")), max_chars=40),
                        "message_intent": sanitize_inline_text(str(item.get("message_intent", "")), max_chars=24),
                        "text": text,
                    }
                )
        if recent_layered_turns:
            history = [{"ts": str(item.get("ts", "")), "source": str(item.get("source", "")), "text": str(item.get("text", ""))} for item in recent_layered_turns]
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
        "frontdesk_reply_strategy": {
            "allow_existing_project_reference": bool(frontdesk_strategy.get("allow_existing_project_reference", False)),
            "latest_turn_only": bool(frontdesk_strategy.get("latest_turn_only", (not expose_project_context))),
            "prefer_frontend_render": bool(frontdesk_strategy.get("prefer_frontend_render", False)),
            "prefer_progress_binding": bool(frontdesk_strategy.get("prefer_progress_binding", False)),
        },
        "reply_guard": {
            "preset_customer_reply_allowed": False,
            "allow_existing_project_reference": expose_project_context,
            "latest_turn_only": bool(frontdesk_strategy.get("latest_turn_only", (not expose_project_context))),
        },
    }
    if isinstance(session_state, dict):
        project_brief = current_project_brief(session_state)
        turn_memory = latest_turn_memory(session_state)
        session_profile = _state_zone(session_state, "session_profile")
        project_constraints = _state_zone(session_state, "project_constraints_memory")
        execution_memory = _state_zone(session_state, "execution_memory")
        history_layers = history_layers_state(session_state)
        working_memory = _state_zone(history_layers, "working_memory")
        task_summary_layer = _state_zone(history_layers, "task_summary")
        user_preferences = _state_zone(history_layers, "user_preferences")
        context["session_state"] = {
            "bound_run_id": sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
            if expose_project_context
            else "",
            "task_summary": project_brief if expose_project_context else "",
            "project_brief": project_brief if expose_project_context else "",
            "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80) if expose_project_context else "",
            "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80) if expose_project_context else "",
            "active_goal": sanitize_inline_text(str(session_state.get("active_goal", "")), max_chars=280) if expose_project_context else "",
            "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32) if expose_project_context else "",
            "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220) if expose_project_context else "none",
            "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220) if expose_project_context else "",
            "latest_message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
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
        context["history_layers"] = {
            "working_memory": {
                "current_goal": sanitize_inline_text(str(working_memory.get("current_goal", "")), max_chars=280) if expose_project_context else "",
                "current_constraints": sanitize_inline_text(str(working_memory.get("current_constraints", "")), max_chars=280) if expose_project_context else "",
                "current_stage": sanitize_inline_text(str(working_memory.get("current_stage", "")), max_chars=32) if expose_project_context else "",
                "pending_decision": sanitize_inline_text(str(working_memory.get("pending_decision", "")), max_chars=220) if expose_project_context else "",
                "next_action": sanitize_inline_text(str(working_memory.get("next_action", "")), max_chars=220) if expose_project_context else "",
                "active_blocker": sanitize_inline_text(str(working_memory.get("active_blocker", "none")), max_chars=220) if expose_project_context else "none",
                "latest_message_intent": sanitize_inline_text(str(working_memory.get("latest_message_intent", "continue")), max_chars=24),
            },
            "task_summary": {
                "task_goal": sanitize_inline_text(str(task_summary_layer.get("task_goal", "")), max_chars=280) if expose_project_context else "",
                "confirmed_requirements": list(task_summary_layer.get("confirmed_requirements", [])) if expose_project_context else [],
                "completed_steps": list(task_summary_layer.get("completed_steps", [])) if expose_project_context else [],
                "pending_steps": list(task_summary_layer.get("pending_steps", [])) if expose_project_context else [],
                "current_risks": list(task_summary_layer.get("current_risks", [])) if expose_project_context else [],
                "result_location": sanitize_inline_text(str(task_summary_layer.get("result_location", "")), max_chars=260) if expose_project_context else "",
            },
            "user_preferences": {
                "language": sanitize_inline_text(str(user_preferences.get("language", "auto")), max_chars=12),
                "tone": sanitize_inline_text(str(user_preferences.get("tone", "task_progressive")), max_chars=40),
                "initiative": sanitize_inline_text(str(user_preferences.get("initiative", "balanced")), max_chars=24),
                "verbosity": sanitize_inline_text(str(user_preferences.get("verbosity", "normal")), max_chars=24),
                "avoid_mechanical": bool(user_preferences.get("avoid_mechanical", False)),
                "prefer_push_to_delivery": bool(user_preferences.get("prefer_push_to_delivery", False)),
                "prefer_less_questions": bool(user_preferences.get("prefer_less_questions", False)),
                "prefer_owner_report_style": bool(user_preferences.get("prefer_owner_report_style", True)),
            },
            "recent_raw_turns": recent_layered_turns[-SUPPORT_HISTORY_PROMPT_RECENT_LIMIT:],
        }
        if frontend_prompt_context_from_frontdesk_state is not None:
            try:
                context["frontdesk_state"] = frontend_prompt_context_from_frontdesk_state(
                    frontdesk_state,
                    include_task_context=expose_project_context,
                )
            except Exception:
                pass
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
    code = str(reason_kind or "").strip().lower()
    use_en = str(lang or "").strip().lower().startswith("en")
    if local_unavailable:
        if use_en:
            return "The reply backend is unavailable right now, and both the API path and local fallback are down."
        return "当前回复后端暂时不可用，API 路径和本地兜底都不可用。"
    if code == "invalid_reply":
        if use_en:
            return "The formal reply path did not produce a customer-ready answer for this turn; only a lower-confidence fallback summary is available."
        return "这轮正式回复链没有产出可直接发送的结果，目前只有一份低置信度兜底说明。"
    if use_en:
        return "The formal reply path is unavailable right now; only a lower-confidence fallback summary is available."
    return "这轮正式回复链暂时不可用，目前只有一份低置信度兜底说明。"

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
    return provider_runtime.execute_provider(
        provider,
        repo_root=ROOT,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets={},
    )

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

def _normalize_reply_semantic(text: str) -> str:
    raw = re.sub(r"\s+", " ", str(text or "").strip()).lower()
    raw = re.sub(r"[，。！？!?;；:：,.\-_/\\()（）\[\]{}\"'`~]+", "", raw)
    return raw

def _contains_any_token(text: str, tokens: tuple[str, ...]) -> bool:
    low = str(text or "").lower()
    return any(str(token or "").lower() in low for token in tokens if str(token or "").strip())

def _task_like_mode(conversation_mode: str) -> bool:
    mode = str(conversation_mode or "").strip().upper()
    return mode in {"PROJECT_DETAIL", "PROJECT_DECISION_REPLY", "STATUS_QUERY"}

def _is_final_ready_context(project_context: dict[str, Any] | None) -> bool:
    if not isinstance(project_context, dict):
        return False
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        return False
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    needs_user_decision = bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0
    return (verify_result == "PASS") and (run_status in _FINAL_READY_RUN_STATUSES) and (not needs_user_decision)

def _reply_has_status_anchor(reply_text: str, binding: dict[str, Any], *, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    phase = str(binding.get("current_phase", "")).strip()
    blocker = str(binding.get("current_blocker", "")).strip()
    done_items = [str(item or "").strip() for item in list(binding.get("last_confirmed_items", []) or []) if str(item or "").strip()]
    if phase and phase in text:
        return True
    if blocker and blocker.lower() != "none" and blocker in text:
        return True
    if any(item in text for item in done_items[:2]):
        return True
    if str(lang or "").strip().lower().startswith("en"):
        return _contains_any_token(text, _TASK_PROGRESS_STATUS_MARKERS_EN)
    return _contains_any_token(text, _TASK_PROGRESS_STATUS_MARKERS_ZH)

def _reply_has_next_action(reply_text: str, binding: dict[str, Any], *, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    next_action = str(binding.get("next_action", "")).strip()
    if next_action and next_action in text:
        return True
    if str(lang or "").strip().lower().startswith("en"):
        return _contains_any_token(text, _TASK_PROGRESS_NEXT_ACTION_MARKERS_EN)
    return _contains_any_token(text, _TASK_PROGRESS_NEXT_ACTION_MARKERS_ZH)

def _reply_low_information(reply_text: str, *, lang: str) -> bool:
    text = re.sub(r"\s+", " ", str(reply_text or "").strip())
    if not text:
        return True
    low = text.lower()
    if str(lang or "").strip().lower().startswith("en"):
        token_hit = any(token in low for token in _TASK_PROGRESS_LOW_INFO_ACKS_EN)
    else:
        token_hit = any(token in text for token in _TASK_PROGRESS_LOW_INFO_ACKS_ZH)
    if not token_hit:
        return False
    if str(lang or "").strip().lower().startswith("en"):
        if any(token in low for token in ("current", "status", "phase", "next", "blocked", "run", "project")):
            return False
    else:
        if any(token in text for token in ("当前", "目前", "进度", "阶段", "卡点", "阻塞", "下一步", "已经", "后台", "项目", "run")):
            return False
    return len(text) <= 40

def _reply_has_ungrounded_completion_claim(reply_text: str, *, project_context: dict[str, Any] | None, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    if _is_final_ready_context(project_context):
        return False
    if str(lang or "").strip().lower().startswith("en"):
        return _contains_any_token(text, _TASK_PROGRESS_COMPLETION_CLAIMS_EN)
    return _contains_any_token(text, _TASK_PROGRESS_COMPLETION_CLAIMS_ZH)

def _reply_transition_incomplete(reply_text: str, *, has_next_action: bool, lang: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    if str(lang or "").strip().lower().startswith("en"):
        transition_claimed = _contains_any_token(text, _TASK_PROGRESS_TRANSITION_MARKERS_EN)
        if not transition_claimed:
            return False
        has_reason = _contains_any_token(text, _TASK_PROGRESS_REASON_MARKERS_EN)
        has_owner = _contains_any_token(text, _TASK_PROGRESS_OWNER_MARKERS_EN)
        return (not has_reason) or (not has_owner) or (not has_next_action)
    transition_claimed = _contains_any_token(text, _TASK_PROGRESS_TRANSITION_MARKERS_ZH)
    if not transition_claimed:
        return False
    has_reason = _contains_any_token(text, _TASK_PROGRESS_REASON_MARKERS_ZH)
    has_owner = _contains_any_token(text, _TASK_PROGRESS_OWNER_MARKERS_ZH)
    return (not has_reason) or (not has_owner) or (not has_next_action)

def _compose_grounded_progress_reply(*, binding: dict[str, Any], lang: str, no_change: bool = False) -> tuple[str, str]:
    phase = sanitize_inline_text(str(binding.get("current_phase", "")), max_chars=80) or ("execution" if lang == "en" else "执行推进")
    blocker = sanitize_inline_text(humanize_progress_runtime_text(str(binding.get("current_blocker", "")), lang=lang), max_chars=160)
    next_action = sanitize_inline_text(humanize_progress_runtime_text(str(binding.get("next_action", "")), lang=lang), max_chars=220)
    done_items = [
        sanitize_inline_text(str(item), max_chars=80)
        for item in list(binding.get("last_confirmed_items", []) or [])[:3]
        if sanitize_inline_text(str(item), max_chars=80)
    ]
    question_needed = str(binding.get("question_needed", "")).strip().lower() in {"yes", "true", "1"}
    blocking_question = sanitize_inline_text(str(binding.get("blocking_question", "")), max_chars=140)
    rows: list[str] = []
    next_question = ""
    if lang == "en":
        if no_change:
            rows.append(f"Current status is unchanged from the previous update; I am still in {phase} and the same blocker truth remains.")
        else:
            rows.append(f"Current phase: {phase}.")
        if done_items and not no_change:
            rows.append(f"Completed so far: {'; '.join(done_items)}.")
        if blocker and blocker.lower() != "none":
            rows.append(f"Current blocker: {blocker}.")
        else:
            rows.append("No new blocker right now.")
        if next_action:
            rows.append(f"Next step: {next_action}.")
        if question_needed and blocking_question:
            next_question = normalize_question(blocking_question)
            rows.append(f"I need one decision before I continue: {blocking_question}")
        return "\n\n".join([x for x in rows if x]).strip(), next_question
    if no_change:
        rows.append(f"当前状态和上一条一致，我还在{phase}阶段处理同一个卡点。")
    else:
        rows.append(f"目前在{phase}这个阶段。")
    if done_items and (not no_change):
        rows.append("我这边已完成：" + "、".join(done_items) + "。")
    if blocker and blocker.lower() != "none":
        rows.append(f"当前卡点是：{blocker}。")
    else:
        rows.append("暂时没有新增阻塞。")
    if next_action:
        rows.append(f"下一步我会继续处理：{next_action}。")
    if question_needed and blocking_question:
        next_question = normalize_question(blocking_question)
        rows.append(f"继续前我只需要你确认这一项：{blocking_question}")
    return "\n\n".join([x for x in rows if x]).strip(), next_question
def _load_previous_reply_snapshot(run_dir: Path) -> tuple[str, str]:
    doc = read_json_doc(run_dir / SUPPORT_REPLY_REL_PATH)
    if not isinstance(doc, dict):
        return "", ""
    previous_reply = str(doc.get("reply_text", "")).strip()
    guard = doc.get("runtime_progress_guard", {})
    if not isinstance(guard, dict):
        guard = {}
    previous_status_hash = str(guard.get("status_hash", "")).strip()
    return previous_reply, previous_status_hash

def enforce_task_progress_runtime_guard(
    *,
    run_dir: Path,
    reply_text: str,
    next_question: str,
    conversation_mode: str,
    project_context: dict[str, Any] | None,
    task_summary_hint: str = "",
    lang: str = "zh",
    question_explicit: bool = False,
) -> tuple[str, str, dict[str, Any]]:
    mode = str(conversation_mode or "").strip().upper()
    if not _task_like_mode(mode):
        return reply_text, next_question, {"applied": False, "status_hash": "", "reasons": []}
    if (not isinstance(project_context, dict)) or (not sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)):
        return reply_text, next_question, {"applied": False, "status_hash": "", "reasons": []}

    status_hash, binding = build_progress_digest(project_context=project_context, task_summary_hint=task_summary_hint)
    if not binding:
        binding = build_progress_binding(project_context=project_context, task_summary_hint=task_summary_hint)
    if not binding:
        return reply_text, next_question, {"applied": False, "status_hash": status_hash, "reasons": []}

    has_status_anchor = _reply_has_status_anchor(reply_text, binding, lang=lang)
    has_next_action = _reply_has_next_action(reply_text, binding, lang=lang)
    low_info = _reply_low_information(reply_text, lang=lang)
    transition_incomplete = _reply_transition_incomplete(reply_text, has_next_action=has_next_action, lang=lang)
    ungrounded_completion = _reply_has_ungrounded_completion_claim(reply_text, project_context=project_context, lang=lang)
    question_needed = str(binding.get("question_needed", "")).strip().lower() in {"yes", "true", "1"}
    blocking_question = sanitize_inline_text(str(binding.get("blocking_question", "")), max_chars=140)

    previous_reply, previous_status_hash = _load_previous_reply_snapshot(run_dir)
    repeated_same_state = bool(
        status_hash
        and previous_status_hash
        and status_hash == previous_status_hash
        and _normalize_reply_semantic(reply_text) == _normalize_reply_semantic(previous_reply)
    )

    reasons: list[str] = []
    if low_info:
        reasons.append("low_information_reply")
    if low_info and (not has_status_anchor):
        reasons.append("missing_status_anchor")
    if low_info and (not has_next_action):
        reasons.append("missing_next_action")
    if transition_incomplete:
        reasons.append("transition_fields_incomplete")
    if ungrounded_completion:
        reasons.append("ungrounded_completion_claim")
    if repeated_same_state:
        reasons.append("repeat_same_state")
    if question_explicit and (not question_needed) and str(next_question or "").strip():
        reasons.append("question_not_needed")
    if question_needed and (not str(next_question or "").strip()) and blocking_question:
        reasons.append("missing_blocking_question")

    if not reasons:
        return reply_text, next_question, {"applied": False, "status_hash": status_hash, "reasons": []}

    guarded_reply, guarded_question = _compose_grounded_progress_reply(
        binding=binding,
        lang=("en" if str(lang or "").strip().lower().startswith("en") else "zh"),
        no_change=("repeat_same_state" in reasons),
    )
    if (not guarded_question) and question_needed and blocking_question:
        guarded_question = normalize_question(blocking_question)
    return (
        guarded_reply or reply_text,
        guarded_question if guarded_question or question_needed else "",
        {
            "applied": True,
            "status_hash": status_hash,
            "reasons": reasons,
            "has_status_anchor": has_status_anchor,
            "has_next_action": has_next_action,
        },
    )

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

def user_confirms_package_delivery(text: str) -> bool:
    raw = sanitize_inline_text(str(text), max_chars=280)
    if not raw:
        return False
    low = raw.lower()
    compact = re.sub(r"\s+", "", low)
    if any(token in compact for token in ("可以发包", "可以发zip", "发zip", "发吧", "发我吧", "就这个发")):
        return True
    if any(token in compact for token in ("ok发", "oksend", "sendit", "looksgood")):
        return True
    return compact in {"可以", "行", "好的", "好", "ok", "okay", "没问题"}

def is_zip_confirmation_after_recent_package_request(user_messages: list[str]) -> bool:
    if len(user_messages) < 2:
        return False
    current = sanitize_inline_text(user_messages[-1], max_chars=280)
    if not user_confirms_package_delivery(current):
        return False
    for prev in reversed(user_messages[:-1][-3:]):
        prev_text = sanitize_inline_text(prev, max_chars=280)
        if not prev_text:
            continue
        return user_requests_project_package(prev_text)
    return False

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
    zip_confirmation_intent: bool = False,
) -> list[dict[str, Any]]:
    out = [dict(item) for item in actions if isinstance(item, dict)]
    if not isinstance(delivery_state, dict):
        return out
    if not bool(delivery_state.get("channel_can_send_files", False)):
        return out
    package_delivery_allowed = bool(delivery_state.get("package_delivery_allowed", False))
    screenshot_ready = bool(delivery_state.get("screenshot_ready", False))
    if not package_delivery_allowed:
        out = [
            dict(item)
            for item in out
            if str(item.get("type", "")).strip().lower() != "send_project_package"
        ]
    if not screenshot_ready:
        out = [
            dict(item)
            for item in out
            if str(item.get("type", "")).strip().lower() != "send_project_screenshot"
        ]
    allow_delivery_actions = should_expose_delivery_context(conversation_mode, user_text)
    if not allow_delivery_actions:
        out = [
            dict(item)
            for item in out
            if str(item.get("type", "")).strip().lower() not in {"send_project_package", "send_project_screenshot"}
        ]
    types = {str(item.get("type", "")).strip().lower() for item in out}
    zip_intent = user_requests_project_package(user_text) or bool(zip_confirmation_intent)
    if zip_intent and bool(delivery_state.get("package_ready", False)) and package_delivery_allowed and "send_project_package" not in types:
        out.append({"type": "send_project_package", "format": "zip"})
        types.add("send_project_package")
    screenshot_count = len([x for x in delivery_state.get("screenshot_files", []) if str(x).strip()])
    if zip_intent and (not package_delivery_allowed) and screenshot_count > 0 and "send_project_screenshot" not in types:
        out.append({"type": "send_project_screenshot", "count": 1})
        types.add("send_project_screenshot")
    if user_requests_project_screenshot(user_text) and screenshot_count > 0 and "send_project_screenshot" not in types:
        out.append({"type": "send_project_screenshot", "count": min(3, screenshot_count)})
    return out

def normalize_reply_text(raw_reply: str, next_question: str) -> str:
    raw = str(raw_reply or "").strip()
    raw = re.sub(r"```[\s\S]*?```", "", raw).strip()

    if raw and not contains_forbidden_reply(raw):
        return raw
    if not raw:
        if detect_lang_hint(raw, next_question).startswith("en"):
            return "I do not have a customer-ready reply yet."
        return "这边没拿到可直接发出的回复。"

    if frontend_render_fallback_reply is not None:
        try:
            rendered = frontend_render_fallback_reply(
                intent="guide_recovery",
                lang_hint=detect_lang_hint(raw, next_question) or "zh",
                project_context={},
                next_question=next_question,
                previous_reply_text="",
            )
            fallback_text = str(rendered.get("reply_text", "")).strip()
            fallback_question = normalize_question(str(rendered.get("next_question", "")).strip())
            if fallback_text and not contains_forbidden_reply(fallback_text):
                if fallback_question:
                    return f"{fallback_text}\n\n{fallback_question}"
                return fallback_text
        except Exception:
            pass

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

def append_delivery_preview_confirmation_note(
    reply_text: str,
    *,
    user_text: str,
    delivery_state: dict[str, Any] | None,
    actions: list[dict[str, Any]],
    zip_confirmation_intent: bool = False,
) -> str:
    if not isinstance(delivery_state, dict):
        return str(reply_text or "").strip()
    if bool(delivery_state.get("package_delivery_allowed", False)):
        return str(reply_text or "").strip()
    if not bool(delivery_state.get("screenshot_ready", False)):
        return str(reply_text or "").strip()
    if not (user_requests_project_package(user_text) or bool(zip_confirmation_intent)):
        return str(reply_text or "").strip()
    action_types = {str(item.get("type", "")).strip().lower() for item in actions if isinstance(item, dict)}
    if "send_project_screenshot" not in action_types:
        return str(reply_text or "").strip()
    note = "我先把当前效果给你看；你确认“可以发包”后，我会继续推进并在达到可交付状态时第一时间发 zip。"
    text = str(reply_text or "").strip()
    if note in text:
        return text
    if not text:
        return note
    return f"{text}\n\n{note}"

def build_frontend_backend_state(
    *,
    provider_result: dict[str, Any],
    raw_doc: dict[str, Any],
    project_context: dict[str, Any] | None,
    conversation_mode: str,
    has_user_msgs: bool,
    task_summary_hint: str = "",
) -> dict[str, Any]:
    return build_frontend_backend_truth_state(
        provider_result=provider_result,
        raw_doc=raw_doc,
        project_context=project_context,
        conversation_mode=conversation_mode,
        has_user_msgs=has_user_msgs,
        task_summary_hint=task_summary_hint,
        build_progress_binding=build_progress_binding,
    )

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
    frontdesk_state: dict[str, Any] | None = None,
    latest_user_message_override: str = "",
    shared_state_snapshots: Mapping[str, Any] | None = None,
    session_state: dict[str, Any] | None = None,
    allow_dedupe_suppress: bool = False,
    dedupe_source_kind: str = "",
) -> dict[str, Any]:
    raw_doc = provider_doc if isinstance(provider_doc, dict) else fallback_reply_doc(provider_result)
    raw_reply_text = str(raw_doc.get("reply_text", ""))
    raw_next_question = str(raw_doc.get("next_question", ""))
    history = load_inbox_history(run_dir, limit=12)
    user_msgs = [str(item.get("text", "")).strip() for item in history if str(item.get("text", "")).strip()]
    previous_reply_text = load_last_reply_text(run_dir)
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
    question_explicit = bool(str(raw_next_question or "").strip())
    latest_user_message_for_render = sanitize_inline_text(latest_user_message_override, max_chars=280)
    if not latest_user_message_for_render:
        latest_user_message_for_render = user_msgs[-1] if user_msgs else task_summary_hint
    frontdesk_strategy: dict[str, Any] = {}
    shared_current = {}
    shared_render = {}
    if isinstance(shared_state_snapshots, Mapping):
        current_doc = shared_state_snapshots.get("current", {})
        render_doc = shared_state_snapshots.get("render", {})
        if isinstance(current_doc, Mapping):
            shared_current = dict(current_doc)
        if isinstance(render_doc, Mapping):
            shared_render = dict(render_doc)
    has_frontdesk_state = isinstance(frontdesk_state, dict) and bool(frontdesk_state)
    if frontend_reply_strategy_from_frontdesk_state is not None and has_frontdesk_state:
        try:
            frontdesk_strategy = frontend_reply_strategy_from_frontdesk_state(
                frontdesk_state or {},
                conversation_mode=conversation_mode,
            )
        except Exception:
            frontdesk_strategy = {}
    use_frontend_render = bool(frontdesk_strategy.get("prefer_frontend_render", not is_non_project_support_mode(conversation_mode)))
    if render_frontend_output is not None and use_frontend_render:
        try:
            summary_text = task_summary_hint.strip() or (user_msgs[-1] if user_msgs else raw_reply_text)
            shared_goal = sanitize_inline_text(str(shared_current.get("current_task_goal", "")), max_chars=260)
            if shared_goal:
                summary_text = shared_goal
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
                    "frontdesk_state": frontdesk_state or {},
                    "frontdesk_reply_strategy": frontdesk_strategy,
                    "shared_state_current": shared_current,
                    "shared_state_render": shared_render,
                },
            )
            reply_text = str(getattr(rendered, "reply_text", "")).strip()
            followups = list(getattr(rendered, "followup_questions", ()) or [])
            if followups:
                next_question = normalize_question(str(followups[0]))
                question_explicit = True
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

    latest_user_text = user_msgs[-1] if user_msgs else task_summary_hint
    zip_confirmation_intent = is_zip_confirmation_after_recent_package_request(user_msgs)
    actions = synthesize_delivery_actions(
        actions=normalize_actions(raw_doc.get("actions")),
        user_text=latest_user_text,
        delivery_state=delivery_state,
        conversation_mode=conversation_mode,
        zip_confirmation_intent=zip_confirmation_intent,
    )
    actions = inject_ready_delivery_actions(
        actions=actions,
        project_context=project_context,
        delivery_state=delivery_state,
        source_hint=source_hint,
    )
    runtime_guard: dict[str, Any] = {"applied": False, "status_hash": "", "reasons": []}
    if not str(provider_result.get("degraded_from", "")).strip():
        reply_text, next_question, runtime_guard = enforce_task_progress_runtime_guard(
            run_dir=run_dir,
            reply_text=reply_text,
            next_question=next_question,
            conversation_mode=conversation_mode,
            project_context=project_context,
            task_summary_hint=task_summary_hint,
            lang=lang,
            question_explicit=question_explicit,
        )
    reply_text = align_reply_with_delivery_actions(reply_text, actions=actions, source_hint=source_hint)
    reply_text = append_delivery_preview_confirmation_note(
        reply_text,
        user_text=latest_user_text,
        delivery_state=delivery_state,
        actions=actions,
        zip_confirmation_intent=zip_confirmation_intent,
    )
    reply_intent = ""
    reply_template_id = ""
    reply_policy: dict[str, Any] = {"fallback_used": False, "reasons": []}
    if frontend_enforce_reply_policy is not None:
        try:
            policy_project_context = inject_provider_truth_context(
                project_context=project_context,
                provider_result=provider_result,
                raw_doc=raw_doc,
            )
            reply_memory = latest_reply_dedupe_memory(session_state) if isinstance(session_state, dict) else {}
            policy_out = frontend_enforce_reply_policy(
                reply_text=reply_text,
                next_question=next_question,
                conversation_mode=conversation_mode,
                lang_hint=lang,
                project_context=policy_project_context,
                provider_status=str(provider_result.get("status", "")).strip(),
                previous_reply_text=previous_reply_text,
                reply_memory=reply_memory,
                now_ts=now_iso(),
                provider_mode=provider,
                source_kind=sanitize_inline_text(
                    dedupe_source_kind
                    or ("fallback" if str(provider_result.get("status", "")).strip().lower() in {"exec_failed", "failed", "error", "deferred"} else "provider"),
                    max_chars=24,
                ),
                allow_suppress=bool(allow_dedupe_suppress),
            )
            policy_reply_text = str(policy_out.get("reply_text", "")).strip()
            if policy_reply_text:
                reply_text = policy_reply_text
            policy_next_question = str(policy_out.get("next_question", "")).strip()
            next_question = normalize_question(policy_next_question) if policy_next_question else ""
            reply_intent = sanitize_inline_text(str(policy_out.get("intent", "")), max_chars=32).lower()
            reply_template_id = sanitize_inline_text(str(policy_out.get("template_id", "")), max_chars=80)
            reply_policy = {
                "fallback_used": bool(policy_out.get("fallback_used", False)),
                "reasons": [
                    sanitize_inline_text(str(item), max_chars=60)
                    for item in list(policy_out.get("reasons", []))
                    if sanitize_inline_text(str(item), max_chars=60)
                ][:8],
                "dedupe_action": sanitize_inline_text(str(policy_out.get("dedupe_action", "send")), max_chars=24) or "send",
                "similarity_max": float(policy_out.get("similarity_max", 0.0) or 0.0),
                "suppressed": bool(policy_out.get("suppressed", False)),
            }
            if isinstance(session_state, dict):
                mem = policy_out.get("reply_memory", {})
                if isinstance(mem, dict):
                    session_state["reply_dedupe_memory"] = mem
        except Exception as exc:
            reply_policy = {"fallback_used": False, "reasons": [f"policy_error:{sanitize_inline_text(str(exc), max_chars=80)}"]}

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
    if isinstance(frontdesk_state, dict):
        frontdesk_name = sanitize_inline_text(str(frontdesk_state.get("state", "")), max_chars=40)
        interrupt_kind = sanitize_inline_text(str(frontdesk_state.get("interrupt_kind", "")), max_chars=40)
        if frontdesk_name:
            debug_combined += f"; frontdesk_state={frontdesk_name}"
        if interrupt_kind:
            debug_combined += f"; interrupt_kind={interrupt_kind}"
    if isinstance(project_context, dict):
        run_id = sanitize_inline_text(str(project_context.get("run_id", "")), max_chars=80)
        if run_id:
            debug_combined += f"; run_id={run_id}"
        whiteboard = project_context.get("whiteboard", {})
        if isinstance(whiteboard, dict):
            hit_count = len(list(whiteboard.get("hits", []))) if isinstance(whiteboard.get("hits", []), list) else 0
            if hit_count:
                debug_combined += f"; whiteboard_hits={hit_count}"
    if isinstance(runtime_guard, dict) and bool(runtime_guard.get("applied", False)):
        reasons = ",".join(str(item) for item in list(runtime_guard.get("reasons", []))[:6] if str(item).strip())
        if reasons:
            debug_combined += f"; runtime_guard={reasons}"
    if reply_intent:
        debug_combined += f"; reply_intent={reply_intent}"
    if bool(reply_policy.get("fallback_used", False)):
        debug_combined += "; reply_policy=fallback"
    policy_reasons = ",".join(str(item) for item in list(reply_policy.get("reasons", []))[:6] if str(item).strip())
    if policy_reasons:
        debug_combined += f"; reply_policy_reasons={policy_reasons}"
    if reply_template_id:
        debug_combined += f"; template_id={reply_template_id}"
    if str(reply_policy.get("dedupe_action", "")).strip():
        debug_combined += f"; dedupe_action={sanitize_inline_text(str(reply_policy.get('dedupe_action', '')), max_chars=24)}"
    if bool(reply_policy.get("suppressed", False)):
        debug_combined += "; dedupe_suppressed=true"

    append_log(run_dir / "logs" / "support_bot.debug.log", f"[{now_iso()}] {debug_combined}\n")
    reply_text = align_reply_with_delivery_actions(reply_text, actions=actions, source_hint=source_hint)

    return {
        "schema_version": "ctcp-support-reply-v1",
        "ts": now_iso(),
        "provider": provider,
        "provider_status": provider_status,
        "reply_text": reply_text,
        "next_question": next_question,
        "actions": actions,
        "reply_intent": reply_intent or "acknowledge_user",
        "reply_template_id": reply_template_id,
        "reply_policy": reply_policy,
        "debug_notes": debug_combined,
        "runtime_progress_guard": runtime_guard if isinstance(runtime_guard, dict) else {},
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

    config, cfg_msg = load_dispatch_config(run_dir)
    append_log(run_dir / "logs" / "support_bot.dispatch.log", f"[{now_iso()}] load_dispatch_config: {cfg_msg}\n")

    detected_mode = detect_conversation_mode(run_dir, user_text, session_state)
    conversation_mode = maybe_override_conversation_mode_with_model(
        run_dir=run_dir,
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        detected_mode=detected_mode,
        session_state=session_state,
        config=config,
        provider_override=provider_override,
    )
    record_turn_memory(session_state, user_text=user_text, source=source, conversation_mode=conversation_mode)

    project_context, session_state = sync_project_context(
        run_dir=run_dir,
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
    )
    delivery_state = collect_public_delivery_state(
        session_state=session_state,
        project_context=project_context,
        source=source,
        support_run_dir=run_dir,
    )
    t2p_report: dict[str, Any] = {}
    if should_trigger_t2p_state_machine(
        session_state=session_state,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
    ):
        t2p_report = run_t2p_state_machine(
            run_dir=run_dir,
            session_state=session_state,
            user_text=user_text,
            source=source,
            conversation_mode=conversation_mode,
            delivery_state=delivery_state,
        )
        delivery_state = collect_public_delivery_state(
            session_state=session_state,
            project_context=project_context,
            source=source,
            support_run_dir=run_dir,
        )
    frontdesk_state = sync_frontdesk_state(
        session_state,
        user_text=user_text,
        conversation_mode=conversation_mode,
        project_context=project_context,
        delivery_state=delivery_state,
    )
    sync_active_task_truth(
        session_state,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
        delivery_state=delivery_state,
    )
    shared_state_snapshots = sync_shared_state_workspace(
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
    )
    save_support_session_state(run_dir, session_state)

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
        frontdesk_state=frontdesk_state,
        shared_state_snapshots=shared_state_snapshots,
        session_state=session_state,
        allow_dedupe_suppress=False,
        dedupe_source_kind="provider",
    )
    if (
        isinstance(t2p_report, dict)
        and str(t2p_report.get("pass_fail", "")).strip().upper() == "PASS"
        and str(source or "").strip().lower() == "telegram"
        and bool(delivery_state.get("package_delivery_allowed", False))
    ):
        action_types = {
            str(item.get("type", "")).strip().lower()
            for item in (final_doc.get("actions", []) if isinstance(final_doc.get("actions", []), list) else [])
            if isinstance(item, dict)
        }
        if "send_project_package" not in action_types:
            actions = list(final_doc.get("actions", [])) if isinstance(final_doc.get("actions", []), list) else []
            actions.append({"type": "send_project_package", "format": "zip"})
            final_doc["actions"] = actions
            append_event(
                run_dir,
                "SUPPORT_T2P_PACKAGE_ACTION_INJECTED",
                SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix(),
            )
    write_json(run_dir / SUPPORT_REPLY_REL_PATH, final_doc)
    frontdesk_state = sync_frontdesk_state(
        session_state,
        user_text=user_text,
        conversation_mode=conversation_mode,
        project_context=project_context,
        delivery_state=delivery_state,
        provider_result=result,
    )
    sync_active_task_truth(
        session_state,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
        delivery_state=delivery_state,
        provider_result=result,
        assistant_reply_text=sanitize_inline_text(str(final_doc.get("reply_text", "")), max_chars=360),
    )
    shared_state_snapshots = sync_shared_state_workspace(
        chat_id=chat_id,
        user_text=user_text,
        source=source,
        conversation_mode=conversation_mode,
        session_state=session_state,
        frontdesk_state=frontdesk_state,
        project_context=project_context,
    )
    remember_progress_notification(
        session_state,
        project_context=project_context,
        task_summary_hint=current_project_brief(session_state),
    )
    session_state["latest_support_context"] = {
        "run_id": str(project_context.get("run_id", "")) if isinstance(project_context, dict) else "",
        "provider_status": str(final_doc.get("provider_status", "")),
        "conversation_mode": conversation_mode,
        "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80),
        "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80),
        "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
        "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220),
        "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
        "message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
        "frontdesk_state": str(frontdesk_state.get("state", "")),
        "interrupt_kind": str(frontdesk_state.get("interrupt_kind", "")),
        "package_ready": bool(delivery_state.get("package_ready", False)),
        "package_delivery_allowed": bool(delivery_state.get("package_delivery_allowed", False)),
        "package_blocked_reason": sanitize_inline_text(str(delivery_state.get("package_blocked_reason", "")), max_chars=120),
        "package_delivery_mode": str(delivery_state.get("package_delivery_mode", "")).strip(),
        "package_structure_hint": list(delivery_state.get("package_structure_hint", [])),
        "screenshot_ready": bool(delivery_state.get("screenshot_ready", False)),
        "t2p_state": sanitize_inline_text(str(latest_generation_state(session_state).get("current_state", "")), max_chars=32),
        "t2p_pass_fail": sanitize_inline_text(str(latest_generation_state(session_state).get("last_pass_fail", "")), max_chars=12),
        "t2p_failure_stage": sanitize_inline_text(
            str(latest_generation_state(session_state).get("last_failure_stage", "")),
            max_chars=40,
        ),
        "t2p_report_path": sanitize_inline_text(
            str(latest_generation_state(session_state).get("last_report_path", "")),
            max_chars=220,
        ),
        "shared_state_task_id": sanitize_inline_text(str((shared_state_snapshots or {}).get("task_id", "")), max_chars=80),
        "shared_state_workspace_root": sanitize_inline_text(str((shared_state_snapshots or {}).get("workspace_root", "")), max_chars=260),
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
    screenshot_files = [Path(str(x)).resolve() for x in prioritize_screenshot_files(delivery_state.get("screenshot_files", []))]
    export_dir = run_dir / SUPPORT_EXPORTS_REL_DIR

    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("type", "")).strip().lower()
        if action_type == "send_project_package":
            if not bool(delivery_state.get("package_delivery_allowed", False)):
                blocked_reason = sanitize_inline_text(str(delivery_state.get("package_blocked_reason", "")), max_chars=120)
                if blocked_reason:
                    plan["errors"].append(f"package requested but blocked: {blocked_reason}")
                else:
                    plan["errors"].append("package requested but package delivery gate is blocked")
                continue
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
        return telegram_post_form(self.base, method, params, timeout_sec=self.timeout_sec + 15)

    def _post_multipart(self, method: str, params: dict[str, Any], file_field: str, file_path: Path) -> Any:
        return telegram_post_multipart(self.base, method, params, file_field, file_path, timeout_sec=self.timeout_sec + 30)

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

    def clear_webhook(self, drop_pending_updates: bool = False) -> None:
        self._post(
            "deleteWebhook",
            {
                "drop_pending_updates": "true" if drop_pending_updates else "false",
            },
        )

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
    """Build status reply doc for proactive progress updates."""
    delivery_state = collect_public_delivery_state(
        session_state=session_state,
        project_context=project_context,
        source="telegram",
        support_run_dir=run_dir,
    )
    lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
    synthetic_status_turn = "what's the latest progress?" if lang_hint.startswith("en") else "现在做到什么程度了"

    # Proactive status updates use grounded render path; provider draft is optional.
    result = {"status": "executed", "reason": "grounded_status_reply"}
    provider_doc = {"reply_text": "", "next_question": "", "actions": [], "debug_notes": "grounded_status_reply"}

    # Proactive status render should not mutate live frontdesk/session state.
    shadow_state = copy.deepcopy(session_state)
    frontdesk_state = sync_frontdesk_state(
        shadow_state,
        user_text=synthetic_status_turn,
        conversation_mode="STATUS_QUERY",
        project_context=project_context,
        delivery_state=delivery_state,
    )
    doc = build_final_reply_doc(
        run_dir=run_dir,
        provider=str(result.get("provider", "api_agent")),
        provider_result=result,
        provider_doc=provider_doc,
        project_context=project_context,
        source_hint="telegram",
        conversation_mode="STATUS_QUERY",
        task_summary_hint=current_project_brief(session_state),
        lang_hint=lang_hint,
        delivery_state=delivery_state,
        frontdesk_state=frontdesk_state,
        latest_user_message_override=synthetic_status_turn,
        session_state=shadow_state,
        allow_dedupe_suppress=True,
        dedupe_source_kind="proactive",
    )
    return doc

def _controller_decision_reply_text(*, project_context: dict[str, Any] | None, decision_prompt: str, lang_hint: str) -> str:
    prompt = sanitize_inline_text(decision_prompt, max_chars=280)
    if not prompt and isinstance(project_context, dict):
        status = project_context.get("status", {})
        if isinstance(status, dict):
            gate = status.get("gate", {})
            if isinstance(gate, dict):
                prompt = sanitize_inline_text(str(gate.get("reason", "")), max_chars=280)
    if not prompt:
        prompt = "这一步需要你确认一个关键选择。"
    if frontend_render_fallback_reply is not None:
        try:
            rendered = frontend_render_fallback_reply(
                intent="ask_decision",
                lang_hint=str(lang_hint or "").strip().lower() or "zh",
                project_context=project_context or {},
                next_question=prompt,
                previous_reply_text="",
            )
            text = str(rendered.get("reply_text", "")).strip()
            if text:
                return text
        except Exception:
            pass
    if str(lang_hint or "").strip().lower().startswith("en"):
        return f"We need one decision from you before I can continue: {prompt}"
    return f"现在这一步需要你先拍一个板：{prompt}"

def _normalize_proactive_progress_reply_text(reply_text: str, *, lang_hint: str = "") -> str:
    return ctcp_support_controller.normalize_proactive_progress_reply_text(
        reply_text,
        lang_hint=lang_hint,
        leak_tokens=_PROACTIVE_INTERNAL_GATE_LEAK_TOKENS,
    )


def _emit_controller_outbound_jobs(
    *,
    tg: TelegramClient,
    chat_id: int,
    run_dir: Path,
    session_state: dict[str, Any],
    project_context: dict[str, Any] | None,
    auto_advanced: bool,
    recovered_candidate: dict[str, Any] | None,
) -> int:
    jobs = ctcp_support_controller.pop_outbound_jobs(session_state, max_jobs=4)
    if not jobs:
        return 0
    sent = 0
    for job in jobs:
        kind = sanitize_inline_text(str(job.get("kind", "")), max_chars=24).lower()
        reply_text = ""
        provider_status = "executed"
        reply_actions: list[dict[str, Any]] = []
        reply_delivery_state: dict[str, Any] | None = None
        if kind == "decision":
            lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
            reply_text = _controller_decision_reply_text(
                project_context=project_context,
                decision_prompt=str(job.get("decision_prompt", "")),
                lang_hint=lang_hint,
            )
        else:
            doc = build_grounded_status_reply_doc(run_dir=run_dir, session_state=session_state, project_context=project_context)
            reply_text = str(doc.get("reply_text", "")).strip()
            provider_status = str(doc.get("provider_status", "executed")).strip() or "executed"
            reply_actions = normalize_actions(doc.get("actions", [])); reply_delivery_state = collect_public_delivery_state(session_state=session_state, project_context=project_context, source="telegram", support_run_dir=run_dir)
            if not reply_text:
                continue
            write_json(run_dir / SUPPORT_REPLY_REL_PATH, doc)
        if kind == "progress":
            lang_hint = str(_state_zone(session_state, "session_profile").get("lang_hint", "")).strip().lower()
            reply_text = _normalize_proactive_progress_reply_text(reply_text, lang_hint=lang_hint)
        if not reply_text:
            continue
        binding = build_progress_binding(
            project_context=project_context,
            task_summary_hint=current_project_brief(session_state),
        )
        sync_active_task_truth(
            session_state,
            user_text="现在做到什么程度了",
            source="telegram_auto_resume",
            conversation_mode="STATUS_QUERY",
            frontdesk_state=current_frontdesk_state(session_state),
            project_context=project_context,
            delivery_state=collect_public_delivery_state(
                session_state=session_state,
                project_context=project_context,
                source="telegram",
                support_run_dir=run_dir,
            ),
            provider_result={"status": provider_status, "reason": str(job.get("reason", ""))},
            assistant_reply_text="",
        )
        frontdesk_state = current_frontdesk_state(session_state)
        session_state["latest_support_context"] = {
            "run_id": str((project_context or {}).get("run_id", "")),
            "provider_status": provider_status,
            "conversation_mode": "STATUS_QUERY",
            "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80),
            "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80),
            "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
            "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220),
            "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
            "message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
            "frontdesk_state": str(frontdesk_state.get("state", "")),
            "interrupt_kind": str(frontdesk_state.get("interrupt_kind", "")),
            "package_ready": False,
            "package_delivery_mode": "",
            "package_structure_hint": [],
            "screenshot_ready": False,
        }
        try:
            emit_public_message(tg, chat_id, reply_text)
            if reply_actions:
                plan = emit_public_delivery(tg, chat_id=chat_id, run_dir=run_dir, actions=reply_actions, delivery_state=reply_delivery_state)
                if delivery_plan_failed(reply_actions, plan): raise RuntimeError("public delivery action produced no sent files")
        except Exception as exc:
            ctcp_support_controller.requeue_outbound_job(session_state, job, sanitize_inline_text=sanitize_inline_text)
            append_event(
                run_dir,
                "SUPPORT_PROGRESS_SEND_FAILED",
                SUPPORT_REPLY_REL_PATH.as_posix(),
                run_id=str((project_context or {}).get("run_id", "")),
                kind=kind,
                reason=str(job.get("reason", "")),
                error=sanitize_inline_text(str(exc), max_chars=220),
            )
            continue
        sent += 1
        ctcp_support_controller.mark_job_sent(
            session_state,
            job,
            now_ts=now_iso(),
            cooldown_sec=SUPPORT_NOTIFICATION_COOLDOWN_SEC,
        )
        if kind in {"progress", "result", "error"}:
            remember_progress_notification(
                session_state,
                project_context=project_context,
                task_summary_hint=current_project_brief(session_state),
                status_hash=str(job.get("status_hash", "")),
            )
        append_event(
            run_dir,
            "SUPPORT_PROGRESS_PUSHED",
            SUPPORT_REPLY_REL_PATH.as_posix(),
            run_id=str((project_context or {}).get("run_id", "")),
            auto_advanced=auto_advanced,
            recovered=bool(recovered_candidate),
            phase=str(binding.get("current_phase", "")),
            kind=kind,
            reason=str(job.get("reason", "")),
        )
    return sent

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

        project_context, _ = fetch_support_context_with_recovery(
            run_dir=run_dir,
            session_state=session_state,
            bound_run_id=bound_run_id,
            trigger="proactive_cycle",
        )
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

        annotate_plan_draft_recovery(project_context, attempted=False)
        auto_advanced = False
        if should_auto_advance_project_context(session_state, project_context):
            bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
            if bound_run_id:
                advance_steps = 4 if is_missing_plan_draft_context(project_context) else 2
                ctcp_front_bridge.ctcp_advance(bound_run_id, max_steps=advance_steps)
                latest_notification_state(session_state)["last_auto_advance_ts"] = now_iso()
                project_context, _ = fetch_support_context_with_recovery(
                    run_dir=run_dir,
                    session_state=session_state,
                    bound_run_id=bound_run_id,
                    trigger="proactive_post_advance",
                )
                annotate_plan_draft_recovery(project_context, attempted=True)
                auto_advanced = True

        status_hash, binding = build_progress_digest(
            project_context=project_context,
            task_summary_hint=current_project_brief(session_state),
        )
        if not status_hash:
            if recovered_candidate is not None:
                save_support_session_state(run_dir, session_state)
            continue

        proactive_delivery_state = collect_public_delivery_state(
            session_state=session_state,
            project_context=project_context,
            source="telegram",
            support_run_dir=run_dir,
        )
        proactive_frontdesk_state = sync_frontdesk_state(
            session_state,
            user_text="现在做到什么程度了",
            conversation_mode="STATUS_QUERY",
            project_context=project_context,
            delivery_state=proactive_delivery_state,
            provider_result={"status": "executed", "reason": "proactive_cycle"},
        )
        sync_active_task_truth(
            session_state,
            user_text="现在做到什么程度了",
            source="telegram_auto_resume",
            conversation_mode="STATUS_QUERY",
            frontdesk_state=proactive_frontdesk_state,
            project_context=project_context,
            delivery_state=proactive_delivery_state,
            provider_result={"status": "executed", "reason": "proactive_cycle"},
            assistant_reply_text="",
            rewrite_latest_user_turn=False,
        )
        session_state["latest_support_context"] = {
            "run_id": str((project_context or {}).get("run_id", "")),
            "provider_status": "executed",
            "conversation_mode": "STATUS_QUERY",
            "active_task_id": sanitize_inline_text(str(session_state.get("active_task_id", "")), max_chars=80),
            "active_run_id": sanitize_inline_text(str(session_state.get("active_run_id", "")), max_chars=80),
            "active_stage": sanitize_inline_text(str(session_state.get("active_stage", "")), max_chars=32),
            "active_blocker": sanitize_inline_text(str(session_state.get("active_blocker", "none")), max_chars=220),
            "active_next_action": sanitize_inline_text(str(session_state.get("active_next_action", "")), max_chars=220),
            "message_intent": sanitize_inline_text(str(session_state.get("latest_message_intent", "continue")), max_chars=24),
            "frontdesk_state": str(proactive_frontdesk_state.get("state", "")),
            "interrupt_kind": str(proactive_frontdesk_state.get("interrupt_kind", "")),
            "package_ready": bool(proactive_delivery_state.get("package_ready", False)),
            "package_delivery_allowed": bool(proactive_delivery_state.get("package_delivery_allowed", False)),
            "package_blocked_reason": sanitize_inline_text(str(proactive_delivery_state.get("package_blocked_reason", "")), max_chars=120),
            "package_delivery_mode": str(proactive_delivery_state.get("package_delivery_mode", "")).strip(),
            "package_structure_hint": list(proactive_delivery_state.get("package_structure_hint", [])),
            "screenshot_ready": bool(proactive_delivery_state.get("screenshot_ready", False)),
            "t2p_state": sanitize_inline_text(str(latest_generation_state(session_state).get("current_state", "")), max_chars=32),
            "t2p_pass_fail": sanitize_inline_text(str(latest_generation_state(session_state).get("last_pass_fail", "")), max_chars=12),
            "t2p_failure_stage": sanitize_inline_text(str(latest_generation_state(session_state).get("last_failure_stage", "")), max_chars=40),
            "t2p_report_path": sanitize_inline_text(str(latest_generation_state(session_state).get("last_report_path", "")), max_chars=220),
        }

        ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts=now_iso(),
            keepalive_interval_sec=SUPPORT_EXECUTION_KEEPALIVE_INTERVAL_SEC,
        )

        _ = _emit_controller_outbound_jobs(
            tg=tg,
            chat_id=chat_id,
            run_dir=run_dir,
            session_state=session_state,
            project_context=project_context,
            auto_advanced=auto_advanced,
            recovered_candidate=recovered_candidate,
        )
        save_support_session_state(run_dir, session_state)

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
    # 修复Windows编码问题：确保stdin使用UTF-8编码
    stdin_encoding = str(getattr(sys.stdin, "encoding", "") or "").lower()
    if stdin_encoding != "utf-8":
        import io
        stdin_buffer = getattr(sys.stdin, "buffer", None)
        if stdin_buffer is not None:
            try:
                sys.stdin = io.TextIOWrapper(stdin_buffer, encoding="utf-8", errors="replace")
            except Exception:
                pass

    user_text = utf8_clean(sys.stdin.read()).strip()
    if not user_text:
        print("[ctcp_support_bot] stdin message is empty", file=sys.stderr)
        return 1
    doc, _ = process_message(chat_id=chat_id, user_text=user_text, source="stdin", provider_override=provider_override)
    print(str(doc.get("reply_text", "")).strip())
    return 0

def _is_telegram_read_timeout(exc: Exception, error_text: str) -> bool:
    low = sanitize_inline_text(error_text, max_chars=320).lower()
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    timeout_markers = (
        "the read operation timed out",
        "read timed out",
        "timed out",
        "timeout",
    )
    return any(marker in low for marker in timeout_markers)

def _should_log_timeout_streak(streak: int) -> bool:
    return streak in {5, 10} or (streak > 0 and (streak % 20 == 0))

def run_telegram_mode(token: str, poll_seconds: int, allowlist_raw: str, provider_override: str = "") -> int:
    try:
        lock_path, lock_fh = acquire_telegram_poll_lock(token)
    except Exception as exc:
        print(f"[ctcp_support_bot] {exc}", file=sys.stderr)
        return 2

    try:
        tg = TelegramClient(token=token, timeout_sec=poll_seconds)
        allowlist = parse_allowlist(allowlist_raw)
        try:
            tg.clear_webhook(drop_pending_updates=False)
        except Exception as exc:
            print(f"[ctcp_support_bot] telegram deleteWebhook warning: {exc}", file=sys.stderr)

        offset = 0
        get_updates_error_streak = 0
        last_get_updates_error = ""
        while True:
            try:
                updates = tg.get_updates(offset)
                get_updates_error_streak = 0
                last_get_updates_error = ""
            except Exception as exc:
                error_text = sanitize_inline_text(str(exc), max_chars=320)
                get_updates_error_streak += 1
                previous_error = last_get_updates_error
                low = error_text.lower()
                timeout_like = _is_telegram_read_timeout(exc, error_text)
                if timeout_like:
                    if _should_log_timeout_streak(get_updates_error_streak):
                        print(
                            f"[ctcp_support_bot] telegram getUpdates timeout (streak={get_updates_error_streak}): {error_text}",
                            file=sys.stderr,
                        )
                    time.sleep(min(2.0, 0.3 + 0.1 * get_updates_error_streak))
                    try:
                        run_proactive_support_cycle(tg, allowlist)
                    except Exception as proactive_exc:
                        print(f"[ctcp_support_bot] proactive progress error: {proactive_exc}", file=sys.stderr)
                    last_get_updates_error = error_text
                    continue
                should_log = (
                    (error_text != previous_error)
                    or get_updates_error_streak in {1, 2, 3, 5, 10}
                    or (get_updates_error_streak % 20 == 0)
                )
                if should_log:
                    print(
                        f"[ctcp_support_bot] telegram getUpdates error (streak={get_updates_error_streak}): {error_text}",
                        file=sys.stderr,
                    )
                last_get_updates_error = error_text
                if "409" in low and "conflict" in low:
                    try:
                        tg.clear_webhook(drop_pending_updates=False)
                    except Exception:
                        pass
                    if get_updates_error_streak >= 3:
                        print(
                            "[ctcp_support_bot] persistent 409 conflict: another polling client may still be using this token.",
                            file=sys.stderr,
                        )
                time.sleep(min(8.0, 1.0 + 0.3 * get_updates_error_streak))
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
                    project_context: dict[str, Any] | None = None
                    bound_run_id = sanitize_inline_text(str(session_state.get("bound_run_id", "")), max_chars=80)
                    if bound_run_id:
                        try:
                            fetched, _ = fetch_support_context_with_recovery(
                                run_dir=support_run_dir,
                                session_state=session_state,
                                bound_run_id=bound_run_id,
                                trigger="telegram_post_reply",
                            )
                            if isinstance(fetched, dict):
                                project_context = fetched
                        except Exception:
                            project_context = None
                    delivery_state = collect_public_delivery_state(
                        session_state=session_state,
                        project_context=project_context,
                        source="telegram",
                        support_run_dir=support_run_dir,
                    )
                    plan = emit_public_delivery(
                        tg,
                        chat_id=chat_id,
                        run_dir=support_run_dir,
                        actions=list(doc.get("actions", []) or []),
                        delivery_state=delivery_state,
                    )
                    if delivery_plan_failed(list(doc.get("actions", []) or []), plan):
                        emit_public_message(tg, chat_id, "交付文件发送失败：我没有把 zip 或截图成功发出，后台会保留失败记录并等待下一次重试。")
                except Exception as exc:
                    print(f"[ctcp_support_bot] telegram update error: {exc}", file=sys.stderr)
                    continue
    finally:
        release_telegram_poll_lock(lock_path, lock_fh)

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
