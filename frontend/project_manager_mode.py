from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from .project_domain_profile import (
    DOMAIN_GENERIC,
    DOMAIN_POINTCLOUD,
    DOMAIN_VISUAL_NOVEL,
    classify_project_domain,
)

_GENERIC_LOW_SIGNAL_PATTERNS = (
    re.compile(r"^(我想做个项目|我想做一个项目|想做个项目|做个项目)$"),
    re.compile(r"^(create|start|do)\s+(a\s+)?project$", re.IGNORECASE),
    re.compile(r"^(帮我处理一下|安排一下|看一下|继续)$"),
)

_DENSE_KEYWORDS = (
    "项目",
    "工具",
    "系统",
    "助手",
    "应用",
    "界面",
    "workflow",
    "pipeline",
    "输入",
    "输出",
    "导出",
    "json",
    "脚本",
    "角色",
    "章节",
    "场景",
    "剧情",
    "ren'py",
    "renpy",
    "点云",
    "point cloud",
    "ply",
    "las",
    "pcd",
    "无人机",
    "drone",
    "uav",
    "建图",
    "mapping",
    "实时",
    "离线",
    "本地",
    "desktop",
    "browser",
    "web",
)

_GENERIC_QUESTION_FRAGMENTS_ZH = (
    "你想做什么类型的项目",
    "能具体说说你的需求吗",
    "请提供更多信息",
    "还有什么补充吗",
)

_GENERIC_QUESTION_FRAGMENTS_EN = (
    "what type of project",
    "can you share more details",
    "please provide more information",
    "anything else to add",
)


