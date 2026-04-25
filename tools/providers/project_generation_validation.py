from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from contracts.schemas.project_intent import ProjectIntent
from tools.providers.project_generation_domain_contract import (
    contamination_hits,
    preview_keywords,
    readme_required_sections,
)

_SOURCE_SCAN_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css"}
_HIGH_INTERACTION_GROUP_RULES: dict[str, tuple[str, ...]] = {
    "image_workspace": (
        "image folder",
        "file browser",
        "image list",
        "thumbnail",
        "workspace",
        ".jpg",
        ".jpeg",
        ".png",
    ),
    "annotation_canvas": (
        "annotation",
        "annotate",
        "bounding box",
        "bbox",
        "keypoints",
        "canvas",
    ),
    "interactive_editing": (
        "drag",
        "move",
        "resize",
        "delete",
        "select",
        "undo",
        "redo",
    ),
    "state_persistence": (
        "autosave",
        "save state",
        "restore state",
        "project state",
        "persistence",
        "persist",
    ),
    "standard_export": (
        "yolo",
        "coco",
        "annotation format",
        "standard annotation",
    ),
    "review_workbench": (
        "review workflow",
        "reviewer",
        "workbench",
        "desktop-style tool",
    ),
}
_HIGH_INTERACTION_CAPABILITY_RULES: dict[str, tuple[str, ...]] = {
    "image_loading": ("image folder", "load image", "image list", "thumbnail", ".jpg", ".jpeg", ".png"),
    "image_navigation": ("previous image", "next image", "image index", "thumbnail list", "current image"),
    "bbox_model": ("bounding box", "bbox", "annotation box", "x1", "y1", "x2", "y2"),
    "bbox_create": ("create box", "new bbox", "draw box", "mouse drag", "canvas"),
    "bbox_move": ("move box", "drag box", "reposition", "move annotation"),
    "bbox_resize": ("resize box", "resize annotation", "handle drag"),
    "bbox_delete": ("delete box", "remove box", "delete annotation"),
    "state_persistence": ("autosave", "save state", "restore state", "project state", "load state", "persist"),
    "standard_export": ("yolo", "coco", "annotation format", "standard annotation"),
}
_README_SECTION_TOKENS: dict[str, tuple[str, ...]] = {
    "what_this_project_is": ("## what this project is", "## project overview", "## 项目是什么", "## 项目概览"),
    "implemented": ("## implemented", "## what is implemented", "## 已实现", "## 当前已实现"),
    "not_implemented": ("## not implemented", "## not yet implemented", "## 未实现", "## 当前未实现"),
    "how_to_run": ("## how to run", "## run", "## quick start", "## usage", "## 如何运行", "## 运行方式"),
    "sample_data": ("## sample data", "## sample project", "## example project", "## 示例数据", "## 示例项目"),
    "directory_map": ("## directory map", "## project layout", "## directory guide", "## 目录说明", "## 主要目录"),
    "limitations": ("## limitations", "## current limitations", "## next steps", "## 限制", "## 下一步建议"),
}
_NARRATIVE_STRUCTURE_RULES: dict[str, tuple[str, ...]] = {
    "editor_entry": ("editor workspace", "workspace panel", "authoring", "project editor", "编辑器", "工作区"),
    "narrative_graph": ("scene graph", "branch", "choice", "narrative node", "route", "剧情图", "分支", "选项"),
    "asset_model": ("character", "cast", "asset", "background", "stage", "角色", "资产", "背景"),
    "preview_export": ("preview", "pack", "export", "bundle", "导出", "预览", "打包"),
}
_TEAM_TASK_PM_RULES: dict[str, tuple[str, ...]] = {
    "board": ("kanban", "build_kanban_board", "kanban_board", "board"),
    "task_crud": ("create_task", "edit_task_fields", "move_task_status", "task_detail_drawer"),
    "filters": ("filter_tasks", "status", "assignee", "priority", "labels"),
    "activity": ("activity_feed", "comment_on_task", "add_activity", "activity"),
}
_INDIE_STUDIO_HUB_RULES: dict[str, tuple[str, ...]] = {
    "task_management": ("task_board", "task_list", "task_detail", "create_task", "move_task_status"),
    "asset_management": ("asset_library", "asset_detail", "create_asset", "asset_type", "replacement"),
    "bug_tracking": ("bug_tracker", "report_bug", "severity", "repro_steps", "version"),
    "build_release": ("build_release_center", "release_summary", "build_records", "current_version_status", "release_checklist"),
    "docs_delivery": ("docs_center", "feature matrix", "page map", "startup guide", "replay guide"),
}


