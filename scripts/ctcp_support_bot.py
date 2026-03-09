#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

PROMPT_TEMPLATE_PATH = ROOT / "agents" / "prompts" / "support_lead_reply.md"
SUPPORT_INBOX_REL_PATH = Path("artifacts") / "support_inbox.jsonl"
SUPPORT_PROMPT_REL_PATH = Path("artifacts") / "support_prompt_input.md"
SUPPORT_REPLY_PROVIDER_REL_PATH = Path("artifacts") / "support_reply.provider.json"
SUPPORT_REPLY_REL_PATH = Path("artifacts") / "support_reply.json"
DISPATCH_CONFIG_REL_PATH = Path("artifacts") / "dispatch_config.json"

KNOWN_PROVIDERS = {"manual_outbox", "ollama_agent", "api_agent", "codex_agent", "mock_agent", "local_exec"}
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
    from frontend.conversation_mode_router import is_greeting_only as frontend_is_greeting_only
    from frontend.response_composer import render_frontend_output
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from frontend.conversation_mode_router import is_greeting_only as frontend_is_greeting_only
    from frontend.response_composer import render_frontend_output
except Exception:
    frontend_is_greeting_only = None  # type: ignore[assignment]
    render_frontend_output = None  # type: ignore[assignment]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utf8_clean(text: str) -> str:
    return str(text or "").encode("utf-8", errors="replace").decode("utf-8", errors="replace")


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
            "support_lead": "ollama_agent",
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
    provider = str(role_map.get("support_lead", config.get("mode", "manual_outbox"))).strip().lower()
    if provider not in KNOWN_PROVIDERS:
        return "manual_outbox"
    if provider == "local_exec":
        return "manual_outbox"
    return provider


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


def default_prompt_template() -> str:
    return (
        "You are CTCP Support Lead. Return JSON only.\n"
        "Keys: reply_text,next_question,actions,debug_notes.\n"
        "reply_text must be customer-facing only and never include logs, file paths, or stack traces.\n"
        "reply_text must be natural conversational prose (no rigid section labels).\n"
        "Ask at most one high-leverage follow-up question when route-changing details are missing.\n"
    )


def load_prompt_template() -> str:
    if PROMPT_TEMPLATE_PATH.exists():
        return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8", errors="replace")
    return default_prompt_template()


def build_support_prompt(run_dir: Path, chat_id: str, user_text: str) -> str:
    history = load_inbox_history(run_dir)
    context = {
        "schema_version": "ctcp-support-context-v1",
        "chat_id": chat_id,
        "ts": now_iso(),
        "history": history,
        "latest_user_message": user_text,
    }
    prompt = (
        load_prompt_template().rstrip()
        + "\n\n# Session Context (JSON)\n"
        + json.dumps(context, ensure_ascii=False, indent=2)
        + "\n"
    )
    write_text(run_dir / SUPPORT_PROMPT_REL_PATH, prompt)
    return prompt


def make_support_request(chat_id: str, user_text: str, prompt_text: str) -> dict[str, Any]:
    reason = prompt_text
    if len(reason) > 20000:
        reason = reason[-20000:]
    return {
        "role": "support_lead",
        "action": "reply",
        "target_path": SUPPORT_REPLY_PROVIDER_REL_PATH.as_posix(),
        "missing_paths": [SUPPORT_PROMPT_REL_PATH.as_posix(), SUPPORT_INBOX_REL_PATH.as_posix()],
        "reason": reason,
        "goal": f"support session {chat_id}",
        "input_text": user_text,
    }


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
    if frontend_is_greeting_only is not None:
        try:
            if frontend_is_greeting_only(raw):
                return True
        except Exception:
            pass
    if any(p.match(raw) for p in SMALLTALK_PATTERNS_ZH):
        return True
    if any(p.match(raw) for p in SMALLTALK_PATTERNS_EN):
        return True
    return False


def smalltalk_reply_text(text: str, lang: str) -> str:
    if str(lang).lower() == "en":
        return "Hi there. I'm here to help. What would you like me to prioritize first?"
    return "你好，我在。你现在最希望我先帮你处理哪一件事？"


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
    return out


