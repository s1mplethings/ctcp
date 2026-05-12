from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ANALYSIS_TARGET_PATH = "artifacts/analysis.md"
ANALYSIS_PROGRESS_PATH = "artifacts/analysis_progress.json"
ANALYSIS_RAW_PATH = "artifacts/analysis.raw.txt"
ANALYSIS_PARTIAL_PATH = "artifacts/analysis.partial.md"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_rel_path(value: str) -> str:
    return str(value or "").strip().replace("\\", "/")


def is_analysis_target(target_path: str) -> bool:
    return normalize_rel_path(target_path).lower().endswith(ANALYSIS_TARGET_PATH)


def is_analysis_request(request: dict[str, Any]) -> bool:
    return is_analysis_target(str((request or {}).get("target_path", "")))


def progress_path(run_dir: Path) -> Path:
    return run_dir / ANALYSIS_PROGRESS_PATH


def raw_path(run_dir: Path) -> Path:
    return run_dir / ANALYSIS_RAW_PATH


def partial_path(run_dir: Path) -> Path:
    return run_dir / ANALYSIS_PARTIAL_PATH


def target_path(run_dir: Path) -> Path:
    return run_dir / ANALYSIS_TARGET_PATH


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_progress(run_dir: Path) -> dict[str, Any]:
    return _read_json(progress_path(run_dir))


def _duration(doc: dict[str, Any]) -> float:
    started = float(doc.get("_started_monotonic", 0.0) or 0.0)
    if started <= 0:
        started = float(doc.get("started_epoch_seconds", 0.0) or 0.0)
        if started <= 0:
            return float(doc.get("duration_seconds", 0.0) or 0.0)
        return round(max(0.0, time.time() - started), 3)
    return round(max(0.0, time.monotonic() - started), 3)


