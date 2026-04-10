from __future__ import annotations

import re
from typing import Iterable

from .project_domain_profile import (
    DOMAIN_POINTCLOUD,
    DOMAIN_VISUAL_NOVEL,
    classify_project_domain,
)

FIELD_QUESTION_MAP_ZH = {
    "input_mode": "第一版你最想先接住哪类输入或资料？",
    "runtime_target": "第一版更偏桌面本地、命令行脚本，还是浏览器页面？",
    "hardware_budget": "第一版主要跑在高性能工作站上，还是普通电脑本地可运行就够？",
    "output_format": "第一版产出你更想先锁成什么：可运行界面、结构化 JSON，还是可导出的脚手架/脚本？",
    "semantic_integration_level": "如果有扩展能力，第一版你更希望先预留接口，还是直接把这部分能力接进主流程？",
    "external_dependency_policy": "第一版你更希望优先复用现成开源组件，还是尽量偏向自研可控？",
}

FIELD_QUESTION_MAP_ZH_POINTCLOUD = {
    "input_mode": "你现在的输入主要是单段视频，还是多段多视角素材？",
    "runtime_target": "你更偏接近实时输出，还是允许离线处理来换更高质量？",
    "hardware_budget": "这套流程主要跑在高性能工作站上，还是需要兼顾普通电脑也能运行？",
    "output_format": "你最后更希望输出稀疏点云、稠密点云，还是标准格式比如 PLY / LAS？",
    "semantic_integration_level": "语义信息这块你是希望先预留接口，还是希望第一版就直接把语义分割接进流程里？",
    "external_dependency_policy": "你更希望优先复用现成开源组件，还是希望方案尽量偏向自研可控？",
}

FIELD_QUESTION_MAP_ZH_VN = {
    "input_mode": "第一版你想先录入哪些资料：角色卡、章节大纲、场景列表，还是三者都要？",
    "runtime_target": "第一版你更想先做桌面本地工具，还是浏览器本地页面？",
    "hardware_budget": "第一版主要给普通 Windows 电脑本地使用就可以，还是要兼顾更轻量环境？",
    "output_format": "第一版导出你更想先锁定 Ren'Py 风格脚本骨架，还是结构化 JSON？",
    "semantic_integration_level": "如果后面要补剧情分析或标签能力，第一版你更想先预留接口，还是直接接进主流程？",
    "external_dependency_policy": "第一版你更希望优先复用现成组件，还是尽量偏向自己可控的实现？",
}

FIELD_QUESTION_MAP_EN = {
    "input_mode": "What is the main input or material V1 needs to accept first?",
    "runtime_target": "Should V1 be a desktop-local tool, a CLI/script flow, or a browser page first?",
    "hardware_budget": "Should V1 target a stronger workstation first, or is a normal local machine enough?",
    "output_format": "What should V1 produce first: a runnable UI, structured JSON, or an exportable scaffold/script?",
    "semantic_integration_level": "If there is an extension capability, should V1 reserve an interface first or wire it into the main flow now?",
    "external_dependency_policy": "Do you prefer reusing proven open-source components first, or leaning toward self-developed controllability?",
}

FIELD_QUESTION_MAP_EN_POINTCLOUD = {
    "input_mode": "Is your input mainly a single drone video, or multiple multi-view clips?",
    "runtime_target": "Do you prefer near real-time output, or offline processing for higher quality?",
    "hardware_budget": "Will this run mostly on a high-performance workstation, or should it also work on regular machines?",
    "output_format": "Which output do you prefer first: sparse point cloud, dense point cloud, or standard formats such as PLY / LAS?",
    "semantic_integration_level": "For semantic information, do you want a first version with an interface only, or direct semantic segmentation integration now?",
    "external_dependency_policy": "Do you prefer reusing proven open-source components first, or leaning toward self-developed controllability?",
}

