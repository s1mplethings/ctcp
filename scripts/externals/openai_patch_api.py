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
    if len(sys.argv) < 8:
        print(
            "usage: openai_patch_api.py <PLAN_PATH> <CONTEXT_PATH> <CONSTRAINTS_PATH> <FIX_BRIEF_PATH> <GOAL> <ROUND> <REPO_ROOT>",
            file=sys.stderr,
        )
        return 2

    plan_path, context_path, constraints_path, fix_brief_path, goal, round_no, _repo_root = sys.argv[1:8]
    model = (
        os.environ.get("SDDAI_OPENAI_PATCH_MODEL", "")
        or os.environ.get("SDDAI_OPENAI_MODEL", "")
        or "gpt-4.1-mini"
    ).strip()
    timeout_sec = int(os.environ.get("SDDAI_OPENAI_TIMEOUT_SEC", "240"))

    prompt = "\n".join(
        [
            """SYSTEM CONTRACT (EN)

You are a patch-first coding agent. Follow these rules strictly:

Scope: Only make changes that are necessary to fulfill the user’s request. Do not refactor, rename, reformat, or change unrelated logic.

Minimality: Prefer the smallest verified change. Avoid touching files not required by the fix.

Output: Produce exactly ONE unified diff patch that is git apply compatible. No explanations, no extra text.

Verification: If the repository has an existing verification command (tests / lint / verify_repo / CI script), run or specify it in your plan. Do not add new dependencies.

If uncertain: Stop after producing a short PLAN in JSON (see below) and do NOT output a patch.

PLAN JSON schema (only when uncertain):
{
"goal": "...",
"assumptions": ["..."],
"files_to_change": ["..."],
"steps": ["..."],
"verification": ["..."]
}

Additional constraints:

Never modify more than the minimum number of files needed.

Never change formatting outside the prompt/contract text area.

Never change any behavior except prompt/contract enforcement.

END SYSTEM CONTRACT

You are an external patch generator.""",
            "Output MUST be unified diff only.",
            "The first output line MUST start with: diff --git",
            "Do not output explanations or code fences.",
            "",
            f"Goal: {goal}",
            f"Round: {round_no}",
            "",
            "Plan:",
            _read(plan_path, limit=8000),
            "",
            "Constraints:",
            _read(constraints_path, limit=8000),
            "",
            "Fix brief:",
            _read(fix_brief_path, limit=8000),
            "",
            "Context evidence:",
            _read(context_path, limit=8000),
            "",
            "Hard limits:",
            "- Keep changes minimal and policy-compliant.",
            "- Do not include any non-patch text.",
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

