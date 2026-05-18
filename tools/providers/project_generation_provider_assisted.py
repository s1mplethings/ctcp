from __future__ import annotations

import ast
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.providers.live_provider_adapter import (
    LiveProviderCallResult,
    call_live_provider_for_fragments,
    live_provider_enabled,
    live_provider_requested,
)
from tools.providers.project_generation_live_full_candidate import (
    live_blind_candidate_enabled,
    live_blind_candidate_requested,
    live_full_candidate_enabled,
    live_full_candidate_requested,
    live_medium_candidate_enabled,
    live_medium_candidate_requested,
)


FORBIDDEN_FRAGMENT_TOKENS = (
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "os.system",
    "eval(",
    "exec(",
    "__import__",
    "open(",
    "Path(",
    "shutil",
    "fetch(",
    "xmlhttprequest",
    "websocket",
    "localstorage",
    "sessionstorage",
    "ctcp_orchestrate",
    "benchmark_report",
)

MAX_FRAGMENT_BYTES = 16_000
_LIVE_PROVIDER_CACHE: dict[tuple[str, str], LiveProviderCallResult] = {}


@dataclass(frozen=True)
class ProviderAssistedResult:
    files: dict[str, str]
    metadata: dict[str, Any]


def provider_assisted_requested(goal_text: str) -> bool:
    haystack = str(goal_text or "").lower()
    return (
        "provider-assisted" in haystack
        or "provider_assisted" in haystack
        or live_provider_requested(goal_text)
        or live_full_candidate_requested(goal_text)
        or live_blind_candidate_requested(goal_text)
        or live_medium_candidate_requested(goal_text)
    )


def provider_assisted_enabled(goal_text: str) -> bool:
    if live_full_candidate_enabled(goal_text):
        return True
    if live_blind_candidate_enabled(goal_text):
        return True
    if live_medium_candidate_enabled(goal_text):
        return True
    if live_provider_enabled(goal_text):
        return True
    if os.environ.get("CTCP_PROVIDER_ASSISTED", "").strip().lower() in {"1", "true", "yes"}:
        return True
    return provider_assisted_requested(goal_text)


def provider_assisted_generation_mode(goal_text: str) -> str:
    if live_full_candidate_enabled(goal_text):
        return "live_provider_full_candidate"
    if live_blind_candidate_enabled(goal_text):
        return "live_provider_blind_candidate"
    if live_medium_candidate_enabled(goal_text):
        return "live_provider_medium_candidate"
    if live_provider_enabled(goal_text):
        return "live_provider_assisted"
    if provider_assisted_enabled(goal_text):
        return "provider_assisted"
    return "concrete_fast_path"


def _fixture_mode() -> str:
    return os.environ.get("CTCP_PROVIDER_ASSISTED_FIXTURE", "").strip().lower()


def _safe_text(path: str, content: str) -> tuple[bool, str]:
    if len(content.encode("utf-8")) > MAX_FRAGMENT_BYTES:
        return False, "fragment_too_large"
    lowered = content.lower()
    for token in FORBIDDEN_FRAGMENT_TOKENS:
        if token in lowered:
            return False, f"forbidden_token:{token}"
    if path.endswith(".py"):
        try:
            ast.parse(content)
        except SyntaxError as exc:
            return False, f"syntax_error:{exc.lineno}:{exc.offset}"
    return True, "ok"


