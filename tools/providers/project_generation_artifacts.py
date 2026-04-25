from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any

from tools.providers.project_generation_business_templates import materialize_business_files
from tools.providers.project_generation_decisions import (
    BENCHMARK_MODE,
    CLI_SHAPE,
    FLOW_NODES,
    PRODUCTION_MODE,
    NARRATIVE_KEYWORDS,
    STRONG_DECISION_NODES,
    TEAM_PM_KEYWORDS,
    enrich_project_spec,
    contains_any as _contains_any,
    decide_project_generation,
    default_package_name,
    default_project_id,
    is_indie_studio_hub_signal,
    is_high_quality_extended_signal,
    resolve_capability_plan,
    shape_contract,
)
from tools.providers.project_generation_source_stage import (
    normalize_project_queue_source_generation_stage,
    normalize_source_generation_stage,
)
from tools.providers.project_generation_validation import (
    pipeline_contract as _pipeline_contract,
    resolve_project_intent as _resolve_project_intent,
    resolve_project_spec as _resolve_project_spec,
)
from tools.providers.project_generation_runtime_support import (
    _collect_project_files,
    _collect_run_output_refs,
    _context_consumption,
    _load_context_pack,
    _stage_report,
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
    "platform",
    "dashboard",
    "portal",
    "service",
    "workspace",
    "task management",
    "task collaboration",
    "team task",
    "local-first",
    "plane-lite",
    "focalboard-lite",
    "生成",
    "项目",
    "工具",
    "助手",
    "服务",
    "应用",
    "平台",
    "工作台",
    "管理平台",
    "协作平台",
    "任务协作",
    "团队任务",
    "任务管理",
    "看板",
    "本地部署",
    "粗目标",
    "不要细规格",
    "重跑生成测试",
    "重跑测试",
    "域提升",
    "完整产品域",
    "资产库",
    "bug tracker",
    "build / release",
    "文档中心",
)
PROJECT_GENERATION_BINDING_HINTS = (
    "绑定任务",
    "绑定一个新任务",
    "绑定新任务",
    "新任务",
    "bind a new task",
    "bind this task",
)
PROJECT_GENERATION_RERUN_HINTS = (
    "重跑生成测试",
    "重跑测试",
    "rerun generation test",
    "rerun the generation test",
    "rerun",
)
PROJECT_GENERATION_DOMAIN_LIFT_HINTS = (
    "domain lift",
    "domain-lift",
    "域提升",
    "coverage gate",
    "user_acceptance_status",
    "internal_runtime_status",
)


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", (text or "").strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "goal"


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _load_frontend_request_doc(run_dir: Path | None) -> dict[str, Any]:
    if run_dir is None:
        return {}
    return _read_json_file(run_dir / "artifacts" / "frontend_request.json")


