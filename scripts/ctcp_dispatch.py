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
SUPPORT_WHITEBOARD_REL = Path("artifacts") / "support_whiteboard.json"
SUPPORT_WHITEBOARD_LOG_REL = Path("artifacts") / "support_whiteboard.md"
SUPPORT_WHITEBOARD_SCHEMA_VERSION = "ctcp-support-whiteboard-v1"

try:
    from ctcp_adapters import dispatch_request_mapper, dispatch_whiteboard
    from llm_core.dispatch import router as core_router
    from llm_core.providers import runtime as provider_runtime
    from tools import local_librarian
    from tools.dispatch_result_contract import apply_dispatch_evidence, normalize_executed_target_result, provider_mode
    from tools.formal_api_lock import append_provider_ledger, formal_api_only_enabled, requires_formal_api
    from tools.run_manifest import update_whiteboard_state
    from tools.providers import api_agent, codex_agent, local_exec, manual_outbox, mock_agent, ollama_agent
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from ctcp_adapters import dispatch_request_mapper, dispatch_whiteboard
    from llm_core.dispatch import router as core_router
    from llm_core.providers import runtime as provider_runtime
    from tools import local_librarian
    from tools.dispatch_result_contract import apply_dispatch_evidence, normalize_executed_target_result, provider_mode
    from tools.formal_api_lock import append_provider_ledger, formal_api_only_enabled, requires_formal_api
    from tools.run_manifest import update_whiteboard_state
    from tools.providers import api_agent, codex_agent, local_exec, manual_outbox, mock_agent, ollama_agent

KNOWN_PROVIDERS = {"manual_outbox", "ollama_agent", "api_agent", "codex_agent", "mock_agent", "local_exec"}
STEP_META_PATH = Path("step_meta.jsonl")
HARD_ROLE_PROVIDERS = {
    "librarian": "api_agent",
    "chair": "api_agent",
    "contract_guardian": "api_agent",
    "cost_controller": "api_agent",
    "researcher": "api_agent",
    "patchmaker": "api_agent",
    "fixer": "api_agent",
}

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
    return dispatch_request_mapper.default_dispatch_config_doc(role_defaults)
def _normalize_provider(value: str) -> str:
    return core_router.normalize_provider(value)

def _apply_hard_role_providers(role_providers: dict[str, str], *, mode: str) -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(role_providers, dict):
        for role, provider in role_providers.items():
            out[str(role).strip().lower()] = _normalize_provider(str(provider))
    mode_norm = str(mode).strip().lower()
    if mode_norm == "mock_agent":
        return out
    for role, provider in HARD_ROLE_PROVIDERS.items():
        out[role] = provider
    return out

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

