#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import json
import mimetypes
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
ORCHESTRATE_PATH = SCRIPTS_DIR / "ctcp_orchestrate.py"
LAST_RUN_POINTER = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
REPORT_LAST = ROOT / "meta" / "reports" / "LAST.md"
SUPPORT_FRONTEND_TURNS_REL = Path("artifacts") / "support_frontend_turns.jsonl"
SUPPORT_RUNTIME_STATE_REL = Path("artifacts") / "support_runtime_state.json"

_FINAL_RUN_STATUSES = {"pass", "done", "completed", "success"}
_RUNNING_STATUSES = {"running", "in_progress", "working"}
_ERROR_RUN_STATUSES = {"fail", "failed", "error", "aborted"}
_ERROR_GATE_STATES = {"error", "failed"}
_USER_DECISION_STATUSES = {"pending", "submitted"}
_DECISION_STATUSES = {"pending", "submitted", "consumed", "rejected", "expired"}

STATUS_LINE_RE = re.compile(r"^\[ctcp_orchestrate\]\s*([^=]+)=(.*)$")

try:
    from tools.run_paths import get_repo_runs_root
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_runs_root

try:
    import ctcp_dispatch
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    import ctcp_dispatch
try:
    from project_manifest_bridge import resolve_project_manifest
except ModuleNotFoundError:
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    from project_manifest_bridge import resolve_project_manifest


class BridgeError(RuntimeError):
    pass


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "cmd": " ".join(cmd),
        "exit_code": int(proc.returncode),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = json.loads(_read_text(path))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    _write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _tail_lines(text: str, max_lines: int = 80) -> str:
    rows = text.splitlines()
    if len(rows) <= max_lines:
        return text
    return "\n".join(rows[-max_lines:])


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _ensure_within_run_dir(run_dir: Path, candidate: Path) -> None:
    if not _is_within(candidate, run_dir):
        raise BridgeError(f"path escapes run_dir: {candidate}")


def _guess_mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    explicit = {
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".json": "application/json",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".html": "text/html",
        ".css": "text/css",
        ".js": "text/javascript",
        ".ts": "text/plain",
    }
    if suffix in explicit:
        return explicit[suffix]
    mime, _enc = mimetypes.guess_type(str(path))
    return str(mime or "application/octet-stream")


