from __future__ import annotations

import os
from typing import Any

VALID_PROVIDERS = {"disabled", "fixture", "external"}


def selected_provider_name() -> str:
    raw = str(os.environ.get("CTCP_AGENT_WEB_PROVIDER", "disabled")).strip().lower()
    return raw if raw in VALID_PROVIDERS else "disabled"


def _provider_module():
    provider = selected_provider_name()
    if provider == "fixture":
        from . import runtime_web_fixture_provider as module
        return provider, module
    if provider == "external":
        from . import runtime_web_http_provider as module
        return provider, module
    raise RuntimeError("web_provider_unavailable")


def _with_provider(output: dict[str, Any], provider: str) -> dict[str, Any]:
    if isinstance(output, dict):
        output.setdefault("provider", provider)
    return output


def execute_web_search(tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    provider, module = _provider_module()
    return _with_provider(module.execute_web_search(tool_input, context), provider)


def execute_fetch_url(tool_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    provider, module = _provider_module()
    return _with_provider(module.execute_fetch_url(tool_input, context), provider)
