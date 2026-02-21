#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

SELF_DIR = Path(__file__).resolve().parent
if str(SELF_DIR) not in sys.path:
    sys.path.insert(0, str(SELF_DIR))

from openai_responses_client import call_openai_responses


def _read(path: str, limit: int = 12000) -> str:
    p = Path(path)
    if not p.exists():
        return f"[missing] {path}"
    text = p.read_text(encoding="utf-8", errors="replace")
    if len(text) > limit:
        return text[:limit] + "\n\n[truncated]"
    return text


def main() -> int:
    if len(sys.argv) < 7:
        print(
            "usage: openai_plan_api.py <CONTEXT_PATH> <CONSTRAINTS_PATH> <FIX_BRIEF_PATH> <GOAL> <ROUND> <REPO_ROOT>",
            file=sys.stderr,
        )
        return 2

    context_path, constraints_path, fix_brief_path, goal, round_no, _repo_root = sys.argv[1:7]
    model = (
        os.environ.get("SDDAI_OPENAI_PLAN_MODEL", "")
        or os.environ.get("SDDAI_OPENAI_MODEL", "")
        or "gpt-4.1-mini"
    ).strip()
    timeout_sec = int(os.environ.get("SDDAI_OPENAI_TIMEOUT_SEC", "180"))

    prompt = "\n".join(
        [
            "You are an external planner for an ADLC self-improve workflow.",
            "Return PLAN.md content only in plain markdown.",
            "Do not wrap in code fences.",
            "",
            f"Goal: {goal}",
            f"Round: {round_no}",
            "",
            "Constraints:",
            _read(constraints_path, limit=8000),
            "",
            "Fix brief:",
            _read(fix_brief_path, limit=8000),
            "",
            "Context evidence:",
            _read(context_path, limit=10000),
            "",
            "Requirements:",
            "- Keep patch scope minimal and policy-compliant.",
            "- Include concrete acceptance steps.",
        ]
    )

    text, err = call_openai_responses(prompt=prompt, model=model, timeout_sec=timeout_sec)
    if err:
        print(err, file=sys.stderr)
        return 1
    sys.stdout.write(text.strip() + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

