from __future__ import annotations

import re
from typing import Iterable


FIELD_QUESTION_MAP_ZH = {
    "input_mode": "你现在的输入主要是单段视频，还是多段多视角素材？",
    "runtime_target": "你更偏接近实时输出，还是允许离线处理来换更高质量？",
    "hardware_budget": "这套流程主要跑在高性能工作站上，还是需要兼顾普通电脑也能运行？",
    "output_format": "你最后更希望输出稀疏点云、稠密点云，还是标准格式比如 PLY / LAS？",
    "semantic_integration_level": "语义信息这块你是希望先预留接口，还是希望第一版就直接把语义分割接进流程里？",
    "external_dependency_policy": "你更希望优先复用现成开源组件，还是希望方案尽量偏向自研可控？",
}

FIELD_QUESTION_MAP_EN = {
    "input_mode": "Is your input mainly a single drone video, or multiple multi-view clips?",
    "runtime_target": "Do you prefer near real-time output, or offline processing for higher quality?",
    "hardware_budget": "Will this run mostly on a high-performance workstation, or should it also work on regular machines?",
    "output_format": "Which output do you prefer first: sparse point cloud, dense point cloud, or standard formats such as PLY / LAS?",
    "semantic_integration_level": "For semantic information, do you want a first version with an interface only, or direct semantic segmentation integration now?",
    "external_dependency_policy": "Do you prefer reusing proven open-source components first, or leaning toward self-developed controllability?",
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
        "output_format": ("output_format", "ply", "las", "point cloud format"),
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

    qmap = FIELD_QUESTION_MAP_EN if lang == "en" else FIELD_QUESTION_MAP_ZH
    questions = [qmap[name] for name in normalized if name in qmap]

    summary = str(ctx.get("task_summary", "")).lower()
    pointcloud_ctx = any(k in summary for k in ("点云", "point cloud", "drone", "无人机", "建图", "mapping"))
    if not questions and pointcloud_ctx:
        # Default high-value pair for 3D-video-to-point-cloud first pass.
        base = ["input_mode", "runtime_target"]
        questions = [qmap[name] for name in base if name in qmap]

    max_questions = 2
    try:
        max_questions = max(1, min(3, int(ctx.get("max_questions", 2))))
    except Exception:
        max_questions = 2

    return questions[:max_questions]