def read_frontend_request(run_dir: Path | None) -> dict[str, Any]:
    if run_dir is None:
        return {}
    path = run_dir / "artifacts" / "frontend_request.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def resolve_project_intent(goal: str, *, run_dir: Path | None, src: dict[str, Any]) -> dict[str, Any]:
    direct = src.get("project_intent")
    if isinstance(direct, dict):
        return ProjectIntent.from_payload(direct, user_goal=goal).to_payload()
    request = read_frontend_request(run_dir)
    from_request = request.get("project_intent")
    if isinstance(from_request, dict):
        return ProjectIntent.from_payload(from_request, user_goal=goal).to_payload()
    constraints = src.get("constraints") if isinstance(src.get("constraints"), dict) else request.get("constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    return ProjectIntent.minimal_from_goal(goal, constraints).to_payload()


def resolve_project_spec(goal: str, *, run_dir: Path | None, src: dict[str, Any], project_intent: dict[str, Any]) -> dict[str, Any]:
    direct = src.get("project_spec")
    if isinstance(direct, dict) and direct:
        return dict(direct)
    request = read_frontend_request(run_dir)
    from_request = request.get("project_spec")
    if isinstance(from_request, dict) and from_request:
        return dict(from_request)
    intent = ProjectIntent.from_payload(project_intent, user_goal=goal)
    constraints = src.get("constraints") if isinstance(src.get("constraints"), dict) else request.get("constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    return {
        "schema_version": "ctcp-project-spec-v1",
        "goal_summary": intent.goal_summary,
        "target_user": intent.target_user,
        "problem_to_solve": intent.problem_to_solve,
        "mvp_scope": list(intent.mvp_scope),
        "required_inputs": list(intent.required_inputs),
        "required_outputs": list(intent.required_outputs),
        "hard_constraints": list(intent.hard_constraints),
        "assumptions": list(intent.assumptions),
        "open_questions": list(intent.open_questions),
        "acceptance_criteria": list(intent.acceptance_criteria),
        "constraint_snapshot": dict(constraints),
    }


def pipeline_contract(*, project_root: str, startup_entrypoint: str, startup_readme: str, business_files: list[str], acceptance_files: list[str]) -> dict[str, Any]:
    core_feature_files = sorted(set(business_files))
    return {
        "schema_version": "ctcp-project-generation-pipeline-v1",
        "stages": [
            {"name": "project_intent", "artifact": "project_intent", "status": "ready"},
            {"name": "spec", "artifact": "artifacts/project_spec.json", "status": "ready"},
            {"name": "capability_plan", "artifact": "artifacts/capability_plan.json", "status": "ready"},
            {"name": "sample_generation_plan", "artifact": "artifacts/sample_generation", "status": "ready"},
            {"name": "scaffold", "artifact": "project_root", "status": "planned", "project_root": project_root},
            {"name": "core_feature_implementation", "artifact": "core_feature_files", "status": "planned", "core_feature_files": core_feature_files},
            {"name": "refinement", "artifact": "artifacts/generation_quality_report.json", "status": "planned"},
            {"name": "smoke_run", "artifact": "startup_entrypoint", "status": "planned", "startup_entrypoint": startup_entrypoint},
            {"name": "demo_evidence", "artifact": "demo_evidence", "status": "planned"},
            {"name": "delivery_package", "artifact": "acceptance_files", "status": "planned", "acceptance_files": list(acceptance_files), "startup_readme": startup_readme},
        ],
    }


def _looks_placeholder_content(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except Exception:
        return False
    compact = text.strip()
    if len(compact) <= 240 and any(marker in compact for marker in ("todo", "placeholder", "coming soon", "stub", "not implemented")):
        return True
    lines = [line.strip() for line in compact.splitlines() if line.strip()]
    return len(lines) <= 4 and any(line == "pass" for line in lines)


def _python_syntax_validation(*, run_dir: Path, generated_business_files: list[str], startup_entrypoint: str) -> dict[str, Any]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in [startup_entrypoint] + list(generated_business_files):
        rel = str(raw or "").strip().replace("\\", "/")
        if not rel or rel in seen or not rel.endswith(".py"):
            continue
        seen.add(rel)
        candidates.append(rel)
    checked: list[str] = []
    syntax_errors: list[dict[str, Any]] = []
    for rel in candidates:
        path = (run_dir / rel).resolve()
        if not path.exists():
            continue
        checked.append(rel)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            ast.parse(source, filename=rel)
        except SyntaxError as exc:
            syntax_errors.append(
                {
                    "path": rel,
                    "message": str(exc.msg or "syntax error"),
                    "line": int(exc.lineno or 0),
                    "offset": int(exc.offset or 0),
                }
            )
    return {
        "checked_files": checked,
        "syntax_errors": syntax_errors,
        "passed": not syntax_errors,
    }


def generic_validation(
    *,
    run_dir: Path,
    startup_entrypoint: str,
    startup_readme: str,
    generated_business_files: list[str],
    behavior_probe: dict[str, Any],
    export_probe: dict[str, Any],
    acceptance_files: list[str],
) -> dict[str, Any]:
    entry = (run_dir / startup_entrypoint).resolve()
    readme = (run_dir / startup_readme).resolve()
    readme_text = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
    entry_name = Path(startup_entrypoint).name.lower()
    placeholder_hits: list[str] = []
    for rel in generated_business_files:
        candidate = (run_dir / rel).resolve()
        if candidate.exists() and _looks_placeholder_content(candidate):
            placeholder_hits.append(rel)
    readme_lower = readme_text.lower()
    readme_has_start_signal = (
        "python" in readme_lower
        or "启动" in readme_text
        or "run " in readme_lower
        or entry_name in readme_lower
        or "quick start" in readme_lower
        or "usage" in readme_lower
    )
    readme_has_start = bool(readme.exists()) and (readme_has_start_signal or bool(readme_text.strip()))
    smoke_passed = int(dict(behavior_probe).get("rc", 1)) == 0 and int(dict(export_probe).get("rc", 1)) == 0
    python_syntax = _python_syntax_validation(
        run_dir=run_dir,
        generated_business_files=generated_business_files,
        startup_entrypoint=startup_entrypoint,
    )
    return {
        "passed": bool(entry.exists())
        and bool(readme.exists())
        and readme_has_start
        and bool(generated_business_files)
        and smoke_passed
        and not placeholder_hits
        and bool(python_syntax.get("passed", False)),
        "has_runnable_entrypoint": bool(entry.exists()),
        "readme_startup_ready": readme_has_start,
        "core_user_flow": [
            "start the generated project from README",
            "execute one smoke export or equivalent core path",
        ],
        "core_feature_files": list(generated_business_files),
        "placeholder_hits": placeholder_hits,
        "python_syntax": python_syntax,
        "delivery_package": list(acceptance_files),
        "smoke_run": {
            "startup_probe": dict(behavior_probe),
            "export_probe": dict(export_probe),
            "passed": smoke_passed,
        },
    }


def readme_quality_validation(
    *,
    run_dir: Path,
    startup_readme: str,
    goal: str,
    project_domain: str,
) -> dict[str, Any]:
    readme_path = (run_dir / startup_readme).resolve()
    required_sections = readme_required_sections(project_domain)
    if not readme_path.exists():
        return {
            "passed": False,
            "path": startup_readme,
            "required_sections": required_sections,
            "present_sections": [],
            "missing_sections": list(required_sections),
            "escaped_literal_hits": [],
            "placeholder_hits": [],
            "goal_dump_detected": False,
            "reasons": ["README missing"],
        }

    text = readme_path.read_text(encoding="utf-8", errors="replace")
    text_lower = text.lower()
    escaped_literal_hits = [token for token in ("\\n", "\\t", "\\r") if token in text]
    placeholder_hits = [token for token in ("todo", "coming soon", "not implemented yet", "lorem ipsum") if token in text_lower]
    present_sections: list[str] = []
    missing_sections: list[str] = []
    for section in required_sections:
        tokens = _README_SECTION_TOKENS.get(section, ())
        if any(token in text_lower for token in tokens):
            present_sections.append(section)
        else:
            missing_sections.append(section)

    goal_lines = [line.strip() for line in str(goal or "").splitlines() if line.strip()]
    normalized_goal = " ".join(goal_lines).strip().lower()
    body_lines = [line.strip() for line in text.splitlines() if line.strip()]
    content_window = " ".join(body_lines[:6]).lower()
    heading_count = sum(1 for line in body_lines if line.startswith("#"))
    goal_dump_detected = bool(normalized_goal) and normalized_goal in content_window and heading_count < 4
    reasons: list[str] = []
    if missing_sections:
        reasons.append(f"README missing sections: {', '.join(missing_sections)}")
    if escaped_literal_hits:
        reasons.append(f"README contains escaped literals: {', '.join(escaped_literal_hits)}")
    if placeholder_hits:
        reasons.append(f"README contains placeholder text: {', '.join(sorted(set(placeholder_hits)))}")
    if goal_dump_detected:
        reasons.append("README body still looks like a raw goal dump")
    return {
        "passed": not reasons,
        "path": startup_readme,
        "required_sections": required_sections,
        "present_sections": present_sections,
        "missing_sections": missing_sections,
        "escaped_literal_hits": escaped_literal_hits,
        "placeholder_hits": sorted(set(placeholder_hits)),
        "goal_dump_detected": goal_dump_detected,
        "reasons": reasons,
    }


def _normalized_paths(rows: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in rows:
        value = str(raw or "").strip().replace("\\", "/")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _intent_signal(goal: str, project_intent: dict[str, Any] | None, project_spec: dict[str, Any] | None) -> str:
    parts: list[str] = [str(goal or "").strip()]
    for doc in (project_intent or {}, project_spec or {}):
        if not isinstance(doc, dict):
            continue
        for key, value in doc.items():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(item).strip() for item in value if str(item).strip())
    return "\n".join(part for part in parts if part)


def classify_product_profile(*, goal: str, project_intent: dict[str, Any] | None, project_spec: dict[str, Any] | None) -> dict[str, Any]:
    signal = _intent_signal(goal, project_intent, project_spec).lower()
    detected_groups: list[str] = []
    matched_keywords: dict[str, list[str]] = {}
    for group, keywords in _HIGH_INTERACTION_GROUP_RULES.items():
        hits = sorted({keyword for keyword in keywords if keyword.lower() in signal})
        if hits:
            detected_groups.append(group)
            matched_keywords[group] = hits
    requires_gate = (
        len(detected_groups) >= 3
        and any(group in detected_groups for group in ("annotation_canvas", "interactive_editing", "standard_export"))
    )
    profile = "high_interaction_software" if requires_gate else "standard"
    reasons = [f"{group}: {', '.join(matched_keywords[group][:4])}" for group in detected_groups]
    return {
        "profile": profile,
        "required": requires_gate,
        "detected_groups": detected_groups,
        "matched_keywords": matched_keywords,
        "reasons": reasons,
    }


def _scan_source_texts(*, run_dir: Path, rel_paths: list[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for rel in rel_paths:
        normalized = str(rel or "").strip().replace("\\", "/")
        if not normalized:
            continue
        path = (run_dir / normalized).resolve()
        if not path.exists() or path.suffix.lower() not in _SOURCE_SCAN_EXTS:
            continue
        try:
            texts[normalized] = path.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue
    return texts


def _capability_hits(*, source_texts: dict[str, str], keywords: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    seen: set[str] = set()
    for rel, text in source_texts.items():
        if any(keyword.lower() in text for keyword in keywords):
            if rel not in seen:
                seen.add(rel)
                hits.append(rel)
    return hits


def product_validation(
    *,
    goal: str,
    project_intent: dict[str, Any],
    project_spec: dict[str, Any],
    project_type: str,
    project_archetype: str,
    startup_entrypoint: str,
    generated_files: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    if str(project_type or "").strip() == "indie_studio_hub" or str(project_archetype or "").strip() == "indie_studio_hub_web":
        source_texts = _scan_source_texts(run_dir=run_dir, rel_paths=generated_files)
        capability_hits = {
            name: _capability_hits(source_texts=source_texts, keywords=keywords)
            for name, keywords in _INDIE_STUDIO_HUB_RULES.items()
        }
        missing = [f"indie studio hub capability missing: {name}" for name, hits in capability_hits.items() if not hits]
        if str(project_archetype or "").strip() in {"generic_copilot", "web_service", "team_task_pm_web"}:
            missing.append("Indie Studio Hub request degraded to a narrower scaffold")
        if not str(startup_entrypoint or "").strip():
            missing.append("startup entrypoint missing")
        return {
            "profile": "indie_studio_hub",
            "required": True,
            "passed": not missing,
            "checks": [f"indie studio hub capability detected: {name}" for name, hits in capability_hits.items() if hits],
            "missing": missing,
            "reasons": [],
            "fallback_detected": bool(str(project_archetype or "").strip() in {"generic_copilot", "web_service", "team_task_pm_web"}),
            "detected_groups": sorted(capability_hits.keys()),
            "evidence": capability_hits,
        }
    if str(project_type or "").strip() == "team_task_pm" or str(project_archetype or "").strip() == "team_task_pm_web":
        source_texts = _scan_source_texts(run_dir=run_dir, rel_paths=generated_files)
        capability_hits = {
            name: _capability_hits(source_texts=source_texts, keywords=keywords)
            for name, keywords in _TEAM_TASK_PM_RULES.items()
        }
        missing = [f"team task PM capability missing: {name}" for name, hits in capability_hits.items() if not hits]
        if str(project_archetype or "").strip() in {"generic_copilot", "web_service"}:
            missing.append("Plane-lite/team task PM request degraded to generic/web_service scaffold")
        if not str(startup_entrypoint or "").strip():
            missing.append("startup entrypoint missing")
        return {
            "profile": "team_task_pm",
            "required": True,
            "passed": not missing,
            "checks": [f"team task PM capability detected: {name}" for name, hits in capability_hits.items() if hits],
            "missing": missing,
            "reasons": [],
            "fallback_detected": bool(str(project_archetype or "").strip() in {"generic_copilot", "web_service"}),
            "detected_groups": sorted(capability_hits.keys()),
            "evidence": capability_hits,
        }

    profile = classify_product_profile(goal=goal, project_intent=project_intent, project_spec=project_spec)
    if not bool(profile.get("required", False)):
        return {
            "profile": str(profile.get("profile", "standard")),
            "required": False,
            "passed": True,
            "checks": ["product capability gate not required for this task profile"],
            "missing": [],
            "reasons": list(profile.get("reasons", [])),
            "fallback_detected": False,
            "detected_groups": list(profile.get("detected_groups", [])),
            "evidence": {},
        }

    source_texts = _scan_source_texts(run_dir=run_dir, rel_paths=generated_files)
    capability_hits = {
        name: _capability_hits(source_texts=source_texts, keywords=keywords)
        for name, keywords in _HIGH_INTERACTION_CAPABILITY_RULES.items()
    }
    edit_subchecks = {
        "move": bool(capability_hits["bbox_move"]),
        "resize": bool(capability_hits["bbox_resize"]),
        "delete": bool(capability_hits["bbox_delete"]),
    }
    generic_fallback = str(project_type or "").strip() == "generic_copilot" and str(project_archetype or "").strip() == "generic_copilot"
    checks: list[str] = []
    missing: list[str] = []
    if capability_hits["image_loading"]:
        checks.append("image loading/workspace capability detected")
    else:
        missing.append("image loading/workspace capability missing")
    if capability_hits["image_navigation"]:
        checks.append("image navigation capability detected")
    else:
        missing.append("image navigation capability missing")
    if capability_hits["bbox_model"]:
        checks.append("bbox data model detected")
    else:
        missing.append("bbox data model missing")
    if capability_hits["bbox_create"]:
        checks.append("bbox creation capability detected")
    else:
        missing.append("bbox creation capability missing")
    edit_hits = sum(1 for passed in edit_subchecks.values() if passed)
    if edit_hits >= 2:
        checks.append("bbox editing capability detected")
    else:
        missing.append("bbox editing capability missing")
    if capability_hits["state_persistence"]:
        checks.append("save/restore state capability detected")
    else:
        missing.append("save/restore state capability missing")
    if capability_hits["standard_export"]:
        checks.append("standard annotation export capability detected")
    else:
        missing.append("standard annotation export capability missing")
    reasons = list(profile.get("reasons", []))
    if generic_fallback:
        reasons.append("high-interaction request degraded to generic_copilot/generic fallback")
    if not str(startup_entrypoint or "").strip():
        missing.append("startup entrypoint missing")
    evidence = {
        "image_loading": capability_hits["image_loading"],
        "image_navigation": capability_hits["image_navigation"],
        "bbox_model": capability_hits["bbox_model"],
        "bbox_create": capability_hits["bbox_create"],
        "bbox_move": capability_hits["bbox_move"],
        "bbox_resize": capability_hits["bbox_resize"],
        "bbox_delete": capability_hits["bbox_delete"],
        "state_persistence": capability_hits["state_persistence"],
        "standard_export": capability_hits["standard_export"],
    }
    return {
        "profile": str(profile.get("profile", "high_interaction_software")),
        "required": True,
        "passed": (not generic_fallback) and (not missing),
        "checks": checks,
        "missing": missing,
        "reasons": reasons,
        "fallback_detected": generic_fallback,
        "detected_groups": list(profile.get("detected_groups", [])),
        "evidence": evidence,
    }


def _matching_suffix(rows: list[str], suffix: str) -> str:
    return next((row for row in rows if row.endswith(suffix)), "")


def _validate_required_suffixes(rows: list[str], suffixes: list[str], *, run_dir: Path) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    missing: list[str] = []
    for suffix in suffixes:
        matched = _matching_suffix(rows, suffix)
        if not matched:
            missing.append(suffix)
            continue
        if not (run_dir / matched).resolve().exists():
            missing.append(matched)
            continue
        checks.append(f"generated {suffix}")
    return checks, missing


def _readme_has_tokens(*, run_dir: Path, startup_readme: str, tokens: tuple[str, ...]) -> bool:
    readme_path = (run_dir / startup_readme).resolve()
    if not readme_path.exists():
        return False
    text = readme_path.read_text(encoding="utf-8", errors="replace").lower()
    return any(token.lower() in text for token in tokens)


def _existing_paths(run_dir: Path, rows: list[str]) -> list[str]:
    return [rel for rel in _normalized_paths(rows) if (run_dir / rel).resolve().exists()]


def _scan_text_bundle(*, run_dir: Path, rel_paths: list[str]) -> dict[str, str]:
    texts: dict[str, str] = {}
    for rel in _normalized_paths(rel_paths):
        path = (run_dir / rel).resolve()
        if not path.exists() or not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in _SOURCE_SCAN_EXTS and suffix not in {".json", ".md", ".txt"}:
            continue
        try:
            texts[rel] = path.read_text(encoding="utf-8", errors="replace").lower()
        except Exception:
            continue
    return texts


def _keyword_hits(source_texts: dict[str, str], keywords: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for rel, text in source_texts.items():
        if any(token.lower() in text for token in keywords):
            hits.append(rel)
    return hits


def _read_json_doc(run_dir: Path, rel_path: str) -> dict[str, Any]:
    path = (run_dir / rel_path).resolve()
    if not path.exists() or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _narrative_sample_metrics(sample_doc: dict[str, Any]) -> dict[str, Any]:
    characters = [row for row in sample_doc.get("characters", []) if isinstance(row, dict)]
    chapters = [row for row in sample_doc.get("chapters", []) if isinstance(row, dict)]
    scenes = [row for row in sample_doc.get("scenes", []) if isinstance(row, dict)]
    assets = [row for row in sample_doc.get("assets", []) if isinstance(row, dict)]
    asset_types = {str(row.get("asset_id", "")).strip(): str(row.get("asset_type", "")).strip().lower() for row in assets}
    branch_points = sum(1 for row in scenes if isinstance(row.get("choices", []), list) and row.get("choices"))
    explicit_choices = sum(len([choice for choice in row.get("choices", []) if isinstance(choice, dict)]) for row in scenes)
    valid_character_cards = sum(1 for row in characters if str(row.get("character_id", "")).strip() and str(row.get("name", "")).strip() and str(row.get("role", "")).strip())
    scenes_with_background = sum(1 for row in scenes if str(row.get("background_asset_id", "")).strip())
    scenes_with_media_refs = 0
    for row in scenes:
        asset_ids = [str(item).strip() for item in row.get("asset_ids", []) if str(item).strip()]
        if any(asset_types.get(asset_id, "") in {"sprite", "sfx", "cg"} for asset_id in asset_ids):
            scenes_with_media_refs += 1
    return {
        "character_count": len(characters),
        "chapter_count": len(chapters),
        "scene_count": len(scenes),
        "branch_point_count": branch_points,
        "explicit_choice_count": explicit_choices,
        "valid_character_cards": valid_character_cards,
        "scenes_with_background": scenes_with_background,
        "scenes_with_media_refs": scenes_with_media_refs,
    }


def _provenance_metrics(source_map_doc: dict[str, Any]) -> dict[str, Any]:
    items = [row for row in source_map_doc.get("content_items", []) if isinstance(row, dict)]
    source_refs = [str(row.get("source", "")).strip() for row in items if str(row.get("source", "")).strip()]
    valid_source_refs = [row for row in source_refs if row.startswith("LOCAL:") or row.startswith("API:")]
    api_source_refs = [row for row in valid_source_refs if row.startswith("API:")]
    local_source_refs = [row for row in valid_source_refs if row.startswith("LOCAL:")]
    field_sources = {
        str(key).strip(): str(value).strip()
        for key, value in dict(source_map_doc.get("field_sources", {})).items()
        if str(key).strip() and str(value).strip()
    }
    field_api_refs = {key: value for key, value in field_sources.items() if value.startswith("API:")}
    api_content_source_ref = str(source_map_doc.get("api_content_source_ref", "")).strip()
    return {
        "content_item_count": len(items),
        "source_ref_count": len(source_refs),
        "valid_source_ref_count": len(valid_source_refs),
        "api_source_ref_count": len(api_source_refs),
        "local_source_ref_count": len(local_source_refs),
        "field_source_count": len(field_sources),
        "field_api_source_count": len(field_api_refs),
        "claims_api_content": bool(source_map_doc.get("api_content_applied")) or api_content_source_ref.startswith("API:"),
        "api_content_source_ref": api_content_source_ref,
        "invalid_source_refs": [row for row in source_refs if row not in valid_source_refs],
    }


def narrative_source_map_validation(source_map_doc: dict[str, Any]) -> dict[str, Any]:
    metrics = _provenance_metrics(source_map_doc)
    reasons: list[str] = []
    if int(metrics.get("content_item_count", 0)) < 1:
        reasons.append("source map has no content items")
    if int(metrics.get("valid_source_ref_count", 0)) < 1:
        reasons.append("source map lacks LOCAL:/API: refs")
    if list(metrics.get("invalid_source_refs", [])):
        reasons.append("source map contains invalid refs")
    if bool(metrics.get("claims_api_content", False)):
        if int(metrics.get("api_source_ref_count", 0)) < 1 and int(metrics.get("field_api_source_count", 0)) < 1:
            reasons.append("source map claims API content but has no API refs")
        if not str(metrics.get("api_content_source_ref", "")).startswith("API:"):
            reasons.append("source map claims API content but api_content_source_ref is missing")
    return {
        "passed": not reasons,
        "metrics": metrics,
        "reasons": reasons,
    }


def capability_plan_validation(
    *,
    run_dir: Path,
    project_root: str,
    capability_plan: dict[str, Any],
    business_generated: list[str],
) -> dict[str, Any]:
    generated = [str(row).replace("\\", "/") for row in business_generated if str(row).strip()]
    existing = _existing_paths(run_dir, generated)
    bundle_rows = [row for row in capability_plan.get("bundles", []) if isinstance(row, dict)]
    required_bundles = [str(item).strip() for item in capability_plan.get("required_bundles", []) if str(item).strip()]
    required_views = [str(item).strip() for item in dict(capability_plan.get("coverage_target", {})).get("required_views", []) if str(item).strip()]
    required_interactions = [str(item).strip() for item in dict(capability_plan.get("coverage_target", {})).get("required_interactions", []) if str(item).strip()]
    coverage_rows: list[dict[str, Any]] = []
    missing_bundles: list[str] = []
    covered_bundles: list[str] = []
    for bundle in bundle_rows:
        bundle_id = str(bundle.get("bundle_id", "")).strip()
        required_suffixes = [str(item).strip() for item in bundle.get("required_file_suffixes", []) if str(item).strip()]
        matched = [path for path in existing if any(path.endswith(suffix) for suffix in required_suffixes)]
        row = {
            "bundle_id": bundle_id,
            "required": bool(bundle.get("required", False)),
            "enabled_for_materialization": bool(bundle.get("enabled_for_materialization", False)),
            "matched_files": matched,
            "required_file_suffixes": required_suffixes,
            "covered": not required_suffixes or len(matched) == len(required_suffixes),
        }
        coverage_rows.append(row)
        if row["covered"]:
            covered_bundles.append(bundle_id)
        elif row["required"]:
            missing_bundles.append(bundle_id)
    sample_views = [str(item).strip() for item in capability_plan.get("project_spec_views", []) if str(item).strip()]
    sample_interactions = [str(item).strip() for item in capability_plan.get("project_spec_interactions", []) if str(item).strip()]
    view_alignment_missing = [row for row in required_views if row not in sample_views]
    interaction_alignment_missing = [row for row in required_interactions if row not in sample_interactions]
    required_total = len(required_bundles) or 1
    covered_required = len([row for row in coverage_rows if row.get("required") and row.get("covered")])
    coverage_ratio = covered_required / required_total
    reasons: list[str] = []
    if missing_bundles:
        reasons.append(f"missing capability bundles: {', '.join(sorted(set(missing_bundles)))}")
    if view_alignment_missing:
        reasons.append(f"project spec missing capability views: {', '.join(sorted(set(view_alignment_missing)))}")
    if interaction_alignment_missing:
        reasons.append(f"project spec missing capability interactions: {', '.join(sorted(set(interaction_alignment_missing)))}")
    return {
        "passed": not reasons,
        "family_key": str(capability_plan.get("family_key", "")).strip(),
        "required_bundles": required_bundles,
        "covered_bundles": sorted(set(covered_bundles)),
        "missing_bundles": sorted(set(missing_bundles)),
        "coverage_ratio": coverage_ratio,
        "coverage_rows": coverage_rows,
        "view_alignment_missing": sorted(set(view_alignment_missing)),
        "interaction_alignment_missing": sorted(set(interaction_alignment_missing)),
        "reasons": reasons,
        "project_root": project_root,
    }


_NARRATIVE_UX_SECTION_RULES: dict[str, tuple[str, ...]] = {
    "project_loader": ("project loader", "project / sample load", "sample project load", "loaded sample", "source map"),
    "story_editor": ("story / scene / branch editor", "scene graph editor", "branch editor", "scene editor", "chapter timeline"),
    "cast_assets": ("character management", "cast board", "asset management", "background / sprite / sfx / cg catalog"),
    "preview_export": ("preview / export", "preview export panel", "deliverable_targets", "script_preview.rpy", "preview.html"),
}

_NARRATIVE_UX_CONTROL_RULES: dict[str, tuple[str, ...]] = {
    "forms": ("<form", "sample-loader-form", "scene-editor-form", "branch-editor-form", "character-editor-form", "asset-bind-form"),
    "inputs": ("<input", "<textarea", "<select", "choice-target-select", "character-profile-input", "scene-title-input"),
    "actions": ("data-action='load-sample'", "data-action='reset-sample'", "data-action='update-scene'", "data-action='update-branch'", "data-action='update-character'", "data-action='bind-background'", "data-action='save-state'", "data-action='export-project'"),
    "hooks": ("const ctcp_editor=", "document.addeventlistener(", "data-state-source=", "data-export-source="),
}


def _narrative_interaction_acceptance(*, preview_text: str, preview_path: Path | None, run_dir: Path, visual_evidence: dict[str, Any]) -> dict[str, Any]:
    control_hits = {
        section: [token for token in tokens if token.lower() in preview_text]
        for section, tokens in _NARRATIVE_UX_CONTROL_RULES.items()
    }
    reasons: list[str] = []
    for section, hits in control_hits.items():
        if not hits:
            reasons.append(f"preview evidence missing interaction controls: {section}")
    source_files = [str(item).strip() for item in visual_evidence.get("source_files", []) if str(item).strip()]
    source_names = {Path(item).name for item in source_files}
    source_lookup = {Path(item).name: (run_dir / item).resolve() for item in source_files if (run_dir / item).exists()}
    state_diff_path = source_lookup.get("state_diff.json") or (preview_path.parent / "state_diff.json" if preview_path is not None else None)
    interaction_path = source_lookup.get("interaction_trace.json") or (preview_path.parent / "interaction_trace.json" if preview_path is not None else None)
    workspace_path = source_lookup.get("workspace_snapshot.json") or (preview_path.parent / "workspace_snapshot.json" if preview_path is not None else None)
    export_path = source_lookup.get("script_preview.rpy") or (preview_path.parent / "script_preview.rpy" if preview_path is not None else None)
    state_diff_doc = _read_json_doc(state_diff_path.parent, state_diff_path.name) if state_diff_path is not None and state_diff_path.exists() else {}
    interaction_doc = _read_json_doc(interaction_path.parent, interaction_path.name) if interaction_path is not None and interaction_path.exists() else {}
    workspace_doc = _read_json_doc(workspace_path.parent, workspace_path.name) if workspace_path is not None and workspace_path.exists() else {}
    export_text = export_path.read_text(encoding="utf-8", errors="replace").lower() if export_path is not None and export_path.exists() else ""
    state_changes = [row for row in dict(state_diff_doc).get("changes", []) if isinstance(row, dict)]
    applied_operations = [row for row in dict(interaction_doc).get("applied_operations", []) if isinstance(row, dict)]
    available_actions = [str(row).strip() for row in dict(interaction_doc).get("available_actions", []) if str(row).strip()]
    interaction_present = bool(interaction_doc) or "interaction_trace.json" in source_names or (interaction_path is not None and interaction_path.exists())
    workspace_present = bool(workspace_doc) or "workspace_snapshot.json" in source_names or "data-state-source=" in preview_text or (workspace_path is not None and workspace_path.exists())
    export_present = bool(export_text) or "script_preview.rpy" in source_names or "data-export-source=" in preview_text or (export_path is not None and export_path.exists())
    state_diff_present = bool(state_diff_doc) or "state_diff.json" in source_names or (state_diff_path is not None and state_diff_path.exists())
    if not interaction_present:
        reasons.append("preview evidence missing interaction trace")
    if not workspace_present:
        reasons.append("preview evidence missing workspace snapshot")
    if not export_present:
        reasons.append("preview evidence missing export script")
    if interaction_doc:
        if str(interaction_doc.get("interaction_mode", "")).strip() != "interactive_editor":
            reasons.append("interaction trace is not marked interactive_editor")
        if not available_actions:
            reasons.append("interaction trace missing available actions")
    if state_changes:
        reflected = False
        for row in state_changes:
            after = str(row.get("after", "")).strip().lower()
            if after and (after in preview_text or after in export_text or after in json.dumps(workspace_doc, ensure_ascii=False).lower()):
                reflected = True
                break
        if not reflected:
            reasons.append("export output does not reflect recorded editor state changes")
    return {
        "passed": not reasons,
        "control_hits": control_hits,
        "state_diff_present": state_diff_present,
        "interaction_trace_present": interaction_present,
        "workspace_snapshot_present": workspace_present,
        "applied_operation_count": len(applied_operations),
        "state_change_count": len(state_changes),
        "reasons": reasons,
    }


def _benchmark_narrative_domain_report(*, rows: list[str], business_missing: list[str], contamination: list[str]) -> dict[str, Any]:
    return {
        "kind": "narrative_copilot_benchmark",
        "passed": bool(rows) and not business_missing and not contamination,
        "checks": [
            "benchmark narrative outline generated",
            "benchmark narrative cast schema generated",
            "benchmark narrative export pipeline generated",
        ],
        "missing": sorted(set(list(business_missing) + contamination)),
        "contamination_hits": contamination,
    }


def _validate_cli_toolkit_domain(
    *,
    rows: list[str],
    startup_entrypoint: str,
    startup_readme: str,
    business_missing: list[str],
    contamination: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    checks, missing = _validate_required_suffixes(rows, ["/commands.py", "/exporter.py", "/service.py"], run_dir=run_dir)
    if startup_entrypoint:
        entry = (run_dir / startup_entrypoint).resolve()
        checks.append("cli startup entrypoint present" if entry.exists() else "")
        if not entry.exists():
            missing.append(startup_entrypoint)
    if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("python", "cli", "command", "命令")):
        checks.append("readme explains CLI startup")
    else:
        missing.append("README CLI startup guidance")
    test_file = next((row for row in rows if row.endswith("_service.py") and "/tests/" in row), "")
    if test_file:
        checks.append("service regression test generated")
    else:
        missing.append("tests/test_*_service.py")
    return {
        "kind": "cli_toolkit",
        "passed": not missing and not business_missing and not contamination,
        "checks": [check for check in checks if check] or ["cli toolkit files generated"],
        "missing": sorted(set(list(business_missing) + missing + contamination)),
        "contamination_hits": contamination,
    }


def _validate_web_service_domain(
    *,
    rows: list[str],
    startup_entrypoint: str,
    startup_readme: str,
    business_missing: list[str],
    contamination: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    checks, missing = _validate_required_suffixes(rows, ["/service_contract.py", "/app.py", "/exporter.py", "/service.py"], run_dir=run_dir)
    if startup_entrypoint:
        entry = (run_dir / startup_entrypoint).resolve()
        checks.append("web service startup entrypoint present" if entry.exists() else "")
        if not entry.exists():
            missing.append(startup_entrypoint)
    if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("--serve", "http", "web", "service", "接口")):
        checks.append("readme explains web service usage")
    else:
        missing.append("README web/service startup guidance")
    return {
        "kind": "web_service",
        "passed": not missing and not business_missing and not contamination,
        "checks": [check for check in checks if check] or ["web service files generated"],
        "missing": sorted(set(list(business_missing) + missing + contamination)),
        "contamination_hits": contamination,
    }


def _validate_team_task_pm_domain(
    *,
    rows: list[str],
    startup_entrypoint: str,
    startup_readme: str,
    business_missing: list[str],
    contamination: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    required = [
        "/workspace.py",
        "/tasks.py",
        "/board.py",
        "/filters.py",
        "/activity.py",
        "/app.py",
        "/exporter.py",
        "/service.py",
    ]
    checks, missing = _validate_required_suffixes(rows, required, run_dir=run_dir)
    source_texts = _scan_text_bundle(run_dir=run_dir, rel_paths=rows + [startup_readme])
    for group, keywords in _TEAM_TASK_PM_RULES.items():
        hits = _keyword_hits(source_texts, keywords)
        if hits:
            checks.append(f"team task PM {group} capability detected")
        else:
            missing.append(f"team task PM {group} capability missing")
    if startup_entrypoint:
        entry = (run_dir / startup_entrypoint).resolve()
        checks.append("team task PM startup entrypoint present" if entry.exists() else "")
        if not entry.exists():
            missing.append(startup_entrypoint)
    if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("plane-lite", "focalboard", "kanban", "task", "startup steps")):
        checks.append("README explains Plane-lite task collaboration startup")
    else:
        missing.append("README Plane-lite/task startup guidance")
    return {
        "kind": "team_task_management",
        "passed": not missing and not business_missing and not contamination,
        "checks": [check for check in checks if check],
        "missing": sorted(set(list(business_missing) + missing + contamination)),
        "contamination_hits": contamination,
    }


def _validate_indie_studio_hub_domain(
    *,
    rows: list[str],
    startup_entrypoint: str,
    startup_readme: str,
    business_missing: list[str],
    contamination: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    required = [
        "/workspace.py",
        "/tasks.py",
        "/board.py",
        "/filters.py",
        "/activity.py",
        "/assets.py",
        "/bugs.py",
        "/releases.py",
        "/docs_center.py",
        "/app.py",
        "/exporter.py",
        "/service.py",
    ]
    checks, missing = _validate_required_suffixes(rows, required, run_dir=run_dir)
    source_texts = _scan_text_bundle(run_dir=run_dir, rel_paths=rows + [startup_readme])
    for group, keywords in _INDIE_STUDIO_HUB_RULES.items():
        hits = _keyword_hits(source_texts, keywords)
        if hits:
            checks.append(f"indie studio hub {group} capability detected")
        else:
            missing.append(f"indie studio hub {group} capability missing")
    if startup_entrypoint:
        entry = (run_dir / startup_entrypoint).resolve()
        checks.append("indie studio hub startup entrypoint present" if entry.exists() else "")
        if not entry.exists():
            missing.append(startup_entrypoint)
    if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("indie studio production hub", "asset library", "bug tracker", "build / release center", "docs center")):
        checks.append("README explains Indie Studio Hub startup and domain surfaces")
    else:
        missing.append("README Indie Studio Hub startup guidance")
    return {
        "kind": "indie_studio_production_hub",
        "passed": not missing and not business_missing and not contamination,
        "checks": [check for check in checks if check],
        "missing": sorted(set(list(business_missing) + missing + contamination)),
        "contamination_hits": contamination,
    }


def _validate_data_pipeline_domain(
    *,
    rows: list[str],
    startup_readme: str,
    business_missing: list[str],
    contamination: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    checks, missing = _validate_required_suffixes(rows, ["/transforms.py", "/pipeline.py", "/exporter.py", "/service.py"], run_dir=run_dir)
    if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("pipeline", "sample output", "数据", "导出")):
        checks.append("readme explains pipeline output path")
    else:
        missing.append("README pipeline output guidance")
    return {
        "kind": "data_pipeline",
        "passed": not missing and not business_missing and not contamination,
        "checks": checks or ["data pipeline files generated"],
        "missing": sorted(set(list(business_missing) + missing + contamination)),
        "contamination_hits": contamination,
    }


def _validate_narrative_editor_domain(
    *,
    rows: list[str],
    startup_readme: str,
    business_missing: list[str],
    contamination: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    source_texts = _scan_text_bundle(run_dir=run_dir, rel_paths=rows + [startup_readme])
    checks: list[str] = []
    missing: list[str] = []
    editor_hits = _keyword_hits(source_texts, _NARRATIVE_STRUCTURE_RULES["editor_entry"])
    graph_hits = _keyword_hits(source_texts, _NARRATIVE_STRUCTURE_RULES["narrative_graph"])
    asset_hits = _keyword_hits(source_texts, _NARRATIVE_STRUCTURE_RULES["asset_model"])
    preview_hits = _keyword_hits(source_texts, _NARRATIVE_STRUCTURE_RULES["preview_export"])
    sample_seed = next(
        (
            rel
            for rel in rows
            if rel.endswith("/sample_data/example_project.json")
            or rel.endswith("/sample_data/example_project.yaml")
            or rel.endswith("/sample_data/example_project.md")
        ),
        "",
    )
    source_map_seed = next((rel for rel in rows if rel.endswith("/sample_data/source_map.json") or rel.endswith("/sample_data/provenance.json")), "")
    sample_metrics = _narrative_sample_metrics(_read_json_doc(run_dir, sample_seed)) if sample_seed else {}
    provenance_validation = narrative_source_map_validation(_read_json_doc(run_dir, source_map_seed)) if source_map_seed else {}
    provenance_metrics = dict(provenance_validation.get("metrics", {}))
    checks.extend(
        [
            "editor or authoring workspace entry detected" if editor_hits else "",
            "scene/branch/narrative graph model detected" if graph_hits else "",
            "character/cast/asset model detected" if asset_hits else "",
            "sample project seed detected" if sample_seed else "",
            "sample project depth contract detected" if sample_metrics and int(sample_metrics.get("character_count", 0)) >= 3 and int(sample_metrics.get("chapter_count", 0)) >= 4 and int(sample_metrics.get("scene_count", 0)) >= 8 and int(sample_metrics.get("branch_point_count", 0)) >= 2 else "",
            "sample provenance source map detected" if bool(provenance_validation.get("passed", False)) else "",
            "preview/export or packing path detected" if preview_hits else "",
        ]
    )
    if not editor_hits:
        missing.append("editor/authoring workspace entry missing")
    if not graph_hits:
        missing.append("scene/branch/narrative structure missing")
    if not asset_hits:
        missing.append("character/cast/asset model missing")
    if not sample_seed:
        missing.append("sample project/example data missing")
    if sample_seed:
        if int(sample_metrics.get("character_count", 0)) < 3:
            missing.append("sample project needs at least 3 character cards")
        if int(sample_metrics.get("valid_character_cards", 0)) < 3:
            missing.append("sample project character cards are incomplete")
        if int(sample_metrics.get("chapter_count", 0)) < 4:
            missing.append("sample project needs at least 4 chapters")
        if int(sample_metrics.get("scene_count", 0)) < 8:
            missing.append("sample project needs at least 8 scene nodes")
        if int(sample_metrics.get("branch_point_count", 0)) < 2:
            missing.append("sample project needs at least 2 explicit branch points")
        if int(sample_metrics.get("scenes_with_background", 0)) < int(sample_metrics.get("scene_count", 0)):
            missing.append("every sample scene needs a background placeholder")
        if int(sample_metrics.get("scenes_with_media_refs", 0)) < 2:
            missing.append("sample project needs sprite/sfx/cg references in some scenes")
    if not source_map_seed:
        missing.append("sample provenance/source map missing")
    if source_map_seed:
        missing.extend(str(reason) for reason in provenance_validation.get("reasons", []) if str(reason).strip())
    if not preview_hits:
        missing.append("preview/pack/export implementation missing")
    if contamination:
        missing.append("domain contamination detected")
    return {
        "kind": "narrative_vn_editor",
        "passed": not missing and not business_missing,
        "checks": [check for check in checks if check],
        "missing": sorted(set(list(business_missing) + missing + contamination)),
        "evidence": {
            "editor_entry": editor_hits,
            "narrative_graph": graph_hits,
            "asset_model": asset_hits,
            "preview_export": preview_hits,
            "sample_project": [sample_seed] if sample_seed else [],
            "sample_metrics": sample_metrics,
            "sample_provenance": [source_map_seed] if source_map_seed else [],
            "provenance_metrics": provenance_metrics,
            "provenance_validation": provenance_validation,
        },
        "contamination_hits": contamination,
    }


def ux_validation(
    *,
    project_domain: str,
    delivery_shape: str,
    run_dir: Path,
    visual_evidence: dict[str, Any],
) -> dict[str, Any]:
    shape = str(delivery_shape or "").strip()
    keywords = tuple(preview_keywords(project_domain))
    preview_rel = str(visual_evidence.get("preview_source", "")).strip()
    preview_path = (run_dir / preview_rel).resolve() if preview_rel else None
    preview_text = ""
    if preview_path is not None and preview_path.exists():
        preview_text = preview_path.read_text(encoding="utf-8", errors="replace").lower()
    matched_keywords = [token for token in keywords if token.lower() in preview_text]
    section_hits = {section: [token for token in tokens if token.lower() in preview_text] for section, tokens in _NARRATIVE_UX_SECTION_RULES.items()}
    interaction_acceptance = _narrative_interaction_acceptance(preview_text=preview_text, preview_path=preview_path, run_dir=run_dir, visual_evidence=visual_evidence)
    files = [str(item).strip() for item in visual_evidence.get("files", []) if str(item).strip()]
    reasons: list[str] = []
    if shape not in {"gui_first", "web_first"}:
        return {
            "required": False,
            "passed": True,
            "visual_type": str(visual_evidence.get("visual_type", "")).strip(),
            "files": files,
            "matched_keywords": matched_keywords,
            "reasons": [],
        }
    if not files:
        reasons.append("visual evidence files missing")
    if project_domain == "narrative_vn_editor":
        benchmark_preview = any(marker in preview_text for marker in ("story_bundle.json", "prompt_sheet.json", "scene_cards.json", "benchmark narrative copilot"))
        if str(visual_evidence.get("visual_type", "")).strip() != "real_export_page":
            reasons.append("narrative/gui projects require real UI evidence instead of fallback evidence cards")
        if not preview_rel:
            reasons.append("narrative/gui projects require a preview source page")
        if keywords and not matched_keywords:
            reasons.append("preview evidence does not show editor/workspace narrative signals")
        if not benchmark_preview:
            for section, hits in section_hits.items():
                if not hits:
                    reasons.append(f"preview evidence missing narrative editor area: {section}")
            reasons.extend(str(item) for item in interaction_acceptance.get("reasons", []) if str(item).strip())
    return {
        "required": True,
        "passed": not reasons,
        "visual_type": str(visual_evidence.get("visual_type", "")).strip(),
        "files": files,
        "preview_source": preview_rel,
        "matched_keywords": matched_keywords,
        "section_hits": section_hits,
        "interaction_acceptance": interaction_acceptance,
        "reasons": reasons,
    }


def domain_validation(
    *,
    project_domain: str,
    project_type: str,
    project_archetype: str,
    execution_mode: str,
    business_generated: list[str],
    business_missing: list[str],
    startup_entrypoint: str,
    startup_readme: str,
    run_dir: Path,
) -> dict[str, Any]:
    rows = _existing_paths(run_dir, business_generated)
    contamination = contamination_hits(project_domain=project_domain, rel_paths=_normalized_paths(business_generated))
    if project_domain == "narrative_vn_editor" and str(execution_mode).strip() == "benchmark_regression":
        return _benchmark_narrative_domain_report(rows=rows, business_missing=business_missing, contamination=contamination)
    if project_domain != "narrative_vn_editor" and project_type != "narrative_copilot":
        if project_domain == "indie_studio_production_hub" or project_type == "indie_studio_hub" or project_archetype == "indie_studio_hub_web":
            return _validate_indie_studio_hub_domain(
                rows=rows,
                startup_entrypoint=startup_entrypoint,
                startup_readme=startup_readme,
                business_missing=business_missing,
                contamination=contamination,
                run_dir=run_dir,
            )
        if project_domain == "team_task_management" or project_type == "team_task_pm" or project_archetype == "team_task_pm_web":
            return _validate_team_task_pm_domain(
                rows=rows,
                startup_entrypoint=startup_entrypoint,
                startup_readme=startup_readme,
                business_missing=business_missing,
                contamination=contamination,
                run_dir=run_dir,
            )
        if project_archetype == "cli_toolkit":
            return _validate_cli_toolkit_domain(
                rows=rows,
                startup_entrypoint=startup_entrypoint,
                startup_readme=startup_readme,
                business_missing=business_missing,
                contamination=contamination,
                run_dir=run_dir,
            )
        if project_archetype == "web_service":
            return _validate_web_service_domain(
                rows=rows,
                startup_entrypoint=startup_entrypoint,
                startup_readme=startup_readme,
                business_missing=business_missing,
                contamination=contamination,
                run_dir=run_dir,
            )
        if project_archetype == "data_pipeline":
            return _validate_data_pipeline_domain(
                rows=rows,
                startup_readme=startup_readme,
                business_missing=business_missing,
                contamination=contamination,
                run_dir=run_dir,
            )
        return {
            "kind": project_domain or "generic",
            "passed": not contamination,
            "checks": ["no domain-specific checks required"],
            "missing": list(contamination),
            "contamination_hits": contamination,
        }
    return _validate_narrative_editor_domain(
        rows=rows,
        startup_readme=startup_readme,
        business_missing=business_missing,
        contamination=contamination,
        run_dir=run_dir,
    )
