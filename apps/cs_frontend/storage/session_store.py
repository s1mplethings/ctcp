from __future__ import annotations

from apps.cs_frontend.domain.chat_session import ChatSession


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, ChatSession] = {}

    def get_or_create(self, session_id: str) -> ChatSession:
        sid = str(session_id or "").strip() or "default"
        if sid not in self._sessions:
            self._sessions[sid] = ChatSession(session_id=sid)
        return self._sessions[sid]

    def save(self, session: ChatSession) -> None:
        self._sessions[session.session_id] = session
