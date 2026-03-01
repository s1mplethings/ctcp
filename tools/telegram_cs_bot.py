#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXTERNALS = ROOT / "scripts" / "externals"
if str(EXTERNALS) not in sys.path:
    sys.path.insert(0, str(EXTERNALS))
try:
    from openai_responses_client import call_openai_responses
except Exception:
    call_openai_responses = None  # type: ignore[assignment]

DEFAULT_LANG = "zh"
MAX_MESSAGE_CHARS = 3800
MAX_OUTBOX_PUSH_PER_TICK = 3
MAX_AGENT_DISPATCH_PER_TICK = 1
TRACE_COOLDOWN_SECONDS = 10.0


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


def detect_intent(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    low = raw.lower()
    if "英文" in raw or re.search(r"\benglish\b|\ben\b", low):
        return ("lang", "en")
    if "中文" in raw or re.search(r"\bchinese\b|\bzh\b", low):
        return ("lang", "zh")
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
        or "新任务" in raw
        or "new run" in low
        or "new project" in low
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


def smalltalk_reply(text: str, lang: str) -> str:
    raw = str(text or "").strip()
    low = raw.lower()
    if not raw:
        return ""
    greetings = {"你好", "嗨", "哈喽", "在吗", "早", "早安", "午安", "晚上好", "hello", "hi", "hey"}
    if raw in greetings or low in greetings:
        return "你好，我在。你可以直接告诉我想做什么程序，我会整理需求并推进。"
    if any(x in raw for x in ("谢谢", "感谢")) or "thank" in low or "thx" in low:
        return "不客气。你继续说需求，我会按客服模式整理并派发。"
    if any(x in raw for x in ("你是谁", "你能做什么", "怎么用")) or "what can you do" in low:
        if str(lang).lower() == "en":
            return "I can chat naturally, track your requirements into run_dir, push outbox/questions, and coordinate agent requests/results."
        return "我可以自然对话、把需求写入 run_dir、主动推送 outbox/question，并协调 agent 的 request/result。"
    return ""


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
        if s.startswith("```"):
            continue
        lines.append(s)
    text = " ".join(lines) if lines else short_tail(raw or "", max_lines=2, max_chars=max_chars)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        return text[: max_chars - 1] + "…"
    return text


def _humanize_trace_event_line(line: str, lang: str) -> str:
    s = str(line or "").strip()
    if not s.startswith("- "):
        return ""
    body = s[2:].strip()
    m = re.search(r"\|\s*([^:]+):\s*([A-Za-z0-9_]+)\s*\(([^)]+)\)", body)
    if m:
        role = _role_label(m.group(1).strip(), lang)
        evt = m.group(2).strip().upper()
        path = m.group(3).strip()
        name = Path(path).name or path
        if str(lang).lower() == "en":
            if evt in {"LOCAL_EXEC_COMPLETED", "GIT_IDENTITY_CAPTURED", "PLAN_TEMPLATE_WRITTEN"}:
                return f"- {role}: completed `{name}`"
            if evt in {"LOCAL_EXEC_FAILED", "PATCH_REJECTED"}:
                return f"- {role}: failed at `{name}`"
            if evt in {"VERIFY_PASSED", "RUN_PASS"}:
                return "- verification passed, workflow completed"
            if evt in {"VERIFY_STARTED"}:
                return "- verification started"
            if evt in {"BUNDLE_CREATED"}:
                return "- failure bundle generated"
            if evt in {"APPLY_BLOCKED_DIRTY"}:
                return "- apply blocked because repo is dirty"
            return f"- {role}: {evt.lower()} (`{name}`)"
        if evt in {"LOCAL_EXEC_COMPLETED", "GIT_IDENTITY_CAPTURED", "PLAN_TEMPLATE_WRITTEN"}:
            return f"- {role}已完成：`{name}`"
        if evt in {"LOCAL_EXEC_FAILED", "PATCH_REJECTED"}:
            return f"- {role}执行失败：`{name}`"
        if evt in {"VERIFY_PASSED", "RUN_PASS"}:
            return "- 验收通过，流程已完成"
        if evt in {"VERIFY_STARTED"}:
            return "- 已开始验收检查"
        if evt in {"BUNDLE_CREATED"}:
            return "- 已生成失败证据包"
        if evt in {"APPLY_BLOCKED_DIRTY"}:
            return "- 应用补丁被拦截：仓库当前有未提交改动"
        return f"- {role}：{evt.lower()}（`{name}`）"
    if str(lang).lower() == "en":
        if "run already PASS" in body:
            return "- run already passed"
        if "blocked:" in body:
            return "- currently blocked; waiting for required artifact"
    else:
        if "run already PASS" in body:
            return "- 当前流程已是通过状态"
        if "blocked:" in body:
            return "- 当前处于等待状态，需要补齐产物后继续"
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
            return "Progress updated. Send 'status' for current state."
        return "进度已更新。发送“进度”可查看当前状态。"
    picked = dedup[-4:]
    if str(lang).lower() == "en":
        return "Progress update:\n" + "\n".join(picked)
    return "进展更新：\n" + "\n".join(picked)


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
            auto_advance=parse_bool(os.environ.get("CTCP_TG_AUTO_ADVANCE", "0"), False),
            api_enabled=parse_bool(os.environ.get("CTCP_TG_API_ENABLED", "1"), True),
            api_model=(
                os.environ.get("CTCP_TG_API_MODEL", "")
                or os.environ.get("SDDAI_OPENAI_AGENT_MODEL", "")
                or os.environ.get("SDDAI_OPENAI_MODEL", "")
                or "gpt-4.1-mini"
            ).strip(),
            api_timeout_sec=parse_int(os.environ.get("CTCP_TG_API_TIMEOUT_SEC", "60"), 60),
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

    def _json(self, method: str, payload: dict[str, Any]) -> Any:
        req = urllib.request.Request(self.base + method, data=json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as resp:
            doc = json.loads(resp.read().decode("utf-8", errors="replace"))
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
        req = urllib.request.Request(self.base + method, data=b"".join(chunks), headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            doc = json.loads(resp.read().decode("utf-8", errors="replace"))
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

    def _run_orchestrate(self, args: list[str]) -> tuple[int, str, str]:
        p = subprocess.run([sys.executable, str(self.cfg.repo_root / "scripts" / "ctcp_orchestrate.py"), *args], cwd=str(self.cfg.repo_root), capture_output=True, text=True, encoding="utf-8", errors="replace")
        return p.returncode, p.stdout, p.stderr

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

    def _run_status(self, run_dir: Path) -> str:
        p = run_dir / "RUN.json"
        if not p.exists():
            return ""
        try:
            doc = json.loads(p.read_text(encoding="utf-8", errors="replace"))
            return str(doc.get("status", "")).strip().lower()
        except Exception:
            return ""

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
            self.tg.send(chat_id=chat_id, text=f"new-run rc={rc}\n{short_tail((out or '') + '\n' + (err or ''), max_lines=16, max_chars=1800)}")
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
        self._append_note(resolved, f"telegram/goal {goal}")
        if str(lang).lower() == "en":
            self.tg.send(chat_id=chat_id, text="Task created and bound. Keep chatting to add requirements, or send 'continue' to push progress.")
        else:
            self.tg.send(chat_id=chat_id, text="已创建并绑定新任务。你可以继续聊天补充需求，或发送“继续”推进流程。")

    def _collect_prompts(self, run_dir: Path) -> list[tuple[Path, PromptItem]]:
        outbox = run_dir / "outbox"
        if not outbox.exists():
            return []
        rows: list[tuple[Path, PromptItem]] = []
        for p in sorted(outbox.glob("*.md")):
            if not p.is_file():
                continue
            item = parse_outbox_prompt(run_dir, p)
            if item and prompt_pending(run_dir, item, p):
                rows.append((p, item))
        return rows

    def _render_prompt(self, run_dir: Path, item: PromptItem, lang: str) -> str:
        brief = _brief_text(item.prompt_text, max_chars=180) or Path(item.target_path).name
        prompt_line = parse_key_line(item.raw_text, "Prompt")
        if item.prompt_type == "question":
            ask = prompt_line or brief or "Please choose an option."
            if str(lang).lower() == "en":
                lines = ["A decision is needed before we can continue.", ask]
                if item.options:
                    lines.append("Options: " + " / ".join(item.options))
                lines.append("Reply to this message (text/file) if needed.")
                return "\n".join(lines)
            lines = ["继续推进前需要你做一个选择。", ask]
            if item.options:
                lines.append("可选项：" + " / ".join(item.options))
            lines.append("如需补充，可直接回复这条消息（文本/文件都可以）。")
            return "\n".join(lines)
        if str(lang).lower() == "en":
            return (
                "I need one piece of input from you to continue.\n"
                f"Topic: {brief}\n"
                "Reply to this message with text or a file; I will write it to the correct place."
            )
        return (
            "我需要你补充一条信息才能继续推进。\n"
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
        trace = run_dir / "TRACE.md"
        t = ""
        if trace.exists():
            t = trace.read_text(encoding="utf-8", errors="replace")
        evt = last_trace_event(t)
        evt_human = _humanize_trace_event_line("- " + evt, lang) if evt else ""
        if str(lang).lower() == "en":
            return (
                f"Current todo: decisions {q}, agent tasks {a}, info requests {n}.\n"
                f"Latest progress: {(evt_human or evt or 'No new progress yet.')}"
            )
        return (
            f"当前待办：提问 {q}，agent 任务 {a}，信息补充 {n}。\n"
            f"最新进展：{(evt_human or evt or '暂无新的进展。')}"
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
                return "No decisions needed from you right now. You can send 'continue' to keep progressing."
            return "目前没有需要你拍板的事项。你可以发送“继续”让我自动推进。"
        lines: list[str] = []
        if str(lang).lower() == "en":
            lines.append(f"There are {len(user_items)} item(s) needing your decision/input:")
        else:
            lines.append(f"当前有 {len(user_items)} 项需要你决定/补充：")
        for idx, item in enumerate(user_items[:3], start=1):
            brief = short_tail(item.prompt_text, max_lines=2, max_chars=120).replace("\n", " / ")
            lines.append(f"{idx}. [{item.prompt_type or 'prompt'}] {item.rel_prompt_path}")
            if brief:
                lines.append(f"   - {brief}")
            lines.append(f"   - Target: {item.target_path}")
        if len(user_items) > 3:
            if str(lang).lower() == "en":
                lines.append(f"...and {len(user_items)-3} more. Send /outbox to review all.")
            else:
                lines.append(f"……还有 {len(user_items)-3} 项。发送 /outbox 可查看全部。")
        return "\n".join(lines)

    def _send_status(self, chat_id: int, run_dir: Path) -> None:
        lang = str(self.db.get_session(chat_id).get("lang", DEFAULT_LANG) or DEFAULT_LANG)
        self.tg.send(chat_id=chat_id, text=self._status_text(run_dir, lang))

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
        rel = str(mapping.get("target_path", "")).strip()
        try:
            target = ensure_within_run_dir(run_dir, rel)
        except Exception as exc:
            self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'write_fail')}: {exc}")
            return
        try:
            if file_id:
                atomic_write_bytes(target, self.tg.download(file_id))
            else:
                payload = str(text or "")
                if not payload.endswith("\n"):
                    payload += "\n"
                atomic_write_text(target, payload)
        except Exception as exc:
            self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'write_fail')}: {exc}")
            return
        self.db.del_map(chat_id, int(mapping["prompt_msg_id"]))
        p = str(mapping.get("prompt_path", "")).strip()
        if p:
            self.db.del_pending(str(run_dir), p)
        self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'write_ok')}: {rel}")

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
            if str(lang).lower() == "en":
                msg = (
                    f"I moved forward {max(1, steps)} step(s), but we are waiting now.\n"
                    f"Reason: {reason or 'waiting for required artifact'}.\n"
                    f"Responsible stage: {owner or 'N/A'}."
                )
            else:
                msg = (
                    f"我已推进 {max(1, steps)} 步，但现在在等待中。\n"
                    f"原因：{reason or '等待必要产物'}。\n"
                    f"当前负责环节：{owner or '未给出'}。"
                )
            self.tg.send(chat_id=chat_id, text=msg)
            return
        if rc == 0:
            if str(lang).lower() == "en":
                msg = f"Advance completed. Next: {next_step or 'unknown'}."
            else:
                msg = f"推进完成。下一步：{next_step or '未给出'}。"
            self.tg.send(chat_id=chat_id, text=msg)
            return
        detail = short_tail(merged, max_lines=16, max_chars=1400)
        if str(lang).lower() == "en":
            self.tg.send(chat_id=chat_id, text=f"Advance failed (rc={rc}).\n{detail}")
        else:
            self.tg.send(chat_id=chat_id, text=f"推进失败（rc={rc}）。\n{detail}")

    def _allow_auto_advance(self, run_dir: Path) -> bool:
        prompts = self._collect_prompts(run_dir)
        return (not prompts) or (not any(i.prompt_type == "question" for _p, i in prompts))

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
                    self.tg.send(chat_id=chat_id, text=f"已派发给内部代理 `{agent}`，返回结果后我会第一时间通知你。")
                count += 1
            except Exception as exc:
                if str(lang).lower() == "en":
                    self.tg.send(chat_id=chat_id, text=f"Agent dispatch failed, switched to manual reply mode: {exc}")
                else:
                    self.tg.send(chat_id=chat_id, text=f"派发给代理失败，已切换为你人工回复模式：{exc}")
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
                self.tg.send(chat_id=chat_id, text="已收到内部代理结果，并自动写入对应位置。")
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
        self.tg.send(chat_id=chat_id, text=_humanize_trace_delta(delta, lang))
        self.db.update_cursors(chat_id, trace_offset=size, cooldown_ts=now_ts)

    def _scan_push(self, chat_id: int, run_dir: Path) -> dict[str, int]:
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
        return {"questions": 0, "agent_dispatch": 0, "normal": normal, "agent_results": done}

    def run_tick(self) -> None:
        for s in self.db.list_bound_sessions():
            chat_id = int(s["chat_id"])
            if not self.allowed(chat_id):
                continue
            run_dir = Path(str(s.get("run_dir", "")).strip()).expanduser().resolve()
            if run_dir.exists():
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
            "You are CTCP Telegram customer-service router. Return JSON only.\n"
            "Keys: intent,reply,note,agent_summary,advance_steps.\n"
            "intent in: note,status,advance,outbox,bundle,report,decision,lang_zh,lang_en.\n"
            "Use concise reply. note should be concise requirement line. agent_summary <=180 chars.\n"
            f"lang={lang}\nrun_dir={run_dir}\npending: question={q}, agent_request={a}, prompt={n}\n"
            f"user_notes_tail:\n{notes_tail or '(none)'}\n\ntrace_tail:\n{trace_tail or '(none)'}\n\nuser_message:\n{user_text.strip()}\n"
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
            return ApiDecision(intent=intent, reply=str(doc.get("reply", "")).strip(), note=str(doc.get("note", "")).strip(), summary=str(doc.get("agent_summary", "")).strip(), steps=max(1, min(3, parse_int(str(doc.get("advance_steps", "1")), 1))))
        except Exception:
            return None

    def _handle_bound_api(self, chat_id: int, lang: str, run_dir: Path, text: str) -> bool:
        d = self._api_route(run_dir, lang, text)
        if d is None:
            return False
        note = d.note.strip() or text.strip()
        summary = d.summary.strip()
        if len(summary) > 180:
            summary = summary[:180]
        if d.intent == "lang_zh":
            self.db.set_lang(chat_id, "zh")
            self._append_note(run_dir, "telegram/lang zh (api)")
            self.tg.send(chat_id=chat_id, text=d.reply or "已切换中文。")
        elif d.intent == "lang_en":
            self.db.set_lang(chat_id, "en")
            self._append_note(run_dir, "telegram/lang en (api)")
            self.tg.send(chat_id=chat_id, text=d.reply or "Switched to English.")
        elif d.intent == "status":
            if d.reply:
                self.tg.send(chat_id=chat_id, text=d.reply)
            self._send_status(chat_id, run_dir)
        elif d.intent == "advance":
            self._append_note(run_dir, f"telegram/advance request(api): {text}")
            if d.reply:
                self.tg.send(chat_id=chat_id, text=d.reply)
            self._advance_once(chat_id, run_dir, d.steps)
            self._scan_push(chat_id, run_dir)
        elif d.intent == "outbox":
            if d.reply:
                self.tg.send(chat_id=chat_id, text=d.reply)
            stats = self._scan_push(chat_id, run_dir)
            if stats["questions"] + stats["agent_dispatch"] + stats["normal"] + stats["agent_results"] == 0:
                self.tg.send(chat_id=chat_id, text="No pending outbox items.")
        elif d.intent == "bundle":
            if d.reply:
                self.tg.send(chat_id=chat_id, text=d.reply)
            self._send_bundle(chat_id, run_dir, True)
        elif d.intent == "report":
            if d.reply:
                self.tg.send(chat_id=chat_id, text=d.reply)
            self._send_verify(chat_id, run_dir)
        elif d.intent == "decision":
            if d.reply:
                self.tg.send(chat_id=chat_id, text=d.reply)
            self.tg.send(chat_id=chat_id, text=self._decision_text(run_dir, lang))
        else:
            chat_reply = d.reply or smalltalk_reply(text, lang)
            if chat_reply:
                self.tg.send(chat_id=chat_id, text=chat_reply)
            else:
                p = self._append_note(run_dir, f"telegram/note {note}")
                self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'saved_note')}: {p.relative_to(run_dir).as_posix()}")
        if summary:
            self._append_summary(run_dir, text, summary, d.intent)
        return True

    def _handle_bound_fallback(self, chat_id: int, lang: str, run_dir: Path, text: str) -> None:
        intent, val = detect_intent(text)
        if intent == "lang":
            nxt = val if val in {"zh", "en"} else lang
            self.db.set_lang(chat_id, nxt)
            self._append_note(run_dir, f"telegram/lang {nxt}")
            self.tg.send(chat_id=chat_id, text=f"language={nxt}")
        elif intent == "status":
            self._send_status(chat_id, run_dir)
        elif intent == "advance":
            self._append_note(run_dir, f"telegram/advance request: {text}")
            self._advance_once(chat_id, run_dir, 1)
            self._scan_push(chat_id, run_dir)
        elif intent == "bundle":
            self._send_bundle(chat_id, run_dir, True)
        elif intent == "report":
            self._send_verify(chat_id, run_dir)
        elif intent == "decision":
            self.tg.send(chat_id=chat_id, text=self._decision_text(run_dir, lang))
        elif intent == "outbox":
            stats = self._scan_push(chat_id, run_dir)
            if stats["questions"] + stats["agent_dispatch"] + stats["normal"] + stats["agent_results"] == 0:
                self.tg.send(chat_id=chat_id, text="No pending outbox items.")
        else:
            chat_reply = smalltalk_reply(text, lang)
            if chat_reply:
                self.tg.send(chat_id=chat_id, text=chat_reply)
            else:
                p = self._append_note(run_dir, f"telegram/note {text}")
                self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'saved_note')}: {p.relative_to(run_dir).as_posix()}")

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
                self._append_note(run_dir, "telegram/failure_action retry")
                self._advance_once(chat_id, run_dir, 1)
                self._scan_push(chat_id, run_dir)
                self.tg.answer_cb(cb_id, text="retry triggered")
                return
            if action == "stop":
                self._append_note(run_dir, "telegram/failure_action stop")
                self.tg.send(chat_id=chat_id, text="Recorded stop request in USER_NOTES.")
                self.tg.answer_cb(cb_id, text="stop recorded")
                return
            if action == "relax":
                ap = run_dir / "artifacts" / "answers" / "RELAX_LIMITS.md"
                append_text(ap, f"- {now_iso()} | chat_id={chat_id} | relax_limits\n")
                self.tg.send(chat_id=chat_id, text="Recorded relax request at artifacts/answers/RELAX_LIMITS.md.")
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
        elif cmd == "/advance":
            n = parse_int(arg or "1", 1)
            self._advance_once(chat_id, run_dir, n)
            self._scan_push(chat_id, run_dir)
        elif cmd == "/outbox":
            stats = self._scan_push(chat_id, run_dir)
            if stats["questions"] + stats["agent_dispatch"] + stats["normal"] + stats["agent_results"] == 0:
                self.tg.send(chat_id=chat_id, text="No new pending outbox prompts.")
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
                p = self._append_note(run_dir, f"telegram/note {arg}")
                self.tg.send(chat_id=chat_id, text=f"{i18n(lang, 'saved_note')}: {p.relative_to(run_dir).as_posix()}")
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
                self._create_run(chat_id, lang, text)
            else:
                self.tg.send(chat_id=chat_id, text=i18n(lang, "need_run"))
            return
        run_dir = Path(run_raw).expanduser().resolve()
        if not run_dir.exists():
            self.db.clear_run(chat_id)
            self.tg.send(chat_id=chat_id, text="bound run_dir no longer exists; send a new goal.")
            return
        if msg.get("document"):
            self.tg.send(chat_id=chat_id, text="请回复某条 outbox 提示消息后再上传文件。")
            return
        if text:
            direct_intent, _ = detect_intent(text)
            run_status = self._run_status(run_dir)
            terminal_statuses = {"pass", "blocked", "failed", "error", "done", "stopped", "cancelled"}
            if direct_intent == "note":
                if looks_like_new_goal(text) and run_status in terminal_statuses:
                    self._create_run(chat_id, lang, text)
                    return
                if ("新建" in text or "重新开始" in text or "new run" in text.lower()) and len(text.strip()) >= 6:
                    self._create_run(chat_id, lang, text)
                    return
            if direct_intent == "decision":
                self.tg.send(chat_id=chat_id, text=self._decision_text(run_dir, lang))
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
            except Exception as exc:
                print(f"[telegram_cs_bot] getUpdates error: {exc}", file=sys.stderr)
                time.sleep(1.0)
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
