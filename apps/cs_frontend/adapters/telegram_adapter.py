from __future__ import annotations

from apps.cs_frontend.adapters.cli_adapter import CliAdapter


class TelegramAdapter:
    """Placeholder adapter to keep frontend boundary explicit."""

    def __init__(self) -> None:
        self._cli = CliAdapter()

    def handle_text(self, chat_id: str, text: str) -> str:
        event = self._cli.handle(session_id=str(chat_id), text=text)
        return event.reply_text
