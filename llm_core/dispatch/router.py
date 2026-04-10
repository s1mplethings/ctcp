from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from llm_core.dispatch.result import apply_dispatch_evidence, normalize_dispatch_result

KNOWN_PROVIDERS = {"manual_outbox", "ollama_agent", "api_agent", "codex_agent", "mock_agent", "local_exec"}


def normalize_provider(value: str) -> str:
    text = str(value or "").strip().lower()
    if text in KNOWN_PROVIDERS:
        return text
    return "manual_outbox"


def resolve_provider(
    config: dict[str, Any],
    role: str,
    action: str,
    *,
    force_provider: str = "",
    hard_role_providers: dict[str, str] | None = None,
) -> tuple[str, str]:
    role_name = str(role or "").strip().lower()
    action_name = str(action or "").strip().lower()
    forced = normalize_provider(force_provider) if str(force_provider or "").strip() else ""
    locked_roles = {str(k).strip().lower(): normalize_provider(str(v)) for k, v in dict(hard_role_providers or {}).items()}
    hard_provider = locked_roles.get(role_name, "")
    mode_norm = str(config.get("mode", "")).strip().lower()
    if forced:
        if hard_provider:
            if forced != hard_provider:
                return (
                    hard_provider,
                    f"ignored CTCP_FORCE_PROVIDER={forced} for hard-local role={role_name}; using {hard_provider}",
                )
            return hard_provider, f"forced provider matches hard-local role={role_name}"
        return forced, f"forced by CTCP_FORCE_PROVIDER={forced}"

    role_providers = config.get("role_providers", {})
    if not isinstance(role_providers, dict):
        role_providers = {}
    provider = normalize_provider(str(role_providers.get(role_name, config.get("mode", "manual_outbox"))))
    if (role_name, action_name) == ("librarian", "context_pack"):
        if mode_norm == "mock_agent":
            return provider, ""
        locked = hard_provider or "ollama_agent"
        if provider != locked:
            return (
                locked,
                f"blocked configured provider={provider or 'unknown'} for hard-local-model role={role_name}; using {locked}",
            )
        return locked, ""
    if provider == "local_exec" and (role_name, action_name) != ("librarian", "context_pack"):
        return "api_agent", "local_exec restricted to librarian/context_pack; fallback to api_agent"
    if provider == "ollama_agent" and role_name != "librarian":
        return "api_agent", "ollama_agent restricted to librarian/context_pack; fallback to api_agent"
    return provider, ""


def dispatch_preview(
    *,
    request: dict[str, Any],
    config: dict[str, Any],
    run_dir: Path,
    preview_provider: Callable[..., dict[str, Any]],
    force_provider: str = "",
    hard_role_providers: dict[str, str] | None = None,
    live_policy: Callable[..., dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    provider, note = resolve_provider(
        config,
        str(request.get("role", "")),
        str(request.get("action", "")),
        force_provider=force_provider,
        hard_role_providers=hard_role_providers,
    )
    if live_policy is not None:
        violation = live_policy(
            run_dir=run_dir,
            request=request,
            provider=provider,
            note=note,
        )
        if violation is not None:
            if note:
                violation["note"] = note
            return apply_dispatch_evidence(violation, request=request, provider=provider, note=note)

    preview = preview_provider(provider, run_dir=run_dir, request=request, config=config)
    preview["role"] = request.get("role", "")
    preview["action"] = request.get("action", "")
    preview["target_path"] = request.get("target_path", "")
    if note:
        preview["note"] = note
    return apply_dispatch_evidence(preview, request=request, provider=provider, note=note)


def dispatch_execute(
    *,
    request: dict[str, Any],
    config: dict[str, Any],
    run_dir: Path,
    repo_root: Path,
    execute_provider: Callable[..., dict[str, Any]],
    guardrails_budgets: dict[str, str] | None = None,
    force_provider: str = "",
    hard_role_providers: dict[str, str] | None = None,
    live_policy: Callable[..., dict[str, Any] | None] | None = None,
) -> dict[str, Any]:
    provider, note = resolve_provider(
        config,
        str(request.get("role", "")),
        str(request.get("action", "")),
        force_provider=force_provider,
        hard_role_providers=hard_role_providers,
    )
    if live_policy is not None:
        violation = live_policy(
            run_dir=run_dir,
            request=request,
            provider=provider,
            note=note,
        )
        if violation is not None:
            if note:
                violation["note"] = note
            return apply_dispatch_evidence(violation, request=request, provider=provider, note=note)

    result = execute_provider(
        provider,
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=dict(guardrails_budgets or {}),
    )
    normalized = normalize_dispatch_result(run_dir=run_dir, request=request, result=result)
    normalized["role"] = request.get("role", "")
    normalized["action"] = request.get("action", "")
    normalized["target_path"] = request.get("target_path", "")
    if note:
        normalized["note"] = note
    return apply_dispatch_evidence(normalized, request=request, provider=provider, note=note)
