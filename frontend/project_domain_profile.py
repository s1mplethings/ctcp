from __future__ import annotations

import re
from typing import Iterable


DOMAIN_POINTCLOUD = "pointcloud_pipeline"
DOMAIN_VISUAL_NOVEL = "visual_novel_assistant"
DOMAIN_GENERIC = "generic_software_project"

_POINTCLOUD_MARKERS = (
    "点云",
    "point cloud",
    "ply",
    "las",
    "pcd",
    "建图",
    "mapping",
    "重建",
    "reconstruction",
    "无人机",
    "drone",
    "uav",
    "航拍",
    "语义分割",
    "semantic segmentation",
    "单目",
    "monocular",
    "多视角",
    "multi-view",
)

_VISUAL_NOVEL_MARKERS = (
    "vn",
    "visual novel",
    "ren'py",
    "renpy",
    "角色卡",
    "角色资料",
    "角色设定",
    "章节",
    "章节大纲",
    "场景",
    "场景列表",
    "剧情",
    "剧情流程",
    "立绘",
    "背景",
    "脚本骨架",
    "分支剧情",
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def merge_project_text(texts: Iterable[str]) -> str:
    return " ".join(_norm(item) for item in texts if _norm(item))


def has_pointcloud_markers(text: str) -> bool:
    raw = _norm(text)
    low = raw.lower()
    return any(marker in raw or marker in low for marker in _POINTCLOUD_MARKERS)


def has_visual_novel_markers(text: str) -> bool:
    raw = _norm(text)
    low = raw.lower()
    return any(marker in raw or marker in low for marker in _VISUAL_NOVEL_MARKERS)


def classify_project_domain(texts: Iterable[str]) -> str:
    merged = merge_project_text(texts)
    if not merged:
        return DOMAIN_GENERIC
    if has_pointcloud_markers(merged):
        return DOMAIN_POINTCLOUD
    if has_visual_novel_markers(merged):
        return DOMAIN_VISUAL_NOVEL
    return DOMAIN_GENERIC
