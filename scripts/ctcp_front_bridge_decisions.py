from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable

_USER_DECISION_STATUSES = {"pending", "submitted"}
_DECISION_STATUSES = {"pending", "submitted", "consumed", "rejected", "expired"}


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


def _scan_pending_decisions_from_legacy(
    run_dir: Path,
    *,
    ensure_within_run_dir: Callable[[Path, Path], None],
    file_ts_iso: Callable[[Path], str],
    now_utc_iso: Callable[[], str],
    parse_outbox_prompt: Callable[[Path], dict[str, str]],
    read_text: Callable[[Path], str],
) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    outbox_dir = run_dir / "outbox"
    for prompt in sorted(outbox_dir.glob("*.md")) if outbox_dir.exists() else []:
        parsed = parse_outbox_prompt(prompt)
        target_rel = str(parsed.get("target_path", "")).strip()
        if not target_rel:
            target_rel = _decision_default_target(f"outbox:{prompt.stem}")
        target_abs = (run_dir / target_rel).resolve()
        ensure_within_run_dir(run_dir, target_abs)
        if target_abs.exists():
            continue
        expected_format, schema = _decision_format(target_rel)
        question = str(parsed.get("question_hint", "")).strip() or str(parsed.get("reason", "")).strip()
        decisions.append(
            _normalize_decision_row(
                {
                    "decision_id": f"outbox:{prompt.stem}",
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
                    "created_at": file_ts_iso(prompt),
                },
                now_ts=now_utc_iso(),
            )
        )

    questions_path = run_dir / "QUESTIONS.md"
    if questions_path.exists():
        created_at = file_ts_iso(questions_path)
        rows = [ln.strip() for ln in read_text(questions_path).splitlines() if ln.strip()]
        for idx, row in enumerate(rows, start=1):
            if row.startswith("#"):
                continue
            if row.startswith("-"):
                row = row.lstrip("-").strip()
            if not row:
                continue
            target_rel = _decision_default_target(f"questions:{idx}")
            target_abs = (run_dir / target_rel).resolve()
            ensure_within_run_dir(run_dir, target_abs)
            if target_abs.exists():
                continue
            decisions.append(
                _normalize_decision_row(
                    {
                        "decision_id": f"questions:{idx}",
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
                    now_ts=now_utc_iso(),
                )
            )
    return decisions


def _decision_sort_key(row: dict[str, Any]) -> str:
    for key in ("consumed_at", "submitted_at", "created_at"):
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


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
        if decision_id:
            merged[decision_id] = row
    deduped = list(merged.values())
    deduped.sort(key=_decision_sort_key)
    return deduped, has_explicit


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
    previous_rows: dict[str, dict[str, Any]] = {}
    for item in previous_rows_raw:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_decision_row(item, now_ts=now_ts, status_fallback="pending")
        decision_id = str(normalized.get("decision_id", "")).strip()
        if decision_id:
            previous_rows[decision_id] = normalized

    pending_rows: dict[str, dict[str, Any]] = {}
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


def _decision_registry_with_fallback(
    *,
    run_dir: Path,
    previous_state: dict[str, Any],
    now_ts: str,
    core_hash_seed: str,
    ensure_within_run_dir: Callable[[Path, Path], None],
    file_ts_iso: Callable[[Path], str],
    now_utc_iso: Callable[[], str],
    parse_outbox_prompt: Callable[[Path], dict[str, str]],
    read_text: Callable[[Path], str],
) -> tuple[list[dict[str, Any]], str, bool]:
    canonical_rows, canonical_explicit = _canonical_decisions_from_runtime_state(previous_state, now_ts=now_ts)
    if canonical_explicit:
        return canonical_rows, "canonical", False

    legacy_rows = _scan_pending_decisions_from_legacy(
        run_dir,
        ensure_within_run_dir=ensure_within_run_dir,
        file_ts_iso=file_ts_iso,
        now_utc_iso=now_utc_iso,
        parse_outbox_prompt=parse_outbox_prompt,
        read_text=read_text,
    )
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