def _sha256_hex(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _resolve_latest_run_dir() -> Path:
    raw = _read_text(LAST_RUN_POINTER).strip()
    if not raw:
        raise BridgeError("missing LAST_RUN pointer; create a run first")
    run_dir = Path(raw).expanduser().resolve()
    if not run_dir.exists():
        raise BridgeError(f"LAST_RUN pointer does not exist: {run_dir}")
    return run_dir


def _resolve_run_dir(run_id: str = "") -> Path:
    rid = str(run_id or "").strip()
    if not rid:
        return _resolve_latest_run_dir()

    direct = Path(rid).expanduser()
    if direct.is_absolute() and direct.exists():
        return direct.resolve()

    if direct.exists() and direct.is_dir():
        return direct.resolve()

    run_dir = (get_repo_runs_root(ROOT) / rid).resolve()
    if run_dir.exists():
        return run_dir
    raise BridgeError(f"run_id not found: {rid}")


def _run_id_from_dir(run_dir: Path) -> str:
    return run_dir.resolve().name


def _parse_status_output(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = STATUS_LINE_RE.match(line)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            out[key] = m.group(2).strip()
            continue
        if line.startswith("[ctcp_orchestrate] blocked:"):
            out["blocked"] = line.split(":", 1)[1].strip()
    return out


def _parse_outbox_prompt(path: Path) -> dict[str, str]:
    text = _read_text(path)
    out = {
        "role": "",
        "action": "",
        "target_path": "",
        "reason": "",
        "question_hint": "",
    }
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Role:"):
            out["role"] = line.split(":", 1)[1].strip()
        elif line.startswith("Action:"):
            out["action"] = line.split(":", 1)[1].strip()
        elif line.startswith("Target-Path:"):
            out["target_path"] = line.split(":", 1)[1].strip()
        elif line.startswith("Reason:"):
            out["reason"] = line.split(":", 1)[1].strip()
        elif line.startswith("Question:"):
            out["question_hint"] = line.split(":", 1)[1].strip()
    return out


def _runtime_state_path(run_dir: Path) -> Path:
    return run_dir / SUPPORT_RUNTIME_STATE_REL


def _iso_from_epoch(epoch: float) -> str:
    return dt.datetime.fromtimestamp(float(epoch), tz=dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _file_ts_iso(path: Path) -> str:
    try:
        return _iso_from_epoch(path.stat().st_mtime)
    except Exception:
        return _now_utc_iso()


def _decision_default_target(decision_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(decision_id or "").strip()).strip("_")
    safe = safe or "decision"
    return f"artifacts/support_decisions/{safe}.md"


def _decision_format(target_path: str) -> tuple[str, dict[str, Any]]:
    suffix = Path(str(target_path or "").strip()).suffix.lower()
    if suffix == ".json":
        return "json", {"type": "object"}
    if suffix == ".md":
        return "markdown", {"type": "string"}
    return "text", {"type": "string"}


def _normalize_decision_status(value: str, *, fallback: str = "pending") -> str:
    status = str(value or "").strip().lower()
    if status in _DECISION_STATUSES:
        return status
    return fallback


def _normalize_decision_row(raw: dict[str, Any], *, now_ts: str, status_fallback: str = "pending") -> dict[str, Any]:
    decision_id = str(raw.get("decision_id", "")).strip()
    question = str(raw.get("question", "") or raw.get("question_hint", "") or raw.get("reason", "")).strip()
    target_path = str(raw.get("target_path", "")).strip()
    if not target_path and decision_id:
        target_path = _decision_default_target(decision_id)
    expected_format = str(raw.get("expected_format", "")).strip()
    schema = raw.get("schema", {})
    if not expected_format:
        expected_format, default_schema = _decision_format(target_path)
        if not isinstance(schema, dict) or not schema:
            schema = default_schema
    if not isinstance(schema, dict):
        schema = {}

    status = _normalize_decision_status(str(raw.get("status", "")), fallback=status_fallback)
    created_at = str(raw.get("created_at", "")).strip() or now_ts
    submitted_at = str(raw.get("submitted_at", "")).strip()
    consumed_at = str(raw.get("consumed_at", "")).strip()
    rejected_at = str(raw.get("rejected_at", "")).strip()
    expired_at = str(raw.get("expired_at", "")).strip()
    submission_state_hash = str(raw.get("submission_state_hash", "")).strip()
    prompt_path = str(raw.get("prompt_path", "")).strip()
    role = str(raw.get("role", "")).strip()
    action = str(raw.get("action", "")).strip()
    reason = str(raw.get("reason", "")).strip() or question
    kind = str(raw.get("kind", "")).strip() or "decision"
    source = str(raw.get("source", "")).strip() or "canonical"

    return {
        "decision_id": decision_id,
        "kind": kind,
        "question": question,
        "question_hint": question,
        "target_path": target_path,
        "prompt_path": prompt_path,
        "role": role,
        "action": action,
        "reason": reason,
        "expected_format": expected_format,
        "schema": schema,
        "status": status,
        "created_at": created_at,
        "submitted_at": submitted_at,
        "consumed_at": consumed_at,
        "rejected_at": rejected_at,
        "expired_at": expired_at,
        "submission_state_hash": submission_state_hash,
        "source": source,
    }


def _scan_pending_decisions_from_legacy(run_dir: Path) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    outbox_dir = run_dir / "outbox"
    for prompt in sorted(outbox_dir.glob("*.md")) if outbox_dir.exists() else []:
        parsed = _parse_outbox_prompt(prompt)
        target_rel = str(parsed.get("target_path", "")).strip()
        if not target_rel:
            target_rel = _decision_default_target(f"outbox:{prompt.stem}")
        target_abs = (run_dir / target_rel).resolve()
        _ensure_within_run_dir(run_dir, target_abs)
        if target_abs.exists():
            continue
        expected_format, schema = _decision_format(target_rel)
        question = str(parsed.get("question_hint", "")).strip() or str(parsed.get("reason", "")).strip()
        decision_id = f"outbox:{prompt.stem}"
        decisions.append(
            _normalize_decision_row(
                {
                    "decision_id": decision_id,
                    "kind": "outbox_prompt",
                    "source": "fallback_legacy",
                    "prompt_path": prompt.relative_to(run_dir).as_posix(),
                    "role": str(parsed.get("role", "")).strip(),
                    "action": str(parsed.get("action", "")).strip(),
                    "target_path": target_rel,
                    "reason": str(parsed.get("reason", "")).strip(),
                    "question": question,
                    "expected_format": expected_format,
                    "schema": schema,
                    "status": "pending",
                    "created_at": _file_ts_iso(prompt),
                },
                now_ts=_now_utc_iso(),
            )
        )

    questions_path = run_dir / "QUESTIONS.md"
    if questions_path.exists():
        created_at = _file_ts_iso(questions_path)
        rows = [ln.strip() for ln in _read_text(questions_path).splitlines() if ln.strip()]
        for idx, row in enumerate(rows, start=1):
            if row.startswith("#"):
                continue
            if row.startswith("-"):
                row = row.lstrip("-").strip()
            if not row:
                continue
            decision_id = f"questions:{idx}"
            target_rel = _decision_default_target(decision_id)
            target_abs = (run_dir / target_rel).resolve()
            _ensure_within_run_dir(run_dir, target_abs)
            if target_abs.exists():
                continue
            decisions.append(
                _normalize_decision_row(
                    {
                        "decision_id": decision_id,
                        "kind": "questions_md",
                        "source": "fallback_legacy",
                        "prompt_path": "QUESTIONS.md",
                        "role": "chair/planner",
                        "action": "question",
                        "target_path": target_rel,
                        "reason": row,
                        "question": row,
                        "expected_format": "markdown",
                        "schema": {"type": "string"},
                        "status": "pending",
                        "created_at": created_at,
                    },
                    now_ts=_now_utc_iso(),
                )
            )
    return decisions


def _canonical_decisions_from_runtime_state(state_doc: dict[str, Any], *, now_ts: str) -> tuple[list[dict[str, Any]], bool]:
    rows: list[dict[str, Any]] = []
    has_explicit = False
    for key in ("decisions", "pending_decisions"):
        if key in state_doc:
            has_explicit = True
        value = state_doc.get(key, [])
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict):
                continue
            normalized = _normalize_decision_row(item, now_ts=now_ts, status_fallback="pending")
            decision_id = str(normalized.get("decision_id", "")).strip()
            if not decision_id:
                continue
            if not str(normalized.get("source", "")).strip():
                normalized["source"] = "canonical"
            rows.append(normalized)
    merged: dict[str, dict[str, Any]] = {}
    for row in rows:
        decision_id = str(row.get("decision_id", "")).strip()
        if not decision_id:
            continue
        merged[decision_id] = row
    deduped = list(merged.values())
    deduped.sort(key=_decision_sort_key)
    return deduped, has_explicit


def _decision_registry_with_fallback(
    *,
    run_dir: Path,
    previous_state: dict[str, Any],
    now_ts: str,
    core_hash_seed: str,
) -> tuple[list[dict[str, Any]], str, bool]:
    canonical_rows, canonical_explicit = _canonical_decisions_from_runtime_state(previous_state, now_ts=now_ts)
    if canonical_explicit:
        return canonical_rows, "canonical", False

    legacy_rows = _scan_pending_decisions_from_legacy(run_dir)
    if legacy_rows:
        merged = _merge_decision_registry(
            previous_state=previous_state,
            pending_from_legacy=legacy_rows,
            core_hash=core_hash_seed,
            now_ts=now_ts,
        )
        for item in merged:
            if not str(item.get("source", "")).strip():
                item["source"] = "fallback_legacy"
        return merged, "fallback_legacy", True
    return canonical_rows, "canonical", False


def _runtime_core_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


def _derive_runtime_phase(
    *,
    run_status: str,
    verify_result: str,
    gate_state: str,
    needs_user_decision: bool,
    has_error: bool,
) -> str:
    if has_error:
        return "RECOVER"
    if verify_result == "PASS" and run_status in _FINAL_RUN_STATUSES and not needs_user_decision:
        return "FINALIZE"
    if needs_user_decision:
        return "WAIT_USER_DECISION"
    if gate_state in {"ready_verify", "verify", "verification"}:
        return "VERIFY"
    if run_status in _RUNNING_STATUSES:
        return "EXECUTE"
    if run_status in {"new", "created", "pending", "queued"}:
        return "PLAN"
    if gate_state == "blocked":
        return "RECOVER"
    return "PLAN"


def _decision_sort_key(row: dict[str, Any]) -> str:
    for key in ("consumed_at", "submitted_at", "created_at"):
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def _merge_decision_registry(
    *,
    previous_state: dict[str, Any],
    pending_from_legacy: list[dict[str, Any]],
    core_hash: str,
    now_ts: str,
) -> list[dict[str, Any]]:
    previous_rows_raw = previous_state.get("decisions", [])
    if not isinstance(previous_rows_raw, list):
        previous_rows_raw = []
    previous_rows = {}
    for item in previous_rows_raw:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_decision_row(item, now_ts=now_ts, status_fallback="pending")
        decision_id = str(normalized.get("decision_id", "")).strip()
        if decision_id:
            previous_rows[decision_id] = normalized

    pending_rows = {}
    for item in pending_from_legacy:
        normalized = _normalize_decision_row(item, now_ts=now_ts, status_fallback="pending")
        decision_id = str(normalized.get("decision_id", "")).strip()
        if decision_id:
            pending_rows[decision_id] = normalized

    merged: dict[str, dict[str, Any]] = {}
    for decision_id, current in pending_rows.items():
        prev = previous_rows.get(decision_id)
        if prev and str(prev.get("status", "")).strip().lower() == "submitted":
            current["status"] = "submitted"
            current["submitted_at"] = str(prev.get("submitted_at", "")).strip()
            current["submission_state_hash"] = str(prev.get("submission_state_hash", "")).strip()
        elif prev:
            current["created_at"] = str(prev.get("created_at", "")).strip() or str(current.get("created_at", "")).strip() or now_ts
        merged[decision_id] = current

    for decision_id, prev in previous_rows.items():
        if decision_id in merged:
            continue
        status = str(prev.get("status", "")).strip().lower()
        if status == "submitted":
            submit_hash = str(prev.get("submission_state_hash", "")).strip()
            if submit_hash and submit_hash != core_hash:
                prev["status"] = "consumed"
                prev["consumed_at"] = str(prev.get("consumed_at", "")).strip() or now_ts
            else:
                prev["status"] = "submitted"
        elif status == "pending":
            prev["status"] = "expired"
            prev["expired_at"] = str(prev.get("expired_at", "")).strip() or now_ts
        merged[decision_id] = prev

    unresolved = [row for row in merged.values() if str(row.get("status", "")).strip().lower() in _USER_DECISION_STATUSES]
    resolved = [row for row in merged.values() if str(row.get("status", "")).strip().lower() not in _USER_DECISION_STATUSES]
    unresolved.sort(key=_decision_sort_key)
    resolved.sort(key=_decision_sort_key, reverse=True)
    return unresolved + resolved[:32]


def _read_runtime_state(run_dir: Path) -> dict[str, Any]:
    doc = _read_json(_runtime_state_path(run_dir))
    if not isinstance(doc, dict):
        return {}
    schema = str(doc.get("schema_version", "")).strip()
    if schema != "ctcp-support-runtime-state-v1":
        return {}
    return doc

def _write_runtime_state(run_dir: Path, state: dict[str, Any]) -> None:
    _write_json(_runtime_state_path(run_dir), state)

def _refresh_runtime_state(run_dir: Path) -> dict[str, Any]:
    # Backend-interface-first refresh:
    # - canonical runtime snapshot is primary truth
    # - orchestrate status output is metadata only
    # - no outbox/questions/RUN/verify file peeking for primary state synthesis
    status_cmd = _orchestrate_status(run_dir)
    parsed = status_cmd.get("parsed", {}) if isinstance(status_cmd.get("parsed"), dict) else {}
    gate_state = str(parsed.get("next", "") or parsed.get("gate_state", "")).strip().lower()
    gate = {
        "state": gate_state,
        "owner": str(parsed.get("owner", "")).strip(),
        "path": str(parsed.get("path", "")).strip(),
        "reason": str(parsed.get("reason", "") or parsed.get("blocked", "")).strip(),
    }
    latest_status_raw = {
        "exit_code": int(status_cmd.get("exit_code", 0) or 0),
        "stdout": str(status_cmd.get("stdout", "")),
        "stderr": str(status_cmd.get("stderr", "")),
    }
    now_ts = _now_utc_iso()
    previous_state = _read_runtime_state(run_dir)
    previous_iterations = previous_state.get("iterations", {}) if isinstance(previous_state.get("iterations", {}), dict) else {}
    iterations = {
        "current": int(previous_iterations.get("current", 0) or 0),
        "max": int(previous_iterations.get("max", 0) or 0),
        "source": str(previous_iterations.get("source", "")).strip(),
    }
    run_status = str(parsed.get("run_status", "")).strip().lower()
    if not run_status:
        run_status = str(previous_state.get("run_status", "")).strip().lower()
    verify_result = str(previous_state.get("verify_result", "")).strip().upper()
    verify_gate = str(previous_state.get("verify_gate", "")).strip().lower()
    if verify_doc := _read_json(run_dir / "artifacts" / "verify_report.json"):
        verify_result = str(verify_doc.get("result", "")).strip().upper() or verify_result
        verify_gate = str(verify_doc.get("gate", "")).strip().lower() or verify_gate
        iterations["current"], iterations["max"] = int(verify_doc.get("iteration", iterations.get("current", 0)) or 0), int(verify_doc.get("max_iterations", iterations.get("max", 0)) or 0)
        if verify_doc.get("max_iterations") is not None: iterations["source"] = str(iterations.get("source", "")).strip() or "verify_report.json"
    raw_decisions = previous_state.get("decisions", [])
    if not isinstance(raw_decisions, list):
        raw_decisions = []
    decision_registry: list[dict[str, Any]] = []
    for item in raw_decisions:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_decision_row(item, now_ts=now_ts, status_fallback="pending")
        if not str(normalized.get("decision_id", "")).strip():
            continue
        decision_registry.append(normalized)

    pending_user_decisions = [row for row in decision_registry if str(row.get("status", "")).strip().lower() == "pending"]
    open_decisions = [row for row in decision_registry if str(row.get("status", "")).strip().lower() in _USER_DECISION_STATUSES]
    submitted_open = [row for row in decision_registry if str(row.get("status", "")).strip().lower() == "submitted"]
    needs_user_decision = bool(pending_user_decisions)
    final_ready = run_status in _FINAL_RUN_STATUSES and verify_result == "PASS" and not needs_user_decision
    previous_error = previous_state.get("error", {})
    has_error = not final_ready and (
        run_status in _ERROR_RUN_STATUSES
        or gate_state in _ERROR_GATE_STATES
        or verify_result == "FAIL"
        or (isinstance(previous_error, dict) and bool(previous_error.get("has_error", False)))
    )
    phase = _derive_runtime_phase(
        run_status=run_status,
        verify_result=verify_result,
        gate_state=gate_state,
        needs_user_decision=needs_user_decision,
        has_error=has_error,
    )
    if submitted_open and phase in {"PLAN", "RECOVER"} and not has_error:
        phase = "EXECUTE"
    blocking_reason = "none"
    if pending_user_decisions:
        first = pending_user_decisions[0]
        blocking_reason = str(first.get("question", "") or first.get("reason", "")).strip() or str(gate.get("reason", "")).strip() or "decision_required"
    elif submitted_open:
        blocking_reason = "decision_submitted_waiting_backend_consume"
    elif has_error:
        blocking_reason = str(gate.get("reason", "")).strip() or f"run_status={run_status or 'error'}"
    elif gate_state == "blocked":
        blocking_reason = str(gate.get("reason", "")).strip() or "blocked"
    elif str(previous_state.get("blocking_reason", "")).strip():
        blocking_reason = str(previous_state.get("blocking_reason", "")).strip()
    if final_ready: blocking_reason = "none"
    error_doc = {
        "has_error": bool(has_error),
        "code": run_status if run_status in _ERROR_RUN_STATUSES else (gate_state if gate_state in _ERROR_GATE_STATES else ""),
        "message": str(gate.get("reason", "")).strip() if has_error else "",
    }
    recovery_doc = {"needed": False, "hint": "", "status": "none"} if final_ready else {"needed": bool(has_error or submitted_open), "hint": "run ctcp_advance after decision consumption" if submitted_open else ("inspect verify report and failure bundle" if has_error else ""), "status": "required" if (has_error or submitted_open) else "none"}
    latest_result = {
        "verify_result": verify_result,
        "verify_gate": verify_gate,
        "iterations": iterations,
        "gate": gate,
        "status_raw": latest_status_raw,
    }
    core_hash = _runtime_core_hash(
        {
            "run_status": run_status,
            "verify_result": verify_result,
            "verify_gate": verify_gate,
            "gate": gate,
            "iterations": iterations,
            "latest_status_raw": latest_status_raw,
            "decisions": decision_registry,
        }
    )
    snapshot = {
        "schema_version": "ctcp-support-runtime-state-v1",
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "phase": phase,
        "run_status": run_status,
        "blocking_reason": blocking_reason or "none",
        "needs_user_decision": bool(needs_user_decision),
        "pending_decisions": open_decisions[:32],
        "decisions": decision_registry[:64],
        "latest_result": latest_result,
        "error": error_doc,
        "recovery": recovery_doc,
        "gate": gate,
        "iterations": iterations,
        "verify_result": verify_result,
        "verify_gate": verify_gate,
        "decisions_needed_count": len(pending_user_decisions),
        "open_decisions_count": len(open_decisions),
        "submitted_decisions_count": len(submitted_open),
        "core_hash": core_hash,
        "updated_at": now_ts,
        "snapshot_source": "backend_interface_snapshot",
    }
    _write_runtime_state(run_dir, snapshot)
    return snapshot

def _load_runtime_state(run_dir: Path, *, refresh: bool = True) -> dict[str, Any]:
    state = _read_runtime_state(run_dir)
    if not state:
        return _refresh_runtime_state(run_dir)
    if refresh:
        return _refresh_runtime_state(run_dir)
    return state


def _classify_artifact(rel_path: str) -> str:
    suffix = Path(rel_path).suffix.lower()
    rel_l = str(rel_path).lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}:
        return "image"
    if suffix in {".zip", ".tar", ".gz", ".tgz"}:
        return "archive"
    if suffix in {".html", ".css", ".js", ".ts", ".py", ".md", ".txt", ".json", ".yaml", ".yml"}:
        return "code"
    if "report" in rel_l or rel_l.endswith("trace.md"):
        return "report"
    return "other"


def _is_output_artifact_rel(rel_path: str) -> bool:
    rel = str(rel_path).strip().replace("\\", "/")
    if not rel:
        return False
    if rel.startswith("outbox/"):
        return False
    if rel in {"RUN.json", "events.jsonl"}:
        return False
    if rel.startswith("artifacts/frontend_uploads/"):
        # uploaded user inputs are not backend-produced output artifacts
        return False
    if rel.startswith("artifacts/support_decisions/"):
        # user decision payloads are not output deliverables
        return False
    return True


def _artifact_row(run_dir: Path, file_path: Path) -> dict[str, Any]:
    rel_path = file_path.resolve().relative_to(run_dir.resolve()).as_posix()
    artifact_id = hashlib.sha1(rel_path.encode("utf-8", errors="replace")).hexdigest()
    mime_type = _guess_mime_type(file_path)
    return {
        "artifact_id": artifact_id,
        "rel_path": rel_path,
        "kind": _classify_artifact(rel_path),
        "mime_type": mime_type,
        "size_bytes": int(file_path.stat().st_size),
        "created_at": _file_ts_iso(file_path),
    }


def _collect_output_artifacts(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.resolve().relative_to(run_dir.resolve()).as_posix()
        if not _is_output_artifact_rel(rel_path):
            continue
        rows.append(_artifact_row(run_dir, path))
    return rows


def ctcp_get_project_manifest(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    rid = _run_id_from_dir(run_dir)
    artifacts = _collect_output_artifacts(run_dir)
    manifest_path = run_dir / "artifacts" / "project_manifest.json"
    declared = _read_json(manifest_path) if manifest_path.exists() else None
    if not isinstance(declared, dict) or not declared:
        declared = None
    return resolve_project_manifest(run_id=rid, run_dir=run_dir, artifacts=artifacts, declared=declared)


def _resolve_artifact_path(run_dir: Path, artifact_ref: str) -> tuple[Path, dict[str, Any]]:
    ref = str(artifact_ref or "").strip()
    if not ref:
        raise BridgeError("artifact_ref is required")
    rows = _collect_output_artifacts(run_dir)
    row: dict[str, Any] | None = None
    for item in rows:
        if str(item.get("artifact_id", "")).strip() == ref:
            row = item
            break
        if str(item.get("rel_path", "")).strip() == ref.replace("\\", "/"):
            row = item
            break
    if row is None:
        raise BridgeError(f"output artifact not found: {ref}")
    rel = str(row.get("rel_path", "")).strip()
    target = (run_dir / rel).resolve()
    _ensure_within_run_dir(run_dir, target)
    if not target.exists() or not target.is_file():
        raise BridgeError(f"output artifact path missing: {target}")
    return target, row


def _append_event(run_dir: Path, event: str, path: str = "", **extra: Any) -> None:
    row: dict[str, Any] = {
        "ts": _now_utc_iso(),
        "role": "frontend_bridge",
        "event": event,
        "path": path,
    }
    for key, value in extra.items():
        row[str(key)] = value
    events_path = run_dir / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _orchestrate_status(run_dir: Path) -> dict[str, Any]:
    cmd = [sys.executable, str(ORCHESTRATE_PATH), "status", "--run-dir", str(run_dir)]
    result = _run_cmd(cmd, ROOT)
    result["parsed"] = _parse_status_output(str(result.get("stdout", "")))
    return result


def ctcp_new_run(goal: str, constraints: dict[str, Any] | None = None, attachments: list[str] | None = None) -> dict[str, Any]:
    goal_text = str(goal or "").strip()
    if not goal_text:
        raise BridgeError("goal is required")
    if not isinstance(constraints, dict):
        try: from apps.cs_frontend.dialogue.requirement_collector import collect_frontend_constraints as _collect; constraints = _collect(mode="PROJECT_DETAIL", latest_user_text=goal_text, history=[])
        except Exception: constraints = {}

    cmd = [sys.executable, str(ORCHESTRATE_PATH), "new-run", "--goal", goal_text]
    created = _run_cmd(cmd, ROOT)
    if int(created.get("exit_code", 1)) != 0:
        raise BridgeError(f"ctcp_orchestrate new-run failed: {created.get('stderr', '').strip()}")

    run_dir = _resolve_latest_run_dir()
    run_id = _run_id_from_dir(run_dir)

    uploaded: list[dict[str, Any]] = []
    for item in attachments or []:
        uploaded.append(ctcp_upload_artifact(run_id, item))

    request_doc = {
        "schema_version": "ctcp-frontend-request-v1",
        "ts": _now_utc_iso(),
        "goal": goal_text,
        "constraints": constraints if isinstance(constraints, dict) else {},
        "attachments": uploaded,
    }
    _write_json(run_dir / "artifacts" / "frontend_request.json", request_doc)
    _append_event(run_dir, "FRONTEND_REQUEST_WRITTEN", "artifacts/frontend_request.json")

    status = ctcp_get_status(run_id)
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "created": created,
        "status": status,
    }


def ctcp_get_status(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    runtime_state = _load_runtime_state(run_dir, refresh=True)
    gate = runtime_state.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    latest_result = runtime_state.get("latest_result", {})
    if not isinstance(latest_result, dict):
        latest_result = {}
    iterations = runtime_state.get("iterations", {})
    if not isinstance(iterations, dict):
        iterations = {}
    latest_status_raw = latest_result.get("status_raw", {})
    if not isinstance(latest_status_raw, dict):
        latest_status_raw = {}
    pending_decisions = runtime_state.get("pending_decisions", [])
    if not isinstance(pending_decisions, list):
        pending_decisions = []
    pending_user_count = int(runtime_state.get("decisions_needed_count", 0) or 0)
    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "run_status": str(runtime_state.get("run_status", "")).strip().lower(),
        "verify_result": str(runtime_state.get("verify_result", "")).strip().upper(),
        "verify_gate": str(runtime_state.get("verify_gate", "")).strip().lower(),
        "iterations": {
            "current": int(iterations.get("current", 0) or 0),
            "max": int(iterations.get("max", 0) or 0),
            "source": str(iterations.get("source", "")).strip(),
        },
        "gate": {
            "state": str(gate.get("state", "")).strip().lower(),
            "owner": str(gate.get("owner", "")).strip(),
            "path": str(gate.get("path", "")).strip(),
            "reason": str(gate.get("reason", "")).strip(),
        },
        "phase": str(runtime_state.get("phase", "")).strip(),
        "blocking_reason": str(runtime_state.get("blocking_reason", "")).strip(),
        "needs_user_decision": bool(runtime_state.get("needs_user_decision", False)),
        "decisions_needed_count": pending_user_count,
        "pending_decisions": pending_decisions,
        "latest_result": latest_result,
        "error": dict(runtime_state.get("error", {}) if isinstance(runtime_state.get("error", {}), dict) else {}),
        "recovery": dict(runtime_state.get("recovery", {}) if isinstance(runtime_state.get("recovery", {}), dict) else {}),
        "updated_at": str(runtime_state.get("updated_at", "")).strip(),
        "latest_status_raw": {
            "exit_code": int(latest_status_raw.get("exit_code", 0) or 0),
            "stdout": str(latest_status_raw.get("stdout", "")),
            "stderr": str(latest_status_raw.get("stderr", "")),
        },
        "runtime_state_path": SUPPORT_RUNTIME_STATE_REL.as_posix(),
        "runtime_state": runtime_state,
    }


def ctcp_get_support_context(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    rid = _run_id_from_dir(run_dir)
    status = ctcp_get_status(rid)
    decisions = ctcp_list_decisions_needed(rid)
    current_snapshot = ctcp_get_current_state_snapshot(rid)
    render_snapshot = ctcp_get_render_state_snapshot(rid)
    output_artifacts = ctcp_list_output_artifacts(rid)
    project_manifest = ctcp_get_project_manifest(rid)
    whiteboard = ctcp_dispatch.get_support_whiteboard_context(run_dir)
    frontend_request = _read_json(run_dir / "artifacts" / "frontend_request.json")
    return {
        "run_id": rid,
        "run_dir": str(run_dir),
        "status": status,
        "runtime_state": dict(status.get("runtime_state", {}) if isinstance(status.get("runtime_state", {}), dict) else {}),
        "current_snapshot": current_snapshot,
        "render_snapshot": render_snapshot,
        "decisions": decisions,
        "output_artifacts": output_artifacts,
        "project_manifest": project_manifest,
        "whiteboard": whiteboard,
        "frontend_request": frontend_request,
        "goal": str(frontend_request.get("goal", "")).strip(),
    }


def ctcp_advance(run_id: str, max_steps: int = 1) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    steps = max(1, min(int(max_steps or 1), 32))
    cmd = [
        sys.executable,
        str(ORCHESTRATE_PATH),
        "advance",
        "--run-dir",
        str(run_dir),
        "--max-steps",
        str(steps),
    ]
    result = _run_cmd(cmd, ROOT)
    status = ctcp_get_status(_run_id_from_dir(run_dir))
    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "max_steps": steps,
        "advance": result,
        "status": status,
    }


def ctcp_record_support_turn(
    run_id: str,
    *,
    text: str,
    source: str = "support_bot",
    chat_id: str = "",
    conversation_mode: str = "",
) -> dict[str, Any]:
    message = str(text or "").strip()
    if not message:
        raise BridgeError("support turn text is required")

    run_dir = _resolve_run_dir(run_id)
    row = {
        "schema_version": "ctcp-support-frontend-turn-v1",
        "ts": _now_utc_iso(),
        "chat_id": str(chat_id or "").strip(),
        "source": str(source or "").strip() or "support_bot",
        "conversation_mode": str(conversation_mode or "").strip(),
        "text": message,
    }
    _append_jsonl(run_dir / SUPPORT_FRONTEND_TURNS_REL, row)
    _append_event(
        run_dir,
        "FRONT_SUPPORT_TURN_WRITTEN",
        SUPPORT_FRONTEND_TURNS_REL.as_posix(),
        chat_id=str(chat_id or "").strip(),
        conversation_mode=str(conversation_mode or "").strip(),
    )
    whiteboard = ctcp_dispatch.record_support_turn_whiteboard(
        run_dir=run_dir,
        repo_root=ROOT,
        text=message,
        source=str(source or "").strip() or "support_bot",
        conversation_mode=str(conversation_mode or "").strip(),
        chat_id=str(chat_id or "").strip(),
    )
    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "written_path": SUPPORT_FRONTEND_TURNS_REL.as_posix(),
        "whiteboard": whiteboard,
    }


def ctcp_get_last_report(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    verify_report_path = run_dir / "artifacts" / "verify_report.json"
    report_text = _read_text(REPORT_LAST)
    trace_text = _read_text(run_dir / "TRACE.md")
    verify_doc = _read_json(verify_report_path)

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "repo_report_path": str(REPORT_LAST),
        "repo_report_exists": REPORT_LAST.exists(),
        "repo_report_tail": _tail_lines(report_text, max_lines=120),
        "trace_tail": _tail_lines(trace_text, max_lines=80),
        "verify_report_path": str(verify_report_path),
        "verify_report": verify_doc,
    }


def ctcp_list_output_artifacts(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    rows = _collect_output_artifacts(run_dir)
    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "artifacts": rows,
        "count": len(rows),
    }


def ctcp_get_output_artifact_meta(run_id: str, artifact_ref: str) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    target, row = _resolve_artifact_path(run_dir, artifact_ref)
    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "artifact_id": str(row.get("artifact_id", "")).strip(),
        "rel_path": str(row.get("rel_path", "")).strip(),
        "kind": str(row.get("kind", "")).strip(),
        "mime_type": str(row.get("mime_type", "")).strip(),
        "size_bytes": int(row.get("size_bytes", 0) or 0),
        "sha256": _sha256_hex(target),
        "created_at": str(row.get("created_at", "")).strip(),
    }


