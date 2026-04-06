from __future__ import annotations

import json
from pathlib import Path
from typing import Any

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
TOOL_KEYWORDS = ("sdk", "library", "package", "module", "import", "api", "toolkit", "库", "模块")
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
USER_CONTEXT_PREFIXES = ("artifacts/frontend_uploads/", "input/", "inputs/", "requirements/", "specs/")


def contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    haystack = str(text or "").lower()
    return any(keyword and keyword.lower() in haystack for keyword in keywords)


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


def detect_project_type(goal: str, context_files: list[dict[str, Any]] | None = None, *, execution_mode: str, benchmark_case_value: str, project_intent: dict[str, Any] | None = None) -> str:
    signal = intent_text_signal(project_intent or {})
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
) -> tuple[str, str]:
    if project_type == "narrative_copilot":
        return "narrative_copilot", "project_type:narrative_copilot"

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

    matched, source = _has(WEB_SERVICE_KEYWORDS + WEB_KEYWORDS)
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
) -> tuple[str, str]:
    signal = intent_text_signal(project_intent or {})
    explicit = normalize_delivery_shape(str(constraints.get("delivery_shape", "")).strip() or str(constraints.get("project_delivery_shape", "")).strip())
    if explicit:
        return explicit, "constraints.delivery_shape"
    if normalize_mode(execution_mode) == BENCHMARK_MODE and contains_any(benchmark_case_value, BENCHMARK_HINTS + NARRATIVE_KEYWORDS):
        return CLI_SHAPE, f"benchmark_case:{benchmark_case_value or 'benchmark'}"
    if contains_any(signal, WEB_KEYWORDS):
        return WEB_SHAPE, "project_intent:web_keywords"
    if contains_any(signal, GUI_KEYWORDS):
        return GUI_SHAPE, "project_intent:gui_keywords"
    if contains_any(signal, TOOL_KEYWORDS):
        return TOOL_SHAPE, "project_intent:tool_keywords"
    if contains_any(goal, WEB_KEYWORDS):
        return WEB_SHAPE, "goal:web_keywords"
    if contains_any(goal, GUI_KEYWORDS):
        return GUI_SHAPE, "goal:gui_keywords"
    if contains_any(goal, TOOL_KEYWORDS):
        return TOOL_SHAPE, "goal:tool_keywords"
    if contains_any(goal, CLI_KEYWORDS):
        return CLI_SHAPE, "goal:cli_keywords"
    signal = user_context_signal(context_files)
    if contains_any(signal, WEB_KEYWORDS):
        return WEB_SHAPE, "context:web_keywords"
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
    value = "".join(ch if ch.isalnum() else "_" for ch in str(project_id or "").lower()).strip("_")
    if value in {"json", "sys", "re", "typing", "pathlib", "os", "subprocess", "asyncio", "unittest"}:
        value = f"project_{value}"
    return value or ("narrative_copilot" if project_type == "narrative_copilot" else "project_copilot")


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
    benchmark_case_value = benchmark_case(constraints)
    src_mode = str(src.get("execution_mode", "")).strip() if isinstance(src, dict) else ""
    execution_mode = normalize_mode(
        str(constraints.get("project_generation_mode", "")).strip()
        or str(constraints.get("execution_mode", "")).strip()
        or src_mode
        or (BENCHMARK_MODE if contains_any(benchmark_case_value, BENCHMARK_HINTS + NARRATIVE_KEYWORDS) else "")
    )
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
    )
    project_archetype, archetype_source = detect_project_archetype(
        goal,
        project_type=project_type,
        delivery_shape=delivery_shape,
        context_files=context_files,
        project_intent=project_intent,
    )
    visual_required, screenshot_required, visual_status = visual_requirements(delivery_shape)
    return {
        "execution_mode": execution_mode,
        "benchmark_case": benchmark_case_value,
        "project_type": project_type,
        "project_archetype": project_archetype,
        "project_type_decision_source": f"benchmark_case:{benchmark_case_value}" if execution_mode == BENCHMARK_MODE and benchmark_case_value else "goal_or_context",
        "project_archetype_decision_source": archetype_source,
        "delivery_shape": delivery_shape,
        "shape_decision_source": shape_source,
        "demo_required": demo_required(goal, execution_mode, constraints, project_intent=project_intent),
        "visual_evidence_required": visual_required,
        "screenshot_required": screenshot_required,
        "visual_evidence_status": visual_status,
        "benchmark_sample_applied": execution_mode == BENCHMARK_MODE and project_type == "narrative_copilot",
        "decision_nodes": list(STRONG_DECISION_NODES),
        "flow_nodes": list(FLOW_NODES),
        "project_intent": project_intent,
    }
