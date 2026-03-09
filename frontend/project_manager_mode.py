from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable


_GENERIC_LOW_SIGNAL_PATTERNS = (
    re.compile(r"^(我想做个项目|我想做一个项目|想做个项目|做个项目)$"),
    re.compile(r"^(create|start|do)\s+(a\s+)?project$", re.IGNORECASE),
    re.compile(r"^(帮我处理一下|安排一下|看一下|继续)$"),
)

_DENSE_KEYWORDS = (
    "3d",
    "视频",
    "video",
    "点云",
    "point cloud",
    "workflow",
    "pipeline",
    "无人机",
    "drone",
    "uav",
    "建图",
    "mapping",
    "语义",
    "semantic",
    "实时",
    "离线",
    "多视角",
    "单目",
    "速度",
    "质量",
    "成本",
    "ply",
    "las",
    "pcd",
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
        "project_type": "unknown",
        "input_mode": "unknown",
        "runtime_target": "unknown",
        "semantic_integration_level": "unknown",
        "deployment_boundary": "unknown",
        "output_format": "unknown",
    }

    if any(k in merged for k in ("点云", "建图", "视频")) or any(k in low for k in ("point cloud", "mapping", "video", "3d")):
        facts["project_type"] = "video_to_pointcloud"
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
        # Speed is known, but realtime/offline boundary still unresolved.
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


def build_default_assumptions(known_facts: dict[str, str]) -> dict[str, str]:
    assumptions: dict[str, str] = {
        "external_dependency_policy": "prefer_open_source_first",
        "delivery_strategy": "pipeline_first_speed_first",
        "output_format_default": "ply_first",
    }
    semantic_level = str(known_facts.get("semantic_integration_level", "unknown"))
    if semantic_level == "integrate_v1":
        assumptions["semantic_plan"] = "integrate_semantic_in_v1"
    else:
        assumptions["semantic_plan"] = "reserve_semantic_extension_first"
    if str(known_facts.get("deployment_boundary", "unknown")) == "unknown":
        assumptions["deployment_boundary_default"] = "workstation_first"
    return assumptions


def _zh_question_map() -> dict[str, str]:
    return {
        "input_mode": "你现在的输入主要是单目无人机视频，还是多段多视角素材？",
        "runtime_target": "你更偏向接近实时输出，还是允许离线处理来换更稳定的质量？",
        "deployment_boundary": "这套流程第一版你更希望部署在机载端，还是地面工作站/服务器端？",
        "hardware_budget": "第一版主要跑在高性能工作站，还是需要兼顾普通电脑也可运行？",
    }


def _en_question_map() -> dict[str, str]:
    return {
        "input_mode": "Is your input mainly monocular drone video, or multiple multi-view clips?",
        "runtime_target": "Do you prefer near real-time output, or offline processing for more stable quality?",
        "deployment_boundary": "For V1, should this run on edge/onboard devices or on ground workstations/servers?",
        "hardware_budget": "Should V1 target high-performance workstations first, or also run on regular machines?",
    }


def select_high_leverage_questions(known_facts: dict[str, str], lang: str, max_questions: int = 2) -> list[str]:
    language = str(lang or "zh").strip().lower()
    qmap = _en_question_map() if language == "en" else _zh_question_map()
    questions: list[str] = []

    input_mode = str(known_facts.get("input_mode", "unknown"))
    runtime_target = str(known_facts.get("runtime_target", "unknown"))
    deployment = str(known_facts.get("deployment_boundary", "unknown"))

    if input_mode in {"unknown", ""}:
        questions.append(qmap["input_mode"])
    if runtime_target in {"unknown", "", "speed_first_unresolved"}:
        questions.append(qmap["runtime_target"])
    if deployment in {"unknown", ""} and len(questions) < max(1, int(max_questions)):
        questions.append(qmap["deployment_boundary"])

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
        return "AeroCloud"
    if any(k in raw for k in ("无人机", "航拍")) or any(k in low for k in ("drone", "uav", "aerial")):
        if any(k in raw for k in ("点云", "建图")) or any(k in low for k in ("point cloud", "mapping")):
            return _hash_pick(["SkyMap Flow", "AeroCloud", "UAV Recon Flow", "SwiftPoint UAV"], seed=raw)
    if any(k in raw for k in ("点云", "重建")) or any(k in low for k in ("point cloud", "reconstruction")):
        return _hash_pick(["PointWeave", "CloudRoute", "ReconCloud"], seed=raw)
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

