from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

_FINAL_READY_RUN_STATUSES = {"pass", "done", "completed", "success"}
_DELIVERY_ACTION_TYPES = {"send_project_package", "send_project_screenshot"}
_HIGH_VALUE_SCREENSHOT_MARKERS = (
    "final-ui",
    "final",
    "result",
    "app-home",
    "home",
    "main-screen",
    "ui",
    "page",
    "render",
    "output",
)
_MID_VALUE_SCREENSHOT_MARKERS = ("preview", "screen", "screenshot")
_LOW_VALUE_SCREENSHOT_MARKERS = ("overview", "debug", "trace", "proof", "evidence", "timeline")
_INTERNAL_REPLY_MARKERS = (
    "stage",
    "gate",
    "artifact",
    "artifacts/",
    ".json",
    "hash",
    "path",
    "report",
    "project_output/",
    "plan_draft",
    "file_request",
    "source_generation_report",
    "support_public_delivery",
)


def _screenshot_priority_key(value: Any) -> tuple[int, str]:
    name = Path(str(value or "")).name.lower()
    if any(marker in name for marker in _HIGH_VALUE_SCREENSHOT_MARKERS):
        return (0, name)
    if any(marker in name for marker in _MID_VALUE_SCREENSHOT_MARKERS):
        return (1, name)
    if any(marker in name for marker in _LOW_VALUE_SCREENSHOT_MARKERS):
        return (3, name)
    return (2, name)


def prioritize_screenshot_files(paths: Iterable[Any]) -> list[str]:
    normalized = [str(item).strip() for item in paths if str(item).strip()]
    return sorted(normalized, key=_screenshot_priority_key)


def _looks_internal(text: str) -> bool:
    low = text.lower()
    if re.search(r"\b[a-f0-9]{40}\b", low):
        return True
    return any(marker in low for marker in _INTERNAL_REPLY_MARKERS)


def align_reply_with_delivery_actions(reply_text: str, *, actions: list[dict[str, Any]], source_hint: str) -> str:
    text = str(reply_text or "").strip()
    if str(source_hint or "").strip().lower() != "telegram":
        return text
    action_types = {str(item.get("type", "")).strip().lower() for item in actions if isinstance(item, dict)}
    if not (_DELIVERY_ACTION_TYPES & action_types):
        return text
    text = re.sub(
        r"\n*\s*((本轮已产出文件|关键产出仍是)[:：].*|Artifacts generated:.*|Key outputs remain:.*)\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()
    low = text.lower()
    if any(token in text for token in ("邮箱", "邮件")) or ("email" in low) or ("mail" in low):
        note = "文件我会直接发到当前对话，不用再留邮箱。"
        if note not in text:
            text = f"{text}\n\n{note}" if text else note

    base_delivery_text = (
        "项目已经整理好了，你可以直接开始查看。\n\n"
        "你先看我发的成品截图确认界面和结果，再打开 zip 包看完整代码。\n\n"
        "zip 里包含 README、启动入口和主要代码；运行方式先按 README 里的说明执行。"
    )
    if _looks_internal(text):
        text = base_delivery_text
    elif {"send_project_package", "send_project_screenshot"} <= action_types and not all(
        token in text for token in ("README", "启动入口", "运行方式")
    ):
        text = base_delivery_text

    delivery_note = ""
    if {"send_project_package", "send_project_screenshot"} <= action_types:
        delivery_note = "我会把成品截图和项目 zip 直接发到当前对话，你先看截图，再打开 zip。"
    elif "send_project_package" in action_types:
        delivery_note = "我会把项目 zip 直接发到当前对话。"
    elif "send_project_screenshot" in action_types:
        delivery_note = "我先把成品截图直接发到当前对话。"
    if delivery_note and delivery_note not in text:
        text = f"{text}\n\n{delivery_note}" if text else delivery_note
    return text


def is_verify_pass_delivery_context(project_context: dict[str, Any] | None) -> bool:
    if not isinstance(project_context, dict):
        return False
    status = project_context.get("status", {})
    runtime = project_context.get("runtime_state", {})
    status_doc = status if isinstance(status, dict) else {}
    runtime_doc = runtime if isinstance(runtime, dict) else {}
    verify_result = str(status_doc.get("verify_result", "")).strip().upper() or str(
        runtime_doc.get("verify_result", "")
    ).strip().upper()
    if verify_result == "PASS":
        return True
    run_status = str(status_doc.get("run_status", "")).strip().lower() or str(runtime_doc.get("run_status", "")).strip().lower()
    return run_status in _FINAL_READY_RUN_STATUSES


def inject_ready_delivery_actions(
    *,
    actions: list[dict[str, Any]],
    project_context: dict[str, Any] | None,
    delivery_state: dict[str, Any] | None,
    source_hint: str,
) -> list[dict[str, Any]]:
    out = [dict(item) for item in actions if isinstance(item, dict)]
    if str(source_hint or "").strip().lower() != "telegram":
        return out
    if not isinstance(delivery_state, dict) or not is_verify_pass_delivery_context(project_context):
        return out
    types = {str(item.get("type", "")).strip().lower() for item in out}
    screenshot_files = prioritize_screenshot_files(delivery_state.get("screenshot_files", []) or [])
    screenshot_count = len(screenshot_files)
    if bool(delivery_state.get("screenshot_ready", False)) and screenshot_count > 0 and "send_project_screenshot" not in types:
        out.append({"type": "send_project_screenshot", "count": min(2, screenshot_count)})
        types.add("send_project_screenshot")
    if bool(delivery_state.get("package_delivery_allowed", False)) and "send_project_package" not in types:
        out.append({"type": "send_project_package", "format": "zip"})
    return out


def delivery_plan_failed(actions: list[dict[str, Any]] | None, plan: dict[str, Any] | None) -> bool:
    action_types = {str(item.get("type", "")).strip().lower() for item in actions or [] if isinstance(item, dict)}
    if not (_DELIVERY_ACTION_TYPES & action_types):
        return False
    if not isinstance(plan, dict):
        return True
    sent = [item for item in plan.get("sent", []) if isinstance(item, dict)]
    errors = [item for item in plan.get("errors", []) if str(item).strip()]
    sent_types = {str(item.get("type", "")).strip().lower() for item in sent}
    if "send_project_package" in action_types and "document" not in sent_types:
        return True
    if "send_project_screenshot" in action_types and "photo" not in sent_types:
        return True
    return bool(errors) or not sent
