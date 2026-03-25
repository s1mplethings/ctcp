from __future__ import annotations

from apps.cs_frontend.domain.chat_session import ChatSession
from apps.cs_frontend.storage.session_store import SessionStore


class SessionManager:
    def __init__(self, session_store: SessionStore) -> None:
        self.session_store = session_store

    def get_or_create(self, session_id: str) -> ChatSession:
        return self.session_store.get_or_create(session_id)

    def remember_turn(self, session: ChatSession, text: str) -> None:
        line = str(text or "").strip()
        if not line:
            return
        session.history_summary.append(line)
        if len(session.history_summary) > 8:
            session.history_summary = session.history_summary[-8:]
        self.session_store.save(session)
