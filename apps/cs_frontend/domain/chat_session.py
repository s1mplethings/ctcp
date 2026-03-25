from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ChatSession:
    session_id: str
    active_job_id: str = ""
    latest_mode: str = "SMALLTALK"
    history_summary: list[str] = field(default_factory=list)
