from __future__ import annotations

import re


def normalize_analysis_md(raw_text: str, *, goal: str) -> str:
    text = str(raw_text or "").strip()
    flat_goal = re.sub(r"\s+", " ", str(goal or "").strip())
    flat_text = re.sub(r"\s+", " ", text)
    bullet_lines = [line.strip() for line in text.splitlines() if line.strip().startswith(("-", "*"))]
    summary = ""
    for line in text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            summary = stripped
            break
    if not summary:
        summary = "收敛成一个可执行 MVP，不扩散范围。"
    if bullet_lines:
        summary = bullet_lines[0].lstrip("-*").strip() or summary

    goal_text = str(goal or "").strip() or "dispatch-goal"
    deliverables = "至少提供高价值截图与项目包，成功时可进入 public delivery。"
    if any(token in goal_text.lower() for token in ("upload", "csv", "导出", "export")):
        user_path = "上传输入文件 -> 触发处理 -> 查看结果 -> 导出结果。"
        boundary = "只做单一上传/处理/导出主链，不扩展多步骤协同、账号系统、云端同步。"
        entry = "主页面提供上传区、结果区、导出按钮。"
    elif any(token in goal_text.lower() for token in ("landing", "hero", "faq", "cta", "落地页", "单页")):
        user_path = "打开首页 -> 浏览 hero/功能区/FAQ -> 点击 CTA。"
        boundary = "只做单页展示主链，不扩展后台、登录、复杂 CMS。"
        entry = "首页 `index.html` 作为单一入口。"
    else:
        user_path = "进入主页面 -> 完成一个核心动作 -> 查看结果或产物。"
        boundary = "只做一个核心用户路径的 MVP，不扩展多角色、多工作台、多模态并行链路。"
        entry = "提供一个明确入口页或启动入口。"

    return "\n".join(
        [
            "# Analysis",
            "",
            f"Goal: {flat_goal or goal_text}",
            f"Reason: {flat_text or summary}",
            "",
            "## Core Goal",
            f"- {goal_text}",
            "",
            "## Single User Path",
            f"- {user_path}",
            "",
            "## MVP Boundary",
            f"- {boundary}",
            "- 技术落点优先使用当前默认生成链路，不额外引入联网依赖。",
            "",
            "## Entry And Flow",
            f"- {entry}",
            "- 产物必须能进入 smoke，再进入 screenshot / package / delivery。",
            "",
            "## Not In Scope",
            "- 不扩展额外后台、账户体系、复杂多步骤工作流。",
            "- 不为了展示而添加与主路径无关的附属页面。",
            "",
            "## Delivery Expectation",
            f"- {deliverables}",
            "- 若 verify/pass 且存在高价值截图，应继续收口到 package 与 delivery manifest。",
            "",
            "## Working Summary",
            f"- {summary}",
            "",
        ]
    )
