from __future__ import annotations

import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from llm_core.clients.openai_compatible import call_openai_compatible


LIVE_PROVIDER_PROJECTS = {
    "markdown_notes_api",
    "csv_expense_analyzer",
    "local_kanban_board_app",
}

ALLOWED_FRAGMENT_PATHS = {
    "markdown_notes_api": {
        "provider_live_note_helpers.py",
        "docs/live_provider_assisted.md",
    },
    "csv_expense_analyzer": {
        "provider_live_helper.py",
        "docs/live_provider_assisted.md",
    },
    "local_kanban_board_app": {
        "static/live_provider_enhancements.js",
        "docs/live_provider_assisted.md",
    },
}

DEFAULT_LIVE_PROVIDER_MODEL = "gpt-4.1-mini"
DEFAULT_TIMEOUT_SECONDS = 45
MAX_PROVIDER_RETRIES = 1


@dataclass(frozen=True)
class LiveProviderCallResult:
    fragments: dict[str, str]
    metadata: dict[str, Any]


def live_provider_requested(goal_text: str) -> bool:
    haystack = str(goal_text or "").lower()
    return (
        "live-provider-assisted" in haystack
        or "live_provider_assisted" in haystack
        or "live provider-assisted" in haystack
        or "live provider assisted" in haystack
    )


def live_provider_enabled(goal_text: str) -> bool:
    raw = str(os.environ.get("CTCP_LIVE_PROVIDER_ASSISTED", "")).strip().lower()
    return raw in {"1", "true", "yes"} or live_provider_requested(goal_text)


@contextmanager
def _bounded_live_provider_env() -> Any:
    keys = {
        "SDDAI_OPENAI_RESPONSE_FORMAT": "json_object",
        "SDDAI_OPENAI_MAX_OUTPUT_TOKENS": str(_safe_int_env("CTCP_LIVE_PROVIDER_MAX_OUTPUT_TOKENS", 900, 200, 1800)),
        "SDDAI_OPENAI_MAX_ATTEMPTS": "1",
    }
    old = {key: os.environ.get(key) for key in keys}
    try:
        os.environ.update(keys)
        yield
    finally:
        for key, value in old.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _safe_int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = str(os.environ.get(name, "")).strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except Exception:
        return default
    return min(max(value, minimum), maximum)


def _live_provider_model() -> str:
    return (
        str(os.environ.get("CTCP_LIVE_PROVIDER_MODEL", "")).strip()
        or str(os.environ.get("SDDAI_OPENAI_AGENT_MODEL", "")).strip()
        or str(os.environ.get("SDDAI_OPENAI_MODEL", "")).strip()
        or DEFAULT_LIVE_PROVIDER_MODEL
    )


def _live_provider_timeout() -> int:
    return _safe_int_env("CTCP_LIVE_PROVIDER_TIMEOUT_SEC", DEFAULT_TIMEOUT_SECONDS, 5, 90)


def _build_prompt(*, goal_text: str, project_id: str) -> str:
    allowed = sorted(ALLOWED_FRAGMENT_PATHS.get(project_id, set()))
    if project_id == "csv_expense_analyzer":
        task = (
            "Generate a tiny pure Python helper for CSV expense report formatting. "
            "Do not read files, do not call open(), do not import csv/sys/os/pathlib. "
            "Prefer pure functions like format_money(value) and category_label(category, amount)."
        )
    elif project_id == "markdown_notes_api":
        task = (
            "Generate a tiny pure Python helper for markdown note metadata summarization. "
            "Do not read files, do not call open(), and do not import pathlib/os. "
            "Prefer pure functions that count headings or summarize a title and markdown string."
        )
    elif project_id == "local_kanban_board_app":
        task = (
            "Generate a tiny browser JavaScript helper for Kanban column/card display. "
            "Do not call fetch/XMLHttpRequest/WebSocket/localStorage/sessionStorage. "
            "Prefer pure display helpers attached to window."
        )
    else:
        task = "Generate a tiny safe helper fragment."
    return (
        "Return strict JSON only. No markdown fences.\n"
        "You are generating bounded low-risk helper fragments for CTCP live_provider_assisted mode.\n"
        "Do not generate server core, database code, subprocess, shell, network, eval, exec, filesystem traversal, file IO, imports for IO/network/system modules, or validation bypass code.\n"
        "Use only the allowed relative paths. Keep each content under 120 lines.\n"
        f"Project id: {project_id}\n"
        f"Allowed paths: {', '.join(allowed)}\n"
        f"Task: {task}\n"
        f"User goal: {goal_text[:800]}\n"
        "Schema:\n"
        "{\n"
        '  "fragments": [{"path": "allowed/path.ext", "content": "file contents"}],\n'
        '  "sections": ["live_helper_generation"],\n'
        '  "notes": "short note"\n'
        "}\n"
    )


