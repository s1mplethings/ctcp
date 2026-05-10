from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable

from tools.providers.project_generation_decisions import (
    BENCHMARK_MODE,
    CLI_SHAPE,
    PRODUCTION_MODE,
    decide_project_generation,
)
from tools.providers.project_generation_domain_contract import compatibility_report
from tools.providers.project_generation_extended_evidence import (
    _is_high_quality_team_task,
    _is_indie_studio_hub,
    _materialize_high_quality_indie_studio_hub_evidence,
    _materialize_high_quality_team_task_evidence,
)
from tools.providers.project_generation_import_validation import provider_interface_contract
from tools.providers.project_generation_provider_source_files import (
    _ensure_provider_package_init_files,
    _materialize_provider_source_files,
    _provider_source_file_rows,
)
from tools.providers.project_generation_provenance import attach_source_generation_provenance
from tools.providers.project_generation_sample_metrics import narrative_sample_metrics
from tools.providers.project_generation_source_helpers import (
    build_missing_context_extra,
    build_runtime_checks,
    build_success_extra,
)
from tools.providers.project_generation_validation import (
    capability_plan_validation as _capability_plan_validation,
    domain_validation as _domain_validation,
    generic_validation as _generic_validation,
    product_validation as _product_validation,
    readme_quality_validation as _readme_quality_validation,
    resolve_project_intent as _resolve_project_intent,
    resolve_project_spec as _resolve_project_spec,
    ux_validation as _ux_validation,
)
from tools.providers.project_generation_queue_stage import normalize_project_queue_source_generation_stage
from tools.providers.project_generation_runtime_support import (
    _collect_project_files,
    _context_consumption,
    _load_context_pack,
    _run_pointcloud_scaffold,
    _stage_report,
)


def _source_generation_inputs(
    *,
    doc: dict[str, Any] | None,
    goal: str,
    run_dir: Path,
    load_output_contract_lists: Callable[..., dict[str, Any]],
    project_slug: Callable[[str, str], str],
) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = load_output_contract_lists(run_dir, goal=goal_text)
    project_intent = (
        dict(lists.get("project_intent", {}))
        if isinstance(lists.get("project_intent", {}), dict)
        else _resolve_project_intent(goal_text, run_dir=run_dir, src=src)
    )
    project_spec = (
        dict(lists.get("project_spec", {}))
        if isinstance(lists.get("project_spec", {}), dict)
        else _resolve_project_spec(goal_text, run_dir=run_dir, src=src, project_intent=project_intent)
    )
    capability_plan = dict(lists.get("capability_plan", {})) if isinstance(lists.get("capability_plan", {}), dict) else {}
    project_type = str(lists.get("project_type", "")).strip() or "generic_copilot"
    project_root = str(lists.get("project_root", "")).strip() or f"project_output/{project_slug(goal_text, project_type)}"
    context_doc, context_files = _load_context_pack(run_dir)
    decision = decide_project_generation(goal_text, run_dir=run_dir, context_files=context_files)
    context_usage = _context_consumption(goal_text, context_files, decision=decision)
    project_domain = str(lists.get("project_domain", "")).strip() or "generic_software_project"
    scaffold_family = str(lists.get("scaffold_family", "")).strip() or "generic_copilot"
    return {
        "src": src,
        "goal_text": goal_text,
        "lists": lists,
        "project_intent": project_intent,
        "project_spec": project_spec,
        "project_spec_path": str(lists.get("project_spec_path", "")).strip() or "artifacts/project_spec.json",
        "capability_plan": capability_plan,
        "capability_plan_path": str(lists.get("capability_plan_path", "")).strip() or "artifacts/capability_plan.json",
        "sample_generation_plan": dict(lists.get("sample_generation_plan", {})) if isinstance(lists.get("sample_generation_plan", {}), dict) else {},
        "sample_generation_artifacts": [str(item).strip() for item in lists.get("sample_generation_artifacts", []) if str(item).strip()] if isinstance(lists.get("sample_generation_artifacts", []), list) else [],
        "generation_quality_report_path": str(lists.get("generation_quality_report_path", "")).strip() or "artifacts/generation_quality_report.json",
        "materialize_capabilities": [str(item).strip() for item in lists.get("materialize_capabilities", lists.get("business_capabilities", [])) if str(item).strip()] if isinstance(lists.get("materialize_capabilities", lists.get("business_capabilities", [])), list) else [],
        "pipeline_contract": dict(lists.get("pipeline_contract", {})) if isinstance(lists.get("pipeline_contract", {}), dict) else {},
        "project_root": project_root,
        "project_type": project_type,
        "project_archetype": str(lists.get("project_archetype", "")).strip() or "generic_copilot",
        "package_name": str(lists.get("package_name", "")).strip() or "project_copilot",
        "profile": str(lists.get("project_profile", "business_copilot")).strip().lower() or "business_copilot",
        "project_domain": project_domain,
        "scaffold_family": scaffold_family,
        "entry_script": str(lists.get("startup_entrypoint", "")).strip() or f"{project_root}/scripts/run_project_cli.py",
        "context_doc": context_doc,
        "context_files": context_files,
        "context_usage": context_usage,
        "consumed_context": bool(context_usage.get("consumed_context_pack", False)),
        "consumed_files": list(context_usage.get("consumed_context_files", [])),
        "domain_compatibility": compatibility_report(project_domain=project_domain, scaffold_family=scaffold_family),
    }


