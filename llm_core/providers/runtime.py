from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

try:
    from tools.providers import api_agent, codex_agent, local_exec, manual_outbox, mock_agent, ollama_agent
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.providers import api_agent, codex_agent, local_exec, manual_outbox, mock_agent, ollama_agent

KNOWN_PROVIDERS = {
    "manual_outbox",
    "ollama_agent",
    "api_agent",
    "codex_agent",
    "mock_agent",
    "local_exec",
}


def preview_provider(
    provider: str,
    *,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    name = str(provider or "").strip().lower()
    if name == "manual_outbox":
        return manual_outbox.preview(run_dir=run_dir, request=request, config=config)
    if name == "local_exec":
        return {"status": "can_execute_local"}
    if name == "ollama_agent":
        return ollama_agent.preview(run_dir=run_dir, request=request, config=config)
    if name == "api_agent":
        return api_agent.preview(run_dir=run_dir, request=request, config=config)
    if name == "codex_agent":
        return codex_agent.preview(run_dir=run_dir, request=request, config=config)
    if name == "mock_agent":
        return mock_agent.preview(run_dir=run_dir, request=request, config=config)
    return {"status": "unsupported_provider", "reason": provider}


def execute_provider(
    provider: str,
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str] | None = None,
) -> dict[str, Any]:
    budgets = dict(guardrails_budgets or {})
    name = str(provider or "").strip().lower()
    if name == "manual_outbox":
        return manual_outbox.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=budgets,
        )
    if name == "local_exec":
        return local_exec.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
        )
    if name == "ollama_agent":
        return ollama_agent.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=budgets,
        )
    if name == "api_agent":
        return api_agent.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=budgets,
        )
    if name == "codex_agent":
        return codex_agent.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=budgets,
        )
    if name == "mock_agent":
        return mock_agent.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=budgets,
        )
    return {
        "status": "exec_failed",
        "reason": f"unsupported provider: {provider}",
    }
