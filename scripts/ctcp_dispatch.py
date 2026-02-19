#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_CONFIG_PATH = Path("artifacts") / "dispatch_config.json"

try:
    from tools.providers import local_exec, manual_outbox
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools.providers import local_exec, manual_outbox

KNOWN_PROVIDERS = {"manual_outbox", "local_exec"}


def default_dispatch_config_doc() -> dict[str, Any]:
    return {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": "manual_outbox",
        "role_providers": {
            "librarian": "local_exec",
            "chair": "manual_outbox",
            "contract_guardian": "manual_outbox",
            "cost_controller": "manual_outbox",
            "patchmaker": "manual_outbox",
            "fixer": "manual_outbox",
            "researcher": "manual_outbox",
        },
        "budgets": {"max_outbox_prompts": 20},
    }


def _normalize_provider(value: str) -> str:
    text = (value or "").strip().lower()
    if text in KNOWN_PROVIDERS:
        return text
    return "manual_outbox"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_dispatch_config(run_dir: Path) -> Path:
    path = run_dir / DISPATCH_CONFIG_PATH
    if not path.exists():
        _write_json(path, default_dispatch_config_doc())
    return path


def load_dispatch_config(run_dir: Path) -> tuple[dict[str, Any] | None, str]:
    path = run_dir / DISPATCH_CONFIG_PATH
    if not path.exists():
        return None, "missing artifacts/dispatch_config.json"

    try:
        raw = _read_json(path)
    except Exception as exc:
        return None, f"invalid dispatch_config json: {exc}"

    if not isinstance(raw, dict):
        return None, "dispatch_config must be object"

    if raw.get("schema_version") != "ctcp-dispatch-config-v1":
        return None, "dispatch_config schema_version must be ctcp-dispatch-config-v1"

    role_providers_raw = raw.get("role_providers", {})
    role_providers: dict[str, str] = {}
    if isinstance(role_providers_raw, dict):
        for k, v in role_providers_raw.items():
            role_providers[str(k).strip().lower()] = _normalize_provider(str(v))

    budgets = raw.get("budgets", {})
    if not isinstance(budgets, dict):
        budgets = {}
    try:
        max_prompts = int(budgets.get("max_outbox_prompts", 20))
    except Exception:
        max_prompts = 20
    budgets["max_outbox_prompts"] = max(1, max_prompts)

    cfg = {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": _normalize_provider(str(raw.get("mode", "manual_outbox"))),
        "role_providers": role_providers,
        "budgets": budgets,
    }
    return cfg, "ok"


def _parse_guardrails_budgets(run_dir: Path) -> dict[str, str]:
    path = run_dir / "artifacts" / "guardrails.md"
    if not path.exists():
        return {"max_files": "", "max_total_bytes": "", "max_iterations": ""}
    out = {"max_files": "", "max_total_bytes": "", "max_iterations": ""}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        key = m.group(1).strip().lower()
        if key in out:
            out[key] = m.group(2).strip()
    return out