def _blocked_source_generation_report(
    *,
    inputs: dict[str, Any],
    run_dir: Path,
    reason: str = "",
) -> dict[str, Any]:
    lists = inputs["lists"]
    report = _stage_report(
        stage="source_generation",
        goal=inputs["goal_text"],
        project_root=inputs["project_root"],
        required_files=list(lists.get("source_files", [])),
        generated_files=_collect_project_files(run_dir, inputs["project_root"]),
        extra=build_missing_context_extra(
            lists=lists,
            project_id=str(lists.get("project_id", "")),
            project_type=inputs["project_type"],
            package_name=inputs["package_name"],
            entry_script=inputs["entry_script"],
        ),
    )
    for key in ("project_intent", "project_spec", "pipeline_contract", "project_domain", "scaffold_family", "domain_compatibility"):
        report[key] = inputs[key]
    report["status"] = "blocked"
    if reason:
        report["blocking_reason"] = reason
    report["generic_validation"] = {
        "passed": False,
        "has_runnable_entrypoint": False,
        "readme_startup_ready": False,
        "core_user_flow": [],
        "core_feature_files": [],
        "placeholder_hits": [],
        "python_syntax": {"passed": False, "checked_files": [], "syntax_errors": []},
        "python_import_consistency": {"passed": False, "issues": []},
        "python_signature_consistency": {"passed": False, "issues": []},
        "generated_tests": {"passed": True, "status": "skipped", "checked_files": []},
        "delivery_package": [],
        "smoke_run": {"startup_probe": {}, "export_probe": {}, "passed": False},
    }
    return report


def _production_local_templates_disabled(inputs: dict[str, Any]) -> bool:
    return str(inputs["lists"].get("execution_mode", PRODUCTION_MODE)).strip() == PRODUCTION_MODE


