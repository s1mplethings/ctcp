from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.providers.project_generation_decisions import CLI_SHAPE, PRODUCTION_MODE, TOOL_SHAPE


def build_missing_context_extra(*, lists: dict[str, Any], project_id: str, project_type: str, package_name: str, entry_script: str) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_type": project_type,
        "project_archetype": str(lists.get("project_archetype", "")),
        "package_name": package_name,
        "execution_mode": str(lists.get("execution_mode", PRODUCTION_MODE)),
        "benchmark_case": str(lists.get("benchmark_case", "")),
        "delivery_shape": str(lists.get("delivery_shape", CLI_SHAPE)),
        "project_type_decision_source": str(lists.get("project_type_decision_source", "")),
        "project_archetype_decision_source": str(lists.get("project_archetype_decision_source", "")),
        "shape_decision_source": str(lists.get("shape_decision_source", "")),
        "entrypoint": entry_script,
        "startup_readme": str(lists.get("startup_readme", "")),
        "generation_mode": str(lists.get("generation_mode", "")),
        "scaffold_bootstrap_used": False,
        "business_codegen_used": False,
        "consumed_context_pack": False,
        "consumed_context_files": [],
        "context_influence_summary": [],
        "business_files_generated": [],
        "business_files_missing": list(lists.get("business_files", [])),
        "reference_project_mode": lists.get("reference_project_mode", {"enabled": False, "mode": "structure_workflow_docs"}),
        "reference_style_applied": [],
        "demo_required": bool(lists.get("demo_required", False)),
        "visual_evidence_required": bool(lists.get("visual_evidence_required", False)),
        "screenshot_required": bool(lists.get("screenshot_required", False)),
        "visual_evidence_status": str(lists.get("visual_evidence_status", "not_requested")),
        "benchmark_sample_applied": bool(lists.get("benchmark_sample_applied", False)),
        "decision_nodes": list(lists.get("decision_nodes", [])),
        "flow_nodes": list(lists.get("flow_nodes", [])),
        "gate_layers": {
            "structural": {"passed": False, "reason": "missing context pack"},
            "behavioral": {"passed": False, "reason": "missing context pack"},
            "result": {"passed": False, "target": "missing_context_pack", "reason": "missing context pack"},
        },
        "behavioral_checks": {"startup_probe": {}, "export_probe": {}},
        "context_pack_error": "missing_or_empty_context_pack",
    }


def build_success_extra(
    *,
    lists: dict[str, Any],
    project_id: str,
    project_type: str,
    package_name: str,
    entry_script: str,
    consumed_context: bool,
    consumed_files: list[str],
    context_influence_summary: list[str],
    business_generated: list[str],
    business_missing: list[str],
    reference_style_applied: list[str],
    gate_layers: dict[str, Any],
    behavior_probe: dict[str, Any],
    export_probe: dict[str, Any],
    scaffold: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project_id": project_id,
        "project_type": project_type,
        "project_archetype": str(lists.get("project_archetype", "")),
        "package_name": package_name,
        "execution_mode": str(lists.get("execution_mode", PRODUCTION_MODE)),
        "benchmark_case": str(lists.get("benchmark_case", "")),
        "delivery_shape": str(lists.get("delivery_shape", CLI_SHAPE)),
        "project_type_decision_source": str(lists.get("project_type_decision_source", "")),
        "project_archetype_decision_source": str(lists.get("project_archetype_decision_source", "")),
        "shape_decision_source": str(lists.get("shape_decision_source", "")),
        "entrypoint": entry_script,
        "startup_readme": str(lists.get("startup_readme", "")),
        "generation_mode": str(lists.get("generation_mode", "")),
        "scaffold_bootstrap_used": str(scaffold.get("status", "")).strip().lower() == "pass",
        "business_codegen_used": bool(business_generated),
        "consumed_context_pack": consumed_context,
        "consumed_context_files": consumed_files,
        "context_influence_summary": context_influence_summary,
        "business_files_generated": business_generated,
        "business_files_missing": business_missing,
        "reference_project_mode": lists.get("reference_project_mode", {"enabled": False, "mode": "structure_workflow_docs"}),
        "reference_style_applied": reference_style_applied,
        "demo_required": bool(lists.get("demo_required", False)),
        "visual_evidence_required": bool(lists.get("visual_evidence_required", False)),
        "screenshot_required": bool(lists.get("screenshot_required", False)),
        "visual_evidence_status": str(lists.get("visual_evidence_status", "not_requested")),
        "benchmark_sample_applied": bool(lists.get("benchmark_sample_applied", False)),
        "decision_nodes": list(lists.get("decision_nodes", [])),
        "flow_nodes": list(lists.get("flow_nodes", [])),
        "gate_layers": gate_layers,
        "behavioral_checks": {"startup_probe": behavior_probe, "export_probe": export_probe},
        "scaffold": scaffold,
    }


