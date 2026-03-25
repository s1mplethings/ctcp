from __future__ import annotations

from frontend.conversation_mode_router import route_conversation_mode


class IntentRouter:
    def route(self, *, latest_user_text: str, history: list[str], active_state: dict[str, object]) -> str:
        return str(route_conversation_mode(history, latest_user_text, active_state))
