from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class JobPhase(StrEnum):
    CREATED = "created"
    ANALYZE = "analyze"
    PLANNING = "planning"
    CONTEXT = "context"
    GENERATION = "generation"
    VERIFICATION = "verification"
    REPAIR = "repair"
    WAITING_ANSWER = "waiting_answer"
    DONE = "done"
    FAILED = "failed"


class EventType(StrEnum):
    STATUS = "event_status"
    QUESTION = "event_question"
    RESULT = "event_result"
    FAILURE = "event_failure"
