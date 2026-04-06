from __future__ import annotations

import re
from typing import Any

from contracts.schemas.project_intent import ProjectIntent


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    raw = str(text or "").lower()
    return any(token and token.lower() in raw for token in tokens)


def _is_backend_test_default_output_request(raw: str) -> bool:
    has_backend_test = ("后端测试" in raw) or ("测试后端" in raw) or ("backend test" in raw) or ("test backend" in raw)
    has_default_output = ("默认输出" in raw) or ("直接输出" in raw) or ("default output" in raw)
    return has_backend_test and has_default_output


def _extract_constraints(text: str) -> dict[str, Any]:
    raw = str(text or "").lower()
    constraints: dict[str, Any] = {}
    if _contains_any(raw, ("benchmark", "regression", "基准", "回归")):
        constraints["project_generation_mode"] = "benchmark_regression"
    if _contains_any(raw, ("离线", "offline")):
        constraints["runtime_target"] = "offline"
    if _contains_any(raw, ("实时", "real-time", "realtime")):
        constraints["runtime_target"] = "realtime"
    if "qt" in raw:
        constraints["ui"] = "qt"
        constraints["delivery_shape"] = "gui_first"
    if _contains_any(raw, ("web", "网页", "browser", "浏览器")):
        constraints["delivery_shape"] = "web_first"
    if _contains_any(raw, ("sdk", "library", "package", "模块", "库", "toolkit")):
        constraints["delivery_shape"] = "tool_library_first"
    if "telegram" in raw:
        constraints["channel"] = "telegram"
    if _contains_any(raw, ("剧情", "叙事", "故事线", "storyline", "narrative")):
        constraints["project_domain"] = "story_reasoning_game"
    if _contains_any(raw, ("推理", "deduction", "mystery")):
        constraints["gameplay_focus"] = "reasoning"
    if _contains_any(raw, ("世界线", "worldline", "时间线", "timeline")):
        constraints["worldline_management"] = "required"
    if _contains_any(raw, ("记录", "整理", "梳理", "record", "organize")):
        constraints["story_knowledge_ops"] = "required"
    if _contains_any(raw, ("画图", "绘图", "diagram", "graph", "关系图", "流程图")):
        constraints["diagram_support"] = "required"
    if _is_backend_test_default_output_request(raw):
        constraints["backend_test_default_output"] = True
        constraints["delivery_trigger_mode"] = "support"
    return constraints


def _first_sentence(text: str) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    parts = re.split(r"[。！？!?;\n]+", raw, maxsplit=1)
    return str(parts[0] or raw).strip()


def _goal_summary(text: str, constraints: dict[str, Any]) -> str:
    sentence = _first_sentence(text)
    if sentence:
        sentence = re.sub(r"^(我想要?|请帮我|帮我|请)\s*", "", sentence).strip()
    if sentence:
        return sentence
    if constraints.get("project_domain") == "story_reasoning_game":
        return "构建一个可运行的剧情推理项目 MVP"
    return "构建一个可运行的 MVP 项目"


def _target_user(text: str, constraints: dict[str, Any]) -> str:
    raw = str(text or "").lower()
    if _contains_any(raw, ("创作者", "编剧", "写手", "作者", "creator", "writer")):
        return "内容创作者"
    if constraints.get("channel") == "telegram":
        return "通过 Telegram 触发项目的运营或客服人员"
    if constraints.get("project_domain") == "story_reasoning_game":
        return "需要整理剧情结构的叙事设计者"
    return "希望尽快验证想法的项目发起人"


def _problem_to_solve(text: str, constraints: dict[str, Any]) -> str:
    if constraints.get("project_domain") == "story_reasoning_game":
        return "把分散的剧情、角色和世界线信息整理成可持续推进的叙事项目流程"
    if constraints.get("backend_test_default_output"):
        return "用最少交互验证后端可以直接产出结果而不是停在追问上"
    return "把模糊目标收束成一个最小可运行项目，而不是只停留在流程和证明工件上"


