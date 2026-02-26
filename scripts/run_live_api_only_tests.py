#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCAL_NOTES_PATH = ROOT / ".agent_private" / "NOTES.md"


def _load_local_notes_defaults() -> dict[str, str]:
    path_text = str(os.environ.get("CTCP_LOCAL_NOTES_PATH", "")).strip()
    path = Path(path_text) if path_text else DEFAULT_LOCAL_NOTES_PATH
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    out: dict[str, str] = {}
    m_url = re.search(r"`(https?://[^`\s]+)`", text)
    if m_url:
        out["base_url"] = m_url.group(1).strip()
    m_key = re.search(r"`(sk-[^`\s]+)`", text)
    if m_key:
        out["api_key"] = m_key.group(1).strip()
    return out


def main() -> int:
    env = os.environ.copy()
    defaults = _load_local_notes_defaults()
    if not str(env.get("OPENAI_API_KEY", "")).strip():
        if str(env.get("CTCP_OPENAI_API_KEY", "")).strip():
            env["OPENAI_API_KEY"] = str(env.get("CTCP_OPENAI_API_KEY", "")).strip()
        elif defaults.get("api_key"):
            env["OPENAI_API_KEY"] = defaults["api_key"]
    if not str(env.get("OPENAI_BASE_URL", "")).strip() and defaults.get("base_url"):
        env["OPENAI_BASE_URL"] = defaults["base_url"]
    if str(env.get("OPENAI_API_KEY", "")).strip():
        env.setdefault("CTCP_LIVE_API", "1")

    cmd = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_live_api_only_pipeline.py",
        "-v",
    ]
    proc = subprocess.run(cmd, env=env)
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
