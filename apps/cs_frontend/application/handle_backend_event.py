from __future__ import annotations

from apps.cs_frontend.dialogue.response_renderer import ResponseRenderer
from apps.cs_frontend.domain.presentable_event import PresentableEvent
from apps.cs_frontend.storage.pending_question_store import PendingQuestionStore


def handle_backend_event(
    *,
    renderer: ResponseRenderer,
    pending_store: PendingQuestionStore,
    session_id: str,
    events: list[dict[str, object]],
) -> PresentableEvent:
    for event in events:
        if str(event.get("event_type", "")) == "event_question":
            pending_store.set(
                session_id,
                question_id=str(event.get("question_id", "")),
                question_text=str(event.get("question_text", "")),
            )
    return renderer.from_backend_events(events)
