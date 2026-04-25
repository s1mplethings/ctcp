from __future__ import annotations

import json
import keyword
import re
from pathlib import Path
from typing import Any

from tools.providers.project_generation_domain_contract import detect_project_domain

PRODUCTION_MODE = "production"
BENCHMARK_MODE = "benchmark_regression"

CLI_SHAPE = "cli_first"
GUI_SHAPE = "gui_first"
WEB_SHAPE = "web_first"
TOOL_SHAPE = "tool_library_first"

STRONG_DECISION_NODES = [
    "chair.output_contract_freeze",
    "chair.source_generation",
]
FLOW_NODES = [
    "librarian.context_pack",
    "chair.docs_generation",
    "chair.workflow_generation",
    "chair.artifact_manifest_build",
    "chair.deliver",
]

NARRATIVE_KEYWORDS = (
    "剧情工具",
    "剧情辅助",
    "剧情辅助生成",
    "叙事",
    "叙事设计",
    "故事线",
    "角色关系",
    "章节结构",
    "分支结局",
    "分镜",
    "立绘",
    "表情",
    "背景",
    "cg",
    "narrative",
    "story bible",
    "storyboard",
    "storyline",
)
GUI_KEYWORDS = ("gui", "desktop", "window", "tkinter", "qt", "electron", "桌面", "窗口", "界面")
WEB_KEYWORDS = ("web", "browser", "site", "http", "html", "frontend", "网页", "浏览器")
TEAM_PM_KEYWORDS = (
    "plane_lite_team_pm",
    "task collaboration",
    "task management",
    "team task",
    "project management",
    "kanban",
    "board",
    "task board",
    "task detail",
    "activity feed",
    "plane-lite",
    "plane lite",
    "focalboard-lite",
    "focalboard lite",
    "focalboard",
    "协作平台",
    "任务协作平台",
    "任务协作",
    "任务管理",
    "团队任务",
    "项目协作",
    "看板",
)
INDIE_STUDIO_HUB_KEYWORDS = (
    "indie studio",
    "indie game team",
    "indie studio production hub",
    "game production hub",
    "visual novel team",
    "local-first production collaboration",
    "task asset bug release",
    "asset library",
    "asset detail",
    "bug tracker",
    "build release",
    "release center",
    "docs center",
    "milestone plan",
    "startup guide",
    "replay guide",
    "mid stage review",
    "独立游戏团队",
    "独立团队",
    "本地生产协作平台",
    "任务、素材、bug、版本进度",
    "任务 素材 bug 版本进度",
    "资产库",
    "资产详情",
    "bug 跟踪",
    "构建发布",
    "发布中心",
    "文档中心",
    "里程碑计划",
    "启动指南",
    "回放指南",
)
TOOL_KEYWORDS = ("sdk", "library", "tool library", "package", "module", "import", "api", "toolkit", "工具库", "库", "模块")
CLI_KEYWORDS = ("cli", "terminal", "command line", "shell", "命令行", "终端")
WEB_SERVICE_KEYWORDS = (
    "api service",
    "rest api",
    "http service",
    "endpoint",
    "webhook",
    "json api",
    "service endpoint",
    "本地服务",
    "接口服务",
    "服务接口",
)
DATA_PIPELINE_KEYWORDS = (
    "etl",
    "pipeline",
    "transform",
    "ingest",
    "dataset",
    "csv",
    "json export",
    "batch",
    "数据处理",
    "数据管道",
    "导出",
    "转换",
)
CLI_TOOLKIT_KEYWORDS = (
    "command",
    "commands",
    "automation",
    "task plan",
    "operator checklist",
    "toolkit",
    "任务规划",
    "操作清单",
    "自动化",
    "批处理",
)
DEMO_KEYWORDS = ("demo", "showcase", "example", "sample", "演示", "示例")
BENCHMARK_HINTS = ("benchmark", "regression", "fixed_narrative", "回归", "基准")
HIGH_QUALITY_KEYWORDS = (
    "high-quality",
    "high quality",
    "extended",
    "product depth",
    "thicker",
    "formal product",
    "not minimal mvp",
    "not just mvp",
    "8 screenshots",
    "feature matrix",
    "page map",
    "data model summary",
    "更厚",
    "正式产品",
    "高质量",
    "扩展",
    "不是最小 mvp",
    "不要缩回基础 mvp",
    "8 张",
    "功能矩阵",
    "页面地图",
    "数据模型",
    "10 screenshots",
    "10+ screenshots",
    "10 张",
    "10+ 张",
    "milestone plan",
    "startup guide",
    "replay guide",
    "mid stage review",
)
USER_CONTEXT_PREFIXES = ("artifacts/frontend_uploads/", "input/", "inputs/", "requirements/", "specs/")
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CAPABILITY_BUNDLE_CONTRACT_PATH = _REPO_ROOT / "contracts" / "project_capability_bundles.json"


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    haystack = str(text or "").lower()
    return any(keyword and keyword.lower() in haystack for keyword in keywords)