@dataclass(frozen=True)
class ProjectManagerContext:
    requirement_summary: str
    known_facts: dict[str, str]
    assumptions: dict[str, str]
    high_leverage_questions: tuple[str, ...]
    project_name: str
    signal_score: float


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _is_low_signal_line(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return True
    return any(p.match(raw) for p in _GENERIC_LOW_SIGNAL_PATTERNS)


def requirement_information_score(text: str) -> float:
    raw = _norm(text)
    if not raw:
        return 0.0
    low = raw.lower()
    if _is_low_signal_line(raw):
        return 0.1
    length_score = min(4.0, len(raw) / 36.0)
    keyword_hits = sum(1.0 for k in _DENSE_KEYWORDS if k in low or k in raw)
    punctuation_bonus = 0.8 if any(ch in raw for ch in ("，", ",", "；", ";", "。", ".")) else 0.0
    explicit_goal_bonus = 1.0 if any(k in raw for k in ("目标", "优先", "尽可能", "核心")) else 0.0
    return length_score + min(6.0, keyword_hits * 0.75) + punctuation_bonus + explicit_goal_bonus


def select_best_requirement_source(user_messages: Iterable[str]) -> str:
    msgs = [_norm(x) for x in user_messages if _norm(x)]
    if not msgs:
        return ""
    best_text = msgs[-1]
    best_score = -1.0
    total = max(1, len(msgs))
    for idx, text in enumerate(msgs):
        recency_bonus = (idx + 1) / total * 0.7
        score = requirement_information_score(text) + recency_bonus
        if score > best_score:
            best_score = score
            best_text = text
    return best_text


def extract_known_project_facts(user_messages: Iterable[str], requirement_text: str = "") -> dict[str, str]:
    merged_rows = [_norm(x) for x in user_messages if _norm(x)]
    if _norm(requirement_text):
        merged_rows.append(_norm(requirement_text))
    merged = " ".join(merged_rows)
    low = merged.lower()

    facts: dict[str, str] = {
        "project_type": DOMAIN_GENERIC,
        "input_mode": "unknown",
        "runtime_target": "unknown",
        "semantic_integration_level": "unknown",
        "deployment_boundary": "unknown",
        "output_format": "unknown",
    }
    domain = classify_project_domain([merged])
    facts["project_type"] = domain

    if domain == DOMAIN_POINTCLOUD:
        if any(k in merged for k in ("无人机", "航拍")) or any(k in low for k in ("drone", "uav", "aerial")):
            facts["viewpoint"] = "uav"
        if any(k in merged for k in ("单目", "单段")) or any(k in low for k in ("single-view", "single view", "monocular")):
            facts["input_mode"] = "single_view"
        elif any(k in merged for k in ("多视角", "多段", "多机位")) or any(k in low for k in ("multi-view", "multi view", "multi clip")):
            facts["input_mode"] = "multi_view"

        realtime_markers = ("接近实时", "实时", "低延迟")
        offline_markers = ("离线", "批处理", "高质量优先")
        speed_markers = ("尽可能快", "越快越好", "优先速度", "高速")
        if any(k in merged for k in realtime_markers) or any(k in low for k in ("real-time", "realtime", "near real-time", "low latency")):
            facts["runtime_target"] = "near_realtime"
        elif any(k in merged for k in offline_markers) or any(k in low for k in ("offline", "batch")):
            facts["runtime_target"] = "offline_quality"
        elif any(k in merged for k in speed_markers) or any(k in low for k in ("as fast as possible", "speed first", "fastest")):
            facts["runtime_target"] = "speed_first_unresolved"

        if any(k in merged for k in ("语义", "语义信息", "语义分割")) or any(k in low for k in ("semantic", "segmentation")):
            if any(k in merged for k in ("第一版就", "首版就", "必须先接")) or any(k in low for k in ("must in v1", "first version must")):
                facts["semantic_integration_level"] = "integrate_v1"
            else:
                facts["semantic_integration_level"] = "optional_or_phase2"

        if any(k in low for k in ("edge", "on-device", "onboard")) or any(k in merged for k in ("机载", "边缘设备", "端侧")):
            facts["deployment_boundary"] = "edge_device"
        elif any(k in low for k in ("cloud", "server", "workstation")) or any(k in merged for k in ("云端", "服务器", "工作站")):
            facts["deployment_boundary"] = "server_side"

        if "ply" in low:
            facts["output_format"] = "ply"
        elif "las" in low:
            facts["output_format"] = "las"
        elif "pcd" in low:
            facts["output_format"] = "pcd"
        return facts

    if domain == DOMAIN_VISUAL_NOVEL:
        if all(token in merged for token in ("角色", "章节", "场景")):
            facts["input_mode"] = "story_asset_bundle"
        elif any(token in merged for token in ("角色", "角色卡")):
            facts["input_mode"] = "character_first"
        if any(token in merged for token in ("桌面", "本地工具", "windows")) or any(
            token in low for token in ("desktop", "local tool", "windows")
        ):
            facts["runtime_target"] = "desktop_local"
        elif any(token in merged for token in ("网页", "浏览器", "web")) or any(token in low for token in ("browser", "web")):
            facts["runtime_target"] = "browser_local"
        if any(token in merged for token in ("ren'py", "renpy", "脚本骨架")):
            facts["output_format"] = "renpy_script"
        elif "json" in low:
            facts["output_format"] = "structured_json"
        return facts

    if any(token in merged for token in ("桌面", "本地工具", "windows")) or any(
        token in low for token in ("desktop", "local tool", "windows")
    ):
        facts["runtime_target"] = "desktop_local"
    elif any(token in merged for token in ("网页", "浏览器", "web")) or any(token in low for token in ("browser", "web")):
        facts["runtime_target"] = "browser_local"
    elif any(token in merged for token in ("命令行", "脚本")) or any(token in low for token in ("cli", "command line", "script")):
        facts["runtime_target"] = "cli_local"
    if "json" in low:
        facts["output_format"] = "structured_json"
    elif any(token in merged for token in ("脚本", "脚手架")) or "scaffold" in low:
        facts["output_format"] = "script_or_scaffold"

    return facts


def build_default_assumptions(known_facts: dict[str, str]) -> dict[str, str]:
    project_type = str(known_facts.get("project_type", DOMAIN_GENERIC)).strip().lower()
    assumptions: dict[str, str] = {"external_dependency_policy": "prefer_open_source_first"}
    if project_type == DOMAIN_POINTCLOUD:
        assumptions.update(
            {
                "delivery_strategy": "pipeline_first_speed_first",
                "output_format_default": "ply_first",
            }
        )
    elif project_type == DOMAIN_VISUAL_NOVEL:
        assumptions.update(
            {
                "delivery_strategy": "mvp_first_visual_workbench",
                "output_format_default": "renpy_or_json_first",
            }
        )
    else:
        assumptions.update(
            {
                "delivery_strategy": "mvp_first_minimal_user_flow",
                "output_format_default": "fit_to_goal",
            }
        )
    semantic_level = str(known_facts.get("semantic_integration_level", "unknown"))
    if project_type == DOMAIN_POINTCLOUD and semantic_level == "integrate_v1":
        assumptions["semantic_plan"] = "integrate_semantic_in_v1"
    elif project_type == DOMAIN_POINTCLOUD:
        assumptions["semantic_plan"] = "reserve_semantic_extension_first"
    if str(known_facts.get("deployment_boundary", "unknown")) == "unknown":
        assumptions["deployment_boundary_default"] = "local_first"
    return assumptions


def _zh_question_map(project_type: str) -> dict[str, str]:
    if project_type == DOMAIN_POINTCLOUD:
        return {
            "input_mode": "你现在的输入主要是单目无人机视频，还是多段多视角素材？",
            "runtime_target": "你更偏向接近实时输出，还是允许离线处理来换更稳定的质量？",
            "deployment_boundary": "这套流程第一版你更希望部署在机载端，还是地面工作站/服务器端？",
            "hardware_budget": "第一版主要跑在高性能工作站，还是需要兼顾普通电脑也可运行？",
            "output_format": "你第一版更想先锁定哪种输出：PLY、LAS，还是 PCD？",
        }
    if project_type == DOMAIN_VISUAL_NOVEL:
        return {
            "input_mode": "第一版你想先录入哪些资料：角色卡、章节大纲、场景列表，还是三者都要？",
            "runtime_target": "第一版你更想先做桌面本地工具，还是浏览器本地页面？",
            "output_format": "第一版导出你更想先锁定 Ren'Py 风格脚本骨架，还是结构化 JSON？",
            "deployment_boundary": "第一版先给你自己本地使用，还是一开始就要考虑多人共享协作？",
        }
    return {
        "input_mode": "第一版你最想先接住哪类输入或资料？",
        "runtime_target": "第一版更偏桌面本地、命令行脚本，还是浏览器页面？",
        "output_format": "第一版产出你更想先锁成什么：可运行界面、结构化 JSON，还是可导出的脚手架/脚本？",
        "deployment_boundary": "第一版先给你自己本地使用，还是一开始就需要多人共享或部署？",
    }


def _en_question_map(project_type: str) -> dict[str, str]:
    if project_type == DOMAIN_POINTCLOUD:
        return {
            "input_mode": "Is your input mainly monocular drone video, or multiple multi-view clips?",
            "runtime_target": "Do you prefer near real-time output, or offline processing for more stable quality?",
            "deployment_boundary": "For V1, should this run on edge/onboard devices or on ground workstations/servers?",
            "hardware_budget": "Should V1 target high-performance workstations first, or also run on regular machines?",
            "output_format": "Which output should V1 lock first: PLY, LAS, or PCD?",
        }
    if project_type == DOMAIN_VISUAL_NOVEL:
        return {
            "input_mode": "For V1, which inputs should land first: character cards, chapter outlines, scene lists, or all three?",
            "runtime_target": "Should V1 be a local desktop tool first, or a browser-based local page?",
            "output_format": "Which export should V1 lock first: a Ren'Py-style script skeleton or structured JSON?",
            "deployment_boundary": "Is V1 only for your local use first, or should it consider shared collaboration from day one?",
        }
    return {
        "input_mode": "What is the main input or material V1 needs to accept first?",
        "runtime_target": "Should V1 be a desktop-local tool, a CLI/script flow, or a browser page first?",
        "output_format": "What should V1 produce first: a runnable UI, structured JSON, or an exportable scaffold/script?",
        "deployment_boundary": "Is V1 for your own local use first, or should it support shared deployment from day one?",
    }


def select_high_leverage_questions(known_facts: dict[str, str], lang: str, max_questions: int = 2) -> list[str]:
    language = str(lang or "zh").strip().lower()
    project_type = str(known_facts.get("project_type", DOMAIN_GENERIC)).strip().lower()
    qmap = _en_question_map(project_type) if language == "en" else _zh_question_map(project_type)
    questions: list[str] = []

    input_mode = str(known_facts.get("input_mode", "unknown"))
    runtime_target = str(known_facts.get("runtime_target", "unknown"))
    deployment = str(known_facts.get("deployment_boundary", "unknown"))
    output_format = str(known_facts.get("output_format", "unknown"))

    if project_type == DOMAIN_POINTCLOUD:
        if input_mode in {"unknown", ""}:
            questions.append(qmap["input_mode"])
        if runtime_target in {"unknown", "", "speed_first_unresolved"}:
            questions.append(qmap["runtime_target"])
        if deployment in {"unknown", ""} and len(questions) < max(1, int(max_questions)):
            questions.append(qmap["deployment_boundary"])
    elif project_type == DOMAIN_VISUAL_NOVEL:
        if input_mode in {"unknown", ""}:
            questions.append(qmap["input_mode"])
        if output_format in {"unknown", ""}:
            questions.append(qmap["output_format"])
        if runtime_target in {"unknown", ""} and len(questions) < max(1, int(max_questions)):
            questions.append(qmap["runtime_target"])
    else:
        if runtime_target in {"unknown", ""}:
            questions.append(qmap["runtime_target"])
        if output_format in {"unknown", ""}:
            questions.append(qmap["output_format"])
        if input_mode in {"unknown", ""} and len(questions) < max(1, int(max_questions)):
            questions.append(qmap["input_mode"])

    limit = max(1, min(2, int(max_questions or 2)))
    return questions[:limit]


def _hash_pick(options: list[str], seed: str) -> str:
    if not options:
        return ""
    h = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()
    idx = int(h[:8], 16) % len(options)
    return options[idx]


def suggest_domain_project_name(requirement_text: str, lang: str = "zh") -> str:
    raw = _norm(requirement_text)
    low = raw.lower()
    if not raw:
        return "Northline"
    project_type = classify_project_domain([raw])
    if project_type == DOMAIN_POINTCLOUD:
        if any(k in raw for k in ("无人机", "航拍")) or any(k in low for k in ("drone", "uav", "aerial")):
            return _hash_pick(["SkyMap Flow", "AeroCloud", "UAV Recon Flow", "SwiftPoint UAV"], seed=raw)
        return _hash_pick(["PointWeave", "CloudRoute", "ReconCloud"], seed=raw)
    if project_type == DOMAIN_VISUAL_NOVEL:
        if str(lang).lower() == "en":
            return _hash_pick(["Story Atlas", "Scene Ledger", "Branch Desk"], seed=raw)
        return _hash_pick(["剧情台账", "场景工坊", "分支地图"], seed=raw)
    if str(lang).lower() == "en":
        return _hash_pick(["Project Northline", "Ops Vector"], seed=raw)
    return _hash_pick(["北线计划", "向量推进"], seed=raw)


def build_project_manager_context(
    user_messages: Iterable[str],
    *,
    lang: str = "zh",
    max_questions: int = 2,
) -> ProjectManagerContext:
    msgs = [_norm(x) for x in user_messages if _norm(x)]
    best = select_best_requirement_source(msgs)
    facts = extract_known_project_facts(msgs, best)
    assumptions = build_default_assumptions(facts)
    questions = select_high_leverage_questions(facts, lang, max_questions=max_questions)
    project_name = suggest_domain_project_name(best, lang=lang)
    return ProjectManagerContext(
        requirement_summary=best,
        known_facts=facts,
        assumptions=assumptions,
        high_leverage_questions=tuple(questions),
        project_name=project_name,
        signal_score=requirement_information_score(best),
    )


def is_generic_intake_question(question: str, lang: str = "zh") -> bool:
    q = _norm(question).lower()
    if not q:
        return False
    if str(lang).lower() == "en":
        return any(token in q for token in _GENERIC_QUESTION_FRAGMENTS_EN)
    return any(token in q for token in _GENERIC_QUESTION_FRAGMENTS_ZH)
