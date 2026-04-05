from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
ORCH_SCRIPT = ROOT / "scripts" / "ctcp_orchestrate.py"
POINTCLOUD_DIALOGUE_SCRIPT = ROOT / "tests" / "fixtures" / "dialogues" / "scaffold_pointcloud.jsonl"

from tools.providers.project_generation_business_templates import materialize_business_files
from tools.providers.project_generation_decisions import (
    BENCHMARK_HINTS,
    BENCHMARK_MODE,
    CLI_SHAPE,
    FLOW_NODES,
    GUI_KEYWORDS,
    GUI_SHAPE,
    PRODUCTION_MODE,
    STRONG_DECISION_NODES,
    TOOL_KEYWORDS,
    TOOL_SHAPE,
    NARRATIVE_KEYWORDS,
    WEB_KEYWORDS,
    WEB_SHAPE,
    contains_any as _contains_any,
    decide_project_generation,
    default_package_name,
    default_project_id,
    detect_project_type,
    normalize_mode as _normalize_mode,
    shape_contract,
)
from tools.providers.project_generation_source_helpers import (
    build_missing_context_extra,
    build_runtime_checks,
    build_success_extra,
)
PROJECT_GENERATION_KEYWORDS = (
    "generate",
    "generator",
    "project",
    "assistant",
    "copilot",
    "tool",
    "app",
    "application",
    "service",
    "workspace",
    "生成",
    "项目",
    "工具",
    "助手",
    "服务",
)


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", (text or "").strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "goal"


def is_project_generation_goal(goal: str) -> bool:
    return _contains_any(goal, NARRATIVE_KEYWORDS + PROJECT_GENERATION_KEYWORDS)


def build_default_context_request(goal: str) -> dict[str, Any]:
    if not is_project_generation_goal(goal):
        return {
            "needs": [{"path": "README.md", "mode": "snippets", "line_ranges": [[1, 80]]}],
            "budget": {"max_files": 6, "max_total_bytes": 48000},
            "reason": "chair file request for downstream context pack",
        }

    return {
        "needs": [
            {"path": "README.md", "mode": "snippets", "line_ranges": [[1, 120]]},
            {"path": "docs/04_execution_flow.md", "mode": "snippets", "line_ranges": [[1, 220]]},
            {"path": "docs/41_low_capability_project_generation.md", "mode": "snippets", "line_ranges": [[1, 220]]},
            {"path": "docs/backend_interface_contract.md", "mode": "snippets", "line_ranges": [[1, 220]]},
            {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "mode": "full"},
            {"path": "tools/providers/project_generation_artifacts.py", "mode": "snippets", "line_ranges": [[1, 360]]},
            {"path": "tools/providers/api_agent.py", "mode": "snippets", "line_ranges": [[120, 420]]},
            {"path": "scripts/ctcp_dispatch.py", "mode": "snippets", "line_ranges": [[840, 940]]},
            {"path": "scripts/ctcp_front_bridge.py", "mode": "snippets", "line_ranges": [[740, 860]]},
            {"path": "scripts/project_generation_gate.py", "mode": "full"},
            {"path": "scripts/project_manifest_bridge.py", "mode": "full"},
            {"path": "scripts/ctcp_librarian.py", "mode": "snippets", "line_ranges": [[1, 360]]},
        ],
        "budget": {"max_files": 18, "max_total_bytes": 220000},
        "reason": "project-generation repo context for business code materialization",
    }


def _project_slug(goal: str, project_type: str = "generic_copilot") -> str:
    return default_project_id(_slug(goal), project_type, PRODUCTION_MODE)


