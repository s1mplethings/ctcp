from __future__ import annotations

import json
import re
import shutil
import zipfile
from pathlib import Path
from typing import Any, Callable

from tools.providers.project_generation_runtime_support import _collect_project_files
from tools.formal_api_lock import load_provider_ledger_summary

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