def ctcp_read_output_artifact(run_id: str, artifact_ref: str, *, max_text_bytes: int = 65536) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    target, row = _resolve_artifact_path(run_dir, artifact_ref)
    rel_path = str(row.get("rel_path", "")).strip()
    mime_type = str(row.get("mime_type", "")).strip() or _guess_mime_type(target)
    out: dict[str, Any] = {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "artifact_id": str(row.get("artifact_id", "")).strip(),
        "rel_path": rel_path,
        "kind": str(row.get("kind", "")).strip(),
        "mime_type": mime_type,
        "size_bytes": int(row.get("size_bytes", 0) or 0),
        "download_path": str(target),
        "sha256": _sha256_hex(target),
    }
    if mime_type.startswith("text/") or target.suffix.lower() in {".md", ".txt", ".json", ".yaml", ".yml", ".html", ".css", ".js", ".ts"}:
        text = target.read_text(encoding="utf-8", errors="replace")
        max_len = max(0, int(max_text_bytes or 0))
        if max_len > 0 and len(text.encode("utf-8", errors="replace")) > max_len:
            encoded = text.encode("utf-8", errors="replace")
            text = encoded[:max_len].decode("utf-8", errors="replace")
            out["truncated"] = True
        else:
            out["truncated"] = False
        out["text"] = text
    return out