def normalize_reply_text(raw_reply: str, next_question: str) -> str:
    raw = str(raw_reply or "").strip()
    raw = re.sub(r"```[\s\S]*?```", "", raw).strip()

    if raw and not contains_forbidden_reply(raw):
        return raw

    conclusion = sanitize_inline_text(raw, max_chars=120)
    if (not conclusion) or contains_forbidden_reply(conclusion):
        conclusion = "我已理解你的诉求，并会按项目经理方式推进。"
    plan = "我会先确认当前优先级并补齐默认项，再给你可执行方案并持续推进。"

    reply = f"{conclusion}\n\n{plan}\n\n{next_question}"
    if contains_forbidden_reply(reply):
        reply = "我已接手你的需求。你可以先告诉我这轮最想达成的目标，我马上推进。"
    return reply


def fallback_reply_doc(result: dict[str, Any]) -> dict[str, Any]:
    reason = sanitize_inline_text(str(result.get("reason", "")), max_chars=180)
    return {
        "reply_text": (
            "我已经接手你的需求，并会按项目经理方式继续推进。"
            "我会先补齐默认项并给你可执行路径，只在关键分歧点向你确认问题。"
            "你先告诉我这轮最想达成的目标，我就继续推进。"
        ),
        "next_question": "你现在最希望我先解决的一个具体问题是什么？",
        "actions": [{"type": "request_file", "hint": "如有失败包或截图，请直接上传"}],
        "debug_notes": reason,
    }