def _sanitize(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "item"

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

def _brief_text(value: str, *, max_chars: int = 260) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    limit = max(8, int(max_chars))
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."

def _safe_whiteboard_hits(rows: Any, *, max_items: int = 5) -> list[dict[str, Any]]:
    """Sanitize and limit librarian search hits for whiteboard storage.

    WHITEBOARD HELPER: Validates and truncates hit arrays to prevent whiteboard bloat
    CALLED BY: record_support_turn_whiteboard(), _prepare_dispatch_whiteboard_context(), _compact_whiteboard_snapshot()

    Returns list of dicts with path, start_line, snippet (max 5 items by default).
    """
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    for item in rows:
        if not isinstance(item, dict):
            continue
        path = _brief_text(str(item.get("path", "")), max_chars=240)
        if not path:
            continue
        try:
            start_line = max(1, int(item.get("start_line", 1) or 1))
        except Exception:
            start_line = 1
        out.append(
            {
                "path": path,
                "start_line": start_line,
                "snippet": _brief_text(str(item.get("snippet", "")), max_chars=220),
            }
        )
        if len(out) >= max(1, int(max_items)):
            break
    return out


def _safe_whiteboard_entries(rows: Any, *, max_items: int = 120) -> list[dict[str, Any]]:
    """Sanitize and limit whiteboard entries to prevent unbounded growth.

    WHITEBOARD HELPER: Validates, truncates, and normalizes entry arrays (max 120 by default)
    CALLED BY: All whiteboard read/write functions to enforce size limits and data consistency

    Returns list of normalized entry dicts with ts, role, kind, text, optional query/hits.
    """
    out: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return out
    limit = max(1, int(max_items))
    for item in rows[-limit:]:
        if not isinstance(item, dict):
            continue
        role = _brief_text(str(item.get("role", "")).lower(), max_chars=32) or "unknown"
        kind = _brief_text(str(item.get("kind", "")).lower(), max_chars=48) or "note"
        entry: dict[str, Any] = {
            "ts": _brief_text(str(item.get("ts", _now_iso())), max_chars=40),
            "role": role,
            "kind": kind,
            "text": _brief_text(str(item.get("text", "")), max_chars=260),
        }
        query = _brief_text(str(item.get("query", "")), max_chars=220)
        question = _brief_text(str(item.get("question", "")), max_chars=220)
        if query:
            entry["query"] = query
        if question:
            entry["question"] = question
        hits = _safe_whiteboard_hits(item.get("hits"), max_items=5)
        if hits:
            entry["hits"] = hits
            entry["hit_count"] = len(hits)
        out.append(entry)
    return out


def _load_support_whiteboard(run_dir: Path) -> dict[str, Any]:
    """Load support whiteboard from run directory.

    WHITEBOARD READ: Loads ${run_dir}/artifacts/support_whiteboard.json
    CONSUMED BY: get_support_whiteboard_context() → ctcp_front_bridge → ctcp_support_bot

    Returns dict with schema_version and entries array (max 120 items).
    """
    path = run_dir / SUPPORT_WHITEBOARD_REL
    state: dict[str, Any] = {
        "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
        "entries": [],
    }
    if not path.exists():
        return state
    try:
        doc = _read_json(path)
    except Exception:
        return state
    if not isinstance(doc, dict):
        return state
    state["entries"] = _safe_whiteboard_entries(doc.get("entries", []), max_items=120)
    return state


def _save_support_whiteboard(run_dir: Path, state: dict[str, Any]) -> None:
    """Save support whiteboard to run directory.

    WHITEBOARD WRITE: Writes to ${run_dir}/artifacts/support_whiteboard.json
    CALLED BY: record_support_turn_whiteboard(), _append_dispatch_result_whiteboard()
    """
    payload = {
        "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
        "entries": _safe_whiteboard_entries((state or {}).get("entries", []), max_items=120),
    }
    _write_json(run_dir / SUPPORT_WHITEBOARD_REL, payload)


def _append_support_whiteboard_log(run_dir: Path, line: str) -> None:
    """Append human-readable log entry to whiteboard markdown file.

    WHITEBOARD WRITE: Appends to ${run_dir}/artifacts/support_whiteboard.md (markdown log)
    CALLED BY: record_support_turn_whiteboard(), _append_dispatch_result_whiteboard()

    Creates timestamped markdown list entries for human inspection of whiteboard activity.
    """
    path = run_dir / SUPPORT_WHITEBOARD_LOG_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"- {_now_iso()} | {_brief_text(line, max_chars=420)}\n")


def _compact_whiteboard_snapshot(state: dict[str, Any], *, max_entries: int = 5) -> dict[str, Any]:
    """Create compact whiteboard snapshot for display/transmission.

    WHITEBOARD HELPER: Reduces full whiteboard to last N entries with truncated fields
    CALLED BY: get_support_whiteboard_context(), _append_dispatch_result_whiteboard()
    CONSUMED BY: ctcp_support_bot.build_progress_binding() for recent activity summary

    Returns dict with schema_version, path, entry_count, and last N entries (default 5).
    """
    entries = _safe_whiteboard_entries(state.get("entries", []), max_items=120)
    tail = entries[-max(1, int(max_entries)) :]
    summary_entries: list[dict[str, Any]] = []
    for item in tail:
        row: dict[str, Any] = {
            "ts": str(item.get("ts", "")),
            "role": str(item.get("role", "")),
            "kind": str(item.get("kind", "")),
            "text": _brief_text(str(item.get("text", "")), max_chars=220),
        }
        query = _brief_text(str(item.get("query", "")), max_chars=180)
        if query:
            row["query"] = query
        hits = _safe_whiteboard_hits(item.get("hits"), max_items=2)
        if hits:
            row["hits"] = [{"path": str(h.get("path", "")), "start_line": int(h.get("start_line", 1) or 1)} for h in hits]
            row["hit_count"] = int(item.get("hit_count", len(hits)) or len(hits))
        summary_entries.append(row)
    return {
        "schema_version": SUPPORT_WHITEBOARD_SCHEMA_VERSION,
        "path": SUPPORT_WHITEBOARD_REL.as_posix(),
        "entry_count": len(entries),
        "entries": summary_entries,
    }


