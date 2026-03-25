from __future__ import annotations

import uuid


def _new_id(prefix: str) -> str:
    safe = str(prefix or "id").strip().lower() or "id"
    return f"{safe}-{uuid.uuid4().hex[:12]}"


def new_request_id() -> str:
    return _new_id("req")


def new_job_id() -> str:
    return _new_id("job")


def new_event_id() -> str:
    return _new_id("evt")
