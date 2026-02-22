#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_CONFIG_PATH = Path("artifacts") / "dispatch_config.json"
FIND_RESULT_PATH = Path("artifacts") / "find_result.json"
WORKFLOW_INDEX_PATH = ROOT / "workflow_registry" / "index.json"

try:
    from tools.providers import api_agent, codex_agent, local_exec, manual_outbox, mock_agent
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools.providers import api_agent, codex_agent, local_exec, manual_outbox, mock_agent

KNOWN_PROVIDERS = {"manual_outbox", "local_exec", "api_agent", "codex_agent", "mock_agent"}
STEP_META_PATH = Path("step_meta.jsonl")

# BEHAVIOR_ID: B017
BEHAVIOR_ID_STEP_FAIL_TO_FIXER = "B017"
# BEHAVIOR_ID: B018
BEHAVIOR_ID_STEP_CONTEXT_PACK = "B018"
# BEHAVIOR_ID: B019
BEHAVIOR_ID_STEP_REVIEW_CONTRACT = "B019"
# BEHAVIOR_ID: B020
BEHAVIOR_ID_STEP_REVIEW_COST = "B020"
# BEHAVIOR_ID: B021
BEHAVIOR_ID_STEP_PLAN_SIGNED = "B021"
# BEHAVIOR_ID: B022
BEHAVIOR_ID_STEP_FILE_REQUEST = "B022"
# BEHAVIOR_ID: B023
BEHAVIOR_ID_STEP_FIND_WEB = "B023"
# BEHAVIOR_ID: B024
BEHAVIOR_ID_STEP_PATCHMAKER = "B024"
# BEHAVIOR_ID: B025
BEHAVIOR_ID_STEP_FIXER_PATCH = "B025"
# BEHAVIOR_ID: B026
BEHAVIOR_ID_STEP_PLAN_DRAFT_FAMILY = "B026"
# BEHAVIOR_ID: B027
BEHAVIOR_ID_PROVIDER_RESOLUTION = "B027"


