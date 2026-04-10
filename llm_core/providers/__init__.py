from __future__ import annotations

KNOWN_PROVIDERS = {
    "manual_outbox",
    "ollama_agent",
    "api_agent",
    "codex_agent",
    "mock_agent",
    "local_exec",
}


def preview_provider(*args, **kwargs):
    from .runtime import preview_provider as _preview_provider

    return _preview_provider(*args, **kwargs)


def execute_provider(*args, **kwargs):
    from .runtime import execute_provider as _execute_provider

    return _execute_provider(*args, **kwargs)


__all__ = [
    "KNOWN_PROVIDERS",
    "execute_provider",
    "preview_provider",
]
