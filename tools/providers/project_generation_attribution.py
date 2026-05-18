from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_generation_attribution(
    *,
    run_dir: Path,
    project_id: str,
    project_root: str,
    provenance: dict[str, Any] | None,
    source_generation_report_path: str = "artifacts/source_generation_report.json",
) -> dict[str, Any]:
    source_rel = str(source_generation_report_path or "artifacts/source_generation_report.json")
    project_root_rel = str(project_root or f"project_output/{project_id}").replace("\\", "/")
    prov = dict(provenance or {})
    used_local_materializer = bool(prov.get("local_materializer_used", False))
    provider_authorship = str(prov.get("provider_authorship", "not_claimed"))
    used_provider_agent = bool(prov.get("used_provider_agent", False))
    provider_validation = prov.get("provider_validation") if isinstance(prov.get("provider_validation"), dict) else {}
    candidate_validation = prov.get("provider_candidate_validation") if isinstance(prov.get("provider_candidate_validation"), dict) else {}
    return {
        "ordinary_mainline": True,
        "entrypoint": "new-run/status/advance",
        "used_agent_project": False,
        "used_agent_scaffold": False,
        "used_local_agent_runtime": False,
        "used_local_materializer": used_local_materializer,
        "local_materializer_name": str(prov.get("project_type", project_id or "concrete_project")) if used_local_materializer else "",
        "used_provider_agent": used_provider_agent,
        "provider_name": str(prov.get("provider_name", "local_fixture_provider" if used_provider_agent else ("local_deterministic_materializer" if used_local_materializer else ""))),
        "provider_authorship": provider_authorship,
        "generation_mode": str(prov.get("generation_mode", "unknown")),
        "live_provider_used": bool(prov.get("live_provider_used", False)),
        "provider_request_count": int(prov.get("provider_request_count", 0) or 0),
        "provider_fragment_count": int(prov.get("provider_fragment_count", 0) or 0),
        "provider_project_candidate_count": int(prov.get("provider_project_candidate_count", 0) or 0),
        "provider_plan_requested": bool(prov.get("provider_plan_requested", False)),
        "provider_plan_valid": bool(prov.get("provider_plan_valid", False)),
        "provider_manifest_valid": bool(prov.get("provider_manifest_valid", False)),
        "provider_manifest_file_count": int(prov.get("provider_manifest_file_count", 0) or 0),
        "provider_batch_count": int(prov.get("provider_batch_count", 0) or 0),
        "provider_batch_success_count": int(prov.get("provider_batch_success_count", 0) or 0),
        "provider_batch_retry_count": int(prov.get("provider_batch_retry_count", 0) or 0),
        "provider_batch_errors": list(prov.get("provider_batch_errors", [])) if isinstance(prov.get("provider_batch_errors", []), list) else [],
        "provider_raw_response_paths": list(prov.get("provider_raw_response_paths", [])) if isinstance(prov.get("provider_raw_response_paths", []), list) else [],
        "normalized_manifest_path": str(prov.get("normalized_manifest_path", "")),
        "validation_failure_path": str(prov.get("validation_failure_path", "")),
        "repair_report_path": str(prov.get("repair_report_path", "")),
        "blind_case": bool(prov.get("blind_case", False)),
        "blind_case_name": str(prov.get("blind_case_name", "")),
        "medium_case": bool(prov.get("medium_case", False)),
        "medium_case_name": str(prov.get("medium_case_name", "")),
        "medium_project_contract_path": str(prov.get("medium_project_contract_path", "artifacts/medium_project_contract.json" if prov.get("medium_case") else "")),
        "provider_candidate_outcome": str(prov.get("provider_candidate_outcome", "")),
        "provider_candidate_accepted": bool(prov.get("provider_candidate_accepted", False)),
        "provider_candidate_repaired": bool(prov.get("provider_candidate_repaired", False)),
        "provider_repair_attempt_count": int(prov.get("provider_repair_attempt_count", 0) or 0),
        "provider_repair_sections": list(prov.get("provider_repair_sections", [])) if isinstance(prov.get("provider_repair_sections", []), list) else [],
        "repair_validation_passed": bool(prov.get("repair_validation_passed", False)),
        "fallback_triggered": bool(prov.get("fallback_triggered", False)),
        "unsupported_reason": prov.get("unsupported_reason", None),
        "validation_failures": list(prov.get("validation_failures", [])) if isinstance(prov.get("validation_failures", []), list) else [],
        "provider_candidate_validation": {
            "manifest_valid": bool(candidate_validation.get("manifest_valid", True)),
            "paths_safe": bool(candidate_validation.get("paths_safe", True)),
            "safety_scan_passed": bool(candidate_validation.get("safety_scan_passed", True)),
            "syntax_valid": bool(candidate_validation.get("syntax_valid", True)),
            "import_valid": bool(candidate_validation.get("import_valid", True)),
            "generated_tests_passed": bool(candidate_validation.get("generated_tests_passed", True)),
            "runtime_validation_passed": bool(candidate_validation.get("runtime_validation_passed", True)),
        },
        "provider_assisted_sections": list(prov.get("provider_assisted_sections", [])) if isinstance(prov.get("provider_assisted_sections", []), list) else [],
        "provider_generated_files": list(prov.get("provider_generated_files", [])) if isinstance(prov.get("provider_generated_files", []), list) else [],
        "total_project_files": int(prov.get("total_project_files", 0) or 0),
        "provider_authored_file_ratio": float(prov.get("provider_authored_file_ratio", 0.0) or 0.0),
        "provider_fallbacks": list(prov.get("provider_fallbacks", [])) if isinstance(prov.get("provider_fallbacks", []), list) else [],
        "fallback_reason": str(prov.get("fallback_reason", "")),
        "runtime_validation_passed": bool(prov.get("runtime_validation_passed", False)),
        "provider_validation": {
            "syntax_valid": bool(provider_validation.get("syntax_valid", True)),
            "runtime_valid": bool(provider_validation.get("runtime_valid", True)),
            "fallback_triggered": bool(provider_validation.get("fallback_triggered", False)),
        },
        "provider_model": str(prov.get("provider_model", "")),
        "provider_timeout_seconds": int(prov.get("provider_timeout_seconds", 0) or 0),
        "deterministic_sections": list(prov.get("deterministic_sections", [])) if isinstance(prov.get("deterministic_sections", []), list) else [],
        "source_generation_report_path": source_rel,
        "project_output_path": project_root_rel,
        "analysis_path": "artifacts/analysis.md",
        "run_dir": str(run_dir),
    }


def write_generation_attribution(
    *,
    run_dir: Path,
    project_id: str,
    project_root: str,
    provenance: dict[str, Any] | None,
    source_generation_report_path: str = "artifacts/source_generation_report.json",
) -> dict[str, Any]:
    attribution = build_generation_attribution(
        run_dir=run_dir,
        project_id=project_id,
        project_root=project_root,
        provenance=provenance,
        source_generation_report_path=source_generation_report_path,
    )
    out = run_dir / "artifacts" / "generation_attribution.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(attribution, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if attribution.get("medium_case"):
        try:
            from tools.providers.project_generation_medium_candidate import medium_project_contract

            contract = medium_project_contract(str(attribution.get("medium_case_name", "")))
            contract_path = run_dir / "artifacts" / "medium_project_contract.json"
            contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except Exception:
            pass
    return attribution