def _latest_librarian_context(entries: list[dict[str, Any]]) -> dict[str, Any]:
    query = ""
    lookup_error = ""
    hits: list[dict[str, Any]] = []
    for item in reversed(entries):
        kind = str(item.get("kind", "")).strip().lower()
        if kind not in {"support_lookup", "dispatch_lookup"}:
            continue
        if not query:
            query = _brief_text(str(item.get("query", "")), max_chars=220)
        if not hits:
            hits = _safe_whiteboard_hits(item.get("hits"), max_items=4)
        if not lookup_error:
            text = str(item.get("text", "")).strip()
            if text.lower().startswith("lookup error:"):
                lookup_error = _brief_text(text.split(":", 1)[1], max_chars=180)
        if query or hits or lookup_error:
            break
    return {
        "query": query,
        "hits": hits,
        "lookup_error": lookup_error,
    }
def get_support_whiteboard_context(run_dir: Path) -> dict[str, Any]:
    return dispatch_whiteboard.get_support_whiteboard_context(run_dir)


def record_support_turn_whiteboard(
    *,
    run_dir: Path,
    repo_root: Path,
    text: str,
    source: str,
    conversation_mode: str,
    chat_id: str = "",
) -> dict[str, Any]:
    context = dispatch_whiteboard.record_support_turn_whiteboard(
        run_dir=run_dir,
        repo_root=repo_root,
        text=text,
        source=source,
        conversation_mode=conversation_mode,
        chat_id=chat_id,
    )
    update_whiteboard_state(run_dir)
    return context


def _dispatch_whiteboard_query(request: dict[str, Any]) -> str:
    """Extract search query from dispatch request for librarian lookup.

    WHITEBOARD HELPER: Determines what to search for based on goal/reason/role/action
    CALLED BY: _prepare_dispatch_whiteboard_context() before librarian search

    Returns query string prioritizing: goal > reason > "{role} {action}".
    """
    goal = _brief_text(str(request.get("goal", "")), max_chars=220)
    reason = _brief_text(str(request.get("reason", "")), max_chars=220)
    role = _brief_text(str(request.get("role", "")), max_chars=32)
    action = _brief_text(str(request.get("action", "")), max_chars=48)
    if goal:
        return goal
    if reason:
        return reason
    return _brief_text(f"{role} {action}".strip(), max_chars=120)


def _last_librarian_query(entries: list[dict[str, Any]]) -> str:
    for item in reversed(entries):
        kind = str(item.get("kind", "")).strip().lower()
        if kind not in {"support_lookup", "dispatch_lookup"}:
            continue
        query = str(item.get("query", "")).strip()
        if query:
            return query
    return ""


def _prepare_dispatch_whiteboard_context(
    *,
    run_dir: Path,
    repo_root: Path,
    request: dict[str, Any],
) -> dict[str, Any]:
    context = dispatch_whiteboard.prepare_dispatch_whiteboard_context(
        run_dir=run_dir,
        repo_root=repo_root,
        request=request,
    )
    update_whiteboard_state(run_dir)
    return context


def _append_dispatch_result_whiteboard(
    *,
    run_dir: Path,
    request: dict[str, Any],
    result: dict[str, Any],
) -> dict[str, Any]:
    context = dispatch_whiteboard.append_dispatch_result_whiteboard(
        run_dir=run_dir,
        request=request,
        result=result,
    )
    update_whiteboard_state(run_dir)
    return context


def _live_provider_violation(
    *,
    run_dir: Path,
    gate: dict[str, str],
    request: dict[str, Any],
    provider: str,
    note: str,
) -> dict[str, Any] | None:
    if not formal_api_only_enabled():
        return None
    role = str(request.get("role", "")).strip()
    action = str(request.get("action", "")).strip()
    if not requires_formal_api(role, action):
        return None
    if provider == "api_agent":
        return None
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
        "provider": provider, "chosen_provider": str(result.get("chosen_provider", provider)).strip() or provider,
        "provider_mode": str(result.get("provider_mode", "")).strip() or provider_mode(provider), "model_name": str(result.get("model_name", "")).strip() or str(result.get("ollama_model", "")).strip(),
        "fallback_blocked": bool(result.get("fallback_blocked", False)),
        "inputs": inputs,
        "inputs_ready": all(bool(x.get("exists")) for x in inputs) if inputs else True,
        "outputs": _output_paths(request, result),
        "status": status,
        "result": "OK" if status == "executed" else "ERR",
        "rc": rc,
        "error": error,
    }
    _append_jsonl(run_dir / STEP_META_PATH, row)


