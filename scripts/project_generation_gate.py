from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_WORKFLOW_IDS = {"wf_project_generation_manifest"}


def selected_workflow_id_from_find_result(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(doc, dict):
        return ""
    return str(doc.get("selected_workflow_id", "")).strip()


def is_project_generation_workflow(selected_workflow_id: str, workflow_ids: set[str] | None = None) -> bool:
    text = str(selected_workflow_id or "").strip().lower()
    if not text:
        return False
    if text in (workflow_ids or DEFAULT_WORKFLOW_IDS):
        return True
    return "project_generation" in text or "project-generation" in text


def _validate_json_list_field(doc: dict[str, Any], field: str) -> tuple[bool, str]:
    value = doc.get(field)
    if not isinstance(value, list):
        return False, f"{field} must be array"
    return True, "ok"


def _load_json(path: Path, *, waiting: str, invalid: str, object_name: str) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, waiting
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"{invalid}: {exc}"
    if not isinstance(doc, dict):
        return None, f"{object_name} must be object"
    return doc, "ok"


def _validate_output_contract_freeze(path: Path) -> tuple[bool, str]:
    doc, msg = _load_json(
        path,
        waiting="waiting for output_contract_freeze",
        invalid="invalid output_contract_freeze.json",
        object_name="output_contract_freeze.json",
    )
    if doc is None:
        return False, msg
    if str(doc.get("schema_version", "")).strip() != "ctcp-project-output-contract-v1":
        return False, "output_contract_freeze schema_version must be ctcp-project-output-contract-v1"
    for field in ("target_files", "source_files", "doc_files", "workflow_files", "acceptance_files"):
        ok, msg = _validate_json_list_field(doc, field)
        if not ok:
            return False, msg
    return True, "ok"


def _validate_project_manifest(path: Path) -> tuple[bool, str]:
    doc, msg = _load_json(
        path,
        waiting="waiting for artifact_manifest_build",
        invalid="invalid project_manifest.json",
        object_name="project_manifest.json",
    )
    if doc is None:
        return False, msg
    for field in ("run_id", "project_id"):
        if not str(doc.get(field, "")).strip():
            return False, f"{field} must be non-empty string"
    for field in (
        "source_files",
        "doc_files",
        "workflow_files",
        "generated_files",
        "missing_files",
        "acceptance_files",
        "artifacts",
    ):
        ok, msg = _validate_json_list_field(doc, field)
        if not ok:
            return False, msg
    if not doc.get("source_files"):
        return False, "source_files must not be empty"
    if not doc.get("doc_files"):
        return False, "doc_files must not be empty"
    if not doc.get("workflow_files"):
        return False, "workflow_files must not be empty"
    if list(doc.get("missing_files", [])):
        return False, "project_manifest missing_files must be empty"
    startup_entrypoint = str(doc.get("startup_entrypoint", "")).strip()
    startup_readme = str(doc.get("startup_readme", "")).strip()
    if not startup_entrypoint:
        return False, "startup_entrypoint must be non-empty"
    if not startup_readme:
        return False, "startup_readme must be non-empty"

    run_dir = path.parent.parent
    for rel in (startup_entrypoint, startup_readme):
        target = (run_dir / rel).resolve()
        if not target.exists():
            return False, f"missing startup file: {rel}"
    mode = doc.get("reference_project_mode")
    if not isinstance(mode, dict):
        return False, "reference_project_mode must be object"
    if "enabled" not in mode or "mode" not in mode:
        return False, "reference_project_mode requires enabled + mode"
    return True, "ok"


def _validate_stage_report(path: Path, *, stage: str) -> tuple[bool, str]:
    doc, msg = _load_json(
        path,
        waiting=f"waiting for {stage}",
        invalid=f"invalid {path.name}",
        object_name=path.name,
    )
    if doc is None:
        return False, msg
    if str(doc.get("schema_version", "")).strip() != "ctcp-project-stage-report-v1":
        return False, f"{path.name} schema_version must be ctcp-project-stage-report-v1"
    if str(doc.get("stage", "")).strip() != stage:
        return False, f"{path.name} stage must be {stage}"
    for field in ("required_files", "generated_files", "missing_files"):
        ok, list_msg = _validate_json_list_field(doc, field)
        if not ok:
            return False, list_msg
    if str(doc.get("status", "")).strip().lower() != "pass":
        return False, f"{stage} status must be pass"
    if list(doc.get("missing_files", [])):
        return False, f"{stage} missing_files must be empty"
    if stage == "source_generation":
        entrypoint = str(doc.get("entrypoint", "")).strip()
        startup_readme = str(doc.get("startup_readme", "")).strip()
        if not entrypoint:
            return False, "source_generation requires entrypoint"
        if not startup_readme:
            return False, "source_generation requires startup_readme"
        run_dir = path.parent.parent
        for rel in (entrypoint, startup_readme):
            target = (run_dir / rel).resolve()
            if not target.exists():
                return False, f"source_generation output missing: {rel}"
    return True, "ok"


def _validate_deliverable_index(path: Path) -> tuple[bool, str]:
    doc, msg = _load_json(
        path,
        waiting="waiting for deliver",
        invalid="invalid deliverable_index.json",
        object_name="deliverable_index.json",
    )
    if doc is None:
        return False, msg
    if str(doc.get("schema_version", "")).strip() != "ctcp-deliverable-index-v1":
        return False, "deliverable_index schema_version must be ctcp-deliverable-index-v1"
    if not str(doc.get("project_manifest_path", "")).strip():
        return False, "project_manifest_path must be non-empty"
    deliverables = doc.get("deliverables")
    if not isinstance(deliverables, list):
        return False, "deliverables must be array"
    if not deliverables:
        return False, "deliverables must not be empty"
    return True, "ok"


def evaluate_project_generation_gate(artifacts: Path) -> dict[str, str]:
    output_contract = artifacts / "output_contract_freeze.json"
    source_stage = artifacts / "source_generation_report.json"
    docs_stage = artifacts / "docs_generation_report.json"
    workflow_stage = artifacts / "workflow_generation_report.json"
    manifest = artifacts / "project_manifest.json"
    deliverable_index = artifacts / "deliverable_index.json"

    ok_contract, msg_contract = _validate_output_contract_freeze(output_contract)
    if not ok_contract:
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/output_contract_freeze.json",
            "reason": msg_contract,
        }

    ok_source, msg_source = _validate_stage_report(source_stage, stage="source_generation")
    if not ok_source:
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/source_generation_report.json",
            "reason": msg_source,
        }

    ok_docs, msg_docs = _validate_stage_report(docs_stage, stage="docs_generation")
    if not ok_docs:
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/docs_generation_report.json",
            "reason": msg_docs,
        }

    ok_workflow, msg_workflow = _validate_stage_report(workflow_stage, stage="workflow_generation")
    if not ok_workflow:
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/workflow_generation_report.json",
            "reason": msg_workflow,
        }

    ok_manifest, msg_manifest = _validate_project_manifest(manifest)
    if not ok_manifest:
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/project_manifest.json",
            "reason": msg_manifest,
        }

    ok_deliver, msg_deliver = _validate_deliverable_index(deliverable_index)
    if not ok_deliver:
        return {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/deliverable_index.json",
            "reason": msg_deliver,
        }

    return {
        "state": "ready_verify",
        "owner": "Local Verifier",
        "path": "artifacts/verify_report.json",
        "reason": "project generation artifacts ready for verify",
    }