def _run_command_capture(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": " ".join(cmd),
        "rc": int(proc.returncode),
        "stdout_tail": "\n".join(str(proc.stdout or "").splitlines()[-12:]),
        "stderr_tail": "\n".join(str(proc.stderr or "").splitlines()[-12:]),
        "status": "pass" if int(proc.returncode) == 0 else "blocked",
    }


def build_runtime_checks(
    *,
    run_dir: Path,
    project_root: str,
    package_name: str,
    entry_script: str,
    delivery_shape: str,
    execution_mode: str,
    benchmark_sample_applied: bool,
    benchmark_case: str,
    visual_evidence_status: str,
    generated_files: list[str],
    source_files: list[str],
    business_missing: list[str],
    generated_business_files: list[str],
    scaffold_status: str,
    consumed_context: bool,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    src_root = (run_dir / project_root / "src").resolve()
    if delivery_shape == TOOL_SHAPE:
        behavior_probe = _run_command_capture(
            [sys.executable, "-c", f"import sys;sys.path.insert(0, r'{src_root}');import {package_name}.service as service;print('ok' if hasattr(service, 'generate_project') else 'missing')"],
            cwd=run_dir,
        )
    else:
        entry_path = (run_dir / entry_script).resolve()
        behavior_probe = _run_command_capture([sys.executable, str(entry_path), "--help"], cwd=entry_path.parent)
    with tempfile.TemporaryDirectory(prefix="ctcp_project_export_probe_") as td:
        if delivery_shape == TOOL_SHAPE:
            export_probe = _run_command_capture(
                [sys.executable, "-c", f"import json, sys;from pathlib import Path;sys.path.insert(0, r'{src_root}');from {package_name}.service import generate_project;result = generate_project(goal='smoke export', project_name='Smoke Project', out_dir=Path(r'{Path(td)}'));print(json.dumps(result, ensure_ascii=False))"],
                cwd=run_dir,
            )
        else:
            entry_path = (run_dir / entry_script).resolve()
            export_probe = _run_command_capture([sys.executable, str(entry_path), "--goal", "smoke export", "--project-name", "Smoke Project", "--out", str(Path(td))], cwd=entry_path.parent)
    gate_layers = {
        "structural": {
            "passed": not sorted(set(source_files) - set(generated_files)) and scaffold_status == "pass" and bool(generated_business_files) and not business_missing,
            "reason": "required files, manifest inputs, and deliverables are all present",
        },
        "behavioral": {
            "passed": str(behavior_probe.get("status", "")).lower() == "pass" and str(export_probe.get("status", "")).lower() == "pass",
            "reason": "startup and export probes passed",
        },
        "result": {
            "passed": consumed_context and not (execution_mode == PRODUCTION_MODE and benchmark_sample_applied) and visual_evidence_status in {"not_requested", "placeholder_only", "provided"},
            "target": benchmark_case or ("production_request_goal" if execution_mode == PRODUCTION_MODE else "benchmark_regression_case"),
            "reason": "mode-specific result contract satisfied",
        },
    }
    return behavior_probe, export_probe, gate_layers
