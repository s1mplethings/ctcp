from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

RUN_MANIFEST_REL = Path("artifacts") / "run_manifest.json"
RUN_RESPONSIBILITY_MANIFEST_REL = Path("artifacts") / "run_responsibility_manifest.json"
SCHEMA_VERSION = "ctcp-run-manifest-v1"
RESPONSIBILITY_SCHEMA_VERSION = "ctcp-run-responsibility-manifest-v1"


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


def _selected_workflow_id(run_dir: Path) -> str:
    doc = _read_json(run_dir / "artifacts" / "find_result.json")
    return str(doc.get("selected_workflow_id", "")).strip()


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _critical_stage(action: str, role: str) -> str:
    action_text = str(action or "").strip().lower()
    role_text = str(role or "").strip().lower()
    if any(token in action_text for token in ("output_contract_freeze", "project_intent", "project_spec")):
        return "intent"
    if any(token in action_text for token in ("source_generation", "build", "implementation", "materialize")):
        return "core_feature"
    if any(token in action_text for token in ("verify", "smoke")):
        return "smoke_verify"
    if any(token in action_text for token in ("docs_generation", "workflow_generation", "manifest")):
        return "demo_evidence"
    if any(token in action_text for token in ("deliver", "delivery", "bundle", "support_reply")):
        return "delivery_package"
    if role_text == "librarian" and action_text == "context_pack":
        return "goal"
    return ""


def _critical_stage_usage(run_dir: Path) -> tuple[dict[str, str], dict[str, bool], bool, list[dict[str, Any]]]:
    rows = _read_jsonl(run_dir / "artifacts" / "provider_ledger.jsonl")
    provider_by_stage: dict[str, str] = {}
    external_by_stage: dict[str, bool] = {}
    details: list[dict[str, Any]] = []
    fallback_used = False
    for row in rows:
        stage = _critical_stage(str(row.get("action", "")), str(row.get("role", "")))
        if not stage:
            continue
        provider = str(row.get("provider_used", "")).strip()
        external = bool(row.get("external_api_used", False))
        fallback = bool(row.get("fallback_used", False))
        fallback_used = fallback_used or fallback
        if stage not in provider_by_stage:
            provider_by_stage[stage] = provider
            external_by_stage[stage] = external
        details.append(
            {
                "stage": stage,
                "role": str(row.get("role", "")).strip().lower(),
                "action": str(row.get("action", "")).strip().lower(),
                "provider_used": provider,
                "external_api_used": external,
                "fallback_used": fallback,
                "local_function_used": str(row.get("local_function_used", "")).strip(),
                "verdict": str(row.get("verdict", "")).strip(),
            }
        )
    return provider_by_stage, external_by_stage, fallback_used, details


def _stage_owners() -> dict[str, str]:
    return {
        "goal": "Chair/Planner",
        "intent": "Chair/Planner",
        "spec": "Chair/Planner",
        "scaffold": "Chair/Planner",
        "core_feature": "Chair/Planner",
        "smoke_verify": "Local Verifier",
        "demo_evidence": "Chair/Planner",
        "delivery_package": "Chair/Planner",
    }


def _derive_delivery_status(manifest: dict[str, Any], run_dir: Path) -> tuple[str, str, str, str]:
    verify_doc = _read_json(run_dir / "artifacts" / "verify_report.json")
    support_doc = _read_json(run_dir / "artifacts" / "support_public_delivery.json")
    internal_runtime_status = _first_non_empty(
        verify_doc.get("internal_runtime_status"),
        support_doc.get("internal_runtime_status"),
    )
    user_acceptance_status = _first_non_empty(
        verify_doc.get("user_acceptance_status"),
        support_doc.get("user_acceptance_status"),
    )
    final_verdict = _first_non_empty(
        verify_doc.get("final_verdict"),
        support_doc.get("final_verdict"),
    )
    first_failure_point = _first_non_empty(
        verify_doc.get("first_failure_point"),
        support_doc.get("first_failure_point"),
        manifest.get("first_failure_gate"),
    )
    final_status = str(manifest.get("final_status", "")).strip().lower()
    if not internal_runtime_status:
        internal_runtime_status = "PASS" if final_status == "pass" else ("FAIL" if final_status == "fail" else "")
    if not user_acceptance_status:
        user_acceptance_status = "PASS" if final_verdict == "PASS" else ("NEEDS_REWORK" if final_verdict else "")
    if not final_verdict:
        if user_acceptance_status == "PASS":
            final_verdict = "PASS"
        elif internal_runtime_status == "PASS":
            final_verdict = "PARTIAL"
        elif final_status in {"fail", "blocked"}:
            final_verdict = "NEEDS_REWORK"
    return internal_runtime_status, user_acceptance_status, first_failure_point, final_verdict


def _final_producers(provider_by_stage: dict[str, str]) -> tuple[str, str]:
    final_code_producer = _first_non_empty(
        provider_by_stage.get("core_feature"),
        provider_by_stage.get("scaffold"),
    )
    final_doc_producer = _first_non_empty(
        provider_by_stage.get("demo_evidence"),
        provider_by_stage.get("delivery_package"),
    )
    return final_code_producer, final_doc_producer


def _write_run_responsibility_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    run_doc = _run_doc(run_dir)
    provider_by_stage, external_by_stage, fallback_used, stage_usage_rows = _critical_stage_usage(run_dir)
    internal_runtime_status, user_acceptance_status, first_failure_point, final_verdict = _derive_delivery_status(
        manifest,
        run_dir,
    )
    final_code_producer, final_doc_producer = _final_producers(provider_by_stage)
    responsibility = {
        "schema_version": RESPONSIBILITY_SCHEMA_VERSION,
        "run_id": str(run_doc.get("run_id", manifest.get("run_id", run_dir.name))).strip() or run_dir.name,
        "run_dir": str(run_dir.resolve()),
        "raw_user_goal": str(run_doc.get("goal", "")).strip(),
        "chosen_entry": "scripts/ctcp_orchestrate.py",
        "chosen_workflow": _selected_workflow_id(run_dir),
        "bound_run_id": str(run_doc.get("run_id", manifest.get("run_id", run_dir.name))).strip() or run_dir.name,
        "bound_run_dir": str(run_dir.resolve()),
        "stage_owners": _stage_owners(),
        "provider_used_per_critical_stage": provider_by_stage,
        "external_api_used_per_critical_stage": external_by_stage,
        "critical_stage_execution": stage_usage_rows,
        "fallback_used": bool(fallback_used),
        "final_code_producer": final_code_producer,
        "final_doc_producer": final_doc_producer,
        "internal_runtime_status": internal_runtime_status,
        "user_acceptance_status": user_acceptance_status,
        "first_failure_point": first_failure_point,
        "final_verdict": final_verdict,
        "updated_at": _now_utc_iso(),
    }
    _write_json(run_dir / RUN_RESPONSIBILITY_MANIFEST_REL, responsibility)


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
    _write_run_responsibility_manifest(run_dir, manifest)
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
