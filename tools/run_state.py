#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any


def create_run_id() -> str:
    return dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")


def _iso_now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _normalize_state(doc: dict[str, Any]) -> dict[str, Any]:
    run_id = str(doc.get("run_id", "")).strip() or create_run_id()
    phase = str(doc.get("phase", "")).strip() or "init"
    round_value = doc.get("round", 1)
    try:
        round_number = max(1, int(round_value))
    except Exception:
        round_number = 1

    artifacts = doc.get("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}

    last_verify = doc.get("last_verify", {})
    if not isinstance(last_verify, dict):
        last_verify = {}
    rc_raw = last_verify.get("rc", None)
    try:
        rc = int(rc_raw) if rc_raw is not None else None
    except Exception:
        rc = None
    verify_paths = last_verify.get("paths", {})
    if not isinstance(verify_paths, dict):
        verify_paths = {}
    last_verify = {
        "rc": rc,
        "paths": verify_paths,
        "summary": str(last_verify.get("summary", "")),
    }

    last_error = str(doc.get("last_error", ""))

    timestamps = doc.get("timestamps", {})
    if not isinstance(timestamps, dict):
        timestamps = {}
    created_at = str(timestamps.get("created_at", "")).strip() or _iso_now()
    updated_at = str(timestamps.get("updated_at", "")).strip() or created_at

    return {
        "run_id": run_id,
        "phase": phase,
        "round": round_number,
        "artifacts": artifacts,
        "last_verify": last_verify,
        "last_error": last_error,
        "timestamps": {
            "created_at": created_at,
            "updated_at": updated_at,
        },
    }


def load_state(run_dir: str | Path) -> dict[str, Any]:
    run_path = Path(run_dir)
    state_path = run_path / "state.json"
    if not state_path.exists():
        return _normalize_state({})
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    return _normalize_state(raw)


def save_state(run_dir: str | Path, state: dict[str, Any]) -> dict[str, Any]:
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_state(state if isinstance(state, dict) else {})
    normalized["timestamps"]["updated_at"] = _iso_now()
    state_path = run_path / "state.json"
    state_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return normalized