def _runtime_to_visible_state(runtime_state: dict[str, Any]) -> str:
    phase = str(runtime_state.get("phase", "")).strip().upper()
    if phase == "WAIT_USER_DECISION":
        return "WAITING_FOR_DECISION"
    if phase == "RECOVER":
        return "BLOCKED_NEEDS_INPUT"
    if phase in {"FINALIZE", "DELIVER", "DELIVERED"}:
        return "DONE"
    if phase in {"EXECUTE", "VERIFY"}:
        return "EXECUTING"
    return "UNDERSTOOD"


def ctcp_get_current_state_snapshot(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    status = ctcp_get_status(_run_id_from_dir(run_dir))
    runtime_state = status.get("runtime_state", {})
    if not isinstance(runtime_state, dict):
        runtime_state = {}
    frontend_request = _read_json(run_dir / "artifacts" / "frontend_request.json")
    goal = str(frontend_request.get("goal", "")).strip() or str(runtime_state.get("goal", "")).strip()
    gate = runtime_state.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    pending = runtime_state.get("pending_decisions", [])
    if not isinstance(pending, list):
        pending = []
    blocking_question = ""
    for item in pending:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).strip().lower() != "pending":
            continue
        blocking_question = str(item.get("question", "") or item.get("question_hint", "") or item.get("reason", "")).strip()
        if blocking_question:
            break
    if not blocking_question:
        blocking_question = str(runtime_state.get("blocking_reason", "")).strip()
    proof_refs = runtime_state.get("proof_refs", [])
    if not isinstance(proof_refs, list):
        proof_refs = []
    authoritative_stage = str(runtime_state.get("phase", "")).strip().upper() or "EXECUTE"
    return {
        "task_id": _run_id_from_dir(run_dir),
        "authoritative_stage": authoritative_stage,
        "visible_state": _runtime_to_visible_state(runtime_state),
        "conversation_mode": "",
        "current_task_goal": goal,
        "known_facts": [],
        "missing_fields": [],
        "last_confirmed_items": [],
        "current_blocker": str(runtime_state.get("blocking_reason", "")).strip() or str(gate.get("reason", "")).strip(),
        "blocking_question": blocking_question,
        "next_action": str(gate.get("reason", "")).strip(),
        "proof_refs": proof_refs,
        "verify_result": str(runtime_state.get("verify_result", "")).strip().upper(),
        "snapshot_source": "bridge_runtime_mapping",
        "updated_at": str(runtime_state.get("updated_at", "")).strip(),
    }


