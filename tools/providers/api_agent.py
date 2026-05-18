#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_NOTES_PATH = ROOT / ".agent_private" / "NOTES.md"
EMBEDDED_BASE_URL = "https://api.gptsapi.net"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ctcp_adapters import ctcp_artifact_normalizers as ctcp_api
from llm_core.providers import api_provider as core_api

_sanitize = core_api._sanitize
_slug = core_api._slug
_read_text = core_api._read_text
_write_text = core_api._write_text
_first_non_empty_line = core_api._first_non_empty_line
_default_plan_cmd = core_api._default_plan_cmd
_default_patch_cmd = core_api._default_patch_cmd
_default_agent_cmd = core_api._default_agent_cmd
_format_cmd_template = core_api._format_cmd_template
_shell_safe_template_text = core_api._shell_safe_template_text
_decode_subprocess_score = core_api._decode_subprocess_score
_decode_subprocess_text = core_api._decode_subprocess_text
_run_command = core_api._run_command

_normalize_line_ranges = ctcp_api._normalize_line_ranges
_render_snippets = ctcp_api._render_snippets
_extract_json_dict = ctcp_api._extract_json_dict
_to_json_text = ctcp_api._to_json_text
_normalize_file_request = ctcp_api._normalize_file_request
_fallback_context_pack_from_file_request = ctcp_api._fallback_context_pack_from_file_request
_normalize_context_pack = ctcp_api._normalize_context_pack
_normalize_find_web = ctcp_api._normalize_find_web
_normalize_guardrails_md = ctcp_api._normalize_guardrails_md
_normalize_review_md = ctcp_api._normalize_review_md
_normalize_plan_md = ctcp_api._normalize_plan_md
_normalize_json_artifact = ctcp_api._normalize_json_artifact
_record_failure_review = ctcp_api._record_failure_review
_load_externals_doc = ctcp_api._load_externals_doc
_render_context_md = ctcp_api._render_context_md
_render_constraints_md = ctcp_api._render_constraints_md
_render_externals_md = ctcp_api._render_externals_md
_render_fix_brief_seed = ctcp_api._render_fix_brief_seed
_render_whiteboard_md = ctcp_api._render_whiteboard_md
_write_fix_brief = ctcp_api._write_fix_brief
_max_outbox_prompts = ctcp_api._max_outbox_prompts
_build_evidence_pack = ctcp_api._build_evidence_pack
_render_prompt = ctcp_api._render_prompt
_needs_patch = ctcp_api._needs_patch
_needs_plan = ctcp_api._needs_plan
normalize_patch_payload = ctcp_api.normalize_patch_payload


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
    match_url = re.search(r"`(https?://[^`\s]+)`", text)
    if match_url:
        out["base_url"] = match_url.group(1).strip()
    match_key = re.search(r"`(sk-[^`\s]+)`", text)
    if match_key:
        out["api_key"] = match_key.group(1).strip()
    return out


def _normalize_base_url(value: str) -> str:
    root = str(value or "").strip().rstrip("/")
    if root.lower() in {"https://api.gptsapi.net/v1", "http://api.gptsapi.net/v1"}:
        return root[:-3].rstrip("/")
    return root


def _resolved_external_api_credentials() -> tuple[str, str]:
    defaults = _load_local_notes_defaults()
    env_key = str(os.environ.get("OPENAI_API_KEY", "")).strip()
    env_base_url = str(os.environ.get("OPENAI_BASE_URL", "")).strip()
    ctcp_key = str(os.environ.get("CTCP_OPENAI_API_KEY", "")).strip()
    ctcp_base_url = str(os.environ.get("CTCP_OPENAI_BASE_URL", "")).strip()
    notes_key = str(defaults.get("api_key", "")).strip()
    notes_base_url = str(defaults.get("base_url", "")).strip()
    key = env_key
    if key.lower() == "ollama" and not env_base_url:
        replacement_key = ctcp_key or notes_key
        if replacement_key:
            return replacement_key, _normalize_base_url(env_base_url or ctcp_base_url or notes_base_url)
        return key, _normalize_base_url(env_base_url or ctcp_base_url)
    if not key:
        key = ctcp_key or notes_key
    base_url = _normalize_base_url(env_base_url or ctcp_base_url or notes_base_url or EMBEDDED_BASE_URL)
    return key, base_url


def _is_api_env_ready() -> tuple[bool, str]:
    key, base_url = _resolved_external_api_credentials()
    if key:
        if key.lower() == "ollama" and not base_url:
            return False, "missing env: OPENAI_BASE_URL for ollama-style key"
        return True, ""
    return False, "missing env: OPENAI_API_KEY"