def default_dispatch_config_doc(role_defaults: dict[str, str] | None = None) -> dict[str, Any]:
    role_providers: dict[str, str] = {
        "librarian": "local_exec",
    }
    if isinstance(role_defaults, dict):
        for role, provider in role_defaults.items():
            role_providers[str(role).strip().lower()] = _normalize_provider(str(provider))

    return {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": "manual_outbox",
        "role_providers": role_providers,
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


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _forced_provider() -> str:
    raw = str(os.environ.get("CTCP_FORCE_PROVIDER", "")).strip().lower()
    if raw in KNOWN_PROVIDERS:
        return raw
    return ""


def _append_trace(run_dir: Path, text: str) -> None:
    trace = run_dir / "TRACE.md"
    trace.parent.mkdir(parents=True, exist_ok=True)
    with trace.open("a", encoding="utf-8") as fh:
        fh.write(f"- {_now_iso()} | {text}\n")


def _live_provider_violation(
    *,
    run_dir: Path,
    gate: dict[str, str],
    request: dict[str, Any],
    provider: str,
    note: str,
) -> dict[str, Any] | None:
    forced = _forced_provider()
    if forced != "api_agent":
        return None
    if provider == "api_agent":
        return None

    role = str(request.get("role", "")).strip()
    action = str(request.get("action", "")).strip()
    gate_state = str(gate.get("state", "")).strip()
    gate_owner = str(gate.get("owner", "")).strip()
    gate_path = str(gate.get("path", "")).strip()
    detail = (
        "live_api_only_violation: "
        f"gate={gate_state}:{gate_owner}:{gate_path} "
        f"role={role} action={action} provider={provider} expected=api_agent"
    )
    if note:
        detail += f" note={note}"
    _append_trace(run_dir, detail)
    return {
        "status": "provider_mismatch",
        "reason": detail,
        "expected_provider": "api_agent",
        "provider": provider,
        "role": role,
        "action": action,
        "target_path": str(request.get("target_path", "")).strip(),
    }


def _path_exists(run_dir: Path, rel_or_abs: str) -> bool:
    text = str(rel_or_abs or "").strip()
    if not text:
        return False
    p = Path(text)
    if p.is_absolute():
        return p.exists()
    return (run_dir / text).exists()


def _input_statuses(run_dir: Path, request: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in request.get("missing_paths", []):
        path = str(raw or "").strip()
        if not path:
            continue
        rows.append({"path": path, "exists": _path_exists(run_dir, path)})
    return rows


def _output_paths(request: dict[str, Any], result: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        text = str(path or "").strip()
        if not text or text in seen:
            return
        seen.add(text)
        out.append(text)

    add(str(request.get("target_path", "")))
    for key, value in result.items():
        if key.endswith("_path") and isinstance(value, str):
            add(value)
    writes = result.get("writes")
    if isinstance(writes, list):
        for row in writes:
            if isinstance(row, str):
                add(row)
    return out


def _append_step_meta(
    *,
    run_dir: Path,
    gate: dict[str, str],
    request: dict[str, Any],
    provider: str,
    result: dict[str, Any],
) -> None:
    status = str(result.get("status", "")).strip()
    try:
        rc = int(result.get("rc", 0 if status == "executed" else 1))
    except Exception:
        rc = 1 if status != "executed" else 0
    error = str(result.get("reason", "")).strip()
    inputs = _input_statuses(run_dir, request)

    row = {
        "timestamp": _now_iso(),
        "gate": {
            "state": str(gate.get("state", "")).strip(),
            "owner": str(gate.get("owner", "")).strip(),
            "path": str(gate.get("path", "")).strip(),
            "reason": str(gate.get("reason", "")).strip(),
        },
        "role": str(request.get("role", "")).strip(),
        "action": str(request.get("action", "")).strip(),
        "provider": provider,
        "inputs": inputs,
        "inputs_ready": all(bool(x.get("exists")) for x in inputs) if inputs else True,
        "outputs": _output_paths(request, result),
        "status": status,
        "result": "OK" if status == "executed" else "ERR",
        "rc": rc,
        "error": error,
    }
    _append_jsonl(run_dir / STEP_META_PATH, row)


def _selected_workflow_id(run_dir: Path) -> str:
    path = run_dir / FIND_RESULT_PATH
    if not path.exists():
        return ""
    try:
        doc = _read_json(path)
    except Exception:
        return ""
    return str(doc.get("selected_workflow_id", "")).strip()


def _load_recipe_role_providers(run_dir: Path) -> dict[str, str]:
    selected = _selected_workflow_id(run_dir)
    if not selected or not WORKFLOW_INDEX_PATH.exists():
        return {}
    try:
        index = _read_json(WORKFLOW_INDEX_PATH)
    except Exception:
        return {}

    recipe_rel = ""
    for row in index.get("workflows", []):
        if str(row.get("id", "")).strip() == selected:
            recipe_rel = str(row.get("path", "")).strip()
            break
    if not recipe_rel:
        return {}

    recipe_path = (ROOT / recipe_rel).resolve()
    if not recipe_path.exists():
        return {}

    try:
        lines = recipe_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return {}

    providers: dict[str, str] = {}
    in_roles = False
    current_role = ""
    for raw in lines:
        if not raw.strip() or raw.strip().startswith("#"):
            continue
        if not in_roles:
            if raw.strip() == "roles:":
                in_roles = True
            continue

        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if indent == 0:
            break
        if indent == 2 and stripped.endswith(":"):
            current_role = stripped[:-1].strip().lower()
            continue
        if indent >= 4 and stripped.startswith("provider:") and current_role:
            value = stripped.split(":", 1)[1].strip().strip("'").strip('"')
            role = current_role
            if role == "guardian":
                role = "contract_guardian"
            providers[role] = _normalize_provider(value)
    return providers


def ensure_dispatch_config(run_dir: Path) -> Path:
    path = run_dir / DISPATCH_CONFIG_PATH
    if not path.exists():
        _write_json(path, default_dispatch_config_doc(_load_recipe_role_providers(run_dir)))
    return path


def load_dispatch_config(run_dir: Path) -> tuple[dict[str, Any] | None, str]:
    path = run_dir / DISPATCH_CONFIG_PATH
    if not path.exists():
        cfg = default_dispatch_config_doc(_load_recipe_role_providers(run_dir))
        return cfg, "missing dispatch_config; using defaults"

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
    for role, provider in _load_recipe_role_providers(run_dir).items():
        if role not in role_providers:
            role_providers[role] = _normalize_provider(provider)

    budgets = raw.get("budgets", {})
    if not isinstance(budgets, dict):
        budgets = {}
    try:
        max_prompts = int(budgets.get("max_outbox_prompts", 20))
    except Exception:
        max_prompts = 20
    budgets["max_outbox_prompts"] = max(1, max_prompts)

    providers = raw.get("providers", {})
    if not isinstance(providers, dict):
        providers = {}

    cfg = {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": _normalize_provider(str(raw.get("mode", "manual_outbox"))),
        "role_providers": role_providers,
        "budgets": budgets,
        "providers": providers,
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
        # BEHAVIOR_ID: B017
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
        # BEHAVIOR_ID: B018
        role, action, target = "librarian", "context_pack", "artifacts/context_pack.json"
    elif "review_contract.md" in path_l and "review_cost.md" in path_l and "approve reviews" in reason_l:
        # BEHAVIOR_ID: B026
        role, action, target = "chair", "plan_draft", "artifacts/PLAN_draft.md"
    elif "review_contract.md" in path_l:
        # BEHAVIOR_ID: B019
        role, action, target = "contract_guardian", "review_contract", "reviews/review_contract.md"
    elif "review_cost.md" in path_l:
        # BEHAVIOR_ID: B020
        role, action, target = "cost_controller", "review_cost", "reviews/review_cost.md"
    elif "plan_draft.md" in path_l:
        # BEHAVIOR_ID: B026
        role, action, target = "chair", "plan_draft", "artifacts/PLAN_draft.md"
    elif "plan.md" in path_l:
        # BEHAVIOR_ID: B021
        role, action, target = "chair", "plan_signed", "artifacts/PLAN.md"
    elif "file_request.json" in path_l:
        # BEHAVIOR_ID: B022
        role, action, target = "chair", "file_request", "artifacts/file_request.json"
    elif "find_web.json" in path_l or "externals_pack.json" in path_l:
        # BEHAVIOR_ID: B023
        role, action, target = "researcher", "find_web", "artifacts/find_web.json"
    elif "analysis.md" in path_l:
        # BEHAVIOR_ID: B026
        role, action, target = "chair", "plan_draft", "artifacts/analysis.md"
    elif "guardrails.md" in path_l:
        # BEHAVIOR_ID: B026
        role, action, target = "chair", "plan_draft", "artifacts/guardrails.md"
    elif "diff.patch" in path_l:
        if owner == "fixer":
            # BEHAVIOR_ID: B025
            role, action, target = "fixer", "fix_patch", "artifacts/diff.patch"
        else:
            # BEHAVIOR_ID: B024
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
    # BEHAVIOR_ID: B027
    role_providers = config.get("role_providers", {})
    if not isinstance(role_providers, dict):
        role_providers = {}
    provider = _normalize_provider(str(role_providers.get(role, config.get("mode", "manual_outbox"))))
    if provider == "local_exec" and role not in {"librarian", "contract_guardian"}:
        if role in {"patchmaker", "fixer"}:
            return (
                "api_agent",
                "local_exec restricted to librarian/contract_guardian; fallback to api_agent",
            )
        return (
            "manual_outbox",
            "local_exec restricted to librarian/contract_guardian; fallback to manual_outbox",
        )
    if provider == "manual_outbox" and role in {"patchmaker", "fixer"}:
        return (
            "api_agent",
            "manual_outbox disabled for patchmaker/fixer; fallback to api_agent",
        )
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
    elif provider == "api_agent":
        preview = api_agent.preview(run_dir=run_dir, request=request, config=config)
    elif provider == "codex_agent":
        preview = codex_agent.preview(run_dir=run_dir, request=request, config=config)
    elif provider == "mock_agent":
        preview = mock_agent.preview(run_dir=run_dir, request=request, config=config)
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
    # BEHAVIOR_ID: B027
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
    elif provider == "api_agent":
        result = api_agent.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=_parse_guardrails_budgets(run_dir),
        )
    elif provider == "codex_agent":
        result = codex_agent.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=_parse_guardrails_budgets(run_dir),
        )
    elif provider == "mock_agent":
        result = mock_agent.execute(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            config=config,
            guardrails_budgets=_parse_guardrails_budgets(run_dir),
        )
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
