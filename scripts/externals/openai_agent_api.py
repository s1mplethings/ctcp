#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

SELF_DIR = Path(__file__).resolve().parent
if str(SELF_DIR) not in sys.path:
    sys.path.insert(0, str(SELF_DIR))

from openai_responses_client import call_openai_responses


def main() -> int:
    prompt = sys.stdin.read()
    if not prompt.strip():
        if len(sys.argv) >= 2:
            prompt_path = Path(sys.argv[1])
            if prompt_path.exists():
                prompt = prompt_path.read_text(encoding="utf-8", errors="replace")
    if not prompt.strip():
        print("openai_agent_api.py requires prompt from stdin or prompt file path", file=sys.stderr)
        return 2

    model = (
        os.environ.get("SDDAI_OPENAI_AGENT_MODEL", "")
        or os.environ.get("SDDAI_OPENAI_MODEL", "")
        or "gpt-4.1-mini"
    ).strip()
    timeout_sec = int(os.environ.get("SDDAI_OPENAI_TIMEOUT_SEC", "180"))

    text, err = call_openai_responses(prompt=prompt, model=model, timeout_sec=timeout_sec)
    if err:
        print(err, file=sys.stderr)
        return 1
    sys.stdout.write(text.rstrip() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
