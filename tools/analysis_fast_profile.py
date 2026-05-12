from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from tools.analysis_stage_progress import ANALYSIS_TARGET_PATH, is_analysis_request

FAST_ANALYSIS_PROFILE = "fast"
DEFAULT_ANALYSIS_PROFILE = "default"
DEFAULT_FAST_MAX_OUTPUT_TOKENS = 900

FAST_ANALYSIS_OUTPUT_CONTRACT = """# Analysis

## Project Type
One short paragraph naming the concrete software project type.

## Required Files
Bullets for the minimum files/directories the later source_generation step must create.

## Runtime
Bullets for entrypoint, HTTP/server behavior, CLI args if needed, and local run command expectations.

## Data Model
Bullets for persisted entities, fields, enums/status values, and SQLite expectations.

## Acceptance Checks
Bullets for generated tests, HTTP probes, SQLite validation, and README/run instructions.
"""


def analysis_profile() -> str:
    raw = str(os.environ.get("CTCP_ANALYSIS_PROFILE", "")).strip().lower()
    return FAST_ANALYSIS_PROFILE if raw == FAST_ANALYSIS_PROFILE else DEFAULT_ANALYSIS_PROFILE


def fast_analysis_enabled(request: dict[str, Any]) -> bool:
    return is_analysis_request(request) and analysis_profile() == FAST_ANALYSIS_PROFILE


def estimate_tokens(text: str) -> int:
    value = str(text or "")
    if not value:
        return 0
    return max(1, int((len(value) + 3) / 4))


def max_output_tokens() -> int:
    raw = str(os.environ.get("CTCP_ANALYSIS_MAX_OUTPUT_TOKENS", "")).strip()
    if not raw:
        return DEFAULT_FAST_MAX_OUTPUT_TOKENS
    try:
        value = int(raw)
    except Exception:
        return DEFAULT_FAST_MAX_OUTPUT_TOKENS
    return max(256, min(2000, value))


def prompt_budget(prompt_text: str, *, profile: str | None = None, default_prompt_text: str = "") -> dict[str, Any]:
    default_chars = len(str(default_prompt_text or ""))
    return {
        "prompt_char_count": len(str(prompt_text or "")),
        "prompt_estimated_tokens": estimate_tokens(prompt_text),
        "default_prompt_char_count": default_chars,
        "default_prompt_estimated_tokens": estimate_tokens(default_prompt_text) if default_chars else 0,
        "output_contract": FAST_ANALYSIS_OUTPUT_CONTRACT.strip()
        if (profile or analysis_profile()) == FAST_ANALYSIS_PROFILE
        else "default analysis normalizer contract",
        "max_output_tokens": max_output_tokens() if (profile or analysis_profile()) == FAST_ANALYSIS_PROFILE else 0,
        "analysis_profile": profile or analysis_profile(),
    }


def _compact_goal(goal: str, *, max_chars: int = 1800) -> str:
    text = re.sub(r"\s+", " ", str(goal or "").strip())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 20].rstrip() + " ... [truncated]"


def _missing_paths(request: dict[str, Any]) -> str:
    rows = [str(x).strip() for x in request.get("missing_paths", []) if str(x).strip()]
    if not rows:
        rows = [ANALYSIS_TARGET_PATH]
    return "\n".join(f"- {row}" for row in rows)


def render_fast_analysis_prompt(
    *,
    run_dir: Path,
    repo_root: Path,
    request: dict[str, Any],
    evidence: dict[str, Path] | None = None,
) -> str:
    del evidence
    goal = _compact_goal(str(request.get("goal", "")))
    reason = _compact_goal(str(request.get("reason", "")), max_chars=600)
    target_path = str(request.get("target_path", ANALYSIS_TARGET_PATH)).strip() or ANALYSIS_TARGET_PATH
    return "\n".join(
        [
            "# API AGENT PROMPT",
            "",
            "Analysis-Profile: fast",
            f"Run-Dir: {run_dir.resolve()}",
            f"Repo-Root: {repo_root.resolve()}",
            "Role: chair",
            "Action: plan_draft",
            "Provider: api_agent",
            f"Target-Path: {target_path}",
            f"write to: {target_path}",
            "",
            "Goal:",
            goal,
            "",
            "Reason:",
            reason or "waiting for analysis.md",
            "",
            "Missing-Artifact-Paths:",
            _missing_paths(request),
            "",
            "Hard Rules:",
            "- Produce exactly one short Markdown analysis artifact.",
            "- Still analyze the concrete project request; do not skip this gate.",
            "- Do not output source code, patches, or a full implementation plan.",
            "- Do not generate an agent manifest, agent scaffold, dry-run, or workflow package.",
            "- Keep the output under 1200 words.",
            "- Include only information needed by later source_generation.",
            "",
            "Concrete Project Constraints:",
            "- The downstream artifact must describe a real runnable software project.",
            "- Preserve required endpoints, persistence, status enums, generated tests, README, and local runtime expectations from the goal.",
            "- Prefer SQLite persistence when the goal requires it.",
            "",
            "Output Contract:",
            FAST_ANALYSIS_OUTPUT_CONTRACT.strip(),
            "",
            "Return the Markdown artifact only. Do not wrap in code fences.",
            "",
        ]
    )


__all__ = [
    "DEFAULT_FAST_MAX_OUTPUT_TOKENS",
    "FAST_ANALYSIS_OUTPUT_CONTRACT",
    "FAST_ANALYSIS_PROFILE",
    "analysis_profile",
    "estimate_tokens",
    "fast_analysis_enabled",
    "max_output_tokens",
    "prompt_budget",
    "render_fast_analysis_prompt",
]
