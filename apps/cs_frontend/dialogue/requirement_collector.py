from __future__ import annotations

from typing import Any


def _is_backend_test_default_output_request(raw: str) -> bool:
    has_backend_test = ("后端测试" in raw) or ("测试后端" in raw) or ("backend test" in raw) or ("test backend" in raw)
    has_default_output = ("默认输出" in raw) or ("直接输出" in raw) or ("default output" in raw)
    return has_backend_test and has_default_output


def _extract_constraints(text: str) -> dict[str, Any]:
    raw = str(text or "").lower()
    constraints: dict[str, Any] = {}
    if "离线" in raw or "offline" in raw:
        constraints["runtime_target"] = "offline"
    if "实时" in raw or "real-time" in raw or "realtime" in raw:
        constraints["runtime_target"] = "realtime"
    if "qt" in raw:
        constraints["ui"] = "qt"
    if "telegram" in raw:
        constraints["channel"] = "telegram"
    if "vn" in raw or "视觉小说" in raw or "visual novel" in raw:
        constraints["project_domain"] = "vn_reasoning_game"
    if "推理" in raw or "deduction" in raw or "mystery" in raw:
        constraints["gameplay_focus"] = "reasoning"
    if "世界线" in raw or "worldline" in raw or "时间线" in raw or "timeline" in raw:
        constraints["worldline_management"] = "required"
    if "记录" in raw or "整理" in raw or "梳理" in raw or "record" in raw or "organize" in raw:
        constraints["story_knowledge_ops"] = "required"
    if "画图" in raw or "绘图" in raw or "diagram" in raw or "graph" in raw or "关系图" in raw or "流程图" in raw:
        constraints["diagram_support"] = "required"
    if _is_backend_test_default_output_request(raw):
        constraints["backend_test_default_output"] = True
        constraints["delivery_trigger_mode"] = "support"
    return constraints


class RequirementCollector:
    def collect(self, *, mode: str, latest_user_text: str, history: list[str]) -> dict[str, Any]:
        text = str(latest_user_text or "").strip()
        summary = {
            "mode": str(mode or "").upper() or "SMALLTALK",
            "latest_user_text": text,
            "history_digest": [str(item) for item in history[-3:]],
            "constraints": _extract_constraints(text),
        }
        summary["is_project_like"] = summary["mode"].startswith("PROJECT")
        return summary
