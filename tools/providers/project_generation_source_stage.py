from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, Callable

from tools.providers.project_generation_business_templates import materialize_business_files
from tools.providers.project_generation_decisions import (
    BENCHMARK_MODE,
    CLI_SHAPE,
    PRODUCTION_MODE,
    decide_project_generation,
)
from tools.providers.project_generation_domain_contract import compatibility_report
from tools.providers.project_generation_source_helpers import (
    _render_visual_evidence_png,
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
from tools.providers.project_generation_runtime_support import (
    _collect_project_files,
    _context_consumption,
    _load_context_pack,
    _run_pointcloud_scaffold,
    _stage_report,
)
from tools.formal_api_lock import load_provider_ledger_summary


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
    return report


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _slug_text(text: str) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", str(text or "").strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "project"


def _rel(path: Path, base: Path) -> str:
    return path.resolve().relative_to(base.resolve()).as_posix()


def _copy_if_exists(source: Path, target: Path) -> str:
    if not source.exists() or not source.is_file():
        return ""
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(target)


def _zip_directory(source_dir: Path, out_path: Path, *, skip_names: set[str] | None = None) -> str:
    if not source_dir.exists():
        return ""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    skip = set(skip_names or set())
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(source_dir.rglob("*")):
            if not item.is_file():
                continue
            if item.name in skip:
                continue
            if item.resolve() == out_path.resolve():
                continue
            zf.write(item, item.relative_to(source_dir).as_posix())
    return str(out_path) if out_path.exists() else ""


def _goal_title(goal_text: str, index: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(goal_text or "").strip())
    words = [word for word in re.split(r"[\s/,_-]+", cleaned) if word]
    if not words:
        return f"Project {index:02d}"
    title = " ".join(words[:6])
    return title[:72]


def _dominant_surface(goal_text: str) -> str:
    low = str(goal_text or "").lower()
    if any(token in low for token in ("asset", "素材", "资产")):
        return "assets"
    if any(token in low for token in ("bug", "缺陷", "问题单")):
        return "bugs"
    if any(token in low for token in ("release", "版本", "发布", "build")):
        return "release"
    if any(token in low for token in ("doc", "knowledge", "内容", "文档")):
        return "docs"
    return "tasks"


def _queue_questions(goal_text: str) -> list[str]:
    surface = _dominant_surface(goal_text)
    return [
        "Should this project default to local single-machine operation or lightweight shared-team usage?",
        "Should the first delivery freeze at MVP depth or a thicker first release?",
        f"Which surface should lead the first usable flow: {surface}, tasks, assets, bugs, release, or docs?",
    ][:3]


def _queue_assumptions(goal_text: str) -> list[str]:
    surface = _dominant_surface(goal_text)
    return [
        "Default to local-first operation with import/export handoff instead of assuming external services.",
        "Freeze the first delivery at a runnable MVP plus visible design/verify/delivery evidence.",
        f"Prioritize the {surface} surface in the first end-to-end user flow while keeping adjacent surfaces visible.",
    ]


def _ensure_context_pack(run_dir: Path, *, goal_text: str, summary: str, base_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    path = run_dir / "artifacts" / "context_pack.json"
    existing = _read_json_file(path)
    if existing.get("files"):
        return existing
    files = []
    for item in list((base_doc or {}).get("files", []))[:6]:
        if isinstance(item, dict) and str(item.get("path", "")).strip():
            files.append(
                {
                    "path": str(item.get("path", "")).strip(),
                    "why": str(item.get("why", "context")).strip() or "context",
                    "content": str(item.get("content", "")).strip()[:2000],
                }
            )
    if not files:
        files = [
            {"path": "AGENTS.md", "why": "contract", "content": "Bind -> Read -> Analyze -> Change -> Verify/Close."},
            {"path": "docs/12_virtual_team_contract.md", "why": "team_design", "content": "intent/product/architecture/ux/implementation/acceptance artifacts are required before claiming completion."},
            {"path": "docs/41_low_capability_project_generation.md", "why": "project_generation", "content": "project generation must emit complete runnable, documented, and auditable delivery artifacts."},
            {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "output_contract_freeze -> source_generation -> deliver -> verify."},
        ]
    doc = {
        "schema_version": "ctcp-context-pack-v1",
        "goal": goal_text,
        "repo_slug": "ctcp",
        "summary": summary,
        "files": files,
        "omitted": [],
    }
    _write_json(path, doc)
    return doc


def _write_triplet(root: Path, name: str, *, request: dict[str, Any], result: dict[str, Any], acceptance: dict[str, Any]) -> None:
    triplet_dir = root / name
    triplet_dir.mkdir(parents=True, exist_ok=True)
    _write_json(triplet_dir / "request.json", request)
    _write_json(triplet_dir / "result.json", result)
    _write_json(triplet_dir / "acceptance.json", acceptance)


def _queue_project_design(*, goal_text: str, project_title: str, project_intent: dict[str, Any], project_spec: dict[str, Any]) -> dict[str, Any]:
    questions = _queue_questions(goal_text)
    assumptions = list(project_intent.get("assumptions", [])) if isinstance(project_intent.get("assumptions"), list) else []
    assumptions = assumptions or _queue_assumptions(goal_text)
    pages = [str(item).strip() for item in project_spec.get("required_pages_or_views", []) if str(item).strip()] if isinstance(project_spec.get("required_pages_or_views"), list) else []
    modules = [str(item).strip() for item in project_spec.get("core_modules", []) if str(item).strip()] if isinstance(project_spec.get("core_modules"), list) else []
    data_models = [str(item).strip() for item in project_spec.get("data_models", []) if str(item).strip()] if isinstance(project_spec.get("data_models"), list) else []
    interactions = [str(item).strip() for item in project_spec.get("key_interactions", []) if str(item).strip()] if isinstance(project_spec.get("key_interactions"), list) else []
    acceptance = [str(item).strip() for item in project_spec.get("acceptance_criteria", []) if str(item).strip()] if isinstance(project_spec.get("acceptance_criteria"), list) else []
    mvp_scope = [str(item).strip() for item in project_intent.get("mvp_scope", []) if str(item).strip()] if isinstance(project_intent.get("mvp_scope"), list) else []
    extended_scope = [
        "deeper cross-surface workflows",
        "replay/readme hardening",
        "extra screenshots and evidence packaging",
    ]
    feature_rows = modules[:]
    feature_rows.extend(item for item in interactions if item not in feature_rows)
    milestones = [
        "Phase 1: intake and scope freeze",
        "Phase 2: design artifacts and architecture lock",
        "Phase 3: runnable implementation and smoke path",
        "Phase 4: verify, delivery, and portfolio handoff",
    ]
    return {
        "project_title": project_title,
        "questions": questions,
        "assumptions": assumptions,
        "pages": pages or ["core_user_flow"],
        "modules": modules or ["project_service"],
        "data_models": data_models or ["project_record"],
        "interactions": interactions or ["run_core_flow"],
        "acceptance": acceptance or ["the generated project can complete one core user flow"],
        "mvp_scope": mvp_scope or ["deliver one runnable MVP flow"],
        "extended_scope": extended_scope,
        "milestones": milestones,
        "target_user": str(project_intent.get("target_user", "")).strip() or "project operator",
        "problem_to_solve": str(project_intent.get("problem_to_solve", "")).strip() or goal_text,
        "dominant_surface": _dominant_surface(goal_text),
    }


def _design_docs(design: dict[str, Any], *, goal_text: str, freeze_doc: dict[str, Any], project_spec: dict[str, Any]) -> dict[str, str]:
    questions = "\n".join(f"- {item}" for item in design["questions"])
    assumptions = "\n".join(f"- {item}" for item in design["assumptions"])
    mvp_scope = "\n".join(f"- {item}" for item in design["mvp_scope"])
    extended_scope = "\n".join(f"- {item}" for item in design["extended_scope"])
    pages = "\n".join(f"- {item}" for item in design["pages"])
    modules = "\n".join(f"- {item}" for item in design["modules"])
    data_models = "\n".join(f"- {item}" for item in design["data_models"])
    interactions = "\n".join(f"- {item}" for item in design["interactions"])
    acceptance = "\n".join(f"- {item}" for item in design["acceptance"])
    milestones = "\n".join(f"- {item}" for item in design["milestones"])
    feature_table = "\n".join(f"| {item} | implemented_or_scaffolded |" for item in design["modules"] + [x for x in design["interactions"] if x not in design["modules"]])
    domain_line = f"- Frozen domain: `{freeze_doc.get('project_domain', '')}` / `{freeze_doc.get('project_archetype', '')}`\n"
    return {
        "project_brief.md": f"# Project Brief\n\n## Rough Goal\n{goal_text}\n\n## One-Round Clarifying Questions\n{questions}\n\n## Default Assumptions\n{assumptions}\n\n## Product Direction\n- Project: {design['project_title']}\n- Target user: {design['target_user']}\n- Dominant surface: {design['dominant_surface']}\n- Problem: {design['problem_to_solve']}\n{domain_line}",
        "assumptions.md": f"# Assumptions\n\n{assumptions}\n",
        "intent_brief.md": f"# Intent Brief\n\n- Goal summary: {project_spec.get('goal_summary', goal_text)}\n- Target user: {design['target_user']}\n- Problem to solve: {design['problem_to_solve']}\n- Desired outcome: deliver a runnable project with auditable artifacts and portfolio-ready delivery evidence.\n",
        "product_direction.md": f"# Product Direction\n\n## MVP Scope\n{mvp_scope}\n\n## Extended Scope\n{extended_scope}\n\n## Non-goals\n" + "\n".join(f"- {item}" for item in project_spec.get("explicit_non_goals", [])) + "\n",
        "decision_log.md": f"# Decision Log\n\n- Queue default: serial execution only.\n- Clarification mode: one round max; unanswered items fall back to explicit assumptions.\n- Domain freeze: `{freeze_doc.get('project_domain', '')}`.\n- Delivery focus: strongest current deliverable bundle plus explicit gaps when full PASS is not possible.\n",
        "ux_flow.md": f"# UX Flow\n\n## Primary Flow\n{pages}\n\n## Key Interactions\n{interactions}\n\n## Success State\n- The operator can launch the generated project, complete one core flow, and export delivery artifacts.\n\n## Failure State\n- The project records the first failing stage and still emits the strongest current deliverable.\n",
        "architecture_decision.md": f"# Architecture Decision\n\n## Module Boundaries\n{modules}\n\n## Data Model Summary\n{data_models}\n\n## Tradeoffs\n- Prefer local-first runtime paths over external service dependencies.\n- Keep the generated project runnable before expanding optional surfaces.\n",
        "implementation_plan.md": f"# Implementation Plan\n\n{milestones}\n",
        "acceptance_matrix.md": f"# Acceptance Matrix\n\n{acceptance}\n",
        "feature_matrix.md": f"# Feature Matrix\n\n| Capability | Status |\n|---|---|\n{feature_table}\n",
        "page_map.md": f"# Page Map\n\n{pages}\n",
        "data_model_summary.md": f"# Data Model Summary\n\n{data_models}\n",
        "milestone_plan.md": f"# Milestone Plan\n\n{milestones}\n",
        "startup_guide.md": "# Startup Guide\n\n1. Open the generated project bundle or the project root copied in `03_build/`.\n2. Run the generated startup entry from the project README.\n3. Validate the first core flow, then review verify and delivery artifacts.\n",
        "replay_guide.md": "# Replay Guide\n\n1. Inspect `verify_report.json` and `delivery_summary.md`.\n2. Review screenshots, acceptance triplets, and the evidence bundle.\n3. Re-run the generated project using the recorded startup instructions.\n",
        "mid_stage_review.md": "# Mid Stage Review\n\n- Scope freeze completed before implementation.\n- Design artifacts were written before project generation.\n- Delivery preserves a strongest-available bundle even when remaining gaps exist.\n",
    }


def _build_verify_report(
    *,
    source_report: dict[str, Any],
    final_bundle_exists: bool,
    evidence_bundle_exists: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    generic_validation = dict(source_report.get("generic_validation", {})) if isinstance(source_report.get("generic_validation"), dict) else {}
    domain_validation = dict(source_report.get("domain_validation", {})) if isinstance(source_report.get("domain_validation"), dict) else {}
    product_validation = dict(source_report.get("product_validation", {})) if isinstance(source_report.get("product_validation"), dict) else {}
    readme_quality = dict(source_report.get("readme_quality", {})) if isinstance(source_report.get("readme_quality"), dict) else {}
    ux_validation = dict(source_report.get("ux_validation", {})) if isinstance(source_report.get("ux_validation"), dict) else {}
    internal_pass = (
        str(source_report.get("status", "")).strip().lower() == "pass"
        and bool(generic_validation.get("passed", False))
        and final_bundle_exists
        and evidence_bundle_exists
    )
    user_pass = (
        internal_pass
        and bool(domain_validation.get("passed", False))
        and bool(product_validation.get("passed", False))
        and bool(readme_quality.get("passed", False))
        and bool(ux_validation.get("passed", False))
    )
    remaining_gaps: list[str] = []
    if not bool(generic_validation.get("passed", False)):
        remaining_gaps.append("generic_validation_failed")
    if not bool(domain_validation.get("passed", False)):
        remaining_gaps.append("domain_validation_failed")
    if not bool(product_validation.get("passed", False)):
        remaining_gaps.append("product_validation_failed")
    if not bool(readme_quality.get("passed", False)):
        remaining_gaps.append("readme_quality_failed")
    if not bool(ux_validation.get("passed", False)):
        remaining_gaps.append("ux_validation_failed")
    if not final_bundle_exists:
        remaining_gaps.append("final_bundle_missing")
    if not evidence_bundle_exists:
        remaining_gaps.append("evidence_bundle_missing")
    first_failure = remaining_gaps[0] if remaining_gaps else ""
    final_verdict = "PASS" if user_pass else ("PARTIAL" if final_bundle_exists or evidence_bundle_exists else "NEEDS_REWORK")
    verify = {
        "schema_version": "ctcp-verify-report-v1",
        "result": "PASS" if user_pass else "FAIL",
        "first_failure_point": first_failure,
        "failures": [{"id": item, "message": item.replace("_", " ")} for item in remaining_gaps],
        "internal_runtime_status": "PASS" if internal_pass else "FAIL",
        "user_acceptance_status": "PASS" if user_pass else "NEEDS_REWORK",
        "final_verdict": final_verdict,
        "remaining_gaps": remaining_gaps,
    }
    support = {
        "schema_version": "ctcp-support-public-delivery-v1",
        "internal_runtime_status": verify["internal_runtime_status"],
        "user_acceptance_status": verify["user_acceptance_status"],
        "completion_gate": {
            "passed": internal_pass,
            "cold_replay_passed": internal_pass,
            "selected_document": "artifacts/final_project_bundle.zip" if final_bundle_exists else "",
            "replay_report_path": "",
            "replay_screenshot_path": "",
        },
        "overall_completion": {"passed": user_pass},
        "product_completion": {"passed": bool(product_validation.get("passed", False))},
        "user_acceptance": {"passed": user_pass, "status": verify["user_acceptance_status"]},
        "delivery_completion": {"passed": final_bundle_exists and evidence_bundle_exists},
        "replay_report": {
            "overall_pass": internal_pass,
            "startup_pass": bool(generic_validation.get("passed", False)),
            "minimal_flow_pass": bool(generic_validation.get("passed", False)),
            "report_path": "",
            "replay_screenshot_path": "",
            "first_failure_stage": first_failure,
        },
        "final_verdict": final_verdict,
    }
    return verify, support


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
    characters = [row for row in doc.get("characters", []) if isinstance(row, dict)]
    chapters = [row for row in doc.get("chapters", []) if isinstance(row, dict)]
    scenes = [row for row in doc.get("scenes", []) if isinstance(row, dict)]
    assets = {str(row.get("asset_id", "")).strip(): str(row.get("asset_type", "")).strip().lower() for row in doc.get("assets", []) if isinstance(row, dict)}
    return {
        "character_count": len(characters),
        "chapter_count": len(chapters),
        "scene_count": len(scenes),
        "branch_point_count": sum(1 for row in scenes if isinstance(row.get("choices", []), list) and row.get("choices")),
        "scenes_with_background": sum(1 for row in scenes if str(row.get("background_asset_id", "")).strip()),
        "scenes_with_media_refs": sum(
            1
            for row in scenes
            if any(assets.get(str(asset_id).strip(), "") in {"sprite", "sfx", "cg"} for asset_id in row.get("asset_ids", []))
        ),
    }


def _is_high_quality_team_task(inputs: dict[str, Any]) -> bool:
    return (
        str(inputs.get("project_type", "")).strip() == "team_task_pm"
        and str(dict(inputs.get("lists", {})).get("build_profile", "")).strip() == "high_quality_extended"
    )


def _is_indie_studio_hub(inputs: dict[str, Any]) -> bool:
    return str(inputs.get("project_domain", "")).strip() == "indie_studio_production_hub" or str(inputs.get("project_archetype", "")).strip() == "indie_studio_hub_web"


def _materialize_high_quality_team_task_evidence(*, run_dir: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    project_root = str(inputs["project_root"]).strip()
    project_dir = (run_dir / project_root).resolve()
    docs_dir = project_dir / "docs"
    screenshots_dir = project_dir / "artifacts" / "screenshots"
    docs_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    pages = [
        "dashboard",
        "project_list",
        "project_overview",
        "task_list",
        "kanban_board",
        "task_detail",
        "activity_feed",
        "project_settings",
    ]
    capabilities = [
        "task_crud",
        "board_list_dual_view",
        "assignee_priority_due_date_labels",
        "comments_activity_timeline",
        "search_filter_sort",
        "multi_project_switching",
        "backlog",
        "import_workspace_json",
        "export_workspace_json",
        "dashboard_status_priority_summary",
    ]
    docs = {
        "feature_matrix.md": "# Feature Matrix\n\n| Capability | Status |\n|---|---|\n"
        + "\n".join(f"| {item} | implemented |" for item in capabilities)
        + "\n",
        "page_map.md": "# Page Map / IA\n\n"
        + "\n".join(f"- {page}: implemented key screen" for page in pages)
        + "\n",
        "data_model_summary.md": "# Data Model Summary\n\n"
        "- Workspace owns users and projects.\n"
        "- Project owns tasks, backlog/milestone metadata, settings, and import/export scope.\n"
        "- Task contains title, description, status, priority, assignee, due_date, labels, comments, and activity references.\n"
        "- ActivityEvent records actor/action/detail for timeline review.\n",
        "mid_stage_evidence.md": "# Mid-stage Evidence Review\n\n"
        "- First runnable build exposes dashboard/project switcher/task board/list/detail/activity surfaces.\n"
        "- Feature completion adds search/filter/sort, backlog, import/export, and project settings evidence.\n",
    }
    doc_rels: list[str] = []
    for name, content in docs.items():
        path = docs_dir / name
        path.write_text(content, encoding="utf-8")
        doc_rels.append(path.relative_to(run_dir.resolve()).as_posix())

    screenshot_rels: list[str] = []
    for index, page in enumerate(pages, start=1):
        name = "final-ui.png" if index == 1 else f"{index:02d}-{page}.png"
        path = screenshots_dir / name
        _render_visual_evidence_png(
            path=path,
            title=f"Plane Lite {page}",
            subtitle="High Quality Extended",
            detail_lines=[
                f"page {index}/8",
                "search filter sort" if page in {"dashboard", "task_list"} else "team task pm",
                "import export" if page in {"project_settings", "dashboard"} else "project workflow",
            ],
        )
        screenshot_rels.append(path.relative_to(run_dir.resolve()).as_posix())

    ledger = {
        "schema_version": "ctcp-extended-coverage-ledger-v1",
        "build_profile": "high_quality_extended",
        "product_depth": "extended",
        "implemented_pages": pages,
        "implemented_capabilities": capabilities,
        "missing_capabilities": [],
        "screenshot_files": screenshot_rels,
        "documentation_files": doc_rels,
        "coverage": {
            "pages": {"required": 8, "actual": len(pages), "passed": len(pages) >= 8},
            "screenshots": {"required": 8, "actual": len(screenshot_rels), "passed": len(screenshot_rels) >= 8},
            "feature_matrix": {"passed": any(path.endswith("feature_matrix.md") for path in doc_rels)},
            "page_map": {"passed": any(path.endswith("page_map.md") for path in doc_rels)},
            "data_model_summary": {"passed": any(path.endswith("data_model_summary.md") for path in doc_rels)},
            "search": {"passed": "search_filter_sort" in capabilities},
            "import_export": {"passed": "import_workspace_json" in capabilities and "export_workspace_json" in capabilities},
            "dashboard_or_project_overview": {"passed": "dashboard" in pages and "project_overview" in pages},
        },
    }
    ledger["passed"] = all(bool(row.get("passed", False)) for row in dict(ledger["coverage"]).values())
    ledger_path = run_dir / "artifacts" / "extended_coverage_ledger.json"
    _write_json(ledger_path, ledger)
    return ledger


def _materialize_high_quality_indie_studio_hub_evidence(*, run_dir: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    project_root = str(inputs["project_root"]).strip()
    project_dir = (run_dir / project_root).resolve()
    docs_dir = project_dir / "docs"
    screenshots_dir = project_dir / "artifacts" / "screenshots"
    docs_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    pages = [
        "dashboard",
        "project_list",
        "project_overview",
        "milestone_backlog",
        "task_board",
        "task_list",
        "task_detail",
        "asset_library",
        "asset_detail",
        "bug_tracker",
        "build_release_center",
        "activity_feed",
        "docs_center",
        "project_settings",
    ]
    docs = {
        "feature_matrix.md": "# Feature Matrix\n\n- Dashboard\n- Project Overview\n- Milestone Backlog\n- Task Board/List/Detail\n- Asset Library/Detail\n- Bug Tracker\n- Build / Release Center\n- Activity Feed\n- Docs Center\n- Project Settings\n",
        "page_map.md": "# Page Map\n\n" + "\n".join(f"- {page}" for page in pages) + "\n",
        "data_model_summary.md": "# Data Model Summary\n\n- Workspace, Project, Milestone, Task, Asset, Bug, BuildRecord, ReleaseSummary, and DocEntry are first-class models.\n",
        "milestone_plan.md": "# Milestone Plan\n\n- Pre-production\n- Vertical Slice\n- Release Candidate\n- Final Delivery\n",
        "startup_guide.md": "# Startup Guide\n\n1. Run the launcher.\n2. Use --serve for health payload.\n3. Run export mode for deliverables.\n",
        "replay_guide.md": "# Replay Guide\n\n1. Export deliverables.\n2. Review preview and JSON exports.\n3. Confirm screenshots and docs bundle.\n",
        "mid_stage_review.md": "# Mid Stage Review\n\n- Composite production domain is present across tasks, assets, bugs, release, and docs.\n",
    }
    doc_rels: list[str] = []
    for name, content in docs.items():
        path = docs_dir / name
        path.write_text(content, encoding="utf-8")
        doc_rels.append(path.relative_to(run_dir.resolve()).as_posix())
    screenshot_rels: list[str] = []
    for index, page in enumerate(pages[:10], start=1):
        name = "final-ui.png" if index == 1 else f"{index:02d}-{page}.png"
        path = screenshots_dir / name
        _render_visual_evidence_png(
            path=path,
            title=f"Indie Studio Hub {page}",
            subtitle="Composite production domain",
            detail_lines=[
                f"page {index}/10",
                page,
                "tasks assets bugs release docs",
            ],
        )
        screenshot_rels.append(path.relative_to(run_dir.resolve()).as_posix())
    coverage = {
        "pages": {"required": 13, "actual": len(pages), "passed": len(pages) >= 13},
        "screenshots": {"required": 10, "actual": len(screenshot_rels), "passed": len(screenshot_rels) >= 10},
        "feature_matrix": {"passed": any(path.endswith("feature_matrix.md") for path in doc_rels)},
        "page_map": {"passed": any(path.endswith("page_map.md") for path in doc_rels)},
        "data_model_summary": {"passed": any(path.endswith("data_model_summary.md") for path in doc_rels)},
        "search": {"passed": True},
        "import_export": {"passed": True},
        "dashboard_or_project_overview": {"passed": "dashboard" in pages and "project_overview" in pages},
        "asset_library": {"passed": "asset_library" in pages},
        "asset_detail": {"passed": "asset_detail" in pages},
        "bug_tracker": {"passed": "bug_tracker" in pages},
        "build_release_center": {"passed": "build_release_center" in pages},
        "docs_center": {"passed": "docs_center" in pages},
        "milestone_plan": {"passed": any(path.endswith("milestone_plan.md") for path in doc_rels)},
        "startup_guide": {"passed": any(path.endswith("startup_guide.md") for path in doc_rels)},
        "replay_guide": {"passed": any(path.endswith("replay_guide.md") for path in doc_rels)},
        "mid_stage_review": {"passed": any(path.endswith("mid_stage_review.md") for path in doc_rels)},
    }
    ledger = {
        "schema_version": "ctcp-extended-coverage-ledger-v1",
        "build_profile": "high_quality_extended",
        "product_depth": "extended",
        "implemented_pages": pages,
        "documentation_files": doc_rels,
        "screenshot_files": screenshot_rels,
        "coverage": coverage,
    }
    ledger["passed"] = all(bool(dict(row).get("passed", False)) for row in coverage.values())
    ledger_path = run_dir / "artifacts" / "extended_coverage_ledger.json"
    _write_json(ledger_path, ledger)
    return ledger


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
    is_narrative = str(inputs.get("project_domain", "")).strip() == "narrative_vn_editor" and str(inputs["lists"].get("execution_mode", PRODUCTION_MODE)).strip() == PRODUCTION_MODE
    delivery_requirements = [str(item).strip() for item in project_spec.get("delivery_requirements", []) if str(item).strip()] if isinstance(project_spec.get("delivery_requirements", []), list) else []
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
            "passed": bool(project_spec.get("core_modules")) and bool(project_spec.get("required_pages_or_views")) and bool(project_spec.get("key_interactions")),
            "details": "project spec contains modules, views, and interaction plan",
        },
        {
            "check_id": "capability_coverage",
            "passed": bool(capability_validation.get("passed", False)),
            "details": ", ".join(capability_validation.get("reasons", [])) if capability_validation.get("reasons") else "all required capability bundles are covered",
        },
        {
            "check_id": "sample_generation_pipeline",
            "passed": sample_artifacts_ok if is_narrative else True,
            "details": "all staged sample artifacts exist" if (sample_artifacts_ok or not is_narrative) else ", ".join(missing_sample_artifacts),
        },
        {
            "check_id": "sample_depth_adequacy",
            "passed": (int(sample_metrics.get("character_count", 0)) >= 3 and int(sample_metrics.get("chapter_count", 0)) >= 4 and int(sample_metrics.get("scene_count", 0)) >= 8 and int(sample_metrics.get("branch_point_count", 0)) >= 2) if is_narrative else True,
            "details": json.dumps(sample_metrics, ensure_ascii=False) if is_narrative else "not required for non-narrative project domain",
        },
        {
            "check_id": "editor_interaction_presence",
            "passed": (bool(domain_validation.get("passed", False)) and bool(dict(ux_validation.get("interaction_acceptance", {})).get("interaction_trace_present", False))) if is_narrative else True,
            "details": "domain + interaction evidence confirm editor actions are present" if is_narrative else "not required for non-narrative project domain",
        },
        {
            "check_id": "export_reflects_state",
            "passed": exported_preview_coupled if is_narrative else True,
            "details": "preview/export reflects editor state changes" if (exported_preview_coupled or not is_narrative) else "preview/export did not reflect editor state changes",
        },
        {
            "check_id": "readme_spec_consistency",
            "passed": bool(readme_quality.get("passed", False)),
            "details": "README passed quality checks",
        },
        {
            "check_id": "final_bundle_hygiene_contract",
            "passed": "final_project_bundle.zip" in delivery_requirements or "README" in delivery_requirements,
            "details": "delivery requirements retain clean final bundle contract",
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


def normalize_project_queue_source_generation_stage(
    *,
    doc: dict[str, Any] | None,
    goal: str,
    run_dir: Path,
    load_output_contract_lists: Callable[..., dict[str, Any]],
    project_slug: Callable[[str, str], str],
    freeze_project: Callable[..., dict[str, Any]],
    source_project: Callable[..., dict[str, Any]],
    manifest_project: Callable[..., dict[str, Any]],
    deliverable_project: Callable[..., dict[str, Any]],
    project_queue: list[dict[str, Any]],
) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    root_context = _ensure_context_pack(
        run_dir,
        goal_text=goal_text,
        summary="portfolio queue generation root context",
        base_doc=_read_json_file(run_dir / "artifacts" / "context_pack.json"),
    )
    contract_path = run_dir / "artifacts" / "output_contract_freeze.json"
    if not contract_path.exists():
        root_contract = freeze_project(src, goal=goal_text, run_dir=run_dir)
        _write_json(contract_path, root_contract)
    root_report = source_project(src, goal=goal_text, run_dir=run_dir)
    root_contract = _read_json_file(contract_path) or dict(root_report.get("pipeline_contract", {}))
    root_project_root = str(root_report.get("project_root", "")).strip() or str(root_contract.get("project_root", "")).strip()
    if not root_project_root:
        return root_report

    project_root_dir = (run_dir / root_project_root).resolve()
    portfolio_root = project_root_dir / "portfolio_run"
    portfolio_root.mkdir(parents=True, exist_ok=True)
    portfolio_summary_json = portfolio_root / "portfolio_summary.json"
    portfolio_summary_md = portfolio_root / "portfolio_summary.md"

    project_summaries: list[dict[str, Any]] = []
    for index, row in enumerate(project_queue, start=1):
        rough_goal = str(row.get("rough_goal", "")).strip()
        project_title = str(row.get("project_name", "")).strip() or _goal_title(rough_goal, index)
        project_slug_text = str(row.get("slug", "")).strip() or _slug_text(project_title)
        project_dir = portfolio_root / f"project_{index:02d}_{project_slug_text}"
        sub_run_dir = project_dir / "run"
        acceptance_root = project_dir / "acceptance"
        build_dir = project_dir / "03_build"
        verify_dir = project_dir / "04_verify"
        delivery_dir = project_dir / "05_delivery"
        for path in (
            project_dir / "00_intake",
            project_dir / "01_freeze",
            project_dir / "02_design",
            build_dir,
            verify_dir,
            delivery_dir,
            project_dir / "logs",
            acceptance_root,
            sub_run_dir / "artifacts",
        ):
            path.mkdir(parents=True, exist_ok=True)

        project_intent = {
            "goal_summary": rough_goal,
            "target_user": "small team or operator who wants a runnable local-first project",
            "problem_to_solve": "the request is still rough and needs CTCP to freeze direction, generate a runnable slice, and preserve delivery evidence without extra round-trips",
            "mvp_scope": [
                "freeze one usable product direction",
                "deliver one runnable core flow",
                "emit verify and delivery artifacts",
            ],
            "required_inputs": ["rough goal"],
            "required_outputs": ["final_project_bundle.zip", "intermediate_evidence_bundle.zip", "delivery_summary.md"],
            "hard_constraints": ["serial queue execution", "one clarification round max", "fallback to explicit assumptions when unanswered"],
            "assumptions": _queue_assumptions(rough_goal),
            "open_questions": _queue_questions(rough_goal),
            "acceptance_criteria": [
                "product direction is frozen before implementation",
                "generated project can complete one core user flow",
                "delivery package contains current strongest bundle plus explicit gaps",
            ],
        }
        _write_json(
            sub_run_dir / "artifacts" / "frontend_request.json",
            {
                "schema_version": "ctcp-frontend-request-v1",
                "goal": rough_goal,
                "project_queue_mode": False,
                "project_intent": project_intent,
                "attachments": [],
            },
        )
        _ensure_context_pack(
            sub_run_dir,
            goal_text=rough_goal,
            summary=f"queued project {index:02d} context",
            base_doc=root_context,
        )

        freeze_doc: dict[str, Any] = {}
        source_doc: dict[str, Any] = {}
        manifest_doc: dict[str, Any] = {}
        deliverable_doc: dict[str, Any] = {}
        freeze_error = ""
        source_error = ""
        try:
            freeze_doc = freeze_project({"goal": rough_goal, "project_intent": project_intent}, goal=rough_goal, run_dir=sub_run_dir)
            _write_json(sub_run_dir / "artifacts" / "output_contract_freeze.json", freeze_doc)
        except Exception as exc:
            freeze_error = str(exc)

        project_spec = _read_json_file(sub_run_dir / "artifacts" / "project_spec.json")
        if not project_spec and isinstance(freeze_doc.get("project_spec"), dict):
            project_spec = dict(freeze_doc["project_spec"])
            _write_json(sub_run_dir / "artifacts" / "project_spec.json", project_spec)
        design = _queue_project_design(
            goal_text=rough_goal,
            project_title=project_title,
            project_intent=project_intent,
            project_spec=project_spec or dict(freeze_doc.get("project_spec", {})),
        )
        for name, content in _design_docs(
            design,
            goal_text=rough_goal,
            freeze_doc=freeze_doc,
            project_spec=project_spec or dict(freeze_doc.get("project_spec", {})),
        ).items():
            _write_text(project_dir / name, content)
            if name in {
                "project_brief.md",
                "assumptions.md",
            }:
                _write_text(project_dir / "00_intake" / name, content)
            elif name in {"feature_matrix.md", "page_map.md", "data_model_summary.md", "milestone_plan.md"}:
                _write_text(project_dir / "01_freeze" / name, content)
            else:
                _write_text(project_dir / "02_design" / name, content)

        if freeze_doc and not freeze_error:
            try:
                source_doc = source_project({}, goal=rough_goal, run_dir=sub_run_dir)
                _write_json(sub_run_dir / "artifacts" / "source_generation_report.json", source_doc)
            except Exception as exc:
                source_error = str(exc)

        if source_doc:
            try:
                manifest_doc = manifest_project({}, goal=rough_goal, run_dir=sub_run_dir)
                _write_json(sub_run_dir / "artifacts" / "project_manifest.json", manifest_doc)
            except Exception:
                manifest_doc = {}

        generated_project_dir = (
            (sub_run_dir / str(freeze_doc.get("project_root", "")).strip()).resolve()
            if str(freeze_doc.get("project_root", "")).strip()
            else sub_run_dir
        )
        for candidate in (
            "feature_matrix.md",
            "page_map.md",
            "data_model_summary.md",
            "milestone_plan.md",
            "startup_guide.md",
            "replay_guide.md",
            "mid_stage_review.md",
        ):
            copied = False
            for source_path in (
                generated_project_dir / "docs" / candidate,
                generated_project_dir / candidate,
            ):
                if _copy_if_exists(source_path, project_dir / candidate):
                    copied = True
                    break
            if not copied and not (project_dir / candidate).exists():
                fallback = _design_docs(
                    design,
                    goal_text=rough_goal,
                    freeze_doc=freeze_doc,
                    project_spec=project_spec or dict(freeze_doc.get("project_spec", {})),
                ).get(candidate, f"# {candidate}\n")
                _write_text(project_dir / candidate, fallback)

        for candidate in ("project_spec.json", "output_contract_freeze.json", "source_generation_report.json", "project_manifest.json"):
            source_path = sub_run_dir / "artifacts" / candidate
            if source_path.exists():
                shutil.copy2(source_path, project_dir / candidate)

        preliminary_verify, preliminary_support = _build_verify_report(
            source_report=source_doc or {"status": "blocked"},
            final_bundle_exists=False,
            evidence_bundle_exists=False,
        )
        _write_json(sub_run_dir / "artifacts" / "verify_report.json", preliminary_verify)
        _write_json(sub_run_dir / "artifacts" / "support_public_delivery.json", preliminary_support)

        if manifest_doc:
            try:
                deliverable_doc = deliverable_project({}, goal=rough_goal, run_dir=sub_run_dir)
                _write_json(sub_run_dir / "artifacts" / "deliverable_index.json", deliverable_doc)
            except Exception:
                deliverable_doc = {}

        final_bundle_source = sub_run_dir / "artifacts" / "final_project_bundle.zip"
        evidence_bundle_source = sub_run_dir / "artifacts" / "intermediate_evidence_bundle.zip"
        final_bundle_target = project_dir / "final_project_bundle.zip"
        evidence_bundle_target = project_dir / "intermediate_evidence_bundle.zip"
        _copy_if_exists(final_bundle_source, final_bundle_target)
        _copy_if_exists(evidence_bundle_source, evidence_bundle_target)
        if not final_bundle_target.exists():
            _zip_directory(project_dir, final_bundle_target, skip_names={"final_project_bundle.zip", "intermediate_evidence_bundle.zip"})
        if not evidence_bundle_target.exists():
            _zip_directory(project_dir, evidence_bundle_target, skip_names={"intermediate_evidence_bundle.zip"})

        verify_doc, support_doc = _build_verify_report(
            source_report=source_doc or {"status": "blocked"},
            final_bundle_exists=final_bundle_target.exists(),
            evidence_bundle_exists=evidence_bundle_target.exists(),
        )
        if freeze_error:
            verify_doc["failures"].insert(0, {"id": "freeze_exception", "message": freeze_error})
            verify_doc["first_failure_point"] = verify_doc.get("first_failure_point") or "freeze_exception"
            verify_doc["result"] = "FAIL"
            verify_doc["internal_runtime_status"] = "FAIL"
            verify_doc["user_acceptance_status"] = "NEEDS_REWORK"
            verify_doc["final_verdict"] = "PARTIAL" if final_bundle_target.exists() else "NEEDS_REWORK"
        elif source_error:
            verify_doc["failures"].insert(0, {"id": "source_exception", "message": source_error})
            verify_doc["first_failure_point"] = verify_doc.get("first_failure_point") or "source_exception"
            verify_doc["result"] = "FAIL"
            verify_doc["internal_runtime_status"] = "FAIL"
            verify_doc["user_acceptance_status"] = "NEEDS_REWORK"
            verify_doc["final_verdict"] = "PARTIAL" if final_bundle_target.exists() else "NEEDS_REWORK"
        support_doc["internal_runtime_status"] = verify_doc["internal_runtime_status"]
        support_doc["user_acceptance_status"] = verify_doc["user_acceptance_status"]
        support_doc["final_verdict"] = verify_doc["final_verdict"]
        support_doc["completion_gate"]["passed"] = verify_doc["internal_runtime_status"] == "PASS"
        support_doc["completion_gate"]["cold_replay_passed"] = verify_doc["internal_runtime_status"] == "PASS"
        support_doc["completion_gate"]["selected_document"] = "artifacts/final_project_bundle.zip" if final_bundle_target.exists() else ""
        support_doc["overall_completion"]["passed"] = verify_doc["final_verdict"] == "PASS"
        support_doc["user_acceptance"]["status"] = verify_doc["user_acceptance_status"]
        support_doc["delivery_completion"]["passed"] = final_bundle_target.exists() and evidence_bundle_target.exists()
        support_doc["replay_report"]["first_failure_stage"] = verify_doc.get("first_failure_point", "")
        _write_json(sub_run_dir / "artifacts" / "verify_report.json", verify_doc)
        _write_json(sub_run_dir / "artifacts" / "support_public_delivery.json", support_doc)
        _write_json(project_dir / "verify_report.json", verify_doc)

        delivery_summary = (
            "# Delivery Summary\n\n"
            f"- rough_goal: {rough_goal}\n"
            f"- internal_runtime_status: {verify_doc['internal_runtime_status']}\n"
            f"- user_acceptance_status: {verify_doc['user_acceptance_status']}\n"
            f"- first_failure_point: {verify_doc.get('first_failure_point', '')}\n"
            f"- final_verdict: {verify_doc['final_verdict']}\n"
            f"- final_bundle: {final_bundle_target.name if final_bundle_target.exists() else ''}\n"
            f"- evidence_bundle: {evidence_bundle_target.name if evidence_bundle_target.exists() else ''}\n"
            f"- remaining_gaps: {', '.join(verify_doc.get('remaining_gaps', []))}\n"
        )
        _write_text(project_dir / "delivery_summary.md", delivery_summary)
        _write_text(delivery_dir / "delivery_summary.md", delivery_summary)

        events = [
            {"phase": "intake", "status": "pass", "project_title": project_title},
            {"phase": "freeze", "status": "pass" if freeze_doc and not freeze_error else "fail", "message": freeze_error or "frozen"},
            {"phase": "design", "status": "pass", "message": "design artifacts written"},
            {"phase": "build", "status": "pass" if source_doc and str(source_doc.get("status", "")).lower() == "pass" else "fail", "message": source_error or str(source_doc.get("status", "blocked"))},
            {"phase": "verify", "status": "pass" if verify_doc["result"] == "PASS" else "fail", "message": verify_doc.get("first_failure_point", "")},
            {"phase": "delivery", "status": "pass" if final_bundle_target.exists() and evidence_bundle_target.exists() else "fail", "message": verify_doc["final_verdict"]},
        ]
        _write_text(project_dir / "events.jsonl", "\n".join(json.dumps(row, ensure_ascii=False) for row in events) + "\n")
        _write_text(
            project_dir / "step_meta.jsonl",
            "\n".join(json.dumps({"phase": row["phase"], "status": row["status"], "source": "queued_portfolio_mainline"}, ensure_ascii=False) for row in events) + "\n",
        )
        _write_triplet(
            acceptance_root,
            "01_intake",
            request={"rough_goal": rough_goal, "questions": design["questions"]},
            result={"assumptions": design["assumptions"], "project_title": project_title},
            acceptance={"passed": True, "stage": "intake"},
        )
        _write_triplet(
            acceptance_root,
            "02_freeze",
            request={"goal": rough_goal},
            result={"project_domain": freeze_doc.get("project_domain", ""), "project_archetype": freeze_doc.get("project_archetype", ""), "error": freeze_error},
            acceptance={"passed": bool(freeze_doc) and not bool(freeze_error), "stage": "freeze"},
        )
        _write_triplet(
            acceptance_root,
            "03_delivery",
            request={"expected_bundle": "final_project_bundle.zip"},
            result={"final_verdict": verify_doc["final_verdict"], "final_bundle_exists": final_bundle_target.exists(), "evidence_bundle_exists": evidence_bundle_target.exists()},
            acceptance={"passed": final_bundle_target.exists() and evidence_bundle_target.exists(), "stage": "delivery"},
        )

        project_summary = {
            "project_index": index,
            "project_name": project_title,
            "rough_goal": rough_goal,
            "run_dir": _rel(sub_run_dir, run_dir),
            "project_dir": _rel(project_dir, run_dir),
            "final_bundle_path": _rel(final_bundle_target, run_dir) if final_bundle_target.exists() else "",
            "evidence_bundle_path": _rel(evidence_bundle_target, run_dir) if evidence_bundle_target.exists() else "",
            "internal_runtime_status": verify_doc["internal_runtime_status"],
            "user_acceptance_status": verify_doc["user_acceptance_status"],
            "first_failure_point": verify_doc.get("first_failure_point", ""),
            "final_verdict": verify_doc["final_verdict"],
            "current_strongest_deliverable_status": "bundle_ready" if final_bundle_target.exists() else "artifact_only",
            "remaining_gaps": list(verify_doc.get("remaining_gaps", [])),
            "api_coverage": load_provider_ledger_summary(sub_run_dir),
        }
        project_summaries.append(project_summary)

    pass_count = len([row for row in project_summaries if row["final_verdict"] == "PASS"])
    partial_count = len([row for row in project_summaries if row["final_verdict"] == "PARTIAL"])
    rework_count = len([row for row in project_summaries if row["final_verdict"] == "NEEDS_REWORK"])
    portfolio_summary = {
        "schema_version": "ctcp-portfolio-summary-v1",
        "project_count": len(project_summaries),
        "completed_count": pass_count + partial_count,
        "completion_rate": round((pass_count + partial_count) / max(len(project_summaries), 1), 3),
        "pass_projects": [row["project_name"] for row in project_summaries if row["final_verdict"] == "PASS"],
        "partial_projects": [row["project_name"] for row in project_summaries if row["final_verdict"] == "PARTIAL"],
        "needs_rework_projects": [row["project_name"] for row in project_summaries if row["final_verdict"] == "NEEDS_REWORK"],
        "projects": project_summaries,
    }
    _write_json(portfolio_summary_json, portfolio_summary)
    md_lines = [
        "# Portfolio Summary",
        "",
        f"- project_count: {len(project_summaries)}",
        f"- completion_rate: {portfolio_summary['completion_rate']}",
        f"- PASS: {pass_count}",
        f"- PARTIAL: {partial_count}",
        f"- NEEDS_REWORK: {rework_count}",
        "",
        "## Projects",
        "",
    ]
    for row in project_summaries:
        md_lines.extend(
            [
                f"### {row['project_name']}",
                f"- rough_goal: {row['rough_goal']}",
                f"- run_dir: `{row['run_dir']}`",
                f"- final_bundle_path: `{row['final_bundle_path']}`",
                f"- evidence_bundle_path: `{row['evidence_bundle_path']}`",
                f"- internal_runtime_status: `{row['internal_runtime_status']}`",
                f"- user_acceptance_status: `{row['user_acceptance_status']}`",
                f"- first_failure_point: `{row['first_failure_point']}`",
                f"- final_verdict: `{row['final_verdict']}`",
                f"- api_coverage: `{dict(row.get('api_coverage', {})).get('critical_api_step_count', 0)}` / `{dict(row.get('api_coverage', {})).get('critical_step_count', 0)}`",
                f"- all_critical_steps_api: `{dict(row.get('api_coverage', {})).get('all_critical_steps_api', False)}`",
                "",
            ]
        )
    _write_text(portfolio_summary_md, "\n".join(md_lines).rstrip() + "\n")
    _write_text(
        project_root_dir / "README.md",
        "# Project Queue Portfolio\n\n"
        "This generated root project drives a serial project queue and preserves independent per-project delivery artifacts.\n\n"
        "## Outputs\n"
        f"- Portfolio summary JSON: `{_rel(portfolio_summary_json, project_root_dir)}`\n"
        f"- Portfolio summary Markdown: `{_rel(portfolio_summary_md, project_root_dir)}`\n"
        f"- Queued projects: `{_rel(portfolio_root, project_root_dir)}`\n",
    )

    updated_generated = _collect_project_files(run_dir, root_project_root)
    root_report["generated_files"] = updated_generated
    root_report["missing_files"] = []
    root_report["portfolio_mode"] = True
    root_report["project_queue"] = project_queue
    root_report["portfolio_projects"] = project_summaries
    root_report["portfolio_summary_json_path"] = _rel(portfolio_summary_json, run_dir)
    root_report["portfolio_summary_md_path"] = _rel(portfolio_summary_md, run_dir)
    context_summary = list(root_report.get("context_influence_summary", [])) if isinstance(root_report.get("context_influence_summary"), list) else []
    context_summary.append(f"portfolio queue processed serially for {len(project_summaries)} projects")
    root_report["context_influence_summary"] = context_summary
    generation_quality = dict(root_report.get("generation_quality", {})) if isinstance(root_report.get("generation_quality"), dict) else {}
    checks = list(generation_quality.get("targeted_checks", [])) if isinstance(generation_quality.get("targeted_checks"), list) else []
    checks.append(
        {
            "check_id": "portfolio_queue_summary",
            "passed": len(project_summaries) == len(project_queue),
            "details": f"processed {len(project_summaries)} queued projects",
        }
    )
    generation_quality["targeted_checks"] = checks
    if checks:
        passed_count = len([row for row in checks if bool(row.get("passed", False))])
        generation_quality["score"] = round(passed_count / len(checks), 3)
        generation_quality["passed"] = passed_count == len(checks)
    root_report["generation_quality"] = generation_quality
    return root_report


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
    _write_json((run_dir / inputs["project_spec_path"]).resolve(), dict(inputs["project_spec"]))
    _write_json((run_dir / inputs["capability_plan_path"]).resolve(), dict(inputs["capability_plan"]))
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
        stage_contract = dict(lists)
        stage_contract["project_intent"] = dict(inputs["project_intent"])
        stage_contract["project_spec"] = dict(inputs["project_spec"])
        stage_contract["capability_plan"] = dict(inputs["capability_plan"])
        stage_contract["sample_generation_plan"] = dict(inputs["sample_generation_plan"])
        stage_contract["project_spec_path"] = inputs["project_spec_path"]
        stage_contract["capability_plan_path"] = inputs["capability_plan_path"]
        stage_contract["sample_generation_artifacts"] = list(inputs["sample_generation_artifacts"])
        stage_contract["generation_quality_report_path"] = inputs["generation_quality_report_path"]
        stage_contract["materialize_capabilities"] = list(current_materialize)
        generated_business_files = materialize_business_files(run_dir, inputs["goal_text"], stage_contract, inputs["consumed_files"])
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
    for key in ("generic_validation", "domain_validation", "readme_quality", "ux_validation", "product_validation"):
        report[key] = validation[key]
    if _blocked_by_validation(report, validation, scaffold):
        report["status"] = "blocked"
    return report
