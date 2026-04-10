from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from llm_core.dispatch.router import normalize_provider

ROOT = Path(__file__).resolve().parents[1]
DISPATCH_CONFIG_PATH = Path("artifacts") / "dispatch_config.json"
FIND_RESULT_PATH = Path("artifacts") / "find_result.json"
WORKFLOW_INDEX_PATH = ROOT / "workflow_registry" / "index.json"
HARD_ROLE_PROVIDERS = {
    "librarian": "ollama_agent",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_dispatch_config_doc(role_defaults: dict[str, str] | None = None) -> dict[str, Any]:
    role_providers: dict[str, str] = dict(HARD_ROLE_PROVIDERS)
    if isinstance(role_defaults, dict):
        for role, provider in role_defaults.items():
            key = str(role).strip().lower()
            if key in HARD_ROLE_PROVIDERS:
                continue
            role_providers[key] = normalize_provider(str(provider))
    return {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": "api_agent",
        "role_providers": role_providers,
        "budgets": {"max_outbox_prompts": 20},
    }


def _apply_hard_role_providers(role_providers: dict[str, str], *, mode: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(role_providers, dict):
        for role, provider in role_providers.items():
            out[str(role).strip().lower()] = normalize_provider(str(provider))
    if str(mode).strip().lower() == "mock_agent":
        return out
    for role, provider in HARD_ROLE_PROVIDERS.items():
        out[role] = provider
    return out


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
            role = "contract_guardian" if current_role == "guardian" else current_role
            providers[role] = normalize_provider(value)
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

    mode = normalize_provider(str(raw.get("mode", "api_agent")))
    role_providers_raw = raw.get("role_providers", {})
    role_providers: dict[str, str] = {}
    if isinstance(role_providers_raw, dict):
        for key, value in role_providers_raw.items():
            role_providers[str(key).strip().lower()] = normalize_provider(str(value))
    for role, provider in _load_recipe_role_providers(run_dir).items():
        if role not in role_providers:
            role_providers[role] = normalize_provider(provider)
    role_providers = _apply_hard_role_providers(role_providers, mode=mode)

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

    return {
        "schema_version": "ctcp-dispatch-config-v1",
        "mode": mode,
        "role_providers": role_providers,
        "budgets": budgets,
        "providers": providers,
    }, "ok"


def parse_guardrails_budgets(run_dir: Path) -> dict[str, str]:
    path = run_dir / "artifacts" / "guardrails.md"
    if not path.exists():
        return {"max_files": "", "max_total_bytes": "", "max_iterations": ""}
    out = {"max_files": "", "max_total_bytes": "", "max_iterations": ""}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*$", line)
        if not match:
            continue
        key = match.group(1).strip().lower()
        if key in out:
            out[key] = match.group(2).strip()
    return out


def _split_missing_paths(path_value: str) -> list[str]:
    parts = [x.strip() for x in re.split(r"[|,]", path_value or "") if x.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for path in parts:
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def _merge_missing_paths(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for raw in group:
            value = str(raw or "").strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
    return out


def _gate_owner(owner: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(owner or "").strip().lower()).strip("_")


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
    elif "output_contract_freeze.json" in path_l:
        role, action, target = "chair", "output_contract_freeze", "artifacts/output_contract_freeze.json"
    elif "source_generation_report.json" in path_l:
        role, action, target = "chair", "source_generation", "artifacts/source_generation_report.json"
    elif "docs_generation_report.json" in path_l:
        role, action, target = "chair", "docs_generation", "artifacts/docs_generation_report.json"
    elif "workflow_generation_report.json" in path_l:
        role, action, target = "chair", "workflow_generation", "artifacts/workflow_generation_report.json"
    elif "project_manifest.json" in path_l:
        role, action, target = "chair", "artifact_manifest_build", "artifacts/project_manifest.json"
    elif "deliverable_index.json" in path_l:
        role, action, target = "chair", "deliver", "artifacts/deliverable_index.json"
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
        "missing_paths": (
            _merge_missing_paths(["failure_bundle.zip"], _split_missing_paths(path_value))
            if role == "fixer"
            else _split_missing_paths(path_value)
        ),
        "reason": reason,
        "goal": goal,
    }
