from __future__ import annotations

from dataclasses import dataclass

from contracts.enums import EventType


@dataclass(frozen=True)
class QuestionEvent:
    event_id: str
    job_id: str
    question_id: str
    question_text: str

    @property
    def event_type(self) -> EventType:
        return EventType.QUESTION

    def to_payload(self) -> dict[str, str]:
        return {
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "job_id": self.job_id,
            "question_id": self.question_id,
            "question_text": self.question_text,
        }
