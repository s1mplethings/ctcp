from __future__ import annotations


class QuestionBus:
    def __init__(self) -> None:
        self._pending: dict[str, dict[str, str]] = {}

    def set_pending(self, job_id: str, question_id: str, text: str) -> None:
        self._pending[job_id] = {"question_id": question_id, "question_text": text}

    def get_pending(self, job_id: str) -> dict[str, str] | None:
        return dict(self._pending[job_id]) if job_id in self._pending else None

    def clear(self, job_id: str) -> None:
        self._pending.pop(job_id, None)
