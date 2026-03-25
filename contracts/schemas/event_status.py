from __future__ import annotations

from dataclasses import dataclass

from contracts.enums import EventType, JobPhase


@dataclass(frozen=True)
class StatusEvent:
    event_id: str
    job_id: str
    phase: JobPhase
    summary: str

    @property
    def event_type(self) -> EventType:
        return EventType.STATUS

    def to_payload(self) -> dict[str, str]:
        return {
            "event_type": self.event_type.value,
            "event_id": self.event_id,
            "job_id": self.job_id,
            "phase": self.phase.value,
            "summary": self.summary,
        }
