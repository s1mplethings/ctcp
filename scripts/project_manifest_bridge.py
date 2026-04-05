from __future__ import annotations

from pathlib import Path
from typing import Any

_SOURCE_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".css", ".java", ".go", ".rs", ".c", ".cpp", ".h"}
_WORKFLOW_HINT_FILES = {"TRACE.md", "events.jsonl", "RUN.json", "step_meta.jsonl", "repo_ref.json"}


def _infer_project_manifest(run_id: str, artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    source_files: list[str] = []
    doc_files: list[str] = []
    workflow_files: list[str] = []
    generated_files: list[str] = []

    for row in artifacts:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("rel_path", "")).strip()
        if not rel:
            continue
        generated_files.append(rel)
        suffix = Path(rel).suffix.lower()
        if suffix in _SOURCE_EXTS and not rel.startswith("logs/"):
            source_files.append(rel)
        if suffix in {".md", ".txt"} and not rel.startswith("logs/"):
            doc_files.append(rel)
        if rel.startswith("artifacts/") or rel in _WORKFLOW_HINT_FILES:
            workflow_files.append(rel)

    return {
        "run_id": run_id,
        "project_id": run_id,
        "project_root": "",
        "project_type": "",
        "project_profile": "",
        "generation_mode": "",
        "execution_mode": "production",
        "benchmark_case": "",
        "delivery_shape": "cli_first",
        "project_type_decision_source": "",
        "shape_decision_source": "",
        "source_files": sorted(set(source_files)),
        "doc_files": sorted(set(doc_files)),
        "workflow_files": sorted(set(workflow_files)),
        "business_files_generated": [],
        "business_files_missing": [],
        "generated_files": sorted(set(generated_files)),
        "missing_files": [],
        "acceptance_files": [],
        "startup_entrypoint": "",
        "startup_readme": "",
        "scaffold_run_dir": "",
        "reference_project_mode": {"enabled": False, "mode": "structure_workflow_docs"},
        "reference_style_applied": [],
        "business_codegen_used": False,
        "consumed_context_pack": False,
        "consumed_context_files": [],
        "context_influence_summary": [],
        "demo_required": False,
        "visual_evidence_required": False,
        "screenshot_required": False,
        "visual_evidence_status": "not_requested",
        "benchmark_sample_applied": False,
        "decision_nodes": [],
        "flow_nodes": [],
        "gate_layers": {},
        "behavioral_checks": {},
        "artifacts": artifacts,
    }


def resolve_project_manifest(
    *,
    run_id: str,
    run_dir: Path,
    artifacts: list[dict[str, Any]],
    declared: dict[str, Any] | None,
) -> dict[str, Any]:
    inferred = _infer_project_manifest(run_id, artifacts)
    if isinstance(declared, dict):
        out = dict(inferred)
        out["project_id"] = str(declared.get("project_id", "")).strip() or str(out.get("project_id", ""))
        out["project_root"] = str(declared.get("project_root", "")).strip() or str(out.get("project_root", ""))
        out["project_type"] = str(declared.get("project_type", "")).strip() or str(out.get("project_type", ""))
        out["project_profile"] = str(declared.get("project_profile", "")).strip() or str(out.get("project_profile", ""))
        out["generation_mode"] = str(declared.get("generation_mode", "")).strip() or str(out.get("generation_mode", ""))
        out["execution_mode"] = str(declared.get("execution_mode", "")).strip() or str(out.get("execution_mode", ""))
        out["benchmark_case"] = str(declared.get("benchmark_case", "")).strip() or str(out.get("benchmark_case", ""))
        out["delivery_shape"] = str(declared.get("delivery_shape", "")).strip() or str(out.get("delivery_shape", ""))
        out["project_type_decision_source"] = str(declared.get("project_type_decision_source", "")).strip() or str(out.get("project_type_decision_source", ""))
        out["shape_decision_source"] = str(declared.get("shape_decision_source", "")).strip() or str(out.get("shape_decision_source", ""))
        out["startup_entrypoint"] = str(declared.get("startup_entrypoint", "")).strip() or str(out.get("startup_entrypoint", ""))
        out["startup_readme"] = str(declared.get("startup_readme", "")).strip() or str(out.get("startup_readme", ""))
        out["scaffold_run_dir"] = str(declared.get("scaffold_run_dir", "")).strip() or str(out.get("scaffold_run_dir", ""))
        for field in (
            "source_files",
            "doc_files",
            "workflow_files",
            "business_files_generated",
            "business_files_missing",
            "generated_files",
            "missing_files",
            "acceptance_files",
            "artifacts",
            "reference_style_applied",
            "consumed_context_files",
            "context_influence_summary",
            "decision_nodes",
            "flow_nodes",
        ):
            value = declared.get(field)
            if isinstance(value, list):
                out[field] = value
        for field in ("gate_layers", "behavioral_checks"):
            value = declared.get(field)
            if isinstance(value, dict):
                out[field] = value
        mode = declared.get("reference_project_mode")
        if isinstance(mode, dict) and "enabled" in mode and "mode" in mode:
            out["reference_project_mode"] = mode
        out["business_codegen_used"] = bool(declared.get("business_codegen_used", out.get("business_codegen_used", False)))
        out["consumed_context_pack"] = bool(declared.get("consumed_context_pack", out.get("consumed_context_pack", False)))
        out["demo_required"] = bool(declared.get("demo_required", out.get("demo_required", False)))
        out["visual_evidence_required"] = bool(declared.get("visual_evidence_required", out.get("visual_evidence_required", False)))
        out["screenshot_required"] = bool(declared.get("screenshot_required", out.get("screenshot_required", False)))
        out["visual_evidence_status"] = str(declared.get("visual_evidence_status", "")).strip() or str(out.get("visual_evidence_status", ""))
        out["benchmark_sample_applied"] = bool(declared.get("benchmark_sample_applied", out.get("benchmark_sample_applied", False)))
        out["run_dir"] = str(run_dir)
        out["manifest_path"] = "artifacts/project_manifest.json"
        out["manifest_source"] = "declared"
        return out

    return {
        **inferred,
        "run_dir": str(run_dir),
        "manifest_path": "",
        "manifest_source": "inferred",
    }
