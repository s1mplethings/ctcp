#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_paths import get_repo_slug, get_runs_root

def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None

def _runtime_root() -> Path:
    module = _support_bot_host_module()
    if module is not None and hasattr(module, "ROOT"):
        try:
            return Path(getattr(module, "ROOT"))
        except Exception:
            pass
    return ROOT

def _runtime_runs_root() -> Path:
    module = _support_bot_host_module()
    if module is not None and hasattr(module, "get_runs_root"):
        candidate = getattr(module, "get_runs_root")
        if callable(candidate):
            try:
                return Path(candidate())
            except Exception:
                pass
    return Path(get_runs_root())

def _runtime_repo_slug(root: Path) -> str:
    module = _support_bot_host_module()
    if module is not None and hasattr(module, "get_repo_slug"):
        candidate = getattr(module, "get_repo_slug")
        if callable(candidate):
            try:
                return str(candidate(root))
            except Exception:
                pass
    return get_repo_slug(root)

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

def parse_iso_ts(text: str) -> dt.datetime | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    try:
        return dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None

def seconds_since(text: str) -> float | None:
    stamp = parse_iso_ts(text)
    if stamp is None:
        return None
    now = dt.datetime.now(dt.timezone.utc)
    return max(0.0, (now - stamp.astimezone(dt.timezone.utc)).total_seconds())

def utf8_clean(text: str) -> str:
    return str(text or "").encode("utf-8", errors="replace").decode("utf-8", errors="replace")

def _replacement_char_count(text: str) -> int:
    return str(text or "").count("\ufffd")

def clean_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return utf8_clean(value)
    if isinstance(value, list):
        return [clean_json_value(item) for item in value]
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for key, item in value.items():
            out[str(key)] = clean_json_value(item)
        return out
    return value

def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(utf8_clean(text), encoding="utf-8")

def write_json(path: Path, doc: dict[str, Any]) -> None:
    write_text(path, json.dumps(clean_json_value(doc), ensure_ascii=False, indent=2) + "\n")

def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_row = clean_json_value(row)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(safe_row, ensure_ascii=False) + "\n")

def append_log(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(utf8_clean(text))

def append_trace(run_dir: Path, text: str) -> None:
    append_log(run_dir / "TRACE.md", f"- {now_iso()} | support_bot: {text}\n")

def append_event(run_dir: Path, event: str, path: str = "", **extra: Any) -> None:
    row: dict[str, Any] = {
        "ts": now_iso(),
        "role": "support_bot",
        "event": event,
        "path": path,
    }
    for key, value in extra.items():
        row[key] = value
    append_jsonl(run_dir / "events.jsonl", row)
    if path:
        append_trace(run_dir, f"{event} ({path})")
    else:
        append_trace(run_dir, event)

def ensure_external_run_dir(run_dir: Path) -> None:
    try:
        run_dir.resolve().relative_to(_runtime_root().resolve())
    except ValueError:
        return
    raise SystemExit(f"[ctcp_support_bot] run_dir must be outside repo root: {run_dir}")

def safe_session_id(chat_id: str | int) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(chat_id).strip())
    value = value.strip("-.")
    return value or "session"

def session_run_dir(chat_id: str | int) -> Path:
    root = _runtime_root()
    run_dir = (_runtime_runs_root() / _runtime_repo_slug(root) / "support_sessions" / safe_session_id(chat_id)).resolve()
    ensure_external_run_dir(run_dir)
    return run_dir

def _telegram_lock_path(token: str) -> Path:
    token_hash = hashlib.sha1(str(token or "").encode("utf-8", errors="ignore")).hexdigest()[:16]
    root = _runtime_root()
    return (_runtime_runs_root() / _runtime_repo_slug(root) / "support_bot_locks" / f"telegram_poll_{token_hash}.lock").resolve()

def acquire_telegram_poll_lock(token: str) -> tuple[Path, Any]:
    lock_path = _telegram_lock_path(token)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("a+", encoding="utf-8")
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt  # type: ignore

            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl  # type: ignore

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
        owner = ""
        try:
            fh.seek(0)
            owner = fh.read().strip()
        except Exception:
            owner = ""
        try:
            fh.close()
        except Exception:
            pass
        hint = f" (owner={owner})" if owner else ""
        raise RuntimeError(f"telegram poll lock busy: {lock_path}{hint}")

    try:
        fh.seek(0)
        fh.truncate(0)
        fh.write(f"pid={os.getpid()} ts={now_iso()}\n")
        fh.flush()
    except Exception:
        pass
    return lock_path, fh

def release_telegram_poll_lock(lock_path: Path, fh: Any) -> None:
    try:
        fh.seek(0)
        if os.name == "nt":
            import msvcrt  # type: ignore

            msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl  # type: ignore

            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass
    try:
        fh.close()
    except Exception:
        pass
    try:
        lock_path.unlink(missing_ok=True)
    except Exception:
        pass

def ensure_layout(run_dir: Path) -> None:
    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (run_dir / "logs").mkdir(parents=True, exist_ok=True)
    (run_dir / "outbox").mkdir(parents=True, exist_ok=True)

__all__ = [
    "now_iso",
    "parse_iso_ts",
    "seconds_since",
    "utf8_clean",
    "_replacement_char_count",
    "clean_json_value",
    "write_text",
    "write_json",
    "append_jsonl",
    "append_log",
    "append_trace",
    "append_event",
    "ensure_external_run_dir",
    "safe_session_id",
    "session_run_dir",
    "acquire_telegram_poll_lock",
    "release_telegram_poll_lock",
    "ensure_layout",
]
