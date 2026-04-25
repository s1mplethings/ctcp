from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

RUN_MANIFEST_REL = Path("artifacts") / "run_manifest.json"
SCHEMA_VERSION = "ctcp-run-manifest-v1"


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _rel(path: Path, run_dir: Path) -> str:
    try:
        return path.resolve().relative_to(run_dir.resolve()).as_posix()
    except Exception:
        return path.as_posix()


def _run_doc(run_dir: Path) -> dict[str, Any]:
    return _read_json(run_dir / "RUN.json")


def _default_manifest(run_dir: Path) -> dict[str, Any]:
    run_doc = _run_doc(run_dir)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(run_doc.get("run_id", run_dir.resolve().name)).strip() or run_dir.resolve().name,
        "workflow_name": "ctcp_default_mainline",
        "execution_lane": "default",
        "context_pack_present": False,
        "context_pack_path": "artifacts/context_pack.json",
        "adlc_phase": "",
        "adlc_plan_present": False,
        "adlc_gate_status": "",
        "whiteboard_present": False,
        "whiteboard_path": "artifacts/support_whiteboard.json",
        "bridge_present": False,
        "bridge_output_present": False,
        "bridge_output_refs": [],
        "delivery_artifacts": [],
        "gates_passed": [],
        "first_failure_gate": "",
        "first_failure_reason": "",
        "final_status": str(run_doc.get("status", "")).strip().lower() or "created",
        "updated_at": _now_utc_iso(),
    }


def _dedupe_strings(values: Any) -> list[str]:
    out: list[str] = []
    rows = values if isinstance(values, list) else []
    for item in rows:
        text = str(item or "").strip().replace("\\", "/")
        if text and text not in out:
            out.append(text)
    return out


def load_run_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / RUN_MANIFEST_REL
    base = _default_manifest(run_dir)
    current = _read_json(path)
    if current:
        base.update(current)
    return base


def refresh_observed_fields(manifest: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    run_doc = _run_doc(run_dir)
    context_pack = run_dir / "artifacts" / "context_pack.json"
    plan_paths = [run_dir / "artifacts" / "PLAN.md", run_dir / "artifacts" / "plan.md"]
    whiteboard = run_dir / "artifacts" / "support_whiteboard.json"
    frontend_request = run_dir / "artifacts" / "frontend_request.json"
    verify_report = run_dir / "artifacts" / "verify_report.json"

    manifest["run_id"] = str(run_doc.get("run_id", manifest.get("run_id", run_dir.resolve().name))).strip() or run_dir.resolve().name
    manifest["context_pack_present"] = context_pack.exists()
    manifest["context_pack_path"] = "artifacts/context_pack.json"
    manifest["adlc_plan_present"] = any(path.exists() for path in plan_paths)
    manifest["whiteboard_present"] = whiteboard.exists()
    manifest["whiteboard_path"] = "artifacts/support_whiteboard.json"
    manifest["bridge_present"] = bool(manifest.get("bridge_present", False)) or frontend_request.exists()
    manifest["final_status"] = str(run_doc.get("status", manifest.get("final_status", ""))).strip().lower() or str(
        manifest.get("final_status", "created")
    )
    if verify_report.exists() and "verify_report" not in _dedupe_strings(manifest.get("gates_passed", [])):
        report = _read_json(verify_report)
        if str(report.get("result", "")).strip().upper() == "PASS":
            manifest["gates_passed"] = _dedupe_strings([*manifest.get("gates_passed", []), "verify_report"])
    return manifest


def update_run_manifest(run_dir: Path, **updates: Any) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    manifest = load_run_manifest(run_dir)
    manifest = refresh_observed_fields(manifest, run_dir)
    for key, value in updates.items():
        if key in {"bridge_output_refs", "delivery_artifacts", "gates_passed"}:
            manifest[key] = _dedupe_strings([*manifest.get(key, []), *(value if isinstance(value, list) else [value])])
            continue
        if value is not None:
            manifest[key] = value
    manifest["updated_at"] = _now_utc_iso()
    _write_json(run_dir / RUN_MANIFEST_REL, manifest)
    return manifest


def update_librarian_context(run_dir: Path, *, success: bool, reason: str = "") -> dict[str, Any]:
    return update_run_manifest(
        run_dir,
        execution_lane="default",
        context_pack_present=bool(success),
        context_pack_path="artifacts/context_pack.json",
        adlc_phase="context_pack" if success else "context_pack_failed",
        adlc_gate_status="context_pack_ready" if success else "context_pack_failed",
        first_failure_gate="" if success else "librarian/context_pack",
        first_failure_reason="" if success else str(reason or "context_pack failed"),
    )


def update_adlc_state(
    run_dir: Path,
    *,
    phase: str = "",
    gate_status: str = "",
    final_status: str = "",
    first_failure_gate: str = "",
    first_failure_reason: str = "",
    gates_passed: list[str] | None = None,
) -> dict[str, Any]:
    return update_run_manifest(
        run_dir,
        adlc_phase=str(phase or "").strip() or None,
        adlc_gate_status=str(gate_status or "").strip() or None,
        final_status=str(final_status or "").strip().lower() or None,
        first_failure_gate=str(first_failure_gate or "").strip() or None,
        first_failure_reason=str(first_failure_reason or "").strip() or None,
        gates_passed=gates_passed or [],
    )


def update_whiteboard_state(run_dir: Path) -> dict[str, Any]:
    return update_run_manifest(
        run_dir,
        whiteboard_present=True,
        whiteboard_path="artifacts/support_whiteboard.json",
    )


def update_bridge_state(run_dir: Path, *, output_ref: str = "", output_present: bool = True) -> dict[str, Any]:
    refs = [output_ref] if str(output_ref or "").strip() else []
    return update_run_manifest(
        run_dir,
        bridge_present=True,
        bridge_output_present=bool(output_present),
        bridge_output_refs=refs,
    )


def infer_run_dir_from_path(path: Path) -> Path | None:
    current = path.resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / "RUN.json").exists():
            return candidate
    return None

