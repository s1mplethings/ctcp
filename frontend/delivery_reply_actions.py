from __future__ import annotations

import re
from typing import Any

_FINAL_READY_RUN_STATUSES = {"pass", "done", "completed", "success"}


def align_reply_with_delivery_actions(reply_text: str, *, actions: list[dict[str, Any]], source_hint: str) -> str:
    text = str(reply_text or "").strip()
    if str(source_hint or "").strip().lower() != "telegram":
        return text
    action_types = {str(item.get("type", "")).strip().lower() for item in actions if isinstance(item, dict)}
    if not ({"send_project_package", "send_project_screenshot"} & action_types):
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
    delivery_note = ""
    if {"send_project_package", "send_project_screenshot"} <= action_types:
        delivery_note = "我现在直接把 zip 包和结果截图发到当前对话。"
    elif "send_project_package" in action_types:
        delivery_note = "我现在直接把 zip 包发到当前对话。"
    elif "send_project_screenshot" in action_types:
        delivery_note = "我先把结果截图发到当前对话。"
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
    screenshot_count = len([x for x in delivery_state.get("screenshot_files", []) if str(x).strip()])
    if bool(delivery_state.get("screenshot_ready", False)) and screenshot_count > 0 and "send_project_screenshot" not in types:
        out.append({"type": "send_project_screenshot", "count": min(2, screenshot_count)})
        types.add("send_project_screenshot")
    if bool(delivery_state.get("package_delivery_allowed", False)) and "send_project_package" not in types:
        out.append({"type": "send_project_package", "format": "zip"})
    return out


def delivery_plan_failed(actions: list[dict[str, Any]] | None, plan: dict[str, Any] | None) -> bool:
    action_types = {str(item.get("type", "")).strip().lower() for item in actions or [] if isinstance(item, dict)}
    if not ({"send_project_package", "send_project_screenshot"} & action_types):
        return False
    if not isinstance(plan, dict):
        return True
    sent = [item for item in plan.get("sent", []) if isinstance(item, dict)]
    errors = [item for item in plan.get("errors", []) if str(item).strip()]
    return bool(errors) or not sent