def _mvp_scope(text: str, constraints: dict[str, Any]) -> list[str]:
    scope = ["提供可运行入口和 README 启动说明", "至少打通一条核心用户流程"]
    if constraints.get("worldline_management") == "required":
        scope.append("支持世界线/时间线记录与整理")
    if constraints.get("diagram_support") == "required":
        scope.append("支持关系图或流程图输出")
    if constraints.get("backend_test_default_output"):
        scope.append("后端测试模式下可直接返回默认结果")
    if constraints.get("delivery_shape") == "tool_library_first":
        scope.append("对外暴露可调用的服务接口")
    return scope


def _required_inputs(constraints: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    if constraints.get("channel") == "telegram":
        rows.append("Telegram 会话输入")
    if constraints.get("project_domain") == "story_reasoning_game":
        rows.append("剧情设定、角色信息、世界线素材")
    if not rows:
        rows.append("用户目标描述")
    return rows


def _required_outputs(constraints: dict[str, Any]) -> list[str]:
    rows = ["可运行项目代码", "README 启动说明", "至少一条核心流程的验证结果"]
    if constraints.get("diagram_support") == "required":
        rows.append("结构图或导出内容")
    return rows


def _hard_constraints(text: str, constraints: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    if constraints.get("runtime_target"):
        rows.append(f"runtime_target={constraints['runtime_target']}")
    if constraints.get("delivery_shape"):
        rows.append(f"delivery_shape={constraints['delivery_shape']}")
    if constraints.get("project_generation_mode"):
        rows.append(f"project_generation_mode={constraints['project_generation_mode']}")
    if constraints.get("backend_test_default_output"):
        rows.append("backend test should allow direct default output")
    if "不要" in str(text or ""):
        rows.append("respect explicit negative requirements from the user text")
    return rows


def _assumptions(text: str, constraints: dict[str, Any]) -> list[str]:
    rows = ["默认先生成最小可运行版本，再逐步扩展非核心能力"]
    if not constraints.get("delivery_shape"):
        rows.append("默认交付形态采用最容易验证的闭环入口")
    if not constraints.get("runtime_target"):
        rows.append("未指定部署环境时默认按本地可运行优先")
    if constraints.get("project_domain") == "story_reasoning_game":
        rows.append("未给出完整剧情资料时先提供可扩展的数据结构和示例流程")
    return rows


def _blocking_unknowns(text: str, constraints: dict[str, Any]) -> list[str]:
    raw = str(text or "").strip()
    if len(raw) < 8:
        return ["需要至少说明你想做什么项目，以及它要解决什么问题"]
    if not _contains_any(raw, ("项目", "系统", "工具", "bot", "游戏", "workflow", "pipeline", "app", "应用", "服务")):
        return ["需要确认你想交付的是项目、工具还是服务"]
    return []


def _project_like_signal(text: str, constraints: dict[str, Any]) -> bool:
    if constraints:
        return True
    return _contains_any(text, ("项目", "系统", "工具", "bot", "游戏", "workflow", "pipeline", "app", "应用", "服务"))


def _non_blocking_unknowns(constraints: dict[str, Any]) -> list[str]:
    rows: list[str] = []
    if not constraints.get("delivery_shape"):
        rows.append("尚未明确交付形态，先按最小闭环入口假设")
    if not constraints.get("runtime_target"):
        rows.append("尚未明确运行环境，先按本地 smoke run 假设")
    return rows


def _open_questions(blocking_unknowns: list[str], non_blocking_unknowns: list[str]) -> list[str]:
    return list(blocking_unknowns) + [f"非阻塞待确认: {row}" for row in non_blocking_unknowns]


def _acceptance_criteria(constraints: dict[str, Any]) -> list[str]:
    rows = ["README 能指导启动项目", "项目存在真实可运行入口", "至少一条核心用户流程通过 smoke run"]
    if constraints.get("worldline_management") == "required":
        rows.append("世界线整理流程可执行")
    if constraints.get("diagram_support") == "required":
        rows.append("图结构或导出内容可生成")
    return rows


def collect_project_intent_payload(*, latest_user_text: str, constraints: dict[str, Any]) -> dict[str, Any]:
    blocking_unknowns = _blocking_unknowns(latest_user_text, constraints)
    non_blocking_unknowns = _non_blocking_unknowns(constraints)
    project_intent = ProjectIntent(
        goal_summary=_goal_summary(latest_user_text, constraints),
        target_user=_target_user(latest_user_text, constraints),
        problem_to_solve=_problem_to_solve(latest_user_text, constraints),
        mvp_scope=_mvp_scope(latest_user_text, constraints),
        required_inputs=_required_inputs(constraints),
        required_outputs=_required_outputs(constraints),
        hard_constraints=_hard_constraints(latest_user_text, constraints),
        assumptions=_assumptions(latest_user_text, constraints),
        open_questions=_open_questions(blocking_unknowns, non_blocking_unknowns),
        acceptance_criteria=_acceptance_criteria(constraints),
    )
    return project_intent.to_payload()


def _understanding_summary(intent: ProjectIntent, *, blocking_unknowns: list[str], non_blocking_unknowns: list[str]) -> str:
    lines = [
        f"目标: {intent.goal_summary}",
        f"用户: {intent.target_user}",
        f"问题: {intent.problem_to_solve}",
        f"MVP: {'；'.join(intent.mvp_scope[:3])}",
    ]
    if blocking_unknowns:
        lines.append(f"阻塞信息: {'；'.join(blocking_unknowns)}")
    elif non_blocking_unknowns:
        lines.append(f"默认假设: {'；'.join(non_blocking_unknowns)}")
    return " | ".join(lines)


class RequirementCollector:
    def collect(self, *, mode: str, latest_user_text: str, history: list[str]) -> dict[str, Any]:
        text = str(latest_user_text or "").strip()
        constraints = _extract_constraints(text)
        blocking_unknowns = _blocking_unknowns(text, constraints)
        non_blocking_unknowns = _non_blocking_unknowns(constraints)
        intent = ProjectIntent.from_payload(collect_project_intent_payload(latest_user_text=text, constraints=constraints), user_goal=text)
        summary = {
            "mode": str(mode or "").upper() or "SMALLTALK",
            "latest_user_text": text,
            "history_digest": [str(item) for item in history[-3:]],
            "constraints": constraints,
            "project_intent": intent.to_payload(),
            "blocking_unknowns": blocking_unknowns,
            "non_blocking_unknowns": non_blocking_unknowns,
            "understanding_summary": _understanding_summary(intent, blocking_unknowns=blocking_unknowns, non_blocking_unknowns=non_blocking_unknowns),
        }
        summary["is_project_like"] = bool(summary["mode"].startswith("PROJECT")) or _project_like_signal(text, constraints)
        summary["can_start_generation"] = bool(summary["is_project_like"]) and not blocking_unknowns
        return summary


def collect_frontend_constraints(*, mode: str, latest_user_text: str, history: list[str]) -> dict[str, Any]:
    try:
        summary = RequirementCollector().collect(mode=mode, latest_user_text=latest_user_text, history=history)
    except Exception:
        return {}
    constraints = summary.get("constraints", {}) if isinstance(summary, dict) else {}
    return dict(constraints) if isinstance(constraints, dict) else {}


def collect_frontend_request_context(*, latest_user_text: str) -> dict[str, Any]:
    summary = RequirementCollector().collect(mode="PROJECT_DETAIL", latest_user_text=latest_user_text, history=[])
    return {
        "constraints": dict(summary.get("constraints", {})) if isinstance(summary.get("constraints", {}), dict) else {},
        "project_intent": dict(summary.get("project_intent", {})) if isinstance(summary.get("project_intent", {}), dict) else {},
        "understanding_summary": str(summary.get("understanding_summary", "")).strip(),
    }