def _output_exists(run_dir: Path, rel_path: str) -> bool:
    value = str(rel_path or "").strip().replace("\\", "/")
    if not value:
        return False
    return (run_dir / value).exists()


def _review_step_requires_remote_success(request: dict[str, Any]) -> bool:
    role = str(request.get("role", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    return role in {"contract_guardian", "cost_controller"} or action.startswith("review_") or "review" in action


def _true_api_mode(provider: str, result: dict[str, Any]) -> bool:
    forced = _forced_provider()
    chosen = str(result.get("chosen_provider", provider)).strip().lower()
    mode = str(result.get("provider_mode", "")).strip().lower()
    return (
        forced == "api_agent"
        or chosen == "api_agent"
        or str(provider or "").strip().lower() == "api_agent"
        or mode == "remote"
        or str(os.environ.get("CTCP_TRUE_API_REQUIRED", "")).strip().lower() in {"1", "true", "yes", "on"}
    )


def _write_step_acceptance(
    *,
    run_dir: Path,
    gate: dict[str, str],
    request: dict[str, Any],
    provider: str,
    result: dict[str, Any],
) -> None:
    ts = _now_iso()
    stamp = re.sub(r"[^0-9A-Za-z]+", "", ts)[:15] or "step"
    role = _sanitize(str(request.get("role", "")).strip() or "role")
    action = _sanitize(str(request.get("action", "")).strip() or "action")
    step_dir = run_dir / "artifacts" / "acceptance" / f"{stamp}_{role}_{action}"
    step_dir.mkdir(parents=True, exist_ok=True)
    output_paths = _output_paths(request, result)
    missing_outputs = [
        path
        for path in output_paths
        if path and path.startswith("artifacts/") and not _output_exists(run_dir, path)
    ]
    status = str(result.get("status", "")).strip()
    reasons: list[str] = []
    if status != "executed":
        reasons.append(str(result.get("reason", "")).strip() or f"provider status was {status or 'empty'}")
    if missing_outputs:
        reasons.append(f"declared outputs missing: {', '.join(missing_outputs)}")
    if _review_step_requires_remote_success(request):
        if bool(result.get("fallback_used", False)):
            reasons.append("review step used provider fallback")
        if str(result.get("provider_mode", "")).strip() == "local_fallback":
            reasons.append("review step used local fallback")
        if str(result.get("reason", "")).strip() and status != "executed":
            reasons.append("review step has provider error")
    if bool(result.get("fallback_used", False)) and _true_api_mode(provider, result):
        reasons.append("api_fallback_not_allowed")
    acceptance = {
        "schema_version": "ctcp-step-acceptance-v1",
        "timestamp": ts,
        "gate": {
            "state": str(gate.get("state", "")).strip(),
            "owner": str(gate.get("owner", "")).strip(),
            "path": str(gate.get("path", "")).strip(),
            "reason": str(gate.get("reason", "")).strip(),
        },
        "role": str(request.get("role", "")).strip(),
        "action": str(request.get("action", "")).strip(),
        "provider": provider,
        "chosen_provider": str(result.get("chosen_provider", provider)).strip() or provider,
        "provider_mode": str(result.get("provider_mode", "")).strip() or provider_mode(provider),
        "request_path": (step_dir / "request.json").relative_to(run_dir).as_posix(),
        "result_path": (step_dir / "result.json").relative_to(run_dir).as_posix(),
        "acceptance_path": (step_dir / "acceptance.json").relative_to(run_dir).as_posix(),
        "outputs": output_paths,
        "missing_outputs": missing_outputs,
        "passed": not reasons,
        "result": "OK" if not reasons else "ERR",
        "reasons": reasons,
    }
    _write_json(step_dir / "request.json", request)
    _write_json(step_dir / "result.json", result)
    _write_json(step_dir / "acceptance.json", acceptance)
    _append_jsonl(run_dir / "artifacts" / "acceptance" / "ledger.jsonl", acceptance)


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
    return dispatch_request_mapper.ensure_dispatch_config(run_dir)


def load_dispatch_config(run_dir: Path) -> tuple[dict[str, Any] | None, str]:
    return dispatch_request_mapper.load_dispatch_config(run_dir)


def _parse_guardrails_budgets(run_dir: Path) -> dict[str, str]:
    return dispatch_request_mapper.parse_guardrails_budgets(run_dir)


def _split_missing_paths(path_value: str) -> list[str]:
    parts = [x.strip() for x in re.split(r"[|,]", path_value or "") if x.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
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
    return re.sub(r"[^a-z0-9]+", "_", (owner or "").strip().lower()).strip("_")


def derive_request(gate: dict[str, str], run_doc: dict[str, Any]) -> dict[str, Any] | None:
    return dispatch_request_mapper.derive_request(gate, run_doc)


def _resolve_provider(config: dict[str, Any], role: str, action: str) -> tuple[str, str]:
    return core_router.resolve_provider(
        config,
        role,
        action,
        force_provider=_forced_provider(),
        hard_role_providers=HARD_ROLE_PROVIDERS,
    )


def dispatch_preview(run_dir: Path, run_doc: dict[str, Any], gate: dict[str, str]) -> dict[str, Any]:
    config, cfg_msg = load_dispatch_config(run_dir)
    if config is None:
        return {"status": "disabled", "reason": cfg_msg}

    request = derive_request(gate, run_doc)
    if request is None:
        return {"status": "no_request"}
    return core_router.dispatch_preview(
        request=request,
        config=config,
        run_dir=run_dir,
        preview_provider=provider_runtime.preview_provider,
        force_provider=_forced_provider(),
        hard_role_providers=HARD_ROLE_PROVIDERS,
        live_policy=lambda **kwargs: _live_provider_violation(gate=gate, **kwargs),
    )


def dispatch_once(run_dir: Path, run_doc: dict[str, Any], gate: dict[str, str], repo_root: Path) -> dict[str, Any]:
    # BEHAVIOR_ID: B027
    config, cfg_msg = load_dispatch_config(run_dir)
    if config is None:
        return {"status": "disabled", "reason": cfg_msg}

    request_raw = derive_request(gate, run_doc)
    if request_raw is None:
        return {"status": "no_request"}
    request = dict(request_raw)
    whiteboard_context = _prepare_dispatch_whiteboard_context(
        run_dir=run_dir,
        repo_root=repo_root,
        request=request,
    )
    request["whiteboard"] = {
        "path": str(whiteboard_context.get("path", "")),
        "query": str(whiteboard_context.get("query", "")),
        "hits": list(whiteboard_context.get("hits", [])),
        "lookup_error": str(whiteboard_context.get("lookup_error", "")),
        "snapshot": dict(whiteboard_context.get("snapshot", {})),
    }

    provider, _note = _resolve_provider(config, str(request["role"]), str(request["action"]))
    result = core_router.dispatch_execute(
        request=request,
        config=config,
        run_dir=run_dir,
        repo_root=repo_root,
        execute_provider=provider_runtime.execute_provider,
        guardrails_budgets=_parse_guardrails_budgets(run_dir),
        force_provider=_forced_provider(),
        hard_role_providers=HARD_ROLE_PROVIDERS,
        live_policy=lambda **kwargs: _live_provider_violation(gate=gate, **kwargs),
    )

    result_snapshot = _append_dispatch_result_whiteboard(
        run_dir=run_dir,
        request=request,
        result=result,
    )
    result["whiteboard"] = {
        "path": str(whiteboard_context.get("path", "")),
        "query": str(whiteboard_context.get("query", "")),
        "hit_count": len(list(whiteboard_context.get("hits", []))),
        "lookup_error": str(whiteboard_context.get("lookup_error", "")),
        "snapshot": result_snapshot,
    }
    provider_used = (
        str(result.get("provider", "")).strip()
        or str(result.get("chosen_provider", "")).strip()
        or str(provider).strip()
    )
    append_provider_ledger(
        run_dir,
        role=str(request.get("role", "")),
        action=str(request.get("action", "")),
        provider_used=provider_used,
        result=result,
    )
    _append_step_meta(
        run_dir=run_dir,
        gate=gate,
        request=request,
        provider=provider_used,
        result=result,
    )
    _write_step_acceptance(
        run_dir=run_dir,
        gate=gate,
        request=request,
        provider=provider_used,
        result=result,
    )
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