def validate_provider_fragments(fragments: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for path, content in sorted(fragments.items()):
        valid, reason = _safe_text(path, content)
        rows.append({"path": path, "valid": valid, "reason": reason})
    syntax_valid = all(row["valid"] for row in rows)
    return {
        "syntax_valid": syntax_valid,
        "runtime_valid": syntax_valid,
        "fallback_triggered": not syntax_valid,
        "rows": rows,
    }


def _provider_fragment_for_project(project_id: str) -> dict[str, str]:
    if _fixture_mode() == "invalid":
        return {
            "provider_assisted_helper.py": "def provider_assisted_helper(:\n    return 'broken'\n",
        }
    if project_id == "csv_expense_analyzer":
        return {
            "provider_assisted_helper.py": (
                "from __future__ import annotations\n\n"
                "def format_money(value: float) -> str:\n"
                "    return f\"${value:.2f}\"\n\n"
                "def report_label(category: str, amount: float) -> str:\n"
                "    return f\"{category}: {format_money(amount)}\"\n"
            ),
            "docs/provider_assisted.md": (
                "# Provider-Assisted Sections\n\n"
                "- Added safe formatting helper functions for report presentation.\n"
                "- Core CSV parsing and totals remain deterministic materializer code.\n"
            ),
        }
    if project_id == "markdown_notes_api":
        return {
            "provider_note_helpers.py": (
                "from __future__ import annotations\n\n"
                "def summarize_markdown_title(title: str, markdown: str) -> dict[str, object]:\n"
                "    heading_count = sum(1 for line in markdown.splitlines() if line.lstrip().startswith('#'))\n"
                "    return {'title': title.strip(), 'heading_count': heading_count, 'has_body': bool(markdown.strip())}\n"
            ),
            "docs/provider_assisted.md": (
                "# Provider-Assisted Sections\n\n"
                "- Added markdown summary helper for optional note metadata.\n"
                "- Filesystem storage and HTTP behavior remain deterministic materializer code.\n"
            ),
        }
    if project_id == "local_kanban_board_app":
        return {
            "static/provider_enhancements.js": (
                "function providerColumnLabel(column) {\n"
                "  const labels = {todo: 'Todo', doing: 'Doing', done: 'Done'};\n"
                "  return labels[column] || column;\n"
                "}\n"
                "window.providerColumnLabel = providerColumnLabel;\n"
            ),
            "docs/provider_assisted.md": (
                "# Provider-Assisted Sections\n\n"
                "- Added optional frontend column-label helper.\n"
                "- Board/card API, SQLite persistence, and move behavior remain deterministic materializer code.\n"
            ),
        }
    return {
        "docs/provider_assisted.md": (
            "# Provider-Assisted Sections\n\n"
            "- Provider assistance requested, but no project-specific safe fragment was available.\n"
        )
    }


def _append_readme_note(files: dict[str, str], project_root: str) -> None:
    readme = f"{project_root}/README.md"
    if readme not in files:
        return
    files[readme] = (
        files[readme].rstrip()
        + "\n\n## Provider-Assisted Variation\n\n"
        "- Low-risk helper/documentation fragments were generated through provider-assisted mode.\n"
        "- Deterministic materializer output remains the core runtime source of truth.\n"
    )
    if "provider_assisted" not in files[readme]:
        files[readme] += "\n"


def _touch_manifest(files: dict[str, str], project_root: str, generation_mode: str = "provider_assisted") -> None:
    manifest = f"{project_root}/meta/manifest.json"
    if manifest in files:
        files[manifest] = files[manifest].replace('"generation_mode": "concrete_fast_path"', f'"generation_mode": "{generation_mode}"')
        files[manifest] = files[manifest].replace('"generation_mode": "provider_assisted"', f'"generation_mode": "{generation_mode}"')


def _live_provider_result(goal_text: str, project_id: str) -> LiveProviderCallResult:
    key = (str(project_id or ""), str(goal_text or ""))
    if key not in _LIVE_PROVIDER_CACHE:
        _LIVE_PROVIDER_CACHE[key] = call_live_provider_for_fragments(goal_text=goal_text, project_id=project_id)
    return _LIVE_PROVIDER_CACHE[key]


def apply_provider_assistance(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    deterministic_files: dict[str, str],
) -> ProviderAssistedResult:
    if not provider_assisted_enabled(goal_text):
        return ProviderAssistedResult(files=deterministic_files, metadata=provider_assisted_metadata(project_id=project_id, enabled=False))

    generation_mode = provider_assisted_generation_mode(goal_text)
    live_metadata: dict[str, Any] = {}
    if generation_mode == "live_provider_assisted":
        live_result = _live_provider_result(goal_text, project_id)
        fragments_rel = dict(live_result.fragments)
        live_metadata = dict(live_result.metadata)
    else:
        fragments_rel = _provider_fragment_for_project(project_id)
    validation = validate_provider_fragments(fragments_rel)
    if not fragments_rel or not bool(validation.get("syntax_valid", False)):
        fallback_reason = "live_provider_fragment_validation_failed" if generation_mode == "live_provider_assisted" else "provider_fragment_validation_failed"
        metadata = provider_assisted_metadata(
            project_id=project_id,
            enabled=True,
            generation_mode=generation_mode,
            provider_name="live_provider" if generation_mode == "live_provider_assisted" else "local_fixture_provider",
            live_provider_used=bool(live_metadata.get("live_provider_used", False)),
            provider_request_count=int(live_metadata.get("provider_request_count", 0) or 0),
            provider_fragment_count=int(live_metadata.get("provider_fragment_count", 0) or 0),
            fallback_triggered=True,
            fallbacks=list(live_metadata.get("provider_fallbacks", []))
            or [{"project": project_id, "reason": fallback_reason, "validation": validation}],
            validation=validation,
            extra_metadata=live_metadata,
        )
        return ProviderAssistedResult(files=deterministic_files, metadata=metadata)

    files = dict(deterministic_files)
    provider_files: list[str] = []
    root = str(project_root).strip().rstrip("/")
    for rel, content in fragments_rel.items():
        full_rel = f"{root}/{rel.strip().lstrip('/')}"
        files[full_rel] = content
        provider_files.append(full_rel)
    _append_readme_note(files, root)
    _touch_manifest(files, root, generation_mode)
    metadata = provider_assisted_metadata(
        project_id=project_id,
        enabled=True,
        generation_mode=generation_mode,
        provider_name="live_provider" if generation_mode == "live_provider_assisted" else "local_fixture_provider",
        live_provider_used=bool(live_metadata.get("live_provider_used", False)),
        provider_request_count=int(live_metadata.get("provider_request_count", 0) or 0),
        provider_fragment_count=len(provider_files),
        provider_assisted_sections=list(live_metadata.get("provider_assisted_sections", [])) if generation_mode == "live_provider_assisted" else None,
        provider_generated_files=provider_files,
        validation=validation,
        extra_metadata=live_metadata,
    )
    files[f"{root}/provider_assisted_report.json"] = json.dumps(metadata, ensure_ascii=False, indent=2) + "\n"
    return ProviderAssistedResult(files=files, metadata=metadata)


def provider_assisted_metadata(
    *,
    project_id: str,
    enabled: bool,
    generation_mode: str | None = None,
    provider_name: str = "local_fixture_provider",
    provider_generated_files: list[str] | None = None,
    provider_assisted_sections: list[str] | None = None,
    fallbacks: list[dict[str, Any]] | None = None,
    fallback_triggered: bool = False,
    validation: dict[str, Any] | None = None,
    live_provider_used: bool = False,
    provider_request_count: int = 0,
    provider_fragment_count: int | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extra = dict(extra_metadata or {})
    provider_files = list(provider_generated_files or [])
    sections = list(provider_assisted_sections or [])
    if enabled and provider_files and not sections:
        sections = ["safe_helper_generation", "README/provider documentation variation"]
    mode = generation_mode or ("provider_assisted" if enabled else "concrete_fast_path")
    validation_doc = validation or dict(extra.get("provider_validation", {})) or {
        "syntax_valid": not fallback_triggered,
        "runtime_valid": not fallback_triggered,
        "fallback_triggered": bool(fallback_triggered),
        "rows": [],
    }
    validation_doc["fallback_triggered"] = bool(validation_doc.get("fallback_triggered", False) or fallback_triggered)
    return {
        "used_provider_agent": bool(enabled),
        "provider_name": provider_name,
        "provider_authorship": "provider_assisted" if enabled else "not_claimed",
        "generation_mode": mode,
        "live_provider_used": bool(live_provider_used),
        "provider_request_count": int(provider_request_count or 0),
        "provider_fragment_count": int(provider_fragment_count if provider_fragment_count is not None else len(provider_files)),
        "provider_assisted_sections": sections,
        "provider_generated_files": provider_files,
        "provider_fallbacks": list(fallbacks or []),
        "provider_validation": validation_doc,
        "deterministic_sections": [
            "core project structure",
            "runtime validation contract",
            "persistence guarantee",
            "generated tests",
        ],
        "provider_participation_model": "bounded_low_risk_fragments" if enabled else "none",
        "safety_filters": {
            "forbidden_tokens": list(FORBIDDEN_FRAGMENT_TOKENS),
            "max_fragment_bytes": MAX_FRAGMENT_BYTES,
        },
        "provider_model": str(extra.get("provider_model", "")),
        "provider_timeout_seconds": int(extra.get("provider_timeout_seconds", 0) or 0),
    }


def merge_provider_assisted_provenance(base: dict[str, Any], metadata: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(base)
    meta = dict(metadata or {})
    if not meta.get("used_provider_agent"):
        out.setdefault("used_provider_agent", False)
        out.setdefault("provider_assisted_sections", [])
        out.setdefault("provider_generated_files", [])
        out.setdefault("provider_fallbacks", [])
        out.setdefault("provider_validation", {"syntax_valid": True, "runtime_valid": True, "fallback_triggered": False})
        return out
    out["generation_mode"] = str(meta.get("generation_mode", "provider_assisted"))
    out["provider_authorship"] = "provider_assisted"
    out["used_provider_agent"] = True
    out["provider_name"] = str(meta.get("provider_name", "local_fixture_provider"))
    out["live_provider_used"] = bool(meta.get("live_provider_used", False))
    out["provider_request_count"] = int(meta.get("provider_request_count", 0) or 0)
    out["provider_fragment_count"] = int(meta.get("provider_fragment_count", 0) or 0)
    out["provider_assisted_sections"] = list(meta.get("provider_assisted_sections", []))
    out["provider_generated_files"] = list(meta.get("provider_generated_files", []))
    out["provider_fallbacks"] = list(meta.get("provider_fallbacks", []))
    out["provider_validation"] = dict(meta.get("provider_validation", {}))
    out["deterministic_sections"] = list(meta.get("deterministic_sections", []))
    out["provider_participation_model"] = str(meta.get("provider_participation_model", "bounded_low_risk_fragments"))
    out["safety_filters"] = dict(meta.get("safety_filters", {}))
    out["provider_model"] = str(meta.get("provider_model", ""))
    out["provider_timeout_seconds"] = int(meta.get("provider_timeout_seconds", 0) or 0)
    return out


def read_provider_assisted_metadata(run_dir: Path) -> dict[str, Any]:
    path = Path(run_dir) / "artifacts" / "provider_assisted_generation.json"
    if not path.exists():
        return provider_assisted_metadata(project_id="", enabled=False)
    try:
        import json

        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return provider_assisted_metadata(project_id="", enabled=False, fallback_triggered=True)
    return raw if isinstance(raw, dict) else provider_assisted_metadata(project_id="", enabled=False)