def ctcp_get_render_state_snapshot(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    current = ctcp_get_current_state_snapshot(_run_id_from_dir(run_dir))
    status = ctcp_get_status(_run_id_from_dir(run_dir))
    runtime_state = status.get("runtime_state", {})
    if not isinstance(runtime_state, dict):
        runtime_state = {}
    pending = runtime_state.get("pending_decisions", [])
    if not isinstance(pending, list):
        pending = []
    decision_cards: list[dict[str, Any]] = []
    followups: list[str] = []
    for item in pending:
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).strip().lower() != "pending":
            continue
        question = str(item.get("question", "") or item.get("question_hint", "") or item.get("reason", "")).strip()
        if question and question not in followups and len(followups) < 3:
            followups.append(question)
        decision_cards.append(
            {
                "decision_id": str(item.get("decision_id", "")).strip(),
                "question": question,
                "target_path": str(item.get("target_path", "")).strip(),
                "status": str(item.get("status", "")).strip().lower(),
            }
        )
    visible_state = str(current.get("visible_state", "")).strip() or "UNDERSTOOD"
    ui_badge = "in_progress"
    if visible_state == "WAITING_FOR_DECISION":
        ui_badge = "needs_decision"
    elif visible_state == "DONE":
        ui_badge = "done"
    elif visible_state == "BLOCKED_NEEDS_INPUT":
        ui_badge = "blocked"
    progress_summary = str(current.get("current_blocker", "")).strip() or "runtime progressing"
    return {
        "task_id": str(current.get("task_id", "")).strip(),
        "ui_badge": ui_badge,
        "reply_style": "progressive",
        "followup_questions": followups,
        "decision_cards": decision_cards[:8],
        "visible_state": visible_state,
        "progress_summary": progress_summary,
        "proof_refs": list(current.get("proof_refs", [])) if isinstance(current.get("proof_refs", []), list) else [],
        "snapshot_source": "bridge_runtime_mapping",
        "updated_at": str(current.get("updated_at", "")).strip(),
    }