def _normalize_rel_list(rows: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in rows:
        value = str(raw or "").strip().replace("\\", "/")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def normalize_patch_payload(raw_text: str) -> tuple[str, str]:
    text = str(raw_text or "")
    if not text.strip():
        return "", "patch output is empty"

    fenced_blocks = re.findall(r"```(?:diff|patch)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE)
    if fenced_blocks:
        for block in fenced_blocks:
            if "diff --git " in block:
                text = block
                break

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start_idx = -1
    for idx, line in enumerate(lines):
        if line.startswith("diff --git "):
            start_idx = idx
            break
    if start_idx < 0:
        return "", "patch output must contain diff --git header"

    normalized_lines = [line for line in lines[start_idx:] if line.strip()]
    if not normalized_lines:
        return "", "patch output has no non-empty diff lines"
    if not normalized_lines[0].startswith("diff --git "):
        return "", "patch output must start with diff --git"
    return "\n".join(normalized_lines).rstrip() + "\n", ""


def _prefixed(project_root: str, rels: list[str]) -> list[str]:
    root = str(project_root or "").strip().replace("\\", "/").strip("/")
    return [f"{root}/{rel}".replace("//", "/") for rel in rels]


def _benchmark_narrative_defaults() -> dict[str, Any]:
    return {
        "source_rel": [
            "pyproject.toml",
            "scripts/run_narrative_copilot.py",
            "src/narrative_copilot/__init__.py",
            "src/narrative_copilot/models.py",
            "src/narrative_copilot/story/__init__.py",
            "src/narrative_copilot/story/outline.py",
            "src/narrative_copilot/story/chapter_planner.py",
            "src/narrative_copilot/cast/__init__.py",
            "src/narrative_copilot/cast/schema.py",
            "src/narrative_copilot/pipeline/__init__.py",
            "src/narrative_copilot/pipeline/prompt_pipeline.py",
            "src/narrative_copilot/exporters/__init__.py",
            "src/narrative_copilot/exporters/deliver.py",
            "src/narrative_copilot/service.py",
            "tests/test_narrative_copilot_service.py",
        ],
        "doc_rel": ["README.md", "docs/00_CORE.md", "docs/benchmark_workflow.md"],
        "business_rel": [
            "scripts/run_narrative_copilot.py",
            "src/narrative_copilot/models.py",
            "src/narrative_copilot/story/outline.py",
            "src/narrative_copilot/story/chapter_planner.py",
            "src/narrative_copilot/cast/schema.py",
            "src/narrative_copilot/pipeline/prompt_pipeline.py",
            "src/narrative_copilot/exporters/deliver.py",
            "src/narrative_copilot/service.py",
            "tests/test_narrative_copilot_service.py",
        ],
        "capabilities": [
            "story_outline",
            "chapter_planning",
            "character_schema",
            "scene_prompt_pipeline",
            "deliver_export",
            "cli_service",
            "business_tests",
            "benchmark_sample",
        ],
        "startup_rel": "scripts/run_narrative_copilot.py",
        "project_profile": "narrative_copilot_benchmark",
        "generation_mode": "benchmark_narrative_business_deliverable_first",
    }


def _production_project_defaults(project_type: str, package_name: str, delivery_shape: str) -> dict[str, Any]:
    shape_info = shape_contract(delivery_shape, package_name)
    startup_rel = str(shape_info["startup_rel"])
    workflow_doc_rel = str(shape_info["workflow_doc_rel"])
    if project_type == "narrative_copilot":
        source_rel = [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/story/__init__.py",
            f"src/{package_name}/story/outline.py",
            f"src/{package_name}/story/stage_planner.py",
            f"src/{package_name}/cast/__init__.py",
            f"src/{package_name}/cast/schema.py",
            f"src/{package_name}/pipeline/__init__.py",
            f"src/{package_name}/pipeline/prompt_pipeline.py",
            f"src/{package_name}/exporters/__init__.py",
            f"src/{package_name}/exporters/deliver.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ]
        business_rel = [
            startup_rel,
            f"src/{package_name}/models.py",
            f"src/{package_name}/story/outline.py",
            f"src/{package_name}/story/stage_planner.py",
            f"src/{package_name}/cast/schema.py",
            f"src/{package_name}/pipeline/prompt_pipeline.py",
            f"src/{package_name}/exporters/deliver.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ]
        capabilities = [
            "story_outline",
            "stage_planning",
            "role_schema",
            "prompt_export",
            str(shape_info["shape_capability"]),
            "business_tests",
        ]
        project_profile = "narrative_copilot"
        generation_mode = "production_narrative_deliverable_first"
    else:
        source_rel = [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/planner.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ]
        business_rel = [
            startup_rel,
            f"src/{package_name}/models.py",
            f"src/{package_name}/planner.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ]
        capabilities = [
            "domain_model",
            "planning_logic",
            "deliver_export",
            str(shape_info["shape_capability"]),
            "business_tests",
        ]
        project_profile = "business_copilot"
        generation_mode = "production_business_deliverable_first"
    if startup_rel.startswith("scripts/"):
        source_rel.insert(1, startup_rel)
    return {
        "source_rel": source_rel,
        "doc_rel": ["README.md", "docs/00_CORE.md", workflow_doc_rel],
        "business_rel": [row for row in business_rel if row],
        "capabilities": capabilities,
        "startup_rel": startup_rel,
        "project_profile": project_profile,
        "generation_mode": generation_mode,
    }


def _assemble_project_file_lists(
    *,
    project_root: str,
    project_id: str,
    project_type: str,
    package_name: str,
    decision: dict[str, Any],
    defaults: dict[str, Any],
) -> dict[str, Any]:
    workflow_rel = [
        "meta/tasks/CURRENT.md",
        "meta/reports/LAST.md",
        "meta/manifest.json",
        "scripts/verify_repo.ps1",
    ]
    source_files = _prefixed(project_root, defaults["source_rel"])
    doc_files = _prefixed(project_root, defaults["doc_rel"])
    workflow_files = _prefixed(project_root, workflow_rel)
    business_files = _prefixed(project_root, defaults["business_rel"])
    startup_entrypoint = f"{project_root}/{defaults['startup_rel']}".replace("//", "/")
    return {
        "project_id": project_id,
        "project_root": project_root,
        "project_type": project_type,
        "package_name": package_name,
        "project_profile": str(defaults["project_profile"]),
        "generation_mode": str(defaults["generation_mode"]),
        "execution_mode": str(decision["execution_mode"]),
        "benchmark_case": str(decision["benchmark_case"]),
        "delivery_shape": str(decision["delivery_shape"]),
        "project_type_decision_source": str(decision["project_type_decision_source"]),
        "shape_decision_source": str(decision["shape_decision_source"]),
        "target_files": sorted(set(source_files + doc_files + workflow_files)),
        "source_files": source_files,
        "doc_files": doc_files,
        "workflow_files": workflow_files,
        "business_files": business_files,
        "business_capabilities": list(defaults["capabilities"]),
        "acceptance_files": [f"{project_root}/README.md", startup_entrypoint, business_files[-1]],
        "startup_entrypoint": startup_entrypoint,
        "startup_readme": f"{project_root}/README.md",
        "reference_project_mode": {"enabled": True, "mode": "structure_workflow_docs"},
        "reference_style_applied": [
            "repo_script_layout",
            "workflow_manifest_stage_chain",
            "bridge_readable_manifest",
        ],
        "demo_required": bool(decision["demo_required"]),
        "visual_evidence_required": bool(decision["visual_evidence_required"]),
        "screenshot_required": bool(decision["screenshot_required"]),
        "visual_evidence_status": str(decision["visual_evidence_status"]),
        "benchmark_sample_applied": bool(decision["benchmark_sample_applied"]),
        "decision_nodes": list(decision["decision_nodes"]),
        "flow_nodes": list(decision["flow_nodes"]),
    }


def _default_project_file_lists(
    goal: str,
    *,
    run_dir: Path | None = None,
    context_files: list[dict[str, Any]] | None = None,
    src: dict[str, Any] | None = None,
) -> dict[str, Any]:
    decision = decide_project_generation(goal, run_dir=run_dir, context_files=context_files, src=src)
    execution_mode = str(decision["execution_mode"])
    benchmark_case = str(decision["benchmark_case"])
    project_type = str(decision["project_type"])
    project_id = default_project_id(_slug(goal), project_type, execution_mode)
    package_name = default_package_name(project_id, project_type, execution_mode, benchmark_case)
    project_root = f"project_output/{project_id}"
    if execution_mode == BENCHMARK_MODE and project_type == "narrative_copilot":
        defaults = _benchmark_narrative_defaults()
    else:
        defaults = _production_project_defaults(project_type, package_name, str(decision["delivery_shape"]))
    return _assemble_project_file_lists(
        project_root=project_root,
        project_id=project_id,
        project_type=project_type,
        package_name=package_name,
        decision=decision,
        defaults=defaults,
    )


def normalize_output_contract_freeze(doc: dict[str, Any] | None, *, goal: str, run_dir: Path | None = None) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    defaults = _default_project_file_lists(goal_text, run_dir=run_dir, src=src)
    project_root = str(defaults["project_root"])
    project_id = str(defaults["project_id"])
    project_type = str(defaults["project_type"])
    package_name = str(defaults["package_name"])
    project_profile = str(defaults["project_profile"])

    target_files = src.get("target_files") if isinstance(src.get("target_files"), list) else defaults["target_files"]
    source_files = src.get("source_files") if isinstance(src.get("source_files"), list) else defaults["source_files"]
    doc_files = src.get("doc_files") if isinstance(src.get("doc_files"), list) else defaults["doc_files"]
    workflow_files = src.get("workflow_files") if isinstance(src.get("workflow_files"), list) else defaults["workflow_files"]
    business_files = src.get("business_files") if isinstance(src.get("business_files"), list) else defaults["business_files"]
    business_capabilities = (
        src.get("business_capabilities")
        if isinstance(src.get("business_capabilities"), list)
        else defaults["business_capabilities"]
    )
    acceptance_files = src.get("acceptance_files") if isinstance(src.get("acceptance_files"), list) else defaults["acceptance_files"]
    reference_mode = src.get("reference_project_mode") if isinstance(src.get("reference_project_mode"), dict) else defaults["reference_project_mode"]
    reference_style = (
        src.get("reference_style_applied")
        if isinstance(src.get("reference_style_applied"), list)
        else defaults["reference_style_applied"]
    )

    normalized_target = sorted(set(_normalize_rel_list([str(x) for x in target_files])))
    return {
        "schema_version": "ctcp-project-output-contract-v1",
        "stage": "output_contract_freeze",
        "goal": goal_text,
        "project_id": project_id,
        "project_root": project_root,
        "project_type": project_type,
        "package_name": package_name,
        "project_profile": project_profile,
        "generation_mode": str(defaults["generation_mode"]),
        "execution_mode": str(defaults["execution_mode"]),
        "benchmark_case": str(defaults["benchmark_case"]),
        "delivery_shape": str(defaults["delivery_shape"]),
        "project_type_decision_source": str(defaults["project_type_decision_source"]),
        "shape_decision_source": str(defaults["shape_decision_source"]),
        "target_files": normalized_target,
        "source_files": _normalize_rel_list([str(x) for x in source_files]),
        "doc_files": _normalize_rel_list([str(x) for x in doc_files]),
        "workflow_files": _normalize_rel_list([str(x) for x in workflow_files]),
        "business_files": _normalize_rel_list([str(x) for x in business_files]),
        "business_capabilities": _normalize_rel_list([str(x) for x in business_capabilities]),
        "generated_files": [],
        "missing_files": list(normalized_target),
        "acceptance_files": _normalize_rel_list([str(x) for x in acceptance_files]),
        "startup_entrypoint": str(defaults["startup_entrypoint"]),
        "startup_readme": str(defaults["startup_readme"]),
        "reference_project_mode": reference_mode,
        "reference_style_applied": _normalize_rel_list([str(x) for x in reference_style]),
        "demo_required": bool(defaults["demo_required"]),
        "visual_evidence_required": bool(defaults["visual_evidence_required"]),
        "screenshot_required": bool(defaults["screenshot_required"]),
        "visual_evidence_status": str(defaults["visual_evidence_status"]),
        "benchmark_sample_applied": bool(defaults["benchmark_sample_applied"]),
        "decision_nodes": _normalize_rel_list([str(x) for x in defaults["decision_nodes"]]),
        "flow_nodes": _normalize_rel_list([str(x) for x in defaults["flow_nodes"]]),
    }


def _load_output_contract_lists(run_dir: Path, *, goal: str = "") -> dict[str, Any]:
    path = run_dir / "artifacts" / "output_contract_freeze.json"
    defaults = _default_project_file_lists(goal or run_dir.name, run_dir=run_dir)
    if not path.exists():
        return defaults
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return defaults
    if not isinstance(doc, dict):
        return defaults
    out = dict(defaults)
    for key in (
        "project_root",
        "project_id",
        "project_profile",
        "project_type",
        "package_name",
        "generation_mode",
        "execution_mode",
        "benchmark_case",
        "delivery_shape",
        "project_type_decision_source",
        "shape_decision_source",
        "startup_entrypoint",
        "startup_readme",
        "visual_evidence_status",
    ):
        value = str(doc.get(key, "")).strip()
        if value:
            out[key] = value.replace("\\", "/") if key in {"project_root", "startup_entrypoint", "startup_readme"} else value
    for key in (
        "target_files",
        "source_files",
        "doc_files",
        "workflow_files",
        "acceptance_files",
        "business_files",
        "business_capabilities",
        "reference_style_applied",
        "decision_nodes",
        "flow_nodes",
    ):
        value = doc.get(key)
        if isinstance(value, list):
            cleaned = _normalize_rel_list([str(x) for x in value])
            if cleaned:
                out[key] = cleaned
    for key in ("demo_required", "visual_evidence_required", "screenshot_required", "benchmark_sample_applied"):
        if key in doc:
            out[key] = bool(doc.get(key))
    mode = doc.get("reference_project_mode")
    if isinstance(mode, dict) and "enabled" in mode and "mode" in mode:
        out["reference_project_mode"] = mode
    return out


def _collect_run_output_refs(run_dir: Path) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for path in sorted(run_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.resolve().relative_to(run_dir.resolve()).as_posix()
        if rel.startswith("outbox/"):
            continue
        refs.append({"rel_path": rel, "size_bytes": int(path.stat().st_size)})
    return refs


def _runs_root_for(run_dir: Path) -> Path:
    if run_dir.parent.name.lower() == "ctcp":
        return run_dir.parent.parent
    return run_dir.parent


def _extract_run_dir_from_stdout(text: str) -> str:
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if line.startswith("[ctcp_orchestrate] run_dir="):
            return line.split("=", 1)[1].strip()
    return ""


def _collect_project_files(run_dir: Path, project_root: str) -> list[str]:
    root = (run_dir / project_root).resolve()
    if not root.exists():
        return []
    rows: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rows.append(path.resolve().relative_to(run_dir.resolve()).as_posix())
    return rows


def _run_pointcloud_scaffold(*, run_dir: Path, goal: str, project_root: str, profile: str) -> dict[str, Any]:
    out_dir = (run_dir / project_root).resolve()
    manifest = out_dir / "meta" / "manifest.json"
    if manifest.exists():
        return {
            "status": "pass",
            "result": "reused",
            "project_root": project_root,
            "out_dir": str(out_dir),
            "generated_files": _collect_project_files(run_dir, project_root),
            "scaffold_run_dir": "",
            "command": "",
            "rc": 0,
            "stdout_tail": "",
            "stderr_tail": "",
            "error": "",
        }

    out_dir.parent.mkdir(parents=True, exist_ok=True)
    project_type = "narrative_copilot" if profile == "narrative_copilot" else "generic_copilot"
    project_name = _project_slug(goal or run_dir.name, project_type)
    bootstrap_profile = "standard" if profile not in {"minimal"} else "minimal"
    cmd = [
        sys.executable,
        str(ORCH_SCRIPT),
        "scaffold-pointcloud",
        "--out",
        str(out_dir),
        "--name",
        project_name,
        "--profile",
        bootstrap_profile,
        "--source-mode",
        "template",
        "--force",
        "--runs-root",
        str(_runs_root_for(run_dir)),
        "--dialogue-script",
        str(POINTCLOUD_DIALOGUE_SCRIPT),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = str(proc.stdout or "")
    stderr = str(proc.stderr or "")
    generated = _collect_project_files(run_dir, project_root)
    scaffold_run_dir = _extract_run_dir_from_stdout(stdout)
    failed = int(proc.returncode) != 0 or not manifest.exists()
    return {
        "status": "blocked" if failed else "pass",
        "result": "failed" if failed else "generated",
        "project_root": project_root,
        "out_dir": str(out_dir),
        "generated_files": generated,
        "scaffold_run_dir": scaffold_run_dir,
        "command": " ".join(cmd),
        "rc": int(proc.returncode),
        "stdout_tail": "\n".join(stdout.splitlines()[-12:]),
        "stderr_tail": "\n".join(stderr.splitlines()[-12:]),
        "error": "" if not failed else ("scaffold-pointcloud generation failed"),
    }


def _load_context_pack(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path = run_dir / "artifacts" / "context_pack.json"
    if not path.exists():
        return {}, []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}, []
    if not isinstance(doc, dict):
        return {}, []
    files: list[dict[str, Any]] = []
    for item in doc.get("files", []):
        if not isinstance(item, dict):
            continue
        path_value = str(item.get("path", "")).strip().replace("\\", "/")
        if not path_value:
            continue
        files.append(
            {
                "path": path_value,
                "why": str(item.get("why", "")).strip(),
                "content": str(item.get("content", "")),
            }
        )
    return doc, files


def _context_consumption(goal: str, context_files: list[dict[str, Any]], *, decision: dict[str, Any]) -> dict[str, Any]:
    used_paths: list[str] = []
    influence_summary: list[str] = []
    path_map = {str(item.get("path", "")).strip().replace("\\", "/"): item for item in context_files}
    for path in sorted(path_map):
        content = str(path_map[path].get("content", ""))
        if path == "docs/41_low_capability_project_generation.md":
            used_paths.append(path)
            influence_summary.append("docs/41_low_capability_project_generation.md reinforced production/benchmark split and layered gate semantics")
        elif path == "docs/backend_interface_contract.md":
            used_paths.append(path)
            influence_summary.append("docs/backend_interface_contract.md reinforced manifest and deliver bridge fields")
        elif path == "workflow_registry/wf_project_generation_manifest/recipe.yaml":
            used_paths.append(path)
            influence_summary.append("workflow recipe preserved fixed stage ordering for output_contract/source_generation/deliver")
        elif path == "scripts/project_generation_gate.py":
            used_paths.append(path)
            influence_summary.append("project_generation_gate rules influenced structural/behavioral/result gate reporting")
        elif path == "scripts/project_manifest_bridge.py":
            used_paths.append(path)
            influence_summary.append("project_manifest_bridge shaped bridge-readable manifest fields")
        elif path.startswith("artifacts/frontend_uploads/") and _contains_any(content, GUI_KEYWORDS + WEB_KEYWORDS + TOOL_KEYWORDS + NARRATIVE_KEYWORDS):
            used_paths.append(path)
            influence_summary.append(f"{path} contributed user-context signals to type/shape resolution")
    if "context:" in str(decision.get("shape_decision_source", "")):
        influence_summary.append(f"context influenced delivery_shape via {decision.get('shape_decision_source', '')}")
    return {
        "consumed_context_pack": bool(influence_summary),
        "consumed_context_files": _normalize_rel_list(used_paths),
        "context_influence_summary": influence_summary,
        "reference_style_applied": ["repo_script_layout", "workflow_manifest_stage_chain", "bridge_readable_manifest"] if influence_summary else [],
    }


def _stage_report(
    *,
    stage: str,
    goal: str,
    project_root: str,
    required_files: list[str],
    generated_files: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_required = _normalize_rel_list(required_files)
    normalized_generated = _normalize_rel_list(generated_files)
    missing = sorted(set(normalized_required) - set(normalized_generated))
    out: dict[str, Any] = {
        "schema_version": "ctcp-project-stage-report-v1",
        "stage": stage,
        "goal": goal,
        "project_root": project_root,
        "required_files": normalized_required,
        "generated_files": normalized_generated,
        "missing_files": missing,
        "status": "pass" if not missing else "blocked",
    }
    if isinstance(extra, dict):
        out.update(extra)
    return out


def normalize_source_generation(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    project_root = str(lists.get("project_root", "")).strip() or f"project_output/{_project_slug(goal_text, str(lists.get('project_type', 'generic_copilot')))}"
    project_type = str(lists.get("project_type", "")).strip() or "generic_copilot"
    package_name = str(lists.get("package_name", "")).strip() or "project_copilot"
    profile = str(lists.get("project_profile", "business_copilot")).strip().lower() or "business_copilot"
    context_doc, context_files = _load_context_pack(run_dir)
    decision = decide_project_generation(goal_text, run_dir=run_dir, context_files=context_files)
    context_usage = _context_consumption(goal_text, context_files, decision=decision)
    consumed_context = bool(context_usage.get("consumed_context_pack", False))
    consumed_files = list(context_usage.get("consumed_context_files", []))
    entry_script = str(lists.get("startup_entrypoint", "")).strip() or f"{project_root}/scripts/run_project_cli.py"

    if not context_doc or not context_files:
        report = _stage_report(
            stage="source_generation",
            goal=goal_text,
            project_root=project_root,
            required_files=list(lists.get("source_files", [])),
            generated_files=_collect_project_files(run_dir, project_root),
            extra=build_missing_context_extra(
                lists=lists,
                project_id=str(lists.get("project_id", "")),
                project_type=project_type,
                package_name=package_name,
                entry_script=entry_script,
            ),
        )
        report["status"] = "blocked"
        return report

    scaffold = _run_pointcloud_scaffold(run_dir=run_dir, goal=goal_text, project_root=project_root, profile=profile)
    generated_business_files = materialize_business_files(run_dir, goal_text, lists, consumed_files)
    generated_files = _collect_project_files(run_dir, project_root)
    business_expected = list(lists.get("business_files", []))
    business_generated = sorted(set(business_expected) & set(generated_files))
    business_missing = sorted(set(business_expected) - set(generated_files))
    behavior_probe, export_probe, gate_layers = build_runtime_checks(
        run_dir=run_dir,
        project_root=project_root,
        package_name=package_name,
        entry_script=entry_script,
        delivery_shape=str(lists.get("delivery_shape", CLI_SHAPE)),
        execution_mode=str(lists.get("execution_mode", PRODUCTION_MODE)),
        benchmark_sample_applied=bool(lists.get("benchmark_sample_applied", False)),
        benchmark_case=str(lists.get("benchmark_case", "")),
        visual_evidence_status=str(lists.get("visual_evidence_status", "not_requested")),
        generated_files=generated_files,
        source_files=list(lists.get("source_files", [])),
        business_missing=business_missing,
        generated_business_files=generated_business_files,
        scaffold_status=str(scaffold.get("status", "")).strip().lower(),
        consumed_context=consumed_context,
    )

    report = _stage_report(
        stage="source_generation",
        goal=goal_text,
        project_root=project_root,
        required_files=list(lists.get("source_files", [])),
        generated_files=generated_files,
        extra=build_success_extra(
            lists=lists,
            project_id=str(lists.get("project_id", "")),
            project_type=project_type,
            package_name=package_name,
            entry_script=entry_script,
            consumed_context=consumed_context,
            consumed_files=consumed_files,
            context_influence_summary=list(context_usage.get("context_influence_summary", [])),
            business_generated=business_generated,
            business_missing=business_missing,
            reference_style_applied=context_usage.get("reference_style_applied", []),
            gate_layers=gate_layers,
            behavior_probe=behavior_probe,
            export_probe=export_probe,
            scaffold=scaffold,
        ),
    )
    if (
        not gate_layers["structural"]["passed"]
        or not gate_layers["behavioral"]["passed"]
        or not gate_layers["result"]["passed"]
        or str(scaffold.get("status", "")).strip().lower() != "pass"
    ):
        report["status"] = "blocked"
    return report


def normalize_docs_generation(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    project_root = str(lists.get("project_root", "")).strip() or f"project_output/{_project_slug(goal_text)}"
    generated = _collect_project_files(run_dir, project_root)
    return _stage_report(
        stage="docs_generation",
        goal=goal_text,
        project_root=project_root,
        required_files=list(lists.get("doc_files", [])),
        generated_files=generated,
        extra={
            "project_id": str(lists.get("project_id", "")),
            "project_type": str(lists.get("project_type", "")),
        },
    )


def normalize_workflow_generation(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    project_root = str(lists.get("project_root", "")).strip() or f"project_output/{_project_slug(goal_text)}"
    generated = _collect_project_files(run_dir, project_root)
    return _stage_report(
        stage="workflow_generation",
        goal=goal_text,
        project_root=project_root,
        required_files=list(lists.get("workflow_files", [])),
        generated_files=generated,
        extra={
            "project_id": str(lists.get("project_id", "")),
            "project_type": str(lists.get("project_type", "")),
        },
    )


def normalize_project_manifest(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    lists = _load_output_contract_lists(run_dir, goal=goal_text)
    output_refs = _collect_run_output_refs(run_dir)
    project_root = str(lists.get("project_root", "")).strip()
    project_files = _collect_project_files(run_dir, project_root)
    generated_files = (
        _normalize_rel_list([str(x) for x in src.get("generated_files", [])])
        if isinstance(src.get("generated_files"), list)
        else sorted(
            set(
                project_files
                + [
                    "artifacts/output_contract_freeze.json",
                    "artifacts/source_generation_report.json",
                    "artifacts/docs_generation_report.json",
                    "artifacts/workflow_generation_report.json",
                    "artifacts/project_manifest.json",
                    "artifacts/deliverable_index.json",
                ]
            )
        )
    )
    target_files = list(lists.get("target_files", []))
    missing_files = (
        _normalize_rel_list([str(x) for x in src.get("missing_files", [])])
        if isinstance(src.get("missing_files"), list)
        else sorted(set(target_files) - set(project_files))
    )
    run_id = run_dir.name
    source_files = list(lists.get("source_files", []))
    doc_files = list(lists.get("doc_files", []))
    workflow_files = list(lists.get("workflow_files", []))
    business_files = list(lists.get("business_files", []))
    startup_entrypoint = next((p for p in source_files if p.endswith("/scripts/run_narrative_copilot.py")), "")
    if not startup_entrypoint:
        startup_entrypoint = next((p for p in source_files if p.endswith("/scripts/run_project_copilot.py")), source_files[0] if source_files else "")
    startup_readme = next((p for p in doc_files if p.endswith("/README.md")), doc_files[0] if doc_files else "")
    source_stage_doc: dict[str, Any] = {}
    source_stage_path = run_dir / "artifacts" / "source_generation_report.json"
    if source_stage_path.exists():
        try:
            raw = json.loads(source_stage_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                source_stage_doc = raw
        except Exception:
            source_stage_doc = {}

    return {
        "schema_version": "ctcp-project-manifest-v1",
        "stage": "artifact_manifest_build",
        "goal": goal_text,
        "run_id": str(src.get("run_id", "")).strip() or run_id,
        "project_id": str(src.get("project_id", "")).strip() or str(lists.get("project_id", "")).strip() or _slug(goal_text or run_id),
        "project_root": project_root,
        "project_type": str(lists.get("project_type", "")),
        "project_profile": str(lists.get("project_profile", "")),
        "generation_mode": str(source_stage_doc.get("generation_mode", "")).strip() or str(lists.get("generation_mode", "")),
        "execution_mode": str(source_stage_doc.get("execution_mode", "")).strip() or str(lists.get("execution_mode", PRODUCTION_MODE)),
        "benchmark_case": str(source_stage_doc.get("benchmark_case", "")).strip() or str(lists.get("benchmark_case", "")),
        "delivery_shape": str(source_stage_doc.get("delivery_shape", "")).strip() or str(lists.get("delivery_shape", CLI_SHAPE)),
        "project_type_decision_source": str(source_stage_doc.get("project_type_decision_source", "")).strip()
        or str(lists.get("project_type_decision_source", "")),
        "shape_decision_source": str(source_stage_doc.get("shape_decision_source", "")).strip()
        or str(lists.get("shape_decision_source", "")),
        "source_files": source_files,
        "doc_files": doc_files,
        "workflow_files": workflow_files,
        "business_files_generated": _normalize_rel_list([str(x) for x in source_stage_doc.get("business_files_generated", [])]) if isinstance(source_stage_doc.get("business_files_generated"), list) else sorted(set(business_files) & set(project_files)),
        "business_files_missing": _normalize_rel_list([str(x) for x in source_stage_doc.get("business_files_missing", [])]) if isinstance(source_stage_doc.get("business_files_missing"), list) else sorted(set(business_files) - set(project_files)),
        "generated_files": generated_files,
        "missing_files": missing_files,
        "acceptance_files": list(lists.get("acceptance_files", [])),
        "startup_entrypoint": str(source_stage_doc.get("entrypoint", "")).strip() or startup_entrypoint,
        "startup_readme": str(source_stage_doc.get("startup_readme", "")).strip() or startup_readme,
        "scaffold_run_dir": str(source_stage_doc.get("scaffold", {}).get("scaffold_run_dir", "")).strip(),
        "reference_project_mode": source_stage_doc.get("reference_project_mode") if isinstance(source_stage_doc.get("reference_project_mode"), dict) else lists.get("reference_project_mode", {"enabled": False, "mode": "structure_workflow_docs"}),
        "reference_style_applied": _normalize_rel_list([str(x) for x in source_stage_doc.get("reference_style_applied", [])]) if isinstance(source_stage_doc.get("reference_style_applied"), list) else list(lists.get("reference_style_applied", [])),
        "business_codegen_used": bool(source_stage_doc.get("business_codegen_used", False)),
        "consumed_context_pack": bool(source_stage_doc.get("consumed_context_pack", False)),
        "consumed_context_files": _normalize_rel_list([str(x) for x in source_stage_doc.get("consumed_context_files", [])]) if isinstance(source_stage_doc.get("consumed_context_files"), list) else [],
        "context_influence_summary": _normalize_rel_list([str(x) for x in source_stage_doc.get("context_influence_summary", [])]) if isinstance(source_stage_doc.get("context_influence_summary"), list) else [],
        "demo_required": bool(source_stage_doc.get("demo_required", lists.get("demo_required", False))),
        "visual_evidence_required": bool(source_stage_doc.get("visual_evidence_required", lists.get("visual_evidence_required", False))),
        "screenshot_required": bool(source_stage_doc.get("screenshot_required", lists.get("screenshot_required", False))),
        "visual_evidence_status": str(source_stage_doc.get("visual_evidence_status", "")).strip() or str(lists.get("visual_evidence_status", "not_requested")),
        "benchmark_sample_applied": bool(source_stage_doc.get("benchmark_sample_applied", lists.get("benchmark_sample_applied", False))),
        "decision_nodes": _normalize_rel_list([str(x) for x in source_stage_doc.get("decision_nodes", lists.get("decision_nodes", []))]),
        "flow_nodes": _normalize_rel_list([str(x) for x in source_stage_doc.get("flow_nodes", lists.get("flow_nodes", []))]),
        "gate_layers": source_stage_doc.get("gate_layers") if isinstance(source_stage_doc.get("gate_layers"), dict) else {},
        "behavioral_checks": source_stage_doc.get("behavioral_checks") if isinstance(source_stage_doc.get("behavioral_checks"), dict) else {},
        "artifacts": output_refs,
    }


def normalize_deliverable_index(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    manifest_path = run_dir / "artifacts" / "project_manifest.json"
    manifest_doc: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                manifest_doc = raw
        except Exception:
            manifest_doc = {}
    deliverables: list[str] = []
    for field in ("business_files_generated", "acceptance_files", "source_files", "doc_files", "workflow_files"):
        value = manifest_doc.get(field)
        if isinstance(value, list):
            deliverables.extend(str(row).strip() for row in value if str(row).strip())
    deliverables.extend(
        [
            "artifacts/output_contract_freeze.json",
            "artifacts/source_generation_report.json",
            "artifacts/project_manifest.json",
            "artifacts/deliverable_index.json",
        ]
    )
    return {
        "schema_version": "ctcp-deliverable-index-v1",
        "stage": "deliver",
        "goal": str(src.get("goal", "")).strip() or goal.strip(),
        "run_id": str(src.get("run_id", "")).strip() or run_dir.name,
        "project_id": str(src.get("project_id", "")).strip() or str(manifest_doc.get("project_id", "")).strip() or _slug(goal or run_dir.name),
        "project_manifest_path": "artifacts/project_manifest.json",
        "project_root": str(manifest_doc.get("project_root", "")).strip(),
        "project_type": str(manifest_doc.get("project_type", "")).strip(),
        "generation_mode": str(manifest_doc.get("generation_mode", "")).strip(),
        "execution_mode": str(manifest_doc.get("execution_mode", PRODUCTION_MODE)).strip(),
        "benchmark_case": str(manifest_doc.get("benchmark_case", "")).strip(),
        "delivery_shape": str(manifest_doc.get("delivery_shape", CLI_SHAPE)).strip(),
        "startup_entrypoint": str(manifest_doc.get("startup_entrypoint", "")).strip(),
        "startup_readme": str(manifest_doc.get("startup_readme", "")).strip(),
        "demo_required": bool(manifest_doc.get("demo_required", False)),
        "visual_evidence_required": bool(manifest_doc.get("visual_evidence_required", False)),
        "screenshot_required": bool(manifest_doc.get("screenshot_required", False)),
        "visual_evidence_status": str(manifest_doc.get("visual_evidence_status", "not_requested")).strip(),
        "business_deliverables": _normalize_rel_list([str(x) for x in manifest_doc.get("business_files_generated", [])]) if isinstance(manifest_doc.get("business_files_generated"), list) else [],
        "deliverables": sorted(set(deliverables)),
        "delivery_note": str(src.get("delivery_note", "")).strip() or "deliver artifacts are indexed for bridge consumption and mode-aware verify handoff",
    }
