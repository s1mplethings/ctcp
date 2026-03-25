from __future__ import annotations

from contracts.schemas.event_failure import FailureEvent
from shared.ids import new_event_id


def failure_event(job_id: str, *, code: str, message: str, details: dict[str, object] | None = None) -> FailureEvent:
    return FailureEvent(
        event_id=new_event_id(),
        job_id=job_id,
        error_code=code,
        message=message,
        details=dict(details or {}),
    )