def ctcp_list_decisions_needed(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    runtime_state = _load_runtime_state(run_dir, refresh=True)
    pending_rows_raw = runtime_state.get("pending_decisions", [])
    if not isinstance(pending_rows_raw, list):
        pending_rows_raw = []
    decisions: list[dict[str, Any]] = []
    for item in pending_rows_raw:
        if not isinstance(item, dict):
            continue
        row = _normalize_decision_row(item, now_ts=_now_utc_iso(), status_fallback="pending")
        if not str(row.get("decision_id", "")).strip():
            continue
        decisions.append(row)

    pending_count = sum(
        1 for row in decisions if str(row.get("status", "")).strip().lower() == "pending"
    )
    submitted_count = sum(
        1 for row in decisions if str(row.get("status", "")).strip().lower() == "submitted"
    )

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "count": int(pending_count),
        "pending_count": int(pending_count),
        "submitted_count": int(submitted_count),
        "open_count": len(decisions),
        "decisions": decisions,
    }


def ctcp_submit_decision(run_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise BridgeError("decision must be an object")

    run_dir = _resolve_run_dir(run_id)
    runtime_state = _load_runtime_state(run_dir, refresh=True)
    pending = runtime_state.get("pending_decisions", [])
    if not isinstance(pending, list):
        pending = []

    decision_id = str(decision.get("decision_id", "")).strip()
    prompt_path = str(decision.get("prompt_path", "")).strip()
    target_path = str(decision.get("target_path", "")).strip()
    content = decision.get("content", "")

    selected: dict[str, Any] | None = None
    for row in pending:
        if not isinstance(row, dict):
            continue
        if decision_id and str(row.get("decision_id", "")).strip() == decision_id:
            selected = row
            break
        if prompt_path and str(row.get("prompt_path", "")).strip() == prompt_path:
            selected = row
            break
        if target_path and str(row.get("target_path", "")).strip() == target_path:
            selected = row
            break

    if selected is None:
        raise BridgeError("decision target not found in pending decision list")
    selected_status = str(selected.get("status", "")).strip().lower()
    if selected_status and selected_status != "pending":
        raise BridgeError(f"decision is already {selected_status}; wait for backend consume confirmation")

    final_target = str(selected.get("target_path", "")).strip()
    if not final_target:
        raise BridgeError("selected decision has no writable target_path")

    target_abs = (run_dir / final_target).resolve()
    _ensure_within_run_dir(run_dir, target_abs)

    if isinstance(content, (dict, list)):
        payload = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    else:
        payload = str(content or "")
        if final_target.lower().endswith(".json"):
            try:
                doc = json.loads(payload)
            except Exception as exc:
                raise BridgeError(f"decision content must be valid JSON for {final_target}: {exc}") from exc
            payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        elif not payload.endswith("\n"):
            payload += "\n"

    _write_text(target_abs, payload)
    _append_event(
        run_dir,
        "FRONT_DECISION_SUBMITTED",
        final_target,
        decision_id=str(selected.get("decision_id", "")),
        prompt_path=str(selected.get("prompt_path", "")),
    )

    decision_id_selected = str(selected.get("decision_id", "")).strip()
    state_doc = _read_runtime_state(run_dir)
    if not state_doc:
        state_doc = runtime_state if isinstance(runtime_state, dict) else {}
    now_ts = _now_utc_iso()
    submission_hash = str(state_doc.get("core_hash", "")).strip()
    updated_any = False
    for key in ("decisions", "pending_decisions"):
        rows = state_doc.get(key, [])
        if not isinstance(rows, list):
            continue
        for item in rows:
            if not isinstance(item, dict):
                continue
            if str(item.get("decision_id", "")).strip() != decision_id_selected:
                continue
            item["status"] = "submitted"
            item["submitted_at"] = now_ts
            item["submission_state_hash"] = submission_hash
            item["consumed_at"] = ""
            updated_any = True
    if updated_any:
        pending_rows = state_doc.get("pending_decisions", [])
        if isinstance(pending_rows, list):
            pending_user_count = sum(
                1 for row in pending_rows if isinstance(row, dict) and str(row.get("status", "")).strip().lower() == "pending"
            )
            state_doc["needs_user_decision"] = bool(pending_user_count > 0)
            state_doc["decisions_needed_count"] = int(pending_user_count)
            if pending_user_count == 0 and str(state_doc.get("phase", "")).strip() == "WAIT_USER_DECISION":
                state_doc["phase"] = "EXECUTE"
            if pending_user_count == 0:
                state_doc["blocking_reason"] = "decision_submitted_waiting_backend_consume"
        state_doc["updated_at"] = now_ts
        _write_runtime_state(run_dir, state_doc)

    refreshed_state = _refresh_runtime_state(run_dir)
    refreshed_decisions = refreshed_state.get("decisions", [])
    if not isinstance(refreshed_decisions, list):
        refreshed_decisions = []
    resolved_row: dict[str, Any] = {}
    for item in refreshed_decisions:
        if not isinstance(item, dict):
            continue
        if str(item.get("decision_id", "")).strip() == decision_id_selected:
            resolved_row = item
            break
    decision_status = str(resolved_row.get("status", "submitted")).strip().lower() or "submitted"
    backend_acknowledged = decision_status == "consumed"

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "decision_id": decision_id_selected,
        "target_path": final_target,
        "written": True,
        "decision_status": decision_status,
        "backend_acknowledged": backend_acknowledged,
        "remaining_decisions": int(refreshed_state.get("decisions_needed_count", 0) or 0),
        "needs_user_decision": bool(refreshed_state.get("needs_user_decision", False)),
        "updated_at": str(refreshed_state.get("updated_at", "")),
    }