def _split_missing_paths(path_value: str) -> list[str]:
    parts = [x.strip() for x in re.split(r"[|,]", path_value or "") if x.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _gate_owner(owner: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (owner or "").strip().lower()).strip("_")


def derive_request(gate: dict[str, str], run_doc: dict[str, Any]) -> dict[str, Any] | None:
    state = str(gate.get("state", "")).strip().lower()
    owner = _gate_owner(str(gate.get("owner", "")))
    path_value = str(gate.get("path", "")).strip()
    reason = str(gate.get("reason", "")).strip()
    path_l = path_value.lower()
    reason_l = reason.lower()
    goal = str(run_doc.get("goal", "")).strip()

    if state == "fail":
        return {
            "role": "fixer",
            "action": "fix_patch",
            "target_path": "artifacts/diff.patch",
            "missing_paths": ["failure_bundle.zip", "artifacts/diff.patch"],
            "reason": reason or "verify failed; fix required",
            "goal": goal,
        }

    if state != "blocked":
        return None

    if "context_pack.json" in path_l:
        role, action, target = "librarian", "context_pack", "artifacts/context_pack.json"
    elif "review_contract.md" in path_l and "review_cost.md" in path_l and "approve reviews" in reason_l:
        role, action, target = "chair", "plan_draft", "artifacts/PLAN_draft.md"
    elif "review_contract.md" in path_l:
        role, action, target = "contract_guardian", "review_contract", "reviews/review_contract.md"
    elif "review_cost.md" in path_l:
        role, action, target = "cost_controller", "review_cost", "reviews/review_cost.md"
    elif "plan_draft.md" in path_l:
        role, action, target = "chair", "plan_draft", "artifacts/PLAN_draft.md"
    elif "plan.md" in path_l:
        role, action, target = "chair", "plan_signed", "artifacts/PLAN.md"
    elif "file_request.json" in path_l:
        role, action, target = "chair", "file_request", "artifacts/file_request.json"
    elif "find_web.json" in path_l or "externals_pack.json" in path_l:
        role, action, target = "researcher", "find_web", "artifacts/find_web.json"
    elif "analysis.md" in path_l:
        role, action, target = "chair", "plan_draft", "artifacts/analysis.md"
    elif "guardrails.md" in path_l:
        role, action, target = "chair", "plan_draft", "artifacts/guardrails.md"
    elif "diff.patch" in path_l:
        if owner == "fixer":
            role, action, target = "fixer", "fix_patch", "artifacts/diff.patch"
        else:
            role, action, target = "patchmaker", "make_patch", "artifacts/diff.patch"
    else:
        return None

    return {
        "role": role,
        "action": action,
        "target_path": target,
        "missing_paths": _split_missing_paths(path_value),
        "reason": reason,
        "goal": goal,
    }


def _resolve_provider(config: dict[str, Any], role: str) -> tuple[str, str]:
    role_providers = config.get("role_providers", {})
    if not isinstance(role_providers, dict):
        role_providers = {}
    provider = _normalize_provider(str(role_providers.get(role, config.get("mode", "manual_outbox"))))
    if provider == "local_exec" and role != "librarian":
        return "manual_outbox", "local_exec restricted to librarian; fallback to manual_outbox"
    return provider, ""


def dispatch_preview(run_dir: Path, run_doc: dict[str, Any], gate: dict[str, str]) -> dict[str, Any]:
    config, cfg_msg = load_dispatch_config(run_dir)
    if config is None:
        return {"status": "disabled", "reason": cfg_msg}

    request = derive_request(gate, run_doc)
    if request is None:
        return {"status": "no_request"}

    provider, note = _resolve_provider(config, str(request["role"]))
    preview: dict[str, Any]
    if provider == "manual_outbox":
        preview = manual_outbox.preview(run_dir=run_dir, request=request, config=config)
    elif provider == "local_exec":
        preview = {"status": "can_exec"}
    else:
        preview = {"status": "unsupported_provider", "reason": provider}

    preview["provider"] = provider
    preview["role"] = request["role"]
    preview["action"] = request["action"]
    preview["target_path"] = request["target_path"]
    if note:
        preview["note"] = note
    return preview


def dispatch_once(run_dir: Path, run_doc: dict[str, Any], gate: dict[str, str], repo_root: Path) -> dict[str, Any]:
    config, cfg_msg = load_dispatch_config(run_dir)
    if config is None:
        return {"status": "disabled", "reason": cfg_msg}

    request = derive_request(gate, run_doc)
    if request is None:
        return {"status": "no_request"}

    provider, note = _resolve_provider(config, str(request["role"]))
    if provider == "manual_outbox":
        result = manual_outbox.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=_parse_guardrails_budgets(run_dir),
        )
    elif provider == "local_exec":
        result = local_exec.execute(repo_root=repo_root, run_dir=run_dir, request=request)
    else:
        result = {"status": "unsupported_provider", "reason": provider}

    result["provider"] = provider
    result["role"] = request["role"]
    result["action"] = request["action"]
    result["target_path"] = request["target_path"]
    if note:
        result["note"] = note
    return result


def _read_events(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "events.jsonl"
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except Exception:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def latest_outbox_prompt_path(run_dir: Path) -> str:
    events = _read_events(run_dir)
    for row in reversed(events):
        if str(row.get("event", "")) == "OUTBOX_PROMPT_CREATED":
            return str(row.get("path", ""))
    return ""


def detect_fulfilled_prompts(run_dir: Path) -> list[dict[str, str]]:
    events = _read_events(run_dir)
    created: list[dict[str, str]] = []
    already: set[str] = set()

    for row in events:
        event = str(row.get("event", ""))
        if event == "OUTBOX_PROMPT_CREATED":
            prompt_path = str(row.get("path", "")).strip()
            target_path = str(row.get("target_path", "")).strip()
            role = str(row.get("role", "")).strip()
            if prompt_path and target_path:
                created.append({"prompt_path": prompt_path, "target_path": target_path, "role": role})
        elif event == "OUTBOX_PROMPT_FULFILLED":
            key = str(row.get("path", "")).strip()
            if key:
                already.add(key)

    todo: list[dict[str, str]] = []
    for row in created:
        if row["prompt_path"] in already:
            continue
        if (run_dir / row["target_path"]).exists():
            todo.append(row)
    return todo

