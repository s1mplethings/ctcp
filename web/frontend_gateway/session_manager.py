from __future__ import annotations

import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _default_store_path() -> Path:
    env_path = str(os.environ.get("CTCP_FRONTEND_SESSION_DB", "")).strip()
    if env_path:
        return Path(env_path).expanduser().resolve()
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", "") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":  # type: ignore[name-defined]
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path.home() / ".local" / "share"
    return (root / "ctcp" / "frontend_gateway" / "sessions.json").resolve()


def _sanitize_id(value: str, fallback: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.:@-]+", "-", str(value or "").strip())
    text = text.strip("-.")
    return text or fallback


@dataclass
class SessionRecord:
    session_key: str
    user_id: str
    session_id: str
    project_key: str = ""
    bound_run_id: str = ""
    messages: list[dict[str, str]] = field(default_factory=list)
    attachments: list[dict[str, str]] = field(default_factory=list)
    last_presentation_state: str = ""
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_key": self.session_key,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "project_key": self.project_key,
            "bound_run_id": self.bound_run_id,
            "messages": list(self.messages),
            "attachments": list(self.attachments),
            "last_presentation_state": self.last_presentation_state,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @staticmethod
    def from_dict(doc: dict[str, Any]) -> "SessionRecord":
        return SessionRecord(
            session_key=str(doc.get("session_key", "")).strip(),
            user_id=str(doc.get("user_id", "")).strip(),
            session_id=str(doc.get("session_id", "")).strip(),
            project_key=str(doc.get("project_key", "")).strip(),
            bound_run_id=str(doc.get("bound_run_id", "")).strip(),
            messages=[x for x in doc.get("messages", []) if isinstance(x, dict)],
            attachments=[x for x in doc.get("attachments", []) if isinstance(x, dict)],
            last_presentation_state=str(doc.get("last_presentation_state", "")).strip(),
            created_at=str(doc.get("created_at", "")).strip(),
            updated_at=str(doc.get("updated_at", "")).strip(),
        )


class SessionManager:
    def __init__(self, store_path: str | Path | None = None, max_messages: int = 40) -> None:
        self.store_path = Path(store_path).expanduser().resolve() if store_path else _default_store_path()
        self.max_messages = max(5, int(max_messages))

    @staticmethod
    def make_session_key(user_id: str, session_id: str) -> str:
        uid = _sanitize_id(user_id, "user")
        sid = _sanitize_id(session_id, "session")
        return f"{uid}:{sid}"

    def _load_doc(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return {"schema_version": "ctcp-frontend-session-v1", "sessions": {}}
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            return {"schema_version": "ctcp-frontend-session-v1", "sessions": {}}
        if not isinstance(raw, dict):
            return {"schema_version": "ctcp-frontend-session-v1", "sessions": {}}
        sessions = raw.get("sessions", {})
        if not isinstance(sessions, dict):
            sessions = {}
        return {"schema_version": "ctcp-frontend-session-v1", "sessions": sessions}

    def _save_doc(self, doc: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def get_or_create(self, user_id: str, session_id: str, project_key: str = "") -> SessionRecord:
        key = self.make_session_key(user_id, session_id)
        doc = self._load_doc()
        sessions = doc["sessions"]
        existing = sessions.get(key)
        if isinstance(existing, dict):
            row = SessionRecord.from_dict(existing)
            if project_key and not row.project_key:
                row.project_key = str(project_key).strip()
                row.updated_at = _now_utc_iso()
                sessions[key] = row.to_dict()
                self._save_doc(doc)
            return row

        ts = _now_utc_iso()
        created = SessionRecord(
            session_key=key,
            user_id=_sanitize_id(user_id, "user"),
            session_id=_sanitize_id(session_id, "session"),
            project_key=str(project_key).strip(),
            created_at=ts,
            updated_at=ts,
        )
        sessions[key] = created.to_dict()
        self._save_doc(doc)
        return created

    def _save_record(self, record: SessionRecord) -> None:
        doc = self._load_doc()
        doc["sessions"][record.session_key] = record.to_dict()
        self._save_doc(doc)

    def bind_run(self, user_id: str, session_id: str, run_id: str) -> SessionRecord:
        row = self.get_or_create(user_id, session_id)
        row.bound_run_id = str(run_id).strip()
        row.updated_at = _now_utc_iso()
        self._save_record(row)
        return row

    def append_message(self, user_id: str, session_id: str, role: str, text: str) -> SessionRecord:
        row = self.get_or_create(user_id, session_id)
        payload = {
            "ts": _now_utc_iso(),
            "role": str(role or "").strip() or "user",
            "text": str(text or "").strip(),
        }
        row.messages.append(payload)
        row.messages = row.messages[-self.max_messages :]
        row.updated_at = _now_utc_iso()
        self._save_record(row)
        return row

    def append_attachment_ref(
        self,
        user_id: str,
        session_id: str,
        *,
        source_path: str,
        uploaded_rel: str,
    ) -> SessionRecord:
        row = self.get_or_create(user_id, session_id)
        row.attachments.append(
            {
                "ts": _now_utc_iso(),
                "source_path": str(source_path).strip(),
                "uploaded_rel": str(uploaded_rel).strip(),
            }
        )
        row.attachments = row.attachments[-self.max_messages :]
        row.updated_at = _now_utc_iso()
        self._save_record(row)
        return row

    def update_presentation_state(self, user_id: str, session_id: str, state: str) -> SessionRecord:
        row = self.get_or_create(user_id, session_id)
        row.last_presentation_state = str(state or "").strip().upper()
        row.updated_at = _now_utc_iso()
        self._save_record(row)
        return row

    def get_memory(self, user_id: str, session_id: str, limit: int = 12) -> list[dict[str, str]]:
        row = self.get_or_create(user_id, session_id)
        max_items = max(1, int(limit))
        return row.messages[-max_items:]
