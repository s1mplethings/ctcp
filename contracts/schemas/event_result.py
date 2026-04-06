from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contracts.enums import EventType


@dataclass(frozen=True)
class ResultEvent:
    event_id: str
    job_id: str
    summary: str
    artifacts: dict[str, Any] = field(default_factory=dict)
    delivery_evidence: dict[str, Any] = field(default_factory=dict)

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
            "delivery_evidence": dict(self.delivery_evidence),
        }
