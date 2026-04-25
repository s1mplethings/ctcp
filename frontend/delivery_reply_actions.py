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


def _supports_public_delivery_channel(source_hint: str) -> bool:
    return str(source_hint or "").strip().lower() in {"telegram", "virtual_delivery", "e2e_virtual_delivery"}


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
    if not _supports_public_delivery_channel(source_hint):
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
        "你先看我发的成品截图确认界面和结果，再打开 final project bundle zip 看完整代码。\n\n"
        "这个 zip 里包含 README、启动入口和主要代码；运行方式先按 README 里的说明执行。"
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
    if not _supports_public_delivery_channel(source_hint):
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


def _required_sent_types(actions: list[dict[str, Any]] | None) -> set[str]:
    required: set[str] = set()
    action_types = {str(item.get("type", "")).strip().lower() for item in actions or [] if isinstance(item, dict)}
    if "send_project_package" in action_types:
        required.add("document")
    if "send_project_screenshot" in action_types:
        required.add("photo")
    return required


def _existing_sent_paths(plan: dict[str, Any] | None, *, delivery_type: str, require_existing_files: bool) -> list[str]:
    out: list[str] = []
    for item in plan.get("sent", []) if isinstance(plan, dict) else []:
        if not isinstance(item, dict):
            continue
        if str(item.get("type", "")).strip().lower() != delivery_type:
            continue
        path = str(item.get("path", "")).strip()
        if not path:
            continue
        if require_existing_files and not Path(path).exists():
            continue
        out.append(path)
    return out


def _document_priority(path: str) -> tuple[int, str]:
    name = Path(str(path or "")).name.lower()
    if name == "final_project_bundle.zip":
        return (0, name)
    if name == "process_bundle.zip":
        return (2, name)
    return (1, name)


def evaluate_delivery_completion(
    actions: list[dict[str, Any]] | None,
    plan: dict[str, Any] | None,
    *,
    manifest_path: str = "",
    require_existing_files: bool = False,
    require_cold_replay: bool = False,
) -> dict[str, Any]:
    required_sent_types = _required_sent_types(actions)
    sent_types = {
        str(item.get("type", "")).strip().lower()
        for item in plan.get("sent", []) if isinstance(plan, dict)
        for _ in [item]
        if isinstance(item, dict)
    }
    errors = [str(item).strip() for item in plan.get("errors", []) if str(item).strip()] if isinstance(plan, dict) else []
    manifest_text = str(manifest_path or (plan or {}).get("manifest_path", "")).strip()
    reasons: list[str] = []
    if manifest_text and (not Path(manifest_text).exists()):
        reasons.append("support_public_delivery manifest missing")
    if errors:
        reasons.append("delivery errors present")
    for sent_type in sorted(required_sent_types):
        if sent_type not in sent_types:
            reasons.append(f"missing sent type: {sent_type}")
    document_paths = _existing_sent_paths(plan, delivery_type="document", require_existing_files=require_existing_files)
    document_paths = sorted(document_paths, key=_document_priority)
    photo_paths = _existing_sent_paths(plan, delivery_type="photo", require_existing_files=require_existing_files)
    if "document" in required_sent_types and not document_paths:
        reasons.append("document artifact missing")
    if document_paths and Path(document_paths[0]).name.lower() == "process_bundle.zip":
        reasons.append("selected document is process bundle instead of final project bundle")
    first_photo = photo_paths[0] if photo_paths else ""
    if "photo" in required_sent_types and not photo_paths:
        reasons.append("photo artifact missing")
    prioritized_photos = prioritize_screenshot_files(photo_paths)
    if first_photo and prioritized_photos and first_photo != prioritized_photos[0]:
        reasons.append("first delivered photo is not the highest-value screenshot")
    first_photo_name = Path(first_photo).name.lower() if first_photo else ""
    if first_photo_name and any(marker in first_photo_name for marker in _LOW_VALUE_SCREENSHOT_MARKERS):
        reasons.append("first delivered photo is low-value")
    replay_report = dict(plan.get("replay_report", {})) if isinstance(plan, dict) and isinstance(plan.get("replay_report", {}), dict) else {}
    if require_cold_replay:
        replay_passed = bool(replay_report.get("overall_pass", False))
        if not replay_passed:
            reasons.append("cold replay not passed")
    return {
        "passed": not reasons,
        "reasons": reasons,
        "required_sent_types": sorted(required_sent_types),
        "sent_types": sorted(sent_types),
        "selected_document": document_paths[0] if document_paths else "",
        "selected_photo": first_photo,
        "manifest_path": manifest_text,
        "cold_replay_required": bool(require_cold_replay),
        "cold_replay_passed": bool(replay_report.get("overall_pass", False)),
        "replay_report_path": str(replay_report.get("report_path", "")),
        "replay_screenshot_path": str(replay_report.get("replay_screenshot_path", "")),
    }


