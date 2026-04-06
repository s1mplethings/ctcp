from __future__ import annotations

import json
from pathlib import Path
from typing import Any

DEFAULT_WORKFLOW_IDS = {"wf_project_generation_manifest"}
VALID_EXECUTION_MODES = {"production", "benchmark_regression"}
VALID_DELIVERY_SHAPES = {"cli_first", "gui_first", "web_first", "tool_library_first"}


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


def _validate_json_object_field(doc: dict[str, Any], field: str) -> tuple[bool, str]:
    value = doc.get(field)
    if not isinstance(value, dict):
        return False, f"{field} must be object"
    return True, "ok"


def _validate_gate_layers(doc: dict[str, Any]) -> tuple[bool, str]:
    ok, msg = _validate_json_object_field(doc, "gate_layers")
    if not ok:
        return False, msg
    layers = doc.get("gate_layers")
    for field in ("structural", "behavioral", "result"):
        value = layers.get(field)
        if not isinstance(value, dict):
            return False, f"gate_layers.{field} must be object"
        if "passed" not in value:
            return False, f"gate_layers.{field}.passed is required"
    return True, "ok"


def _validate_project_intent(doc: dict[str, Any]) -> tuple[bool, str]:
    ok, msg = _validate_json_object_field(doc, "project_intent")
    if not ok:
        return False, msg
    intent = doc.get("project_intent")
    required_str = ("goal_summary", "target_user", "problem_to_solve")
    required_lists = ("mvp_scope", "required_inputs", "required_outputs", "hard_constraints", "assumptions", "open_questions", "acceptance_criteria")
    for field in required_str:
        if not str(intent.get(field, "")).strip():
            return False, f"project_intent.{field} must be non-empty string"
    for field in required_lists:
        value = intent.get(field)
        if not isinstance(value, list):
            return False, f"project_intent.{field} must be array"
    return True, "ok"


def _validate_project_spec(doc: dict[str, Any]) -> tuple[bool, str]:
    ok, msg = _validate_json_object_field(doc, "project_spec")
    if not ok:
        return False, msg
    spec = doc.get("project_spec")
    for field in ("goal_summary", "problem_to_solve"):
        if not str(spec.get(field, "")).strip():
            return False, f"project_spec.{field} must be non-empty string"
    for field in ("mvp_scope", "required_outputs", "acceptance_criteria"):
        value = spec.get(field)
        if not isinstance(value, list) or not value:
            return False, f"project_spec.{field} must be non-empty array"
    return True, "ok"


def _validate_pipeline_contract(doc: dict[str, Any]) -> tuple[bool, str]:
    ok, msg = _validate_json_object_field(doc, "pipeline_contract")
    if not ok:
        return False, msg
    stages = dict(doc.get("pipeline_contract", {})).get("stages")
    if not isinstance(stages, list):
        return False, "pipeline_contract.stages must be array"
    names = [str(dict(row).get("name", "")).strip() for row in stages if isinstance(row, dict)]
    expected = [
        "project_intent",
        "spec",
        "scaffold",
        "core_feature_implementation",
        "smoke_run",
        "delivery_package",
    ]
    if names != expected:
        return False, "pipeline_contract.stages must follow project_intent -> spec -> scaffold -> core_feature_implementation -> smoke_run -> delivery_package"
    return True, "ok"


def _validate_generic_validation(doc: dict[str, Any]) -> tuple[bool, str]:
    ok, msg = _validate_json_object_field(doc, "generic_validation")
    if not ok:
        return False, msg
    generic = doc.get("generic_validation")
    if not bool(generic.get("passed", False)):
        return False, "generic_validation.passed must be true"
    if not bool(generic.get("has_runnable_entrypoint", False)):
        return False, "generic_validation.has_runnable_entrypoint must be true"
    if not bool(generic.get("readme_startup_ready", False)):
        return False, "generic_validation.readme_startup_ready must be true"
    core_flow = generic.get("core_user_flow")
    if not isinstance(core_flow, list) or not core_flow:
        return False, "generic_validation.core_user_flow must be non-empty array"
    smoke = generic.get("smoke_run")
    if not isinstance(smoke, dict) or not bool(smoke.get("passed", False)):
        return False, "generic_validation.smoke_run.passed must be true"
    return True, "ok"


