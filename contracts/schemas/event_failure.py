from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.enums import EventType


@dataclass(frozen=True)
class FailureEvent:
    event_id: str
    job_id: str
    error_code: str
    message: str
    details: dict[str, Any]

    @property
    def event_type(self) -> EventType:
        return EventType.FAILURE

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "job_id": self.job_id,
            "error_code": self.error_code,
            "message": self.message,
            "details": dict(self.details),
        }