def ctcp_upload_artifact(run_id: str, file: str | dict[str, Any]) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    if isinstance(file, dict):
        src_text = str(file.get("source_path", "")).strip()
        dest_rel = str(file.get("dest_rel", "")).strip()
    else:
        src_text = str(file or "").strip()
        dest_rel = ""

    if not src_text:
        raise BridgeError("file path is required")
    src = Path(src_text).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise BridgeError(f"upload file not found: {src}")

    if dest_rel:
        dest = (run_dir / dest_rel).resolve()
    else:
        dest = (run_dir / "artifacts" / "frontend_uploads" / src.name).resolve()
        dest_rel = dest.relative_to(run_dir).as_posix()
    _ensure_within_run_dir(run_dir, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    _append_event(run_dir, "FRONT_ARTIFACT_UPLOADED", dest_rel, source=str(src))

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "source_path": str(src),
        "dest_path": str(dest),
        "dest_rel": dest_rel,
        "size_bytes": int(dest.stat().st_size),
        "mime_type": _guess_mime_type(dest),
        "uploaded_at": _now_utc_iso(),
    }


# Backend interface aliases (contract-facing names)
def create_run(goal: str, constraints: dict[str, Any] | None = None, attachments: list[str] | None = None) -> dict[str, Any]:
    return ctcp_new_run(goal=goal, constraints=constraints, attachments=attachments)


