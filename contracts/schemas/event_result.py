from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.enums import EventType


@dataclass(frozen=True)
class ResultEvent:
    event_id: str
    job_id: str
    summary: str
    artifacts: dict[str, Any]

    @property
    def event_type(self) -> EventType:
        return EventType.RESULT

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "job_id": self.job_id,
            "summary": self.summary,
            "artifacts": dict(self.artifacts),
        }
