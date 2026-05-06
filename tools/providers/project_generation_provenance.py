from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LOCAL_BUSINESS_MATERIALIZER = "LOCAL:tools/providers/project_generation_business_materializers.py::materialize_business_files"
DISABLED_LOCAL_TEMPLATE_MATERIALIZER = "DISABLED:production local project templates are disabled"
PROVIDER_SOURCE_MATERIALIZER = "API:provider-authored source files"


def _execution_mode(inputs: dict[str, Any]) -> str:
    lists = inputs.get("lists", {})
    if isinstance(lists, dict):
        return str(lists.get("execution_mode", "")).strip().lower()
    return ""


def _read_project_source_map(*, run_dir: Path, project_root: str) -> dict[str, Any]:
    path = (run_dir / project_root / "sample_data" / "source_map.json").resolve()
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def build_file_materialization_provenance(
    *,
    run_dir: Path,
    inputs: dict[str, Any],
    business_generated: list[str],
    current_materialize: list[str],
) -> dict[str, Any]:
    source_map = _read_project_source_map(run_dir=run_dir, project_root=str(inputs["project_root"]))
    api_content_applied = bool(source_map.get("api_content_applied", False))
    api_content_source_ref = str(source_map.get("api_content_source_ref", "")).strip()
    provider_authorship = "mixed_api_content" if api_content_applied else "not_claimed"
    local_templates_disabled = bool(inputs.get("local_templates_disabled", False))
    provider_source_files_applied = bool(inputs.get("provider_source_files_applied", False))
    if provider_source_files_applied:
        materialization_strategy = "provider_authored_source"
        materializer = PROVIDER_SOURCE_MATERIALIZER
        provider_authorship = "provider_authored_source"
    elif local_templates_disabled:
        materialization_strategy = "disabled_local_templates"
        materializer = DISABLED_LOCAL_TEMPLATE_MATERIALIZER
    else:
        materialization_strategy = "local_materializer"
        materializer = LOCAL_BUSINESS_MATERIALIZER
    materialized_set = {str(path).strip().replace("\\", "/") for path in business_generated if str(path).strip()}
    rows = [
        {
            "path": path,
            "artifact_kind": "business_file",
            "materialized_by": materialization_strategy,
            "materializer": materializer,
            "materializer_returned_path": path in materialized_set,
            "provider_authorship": provider_authorship,
            "provider_execution_ref": "artifacts/provider_ledger.jsonl",
            "api_content_applied": api_content_applied,
            "api_content_source_ref": api_content_source_ref,
        }
        for path in materialized_set
    ]
    return {
        "schema_version": "ctcp-generation-provenance-v1",
        "provider_execution": {
            "stage": "source_generation",
            "provider_identity_source": "artifacts/provider_ledger.jsonl",
            "known_at_source_stage": False,
            "note": "Provider execution is recorded by dispatch; file authorship is recorded separately below.",
        },
        "file_materialization": {
            "strategy": materialization_strategy,
            "materializer": materializer,
            "materialize_capabilities": list(current_materialize),
            "generated_business_file_count": len(materialized_set),
            "materializer_returned_file_count": len(materialized_set),
            "api_content_applied": api_content_applied,
            "api_content_source_ref": api_content_source_ref,
            "local_templates_disabled": local_templates_disabled,
            "provider_source_files_applied": provider_source_files_applied,
            "content_provenance_map": f"{inputs['project_root']}/sample_data/source_map.json",
        },
        "files": rows,
    }


def build_source_customization_completion(provenance: dict[str, Any], *, inputs: dict[str, Any]) -> dict[str, Any]:
    file_materialization = provenance.get("file_materialization", {})
    files = provenance.get("files", [])
    file_rows = [dict(row) for row in files if isinstance(files, list) and isinstance(row, dict)]
    execution_mode = _execution_mode(inputs)
    api_content_applied = bool(dict(file_materialization).get("api_content_applied", False)) if isinstance(file_materialization, dict) else False
    local_templates_disabled = bool(dict(file_materialization).get("local_templates_disabled", False)) if isinstance(file_materialization, dict) else False
    provider_authored_source_present = api_content_applied or any(
        str(row.get("provider_authorship", "")).strip() not in {"", "not_claimed"}
        for row in file_rows
    )
    generated_business_file_count = (
        int(dict(file_materialization).get("generated_business_file_count", 0) or 0)
        if isinstance(file_materialization, dict)
        else len(file_rows)
    )
    lists = inputs.get("lists", {})
    expected_business_file_count = len(list(lists.get("business_files", []))) if isinstance(lists, dict) and isinstance(lists.get("business_files", []), list) else 0
    required_for_final_delivery = execution_mode == "production" and (generated_business_file_count > 0 or expected_business_file_count > 0)
    passed = (not required_for_final_delivery) or provider_authored_source_present
    blocking_reason = ""
    if not passed:
        if local_templates_disabled:
            blocking_reason = "production local project templates are disabled; provider-authored source files are required before project delivery"
        else:
            blocking_reason = (
                "business source files were produced only by the deterministic local materializer; "
                "provider-authored/API content was not applied, so this cannot be delivered as a customized final project"
            )
    return {
        "schema_version": "ctcp-source-customization-completion-v1",
        "status": "passed" if passed else "blocked",
        "passed": passed,
        "customized_implementation_complete": passed,
        "final_delivery_allowed": passed,
        "required_for_final_delivery": required_for_final_delivery,
        "execution_mode": execution_mode,
        "provider_authored_source_present": provider_authored_source_present,
        "api_content_applied": api_content_applied,
        "local_templates_disabled": local_templates_disabled,
        "local_materializer_only": bool(generated_business_file_count and not provider_authored_source_present),
        "generated_business_file_count": generated_business_file_count,
        "expected_business_file_count": expected_business_file_count,
        "blocking_reason": blocking_reason,
    }


def attach_source_generation_provenance(
    report: dict[str, Any],
    run_dir: Path,
    inputs: dict[str, Any],
    business_generated: list[str],
    current_materialize: list[str],
) -> None:
    provenance = build_file_materialization_provenance(
        run_dir=run_dir,
        inputs=inputs,
        business_generated=business_generated,
        current_materialize=current_materialize,
    )
    report["provider_execution"] = provenance["provider_execution"]
    report["file_materialization"] = provenance["file_materialization"]
    report["file_provenance"] = provenance["files"]
    report["source_customization_completion"] = build_source_customization_completion(provenance, inputs=inputs)
    report["provenance"] = provenance


def manifest_provenance_fields(source_stage_doc: dict[str, Any]) -> dict[str, Any]:
    file_provenance_src = source_stage_doc.get("file_provenance", [])
    return {
        "provider_execution": source_stage_doc.get("provider_execution") if isinstance(source_stage_doc.get("provider_execution"), dict) else {},
        "file_materialization": source_stage_doc.get("file_materialization") if isinstance(source_stage_doc.get("file_materialization"), dict) else {},
        "file_provenance": [
            dict(row)
            for row in file_provenance_src
            if isinstance(file_provenance_src, list) and isinstance(row, dict) and str(row.get("path", "")).strip()
        ],
        "source_customization_completion": source_stage_doc.get("source_customization_completion")
        if isinstance(source_stage_doc.get("source_customization_completion"), dict)
        else {},
        "provenance": source_stage_doc.get("provenance") if isinstance(source_stage_doc.get("provenance"), dict) else {},
    }
