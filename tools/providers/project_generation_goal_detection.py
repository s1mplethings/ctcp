from __future__ import annotations

import re

from tools.providers.project_generation_decisions import NARRATIVE_KEYWORDS, contains_any as _contains_any

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
PROJECT_STATUS_QUERY_HINTS = (
    "你还有之前",
    "之前生成的项目",
    "之前的项目",
    "上次生成",
    "历史项目",
    "还在吗",
    "还在不在",
    "还保存着",
    "还有吗",
    "还能找到",
    "现在什么状态",
    "项目状态",
    "项目进度",
    "do you still have",
    "previous project",
    "last generated project",
    "project status",
    "progress update",
    "still there",
)
PROJECT_CREATE_ACTION_HINTS = (
    "做一个",
    "做个",
    "搭一个",
    "搭建一个",
    "创建一个",
    "新建一个",
    "生成一个",
    "实现一个",
    "写一个",
    "创建项目",
    "新建项目",
    "生成项目",
    "搭建项目",
    "build a ",
    "create a ",
    "generate a ",
    "make a ",
    "develop a ",
    "scaffold",
)


def _has_create_action_signal(text: str, low: str) -> bool:
    if any(token in text or token in low for token in PROJECT_CREATE_ACTION_HINTS):
        return True
    if re.search(r"(帮我|请|麻烦).{0,8}(做|搭|创建|生成|实现|开发)", text):
        return True
    if re.search(r"(做|搭|创建|生成|实现|开发|写).{0,2}(一个|个|套|款)", text):
        return True
    if re.search(r"\b(build|create|generate|make|develop|scaffold)\b.{0,24}\b(project|app|tool|service|workflow|dashboard|platform|repo)\b", low):
        return True
    return False


def _is_history_or_status_query(text: str, low: str) -> bool:
    if not any(token in text or token in low for token in PROJECT_STATUS_QUERY_HINTS):
        return False
    if "?" in text or "？" in text:
        return True
    return any(token in text or token in low for token in ("吗", "么", "状态", "进度", "history", "status", "progress"))


def is_project_generation_goal_text(goal: str) -> bool:
    text = str(goal or "").strip()
    if not text:
        return False
    low = text.lower()
    binding = any(token in text or token in low for token in PROJECT_GENERATION_BINDING_HINTS)
    rerun = any(token in text or token in low for token in PROJECT_GENERATION_RERUN_HINTS)
    domain_lift = any(token in text or token in low for token in PROJECT_GENERATION_DOMAIN_LIFT_HINTS)
    rough_goal_signal = any(token in text or token in low for token in ("粗目标", "rough goal", "product definition"))
    has_project_signal = _contains_any(text, NARRATIVE_KEYWORDS + PROJECT_GENERATION_KEYWORDS)
    has_create_action = _has_create_action_signal(text, low)
    if binding and (rerun or domain_lift):
        return True
    if _is_history_or_status_query(text, low) and not (has_create_action or rerun or domain_lift):
        return False
    return bool(has_project_signal and (has_create_action or rough_goal_signal or rerun or domain_lift or binding))