def _base_doc(
    *,
    run_dir: Path,
    request: dict[str, Any],
    prompt_path: str = "",
    provider: str = "",
    provider_model: str = "",
    provider_timeout_seconds: float | int | None = None,
    cmd: str = "",
    prompt_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    previous = load_progress(run_dir)
    now = now_iso()
    doc: dict[str, Any] = {
        "stage": "analysis",
        "status": "running",
        "owner": str(request.get("owner", "") or request.get("role", "") or "chair"),
        "role": str(request.get("role", "")),
        "action": str(request.get("action", "")),
        "target_path": ANALYSIS_TARGET_PATH,
        "prompt_path": normalize_rel_path(prompt_path),
        "provider": str(provider or "api_agent"),
        "provider_model": str(provider_model or ""),
        "provider_timeout_seconds": provider_timeout_seconds,
        "prompt_char_count": 0,
        "prompt_estimated_tokens": 0,
        "output_contract": "",
        "max_output_tokens": 0,
        "analysis_profile": "default",
        "cmd": str(cmd or ""),
        "started_at": previous.get("started_at") if previous.get("status") == "running" else now,
        "updated_at": now,
        "provider_call_started_at": "",
        "provider_call_completed_at": "",
        "parser_started_at": "",
        "parser_completed_at": "",
        "artifact_write_started_at": "",
        "artifact_write_completed_at": "",
        "duration_seconds": 0.0,
        "started_epoch_seconds": time.time(),
        "last_event": "analysis_progress_started",
        "error": None,
        "raw_response_path": ANALYSIS_RAW_PATH if raw_path(run_dir).exists() else "",
        "partial_artifact_path": ANALYSIS_PARTIAL_PATH if partial_path(run_dir).exists() else "",
        "raw_response_exists": raw_path(run_dir).exists(),
        "partial_artifact_exists": partial_path(run_dir).exists(),
        "target_exists": target_path(run_dir).exists(),
        "resume_possible": raw_path(run_dir).exists() and not target_path(run_dir).exists(),
        "_started_monotonic": time.monotonic(),
    }
    if isinstance(prompt_budget, dict):
        for key in ("prompt_char_count", "prompt_estimated_tokens", "output_contract", "max_output_tokens", "analysis_profile"):
            doc[key] = prompt_budget.get(key, doc.get(key))
    if previous:
        doc["previous_status"] = str(previous.get("status", ""))
        doc["previous_error"] = previous.get("error")
        doc["previous_last_event"] = str(previous.get("last_event", ""))
    return doc


def start_progress(
    *,
    run_dir: Path,
    request: dict[str, Any],
    prompt_path: str = "",
    provider: str = "",
    provider_model: str = "",
    provider_timeout_seconds: float | int | None = None,
    cmd: str = "",
    prompt_budget: dict[str, Any] | None = None,
    last_event: str = "analysis_progress_started",
) -> dict[str, Any]:
    doc = _base_doc(
        run_dir=run_dir,
        request=request,
        prompt_path=prompt_path,
        provider=provider,
        provider_model=provider_model,
        provider_timeout_seconds=provider_timeout_seconds,
        cmd=cmd,
        prompt_budget=prompt_budget,
    )
    doc["last_event"] = last_event
    _write_json(progress_path(run_dir), _public_doc(doc))
    return load_progress(run_dir)


def _public_doc(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    out.pop("_started_monotonic", None)
    return out


def update_progress(run_dir: Path, *, status: str | None = None, last_event: str, error: str | None = None, **fields: Any) -> dict[str, Any]:
    doc = load_progress(run_dir)
    if not doc:
        doc = {
            "stage": "analysis",
            "status": status or "running",
            "target_path": ANALYSIS_TARGET_PATH,
            "started_at": now_iso(),
        }
    if status:
        doc["status"] = status
    doc["updated_at"] = now_iso()
    doc["last_event"] = last_event
    if error is not None:
        doc["error"] = error
    for key, value in fields.items():
        doc[key] = value
    doc["raw_response_exists"] = raw_path(run_dir).exists()
    doc["partial_artifact_exists"] = partial_path(run_dir).exists()
    doc["target_exists"] = target_path(run_dir).exists()
    doc["raw_response_path"] = ANALYSIS_RAW_PATH if raw_path(run_dir).exists() else str(doc.get("raw_response_path", ""))
    doc["partial_artifact_path"] = ANALYSIS_PARTIAL_PATH if partial_path(run_dir).exists() else str(doc.get("partial_artifact_path", ""))
    doc["resume_possible"] = raw_path(run_dir).exists() and not target_path(run_dir).exists()
    doc["duration_seconds"] = _duration(doc)
    _write_json(progress_path(run_dir), _public_doc(doc))
    return load_progress(run_dir)


def mark_provider_started(run_dir: Path, *, cmd: str = "") -> dict[str, Any]:
    return update_progress(
        run_dir,
        status="running",
        last_event="provider_call_started",
        provider_call_started_at=now_iso(),
        cmd=cmd,
    )


def mark_provider_completed(run_dir: Path, *, rc: int = 0) -> dict[str, Any]:
    return update_progress(
        run_dir,
        status="running",
        last_event="provider_call_completed",
        provider_call_completed_at=now_iso(),
        provider_return_code=rc,
    )


def mark_parser_started(run_dir: Path) -> dict[str, Any]:
    return update_progress(run_dir, status="running", last_event="parser_started", parser_started_at=now_iso())


def mark_parser_completed(run_dir: Path) -> dict[str, Any]:
    return update_progress(run_dir, status="running", last_event="parser_completed", parser_completed_at=now_iso())


def mark_artifact_write_started(run_dir: Path) -> dict[str, Any]:
    return update_progress(run_dir, status="running", last_event="artifact_write_started", artifact_write_started_at=now_iso())


def mark_artifact_write_completed(run_dir: Path) -> dict[str, Any]:
    return update_progress(
        run_dir,
        status="completed",
        last_event="artifact_write_completed",
        artifact_write_completed_at=now_iso(),
        duration_seconds=load_progress(run_dir).get("duration_seconds", 0.0),
    )


def mark_timeout(run_dir: Path, *, error: str, rc: int = 124) -> dict[str, Any]:
    return update_progress(
        run_dir,
        status="timeout",
        last_event="provider_call_timeout",
        error=error,
        provider_return_code=rc,
        provider_call_completed_at=now_iso(),
    )


def mark_failed(run_dir: Path, *, last_event: str, error: str, **fields: Any) -> dict[str, Any]:
    return update_progress(run_dir, status="failed", last_event=last_event, error=error, **fields)


def preserve_raw_response(run_dir: Path, text: str) -> Path:
    path = raw_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")
    update_progress(run_dir, status="running", last_event="raw_response_preserved", raw_response_path=ANALYSIS_RAW_PATH)
    return path


def preserve_partial_artifact(run_dir: Path, text: str) -> Path:
    path = partial_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(text or ""), encoding="utf-8")
    update_progress(run_dir, status="running", last_event="partial_artifact_preserved", partial_artifact_path=ANALYSIS_PARTIAL_PATH)
    return path


def status_line(run_dir: Path) -> str:
    doc = load_progress(run_dir)
    if not doc:
        return ""
    bits = [
        f"status={doc.get('status', '')}",
        f"last_event={doc.get('last_event', '')}",
        f"duration_seconds={doc.get('duration_seconds', 0)}",
    ]
    if doc.get("error"):
        bits.append(f"error={doc.get('error')}")
    if doc.get("resume_possible"):
        bits.append("resume_possible=true")
    return "[ctcp_orchestrate] analysis_progress " + " ".join(str(bit) for bit in bits if str(bit).strip())
