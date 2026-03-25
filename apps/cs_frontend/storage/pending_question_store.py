from __future__ import annotations


class PendingQuestionStore:
    def __init__(self) -> None:
        self._pending: dict[str, dict[str, str]] = {}

    def set(self, session_id: str, *, question_id: str, question_text: str) -> None:
        self._pending[str(session_id)] = {
            "question_id": str(question_id or "").strip(),
            "question_text": str(question_text or "").strip(),
        }

    def get(self, session_id: str) -> dict[str, str] | None:
        sid = str(session_id or "")
        if sid not in self._pending:
            return None
        return dict(self._pending[sid])

    def clear(self, session_id: str) -> None:
        self._pending.pop(str(session_id or ""), None)