def evaluate_product_completion(project_manifest: dict[str, Any] | None) -> dict[str, Any]:
    manifest = dict(project_manifest) if isinstance(project_manifest, dict) else {}
    product = dict(manifest.get("product_validation", {})) if isinstance(manifest.get("product_validation", {}), dict) else {}
    if product:
        return {
            "profile": str(product.get("profile", "standard")).strip() or "standard",
            "required": bool(product.get("required", False)),
            "passed": bool(product.get("passed", False)),
            "checks": list(product.get("checks", [])) if isinstance(product.get("checks", []), list) else [],
            "missing": list(product.get("missing", [])) if isinstance(product.get("missing", []), list) else [],
            "reasons": list(product.get("reasons", [])) if isinstance(product.get("reasons", []), list) else [],
            "fallback_detected": bool(product.get("fallback_detected", False)),
        }
    generic = dict(manifest.get("generic_validation", {})) if isinstance(manifest.get("generic_validation", {}), dict) else {}
    domain = dict(manifest.get("domain_validation", {})) if isinstance(manifest.get("domain_validation", {}), dict) else {}
    passed = bool(generic.get("passed", False)) and bool(domain.get("passed", False))
    reasons: list[str] = []
    if not bool(generic.get("passed", False)):
        reasons.append("generic validation not passed")
    if not bool(domain.get("passed", False)):
        reasons.append("domain validation not passed")
    return {
        "profile": "standard",
        "required": False,
        "passed": passed,
        "checks": ["fallback to generic/domain product signal"] if passed else [],
        "missing": [],
        "reasons": reasons,
        "fallback_detected": False,
    }


def evaluate_user_acceptance(project_manifest: dict[str, Any] | None) -> dict[str, Any]:
    manifest = dict(project_manifest) if isinstance(project_manifest, dict) else {}
    project_domain = str(manifest.get("project_domain", "")).strip()
    project_type = str(manifest.get("project_type", "")).strip()
    project_archetype = str(manifest.get("project_archetype", "")).strip()
    extended = dict(manifest.get("extended_coverage", {})) if isinstance(manifest.get("extended_coverage", {}), dict) else {}
    coverage = dict(extended.get("coverage", {})) if isinstance(extended.get("coverage", {}), dict) else {}
    if project_domain != "indie_studio_production_hub" and project_type != "indie_studio_hub" and project_archetype != "indie_studio_hub_web":
        passed = bool(evaluate_product_completion(manifest).get("passed", False))
        return {
            "required": False,
            "status": "PASS" if passed else "NEEDS_REWORK",
            "passed": passed,
            "checks": [],
            "missing": [],
            "reasons": [],
        }
    required_keys = {
        "asset_library": "Asset Library missing",
        "asset_detail": "Asset Detail missing",
        "bug_tracker": "Bug Tracker missing",
        "build_release_center": "Build / Release Center missing",
        "docs_center": "Docs Center missing",
        "milestone_plan": "milestone_plan.md missing",
        "startup_guide": "startup_guide.md missing",
        "replay_guide": "replay_guide.md missing",
        "mid_stage_review": "mid_stage_review.md missing",
    }
    missing = [reason for key, reason in required_keys.items() if not bool(dict(coverage.get(key, {})).get("passed", False))]
    screenshots_row = dict(coverage.get("screenshots", {})) if isinstance(coverage.get("screenshots", {}), dict) else {}
    if int(screenshots_row.get("actual", 0) or 0) < 10:
        missing.append("10+ screenshots missing")
    return {
        "required": True,
        "status": "PASS" if not missing else "NEEDS_REWORK",
        "passed": not missing,
        "checks": [f"user acceptance coverage passed: {key}" for key in required_keys if bool(dict(coverage.get(key, {})).get("passed", False))],
        "missing": missing,
        "reasons": [],
    }


def evaluate_overall_completion(
    *,
    delivery_completion: dict[str, Any] | None,
    project_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    delivery = dict(delivery_completion) if isinstance(delivery_completion, dict) else {}
    product = evaluate_product_completion(project_manifest)
    reasons: list[str] = []
    if not bool(delivery.get("passed", False)):
        reasons.extend(str(item) for item in delivery.get("reasons", []) if str(item).strip())
    if not bool(product.get("passed", False)):
        reasons.extend(str(item) for item in product.get("missing", []) if str(item).strip())
        reasons.extend(str(item) for item in product.get("reasons", []) if str(item).strip())
    return {
        "passed": bool(delivery.get("passed", False)) and bool(product.get("passed", False)),
        "delivery_passed": bool(delivery.get("passed", False)),
        "product_passed": bool(product.get("passed", False)),
        "reasons": reasons,
    }


def delivery_plan_failed(actions: list[dict[str, Any]] | None, plan: dict[str, Any] | None) -> bool:
    action_types = {str(item.get("type", "")).strip().lower() for item in actions or [] if isinstance(item, dict)}
    if not (_DELIVERY_ACTION_TYPES & action_types):
        return False
    return not bool(evaluate_delivery_completion(actions, plan).get("passed", False))