def _validate_domain_validation(doc: dict[str, Any]) -> tuple[bool, str]:
    ok, msg = _validate_json_object_field(doc, "domain_validation")
    if not ok:
        return False, msg
    domain = doc.get("domain_validation")
    if not bool(domain.get("passed", False)):
        return False, "domain_validation.passed must be true"
    checks = domain.get("checks")
    if not isinstance(checks, list) or not checks:
        return False, "domain_validation.checks must be non-empty array"
    return True, "ok"


def _is_narrative_project(doc: dict[str, Any]) -> bool:
    project_type = str(doc.get("project_type", "")).strip().lower()
    if project_type == "narrative_copilot":
        return True
    rows = doc.get("business_files_generated")
    if isinstance(rows, list):
        normalized = [str(row).replace("\\", "/") for row in rows]
        return any(path.endswith("/story/outline.py") and "/src/" in path for path in normalized)
    return False


def _project_archetype(doc: dict[str, Any]) -> str:
    value = str(doc.get("project_archetype", "")).strip().lower()
    if value:
        return value
    if _is_narrative_project(doc):
        return "narrative_copilot"
    rows = _normalized_path_rows(doc, "business_files_generated", "source_files")
    if any(row.endswith("/service_contract.py") for row in rows):
        return "web_service"
    if any(row.endswith("/transforms.py") for row in rows):
        return "data_pipeline"
    if any(row.endswith("/commands.py") for row in rows):
        return "cli_toolkit"
    return "generic_copilot"