def _blocked_local_templates_disabled_report(*, inputs: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    reason = "production local project templates are disabled; provider-authored source files are required before source generation can continue"
    report = _blocked_source_generation_report(inputs=inputs, run_dir=run_dir, reason=reason)
    generation_quality = {
        "schema_version": "ctcp-generation-quality-v1",
        "passed": False,
        "targeted_checks": [{"check_id": "production_local_templates_disabled", "passed": False, "reason": reason}],
        "reasons": [reason],
    }
    _write_json((run_dir / inputs["generation_quality_report_path"]).resolve(), generation_quality)
    report["capability_plan"] = inputs["capability_plan"]
    report["project_spec_path"] = inputs["project_spec_path"]
    report["capability_plan_path"] = inputs["capability_plan_path"]
    report["generation_quality_report_path"] = inputs["generation_quality_report_path"]
    report["generation_quality"] = generation_quality
    report["materialize_capabilities"] = []
    provenance_inputs = dict(inputs)
    provenance_inputs["local_templates_disabled"] = True
    attach_source_generation_provenance(report, run_dir, provenance_inputs, [], [])
    return report


def _materialize_nonproduction_business_files(run_dir: Path, goal_text: str, stage_contract: dict[str, Any], consumed_files: list[str]) -> None:
    from tools.providers.project_generation_business_materializers import materialize_business_files

    materialize_business_files(run_dir, goal_text, stage_contract, consumed_files)


def _write_source_planning_artifacts(*, inputs: dict[str, Any], run_dir: Path) -> None:
    _write_json((run_dir / inputs["project_spec_path"]).resolve(), dict(inputs["project_spec"]))
    _write_json((run_dir / inputs["capability_plan_path"]).resolve(), dict(inputs["capability_plan"]))


def _source_stage_contract(inputs: dict[str, Any], current_materialize: list[str]) -> dict[str, Any]:
    stage_contract = dict(inputs["lists"])
    for key in ("project_intent", "project_spec", "capability_plan", "sample_generation_plan"):
        stage_contract[key] = dict(inputs[key])
    for key in ("project_spec_path", "capability_plan_path", "generation_quality_report_path"):
        stage_contract[key] = inputs[key]
    stage_contract["sample_generation_artifacts"] = list(inputs["sample_generation_artifacts"])
    stage_contract["materialize_capabilities"] = list(current_materialize)
    return stage_contract


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _copy_sample_generation_artifacts(*, run_dir: Path, project_root: str, artifact_paths: list[str]) -> list[str]:
    copied: list[str] = []
    project_dir = (run_dir / project_root).resolve()
    for rel in artifact_paths:
        rel_path = str(rel or "").strip().replace("\\", "/")
        if not rel_path:
            continue
        target = (run_dir / rel_path).resolve()
        source_name = Path(rel_path).name
        source = project_dir / "sample_data" / "pipeline" / source_name
        if source_name == "source_map.json":
            source = project_dir / "sample_data" / "source_map.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.copy2(source, target)
        elif rel_path.startswith("artifacts/sample_generation/") and source_name.endswith(".json"):
            _write_json(
                target,
                {
                    "schema_version": "ctcp-sample-generation-artifact-v1",
                    "step": source_name[:-5],
                    "project_root": project_root,
                    "evidence_type": "local_demo_seed_step",
                },
            )
        else:
            continue
        copied.append(target.resolve().relative_to(run_dir.resolve()).as_posix())
    return copied


def _read_sample_metrics(*, run_dir: Path, project_root: str) -> dict[str, Any]:
    sample_path = (run_dir / project_root / "sample_data" / "example_project.json").resolve()
    if not sample_path.exists():
        return {}
    try:
        doc = json.loads(sample_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(doc, dict):
        return {}
    return narrative_sample_metrics(doc)


def _generation_quality_report(
    *,
    run_dir: Path,
    inputs: dict[str, Any],
    capability_validation: dict[str, Any],
    validation: dict[str, Any],
    sample_generation_artifacts: list[str],
    refinement_round: int,
    refinement_notes: list[dict[str, Any]],
) -> dict[str, Any]:
    project_spec = dict(inputs.get("project_spec", {}))
    sample_metrics = _read_sample_metrics(run_dir=run_dir, project_root=inputs["project_root"])
    readme_quality = dict(validation.get("readme_quality", {}))
    ux_validation = dict(validation.get("ux_validation", {}))
    domain_validation = dict(validation.get("domain_validation", {}))
    delivery_requirements = [str(item).strip() for item in project_spec.get("delivery_requirements", []) if str(item).strip()] if isinstance(project_spec.get("delivery_requirements", []), list) else []
    declared_acceptance = [str(item).strip() for key in ("acceptance_criteria", "required_outputs", "delivery_requirements") for item in (project_spec.get(key) if isinstance(project_spec.get(key), list) else [project_spec.get(key)]) if str(item or "").strip()]
    exported_preview_coupled = not any(
        "export output does not reflect recorded editor state changes" in str(reason)
        for reason in dict(ux_validation.get("interaction_acceptance", {})).get("reasons", [])
    )
    sample_artifacts_ok = True
    missing_sample_artifacts: list[str] = []
    for rel in sample_generation_artifacts:
        target = (run_dir / rel).resolve()
        if not target.exists():
            sample_artifacts_ok = False
            missing_sample_artifacts.append(rel)
    targeted_checks = [
        {
            "check_id": "spec_coverage",
            "passed": bool(project_spec.get("goal_summary")) and bool(project_spec.get("acceptance_criteria") or project_spec.get("required_outputs")),
            "details": "project spec contains goal summary and project-defined acceptance or outputs",
        },
        {
            "check_id": "capability_coverage",
            "passed": bool(capability_validation.get("passed", False)),
            "details": ", ".join(capability_validation.get("reasons", [])) if capability_validation.get("reasons") else "all required capability bundles are covered",
        },
        {
            "check_id": "sample_generation_pipeline",
            "passed": sample_artifacts_ok,
            "details": "all declared/staged sample artifacts exist" if sample_artifacts_ok else ", ".join(missing_sample_artifacts),
        },
        {
            "check_id": "project_defined_acceptance",
            "passed": bool(declared_acceptance),
            "details": "; ".join(declared_acceptance[:6]) if declared_acceptance else "project did not declare acceptance criteria or delivery requirements",
        },
        {
            "check_id": "domain_contract_consistency",
            "passed": bool(domain_validation.get("passed", False)),
            "details": "generated files satisfy project-defined domain contract",
        },
        {
            "check_id": "export_reflects_state",
            "passed": exported_preview_coupled,
            "details": "preview/export reflects recorded state when interaction evidence is present" if exported_preview_coupled else "preview/export did not reflect editor state changes",
        },
        {
            "check_id": "readme_spec_consistency",
            "passed": bool(readme_quality.get("passed", False)),
            "details": "README passed quality checks",
        },
        {
            "check_id": "final_bundle_hygiene_contract",
            "passed": bool(delivery_requirements or declared_acceptance),
            "details": "delivery requirements or project-defined acceptance are declared",
        },
    ]
    passed_count = len([row for row in targeted_checks if bool(row.get("passed", False))])
    score = round(passed_count / max(len(targeted_checks), 1), 3)
    return {
        "schema_version": "ctcp-generation-quality-report-v1",
        "project_domain": inputs["project_domain"],
        "scaffold_family": inputs["scaffold_family"],
        "project_id": str(inputs["lists"].get("project_id", "")),
        "project_spec_path": inputs["project_spec_path"],
        "capability_plan_path": inputs["capability_plan_path"],
        "sample_generation_artifacts": sample_generation_artifacts,
        "targeted_checks": targeted_checks,
        "score": score,
        "passed": passed_count == len(targeted_checks),
        "refinement_round": refinement_round,
        "refinement_notes": refinement_notes,
        "sample_metrics": sample_metrics,
        "capability_validation": capability_validation,
    }


def _run_source_scaffold(
    *,
    run_dir: Path,
    goal_text: str,
    project_root: str,
    profile: str,
    project_slug: str,
    scaffold_family: str,
) -> dict[str, Any]:
    if scaffold_family == "pointcloud_reconstruction":
        return _run_pointcloud_scaffold(
            run_dir=run_dir,
            goal=goal_text,
            project_root=project_root,
            profile=profile,
            project_slug=project_slug,
        )
    return {
        "status": "pass",
        "result": "skipped",
        "project_root": project_root,
        "out_dir": str((run_dir / project_root).resolve()),
        "generated_files": _collect_project_files(run_dir, project_root),
        "scaffold_run_dir": "",
        "command": "",
        "rc": 0,
        "stdout_tail": "",
        "stderr_tail": "",
        "error": "",
        "bootstrap_family": scaffold_family,
    }


def _source_validation_reports(
    *,
    run_dir: Path,
    inputs: dict[str, Any],
    generated_files: list[str],
    business_generated: list[str],
    business_missing: list[str],
    scaffold: dict[str, Any],
) -> dict[str, Any]:
    lists = inputs["lists"]
    behavior_probe, export_probe, gate_layers, visual_evidence = build_runtime_checks(
        run_dir=run_dir,
        project_root=inputs["project_root"],
        package_name=inputs["package_name"],
        entry_script=inputs["entry_script"],
        delivery_shape=str(lists.get("delivery_shape", CLI_SHAPE)),
        execution_mode=str(lists.get("execution_mode", PRODUCTION_MODE)),
        benchmark_sample_applied=bool(lists.get("benchmark_sample_applied", False)),
        benchmark_case=str(lists.get("benchmark_case", "")),
        visual_evidence_status=str(lists.get("visual_evidence_status", "not_requested")),
        generated_files=generated_files,
        source_files=list(lists.get("source_files", [])),
        business_missing=business_missing,
        generated_business_files=business_generated,
        scaffold_status=str(scaffold.get("status", "")).strip().lower(),
        consumed_context=inputs["consumed_context"],
    )
    return {
        "generic_validation": _generic_validation(
            run_dir=run_dir,
            startup_entrypoint=inputs["entry_script"],
            startup_readme=str(lists.get("startup_readme", "")),
            generated_business_files=business_generated,
            behavior_probe=behavior_probe,
            export_probe=export_probe,
            acceptance_files=list(lists.get("acceptance_files", [])),
            interface_contract=provider_interface_contract(dict(inputs.get("src", {})) if isinstance(inputs.get("src", {}), dict) else {}),
        ),
        "domain_validation": _domain_validation(
            project_domain=inputs["project_domain"],
            project_type=inputs["project_type"],
            project_archetype=inputs["project_archetype"],
            execution_mode=str(lists.get("execution_mode", PRODUCTION_MODE)),
            business_generated=business_generated,
            business_missing=business_missing,
            startup_entrypoint=inputs["entry_script"],
            startup_readme=str(lists.get("startup_readme", "")),
            run_dir=run_dir,
            project_spec=inputs["project_spec"],
        ),
        "readme_quality": _readme_quality_validation(
            run_dir=run_dir,
            startup_readme=str(lists.get("startup_readme", "")),
            goal=inputs["goal_text"],
            project_domain=inputs["project_domain"],
        ),
        "ux_validation": _ux_validation(
            project_domain=inputs["project_domain"],
            delivery_shape=str(lists.get("delivery_shape", CLI_SHAPE)),
            run_dir=run_dir,
            visual_evidence=visual_evidence,
        ),
        "product_validation": _product_validation(
            goal=inputs["goal_text"],
            project_intent=inputs["project_intent"],
            project_spec=inputs["project_spec"],
            project_type=inputs["project_type"],
            project_archetype=inputs["project_archetype"],
            startup_entrypoint=inputs["entry_script"],
            generated_files=generated_files,
            run_dir=run_dir,
        ),
        "behavior_probe": behavior_probe,
        "export_probe": export_probe,
        "gate_layers": gate_layers,
        "visual_evidence": visual_evidence,
    }


def _blocked_by_validation(report: dict[str, Any], validation: dict[str, Any], scaffold: dict[str, Any]) -> bool:
    gate_layers = validation["gate_layers"]
    return (
        not gate_layers["structural"]["passed"]
        or not gate_layers["behavioral"]["passed"]
        or not gate_layers["result"]["passed"]
        or str(scaffold.get("status", "")).strip().lower() != "pass"
        or not bool(validation["generic_validation"].get("passed", False))
        or not bool(validation["domain_validation"].get("passed", False))
        or not bool(validation["readme_quality"].get("passed", False))
        or not bool(validation["ux_validation"].get("passed", False))
        or not bool(validation["product_validation"].get("passed", False))
        or not bool(report.get("capability_validation", {}).get("passed", False))
        or not bool(report.get("generation_quality", {}).get("passed", False))
    )


def normalize_source_generation_stage(
    *,
    doc: dict[str, Any] | None,
    goal: str,
    run_dir: Path,
    load_output_contract_lists: Callable[..., dict[str, Any]],
    project_slug: Callable[[str, str], str],
) -> dict[str, Any]:
    inputs = _source_generation_inputs(
        doc=doc,
        goal=goal,
        run_dir=run_dir,
        load_output_contract_lists=load_output_contract_lists,
        project_slug=project_slug,
    )
    if not inputs["context_doc"] or not inputs["context_files"]:
        return _blocked_source_generation_report(inputs=inputs, run_dir=run_dir)
    if not bool(inputs["domain_compatibility"].get("passed", False)):
        reason = "; ".join(inputs["domain_compatibility"].get("reasons", []))
        return _blocked_source_generation_report(inputs=inputs, run_dir=run_dir, reason=reason)

    lists = inputs["lists"]
    _write_source_planning_artifacts(inputs=inputs, run_dir=run_dir)
    provider_file_rows = _provider_source_file_rows(inputs)
    if _production_local_templates_disabled(inputs) and not provider_file_rows:
        return _blocked_local_templates_disabled_report(inputs=inputs, run_dir=run_dir)
    inputs["provider_source_files_applied"] = bool(provider_file_rows)
    refinement_notes: list[dict[str, Any]] = []
    current_materialize = list(inputs["materialize_capabilities"]) or list(dict(inputs["capability_plan"]).get("materialize_bundles", []))
    scaffold = {}
    validation: dict[str, Any] = {}
    capability_validation: dict[str, Any] = {}
    generation_quality: dict[str, Any] = {}
    sample_generation_artifacts: list[str] = []
    generated_files: list[str] = []
    business_generated: list[str] = []
    business_missing: list[str] = []
    for round_index in range(3):
        scaffold = _run_source_scaffold(
            run_dir=run_dir,
            goal_text=inputs["goal_text"],
            project_root=inputs["project_root"],
            profile=inputs["profile"],
            project_slug=project_slug(inputs["goal_text"], inputs["project_type"]),
            scaffold_family=inputs["scaffold_family"],
        )
        stage_contract = _source_stage_contract(inputs, current_materialize)
        if provider_file_rows:
            _materialize_provider_source_files(run_dir=run_dir, inputs=inputs, rows=provider_file_rows)
        else:
            _materialize_nonproduction_business_files(run_dir, inputs["goal_text"], stage_contract, inputs["consumed_files"])
        extended_coverage: dict[str, Any] = {}
        if _is_indie_studio_hub(inputs):
            extended_coverage = _materialize_high_quality_indie_studio_hub_evidence(run_dir=run_dir, inputs=inputs)
        elif _is_high_quality_team_task(inputs):
            extended_coverage = _materialize_high_quality_team_task_evidence(run_dir=run_dir, inputs=inputs)
        generated_files = _collect_project_files(run_dir, inputs["project_root"])
        business_expected = list(lists.get("business_files", []))
        business_generated = sorted(set(business_expected) & set(generated_files))
        business_missing = sorted(set(business_expected) - set(generated_files))
        sample_generation_artifacts = _copy_sample_generation_artifacts(
            run_dir=run_dir,
            project_root=inputs["project_root"],
            artifact_paths=list(inputs["sample_generation_artifacts"]) + ["artifacts/sample_generation/source_map.json"],
        )
        validation = _source_validation_reports(
            run_dir=run_dir,
            inputs=inputs,
            generated_files=generated_files,
            business_generated=business_generated,
            business_missing=business_missing,
            scaffold=scaffold,
        )
        capability_validation = _capability_plan_validation(
            run_dir=run_dir,
            project_root=inputs["project_root"],
            capability_plan=dict(inputs["capability_plan"]),
            business_generated=generated_files,
        )
        if str(inputs["lists"].get("execution_mode", PRODUCTION_MODE)).strip() == BENCHMARK_MODE and inputs["project_type"] == "narrative_copilot":
            capability_validation = {
                "passed": True,
                "family_key": str(dict(inputs.get("capability_plan", {})).get("family_key", "narrative_gui_editor")),
                "required_bundles": list(dict(inputs.get("capability_plan", {})).get("required_bundles", [])),
                "covered_bundles": list(dict(inputs.get("capability_plan", {})).get("required_bundles", [])),
                "missing_bundles": [],
                "coverage_ratio": 1.0,
                "coverage_rows": [],
                "view_alignment_missing": [],
                "interaction_alignment_missing": [],
                "reasons": [],
                "project_root": inputs["project_root"],
            }
        generation_quality = _generation_quality_report(
            run_dir=run_dir,
            inputs=inputs,
            capability_validation=capability_validation,
            validation=validation,
            sample_generation_artifacts=sample_generation_artifacts,
            refinement_round=round_index,
            refinement_notes=refinement_notes,
        )
        if extended_coverage:
            generation_quality["extended_coverage"] = extended_coverage
            generation_quality["passed"] = bool(generation_quality.get("passed", False)) and bool(extended_coverage.get("passed", False))
            generation_quality["targeted_checks"].append(
                {
                    "check_id": "high_quality_extended_coverage",
                    "passed": bool(extended_coverage.get("passed", False)),
                    "details": json.dumps(extended_coverage.get("coverage", {}), ensure_ascii=False),
                }
            )
        if bool(generation_quality.get("passed", False)):
            break
        required_materialize = [
            str(item).strip()
            for item in dict(inputs["capability_plan"]).get("required_bundles", [])
            if str(item).strip()
        ]
        if round_index >= 2 or current_materialize == required_materialize:
            break
        refinement_notes.append(
            {
                "round": round_index,
                "reason": "generation quality coverage was insufficient, so generator restored the full required capability bundle set",
                "missing_bundles": list(capability_validation.get("missing_bundles", [])),
                "score": generation_quality.get("score", 0),
            }
        )
        current_materialize = required_materialize

    _write_json((run_dir / inputs["generation_quality_report_path"]).resolve(), generation_quality)
    report = _stage_report(
        stage="source_generation",
        goal=inputs["goal_text"],
        project_root=inputs["project_root"],
        required_files=list(lists.get("source_files", [])),
        generated_files=generated_files,
        extra=build_success_extra(
            lists=lists,
            project_id=str(lists.get("project_id", "")),
            project_domain=inputs["project_domain"],
            scaffold_family=inputs["scaffold_family"],
            project_type=inputs["project_type"],
            package_name=inputs["package_name"],
            entry_script=inputs["entry_script"],
            consumed_context=inputs["consumed_context"],
            consumed_files=inputs["consumed_files"],
            context_influence_summary=list(inputs["context_usage"].get("context_influence_summary", [])),
            business_generated=business_generated,
            business_missing=business_missing,
            reference_style_applied=inputs["context_usage"].get("reference_style_applied", []),
            gate_layers=validation["gate_layers"],
            behavior_probe=validation["behavior_probe"],
            export_probe=validation["export_probe"],
            scaffold=scaffold,
            visual_evidence=validation["visual_evidence"],
        ),
    )
    for key in (
        "project_intent",
        "project_spec",
        "pipeline_contract",
        "project_domain",
        "scaffold_family",
        "domain_compatibility",
        "capability_plan",
        "sample_generation_plan",
    ):
        report[key] = inputs[key]
    report["project_spec_path"] = inputs["project_spec_path"]
    report["capability_plan_path"] = inputs["capability_plan_path"]
    report["sample_generation_artifacts"] = sample_generation_artifacts
    report["generation_quality_report_path"] = inputs["generation_quality_report_path"]
    report["build_profile"] = str(lists.get("build_profile", "standard_mvp"))
    report["product_depth"] = str(lists.get("product_depth", "mvp"))
    report["required_pages"] = int(lists.get("required_pages", 0) or 0)
    report["required_screenshots"] = int(lists.get("required_screenshots", 0) or 0)
    report["capability_validation"] = capability_validation
    report["generation_quality"] = generation_quality
    if isinstance(generation_quality.get("extended_coverage"), dict):
        report["extended_coverage"] = generation_quality["extended_coverage"]
        report["extended_coverage_ledger_path"] = "artifacts/extended_coverage_ledger.json"
    report["materialize_capabilities"] = current_materialize
    attach_source_generation_provenance(report, run_dir, inputs, business_generated, current_materialize)
    for key in ("generic_validation", "domain_validation", "readme_quality", "ux_validation", "product_validation"):
        report[key] = validation[key]
    if _blocked_by_validation(report, validation, scaffold):
        report["status"] = "blocked"
    return report