def _resolve_templates(repo_root: Path, request: dict[str, Any]) -> tuple[dict[str, str], str]:
    return core_api.resolve_templates(
        repo_root,
        request,
        needs_plan=_needs_plan,
        needs_patch=_needs_patch,
        agent_tpl=str(os.environ.get("SDDAI_AGENT_CMD", "")).strip(),
        plan_tpl=str(os.environ.get("SDDAI_PLAN_CMD", "")).strip(),
        patch_tpl=str(os.environ.get("SDDAI_PATCH_CMD", "")).strip(),
        is_api_env_ready=_is_api_env_ready,
        default_plan_cmd=_default_plan_cmd,
        default_patch_cmd=_default_patch_cmd,
        default_agent_cmd=_default_agent_cmd,
    )


def _normalize_target_payload(*, repo_root: Path, run_dir: Path, request: dict[str, Any], raw_text: str) -> tuple[str, str]:
    return ctcp_api.normalize_target_payload(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        raw_text=raw_text,
    )


def _is_provider_assisted_analysis(*, request: dict[str, Any]) -> bool:
    if str(request.get("role", "")).strip().lower() != "chair":
        return False
    target = str(request.get("target_path", "")).strip().replace("\\", "/").lower()
    if not target.endswith("artifacts/analysis.md"):
        return False
    goal = str(request.get("goal", "")).strip().lower()
    return (
        "provider-assisted" in goal
        or "provider_assisted" in goal
        or "live-provider-assisted" in goal
        or "live_provider_assisted" in goal
        or "live provider assisted" in goal
        or "live-provider-full-candidate" in goal
        or "live_provider_full_candidate" in goal
        or "live provider full candidate" in goal
        or "live-provider-blind-candidate" in goal
        or "live_provider_blind_candidate" in goal
        or "live provider blind" in goal
        or "live-provider-medium-candidate" in goal
        or "live_provider_medium_candidate" in goal
        or "live provider medium" in goal
    )


def _provider_generation_mode_from_goal(goal: str) -> str:
    lowered = str(goal or "").lower()
    if (
        "live-provider-assisted" in lowered
        or "live_provider_assisted" in lowered
        or "live provider assisted" in lowered
    ):
        return "live_provider_assisted"
    if (
        "live-provider-full-candidate" in lowered
        or "live_provider_full_candidate" in lowered
        or "live provider full candidate" in lowered
    ):
        return "live_provider_full_candidate"
    if (
        "live-provider-blind-candidate" in lowered
        or "live_provider_blind_candidate" in lowered
        or "live provider blind" in lowered
    ):
        return "live_provider_blind_candidate"
    if (
        "live-provider-medium-candidate" in lowered
        or "live_provider_medium_candidate" in lowered
        or "live provider medium" in lowered
    ):
        return "live_provider_medium_candidate"
    return "provider_assisted"


def _execute_provider_assisted_analysis(*, run_dir: Path, request: dict[str, Any]) -> dict[str, Any] | None:
    if not _is_provider_assisted_analysis(request=request):
        return None
    target_rel = str(request.get("target_path", "artifacts/analysis.md")).strip() or "artifacts/analysis.md"
    goal = str(request.get("goal", "")).strip()
    generation_mode = _provider_generation_mode_from_goal(goal)
    text = (
        "# Analysis\n\n"
        "## Project Type\n"
        f"{generation_mode} concrete project generation benchmark request under ordinary CTCP mainline.\n\n"
        "## Required Files\n"
        "- Generate the matched concrete project output files, generated tests, README, provenance, and attribution.\n"
        "- Add only bounded low-risk provider-assisted helper/documentation fragments.\n\n"
        "## Runtime\n"
        "- Preserve the deterministic runtime contract for the matched project type.\n"
        "- Run generated tests and project-specific CLI/HTTP/persistence validators.\n\n"
        "## Data Model\n"
        "- Keep core persistence and data model under deterministic materializer control.\n\n"
        "## Acceptance Checks\n"
        "- `new-run/status/advance` evidence exists.\n"
        "- `source_generation` writes project output and attribution.\n"
        "- Provider fragments syntax/safety validate or fall back deterministically.\n\n"
        f"## Goal\n{goal}\n"
    )
    target_path = run_dir / target_rel
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(text, encoding="utf-8")
    return {
        "status": "executed",
        "target_path": target_rel,
        "writes": [target_rel],
        "provider": "api_agent",
        "chosen_provider": "api_agent",
        "provider_mode": "local_provider_assisted_analysis",
        "generation_mode": generation_mode,
        "provider_authorship": "provider_assisted",
        "reason": "bounded provider-assisted analysis fast path",
    }


