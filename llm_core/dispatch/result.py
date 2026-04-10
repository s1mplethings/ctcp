from __future__ import annotations

from pathlib import Path
from typing import Any


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def provider_mode(provider: str) -> str:
    value = str(provider or "").strip().lower()
    if value in {"ollama_agent", "local_exec"}:
        return "local"
    if value in {"api_agent", "codex_agent"}:
        return "remote"
    if value == "manual_outbox":
        return "manual"
    if value == "mock_agent":
        return "mock"
    return "unknown"


def apply_dispatch_evidence(payload: dict[str, Any], *, request: dict[str, Any], provider: str, note: str) -> dict[str, Any]:
    role = str(request.get("role", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    payload["provider"] = payload["chosen_provider"] = provider
    payload["provider_mode"] = str(payload.get("provider_mode", "")).strip() or provider_mode(provider)
    model_name = str(payload.get("model_name", "")).strip() or str(payload.get("ollama_model", "")).strip()
    if model_name:
        payload["model_name"] = model_name
    if role == "librarian" and action == "context_pack":
        payload["provider_mode"] = "local"
        payload["fallback_blocked"] = bool(payload.get("fallback_blocked", False)) or bool(str(note).strip())
    return payload


def normalize_executed_target_result(run_dir: Path, request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if str(result.get("status", "")).strip() != "executed":
        return result
    target_rel = str(request.get("target_path", "")).strip()
    target_abs = (run_dir / target_rel).resolve()
    if _is_within(target_abs, run_dir) and target_abs.exists():
        return result
    return {
        **result,
        "status": "exec_failed",
        "reason": f"provider reported executed but target missing: {target_rel}",
        "error_code": "target_missing",
    }


def normalize_dispatch_result(run_dir: Path, request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return normalize_executed_target_result(run_dir=run_dir, request=request, result=result)
