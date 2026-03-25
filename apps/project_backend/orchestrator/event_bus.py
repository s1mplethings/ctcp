from __future__ import annotations

from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._events: dict[str, list[dict[str, Any]]] = {}

    def publish(self, job_id: str, payload: dict[str, Any]) -> None:
        self._events.setdefault(job_id, []).append(dict(payload))

    def pop_all(self, job_id: str) -> list[dict[str, Any]]:
        events = self._events.get(job_id, [])
        self._events[job_id] = []
        return list(events)

    def peek_latest(self, job_id: str, event_type: str = "") -> dict[str, Any] | None:
        rows = self._events.get(job_id, [])
        if not rows:
            return None
        if not event_type:
            return dict(rows[-1])
        for row in reversed(rows):
            if str(row.get("event_type", "")) == event_type:
                return dict(row)
        return None
