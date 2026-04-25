#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_NOTES_PATH = ROOT / ".agent_private" / "NOTES.md"
EMBEDDED_BASE_URL = "https://api.gptsapi.net/v1"
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
            return replacement_key, env_base_url or ctcp_base_url or notes_base_url
        return key, env_base_url or ctcp_base_url
    if not key:
        key = ctcp_key or notes_key
    base_url = env_base_url or ctcp_base_url or notes_base_url or EMBEDDED_BASE_URL
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