FIELD_QUESTION_MAP_EN_VN = {
    "input_mode": "For V1, which inputs should land first: character cards, chapter outlines, scene lists, or all three?",
    "runtime_target": "Should V1 be a local desktop tool first, or a browser-based local page?",
    "hardware_budget": "Is a normal local Windows machine enough for V1, or should it target lighter environments too?",
    "output_format": "Which export should V1 lock first: a Ren'Py-style script skeleton or structured JSON?",
    "semantic_integration_level": "If you later want story analysis or tagging, should V1 reserve the interface first or wire it in now?",
    "external_dependency_policy": "Do you prefer reusing proven components first, or keeping the implementation as self-controlled as possible?",
}

_ALIASES = {
    "input_mode": "input_mode",
    "runtime_target": "runtime_target",
    "hardware_budget": "hardware_budget",
    "output_format": "output_format",
    "semantic_integration_level": "semantic_integration_level",
    "semantic": "semantic_integration_level",
    "external_dependency_policy": "external_dependency_policy",
    "external_policy": "external_dependency_policy",
    "externals": "external_dependency_policy",
    "dependency_policy": "external_dependency_policy",
}

_MISSING_RE = re.compile(r"\bmissing(?:\s+required)?\s+([A-Za-z0-9_]+)", re.IGNORECASE)


def _normalize_field_name(raw: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_]+", "_", str(raw or "").strip().lower()).strip("_")
    return _ALIASES.get(token, token)


def infer_missing_fields_from_text(text: str) -> list[str]:
    raw = str(text or "")
    low = raw.lower()
    fields: list[str] = []

    for match in _MISSING_RE.finditer(raw):
        name = _normalize_field_name(match.group(1))
        if name and name not in fields:
            fields.append(name)

    keyword_map = {
        "input_mode": ("input_mode", "single-view", "multi-view"),
        "runtime_target": ("runtime_target", "real-time", "offline"),
        "hardware_budget": ("hardware_budget", "hardware budget", "compute budget"),
        "output_format": ("output_format", "ply", "las", "point cloud format", "renpy", "ren'py", "json"),
        "semantic_integration_level": ("semantic_integration_level", "semantic integration", "semantic segmentation"),
        "external_dependency_policy": ("external_dependency_policy", "externals", "dependency policy"),
    }
    for field, keywords in keyword_map.items():
        if any(k in low for k in keywords):
            if field not in fields:
                fields.append(field)

    return fields


def rewrite_missing_requirements(missing_fields: Iterable[str], task_context: dict | None = None) -> list[str]:
    ctx = task_context if isinstance(task_context, dict) else {}
    lang = str(ctx.get("lang", "zh")).strip().lower()
    normalized: list[str] = []
    for field in missing_fields:
        name = _normalize_field_name(str(field))
        if name and name not in normalized:
            normalized.append(name)

    summary = str(ctx.get("task_summary", ""))
    domain = classify_project_domain([summary])
    if lang == "en":
        if domain == DOMAIN_POINTCLOUD:
            qmap = FIELD_QUESTION_MAP_EN_POINTCLOUD
        elif domain == DOMAIN_VISUAL_NOVEL:
            qmap = FIELD_QUESTION_MAP_EN_VN
        else:
            qmap = FIELD_QUESTION_MAP_EN
    else:
        if domain == DOMAIN_POINTCLOUD:
            qmap = FIELD_QUESTION_MAP_ZH_POINTCLOUD
        elif domain == DOMAIN_VISUAL_NOVEL:
            qmap = FIELD_QUESTION_MAP_ZH_VN
        else:
            qmap = FIELD_QUESTION_MAP_ZH
    questions = [qmap[name] for name in normalized if name in qmap]

    if not questions and domain == DOMAIN_POINTCLOUD:
        base = ["input_mode", "runtime_target"]
        questions = [qmap[name] for name in base if name in qmap]
    elif not questions and domain == DOMAIN_VISUAL_NOVEL:
        base = ["input_mode", "output_format"]
        questions = [qmap[name] for name in base if name in qmap]
    elif not questions:
        base = ["runtime_target", "output_format"]
        questions = [qmap[name] for name in base if name in qmap]

    max_questions = 2
    try:
        max_questions = max(1, min(3, int(ctx.get("max_questions", 2))))
    except Exception:
        max_questions = 2

    return questions[:max_questions]
