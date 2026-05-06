#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from frontend.telegram_http_client import telegram_post_form, telegram_post_multipart


class TelegramClient:
    def __init__(self, token: str, timeout_sec: int) -> None:
        self.base = f"https://api.telegram.org/bot{token}"
        self.timeout_sec = max(1, int(timeout_sec))

    def _post(self, method: str, params: dict[str, Any]) -> Any:
        return telegram_post_form(self.base, method, params, timeout_sec=self.timeout_sec + 15)

    def _post_multipart(self, method: str, params: dict[str, Any], file_field: str, file_path: Path) -> Any:
        return telegram_post_multipart(self.base, method, params, file_field, file_path, timeout_sec=self.timeout_sec + 30)

    def get_updates(self, offset: int) -> list[dict[str, Any]]:
        result = self._post(
            "getUpdates",
            {"timeout": self.timeout_sec, "offset": offset, "allowed_updates": json.dumps(["message"])},
        )
        return result if isinstance(result, list) else []

    def clear_webhook(self, drop_pending_updates: bool = False) -> None:
        self._post("deleteWebhook", {"drop_pending_updates": "true" if drop_pending_updates else "false"})

    def send_message(self, chat_id: int, text: str) -> None:
        self._post("sendMessage", {"chat_id": chat_id, "text": text[:3800]})

    def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> None:
        self._send_file("sendDocument", chat_id, file_path, "document", caption=caption)

    def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> None:
        self._send_file("sendPhoto", chat_id, file_path, "photo", caption=caption)

    def send_video(self, chat_id: int, file_path: Path, caption: str = "") -> None:
        self._send_file("sendVideo", chat_id, file_path, "video", caption=caption)

    def _send_file(self, method: str, chat_id: int, file_path: Path, file_field: str, *, caption: str = "") -> None:
        params: dict[str, Any] = {"chat_id": chat_id}
        if caption:
            params["caption"] = caption[:900]
        self._post_multipart(method, params, file_field, file_path)


def emit_public_message(tg: TelegramClient, chat_id: int, text: str) -> None:
    tg.send_message(chat_id, str(text or ""))


__all__ = ["TelegramClient", "emit_public_message"]