def build_final_reply_doc(
    *,
    run_dir: Path,
    provider: str,
    provider_result: dict[str, Any],
    provider_doc: dict[str, Any] | None,
) -> dict[str, Any]:
    raw_doc = provider_doc if isinstance(provider_doc, dict) else fallback_reply_doc(provider_result)
    raw_reply_text = str(raw_doc.get("reply_text", ""))
    raw_next_question = str(raw_doc.get("next_question", ""))
    lang = detect_lang_hint(raw_reply_text, raw_next_question, str(raw_doc.get("debug_notes", "")))
    provider_reason_text = str(provider_result.get("reason", "")).strip().lower()
    smalltalk_fast_path = str(provider or "").strip().lower() == "local_smalltalk" or "smalltalk_fast_path" in provider_reason_text

    pipeline_state: dict[str, Any] | None = None
    rendered_used = False
    rendered_visible_state = ""
    reply_text = ""
    next_question = ""
    if render_frontend_output is not None and not smalltalk_fast_path:
        try:
            history = load_inbox_history(run_dir, limit=12)
            user_msgs = [str(item.get("text", "")).strip() for item in history if str(item.get("text", "")).strip()]
            status_text = str(provider_result.get("status", "")).strip().lower()
            reason_text = str(provider_result.get("reason", "")).strip().lower()
            is_executed = status_text == "executed"
            is_deferred = status_text in {"outbox_created", "outbox_exists", "pending", "deferred"}
            is_hard_failure = status_text in {"exec_failed", "failed", "error"} or any(
                token in reason_text for token in ("traceback", "stack trace", "command failed", "exception")
            )
            if is_executed:
                stage = "support_provider_executed"
            elif is_deferred:
                stage = "support_provider_deferred"
            else:
                stage = "support_provider_failed"
            backend_state = {
                "stage": stage,
                "run_status": "",
                "reason": str(provider_result.get("reason", "")).strip(),
                "missing_fields": raw_doc.get("missing_fields", []),
                "blocked_needs_input": bool(is_hard_failure),
                "needs_input": bool(raw_next_question.strip()) or bool(is_hard_failure),
                "has_actionable_goal": bool(user_msgs),
                "first_pass_understood": bool(user_msgs),
            }
            rendered = render_frontend_output(
                raw_backend_state=backend_state,
                task_summary=(user_msgs[-1] if user_msgs else raw_reply_text),
                raw_reply_text=raw_reply_text,
                raw_next_question=raw_next_question,
                notes={
                    "lang": lang,
                    "max_questions": 2,
                    "recent_user_messages": user_msgs,
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
    elif smalltalk_fast_path:
        next_question = ""
        reply_text = normalize_reply_text(raw_reply_text, "")

    if smalltalk_fast_path:
        next_question = ""
    elif rendered_used:
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

    actions = normalize_actions(raw_doc.get("actions"))

    debug_notes = sanitize_inline_text(str(raw_doc.get("debug_notes", "")), max_chars=400)
    provider_status = str(provider_result.get("status", "")).strip()
    provider_reason = sanitize_inline_text(str(provider_result.get("reason", "")), max_chars=220)
    debug_combined = f"provider={provider}; status={provider_status}; reason={provider_reason}"
    if debug_notes:
        debug_combined += f"; notes={debug_notes}"
    if isinstance(pipeline_state, dict):
        selected = sanitize_inline_text(str(pipeline_state.get("selected_requirement_source", "")), max_chars=160)
        visible = sanitize_inline_text(str(pipeline_state.get("visible_state", "")), max_chars=60)
        if selected:
            debug_combined += f"; selected_requirement={selected}"
        if visible:
            debug_combined += f"; visible_state={visible}"

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

    # Smalltalk fast-path: do not route through provider failures for greeting-only turns.
    if is_smalltalk_only_message(user_text):
        lang = detect_lang_hint(user_text)
        final_doc = build_final_reply_doc(
            run_dir=run_dir,
            provider="local_smalltalk",
            provider_result={"status": "executed", "reason": "smalltalk_fast_path"},
            provider_doc={
                "reply_text": smalltalk_reply_text(user_text, lang),
                "next_question": "",
                "actions": [],
                "debug_notes": "smalltalk_fast_path",
            },
        )
        write_json(run_dir / SUPPORT_REPLY_REL_PATH, final_doc)
        append_event(run_dir, "SUPPORT_REPLY_WRITTEN", SUPPORT_REPLY_REL_PATH.as_posix(), provider="local_smalltalk")
        return final_doc, run_dir

    prompt_text = build_support_prompt(run_dir, chat_id, user_text)
    config, cfg_msg = load_dispatch_config(run_dir)
    append_log(run_dir / "logs" / "support_bot.dispatch.log", f"[{now_iso()}] load_dispatch_config: {cfg_msg}\n")

    provider = resolve_support_provider(config, override=provider_override)
    request = make_support_request(chat_id, user_text, prompt_text)

    append_event(run_dir, "SUPPORT_PROVIDER_SELECTED", "", provider=provider)
    result = execute_provider(provider=provider, run_dir=run_dir, request=request, config=config)
    log_provider_result(run_dir, provider, result, "primary")

    if str(result.get("status", "")) != "executed" and provider != "manual_outbox":
        fallback = manual_outbox.execute(
            repo_root=ROOT,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets={},
        )
        log_provider_result(run_dir, "manual_outbox", fallback, "fallback")
        append_event(run_dir, "SUPPORT_PROVIDER_FALLBACK", "", provider="manual_outbox")
        if str(fallback.get("status", "")) in {"outbox_created", "outbox_exists"}:
            result = {
                "status": str(fallback.get("status", "")),
                "reason": str(fallback.get("reason", "provider fallback to manual_outbox")),
                "path": str(fallback.get("path", "")),
            }

    provider_doc = read_json_doc(run_dir / SUPPORT_REPLY_PROVIDER_REL_PATH)
    final_doc = build_final_reply_doc(
        run_dir=run_dir,
        provider=provider,
        provider_result=result,
        provider_doc=provider_doc,
    )
    write_json(run_dir / SUPPORT_REPLY_REL_PATH, final_doc)
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


def emit_public_message(tg: TelegramClient, chat_id: int, text: str) -> None:
    # Single public-output gate for this support bot script.
    tg.send_message(chat_id, str(text or ""))


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

                doc, _ = process_message(
                    chat_id=str(chat_id),
                    user_text=user_text,
                    source="telegram",
                    provider_override=provider_override,
                )
                emit_public_message(tg, chat_id, str(doc.get("reply_text", "")).strip())
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
        provider_override="manual_outbox",
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
    ap.add_argument("--selftest", action="store_true", help="Run offline selftest using manual_outbox fallback")
    ap.add_argument("--provider", default="", help="Optional provider override for support_lead")

    sub = ap.add_subparsers(dest="mode")
    p_tg = sub.add_parser("telegram", help="Run Telegram long-poll loop")
    p_tg.add_argument("--token", required=True, help="Telegram bot token")
    p_tg.add_argument("--poll-seconds", type=int, default=2, help="Telegram long-poll timeout seconds")
    p_tg.add_argument("--allowlist", default="", help="Optional chat id allowlist: id1,id2")

    args = ap.parse_args()

    override = str(args.provider or "").strip()
    if args.selftest:
        return run_selftest()
    if bool(args.stdin):
        return run_stdin_mode(chat_id=str(args.chat_id), provider_override=override)
    if args.mode == "telegram":
        return run_telegram_mode(
            token=str(args.token),
            poll_seconds=int(args.poll_seconds),
            allowlist_raw=str(args.allowlist),
            provider_override=override,
        )

    ap.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
