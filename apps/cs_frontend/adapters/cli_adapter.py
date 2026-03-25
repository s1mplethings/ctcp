from __future__ import annotations

from apps.cs_frontend.bootstrap import bootstrap_frontend
from apps.cs_frontend.domain.presentable_event import PresentableEvent


class CliAdapter:
    def __init__(self) -> None:
        self.handler = bootstrap_frontend()

    def handle(self, session_id: str, text: str) -> PresentableEvent:
        return self.handler.handle_user_message(session_id=session_id, text=text, source="cli")
