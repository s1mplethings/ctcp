from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

FORMAL_API_ONLY_ENV = "CTCP_FORMAL_API_ONLY"
PROVIDER_LEDGER_REL = Path("artifacts") / "provider_ledger.jsonl"
PROVIDER_LEDGER_SUMMARY_REL = Path("artifacts") / "provider_ledger_summary.json"
LOCAL_EXCEPTION_ROLE_ACTIONS = {("librarian", "context_pack")}


def _truthy(raw: str) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def formal_api_only_enabled() -> bool:
    return _truthy(os.environ.get(FORMAL_API_ONLY_ENV, ""))


def normalize_role_action(role: str, action: str) -> tuple[str, str]:
    return str(role or "").strip().lower(), str(action or "").strip().lower()


def is_local_exception(role: str, action: str) -> bool:
    return normalize_role_action(role, action) in LOCAL_EXCEPTION_ROLE_ACTIONS


def requires_formal_api(role: str, action: str) -> bool:
    return not is_local_exception(role, action)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        try:
            doc = json.loads(text)
        except Exception:
            continue
        if isinstance(doc, dict):
            rows.append(doc)
    return rows


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def latest_api_request_id(run_dir: Path, *, role: str, action: str) -> str:
    rows = _read_jsonl(run_dir / "api_calls.jsonl")
    role_name, action_name = normalize_role_action(role, action)
    for row in reversed(rows):
        if normalize_role_action(str(row.get("role", "")), str(row.get("action", ""))) != (role_name, action_name):
            continue
        request_id = str(row.get("request_id", "")).strip()
        if request_id:
            return request_id
    return ""


def external_api_used(provider_used: str, result: dict[str, Any]) -> bool:
    chosen = str(result.get("chosen_provider", provider_used)).strip().lower() or str(provider_used or "").strip().lower()
    mode = str(result.get("provider_mode", "")).strip().lower()
    if str(result.get("request_id", "")).strip():
        return True
    return chosen == "api_agent" or mode == "remote"


def build_provider_ledger_summary(run_dir: Path) -> dict[str, Any]:
    ledger_path = run_dir / PROVIDER_LEDGER_REL
    rows = _read_jsonl(ledger_path)
    critical_rows = [
        row
        for row in rows
        if requires_formal_api(str(row.get("role", "")), str(row.get("action", "")))
    ]
    critical_api_rows = [
        row
        for row in critical_rows
        if bool(row.get("external_api_used", False))
        and str(row.get("provider_used", "")).strip().lower() == "api_agent"
        and not bool(row.get("fallback_used", False))
        and not str(row.get("local_function_used", "")).strip()
        and str(row.get("status", "")).strip() == "executed"
    ]
    summary = {
        "schema_version": "ctcp-provider-ledger-summary-v1",
        "ledger_path": PROVIDER_LEDGER_REL.as_posix(),
        "row_count": len(rows),
        "critical_step_count": len(critical_rows),
        "critical_api_step_count": len(critical_api_rows),
        "local_exception_count": len([row for row in rows if is_local_exception(str(row.get("role", "")), str(row.get("action", "")))]),
        "fallback_count": len([row for row in rows if bool(row.get("fallback_used", False))]),
        "failed_count": len([row for row in rows if str(row.get("status", "")).strip() != "executed"]),
        "all_critical_steps_api": bool(critical_rows) and len(critical_api_rows) == len(critical_rows),
        "critical_steps": [
            {
                "role": str(row.get("role", "")),
                "action": str(row.get("action", "")),
                "provider_used": str(row.get("provider_used", "")),
                "external_api_used": bool(row.get("external_api_used", False)),
                "request_id": str(row.get("request_id", "")),
                "fallback_used": bool(row.get("fallback_used", False)),
                "local_function_used": str(row.get("local_function_used", "")),
                "verdict": str(row.get("verdict", "")),
            }
            for row in critical_rows
        ],
    }
    _write_json(run_dir / PROVIDER_LEDGER_SUMMARY_REL, summary)
    return summary


def load_provider_ledger_summary(run_dir: Path) -> dict[str, Any]:
    path = run_dir / PROVIDER_LEDGER_SUMMARY_REL
    if path.exists():
        return _read_json(path)
    return build_provider_ledger_summary(run_dir)


def append_provider_ledger(
    run_dir: Path,
    *,
    role: str,
    action: str,
    provider_used: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    role_name, action_name = normalize_role_action(role, action)
    request_id = str(result.get("request_id", "")).strip() or latest_api_request_id(
        run_dir,
        role=role_name,
        action=action_name,
    )
    row = {
        "role": role_name,
        "action": action_name,
        "provider_used": str(result.get("chosen_provider", provider_used)).strip() or str(provider_used or "").strip(),
        "external_api_used": external_api_used(provider_used, result),
        "request_id": request_id,
        "fallback_used": bool(result.get("fallback_used", False)),
        "local_function_used": str(result.get("local_function_used", "")).strip(),
        "status": str(result.get("status", "")).strip(),
    }
    if row["status"] == "executed":
        if is_local_exception(role_name, action_name):
            row["verdict"] = "local_exception_allowed"
        elif row["external_api_used"] and row["provider_used"] == "api_agent" and not row["fallback_used"] and not row["local_function_used"]:
            row["verdict"] = "api_executed"
        elif row["fallback_used"]:
            row["verdict"] = "executed_with_fallback"
        elif row["local_function_used"]:
            row["verdict"] = "executed_with_local_function"
        else:
            row["verdict"] = "executed_non_api"
    elif formal_api_only_enabled() and requires_formal_api(role_name, action_name) and row["provider_used"] != "api_agent":
        row["verdict"] = "blocked_non_api_provider"
    elif formal_api_only_enabled() and row["local_function_used"]:
        row["verdict"] = "blocked_local_function"
    else:
        row["verdict"] = "failed"
    _append_jsonl(run_dir / PROVIDER_LEDGER_REL, row)
    build_provider_ledger_summary(run_dir)
    return row
