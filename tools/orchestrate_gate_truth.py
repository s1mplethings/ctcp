from __future__ import annotations

import json
from pathlib import Path


def failure_doc_reason(run_dir: Path, *, target_path: str) -> str:
    path = run_dir / "artifacts" / "context_pack.failure.json"
    if not path.exists():
        return ""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(doc, dict):
        return ""
    if str(doc.get("status", "")).strip().lower() != "failed":
        return ""
    if str(doc.get("target_path", "")).strip() not in {"", target_path}:
        return ""
    return str(doc.get("message", "")).strip()


def latest_step_meta_reason(run_dir: Path, *, target_path: str) -> str:
    path = run_dir / "step_meta.jsonl"
    if not path.exists():
        return ""
    rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for raw in reversed(rows):
        text = raw.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except Exception:
            continue
        if not isinstance(row, dict):
            continue
        if str(row.get("status", "")).strip().lower() == "executed":
            continue
        outputs = row.get("outputs", [])
        if not isinstance(outputs, list) or target_path not in [str(x).strip() for x in outputs]:
            continue
        reason = str(row.get("error", "")).strip()
        if reason:
            return reason
    return ""


def artifact_missing_reason(run_dir: Path, *, target_path: str, fallback: str) -> str:
    return (
        failure_doc_reason(run_dir, target_path=target_path)
        or latest_step_meta_reason(run_dir, target_path=target_path)
        or fallback
    )
