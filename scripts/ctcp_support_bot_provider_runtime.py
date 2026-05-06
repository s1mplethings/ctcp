#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from scripts.ctcp_support_bot_constants import PRIMARY_SUPPORT_PROVIDER
from scripts.ctcp_support_bot_io import append_jsonl, append_log, append_trace, now_iso
from scripts.ctcp_support_bot_provider import _default_support_openai_model, _normalize_support_openai_model

try:
    from llm_core.providers import runtime as provider_runtime
except ModuleNotFoundError:
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from llm_core.providers import runtime as provider_runtime


def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def _host_attr(name: str) -> Any:
    module = _support_bot_host_module()
    return getattr(module, name, None) if module is not None else None


def _repo_root() -> Path:
    root = _host_attr("ROOT")
    return root if isinstance(root, Path) else Path(__file__).resolve().parents[1]


def _provider_runtime_facade() -> Any:
    return _host_attr("provider_runtime") or provider_runtime


@contextmanager
def _with_env_overrides(values: dict[str, str]):
    sentinel = object()
    previous: dict[str, Any] = {}
    for key, value in values.items():
        previous[key] = os.environ.get(key, sentinel)
        os.environ[key] = str(value)
    try:
        yield
    finally:
        for key, old in previous.items():
            if old is sentinel:
                os.environ.pop(key, None)
            else:
                os.environ[key] = str(old)


def execute_provider(
    *,
    provider: str,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    provider_name = str(provider or "").strip().lower()
    role = str(request.get("role", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    support_api_request = provider_name == PRIMARY_SUPPORT_PROVIDER and role == "support_lead" and action == "reply"

    support_model = ""
    overrides: dict[str, str] = {}
    if support_api_request:
        providers = config.get("providers", {}) if isinstance(config, dict) else {}
        api_cfg: dict[str, Any] = {}
        if isinstance(providers, dict):
            raw_api_cfg = providers.get("api_agent", {})
            if isinstance(raw_api_cfg, dict):
                api_cfg = raw_api_cfg
        support_model = _normalize_support_openai_model(
            str(api_cfg.get("support_model", "")).strip()
            or str(api_cfg.get("model", "")).strip()
            or _default_support_openai_model()
        )
        overrides = {
            "SDDAI_OPENAI_AGENT_MODEL": support_model,
            "SDDAI_OPENAI_MODEL": support_model,
        }

    facade = _provider_runtime_facade()
    if overrides:
        with _with_env_overrides(overrides):
            result = facade.execute_provider(
                provider,
                repo_root=_repo_root(),
                run_dir=run_dir,
                request=request,
                config=config,
                guardrails_budgets={},
            )
    else:
        result = facade.execute_provider(
            provider,
            repo_root=_repo_root(),
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets={},
        )

    if support_model and isinstance(result, dict):
        result.setdefault("model_name", support_model)
    return result


def _tail_text(path: Path, max_lines: int = 24, max_chars: int = 3000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln.strip()]
    payload = "\n".join(lines[-max(1, max_lines) :])
    return payload[-max_chars:] if len(payload) > max_chars else payload


def log_provider_result(run_dir: Path, provider: str, result: dict[str, Any], label: str) -> None:
    row = {
        "ts": now_iso(),
        "label": label,
        "provider": provider,
        "status": str(result.get("status", "")),
        "reason": str(result.get("reason", "")),
        "cmd": str(result.get("cmd", "")),
        "rc": int(result.get("rc", 0) or 0),
        "stdout_log": str(result.get("stdout_log", "")),
        "stderr_log": str(result.get("stderr_log", "")),
        "prompt_path": str(result.get("prompt_path", "")),
        "target_path": str(result.get("target_path", "")),
    }
    append_jsonl(run_dir / "logs" / "support_bot.provider.log", row)

    for key, sink in (("stdout_log", "support_bot.stdout.log"), ("stderr_log", "support_bot.stderr.log")):
        rel = str(result.get(key, "")).strip()
        if not rel:
            continue
        tail = _tail_text(run_dir / rel)
        if not tail:
            continue
        append_log(run_dir / "logs" / sink, f"[{now_iso()}] {label} provider={provider} {key}={rel}\n{tail}\n\n")

    append_trace(run_dir, f"provider_{label} provider={provider} status={row['status']}")


def read_json_doc(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    return doc if isinstance(doc, dict) else None


__all__ = [
    "execute_provider",
    "_tail_text",
    "log_provider_result",
    "read_json_doc",
]
