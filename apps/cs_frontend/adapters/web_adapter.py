from __future__ import annotations

from apps.cs_frontend.adapters.cli_adapter import CliAdapter


class WebAdapter:
    """Placeholder adapter; frontend still returns presentable reply text only."""

    def __init__(self) -> None:
        self._cli = CliAdapter()

    def handle_http_message(self, session_id: str, text: str) -> dict[str, object]:
        event = self._cli.handle(session_id=session_id, text=text)
        return {"reply_text": event.reply_text, "events": event.events}