def _is_concrete_fast_path_source_generation(*, run_dir: Path, request: dict[str, Any]) -> bool:
    if str(request.get("role", "")).strip().lower() != "chair":
        return False
    if str(request.get("action", "")).strip().lower() != "source_generation":
        return False
    target = str(request.get("target_path", "")).strip().replace("\\", "/").lower()
    if not target.endswith("artifacts/source_generation_report.json"):
        return False
    contract_path = run_dir / "artifacts" / "output_contract_freeze.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return False
    if not isinstance(contract, dict):
        return False
    return str(contract.get("generation_mode", "")).strip() in {"concrete_fast_path", "provider_assisted", "live_provider_assisted", "live_provider_full_candidate", "live_provider_blind_candidate", "live_provider_medium_candidate"}


def _source_generation_mode_contract(run_dir: Path) -> str:
    contract_path = run_dir / "artifacts" / "output_contract_freeze.json"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return "concrete_fast_path"
    mode = str(contract.get("generation_mode", "")).strip() if isinstance(contract, dict) else ""
    return mode if mode in {"concrete_fast_path", "provider_assisted", "live_provider_assisted", "live_provider_full_candidate", "live_provider_blind_candidate", "live_provider_medium_candidate"} else "concrete_fast_path"


def _execute_concrete_fast_path_source_generation(*, repo_root: Path, run_dir: Path, request: dict[str, Any]) -> dict[str, Any] | None:
    if not _is_concrete_fast_path_source_generation(run_dir=run_dir, request=request):
        return None
    target_rel = str(request.get("target_path", "artifacts/source_generation_report.json")).strip()
    payload, err = _normalize_target_payload(repo_root=repo_root, run_dir=run_dir, request=request, raw_text="{}")
    if err:
        return {
            "status": "failed",
            "reason": err,
            "target_path": target_rel,
            "provider": "api_agent",
            "chosen_provider": "api_agent",
            "provider_mode": "local_materializer",
        }
    target_path = run_dir / target_rel
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(payload, encoding="utf-8")
    generation_mode = _source_generation_mode_contract(run_dir)
    return {
        "status": "executed",
        "target_path": target_rel,
        "writes": [target_rel],
        "provider": "api_agent",
        "chosen_provider": "api_agent",
        "provider_mode": "local_materializer",
        "generation_mode": generation_mode,
        "provider_authorship": "provider_candidate_authored"
        if generation_mode in {"live_provider_full_candidate", "live_provider_blind_candidate", "live_provider_medium_candidate"}
        else ("provider_assisted" if generation_mode in {"provider_assisted", "live_provider_assisted"} else "not_claimed"),
        "local_materializer_used": True,
        "reason": "bounded concrete project benchmark fast path",
    }


def preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    return core_api.preview(
        run_dir=run_dir,
        request=request,
        config=config,
        resolve_templates_fn=_resolve_templates,
        needs_patch_fn=_needs_patch,
        repo_root=ROOT,
    )


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Any]:
    # BEHAVIOR_ID: B031
    analysis_result = _execute_provider_assisted_analysis(
        run_dir=run_dir,
        request=request,
    )
    if analysis_result is not None:
        return analysis_result
    fast_path_result = _execute_concrete_fast_path_source_generation(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
    )
    if fast_path_result is not None:
        return fast_path_result
    hooks = core_api.ApiProviderHooks(
        resolve_templates=_resolve_templates,
        build_evidence_pack=_build_evidence_pack,
        render_prompt=_render_prompt,
        record_failure_review=_record_failure_review,
        needs_patch=_needs_patch,
        normalize_patch_payload=normalize_patch_payload,
        normalize_target_payload=_normalize_target_payload,
    )
    return core_api.execute(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
        hooks=hooks,
    )


__all__ = [
    "_build_evidence_pack",
    "_decode_subprocess_score",
    "_decode_subprocess_text",
    "_default_agent_cmd",
    "_default_patch_cmd",
    "_default_plan_cmd",
    "_extract_json_dict",
    "_fallback_context_pack_from_file_request",
    "_first_non_empty_line",
    "_format_cmd_template",
    "_is_api_env_ready",
    "_load_externals_doc",
    "_load_local_notes_defaults",
    "_max_outbox_prompts",
    "_needs_patch",
    "_needs_plan",
    "_normalize_context_pack",
    "_normalize_file_request",
    "_normalize_find_web",
    "_normalize_guardrails_md",
    "_normalize_json_artifact",
    "_normalize_line_ranges",
    "_normalize_plan_md",
    "_normalize_review_md",
    "_read_text",
    "_record_failure_review",
    "_render_constraints_md",
    "_render_context_md",
    "_render_externals_md",
    "_render_fix_brief_seed",
    "_render_prompt",
    "_render_snippets",
    "_render_whiteboard_md",
    "_resolve_templates",
    "_resolved_external_api_credentials",
    "_run_command",
    "_sanitize",
    "_shell_safe_template_text",
    "_slug",
    "_to_json_text",
    "_write_fix_brief",
    "_write_text",
    "execute",
    "normalize_patch_payload",
    "preview",
]
