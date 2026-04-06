from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable


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
        return False
    if rel.startswith("artifacts/support_decisions/"):
        return False
    return True


def _artifact_row(
    run_dir: Path,
    file_path: Path,
    *,
    guess_mime_type: Callable[[Path], str],
    file_ts_iso: Callable[[Path], str],
) -> dict[str, Any]:
    rel_path = file_path.resolve().relative_to(run_dir.resolve()).as_posix()
    artifact_id = hashlib.sha1(rel_path.encode("utf-8", errors="replace")).hexdigest()
    return {
        "artifact_id": artifact_id,
        "rel_path": rel_path,
        "kind": _classify_artifact(rel_path),
        "mime_type": guess_mime_type(file_path),
        "size_bytes": int(file_path.stat().st_size),
        "created_at": file_ts_iso(file_path),
    }


def _collect_output_artifacts(
    run_dir: Path,
    *,
    guess_mime_type: Callable[[Path], str],
    file_ts_iso: Callable[[Path], str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.resolve().relative_to(run_dir.resolve()).as_posix()
        if not _is_output_artifact_rel(rel_path):
            continue
        rows.append(_artifact_row(run_dir, path, guess_mime_type=guess_mime_type, file_ts_iso=file_ts_iso))
    return rows


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


def _build_current_state_snapshot(*, run_id: str, goal: str, runtime_state: dict[str, Any]) -> dict[str, Any]:
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
        "task_id": run_id,
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


def _build_render_state_snapshot(*, current_snapshot: dict[str, Any], runtime_state: dict[str, Any]) -> dict[str, Any]:
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
    visible_state = str(current_snapshot.get("visible_state", "")).strip() or "UNDERSTOOD"
    ui_badge = "in_progress"
    if visible_state == "WAITING_FOR_DECISION":
        ui_badge = "needs_decision"
    elif visible_state == "DONE":
        ui_badge = "done"
    elif visible_state == "BLOCKED_NEEDS_INPUT":
        ui_badge = "blocked"
    progress_summary = str(current_snapshot.get("current_blocker", "")).strip() or "runtime progressing"
    return {
        "task_id": str(current_snapshot.get("task_id", "")).strip(),
        "ui_badge": ui_badge,
        "reply_style": "progressive",
        "followup_questions": followups,
        "decision_cards": decision_cards[:8],
        "visible_state": visible_state,
        "progress_summary": progress_summary,
        "proof_refs": list(current_snapshot.get("proof_refs", [])) if isinstance(current_snapshot.get("proof_refs", []), list) else [],
        "snapshot_source": "bridge_runtime_mapping",
        "updated_at": str(current_snapshot.get("updated_at", "")).strip(),
    }