def _normalized_path_rows(doc: dict[str, Any], *fields: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for field in fields:
        value = doc.get(field)
        if not isinstance(value, list):
            continue
        for row in value:
            path = str(row or "").strip().replace("\\", "/")
            if not path or path in seen:
                continue
            seen.add(path)
            out.append(path)
    return out


def _narrative_required_suffixes(execution_mode: str) -> list[str]:
    planner = "chapter_planner.py" if str(execution_mode).strip() == "benchmark_regression" else "stage_planner.py"
    return [
        "/story/outline.py",
        f"/story/{planner}",
        "/cast/schema.py",
        "/pipeline/prompt_pipeline.py",
        "/exporters/deliver.py",
        "/service.py",
    ]


def _validate_narrative_outputs(doc: dict[str, Any], *, run_dir: Path, context: str) -> tuple[bool, str]:
    rows = _normalized_path_rows(doc, "business_files_generated", "source_files")
    if not rows:
        return False, f"structural gate: {context} narrative path inventory must not be empty"

    for suffix in _narrative_required_suffixes(str(doc.get("execution_mode", "")).strip()):
        matched = next((row for row in rows if row.endswith(suffix)), "")
        if not matched:
            return False, f"structural gate: {context} missing narrative business output: *{suffix}"
        if not (run_dir / matched).resolve().exists():
            return False, f"structural gate: {context} missing narrative business output: {matched}"

    service_test = next((row for row in rows if "/tests/test_" in row and row.endswith("_service.py")), "")
    if not service_test:
        return False, f"structural gate: {context} missing narrative service test output"
    if not (run_dir / service_test).resolve().exists():
        return False, f"structural gate: {context} missing narrative business output: {service_test}"
    return True, "ok"


def _validate_archetype_outputs(
    doc: dict[str, Any],
    *,
    run_dir: Path,
    context: str,
    archetype: str,
    required_suffixes: list[str],
    required_test: bool = True,
) -> tuple[bool, str]:
    rows = _normalized_path_rows(doc, "business_files_generated", "source_files")
    if not rows:
        return False, f"structural gate: {context} {archetype} path inventory must not be empty"
    for suffix in required_suffixes:
        matched = next((row for row in rows if row.endswith(suffix)), "")
        if not matched:
            return False, f"structural gate: {context} missing {archetype} output: *{suffix}"
        if not (run_dir / matched).resolve().exists():
            return False, f"structural gate: {context} missing {archetype} output: {matched}"
    if required_test:
        service_test = next((row for row in rows if "/tests/test_" in row and row.endswith("_service.py")), "")
        if not service_test:
            return False, f"structural gate: {context} missing {archetype} service test output"
        if not (run_dir / service_test).resolve().exists():
            return False, f"structural gate: {context} missing {archetype} output: {service_test}"
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
    for validator in (_validate_project_intent, _validate_project_spec, _validate_pipeline_contract):
        ok, inner = validator(doc)
        if not ok:
            return False, f"structural gate: {inner}"
    for field in ("target_files", "source_files", "doc_files", "workflow_files", "acceptance_files", "business_files"):
        ok, msg = _validate_json_list_field(doc, field)
        if not ok:
            return False, f"structural gate: {msg}"
    if not str(doc.get("project_type", "")).strip():
        return False, "structural gate: project_type must be non-empty"
    if not str(doc.get("project_archetype", "")).strip():
        return False, "structural gate: project_archetype must be non-empty"
    if not doc.get("business_files"):
        return False, "structural gate: business_files must not be empty"
    if str(doc.get("execution_mode", "")).strip() not in VALID_EXECUTION_MODES:
        return False, "structural gate: execution_mode must be production or benchmark_regression"
    if str(doc.get("delivery_shape", "")).strip() not in VALID_DELIVERY_SHAPES:
        return False, "structural gate: delivery_shape must be a supported shape"
    if not str(doc.get("startup_entrypoint", "")).strip():
        return False, "structural gate: startup_entrypoint must be non-empty"
    if not str(doc.get("startup_readme", "")).strip():
        return False, "structural gate: startup_readme must be non-empty"
    for field in ("decision_nodes", "flow_nodes"):
        ok, msg = _validate_json_list_field(doc, field)
        if not ok:
            return False, f"structural gate: {msg}"
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
    for validator in (
        _validate_project_intent,
        _validate_project_spec,
        _validate_pipeline_contract,
        _validate_generic_validation,
        _validate_domain_validation,
    ):
        ok, inner = validator(doc)
        if not ok:
            return False, inner
    for field in ("run_id", "project_id"):
        if not str(doc.get(field, "")).strip():
            return False, f"{field} must be non-empty string"
    for field in (
        "source_files",
        "doc_files",
        "workflow_files",
        "business_files_generated",
        "business_files_missing",
        "consumed_context_files",
        "context_influence_summary",
        "decision_nodes",
        "flow_nodes",
        "generated_files",
        "missing_files",
        "acceptance_files",
        "artifacts",
    ):
        ok, msg = _validate_json_list_field(doc, field)
        if not ok:
            return False, f"structural gate: {msg}"
    if not doc.get("source_files"):
        return False, "structural gate: source_files must not be empty"
    if not doc.get("doc_files"):
        return False, "structural gate: doc_files must not be empty"
    if not doc.get("workflow_files"):
        return False, "structural gate: workflow_files must not be empty"
    if list(doc.get("missing_files", [])):
        return False, "structural gate: project_manifest missing_files must be empty"
    if not bool(doc.get("business_codegen_used", False)):
        return False, "structural gate: project_manifest business_codegen_used must be true"
    if not bool(doc.get("consumed_context_pack", False)):
        return False, "result gate: project_manifest consumed_context_pack must be true"
    if not doc.get("business_files_generated"):
        return False, "structural gate: project_manifest business_files_generated must not be empty"
    if list(doc.get("business_files_missing", [])):
        return False, "structural gate: project_manifest business_files_missing must be empty"
    if str(doc.get("execution_mode", "")).strip() not in VALID_EXECUTION_MODES:
        return False, "structural gate: project_manifest execution_mode must be valid"
    if not str(doc.get("project_archetype", "")).strip():
        return False, "structural gate: project_manifest project_archetype must be non-empty"
    if str(doc.get("delivery_shape", "")).strip() not in VALID_DELIVERY_SHAPES:
        return False, "structural gate: project_manifest delivery_shape must be valid"
    startup_entrypoint = str(doc.get("startup_entrypoint", "")).strip()
    startup_readme = str(doc.get("startup_readme", "")).strip()
    if not startup_entrypoint:
        return False, "structural gate: startup_entrypoint must be non-empty"
    if not startup_readme:
        return False, "structural gate: startup_readme must be non-empty"

    run_dir = path.parent.parent
    for rel in (startup_entrypoint, startup_readme):
        target = (run_dir / rel).resolve()
        if not target.exists():
            return False, f"structural gate: missing startup file: {rel}"
    mode = doc.get("reference_project_mode")
    if not isinstance(mode, dict):
        return False, "structural gate: reference_project_mode must be object"
    if "enabled" not in mode or "mode" not in mode:
        return False, "structural gate: reference_project_mode requires enabled + mode"
    ok, msg = _validate_gate_layers(doc)
    if not ok:
        return False, f"result gate: {msg}"
    behavior = doc.get("behavioral_checks")
    if not isinstance(behavior, dict):
        return False, "behavioral gate: behavioral_checks must be object"
    if str(doc.get("delivery_shape", "")).strip() in {"gui_first", "web_first"} and str(doc.get("visual_evidence_status", "")).strip() not in {"placeholder_only", "provided"}:
        return False, "result gate: GUI/web manifest must declare visual_evidence_status"
    if str(doc.get("execution_mode", "")).strip() == "production" and bool(doc.get("benchmark_sample_applied", False)):
        return False, "result gate: production manifest must not apply benchmark sample content"
    if _is_narrative_project(doc):
        ok, msg = _validate_narrative_outputs(doc, run_dir=run_dir, context="manifest")
        if not ok:
            return False, msg
    else:
        archetype = _project_archetype(doc)
        if archetype == "cli_toolkit":
            ok, msg = _validate_archetype_outputs(doc, run_dir=run_dir, context="manifest", archetype=archetype, required_suffixes=["/commands.py", "/exporter.py", "/service.py"])
            if not ok:
                return False, msg
        elif archetype == "web_service":
            ok, msg = _validate_archetype_outputs(doc, run_dir=run_dir, context="manifest", archetype=archetype, required_suffixes=["/service_contract.py", "/app.py", "/exporter.py", "/service.py"])
            if not ok:
                return False, msg
        elif archetype == "data_pipeline":
            ok, msg = _validate_archetype_outputs(doc, run_dir=run_dir, context="manifest", archetype=archetype, required_suffixes=["/transforms.py", "/pipeline.py", "/exporter.py", "/service.py"])
            if not ok:
                return False, msg
    if not bool(dict(doc.get("gate_layers", {})).get("structural", {}).get("passed", False)):
        return False, "structural gate: manifest gate_layers.structural.passed must be true"
    if not bool(dict(doc.get("gate_layers", {})).get("behavioral", {}).get("passed", False)):
        return False, "behavioral gate: manifest gate_layers.behavioral.passed must be true"
    if not bool(dict(doc.get("gate_layers", {})).get("result", {}).get("passed", False)):
        return False, "result gate: manifest gate_layers.result.passed must be true"
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
    if stage == "source_generation":
        for validator in (
            _validate_project_intent,
            _validate_project_spec,
            _validate_pipeline_contract,
            _validate_generic_validation,
            _validate_domain_validation,
        ):
            ok, inner = validator(doc)
            if not ok:
                return False, inner
    for field in ("required_files", "generated_files", "missing_files"):
        ok, list_msg = _validate_json_list_field(doc, field)
        if not ok:
            return False, f"structural gate: {list_msg}"
    if str(doc.get("status", "")).strip().lower() != "pass":
        return False, f"structural gate: {stage} status must be pass"
    if list(doc.get("missing_files", [])):
        return False, f"structural gate: {stage} missing_files must be empty"
    if stage == "source_generation":
        entrypoint = str(doc.get("entrypoint", "")).strip()
        startup_readme = str(doc.get("startup_readme", "")).strip()
        if not entrypoint:
            return False, "structural gate: source_generation requires entrypoint"
        if not startup_readme:
            return False, "structural gate: source_generation requires startup_readme"
        run_dir = path.parent.parent
        for rel in (entrypoint, startup_readme):
            target = (run_dir / rel).resolve()
            if not target.exists():
                return False, f"structural gate: source_generation output missing: {rel}"
        if not str(doc.get("generation_mode", "")).strip():
            return False, "structural gate: source_generation requires generation_mode"
        if not bool(doc.get("scaffold_bootstrap_used", False)):
            return False, "structural gate: source_generation scaffold_bootstrap_used must be true"
        if not bool(doc.get("business_codegen_used", False)):
            return False, "structural gate: source_generation business_codegen_used must be true"
        if not bool(doc.get("consumed_context_pack", False)):
            return False, "result gate: source_generation consumed_context_pack must be true"
        if str(doc.get("execution_mode", "")).strip() not in VALID_EXECUTION_MODES:
            return False, "structural gate: source_generation execution_mode must be valid"
        if not str(doc.get("project_archetype", "")).strip():
            return False, "structural gate: source_generation requires project_archetype"
        if str(doc.get("delivery_shape", "")).strip() not in VALID_DELIVERY_SHAPES:
            return False, "structural gate: source_generation delivery_shape must be valid"
        ok, list_msg = _validate_json_list_field(doc, "consumed_context_files")
        if not ok:
            return False, f"result gate: {list_msg}"
        ok, list_msg = _validate_json_list_field(doc, "context_influence_summary")
        if not ok:
            return False, f"result gate: {list_msg}"
        ok, list_msg = _validate_json_list_field(doc, "business_files_generated")
        if not ok:
            return False, f"structural gate: {list_msg}"
        ok, list_msg = _validate_json_list_field(doc, "business_files_missing")
        if not ok:
            return False, f"structural gate: {list_msg}"
        for field in ("decision_nodes", "flow_nodes"):
            ok, list_msg = _validate_json_list_field(doc, field)
            if not ok:
                return False, f"structural gate: {list_msg}"
        if not doc.get("consumed_context_files"):
            return False, "result gate: source_generation consumed_context_files must not be empty"
        if not doc.get("context_influence_summary"):
            return False, "result gate: source_generation context_influence_summary must not be empty"
        if not doc.get("business_files_generated"):
            return False, "structural gate: source_generation business_files_generated must not be empty"
        if list(doc.get("business_files_missing", [])):
            return False, "structural gate: source_generation business_files_missing must be empty"
        ok, msg = _validate_gate_layers(doc)
        if not ok:
            return False, f"result gate: {msg}"
        behavior = doc.get("behavioral_checks")
        if not isinstance(behavior, dict):
            return False, "behavioral gate: source_generation behavioral_checks must be object"
        for field in ("startup_probe", "export_probe"):
            if not isinstance(behavior.get(field), dict):
                return False, f"behavioral gate: behavioral_checks.{field} must be object"
            probe_rc = dict(behavior.get(field)).get("rc", 1)
            try:
                probe_rc_int = int(probe_rc)
            except Exception:
                probe_rc_int = 1
            if probe_rc_int != 0:
                return False, f"behavioral gate: {field} must pass"
        if str(doc.get("delivery_shape", "")).strip() in {"gui_first", "web_first"} and str(doc.get("visual_evidence_status", "")).strip() not in {"placeholder_only", "provided"}:
            return False, "result gate: GUI/web source_generation must declare visual_evidence_status"
        if str(doc.get("execution_mode", "")).strip() == "production" and bool(doc.get("benchmark_sample_applied", False)):
            return False, "result gate: production source_generation must not apply benchmark sample content"
        if _is_narrative_project(doc):
            ok, msg = _validate_narrative_outputs(doc, run_dir=run_dir, context="source_generation")
            if not ok:
                return False, msg
        else:
            archetype = _project_archetype(doc)
            if archetype == "cli_toolkit":
                ok, msg = _validate_archetype_outputs(doc, run_dir=run_dir, context="source_generation", archetype=archetype, required_suffixes=["/commands.py", "/exporter.py", "/service.py"])
                if not ok:
                    return False, msg
            elif archetype == "web_service":
                ok, msg = _validate_archetype_outputs(doc, run_dir=run_dir, context="source_generation", archetype=archetype, required_suffixes=["/service_contract.py", "/app.py", "/exporter.py", "/service.py"])
                if not ok:
                    return False, msg
            elif archetype == "data_pipeline":
                ok, msg = _validate_archetype_outputs(doc, run_dir=run_dir, context="source_generation", archetype=archetype, required_suffixes=["/transforms.py", "/pipeline.py", "/exporter.py", "/service.py"])
                if not ok:
                    return False, msg
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
    for validator in (
        _validate_project_intent,
        _validate_project_spec,
        _validate_pipeline_contract,
        _validate_generic_validation,
        _validate_domain_validation,
    ):
        ok, inner = validator(doc)
        if not ok:
            return False, inner
    if not str(doc.get("project_manifest_path", "")).strip():
        return False, "project_manifest_path must be non-empty"
    deliverables = doc.get("deliverables")
    if not isinstance(deliverables, list):
        return False, "deliverables must be array"
    if not deliverables:
        return False, "deliverables must not be empty"
    business_deliverables = doc.get("business_deliverables")
    if not isinstance(business_deliverables, list):
        return False, "business_deliverables must be array"
    if not business_deliverables:
        return False, "business_deliverables must not be empty"
    if str(doc.get("execution_mode", "")).strip() not in VALID_EXECUTION_MODES:
        return False, "execution_mode must be valid"
    if not str(doc.get("project_archetype", "")).strip():
        return False, "project_archetype must be non-empty"
    if str(doc.get("delivery_shape", "")).strip() not in VALID_DELIVERY_SHAPES:
        return False, "delivery_shape must be valid"
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