def get_run_status(run_id: str = "") -> dict[str, Any]:
    return ctcp_get_status(run_id=run_id)


def advance_run(run_id: str, max_steps: int = 1) -> dict[str, Any]:
    return ctcp_advance(run_id=run_id, max_steps=max_steps)


def list_pending_decisions(run_id: str = "") -> dict[str, Any]:
    return ctcp_list_decisions_needed(run_id=run_id)


def submit_decision(run_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    return ctcp_submit_decision(run_id=run_id, decision=decision)


def upload_input_artifact(run_id: str, file: str | dict[str, Any]) -> dict[str, Any]:
    return ctcp_upload_artifact(run_id=run_id, file=file)


def get_last_report(run_id: str = "") -> dict[str, Any]:
    return ctcp_get_last_report(run_id=run_id)


def get_support_context(run_id: str = "") -> dict[str, Any]:
    return ctcp_get_support_context(run_id=run_id)


def record_support_turn(
    run_id: str,
    *,
    text: str,
    source: str = "support_bot",
    chat_id: str = "",
    conversation_mode: str = "",
) -> dict[str, Any]:
    return ctcp_record_support_turn(
        run_id=run_id,
        text=text,
        source=source,
        chat_id=chat_id,
        conversation_mode=conversation_mode,
    )


def list_output_artifacts(run_id: str = "") -> dict[str, Any]:
    return ctcp_list_output_artifacts(run_id=run_id)


def get_output_artifact_meta(run_id: str, artifact_ref: str) -> dict[str, Any]:
    return ctcp_get_output_artifact_meta(run_id=run_id, artifact_ref=artifact_ref)


def read_output_artifact(run_id: str, artifact_ref: str, *, max_text_bytes: int = 65536) -> dict[str, Any]:
    return ctcp_read_output_artifact(run_id=run_id, artifact_ref=artifact_ref, max_text_bytes=max_text_bytes)


def get_project_manifest(run_id: str = "") -> dict[str, Any]:
    return ctcp_get_project_manifest(run_id=run_id)


def get_current_state_snapshot(run_id: str = "") -> dict[str, Any]:
    return ctcp_get_current_state_snapshot(run_id=run_id)


def get_render_state_snapshot(run_id: str = "") -> dict[str, Any]:
    return ctcp_get_render_state_snapshot(run_id=run_id)


__all__ = [
    "BridgeError",
    "ctcp_new_run",
    "ctcp_get_support_context",
    "ctcp_get_status",
    "ctcp_advance",
    "ctcp_record_support_turn",
    "ctcp_get_last_report",
    "ctcp_list_decisions_needed",
    "ctcp_submit_decision",
    "ctcp_list_output_artifacts",
    "ctcp_get_output_artifact_meta",
    "ctcp_read_output_artifact",
    "ctcp_get_project_manifest",
    "ctcp_get_current_state_snapshot",
    "ctcp_get_render_state_snapshot",
    "ctcp_upload_artifact",
    "create_run",
    "get_run_status",
    "advance_run",
    "list_pending_decisions",
    "submit_decision",
    "upload_input_artifact",
    "get_last_report",
    "get_support_context",
    "record_support_turn",
    "list_output_artifacts",
    "get_output_artifact_meta",
    "read_output_artifact",
    "get_project_manifest",
    "get_current_state_snapshot",
    "get_render_state_snapshot",
]