def _extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        doc = json.loads(raw)
        return doc if isinstance(doc, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {}
    try:
        doc = json.loads(match.group(0))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _normalize_fragments(project_id: str, doc: dict[str, Any]) -> tuple[dict[str, str], list[str], list[str]]:
    allowed = ALLOWED_FRAGMENT_PATHS.get(project_id, set())
    fragments: dict[str, str] = {}
    rejected: list[str] = []
    rows = doc.get("fragments")
    if not isinstance(rows, list):
        return {}, [], ["missing_fragments_array"]
    for row in rows:
        if not isinstance(row, dict):
            rejected.append("non_object_fragment")
            continue
        rel = str(row.get("path", "")).strip().replace("\\", "/").lstrip("/")
        content = str(row.get("content", ""))
        if rel not in allowed:
            rejected.append(f"disallowed_path:{rel}")
            continue
        if not content.strip():
            rejected.append(f"empty_fragment:{rel}")
            continue
        fragments[rel] = content.rstrip() + "\n"
    sections = [str(item).strip() for item in doc.get("sections", []) if str(item).strip()] if isinstance(doc.get("sections", []), list) else []
    if not sections and fragments:
        sections = ["live_helper_generation", "README/live provider documentation variation"]
    return fragments, sections, rejected


def _fallback_metadata(
    *,
    project_id: str,
    request_count: int,
    reason: str,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "live_provider_used": bool(request_count),
        "provider_request_count": int(request_count),
        "provider_fragment_count": 0,
        "provider_name": "live_provider",
        "provider_authorship": "provider_assisted",
        "generation_mode": "live_provider_assisted",
        "provider_assisted_sections": [],
        "provider_generated_files": [],
        "provider_fallbacks": [
            {
                "project": project_id,
                "reason": reason,
                "errors": list(errors or []),
            }
        ],
        "provider_validation": {
            "syntax_valid": False,
            "runtime_valid": True,
            "fallback_triggered": True,
        },
    }


def call_live_provider_for_fragments(*, goal_text: str, project_id: str) -> LiveProviderCallResult:
    if project_id not in LIVE_PROVIDER_PROJECTS:
        return LiveProviderCallResult(
            fragments={},
            metadata=_fallback_metadata(
                project_id=project_id,
                request_count=0,
                reason="live_provider_project_not_allowed",
            ),
        )
    if str(os.environ.get("CTCP_LIVE_PROVIDER_FORCE_INVALID", "")).strip().lower() in {"1", "true", "yes"}:
        return LiveProviderCallResult(
            fragments={"provider_live_helper.py": "def broken(:\n"},
            metadata={
                "live_provider_used": True,
                "provider_request_count": 1,
                "provider_fragment_count": 1,
                "provider_name": "live_provider",
                "provider_authorship": "provider_assisted",
                "generation_mode": "live_provider_assisted",
                "provider_assisted_sections": ["live_helper_generation"],
                "provider_generated_files": [],
                "provider_fallbacks": [],
                "provider_validation": {
                    "syntax_valid": False,
                    "runtime_valid": False,
                    "fallback_triggered": False,
                },
            },
        )

    prompt = _build_prompt(goal_text=goal_text, project_id=project_id)
    model = _live_provider_model()
    timeout_sec = _live_provider_timeout()
    errors: list[str] = []
    request_count = 0
    for _attempt in range(1, MAX_PROVIDER_RETRIES + 2):
        request_count += 1
        with _bounded_live_provider_env():
            text, err = call_openai_compatible(prompt=prompt, model=model, timeout_sec=timeout_sec)
        if err:
            errors.append(err)
            continue
        doc = _extract_json_object(text)
        if not doc:
            errors.append("provider_response_not_json_object")
            continue
        fragments, sections, rejected = _normalize_fragments(project_id, doc)
        if rejected:
            errors.extend(rejected)
        if fragments:
            metadata = {
                "live_provider_used": True,
                "provider_request_count": request_count,
                "provider_fragment_count": len(fragments),
                "provider_name": "live_provider",
                "provider_authorship": "provider_assisted",
                "generation_mode": "live_provider_assisted",
                "provider_assisted_sections": sections,
                "provider_generated_files": [],
                "provider_fallbacks": [],
                "provider_validation": {
                    "syntax_valid": True,
                    "runtime_valid": True,
                    "fallback_triggered": False,
                },
                "provider_model": model,
                "provider_timeout_seconds": timeout_sec,
            }
            return LiveProviderCallResult(fragments=fragments, metadata=metadata)

    return LiveProviderCallResult(
        fragments={},
        metadata=_fallback_metadata(
            project_id=project_id,
            request_count=request_count,
            reason="live_provider_no_valid_fragments",
            errors=errors,
        ),
    )
