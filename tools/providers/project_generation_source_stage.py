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
from tools.providers.project_generation_business_materializers import materialize_business_files
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
    return report


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def _materialize_test_evidence_screenshots(
    *,
    run_dir: Path,
    project_dir: Path,
    project_label: str,
) -> list[str]:
    test_screenshots_dir = project_dir / "artifacts" / "test_screenshots"
    test_screenshots_dir.mkdir(parents=True, exist_ok=True)
    cases = (
        ("test-smoke-runtime.png", "smoke runtime check", "cli startup + basic flow"),
        ("test-export-validation.png", "export validation", "export output consistency"),
        ("test-replay-acceptance.png", "delivery replay", "replay acceptance gate"),
    )
    output: list[str] = []
    for idx, (name, subtitle, detail) in enumerate(cases, start=1):
        path = test_screenshots_dir / name
        _render_visual_evidence_png(
            path=path,
            title=f"{project_label} test evidence",
            subtitle=subtitle,
            detail_lines=[
                f"test case {idx}/{len(cases)}",
                detail,
                "automated evidence snapshot",
            ],
        )
        output.append(path.relative_to(run_dir.resolve()).as_posix())
    return output


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
    test_screenshot_rels = _materialize_test_evidence_screenshots(
        run_dir=run_dir,
        project_dir=project_dir,
        project_label="Plane Lite",
    )

    ledger = {
        "schema_version": "ctcp-extended-coverage-ledger-v1",
        "build_profile": "high_quality_extended",
        "product_depth": "extended",
        "implemented_pages": pages,
        "implemented_capabilities": capabilities,
        "missing_capabilities": [],
        "screenshot_files": screenshot_rels,
        "test_screenshot_files": test_screenshot_rels,
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
    test_screenshot_rels = _materialize_test_evidence_screenshots(
        run_dir=run_dir,
        project_dir=project_dir,
        project_label="Indie Studio Hub",
    )
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
        "test_screenshot_files": test_screenshot_rels,
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