def _load_capability_bundle_contract() -> dict[str, Any]:
    try:
        doc = json.loads(_CAPABILITY_BUNDLE_CONTRACT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": "ctcp-project-capability-bundles-v1", "families": {}}
    if not isinstance(doc, dict):
        return {"schema_version": "ctcp-project-capability-bundles-v1", "families": {}}
    families = doc.get("families")
    return {
        "schema_version": str(doc.get("schema_version", "ctcp-project-capability-bundles-v1")),
        "families": dict(families) if isinstance(families, dict) else {},
    }


def capability_family_key(*, scaffold_family: str, project_archetype: str, project_type: str) -> str:
    families = dict(_load_capability_bundle_contract().get("families", {}))
    for candidate in (str(project_archetype).strip(), str(scaffold_family).strip(), str(project_type).strip(), "generic_copilot"):
        if candidate and candidate in families:
            return candidate
    return "generic_copilot"


def enrich_project_spec(
    *,
    goal: str,
    base_spec: dict[str, Any],
    project_intent: dict[str, Any],
    project_domain: str,
    scaffold_family: str,
    project_type: str,
    project_archetype: str,
    delivery_shape: str,
) -> dict[str, Any]:
    spec = dict(base_spec or {})
    spec["schema_version"] = "ctcp-project-spec-v2"
    spec["goal_summary"] = str(spec.get("goal_summary", "")).strip() or str(project_intent.get("goal_summary", "")).strip() or str(goal).strip()
    spec["target_user"] = str(spec.get("target_user", "")).strip() or str(project_intent.get("target_user", "")).strip() or "project owner"
    spec["problem_to_solve"] = str(spec.get("problem_to_solve", "")).strip() or str(project_intent.get("problem_to_solve", "")).strip() or "turn a scoped goal into a runnable MVP project"
    spec["project_domain"] = str(project_domain).strip()
    spec["scaffold_family"] = str(scaffold_family).strip()
    spec["project_type"] = str(project_type).strip()
    spec["project_archetype"] = str(project_archetype).strip()
    spec["delivery_shape"] = str(delivery_shape).strip()

    if project_domain == "narrative_vn_editor":
        spec["core_modules"] = [
            "seed_loader",
            "editor_workspace",
            "editor_actions",
            "scene_graph",
            "cast_schema",
            "asset_catalog",
            "prompt_pipeline",
            "export_delivery",
        ]
        spec["required_pages_or_views"] = [
            "project_loader",
            "story_scene_branch_editor",
            "character_asset_manager",
            "preview_export_panel",
        ]
        spec["data_models"] = [
            "project_doc",
            "chapter_plan",
            "scene_node",
            "choice_link",
            "character_card",
            "asset_placeholder",
            "source_map",
        ]
        spec["key_interactions"] = [
            "load_sample",
            "reset_sample",
            "add_scene",
            "update_scene",
            "update_branch",
            "update_character",
            "bind_background",
            "save_state",
            "export_project",
        ]
        spec["sample_content_plan"] = {
            "pipeline_id": "narrative_sample_generation",
            "minimum_depth": {
                "characters": 3,
                "chapters": 4,
                "scenes": 8,
                "branch_points": 2,
            },
            "steps": [
                "theme_brief",
                "cast_cards",
                "chapter_plan",
                "scene_graph",
                "choice_map",
                "asset_placeholders",
                "source_map",
            ],
            "api_merge_targets": [
                "character_profiles",
                "chapter_summaries",
                "scene_summaries",
                "choice_labels",
                "asset_notes",
                "runtime_snippets",
            ],
        }
        spec["export_targets"] = [
            "preview.html",
            "script_preview.rpy",
            "scene_graph.json",
            "asset_catalog.json",
            "narrative_editor_project.json",
        ]
        spec["delivery_requirements"] = [
            "final_project_bundle.zip",
            "README",
            "screenshots",
            "verify_summary",
        ]
        spec["explicit_non_goals"] = [
            "full game engine",
            "commercial-grade save database",
            "binary asset production pipeline",
        ]
        return spec

    if project_domain == "indie_studio_production_hub" or is_indie_studio_hub_signal(
        goal,
        project_intent=project_intent,
        project_spec=base_spec,
    ):
        spec["build_profile"] = "high_quality_extended"
        spec["product_depth"] = "extended"
        spec["required_pages"] = 13
        spec["required_screenshots"] = 10
        spec["require_feature_matrix"] = True
        spec["require_page_map"] = True
        spec["require_data_model_summary"] = True
        spec["require_search"] = True
        spec["require_import_or_export"] = "both"
        spec["require_dashboard_or_project_overview"] = True
        spec["core_modules"] = [
            "workspace_project_model",
            "milestone_backlog",
            "task_board",
            "task_list",
            "task_detail",
            "comments_activity",
            "asset_library",
            "asset_detail",
            "bug_tracker",
            "build_release_center",
            "docs_center",
            "dashboard",
            "search",
            "import_export",
            "settings",
            "extended_coverage",
        ]
        spec["required_pages_or_views"] = [
            "dashboard",
            "project_list",
            "project_overview",
            "milestone_backlog",
            "kanban_board",
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
        spec["data_models"] = [
            "user",
            "workspace",
            "project",
            "milestone",
            "task",
            "asset",
            "asset_link",
            "bug",
            "build_record",
            "release_summary",
            "doc_entry",
            "activity_event",
        ]
        spec["key_interactions"] = [
            "create_project",
            "view_milestones",
            "create_task",
            "edit_task_fields",
            "move_task_status",
            "comment_on_task",
            "search_tasks",
            "filter_tasks",
            "sort_tasks",
            "view_asset_library",
            "view_asset_detail",
            "link_asset_to_task",
            "create_bug",
            "update_bug_status",
            "view_build_records",
            "generate_release_summary",
            "view_docs_center",
            "export_project_data",
            "view_activity_feed",
        ]
        spec["task_fields"] = [
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "due_date",
            "labels",
            "linked_assets",
            "linked_bugs",
            "milestone",
        ]
        spec["export_targets"] = [
            "demo_workspace.json",
            "asset_library.json",
            "bug_tracker.json",
            "release_summary.json",
            "feature_matrix.md",
            "page_map.md",
            "data_model_summary.md",
            "milestone_plan.md",
            "startup_guide.md",
            "replay_guide.md",
            "mid_stage_review.md",
            "acceptance_bundle.zip",
        ]
        spec["sample_content_plan"] = {
            "pipeline_id": "indie_studio_hub_demo_seed",
            "minimum_depth": {
                "projects": 2,
                "tasks": 10,
                "assets": 6,
                "bugs": 4,
                "builds": 3,
                "docs": 4,
            },
            "steps": [
                "demo_users",
                "workspace_seed",
                "project_seed",
                "task_seed",
                "asset_seed",
                "bug_seed",
                "build_seed",
                "doc_seed",
            ],
            "api_merge_targets": [],
        }
        spec["delivery_requirements"] = [
            "final_project_bundle.zip",
            "README",
            "milestone_plan.md",
            "startup_guide.md",
            "replay_guide.md",
            "mid_stage_review.md",
            "screenshots",
            "verify_summary",
        ]
        spec["required_doc_files"] = [
            "docs/feature_matrix.md",
            "docs/page_map.md",
            "docs/data_model_summary.md",
            "docs/milestone_plan.md",
            "docs/startup_guide.md",
            "docs/replay_guide.md",
            "docs/mid_stage_review.md",
        ]
        spec["user_acceptance_required_views"] = [
            "asset_library",
            "asset_detail",
            "bug_tracker",
            "build_release_center",
            "docs_center",
        ]
        spec["explicit_non_goals"] = [
            "realtime websocket collaboration",
            "OAuth",
            "multi-tenant SaaS",
            "complex RBAC",
            "cloud sync",
            "AI automatic scheduling",
            "payment flows",
        ]
        return spec

    if project_domain == "team_task_management" or contains_any(" ".join([goal, intent_text_signal(project_intent)]), TEAM_PM_KEYWORDS):
        high_quality = is_high_quality_extended_signal(goal, project_intent=project_intent, project_spec=base_spec)
        spec["core_modules"] = [
            "auth_seed",
            "workspace_project_model",
            "task_board",
            "task_list",
            "task_detail",
            "comments_activity",
            "filters",
            "demo_data",
        ]
        spec["required_pages_or_views"] = [
            "login",
            "workspace_project_switcher",
            "dashboard",
            "project_list",
            "project_overview",
            "kanban_board",
            "task_list",
            "task_detail_drawer",
            "activity_feed",
            "project_settings",
        ]
        spec["data_models"] = [
            "user",
            "workspace",
            "project",
            "task",
            "task_status",
            "task_label",
            "comment",
            "activity_event",
        ]
        spec["key_interactions"] = [
            "login_with_demo_user",
            "create_project",
            "create_task",
            "edit_task_fields",
            "move_task_status",
            "comment_on_task",
            "filter_tasks",
            "view_task_detail",
            "view_activity_feed",
            "export_demo_workspace",
        ]
        if high_quality:
            spec["build_profile"] = "high_quality_extended"
            spec["product_depth"] = "extended"
            spec["required_pages"] = 8
            spec["required_screenshots"] = 8
            spec["require_feature_matrix"] = True
            spec["require_page_map"] = True
            spec["require_data_model_summary"] = True
            spec["require_search"] = True
            spec["require_import_or_export"] = "both"
            spec["require_dashboard_or_project_overview"] = True
            spec["core_modules"].extend(["dashboard", "search", "import_export", "settings", "extended_coverage"])
            spec["key_interactions"].extend(["search_tasks", "sort_tasks", "import_workspace_json", "view_dashboard_stats"])
        spec["task_fields"] = [
            "title",
            "description",
            "status",
            "priority",
            "assignee",
            "due_date",
            "labels",
        ]
        spec["export_targets"] = [
            "demo_workspace.json",
            "import_template.json",
            "feature_matrix.md",
            "page_map.md",
            "data_model_summary.md",
            "acceptance_bundle.zip",
        ]
        spec["sample_content_plan"] = {
            "pipeline_id": "team_pm_demo_seed",
            "minimum_depth": {"workspaces": 1, "projects": 2, "tasks": 8, "comments": 3},
            "steps": ["demo_users", "workspace_seed", "project_seed", "task_seed", "comment_activity_seed"],
            "api_merge_targets": [],
        }
        spec["delivery_requirements"] = [
            "final_project_bundle.zip",
            "README",
            "startup_steps",
            "screenshots",
            "verify_summary",
        ]
        spec["explicit_non_goals"] = [
            "realtime websocket collaboration",
            "RBAC",
            "notifications",
            "gantt or roadmap planning",
            "OAuth",
        ]
        return spec

    archetype_modules: dict[str, dict[str, list[str]]] = {
        "web_service": {
            "core_modules": ["seed", "service_contract", "app", "service", "exporter"],
            "required_pages_or_views": ["service_entry"],
            "data_models": ["request_doc", "response_doc"],
            "key_interactions": ["serve", "generate_response"],
            "export_targets": ["sample_response.json"],
            "explicit_non_goals": ["production hosting", "multi-tenant auth"],
        },
        "data_pipeline": {
            "core_modules": ["seed", "spec_builder", "transforms", "pipeline", "exporter", "service"],
            "required_pages_or_views": ["pipeline_run"],
            "data_models": ["input_record", "output_record", "pipeline_spec"],
            "key_interactions": ["transform", "export"],
            "export_targets": ["sample_output.json"],
            "explicit_non_goals": ["distributed scheduling", "stream processing"],
        },
        "cli_toolkit": {
            "core_modules": ["seed", "spec_builder", "commands", "exporter", "service"],
            "required_pages_or_views": ["cli_entry"],
            "data_models": ["command_request", "command_report"],
            "key_interactions": ["run_command", "export_report"],
            "export_targets": ["deliverable.json"],
            "explicit_non_goals": ["desktop GUI", "remote SaaS backend"],
        },
    }
    profile = archetype_modules.get(project_archetype, {
        "core_modules": ["seed", "spec_builder", "planner", "exporter", "service"],
        "required_pages_or_views": ["planner_view"],
        "data_models": ["project_spec", "project_plan"],
        "key_interactions": ["plan", "export"],
        "export_targets": ["deliverable.json"],
        "explicit_non_goals": ["full product suite"],
    })
    for key, value in profile.items():
        spec[key] = list(value)
    spec["sample_content_plan"] = {
        "pipeline_id": "generic_sample_generation",
        "minimum_depth": {},
        "steps": [],
        "api_merge_targets": [],
    }
    spec["delivery_requirements"] = ["final_project_bundle.zip", "README"]
    return spec


def resolve_capability_plan(
    *,
    project_domain: str,
    scaffold_family: str,
    project_type: str,
    project_archetype: str,
    project_spec: dict[str, Any],
    materialize_capabilities: list[str] | None = None,
) -> dict[str, Any]:
    contract = _load_capability_bundle_contract()
    family_key = capability_family_key(
        scaffold_family=scaffold_family,
        project_archetype=project_archetype,
        project_type=project_type,
    )
    family_doc = dict(dict(contract.get("families", {})).get(family_key, {}))
    bundle_docs = dict(family_doc.get("bundles", {}))
    required_bundles = [str(item).strip() for item in family_doc.get("required_bundles", []) if str(item).strip()]
    enabled = [
        item
        for item in [str(row).strip() for row in (materialize_capabilities or required_bundles)]
        if item and item in bundle_docs
    ]
    if not enabled:
        enabled = list(required_bundles)
    expected_views: list[str] = []
    expected_interactions: list[str] = []
    for bundle_id in required_bundles:
        bundle = dict(bundle_docs.get(bundle_id, {}))
        expected_views.extend(str(item).strip() for item in bundle.get("required_views", []) if str(item).strip())
        expected_interactions.extend(str(item).strip() for item in bundle.get("required_interactions", []) if str(item).strip())
    sample_steps_source = family_doc.get("sample_generation_steps", [])
    if not sample_steps_source:
        sample_steps_source = dict(project_spec.get("sample_content_plan", {})).get("steps", [])
    return {
        "schema_version": "ctcp-capability-plan-v1",
        "project_domain": str(project_domain).strip(),
        "scaffold_family": str(scaffold_family).strip(),
        "family_key": family_key,
        "required_bundles": required_bundles,
        "materialize_bundles": enabled,
        "sample_generation_steps": [
            str(item).strip()
            for item in sample_steps_source
            if str(item).strip()
        ],
        "coverage_target": {
            "required_bundle_ratio": 1.0,
            "required_views": sorted(set(expected_views)),
            "required_interactions": sorted(set(expected_interactions)),
        },
        "bundles": [
            {
                "bundle_id": bundle_id,
                "required": bundle_id in required_bundles,
                "enabled_for_materialization": bundle_id in enabled,
                "summary": str(dict(bundle_docs.get(bundle_id, {})).get("summary", "")).strip(),
                "required_views": [
                    str(item).strip()
                    for item in dict(bundle_docs.get(bundle_id, {})).get("required_views", [])
                    if str(item).strip()
                ],
                "required_interactions": [
                    str(item).strip()
                    for item in dict(bundle_docs.get(bundle_id, {})).get("required_interactions", [])
                    if str(item).strip()
                ],
                "required_file_suffixes": [
                    str(item).strip()
                    for item in dict(bundle_docs.get(bundle_id, {})).get("required_file_suffixes", [])
                    if str(item).strip()
                ],
            }
            for bundle_id in bundle_docs
        ],
        "project_spec_views": list(project_spec.get("required_pages_or_views", [])) if isinstance(project_spec.get("required_pages_or_views"), list) else [],
        "project_spec_interactions": list(project_spec.get("key_interactions", [])) if isinstance(project_spec.get("key_interactions"), list) else [],
        "contract_source": _CAPABILITY_BUNDLE_CONTRACT_PATH.as_posix(),
    }


def normalize_mode(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in {BENCHMARK_MODE, "benchmark", "regression", "benchmark_mode"}:
        return BENCHMARK_MODE
    return PRODUCTION_MODE


def normalize_delivery_shape(raw: str) -> str:
    value = str(raw or "").strip().lower()
    aliases = {
        "cli": CLI_SHAPE,
        "cli_first": CLI_SHAPE,
        "gui": GUI_SHAPE,
        "gui_first": GUI_SHAPE,
        "web": WEB_SHAPE,
        "web_first": WEB_SHAPE,
        "tool": TOOL_SHAPE,
        "tool_first": TOOL_SHAPE,
        "tool_library_first": TOOL_SHAPE,
        "library": TOOL_SHAPE,
    }
    return aliases.get(value, "")


def load_frontend_request(run_dir: Path | None) -> dict[str, Any]:
    if run_dir is None:
        return {}
    path = run_dir / "artifacts" / "frontend_request.json"
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def frontend_constraints(run_dir: Path | None, src: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(src, dict):
        raw = src.get("constraints")
        if isinstance(raw, dict):
            return dict(raw)
    request = load_frontend_request(run_dir)
    raw = request.get("constraints")
    return dict(raw) if isinstance(raw, dict) else {}


def frontend_project_intent(run_dir: Path | None, src: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(src, dict):
        raw = src.get("project_intent")
        if isinstance(raw, dict):
            return dict(raw)
    request = load_frontend_request(run_dir)
    raw = request.get("project_intent")
    return dict(raw) if isinstance(raw, dict) else {}


def intent_text_signal(project_intent: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "goal_summary",
        "target_user",
        "problem_to_solve",
    ):
        text = str(project_intent.get(key, "")).strip()
        if text:
            parts.append(text)
    for key in (
        "mvp_scope",
        "required_inputs",
        "required_outputs",
        "hard_constraints",
        "assumptions",
        "acceptance_criteria",
    ):
        value = project_intent.get(key)
        if isinstance(value, list):
            parts.extend(str(item).strip() for item in value if str(item).strip())
    return "\n".join(parts)


def benchmark_case(constraints: dict[str, Any]) -> str:
    for key in ("benchmark_case", "test_case"):
        value = str(constraints.get(key, "")).strip()
        if value:
            return value
    return ""


def user_context_signal(context_files: list[dict[str, Any]] | None) -> str:
    parts: list[str] = []
    for item in context_files or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip().replace("\\", "/")
        if not path:
            continue
        if path.startswith(USER_CONTEXT_PREFIXES) or not path.startswith(("docs/", "scripts/", "tools/", "workflow_registry/")):
            parts.append(str(item.get("content", ""))[:2000])
    return "\n".join(parts)


def is_team_task_pm_signal(
    goal: str,
    *,
    project_intent: dict[str, Any] | None = None,
    project_spec: dict[str, Any] | None = None,
    context_files: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
) -> bool:
    parts = [
        str(goal or ""),
        intent_text_signal(project_intent or {}),
        user_context_signal(context_files),
    ]
    for doc in (project_spec or {}, constraints or {}):
        if not isinstance(doc, dict):
            continue
        for value in doc.values():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(item) for item in value)
    return contains_any("\n".join(parts), TEAM_PM_KEYWORDS)


def is_indie_studio_hub_signal(
    goal: str,
    *,
    project_intent: dict[str, Any] | None = None,
    project_spec: dict[str, Any] | None = None,
    context_files: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
) -> bool:
    parts = [
        str(goal or ""),
        intent_text_signal(project_intent or {}),
        user_context_signal(context_files),
    ]
    for doc in (project_spec or {}, constraints or {}):
        if not isinstance(doc, dict):
            continue
        for value in doc.values():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(item) for item in value)
    signal = "\n".join(parts)
    return contains_any(signal, INDIE_STUDIO_HUB_KEYWORDS)


def is_high_quality_extended_signal(
    goal: str,
    *,
    project_intent: dict[str, Any] | None = None,
    project_spec: dict[str, Any] | None = None,
    context_files: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
) -> bool:
    parts = [
        str(goal or ""),
        intent_text_signal(project_intent or {}),
        user_context_signal(context_files),
    ]
    for doc in (project_spec or {}, constraints or {}):
        if not isinstance(doc, dict):
            continue
        parts.append(json.dumps(doc, ensure_ascii=False))
    signal = "\n".join(parts)
    if contains_any(signal, HIGH_QUALITY_KEYWORDS):
        return True
    try:
        required_screenshots = int(dict(constraints or {}).get("required_screenshots", 0) or 0)
    except Exception:
        required_screenshots = 0
    return required_screenshots >= 8 or str(dict(constraints or {}).get("build_profile", "")).strip() == "high_quality_extended"


def detect_project_type(goal: str, context_files: list[dict[str, Any]] | None = None, *, execution_mode: str, benchmark_case_value: str, project_intent: dict[str, Any] | None = None) -> str:
    domain = detect_project_domain(
        goal=goal,
        project_intent=project_intent,
        context_files=context_files,
    )
    domain_id = str(domain.get("domain_id", "")).strip()
    explicit_type = str(domain.get("project_type", "")).strip()
    if explicit_type and not (domain_id == "generic_software_project" and explicit_type == "generic_copilot"):
        return explicit_type
    signal = intent_text_signal(project_intent or {})
    if is_indie_studio_hub_signal(goal, project_intent=project_intent, context_files=context_files):
        return "indie_studio_hub"
    if is_team_task_pm_signal(goal, project_intent=project_intent, context_files=context_files):
        return "team_task_pm"
    if normalize_mode(execution_mode) == BENCHMARK_MODE and contains_any(benchmark_case_value, BENCHMARK_HINTS + NARRATIVE_KEYWORDS):
        return "narrative_copilot"
    if contains_any(signal, NARRATIVE_KEYWORDS):
        return "narrative_copilot"
    if contains_any(goal, NARRATIVE_KEYWORDS):
        return "narrative_copilot"
    if contains_any(user_context_signal(context_files), NARRATIVE_KEYWORDS):
        return "narrative_copilot"
    return "generic_copilot"


def detect_project_archetype(
    goal: str,
    *,
    project_type: str,
    delivery_shape: str,
    context_files: list[dict[str, Any]] | None,
    project_intent: dict[str, Any] | None = None,
    project_spec: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
) -> tuple[str, str]:
    domain = detect_project_domain(
        goal=goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    )
    if str(domain.get("domain_id", "")).strip() != "generic_software_project" and str(domain.get("default_archetype", "")).strip():
        return str(domain["default_archetype"]).strip(), f"project_domain:{domain['domain_id']}"
    if is_indie_studio_hub_signal(
        goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    ):
        return "indie_studio_hub_web", "indie_studio_hub_signal:indie_studio_hub_web"
    if is_team_task_pm_signal(
        goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    ):
        return "team_task_pm_web", "team_task_pm_signal:team_task_pm_web"
    if project_type == "narrative_copilot":
        return "narrative_gui_editor", "project_type:narrative_copilot"

    signal = intent_text_signal(project_intent or {})
    context_signal = user_context_signal(context_files)

    def _has(keywords: tuple[str, ...]) -> tuple[bool, str]:
        if contains_any(signal, keywords):
            return True, "project_intent"
        if contains_any(goal, keywords):
            return True, "goal"
        if contains_any(context_signal, keywords):
            return True, "context"
        return False, ""

    matched, source = _has(WEB_SERVICE_KEYWORDS + WEB_KEYWORDS + TEAM_PM_KEYWORDS)
    if normalize_delivery_shape(delivery_shape) == WEB_SHAPE or matched:
        return "web_service", f"{source or 'delivery_shape'}:web_service"

    matched_cli, source_cli = _has(CLI_TOOLKIT_KEYWORDS + CLI_KEYWORDS + TOOL_KEYWORDS)
    matched_data, source_data = _has(DATA_PIPELINE_KEYWORDS)
    if normalize_delivery_shape(delivery_shape) == TOOL_SHAPE:
        return "cli_toolkit", f"{source_cli or 'delivery_shape'}:cli_toolkit"
    if matched_data:
        return "data_pipeline", f"{source_data}:data_pipeline"
    if normalize_delivery_shape(delivery_shape) == CLI_SHAPE or matched_cli:
        return "cli_toolkit", f"{source_cli or 'delivery_shape'}:cli_toolkit"

    return "generic_copilot", "default:generic_copilot"


def detect_delivery_shape(
    goal: str,
    *,
    context_files: list[dict[str, Any]] | None,
    constraints: dict[str, Any],
    execution_mode: str,
    benchmark_case_value: str,
    project_intent: dict[str, Any] | None = None,
    project_spec: dict[str, Any] | None = None,
) -> tuple[str, str]:
    signal = intent_text_signal(project_intent or {})
    explicit = normalize_delivery_shape(str(constraints.get("delivery_shape", "")).strip() or str(constraints.get("project_delivery_shape", "")).strip())
    if explicit:
        return explicit, "constraints.delivery_shape"
    domain = detect_project_domain(
        goal=goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    )
    domain_shape = normalize_delivery_shape(str(domain.get("default_delivery_shape", "")).strip())
    if str(domain.get("domain_id", "")).strip() != "generic_software_project" and domain_shape:
        return domain_shape, f"project_domain:{domain['domain_id']}"
    if normalize_mode(execution_mode) == BENCHMARK_MODE and contains_any(benchmark_case_value, BENCHMARK_HINTS + NARRATIVE_KEYWORDS):
        return CLI_SHAPE, f"benchmark_case:{benchmark_case_value or 'benchmark'}"
    if contains_any(signal, WEB_KEYWORDS):
        return WEB_SHAPE, "project_intent:web_keywords"
    if contains_any(signal, TEAM_PM_KEYWORDS):
        return WEB_SHAPE, "project_intent:team_pm_keywords"
    if contains_any(signal, GUI_KEYWORDS):
        return GUI_SHAPE, "project_intent:gui_keywords"
    if contains_any(signal, TOOL_KEYWORDS):
        return TOOL_SHAPE, "project_intent:tool_keywords"
    if contains_any(goal, WEB_KEYWORDS):
        return WEB_SHAPE, "goal:web_keywords"
    if contains_any(goal, TEAM_PM_KEYWORDS):
        return WEB_SHAPE, "goal:team_pm_keywords"
    if contains_any(goal, GUI_KEYWORDS):
        return GUI_SHAPE, "goal:gui_keywords"
    if contains_any(goal, TOOL_KEYWORDS):
        return TOOL_SHAPE, "goal:tool_keywords"
    if contains_any(goal, CLI_KEYWORDS):
        return CLI_SHAPE, "goal:cli_keywords"
    signal = user_context_signal(context_files)
    if contains_any(signal, WEB_KEYWORDS):
        return WEB_SHAPE, "context:web_keywords"
    if contains_any(signal, TEAM_PM_KEYWORDS):
        return WEB_SHAPE, "context:team_pm_keywords"
    if contains_any(signal, GUI_KEYWORDS):
        return GUI_SHAPE, "context:gui_keywords"
    if contains_any(signal, TOOL_KEYWORDS):
        return TOOL_SHAPE, "context:tool_keywords"
    return CLI_SHAPE, "default:goal_minimal_closed_loop"


def visual_requirements(delivery_shape: str) -> tuple[bool, bool, str]:
    shape = normalize_delivery_shape(delivery_shape) or CLI_SHAPE
    if shape in {GUI_SHAPE, WEB_SHAPE}:
        return True, True, "placeholder_only"
    return False, False, "not_requested"


def demo_required(goal: str, execution_mode: str, constraints: dict[str, Any], project_intent: dict[str, Any] | None = None) -> bool:
    if normalize_mode(execution_mode) == BENCHMARK_MODE:
        return True
    if bool(constraints.get("demo_required", False)):
        return True
    if contains_any(intent_text_signal(project_intent or {}), DEMO_KEYWORDS + ("验证", "smoke", "运行", "启动")):
        return True
    return contains_any(goal, DEMO_KEYWORDS)


def default_project_id(goal_slug: str, project_type: str, execution_mode: str) -> str:
    if normalize_mode(execution_mode) == BENCHMARK_MODE and project_type == "narrative_copilot":
        return "narrative-copilot"
    if goal_slug == "goal":
        return "narrative-project-copilot" if project_type == "narrative_copilot" else "project-copilot"
    return goal_slug[:48]


def default_package_name(project_id: str, project_type: str, execution_mode: str, benchmark_case_value: str) -> str:
    if normalize_mode(execution_mode) == BENCHMARK_MODE and project_type == "narrative_copilot" and contains_any(benchmark_case_value, BENCHMARK_HINTS + NARRATIVE_KEYWORDS):
        return "narrative_copilot"
    value = "".join(ch if ch.isalnum() else "_" for ch in str(project_id or "").lower())
    value = re.sub(r"_+", "_", value).strip("_")
    if not value:
        value = "narrative_copilot" if project_type == "narrative_copilot" else "project_copilot"
    if value[0].isdigit():
        value = f"project_{value}"
    if not value.isidentifier() or keyword.iskeyword(value):
        value = re.sub(r"^[^a-zA-Z_]+", "", value)
        value = re.sub(r"[^0-9a-zA-Z_]+", "_", value)
        value = re.sub(r"_+", "_", value).strip("_")
        if not value or value[0].isdigit():
            value = f"project_{value}" if value else "project"
    if keyword.iskeyword(value) or value in {"json", "sys", "re", "typing", "pathlib", "os", "subprocess", "asyncio", "unittest"}:
        value = f"project_{value}"
    return value if value.isidentifier() else ("narrative_copilot" if project_type == "narrative_copilot" else "project_copilot")


def shape_contract(delivery_shape: str, package_name: str) -> dict[str, str]:
    shape = normalize_delivery_shape(delivery_shape) or CLI_SHAPE
    if shape == GUI_SHAPE:
        return {"startup_rel": "scripts/run_project_gui.py", "workflow_doc_rel": "docs/gui_workflow.md", "shape_capability": "gui_launcher"}
    if shape == WEB_SHAPE:
        return {"startup_rel": "scripts/run_project_web.py", "workflow_doc_rel": "docs/web_workflow.md", "shape_capability": "web_launcher"}
    if shape == TOOL_SHAPE:
        return {"startup_rel": f"src/{package_name}/service.py", "workflow_doc_rel": "docs/tool_workflow.md", "shape_capability": "library_api"}
    return {"startup_rel": "scripts/run_project_cli.py", "workflow_doc_rel": "docs/cli_workflow.md", "shape_capability": "cli_service"}


def decide_project_generation(goal: str, *, run_dir: Path | None = None, context_files: list[dict[str, Any]] | None = None, src: dict[str, Any] | None = None) -> dict[str, Any]:
    constraints = frontend_constraints(run_dir, src)
    project_intent = frontend_project_intent(run_dir, src)
    project_spec = dict(src.get("project_spec", {})) if isinstance(src, dict) and isinstance(src.get("project_spec"), dict) else {}
    benchmark_case_value = benchmark_case(constraints)
    src_mode = str(src.get("execution_mode", "")).strip() if isinstance(src, dict) else ""
    execution_mode = normalize_mode(
        str(constraints.get("project_generation_mode", "")).strip()
        or str(constraints.get("execution_mode", "")).strip()
        or src_mode
        or (BENCHMARK_MODE if contains_any(benchmark_case_value, BENCHMARK_HINTS + NARRATIVE_KEYWORDS) else "")
    )
    project_domain = detect_project_domain(
        goal=goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    )
    indie_hub = is_indie_studio_hub_signal(
        goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    )
    if indie_hub and str(project_domain.get("domain_id", "")).strip() in {"generic_software_project", "team_task_management"}:
        project_domain = {
            "domain_id": "indie_studio_production_hub",
            "scaffold_family": "indie_studio_hub",
            "project_type": "indie_studio_hub",
            "default_archetype": "indie_studio_hub_web",
            "default_delivery_shape": WEB_SHAPE,
            "decision_source": "indie_studio_hub_signal",
            "matched_terms": ["indie studio production hub"],
        }
    if is_team_task_pm_signal(
        goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    ) and not indie_hub and str(project_domain.get("domain_id", "")).strip() == "generic_software_project":
        project_domain = {
            "domain_id": "team_task_management",
            "scaffold_family": "team_task_pm",
            "project_type": "team_task_pm",
            "default_archetype": "team_task_pm_web",
            "default_delivery_shape": WEB_SHAPE,
            "decision_source": "team_task_pm_signal",
            "matched_terms": ["plane-lite/team task pm"],
        }
    project_type = detect_project_type(
        goal,
        context_files=context_files,
        execution_mode=execution_mode,
        benchmark_case_value=benchmark_case_value,
        project_intent=project_intent,
    )
    delivery_shape, shape_source = detect_delivery_shape(
        goal,
        context_files=context_files,
        constraints=constraints,
        execution_mode=execution_mode,
        benchmark_case_value=benchmark_case_value,
        project_intent=project_intent,
        project_spec=project_spec,
    )
    project_archetype, archetype_source = detect_project_archetype(
        goal,
        project_type=project_type,
        delivery_shape=delivery_shape,
        context_files=context_files,
        project_intent=project_intent,
        project_spec=project_spec,
        constraints=constraints,
    )
    visual_required, screenshot_required, visual_status = visual_requirements(delivery_shape)
    high_quality = is_high_quality_extended_signal(
        goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    )
    project_domain_id = str(project_domain.get("domain_id", "")).strip() or "generic_software_project"
    project_scaffold_family = str(project_domain.get("scaffold_family", "")).strip() or "generic_copilot"
    if indie_hub or project_domain_id == "indie_studio_production_hub" or project_type == "indie_studio_hub" or project_archetype == "indie_studio_hub_web":
        project_domain_id = "indie_studio_production_hub"
        project_scaffold_family = "indie_studio_hub"
        high_quality = True
        project_type = "indie_studio_hub"
        project_archetype = "indie_studio_hub_web"
        project_domain["decision_source"] = str(project_domain.get("decision_source", "")).strip() or "indie_studio_hub_signal"
    required_pages = 13 if project_type == "indie_studio_hub" or project_archetype == "indie_studio_hub_web" else (8 if high_quality else 0)
    required_screenshots = 10 if project_type == "indie_studio_hub" or project_archetype == "indie_studio_hub_web" else (8 if high_quality else (1 if screenshot_required else 0))
    require_search = bool(high_quality)
    require_import_or_export = "both" if high_quality else "at_least_one"
    require_dashboard = bool(high_quality)
    if project_type == "indie_studio_hub" or project_archetype == "indie_studio_hub_web":
        require_search = True
        require_import_or_export = "both"
        require_dashboard = True
    return {
        "execution_mode": execution_mode,
        "benchmark_case": benchmark_case_value,
        "project_domain": project_domain_id,
        "scaffold_family": project_scaffold_family,
        "project_type": project_type,
        "project_archetype": project_archetype,
        "project_domain_decision_source": str(project_domain.get("decision_source", "")).strip() or "default_domain",
        "scaffold_family_decision_source": f"project_domain:{project_domain.get('domain_id', '')}",
        "project_type_decision_source": f"benchmark_case:{benchmark_case_value}" if execution_mode == BENCHMARK_MODE and benchmark_case_value else "goal_or_context",
        "project_archetype_decision_source": archetype_source,
        "delivery_shape": delivery_shape,
        "shape_decision_source": shape_source,
        "domain_terms": list(project_domain.get("matched_terms", [])),
        "demo_required": demo_required(goal, execution_mode, constraints, project_intent=project_intent),
        "visual_evidence_required": visual_required,
        "screenshot_required": screenshot_required,
        "visual_evidence_status": visual_status,
        "benchmark_sample_applied": execution_mode == BENCHMARK_MODE and project_type == "narrative_copilot",
        "build_profile": "high_quality_extended" if high_quality else "standard_mvp",
        "product_depth": "extended" if high_quality else "mvp",
        "required_pages": required_pages,
        "required_screenshots": required_screenshots,
        "require_feature_matrix": bool(high_quality),
        "require_page_map": bool(high_quality),
        "require_data_model_summary": bool(high_quality),
        "require_search": require_search,
        "require_import_or_export": require_import_or_export,
        "require_dashboard_or_project_overview": require_dashboard,
        "decision_nodes": list(STRONG_DECISION_NODES),
        "flow_nodes": list(FLOW_NODES),
        "project_intent": project_intent,
    }
