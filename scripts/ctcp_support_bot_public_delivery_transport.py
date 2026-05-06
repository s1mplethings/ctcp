#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent

from frontend.delivery_reply_actions import (
    evaluate_delivery_completion,
    prioritize_screenshot_files,
    prioritize_test_screenshot_files,
    prioritize_video_files,
)
from scripts.support_delivery_bundle_helpers import choose_public_package, parse_scaffold_run_dir, zip_directory
from scripts.support_public_delivery import resolve_public_delivery_mode
from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_delivery_actions import _has_test_screenshot_candidates
from scripts.ctcp_support_bot_io import append_event, now_iso, write_json, write_text
from scripts.ctcp_support_bot_provider import sanitize_inline_text
from scripts.ctcp_support_bot_public_delivery_core import *  # noqa: F403


def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def _host_attr(name: str) -> Any:
    module = _support_bot_host_module()
    return getattr(module, name, None) if module is not None else None


def _repo_root() -> Path:
    module = _support_bot_host_module()
    raw = getattr(module, "ROOT", ROOT) if module is not None else ROOT
    return Path(raw).resolve()


def detect_lang_hint(*texts: str) -> str:
    merged = " ".join(str(x or "") for x in texts)
    if not merged.strip():
        return "zh"
    zh_count = sum(1 for ch in merged if "\u4e00" <= ch <= "\u9fff")
    en_count = sum(1 for ch in merged if ("a" <= ch.lower() <= "z"))
    return "zh" if zh_count >= max(1, en_count // 3) else "en"

def _materialize_support_scaffold_project(
    *,
    run_dir: Path,
    delivery_state: dict[str, Any],
) -> Path | None:
    project_name = _delivery_project_slug(str(delivery_state.get("project_name_hint", "")).strip())
    out_dir = (run_dir / SUPPORT_EXPORTS_REL_DIR / f"{project_name}_ctcp_project").resolve()
    scaffold_runs_root = (run_dir / "artifacts" / "support_scaffold_runs").resolve()

    if _looks_like_ctcp_project_dir(out_dir):
        write_json(
            run_dir / SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH,
            {
                "schema_version": "ctcp-support-scaffold-materialization-v1",
                "ts": now_iso(),
                "project_name": project_name,
                "profile": SUPPORT_SCAFFOLD_PROFILE,
                "source_mode": SUPPORT_SCAFFOLD_SOURCE_MODE,
                "out_dir": str(out_dir),
                "run_dir": "",
                "reused_existing": True,
                "exit_code": 0,
                "stdout_log": "",
                "stderr_log": "",
                "error": "",
            },
        )
        append_event(
            run_dir,
            "SUPPORT_SCAFFOLD_READY",
            SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH.as_posix(),
            reused_existing=True,
            project_name=project_name,
        )
        return out_dir

    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)

    cmd = [
        sys.executable,
        str(SCRIPTS_DIR / "ctcp_orchestrate.py"),
        "scaffold",
        "--profile",
        SUPPORT_SCAFFOLD_PROFILE,
        "--source-mode",
        SUPPORT_SCAFFOLD_SOURCE_MODE,
        "--out",
        str(out_dir),
        "--name",
        project_name,
        "--runs-root",
        str(scaffold_runs_root),
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(_repo_root()),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    write_text(run_dir / SUPPORT_SCAFFOLD_STDOUT_REL_PATH, proc.stdout)
    write_text(run_dir / SUPPORT_SCAFFOLD_STDERR_REL_PATH, proc.stderr)
    scaffold_run_dir = parse_scaffold_run_dir(proc.stdout)
    error_text = ""
    if proc.returncode != 0:
        error_text = sanitize_inline_text(proc.stderr or proc.stdout, max_chars=260) or "scaffold command failed"
    elif not _looks_like_ctcp_project_dir(out_dir):
        error_text = "scaffold output missing CTCP project structure"
    write_json(
        run_dir / SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH,
        {
            "schema_version": "ctcp-support-scaffold-materialization-v1",
            "ts": now_iso(),
            "project_name": project_name,
            "profile": SUPPORT_SCAFFOLD_PROFILE,
            "source_mode": SUPPORT_SCAFFOLD_SOURCE_MODE,
            "out_dir": str(out_dir),
            "run_dir": scaffold_run_dir,
            "reused_existing": False,
            "exit_code": int(proc.returncode),
            "stdout_log": SUPPORT_SCAFFOLD_STDOUT_REL_PATH.as_posix(),
            "stderr_log": SUPPORT_SCAFFOLD_STDERR_REL_PATH.as_posix(),
            "error": error_text,
        },
    )
    if error_text:
        append_event(
            run_dir,
            "SUPPORT_SCAFFOLD_FAILED",
            SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH.as_posix(),
            project_name=project_name,
            reason=error_text,
        )
        return None
    append_event(
        run_dir,
        "SUPPORT_SCAFFOLD_READY",
        SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH.as_posix(),
        reused_existing=False,
        project_name=project_name,
    )
    return out_dir

def resolve_public_delivery_plan(
    *,
    run_dir: Path,
    actions: list[dict[str, Any]] | None,
    delivery_state: dict[str, Any] | None,
) -> dict[str, Any]:
    plan: dict[str, Any] = {
        "schema_version": "ctcp-support-public-delivery-v1",
        "ts": now_iso(),
        "requested_actions": [dict(item) for item in actions or [] if isinstance(item, dict)],
        "deliveries": [],
        "internal_artifacts": [],
        "errors": [],
    }
    if not isinstance(delivery_state, dict):
        return plan

    package_source_dirs = [Path(str(x)).resolve() for x in delivery_state.get("package_source_dirs", []) if str(x).strip()]
    ctcp_package_source_dirs = [
        Path(str(x)).resolve() for x in delivery_state.get("ctcp_package_source_dirs", []) if str(x).strip()
    ]
    placeholder_package_source_dirs = [
        Path(str(x)).resolve() for x in delivery_state.get("placeholder_package_source_dirs", []) if str(x).strip()
    ]
    existing_packages = [Path(str(x)).resolve() for x in delivery_state.get("existing_package_files", []) if str(x).strip()]
    final_packages = [Path(str(x)).resolve() for x in delivery_state.get("final_project_bundle_files", []) if str(x).strip()]
    process_packages = [Path(str(x)).resolve() for x in delivery_state.get("process_bundle_files", []) if str(x).strip()]
    screenshot_files = _filter_public_screenshots(_dedupe_paths_by_content(
        [Path(str(x)).resolve() for x in prioritize_screenshot_files(delivery_state.get("screenshot_files", []))]
    ))
    video_files = _dedupe_paths_by_content(
        [Path(str(x)).resolve() for x in prioritize_video_files(delivery_state.get("video_files", []))]
    )
    export_dir = run_dir / SUPPORT_EXPORTS_REL_DIR

    for action in actions or []:
        if not isinstance(action, dict):
            continue
        action_type = str(action.get("type", "")).strip().lower()
        if action_type == "send_project_package":
            if not bool(delivery_state.get("package_delivery_allowed", False)):
                blocked_reason = sanitize_inline_text(str(delivery_state.get("package_blocked_reason", "")), max_chars=120)
                if blocked_reason:
                    plan["errors"].append(f"package requested but blocked: {blocked_reason}")
                else:
                    plan["errors"].append("package requested but package delivery gate is blocked")
                continue
            chosen: Path | None = None
            process_bundle: Path | None = choose_public_package(process_packages)
            if final_packages:
                chosen = choose_public_package(final_packages)
            elif ctcp_package_source_dirs:
                source_dir = ctcp_package_source_dirs[0]
                chosen = zip_directory(source_dir, export_dir / "final_project_bundle.zip", excluded_root=SUPPORT_EXPORTS_REL_DIR)
                process_bundle = zip_directory(run_dir, export_dir / "process_bundle.zip", excluded_root=SUPPORT_EXPORTS_REL_DIR)
            elif placeholder_package_source_dirs:
                materializer = _host_attr("_materialize_support_scaffold_project")
                if not callable(materializer) or materializer is _materialize_support_scaffold_project:
                    materializer = _materialize_support_scaffold_project
                scaffold_dir = materializer(run_dir=run_dir, delivery_state=delivery_state)
                if scaffold_dir is not None and scaffold_dir.exists():
                    chosen = zip_directory(scaffold_dir, export_dir / "final_project_bundle.zip", excluded_root=SUPPORT_EXPORTS_REL_DIR)
                    process_bundle = zip_directory(run_dir, export_dir / "process_bundle.zip", excluded_root=SUPPORT_EXPORTS_REL_DIR)
                else:
                    plan["errors"].append("package requested but scaffold materialization did not succeed")
                    continue
            elif package_source_dirs:
                source_dir = package_source_dirs[0]
                chosen = zip_directory(source_dir, export_dir / "final_project_bundle.zip", excluded_root=SUPPORT_EXPORTS_REL_DIR)
                process_bundle = zip_directory(run_dir, export_dir / "process_bundle.zip", excluded_root=SUPPORT_EXPORTS_REL_DIR)
            elif existing_packages:
                chosen = choose_public_package(existing_packages)
            if chosen is None or (not chosen.exists()):
                plan["errors"].append("package requested but no package source is available")
                continue
            if process_bundle is not None and process_bundle.exists():
                plan["internal_artifacts"].append({"type": "process_bundle", "path": str(process_bundle), "visibility": "internal"})
            plan["deliveries"].append(
                {
                    "type": "document",
                    "path": str(chosen),
                    "caption": "这里是当前可直接交付的 final project bundle zip。",
                }
            )
            continue
        if action_type == "send_project_screenshot":
            try:
                count = int(action.get("count", 1))
            except Exception:
                count = 1
            profile = str(action.get("profile", "")).strip().lower()
            if (not profile) and _has_test_screenshot_candidates([str(x) for x in screenshot_files]):
                profile = "test_evidence"
            ordered_screenshots = screenshot_files
            if profile == "test_evidence":
                ordered_screenshots = _dedupe_paths_by_content(
                    [Path(str(x)).resolve() for x in prioritize_test_screenshot_files(screenshot_files)]
                )
            selected = ordered_screenshots[: max(1, min(count, 5))]
            if not selected:
                plan["errors"].append("screenshot requested but no screenshot artifact is available")
                continue
            for idx, path in enumerate(selected, start=1):
                plan["deliveries"].append(
                    {
                        "type": "photo",
                        "path": str(path),
                        "caption": (
                            "这是当前项目可直接发送的测试证据截图。"
                            if idx == 1 and profile == "test_evidence"
                            else ("这是当前项目可直接发送的截图。" if idx == 1 else "")
                        ),
                    }
                )
            continue
        if action_type == "send_project_video":
            try:
                count = int(action.get("count", 1))
            except Exception:
                count = 1
            selected_videos = video_files[: max(1, min(count, 2))]
            if not selected_videos:
                plan["errors"].append("video requested but no video artifact is available")
                continue
            for idx, path in enumerate(selected_videos, start=1):
                plan["deliveries"].append(
                    {
                        "type": "video",
                        "path": str(path),
                        "caption": "这是当前项目的测试视频。" if idx == 1 else "",
                    }
                )
    return plan

def _rewrite_public_runtime_terms(reply_text: str, *, lang_hint: str = "") -> str:
    text = str(reply_text or "").strip()
    if not text:
        return ""
    lang = str(lang_hint or "").strip().lower() or detect_lang_hint(text)
    use_en = lang.startswith("en")
    waiting_replacement = "the planning draft is still being generated" if use_en else "方案草案还在生成中"
    retry_replacement = (
        "retry planning synthesis and verify the planning draft lands"
        if use_en
        else "继续重试方案整理，并确认方案草案真正生成出来"
    )
    text = re.sub(r"\bwaiting for PLAN_draft\.md\b", waiting_replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\bretry planner to generate PLAN_draft\.md\b", retry_replacement, text, flags=re.IGNORECASE)
    text = re.sub(r"\bPLAN_draft\.md\b", "planning draft" if use_en else "方案草案", text, flags=re.IGNORECASE)
    return text

def _reply_is_backend_placeholder(reply_text: str) -> bool:
    text = str(reply_text or "").strip()
    if not text:
        return False
    low = text.lower()
    return any(token in text for token in _BACKEND_PLACEHOLDER_REPLY_MARKERS_ZH) or any(
        token in low for token in _BACKEND_PLACEHOLDER_REPLY_MARKERS_EN
    )

def _delivery_ready_notice_from_plan(plan: dict[str, Any], *, lang_hint: str = "") -> str:
    deliveries = [dict(item) for item in plan.get("deliveries", []) if isinstance(item, dict)] if isinstance(plan, dict) else []
    if not deliveries:
        return ""
    lang = str(lang_hint or "").strip().lower()
    if not lang:
        lang = "zh"
    use_en = lang.startswith("en")
    types = {str(item.get("type", "")).strip().lower() for item in deliveries}
    if use_en:
        if {"photo", "document"} <= types:
            return "The project is ready for delivery now; I will send test screenshots and the project zip in this chat."
        if "photo" in types:
            return "The project has reviewable output now; I will send test screenshots in this chat first."
        if "document" in types:
            return "The project package is ready now; I will send the zip in this chat."
        if "video" in types:
            return "The project has a reviewable run now; I will send the test video in this chat."
        return "The project now has reviewable delivery output in this chat."
    if {"photo", "document"} <= types:
        return "当前项目结果已可交付，我先把测试截图和项目包直接发到当前对话。"
    if "photo" in types:
        return "当前项目已有可查看结果，我先把测试截图直接发到当前对话。"
    if "document" in types:
        return "当前项目包已可交付，我先把 zip 直接发到当前对话。"
    if "video" in types:
        return "当前项目已有可查看运行效果，我先把测试视频发到当前对话。"
    return "当前项目已经有可查看的交付结果。"

def _prepare_public_reply_for_telegram(
    reply_text: str,
    *,
    delivery_preview: dict[str, Any] | None = None,
    lang_hint: str = "",
) -> str:
    text = _rewrite_public_runtime_terms(reply_text, lang_hint=lang_hint)
    if _reply_is_backend_placeholder(text):
        delivery_notice = _delivery_ready_notice_from_plan(delivery_preview or {}, lang_hint=lang_hint or detect_lang_hint(text))
        if delivery_notice:
            return delivery_notice
    return text

def emit_public_delivery(
    tg: TelegramClient,
    *,
    chat_id: int,
    run_dir: Path,
    actions: list[dict[str, Any]] | None,
    delivery_state: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest_path = (run_dir / SUPPORT_PUBLIC_DELIVERY_REL_PATH).resolve()
    plan = resolve_public_delivery_plan(run_dir=run_dir, actions=actions, delivery_state=delivery_state)
    plan["delivery_mode"] = str(getattr(tg, "mode", "")).strip().lower() or resolve_public_delivery_mode(None)
    plan["manifest_path"] = str(manifest_path)
    sent: list[dict[str, Any]] = []
    errors = list(plan.get("errors", [])) if isinstance(plan.get("errors", []), list) else []
    for item in plan.get("deliveries", []):
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "")).strip()).resolve()
        caption = sanitize_inline_text(str(item.get("caption", "")), max_chars=300)
        if not path.exists() or not path.is_file():
            errors.append(f"delivery file missing: {path}")
            continue
        delivery_type = str(item.get("type", "")).strip().lower()
        receipt: dict[str, Any] = {}
        if delivery_type == "document":
            maybe_receipt = tg.send_document(chat_id, path, caption=caption)
        elif delivery_type == "photo":
            maybe_receipt = tg.send_photo(chat_id, path, caption=caption)
        elif delivery_type == "video":
            maybe_receipt = tg.send_video(chat_id, path, caption=caption)
        else:
            errors.append(f"unsupported delivery type: {delivery_type}")
            continue
        if isinstance(maybe_receipt, dict): receipt = maybe_receipt
        sent_item = {"type": delivery_type, "path": str(path), "caption": caption}
        sent_item.update(receipt)
        sent.append(sent_item)
    plan["sent"] = sent
    plan["errors"] = errors
    write_json(manifest_path, plan)
    plan["completion_gate"] = evaluate_delivery_completion(actions, plan, manifest_path=str(manifest_path), require_existing_files=True)
    write_json(manifest_path, plan)
    if sent:
        append_event(run_dir, "SUPPORT_PUBLIC_DELIVERY_SENT", SUPPORT_PUBLIC_DELIVERY_REL_PATH.as_posix(), count=len(sent))
    elif errors:
        append_event(run_dir, "SUPPORT_PUBLIC_DELIVERY_SKIPPED", SUPPORT_PUBLIC_DELIVERY_REL_PATH.as_posix(), errors=len(errors))
    return plan

__all__ = ["_materialize_support_scaffold_project", "resolve_public_delivery_plan", "_rewrite_public_runtime_terms", "_reply_is_backend_placeholder", "_delivery_ready_notice_from_plan", "_prepare_public_reply_for_telegram", "emit_public_delivery"]
