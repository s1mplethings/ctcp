from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_text(text: str, max_chars: int = 6000) -> str:
    raw = str(text or "")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\s+\n", "\n", raw)
    raw = re.sub(r"\n{3,}", "\n\n", raw).strip()
    if len(raw) > max_chars:
        return raw[: max_chars - 1] + "..."
    return raw


def _guess_kind(text: str) -> str:
    low = str(text or "").strip().lower()
    if not low:
        return "empty"
    if low in {"status", "/status", "progress", "进度", "查看进度"}:
        return "status"
    if low in {"advance", "continue", "继续"}:
        return "advance"
    if low.startswith("/"):
        return "command"
    return "conversation"


@dataclass(frozen=True)
class InboundAttachment:
    source_path: str
    filename: str
    size_bytes: int


@dataclass(frozen=True)
class InboundMessage:
    user_id: str
    session_id: str
    project_key: str
    text: str
    message_kind: str
    attachments: tuple[InboundAttachment, ...]
    received_at: str


def normalize_attachment(path_text: str) -> InboundAttachment:
    src = Path(str(path_text or "")).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise FileNotFoundError(f"attachment not found: {src}")
    return InboundAttachment(
        source_path=str(src),
        filename=src.name,
        size_bytes=int(src.stat().st_size),
    )


def normalize_inbound_message(payload: dict[str, Any]) -> InboundMessage:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    user_id = str(payload.get("user_id", "")).strip() or "user"
    session_id = str(payload.get("session_id", "")).strip() or "session"
    project_key = str(payload.get("project_key", "")).strip()
    text = normalize_text(str(payload.get("text", "")))

    att_rows = payload.get("attachments", [])
    if isinstance(att_rows, str):
        att_rows = [att_rows]
    if not isinstance(att_rows, list):
        att_rows = []

    attachments: list[InboundAttachment] = []
    for item in att_rows:
        try:
            if isinstance(item, dict):
                attachments.append(normalize_attachment(str(item.get("path", ""))))
            else:
                attachments.append(normalize_attachment(str(item)))
        except Exception:
            continue

    return InboundMessage(
        user_id=user_id,
        session_id=session_id,
        project_key=project_key,
        text=text,
        message_kind=_guess_kind(text),
        attachments=tuple(attachments),
        received_at=_now_utc_iso(),
    )


def to_upload_jobs(message: InboundMessage) -> list[dict[str, str]]:
    jobs: list[dict[str, str]] = []
    for att in message.attachments:
        ext = Path(att.filename).suffix.lower()
        if ext and re.match(r"^\.[a-z0-9]+$", ext):
            safe_name = att.filename
        else:
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", att.filename) or "upload.bin"
        jobs.append(
            {
                "source_path": att.source_path,
                "dest_rel": f"artifacts/frontend_uploads/{safe_name}",
            }
        )
    return jobs