def _normalize_project_queue_items(rows: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, raw in enumerate(rows, start=1):
        goal_text = ""
        name_text = ""
        if isinstance(raw, str):
            goal_text = str(raw).strip()
        elif isinstance(raw, dict):
            goal_text = (
                str(raw.get("goal", "")).strip()
                or str(raw.get("rough_goal", "")).strip()
                or str(raw.get("project_goal", "")).strip()
                or str(raw.get("brief", "")).strip()
                or str(raw.get("request", "")).strip()
            )
            name_text = (
                str(raw.get("name", "")).strip()
                or str(raw.get("title", "")).strip()
                or str(raw.get("project_name", "")).strip()
            )
        if not goal_text:
            continue
        dedupe_key = goal_text.lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        slug = _slug(name_text or goal_text)
        normalized.append(
            {
                "project_index": index,
                "project_name": name_text or f"Project {index:02d}",
                "rough_goal": goal_text,
                "slug": slug,
            }
        )
    return normalized


def _parse_project_queue_from_goal(goal: str) -> list[dict[str, Any]]:
    rows: list[str] = []
    for line in str(goal or "").splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        if cleaned and len(cleaned) >= 12:
            rows.append(cleaned)
    return _normalize_project_queue_items(rows) if len(rows) >= 2 else []


def _extract_project_queue(
    doc: dict[str, Any] | None,
    *,
    goal: str,
    run_dir: Path | None = None,
    include_output_contract: bool = False,
) -> list[dict[str, Any]]:
    src = doc if isinstance(doc, dict) else {}
    candidates: list[Any] = []
    for payload in (src, _load_frontend_request_doc(run_dir)):
        for key in ("project_queue", "projects", "project_goals"):
            value = payload.get(key)
            if isinstance(value, list):
                candidates.extend(value)
                break
    if include_output_contract and run_dir is not None:
        contract_doc = _read_json_file(run_dir / "artifacts" / "output_contract_freeze.json")
        for key in ("project_queue", "projects", "project_goals"):
            value = contract_doc.get(key)
            if isinstance(value, list):
                candidates.extend(value)
                break
    normalized = _normalize_project_queue_items(candidates)
    if normalized:
        return normalized
    return _parse_project_queue_from_goal(goal)


def _portfolio_output_contract(goal_text: str, *, src: dict[str, Any], run_dir: Path | None, project_queue: list[dict[str, Any]]) -> dict[str, Any]:
    project_id = default_project_id(f"portfolio-{_slug(goal_text)[:48]}", "generic_copilot", PRODUCTION_MODE)
    package_name = default_package_name(project_id, "generic_copilot", PRODUCTION_MODE, "")
    project_root = f"project_output/{project_id}"
    defaults = _production_project_defaults("generic_copilot", "cli_toolkit", package_name, CLI_SHAPE)
    decision = {
        "execution_mode": PRODUCTION_MODE,
        "benchmark_case": "",
        "delivery_shape": CLI_SHAPE,
        "project_domain_decision_source": "project_queue_request",
        "scaffold_family_decision_source": "project_queue_request",
        "project_type_decision_source": "project_queue_request",
        "project_archetype_decision_source": "project_queue_request",
        "shape_decision_source": "project_queue_request",
        "demo_required": True,
        "visual_evidence_required": False,
        "screenshot_required": False,
        "visual_evidence_status": "not_requested",
        "benchmark_sample_applied": False,
        "build_profile": "high_quality_extended",
        "product_depth": "extended",
        "required_pages": 0,
        "required_screenshots": 0,
        "require_feature_matrix": False,
        "require_page_map": False,
        "require_data_model_summary": False,
        "require_search": False,
        "require_import_or_export": "at_least_one",
        "require_dashboard_or_project_overview": False,
        "decision_nodes": list(STRONG_DECISION_NODES),
        "flow_nodes": list(FLOW_NODES),
    }
    lists = _assemble_project_file_lists(
        project_root=project_root,
        project_id=project_id,
        project_domain="generic_software_project",
        scaffold_family="generic_copilot",
        project_type="generic_copilot",
        package_name=package_name,
        project_archetype="cli_toolkit",
        decision=decision,
        defaults=defaults,
    )
    summary_json = f"{project_root}/portfolio_run/portfolio_summary.json"
    summary_md = f"{project_root}/portfolio_run/portfolio_summary.md"
    lists["workflow_files"] = _normalize_rel_list(list(lists.get("workflow_files", [])) + [summary_json])
    lists["doc_files"] = _normalize_rel_list(list(lists.get("doc_files", [])) + [summary_md])
    lists["target_files"] = sorted(set(list(lists.get("target_files", [])) + [summary_json, summary_md]))
    lists["acceptance_files"] = _normalize_rel_list(list(lists.get("acceptance_files", [])) + [summary_json, summary_md])

    project_intent = {
        "goal_summary": f"Process a portfolio queue of {len(project_queue)} rough-goal projects into auditable delivery bundles",
        "target_user": "operator who wants multiple CTCP-generated projects processed end-to-end in one serial run",
        "problem_to_solve": "the user wants queued rough-goal projects to advance through product definition, build, verify, delivery, and portfolio summarization without pausing for detailed specs",
        "mvp_scope": [
            "recognize a queued project request",
            "process queued projects serially with independent artifacts",
            "export portfolio summary plus bundle paths",
        ],
        "required_inputs": ["rough-goal project queue"],
        "required_outputs": ["portfolio_summary.json", "portfolio_summary.md", "per-project bundles", "per-project evidence bundles"],
        "hard_constraints": [
            "serial execution only",
            "one clarification round max per project",
            "do not stop on non-hard failures; emit strongest deliverable",
        ],
        "assumptions": [
            "queue projects default to local-first runnable MVPs unless a harder constraint is discoverable locally",
            "portfolio root stays as one top-level runnable project so existing manifest/deliver gates remain intact",
            "per-project verification may degrade to strongest auditable local result when a subproject cannot fully pass",
        ],
        "open_questions": [
            "Should a queued project prefer local single-user operation or lightweight team sharing?",
            "Should a queued project freeze at MVP depth or a thicker first release?",
            "Which domain surface is most urgent for each queued project?",
        ],
        "acceptance_criteria": [
            "each queued project emits independent design/build/verify/delivery artifacts",
            "portfolio summary records bundle paths and dual-layer statuses for every queued project",
            "top-level project root remains runnable and deliverable",
        ],
    }
    project_spec = {
        "schema_version": "ctcp-project-spec-v2",
        "goal_summary": project_intent["goal_summary"],
        "target_user": project_intent["target_user"],
        "problem_to_solve": project_intent["problem_to_solve"],
        "project_domain": "generic_software_project",
        "scaffold_family": "generic_copilot",
        "project_type": "generic_copilot",
        "project_archetype": "cli_toolkit",
        "delivery_shape": CLI_SHAPE,
        "mvp_scope": list(project_intent["mvp_scope"]),
        "required_inputs": list(project_intent["required_inputs"]),
        "required_outputs": list(project_intent["required_outputs"]),
        "hard_constraints": list(project_intent["hard_constraints"]),
        "assumptions": list(project_intent["assumptions"]),
        "open_questions": list(project_intent["open_questions"]),
        "acceptance_criteria": list(project_intent["acceptance_criteria"]),
        "core_modules": [
            "queue_intake",
            "portfolio_runner",
            "serial_project_executor",
            "portfolio_summary_exporter",
        ],
        "required_pages_or_views": ["cli_entry", "portfolio_status_report"],
        "data_models": ["portfolio_request", "queued_project", "project_verdict", "bundle_manifest"],
        "key_interactions": [
            "parse_queue",
            "freeze_project_scope",
            "process_next_project",
            "capture_delivery_paths",
            "export_portfolio_summary",
        ],
        "sample_content_plan": {"queue_mode": "serial", "project_count": len(project_queue)},
        "export_targets": ["portfolio_summary.json", "portfolio_summary.md"],
        "delivery_requirements": ["final_project_bundle.zip", "intermediate_evidence_bundle.zip", "README"],
        "explicit_non_goals": [
            "parallel multi-project execution",
            "waiting for the user to define page maps or data models manually",
            "generic placeholder-only queue output",
        ],
    }
    capability_plan = resolve_capability_plan(
        project_domain="generic_software_project",
        scaffold_family="generic_copilot",
        project_type="generic_copilot",
        project_archetype="cli_toolkit",
        project_spec=project_spec,
        materialize_capabilities=[str(item) for item in defaults["capabilities"]],
    )
    sample_generation_artifacts = [
        f"artifacts/sample_generation/{step}.json"
        for step in capability_plan.get("sample_generation_steps", [])
        if str(step).strip()
    ]
    pipeline_contract = _pipeline_contract(
        project_root=project_root,
        startup_entrypoint=str(lists["startup_entrypoint"]),
        startup_readme=str(lists["startup_readme"]),
        business_files=_normalize_rel_list([str(x) for x in lists.get("business_files", [])]),
        acceptance_files=_normalize_rel_list([str(x) for x in lists.get("acceptance_files", [])]),
    )
    return {
        "schema_version": "ctcp-project-output-contract-v1",
        "stage": "output_contract_freeze",
        "goal": goal_text,
        "project_intent": project_intent,
        "project_spec": project_spec,
        "project_spec_path": "artifacts/project_spec.json",
        "capability_plan": capability_plan,
        "capability_plan_path": "artifacts/capability_plan.json",
        "sample_generation_plan": dict(project_spec.get("sample_content_plan", {})),
        "sample_generation_artifacts": sample_generation_artifacts,
        "generation_quality_report_path": "artifacts/generation_quality_report.json",
        "pipeline_contract": pipeline_contract,
        "project_id": project_id,
        "project_root": project_root,
        "project_domain": "generic_software_project",
        "scaffold_family": "generic_copilot",
        "project_type": "generic_copilot",
        "project_archetype": "cli_toolkit",
        "package_name": package_name,
        "project_profile": str(lists["project_profile"]),
        "generation_mode": str(lists["generation_mode"]),
        "execution_mode": PRODUCTION_MODE,
        "benchmark_case": "",
        "delivery_shape": CLI_SHAPE,
        "project_domain_decision_source": "project_queue_request",
        "scaffold_family_decision_source": "project_queue_request",
        "project_type_decision_source": "project_queue_request",
        "project_archetype_decision_source": "project_queue_request",
        "shape_decision_source": "project_queue_request",
        "target_files": list(lists["target_files"]),
        "source_files": list(lists["source_files"]),
        "doc_files": list(lists["doc_files"]),
        "workflow_files": list(lists["workflow_files"]),
        "business_files": list(lists["business_files"]),
        "business_capabilities": _normalize_rel_list([str(x) for x in capability_plan.get("required_bundles", [])]),
        "materialize_capabilities": _normalize_rel_list([str(x) for x in capability_plan.get("materialize_bundles", [])]),
        "generated_files": [],
        "missing_files": list(lists["target_files"]),
        "acceptance_files": list(lists["acceptance_files"]),
        "startup_entrypoint": str(lists["startup_entrypoint"]),
        "startup_readme": str(lists["startup_readme"]),
        "reference_project_mode": lists.get("reference_project_mode", {"enabled": True, "mode": "structure_workflow_docs"}),
        "reference_style_applied": list(lists.get("reference_style_applied", [])),
        "demo_required": True,
        "visual_evidence_required": False,
        "screenshot_required": False,
        "visual_evidence_status": "not_requested",
        "benchmark_sample_applied": False,
        "build_profile": "high_quality_extended",
        "product_depth": "extended",
        "required_pages": 0,
        "required_screenshots": 0,
        "require_feature_matrix": False,
        "require_page_map": False,
        "require_data_model_summary": False,
        "require_search": False,
        "require_import_or_export": "at_least_one",
        "require_dashboard_or_project_overview": False,
        "decision_nodes": list(STRONG_DECISION_NODES),
        "flow_nodes": list(FLOW_NODES),
        "portfolio_mode": True,
        "project_queue": project_queue,
        "portfolio_summary_json_path": summary_json,
        "portfolio_summary_md_path": summary_md,
    }


def is_project_generation_goal(goal: str) -> bool:
    text = str(goal or "")
    low = text.lower()
    binding = any(token in text or token in low for token in PROJECT_GENERATION_BINDING_HINTS)
    rerun = any(token in text or token in low for token in PROJECT_GENERATION_RERUN_HINTS)
    domain_lift = any(token in text or token in low for token in PROJECT_GENERATION_DOMAIN_LIFT_HINTS)
    if binding and (rerun or domain_lift):
        return True
    return _contains_any(text, NARRATIVE_KEYWORDS + PROJECT_GENERATION_KEYWORDS)


def build_default_context_request(goal: str) -> dict[str, Any]:
    if not is_project_generation_goal(goal):
        return {
            "needs": [{"path": "README.md", "mode": "snippets", "line_ranges": [[1, 80]]}],
            "budget": {"max_files": 6, "max_total_bytes": 48000},
            "reason": "chair file request for downstream context pack",
        }

    return {
        "needs": [
            {"path": "AGENTS.md", "mode": "snippets", "line_ranges": [[1, 140]]},
            {"path": "README.md", "mode": "snippets", "line_ranges": [[1, 120]]},
            {"path": "docs/01_north_star.md", "mode": "snippets", "line_ranges": [[1, 200]]},
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
        "budget": {"max_files": 20, "max_total_bytes": 250000},
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


def _build_final_project_bundle(run_dir: Path, project_root: str) -> str:
    rel = "artifacts/final_project_bundle.zip"
    root_text = str(project_root or "").strip().replace("\\", "/").strip("/")
    if not root_text:
        return ""
    root_path = (run_dir / root_text).resolve()
    run_root = run_dir.resolve()
    try:
        root_path.relative_to(run_root)
    except ValueError:
        return ""
    if not root_path.exists() or not root_path.is_dir():
        return ""
    out_path = run_dir / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(root_path.rglob("*")):
            if not item.is_file():
                continue
            zf.write(item, item.relative_to(root_path).as_posix())
    return rel if out_path.exists() else ""


def build_intermediate_evidence_bundle(run_dir: Path) -> str:
    rel = "artifacts/intermediate_evidence_bundle.zip"
    out_path = run_dir / rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    requested = [
        "artifacts/find_result.json",
        "artifacts/frontend_request.json",
        "artifacts/project_intent.json",
        "artifacts/project_spec.json",
        "artifacts/output_contract_freeze.json",
        "artifacts/capability_plan.json",
        "artifacts/source_generation_report.json",
        "artifacts/generation_quality_report.json",
        "artifacts/verify_report.json",
        "artifacts/project_manifest.json",
        "artifacts/deliverable_index.json",
        "artifacts/support_public_delivery.json",
        "artifacts/extended_coverage_ledger.json",
        "artifacts/provider_ledger.jsonl",
        "artifacts/provider_ledger_summary.json",
        "api_calls.jsonl",
        "support_api_calls.jsonl",
        "TRACE.md",
        "events.jsonl",
        "step_meta.jsonl",
        "artifacts/support_frontend_turns.jsonl",
    ]
    prefixes = [
        "reviews/",
        "artifacts/reviews/",
        "artifacts/acceptance/",
        "artifacts/delivery_replay/",
        "artifacts/screenshots/",
        "project_output/",
    ]
    missing: list[str] = []
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        seen: set[str] = set()
        for rel_path in requested:
            path = (run_dir / rel_path).resolve()
            if path.exists() and path.is_file():
                zf.write(path, rel_path)
                seen.add(rel_path)
            else:
                missing.append(rel_path)
        for prefix in prefixes:
            root = (run_dir / prefix).resolve()
            if not root.exists():
                missing.append(prefix)
                continue
            for item in sorted(root.rglob("*")):
                if not item.is_file():
                    continue
                rel_item = item.relative_to(run_dir.resolve()).as_posix()
                if rel_item == rel or rel_item in seen:
                    continue
                zf.write(item, rel_item)
                seen.add(rel_item)
        manifest = {
            "schema_version": "ctcp-intermediate-evidence-bundle-v1",
            "bundle_path": rel,
            "included_count": len(seen),
            "missing_expected_paths": missing,
            "evidence_classes": [
                "routing",
                "project_spec",
                "output_contract_freeze",
                "reviews",
                "source_generation_report",
                "verify_report",
                "delivery_manifest",
                "api_calls",
                "transcript",
                "TRACE",
                "events",
                "acceptance_ledger",
            ],
        }
        zf.writestr("EVIDENCE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return rel if out_path.exists() else ""


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


def _narrative_production_defaults(package_name: str) -> dict[str, Any]:
    return {
        "source_rel": [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/editor/__init__.py",
            f"src/{package_name}/editor/actions.py",
            f"src/{package_name}/editor/workspace.py",
            f"src/{package_name}/story/__init__.py",
            f"src/{package_name}/story/outline.py",
            f"src/{package_name}/story/scene_graph.py",
            f"src/{package_name}/cast/__init__.py",
            f"src/{package_name}/cast/schema.py",
            f"src/{package_name}/assets/__init__.py",
            f"src/{package_name}/assets/catalog.py",
            f"src/{package_name}/pipeline/__init__.py",
            f"src/{package_name}/pipeline/prompt_pipeline.py",
            f"src/{package_name}/exporters/__init__.py",
            f"src/{package_name}/exporters/deliver.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
            "sample_data/example_project.json",
            "sample_data/source_map.json",
            "sample_data/pipeline/theme_brief.json",
            "sample_data/pipeline/cast_cards.json",
            "sample_data/pipeline/chapter_plan.json",
            "sample_data/pipeline/scene_graph.json",
            "sample_data/pipeline/choice_map.json",
            "sample_data/pipeline/asset_placeholders.json",
        ],
        "business_rel": [
            f"src/{package_name}/seed.py",
            f"src/{package_name}/editor/actions.py",
            f"src/{package_name}/editor/workspace.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/story/outline.py",
            f"src/{package_name}/story/scene_graph.py",
            f"src/{package_name}/cast/schema.py",
            f"src/{package_name}/assets/catalog.py",
            f"src/{package_name}/pipeline/prompt_pipeline.py",
            f"src/{package_name}/exporters/deliver.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
            "sample_data/example_project.json",
            "sample_data/source_map.json",
            "sample_data/pipeline/theme_brief.json",
            "sample_data/pipeline/cast_cards.json",
            "sample_data/pipeline/chapter_plan.json",
            "sample_data/pipeline/scene_graph.json",
            "sample_data/pipeline/choice_map.json",
            "sample_data/pipeline/asset_placeholders.json",
        ],
        "capabilities": [
            "editor_core",
            "scene_branching",
            "character_asset_management",
            "sample_content_generation",
            "preview_export",
            "delivery_ready",
        ],
        "project_profile": "narrative_gui_editor",
        "generation_mode": "production_narrative_editor_deliverable_first",
    }


def _web_service_defaults(package_name: str) -> dict[str, Any]:
    return {
        "source_rel": [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/service_contract.py",
            f"src/{package_name}/app.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "business_rel": [
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/service_contract.py",
            f"src/{package_name}/app.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "capabilities": [
            "service_contract",
            "transport_surface",
            "sample_exchange",
            "delivery_ready",
        ],
        "project_profile": "web_service_copilot",
        "generation_mode": "production_web_service_deliverable_first",
    }


def _team_task_pm_defaults(package_name: str) -> dict[str, Any]:
    return {
        "source_rel": [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/workspace.py",
            f"src/{package_name}/tasks.py",
            f"src/{package_name}/board.py",
            f"src/{package_name}/filters.py",
            f"src/{package_name}/activity.py",
            f"src/{package_name}/app.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "business_rel": [
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/workspace.py",
            f"src/{package_name}/tasks.py",
            f"src/{package_name}/board.py",
            f"src/{package_name}/filters.py",
            f"src/{package_name}/activity.py",
            f"src/{package_name}/app.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "capabilities": [
            "auth_workspace",
            "project_board",
            "task_crud_detail",
            "filters_activity",
            "preview_export",
            "delivery_ready",
        ],
        "project_profile": "team_task_pm",
        "generation_mode": "production_team_task_pm_deliverable_first",
    }


def _data_pipeline_defaults(package_name: str) -> dict[str, Any]:
    return {
        "source_rel": [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/transforms.py",
            f"src/{package_name}/pipeline.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "business_rel": [
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/transforms.py",
            f"src/{package_name}/pipeline.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "capabilities": [
            "pipeline_core",
            "sample_transform_flow",
            "delivery_ready",
        ],
        "project_profile": "data_pipeline_copilot",
        "generation_mode": "production_data_pipeline_deliverable_first",
    }


def _cli_toolkit_defaults(package_name: str) -> dict[str, Any]:
    return {
        "source_rel": [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/commands.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "business_rel": [
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/commands.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "capabilities": [
            "command_core",
            "spec_seed",
            "delivery_ready",
        ],
        "project_profile": "cli_toolkit_copilot",
        "generation_mode": "production_cli_toolkit_deliverable_first",
    }


def _generic_copilot_defaults(package_name: str) -> dict[str, Any]:
    return {
        "source_rel": [
            "pyproject.toml",
            f"src/{package_name}/__init__.py",
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/planner.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "business_rel": [
            f"src/{package_name}/models.py",
            f"src/{package_name}/seed.py",
            f"src/{package_name}/spec_builder.py",
            f"src/{package_name}/planner.py",
            f"src/{package_name}/exporter.py",
            f"src/{package_name}/service.py",
            f"tests/test_{package_name}_service.py",
        ],
        "capabilities": [
            "spec_seed",
            "planner_core",
            "delivery_ready",
        ],
        "project_profile": "business_copilot",
        "generation_mode": "production_business_deliverable_first",
    }


def _indie_studio_hub_defaults(package_name: str) -> dict[str, Any]:
    defaults = _team_task_pm_defaults(package_name)
    defaults["source_rel"] = list(defaults["source_rel"]) + [
        f"src/{package_name}/dashboard.py",
        f"src/{package_name}/pages.py",
        f"src/{package_name}/search.py",
        f"src/{package_name}/import_export.py",
        f"src/{package_name}/settings.py",
        f"src/{package_name}/assets.py",
        f"src/{package_name}/bugs.py",
        f"src/{package_name}/releases.py",
        f"src/{package_name}/docs_center.py",
    ]
    defaults["business_rel"] = list(defaults["business_rel"]) + [
        f"src/{package_name}/dashboard.py",
        f"src/{package_name}/pages.py",
        f"src/{package_name}/search.py",
        f"src/{package_name}/import_export.py",
        f"src/{package_name}/settings.py",
        f"src/{package_name}/assets.py",
        f"src/{package_name}/bugs.py",
        f"src/{package_name}/releases.py",
        f"src/{package_name}/docs_center.py",
    ]
    defaults["capabilities"] = list(defaults["capabilities"]) + [
        "dashboard_overview",
        "milestone_tracking",
        "asset_management",
        "bug_tracking",
        "build_release",
        "docs_delivery",
        "search_sort",
        "import_export",
    ]
    defaults["project_profile"] = "indie_studio_production_hub"
    defaults["generation_mode"] = "production_indie_studio_hub_deliverable_first"
    return defaults


def _archetype_defaults(project_type: str, project_archetype: str, package_name: str) -> dict[str, Any]:
    if project_type == "narrative_copilot":
        return _narrative_production_defaults(package_name)
    if project_type == "indie_studio_hub" or project_archetype == "indie_studio_hub_web":
        return _indie_studio_hub_defaults(package_name)
    if project_type == "team_task_pm" or project_archetype == "team_task_pm_web":
        return _team_task_pm_defaults(package_name)
    if project_archetype == "web_service":
        return _web_service_defaults(package_name)
    if project_archetype == "data_pipeline":
        return _data_pipeline_defaults(package_name)
    if project_archetype == "cli_toolkit":
        return _cli_toolkit_defaults(package_name)
    return _generic_copilot_defaults(package_name)


def _production_project_defaults(project_type: str, project_archetype: str, package_name: str, delivery_shape: str) -> dict[str, Any]:
    shape_info = shape_contract(delivery_shape, package_name)
    startup_rel = str(shape_info["startup_rel"])
    workflow_doc_rel = str(shape_info["workflow_doc_rel"])
    defaults = _archetype_defaults(project_type, project_archetype, package_name)
    source_rel = list(defaults["source_rel"])
    business_rel = [startup_rel] + list(defaults["business_rel"])
    capabilities = list(defaults["capabilities"]) + [str(shape_info["shape_capability"])]
    project_profile = str(defaults["project_profile"])
    generation_mode = str(defaults["generation_mode"])
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
    project_domain: str,
    scaffold_family: str,
    project_type: str,
    package_name: str,
    project_archetype: str,
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
        "project_domain": project_domain,
        "scaffold_family": scaffold_family,
        "project_type": project_type,
        "project_archetype": project_archetype,
        "package_name": package_name,
        "project_profile": str(defaults["project_profile"]),
        "generation_mode": str(defaults["generation_mode"]),
        "execution_mode": str(decision["execution_mode"]),
        "benchmark_case": str(decision["benchmark_case"]),
        "delivery_shape": str(decision["delivery_shape"]),
        "project_domain_decision_source": str(decision.get("project_domain_decision_source", "")),
        "scaffold_family_decision_source": str(decision.get("scaffold_family_decision_source", "")),
        "project_type_decision_source": str(decision["project_type_decision_source"]),
        "project_archetype_decision_source": str(decision.get("project_archetype_decision_source", "")),
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
        "build_profile": str(decision.get("build_profile", "standard_mvp")),
        "product_depth": str(decision.get("product_depth", "mvp")),
        "required_pages": int(decision.get("required_pages", 0) or 0),
        "required_screenshots": int(decision.get("required_screenshots", 0) or 0),
        "require_feature_matrix": bool(decision.get("require_feature_matrix", False)),
        "require_page_map": bool(decision.get("require_page_map", False)),
        "require_data_model_summary": bool(decision.get("require_data_model_summary", False)),
        "require_search": bool(decision.get("require_search", False)),
        "require_import_or_export": str(decision.get("require_import_or_export", "at_least_one")),
        "require_dashboard_or_project_overview": bool(decision.get("require_dashboard_or_project_overview", False)),
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
    project_domain = str(decision.get("project_domain", "generic_software_project"))
    scaffold_family = str(decision.get("scaffold_family", "generic_copilot"))
    project_type = str(decision["project_type"])
    project_archetype = str(decision.get("project_archetype", "generic_copilot"))
    project_id = default_project_id(_slug(goal), project_type, execution_mode)
    package_name = default_package_name(project_id, project_type, execution_mode, benchmark_case)
    project_root = f"project_output/{project_id}"
    if execution_mode == BENCHMARK_MODE and project_type == "narrative_copilot":
        defaults = _benchmark_narrative_defaults()
    else:
        defaults = _production_project_defaults(project_type, project_archetype, package_name, str(decision["delivery_shape"]))
    if project_type == "indie_studio_hub" or project_archetype == "indie_studio_hub_web":
        package_prefix = f"src/{package_name}"
        extra_docs = [
            "docs/feature_matrix.md",
            "docs/page_map.md",
            "docs/data_model_summary.md",
            "docs/milestone_plan.md",
            "docs/startup_guide.md",
            "docs/replay_guide.md",
            "docs/mid_stage_review.md",
        ]
        defaults["doc_rel"] = list(defaults["doc_rel"]) + extra_docs
        defaults["business_rel"] = list(defaults["business_rel"]) + extra_docs
        defaults["capabilities"] = list(defaults["capabilities"]) + [
            "asset_detail",
            "docs_center",
            "ten_screenshots",
        ]
        defaults["project_profile"] = "indie_studio_production_hub"
        defaults["generation_mode"] = "production_indie_studio_hub_high_quality_extended"
    if project_type == "team_task_pm" and str(decision.get("build_profile", "")).strip() == "high_quality_extended":
        package_prefix = f"src/{package_name}"
        extra_source = [
            f"{package_prefix}/dashboard.py",
            f"{package_prefix}/pages.py",
            f"{package_prefix}/search.py",
            f"{package_prefix}/import_export.py",
            f"{package_prefix}/settings.py",
        ]
        extra_docs = [
            "docs/feature_matrix.md",
            "docs/page_map.md",
            "docs/data_model_summary.md",
            "docs/mid_stage_evidence.md",
        ]
        defaults["source_rel"] = list(defaults["source_rel"]) + extra_source
        defaults["doc_rel"] = list(defaults["doc_rel"]) + extra_docs
        defaults["business_rel"] = list(defaults["business_rel"]) + extra_source + extra_docs
        defaults["capabilities"] = list(defaults["capabilities"]) + [
            "dashboard_overview",
            "search_sort",
            "import_export",
            "extended_docs",
            "eight_screenshots",
        ]
        defaults["project_profile"] = "team_task_pm_high_quality_extended"
        defaults["generation_mode"] = "production_team_task_pm_high_quality_extended"
    return _assemble_project_file_lists(
        project_root=project_root,
        project_id=project_id,
        project_domain=project_domain,
        scaffold_family=scaffold_family,
        project_type=project_type,
        package_name=package_name,
        project_archetype=project_archetype,
        decision=decision,
        defaults=defaults,
    )


def normalize_output_contract_freeze(doc: dict[str, Any] | None, *, goal: str, run_dir: Path | None = None) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    project_queue = _extract_project_queue(src, goal=goal_text, run_dir=run_dir, include_output_contract=False)
    if len(project_queue) > 1 or bool(src.get("portfolio_mode", False)):
        return _portfolio_output_contract(goal_text, src=src, run_dir=run_dir, project_queue=project_queue)
    defaults = _default_project_file_lists(goal_text, run_dir=run_dir, src=src)
    project_intent = _resolve_project_intent(goal_text, run_dir=run_dir, src=src)
    project_root = str(defaults["project_root"])
    project_id = str(defaults["project_id"])
    project_domain = str(defaults.get("project_domain", "generic_software_project"))
    scaffold_family = str(defaults.get("scaffold_family", "generic_copilot"))
    project_type = str(defaults["project_type"])
    project_archetype = str(defaults.get("project_archetype", "generic_copilot"))
    package_name = str(defaults["package_name"])
    project_profile = str(defaults["project_profile"])
    team_pm_requested = _contains_any(
        " ".join(
            [
                goal_text,
                json.dumps(project_intent, ensure_ascii=False),
                json.dumps(src.get("project_spec", {}) if isinstance(src.get("project_spec", {}), dict) else {}, ensure_ascii=False),
            ]
        ),
        TEAM_PM_KEYWORDS,
    )
    indie_hub_requested = is_indie_studio_hub_signal(
        goal_text,
        project_intent=project_intent,
        project_spec=src.get("project_spec", {}) if isinstance(src.get("project_spec", {}), dict) else {},
        constraints=src.get("constraints", {}) if isinstance(src.get("constraints", {}), dict) else {},
    )
    if indie_hub_requested and (
        project_domain != "indie_studio_production_hub"
        or scaffold_family != "indie_studio_hub"
        or project_type != "indie_studio_hub"
        or project_archetype != "indie_studio_hub_web"
    ):
        raise ValueError(
            "Indie Studio Production Hub request must freeze as "
            "indie_studio_production_hub/indie_studio_hub/indie_studio_hub/indie_studio_hub_web; "
            f"got {project_domain}/{scaffold_family}/{project_type}/{project_archetype}"
        )
    if team_pm_requested and not indie_hub_requested and (
        project_domain != "team_task_management"
        or scaffold_family != "team_task_pm"
        or project_type != "team_task_pm"
        or project_archetype == "web_service"
        or project_archetype.startswith("generic")
    ):
        raise ValueError(
            "Plane-lite/team task PM project must freeze as team_task_management/team_task_pm/team_task_pm_web; "
            f"got {project_domain}/{scaffold_family}/{project_type}/{project_archetype}"
        )
    project_spec = enrich_project_spec(
        goal=goal_text,
        base_spec=_resolve_project_spec(goal_text, run_dir=run_dir, src=src, project_intent=project_intent),
        project_intent=project_intent,
        project_domain=project_domain,
        scaffold_family=scaffold_family,
        project_type=project_type,
        project_archetype=project_archetype,
        delivery_shape=str(defaults.get("delivery_shape", CLI_SHAPE)),
    )

    target_files = src.get("target_files") if isinstance(src.get("target_files"), list) else defaults["target_files"]
    source_files = src.get("source_files") if isinstance(src.get("source_files"), list) else defaults["source_files"]
    doc_files = src.get("doc_files") if isinstance(src.get("doc_files"), list) else defaults["doc_files"]
    workflow_files = src.get("workflow_files") if isinstance(src.get("workflow_files"), list) else defaults["workflow_files"]
    business_files = src.get("business_files") if isinstance(src.get("business_files"), list) else defaults["business_files"]
    materialize_capabilities = (
        src.get("business_capabilities")
        if isinstance(src.get("business_capabilities"), list)
        else defaults["business_capabilities"]
    )
    capability_plan = resolve_capability_plan(
        project_domain=project_domain,
        scaffold_family=scaffold_family,
        project_type=project_type,
        project_archetype=project_archetype,
        project_spec=project_spec,
        materialize_capabilities=[str(item) for item in materialize_capabilities],
    )
    business_capabilities = list(capability_plan.get("required_bundles", []))
    acceptance_files = src.get("acceptance_files") if isinstance(src.get("acceptance_files"), list) else defaults["acceptance_files"]
    reference_mode = src.get("reference_project_mode") if isinstance(src.get("reference_project_mode"), dict) else defaults["reference_project_mode"]
    reference_style = (
        src.get("reference_style_applied")
        if isinstance(src.get("reference_style_applied"), list)
        else defaults["reference_style_applied"]
    )
    sample_generation_artifacts = [
        f"artifacts/sample_generation/{step}.json"
        for step in capability_plan.get("sample_generation_steps", [])
        if str(step).strip()
    ]

    normalized_target = sorted(set(_normalize_rel_list([str(x) for x in target_files])))
    pipeline_contract = _pipeline_contract(
        project_root=project_root,
        startup_entrypoint=str(defaults["startup_entrypoint"]),
        startup_readme=str(defaults["startup_readme"]),
        business_files=_normalize_rel_list([str(x) for x in business_files]),
        acceptance_files=_normalize_rel_list([str(x) for x in acceptance_files]),
    )
    return {
        "schema_version": "ctcp-project-output-contract-v1",
        "stage": "output_contract_freeze",
        "goal": goal_text,
        "project_intent": project_intent,
        "project_spec": project_spec,
        "project_spec_path": "artifacts/project_spec.json",
        "capability_plan": capability_plan,
        "capability_plan_path": "artifacts/capability_plan.json",
        "sample_generation_plan": dict(project_spec.get("sample_content_plan", {})) if isinstance(project_spec.get("sample_content_plan"), dict) else {},
        "sample_generation_artifacts": sample_generation_artifacts,
        "generation_quality_report_path": "artifacts/generation_quality_report.json",
        "pipeline_contract": pipeline_contract,
        "project_id": project_id,
        "project_root": project_root,
        "project_domain": project_domain,
        "scaffold_family": scaffold_family,
        "project_type": project_type,
        "project_archetype": project_archetype,
        "package_name": package_name,
        "project_profile": project_profile,
        "generation_mode": str(defaults["generation_mode"]),
        "execution_mode": str(defaults["execution_mode"]),
        "benchmark_case": str(defaults["benchmark_case"]),
        "delivery_shape": str(defaults["delivery_shape"]),
        "project_domain_decision_source": str(defaults.get("project_domain_decision_source", "")),
        "scaffold_family_decision_source": str(defaults.get("scaffold_family_decision_source", "")),
        "project_type_decision_source": str(defaults["project_type_decision_source"]),
        "project_archetype_decision_source": str(defaults.get("project_archetype_decision_source", "")),
        "shape_decision_source": str(defaults["shape_decision_source"]),
        "target_files": normalized_target,
        "source_files": _normalize_rel_list([str(x) for x in source_files]),
        "doc_files": _normalize_rel_list([str(x) for x in doc_files]),
        "workflow_files": _normalize_rel_list([str(x) for x in workflow_files]),
        "business_files": _normalize_rel_list([str(x) for x in business_files]),
        "business_capabilities": _normalize_rel_list([str(x) for x in business_capabilities]),
        "materialize_capabilities": _normalize_rel_list([str(x) for x in capability_plan.get("materialize_bundles", [])]),
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
        "build_profile": str(defaults.get("build_profile", "standard_mvp")),
        "product_depth": str(defaults.get("product_depth", "mvp")),
        "required_pages": int(defaults.get("required_pages", 0) or 0),
        "required_screenshots": int(defaults.get("required_screenshots", 0) or 0),
        "require_feature_matrix": bool(defaults.get("require_feature_matrix", False)),
        "require_page_map": bool(defaults.get("require_page_map", False)),
        "require_data_model_summary": bool(defaults.get("require_data_model_summary", False)),
        "require_search": bool(defaults.get("require_search", False)),
        "require_import_or_export": str(defaults.get("require_import_or_export", "at_least_one")),
        "require_dashboard_or_project_overview": bool(defaults.get("require_dashboard_or_project_overview", False)),
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
        "project_domain",
        "scaffold_family",
        "project_type",
        "package_name",
        "project_archetype",
        "generation_mode",
        "execution_mode",
        "benchmark_case",
        "delivery_shape",
        "project_domain_decision_source",
        "scaffold_family_decision_source",
        "project_type_decision_source",
        "project_archetype_decision_source",
        "shape_decision_source",
        "startup_entrypoint",
        "startup_readme",
        "visual_evidence_status",
        "build_profile",
        "product_depth",
        "require_import_or_export",
        "project_spec_path",
        "capability_plan_path",
        "generation_quality_report_path",
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
        "materialize_capabilities",
        "reference_style_applied",
        "decision_nodes",
        "flow_nodes",
        "sample_generation_artifacts",
    ):
        value = doc.get(key)
        if isinstance(value, list):
            cleaned = _normalize_rel_list([str(x) for x in value])
            if cleaned:
                out[key] = cleaned
    for key in (
        "demo_required",
        "visual_evidence_required",
        "screenshot_required",
        "benchmark_sample_applied",
        "require_feature_matrix",
        "require_page_map",
        "require_data_model_summary",
        "require_search",
        "require_dashboard_or_project_overview",
    ):
        if key in doc:
            out[key] = bool(doc.get(key))
    for key in ("required_pages", "required_screenshots"):
        if key in doc:
            try:
                out[key] = int(doc.get(key, 0) or 0)
            except Exception:
                out[key] = 0
    for key in ("project_intent", "project_spec", "pipeline_contract", "capability_plan", "sample_generation_plan"):
        value = doc.get(key)
        if isinstance(value, dict) and value:
            out[key] = value
    mode = doc.get("reference_project_mode")
    if isinstance(mode, dict) and "enabled" in mode and "mode" in mode:
        out["reference_project_mode"] = mode
    return out


def normalize_source_generation(doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
    project_queue = _extract_project_queue(doc, goal=goal, run_dir=run_dir, include_output_contract=True)
    if len(project_queue) > 1:
        def _freeze_project(freeze_doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
            return normalize_output_contract_freeze(freeze_doc, goal=goal, run_dir=run_dir)

        def _single_source_generation(source_doc: dict[str, Any] | None, *, goal: str, run_dir: Path) -> dict[str, Any]:
            return normalize_source_generation_stage(
                doc=source_doc,
                goal=goal,
                run_dir=run_dir,
                load_output_contract_lists=_load_output_contract_lists,
                project_slug=_project_slug,
            )

        return normalize_project_queue_source_generation_stage(
            doc=doc,
            goal=goal,
            run_dir=run_dir,
            load_output_contract_lists=_load_output_contract_lists,
            project_slug=_project_slug,
            freeze_project=_freeze_project,
            source_project=_single_source_generation,
            manifest_project=normalize_project_manifest,
            deliverable_project=normalize_deliverable_index,
            project_queue=project_queue,
        )
    return normalize_source_generation_stage(
        doc=doc,
        goal=goal,
        run_dir=run_dir,
        load_output_contract_lists=_load_output_contract_lists,
        project_slug=_project_slug,
    )


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
                    "artifacts/project_spec.json",
                    "artifacts/capability_plan.json",
                    "artifacts/source_generation_report.json",
                    "artifacts/generation_quality_report.json",
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
    startup_entrypoint = str(lists.get("startup_entrypoint", "")).strip()
    if startup_entrypoint and startup_entrypoint not in source_files and not (run_dir / startup_entrypoint).exists():
        startup_entrypoint = ""
    startup_entrypoint = startup_entrypoint or next((p for p in source_files if p.endswith("/scripts/run_narrative_copilot.py")), "")
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
    project_intent = source_stage_doc.get("project_intent") if isinstance(source_stage_doc.get("project_intent"), dict) else lists.get("project_intent", {})
    if not isinstance(project_intent, dict) or not project_intent:
        project_intent = _resolve_project_intent(goal_text, run_dir=run_dir, src=src)
    project_spec = source_stage_doc.get("project_spec") if isinstance(source_stage_doc.get("project_spec"), dict) else lists.get("project_spec", {})
    if not isinstance(project_spec, dict) or not project_spec:
        project_spec = _resolve_project_spec(goal_text, run_dir=run_dir, src=src, project_intent=project_intent)
    capability_plan = source_stage_doc.get("capability_plan") if isinstance(source_stage_doc.get("capability_plan"), dict) else lists.get("capability_plan", {})
    if not isinstance(capability_plan, dict):
        capability_plan = {}
    pipeline_contract = source_stage_doc.get("pipeline_contract") if isinstance(source_stage_doc.get("pipeline_contract"), dict) else lists.get("pipeline_contract", {})
    if not isinstance(pipeline_contract, dict):
        pipeline_contract = {}
    generic_validation = source_stage_doc.get("generic_validation") if isinstance(source_stage_doc.get("generic_validation"), dict) else {}
    if not isinstance(generic_validation, dict):
        generic_validation = {}
    domain_validation = source_stage_doc.get("domain_validation") if isinstance(source_stage_doc.get("domain_validation"), dict) else {}
    if not isinstance(domain_validation, dict):
        domain_validation = {}
    product_validation = source_stage_doc.get("product_validation") if isinstance(source_stage_doc.get("product_validation"), dict) else {}
    if not isinstance(product_validation, dict):
        product_validation = {}

    return {
        "schema_version": "ctcp-project-manifest-v1",
        "stage": "artifact_manifest_build",
        "goal": goal_text,
        "project_intent": project_intent,
        "project_spec": project_spec,
        "project_spec_path": str(source_stage_doc.get("project_spec_path", "")).strip() or str(lists.get("project_spec_path", "")),
        "capability_plan": capability_plan,
        "capability_plan_path": str(source_stage_doc.get("capability_plan_path", "")).strip() or str(lists.get("capability_plan_path", "")),
        "sample_generation_plan": source_stage_doc.get("sample_generation_plan") if isinstance(source_stage_doc.get("sample_generation_plan"), dict) else lists.get("sample_generation_plan", {}),
        "sample_generation_artifacts": _normalize_rel_list([str(x) for x in source_stage_doc.get("sample_generation_artifacts", lists.get("sample_generation_artifacts", []))]),
        "generation_quality_report_path": str(source_stage_doc.get("generation_quality_report_path", "")).strip() or str(lists.get("generation_quality_report_path", "")),
        "generation_quality": source_stage_doc.get("generation_quality") if isinstance(source_stage_doc.get("generation_quality"), dict) else {},
        "capability_validation": source_stage_doc.get("capability_validation") if isinstance(source_stage_doc.get("capability_validation"), dict) else {},
        "pipeline_contract": pipeline_contract,
        "run_id": str(src.get("run_id", "")).strip() or run_id,
        "project_id": str(src.get("project_id", "")).strip() or str(lists.get("project_id", "")).strip() or _slug(goal_text or run_id),
        "project_root": project_root,
        "project_domain": str(lists.get("project_domain", "")),
        "scaffold_family": str(lists.get("scaffold_family", "")),
        "project_type": str(lists.get("project_type", "")),
        "project_archetype": str(lists.get("project_archetype", "")),
        "project_profile": str(lists.get("project_profile", "")),
        "generation_mode": str(source_stage_doc.get("generation_mode", "")).strip() or str(lists.get("generation_mode", "")),
        "execution_mode": str(source_stage_doc.get("execution_mode", "")).strip() or str(lists.get("execution_mode", PRODUCTION_MODE)),
        "benchmark_case": str(source_stage_doc.get("benchmark_case", "")).strip() or str(lists.get("benchmark_case", "")),
        "delivery_shape": str(source_stage_doc.get("delivery_shape", "")).strip() or str(lists.get("delivery_shape", CLI_SHAPE)),
        "project_domain_decision_source": str(source_stage_doc.get("project_domain_decision_source", "")).strip()
        or str(lists.get("project_domain_decision_source", "")),
        "scaffold_family_decision_source": str(source_stage_doc.get("scaffold_family_decision_source", "")).strip()
        or str(lists.get("scaffold_family_decision_source", "")),
        "project_type_decision_source": str(source_stage_doc.get("project_type_decision_source", "")).strip()
        or str(lists.get("project_type_decision_source", "")),
        "project_archetype_decision_source": str(source_stage_doc.get("project_archetype_decision_source", "")).strip()
        or str(lists.get("project_archetype_decision_source", "")),
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
        "visual_evidence_files": _normalize_rel_list([str(x) for x in source_stage_doc.get("visual_evidence_files", [])]) if isinstance(source_stage_doc.get("visual_evidence_files"), list) else [],
        "visual_type": str(source_stage_doc.get("visual_type", "")).strip()
        or str(dict(source_stage_doc.get("visual_evidence_capture", {})).get("visual_type", "")).strip(),
        "benchmark_sample_applied": bool(source_stage_doc.get("benchmark_sample_applied", lists.get("benchmark_sample_applied", False))),
        "decision_nodes": _normalize_rel_list([str(x) for x in source_stage_doc.get("decision_nodes", lists.get("decision_nodes", []))]),
        "flow_nodes": _normalize_rel_list([str(x) for x in source_stage_doc.get("flow_nodes", lists.get("flow_nodes", []))]),
        "gate_layers": source_stage_doc.get("gate_layers") if isinstance(source_stage_doc.get("gate_layers"), dict) else {},
        "behavioral_checks": source_stage_doc.get("behavioral_checks") if isinstance(source_stage_doc.get("behavioral_checks"), dict) else {},
        "domain_compatibility": source_stage_doc.get("domain_compatibility") if isinstance(source_stage_doc.get("domain_compatibility"), dict) else compatibility_report(project_domain=str(lists.get("project_domain", "")), scaffold_family=str(lists.get("scaffold_family", ""))),
        "readme_quality": source_stage_doc.get("readme_quality") if isinstance(source_stage_doc.get("readme_quality"), dict) else {},
        "ux_validation": source_stage_doc.get("ux_validation") if isinstance(source_stage_doc.get("ux_validation"), dict) else {},
        "visual_evidence_capture": source_stage_doc.get("visual_evidence_capture") if isinstance(source_stage_doc.get("visual_evidence_capture"), dict) else {},
        "build_profile": str(source_stage_doc.get("build_profile", "")).strip() or str(lists.get("build_profile", "standard_mvp")),
        "product_depth": str(source_stage_doc.get("product_depth", "")).strip() or str(lists.get("product_depth", "mvp")),
        "required_pages": int(lists.get("required_pages", 0) or 0),
        "required_screenshots": int(lists.get("required_screenshots", 0) or 0),
        "extended_coverage": source_stage_doc.get("extended_coverage") if isinstance(source_stage_doc.get("extended_coverage"), dict) else {},
        "extended_coverage_ledger_path": str(source_stage_doc.get("extended_coverage_ledger_path", "")).strip(),
        "generic_validation": generic_validation,
        "domain_validation": domain_validation,
        "product_validation": product_validation,
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
    for field in ("business_files_generated", "acceptance_files", "source_files", "doc_files", "workflow_files", "visual_evidence_files", "sample_generation_artifacts"):
        value = manifest_doc.get(field)
        if isinstance(value, list):
            deliverables.extend(str(row).strip() for row in value if str(row).strip())
    final_package_path = _build_final_project_bundle(run_dir, str(manifest_doc.get("project_root", "")).strip())
    if final_package_path:
        deliverables.append(final_package_path)
    evidence_bundle_path = build_intermediate_evidence_bundle(run_dir)
    if evidence_bundle_path:
        deliverables.append(evidence_bundle_path)
    deliverables.extend(
        [
            "artifacts/output_contract_freeze.json",
            "artifacts/project_spec.json",
            "artifacts/capability_plan.json",
            "artifacts/source_generation_report.json",
            "artifacts/generation_quality_report.json",
            "artifacts/project_manifest.json",
            "artifacts/deliverable_index.json",
        ]
    )
    return {
        "schema_version": "ctcp-deliverable-index-v1",
        "stage": "deliver",
        "goal": str(src.get("goal", "")).strip() or goal.strip(),
        "project_intent": manifest_doc.get("project_intent", {}) if isinstance(manifest_doc.get("project_intent"), dict) else {},
        "project_spec": manifest_doc.get("project_spec", {}) if isinstance(manifest_doc.get("project_spec"), dict) else {},
        "project_spec_path": str(manifest_doc.get("project_spec_path", "")).strip(),
        "capability_plan": manifest_doc.get("capability_plan", {}) if isinstance(manifest_doc.get("capability_plan"), dict) else {},
        "capability_plan_path": str(manifest_doc.get("capability_plan_path", "")).strip(),
        "sample_generation_plan": manifest_doc.get("sample_generation_plan", {}) if isinstance(manifest_doc.get("sample_generation_plan"), dict) else {},
        "sample_generation_artifacts": [str(row).strip() for row in manifest_doc.get("sample_generation_artifacts", []) if str(row).strip()] if isinstance(manifest_doc.get("sample_generation_artifacts"), list) else [],
        "generation_quality_report_path": str(manifest_doc.get("generation_quality_report_path", "")).strip(),
        "generation_quality": manifest_doc.get("generation_quality", {}) if isinstance(manifest_doc.get("generation_quality"), dict) else {},
        "capability_validation": manifest_doc.get("capability_validation", {}) if isinstance(manifest_doc.get("capability_validation"), dict) else {},
        "pipeline_contract": manifest_doc.get("pipeline_contract", {}) if isinstance(manifest_doc.get("pipeline_contract"), dict) else {},
        "run_id": str(src.get("run_id", "")).strip() or run_dir.name,
        "project_id": str(src.get("project_id", "")).strip() or str(manifest_doc.get("project_id", "")).strip() or _slug(goal or run_dir.name),
        "project_manifest_path": "artifacts/project_manifest.json",
        "project_root": str(manifest_doc.get("project_root", "")).strip(),
        "project_domain": str(manifest_doc.get("project_domain", "")).strip(),
        "scaffold_family": str(manifest_doc.get("scaffold_family", "")).strip(),
        "project_type": str(manifest_doc.get("project_type", "")).strip(),
        "project_archetype": str(manifest_doc.get("project_archetype", "")).strip(),
        "generation_mode": str(manifest_doc.get("generation_mode", "")).strip(),
        "execution_mode": str(manifest_doc.get("execution_mode", PRODUCTION_MODE)).strip(),
        "benchmark_case": str(manifest_doc.get("benchmark_case", "")).strip(),
        "delivery_shape": str(manifest_doc.get("delivery_shape", CLI_SHAPE)).strip(),
        "project_domain_decision_source": str(manifest_doc.get("project_domain_decision_source", "")).strip(),
        "scaffold_family_decision_source": str(manifest_doc.get("scaffold_family_decision_source", "")).strip(),
        "project_type_decision_source": str(manifest_doc.get("project_type_decision_source", "")).strip(),
        "project_archetype_decision_source": str(manifest_doc.get("project_archetype_decision_source", "")).strip(),
        "shape_decision_source": str(manifest_doc.get("shape_decision_source", "")).strip(),
        "startup_entrypoint": str(manifest_doc.get("startup_entrypoint", "")).strip(),
        "startup_readme": str(manifest_doc.get("startup_readme", "")).strip(),
        "demo_required": bool(manifest_doc.get("demo_required", False)),
        "visual_evidence_required": bool(manifest_doc.get("visual_evidence_required", False)),
        "screenshot_required": bool(manifest_doc.get("screenshot_required", False)),
        "visual_evidence_status": str(manifest_doc.get("visual_evidence_status", "not_requested")).strip(),
        "visual_evidence_files": _normalize_rel_list([str(x) for x in manifest_doc.get("visual_evidence_files", [])]) if isinstance(manifest_doc.get("visual_evidence_files"), list) else [],
        "visual_type": str(manifest_doc.get("visual_type", "")).strip(),
        "build_profile": str(manifest_doc.get("build_profile", "standard_mvp")).strip(),
        "product_depth": str(manifest_doc.get("product_depth", "mvp")).strip(),
        "required_pages": int(manifest_doc.get("required_pages", 0) or 0),
        "required_screenshots": int(manifest_doc.get("required_screenshots", 0) or 0),
        "extended_coverage": manifest_doc.get("extended_coverage", {}) if isinstance(manifest_doc.get("extended_coverage", {}), dict) else {},
        "extended_coverage_ledger_path": str(manifest_doc.get("extended_coverage_ledger_path", "")).strip(),
        "final_package_path": final_package_path,
        "evidence_bundle_path": evidence_bundle_path,
        "generic_validation": manifest_doc.get("generic_validation", {}) if isinstance(manifest_doc.get("generic_validation"), dict) else {},
        "domain_validation": manifest_doc.get("domain_validation", {}) if isinstance(manifest_doc.get("domain_validation"), dict) else {},
        "product_validation": manifest_doc.get("product_validation", {}) if isinstance(manifest_doc.get("product_validation"), dict) else {},
        "domain_compatibility": manifest_doc.get("domain_compatibility", {}) if isinstance(manifest_doc.get("domain_compatibility"), dict) else {},
        "readme_quality": manifest_doc.get("readme_quality", {}) if isinstance(manifest_doc.get("readme_quality"), dict) else {},
        "ux_validation": manifest_doc.get("ux_validation", {}) if isinstance(manifest_doc.get("ux_validation"), dict) else {},
        "business_deliverables": _normalize_rel_list([str(x) for x in manifest_doc.get("business_files_generated", [])]) if isinstance(manifest_doc.get("business_files_generated"), list) else [],
        "deliverables": sorted(set(deliverables)),
        "delivery_note": str(src.get("delivery_note", "")).strip() or "deliver artifacts are indexed for bridge consumption and mode-aware verify handoff",
    }
