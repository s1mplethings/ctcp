#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from frontend.delivery_reply_actions import prioritize_screenshot_files, prioritize_video_files
from scripts.support_delivery_bundle_helpers import package_bundle_role
from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_delivery_actions import user_requests_project_package
from scripts.ctcp_support_bot_provider import sanitize_inline_text
from scripts.ctcp_support_bot_public_delivery_core import *  # noqa: F403
from scripts.ctcp_support_bot_session_state import current_project_brief


def evaluate_package_delivery_gate(project_context: dict[str, Any] | None) -> tuple[bool, str]:
    if not isinstance(project_context, dict):
        return False, "missing project context"
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        return False, "missing run status"
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    gate_state = str(gate.get("state", "")).strip().lower()
    needs_user_decision = bool(status.get("needs_user_decision", False))
    decisions_needed_count = int(status.get("decisions_needed_count", 0) or 0)
    if verify_result != "PASS":
        return False, "verify_result is not PASS"
    if run_status not in {"pass", "done", "completed", "success"}:
        return False, f"run_status not final: {run_status or 'unknown'}"
    if gate_state in {"blocked", "error", "failed"}:
        return False, f"gate_state not deliverable: {gate_state}"
    if needs_user_decision or decisions_needed_count > 0:
        return False, "pending user decision"
    return True, ""


def should_attempt_delivery_unblock_advance(*, project_context: dict[str, Any] | None, user_text: str) -> bool:
    if not user_requests_project_package(user_text) or not isinstance(project_context, dict):
        return False
    status = project_context.get("status", {})
    if not isinstance(status, dict):
        return False
    gate = status.get("gate", {})
    if not isinstance(gate, dict):
        gate = {}
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    gate_state = str(gate.get("state", "")).strip().lower()
    if bool(status.get("needs_user_decision", False)) or int(status.get("decisions_needed_count", 0) or 0) > 0:
        return False
    if verify_result == "PASS" and run_status in {"pass", "done", "completed", "success"}:
        return False
    return run_status not in {"fail", "failed", "error", "aborted"} and gate_state not in {"error", "failed"}


def _initial_delivery_state(*, source: str, project_name_hint: str) -> dict[str, Any]:
    return {
        "channel": str(source or "").strip().lower(),
        "channel_can_send_files": can_channel_send_files(source),
        "bound_run_id": "",
        "bound_run_dir": "",
        "package_source_dirs": [],
        "ctcp_package_source_dirs": [],
        "placeholder_package_source_dirs": [],
        "existing_package_files": [],
        "final_project_bundle_files": [],
        "process_bundle_files": [],
        "screenshot_files": [],
        "video_files": [],
        "project_name_hint": project_name_hint,
        "package_delivery_mode": "",
        "package_structure_hint": [],
        "package_ready": False,
        "package_delivery_allowed": False,
        "package_blocked_reason": "",
        "package_quality_ready": False,
        "package_quality_score": 0,
        "package_quality_tier": "unknown",
        "package_quality_subject": "",
        "package_quality_reason": "",
        "screenshot_ready": False,
        "video_ready": False,
    }


def _delivery_slug_hints(
    *,
    session_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    project_name_hint: str,
) -> list[str]:
    return [
        _delivery_project_slug(project_name_hint),
        _delivery_project_slug(current_project_brief(session_state if isinstance(session_state, dict) else {})),
        _delivery_project_slug(str((session_state or {}).get("bound_run_id", "")).strip()),
        _delivery_project_slug(str((project_context or {}).get("run_id", "")).strip()),
    ]


def _resolve_bound_run(
    *,
    session_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
) -> tuple[str, Path | None]:
    bound_run_id = ""
    bound_run_dir: Path | None = None
    if isinstance(project_context, dict):
        bound_run_id = str(project_context.get("run_id", "")).strip()
        bound_run_dir = _existing_path(str(project_context.get("run_dir", "")).strip())
    if bound_run_dir is None and isinstance(session_state, dict):
        bound_run_id = bound_run_id or str(session_state.get("bound_run_id", "")).strip()
        bound_run_dir = _existing_path(str(session_state.get("bound_run_dir", "")).strip())
    return bound_run_id, bound_run_dir


def _add_bound_run_package_sources(
    *,
    bound_run_dir: Path | None,
    project_context: dict[str, Any] | None,
    package_source_dirs: list[Path],
) -> Path | None:
    if bound_run_dir is None or not bound_run_dir.is_dir():
        return None
    declared_project_root = _declared_project_root_from_context(bound_run_dir, project_context)
    if declared_project_root is not None and _is_public_delivery_source_dir(declared_project_root):
        _append_unique_path(package_source_dirs, declared_project_root)
    for candidate in _generated_project_roots_from_patch_apply(bound_run_dir):
        _append_unique_path(package_source_dirs, candidate if _is_public_delivery_source_dir(candidate) else None)
    for candidate in _parse_scope_allow_roots(bound_run_dir / "artifacts" / "PLAN.md"):
        if _is_public_delivery_source_dir(candidate):
            _append_unique_path(package_source_dirs, candidate)
    return bound_run_dir / "artifacts"


def _resolve_exports_root(*, support_run_dir: Path | None, bound_run_dir: Path | None) -> Path | None:
    if isinstance(support_run_dir, Path):
        return (support_run_dir / SUPPORT_EXPORTS_REL_DIR).resolve()
    if bound_run_dir is not None and bound_run_dir.is_dir():
        candidate = bound_run_dir / SUPPORT_EXPORTS_REL_DIR
        if candidate.exists():
            return candidate.resolve()
    return None


def _active_export_dirs(exports_root: Path, preferred_slugs: list[str]) -> list[Path]:
    active: list[Path] = []
    for slug in preferred_slugs:
        if not slug or slug == "project":
            continue
        preferred_export_dir = (exports_root / f"{slug}_ctcp_project").resolve()
        if preferred_export_dir.exists() and preferred_export_dir.is_dir():
            return [preferred_export_dir]
    export_dirs = [node.resolve() for node in exports_root.iterdir() if node.is_dir()]
    if export_dirs:
        active.append(max(export_dirs, key=lambda path: path.stat().st_mtime))
    return active


def _collect_export_artifacts(
    *,
    exports_root: Path | None,
    preferred_slugs: list[str],
    package_source_dirs: list[Path],
    existing_package_files: list[Path],
    screenshot_files: list[Path],
    video_files: list[Path],
) -> None:
    if exports_root is None or not exports_root.exists() or not exports_root.is_dir():
        return
    active_dirs = _active_export_dirs(exports_root, preferred_slugs)
    for node in active_dirs:
        _append_unique_path(package_source_dirs, node)
    for candidate in sorted(exports_root.glob("*.zip")):
        if candidate.name.lower() != "failure_bundle.zip":
            _append_unique_path(existing_package_files, candidate)
    _collect_media_files(active_dirs + [exports_root], screenshot_files=screenshot_files, video_files=video_files, direct_only=True)


def _collect_media_files(
    roots: list[Path],
    *,
    screenshot_files: list[Path],
    video_files: list[Path],
    direct_only: bool = False,
) -> None:
    for root in roots:
        candidates = sorted(root.glob("*")) if direct_only else sorted(root.rglob("*"))
        for candidate in candidates:
            if not candidate.is_file():
                continue
            suffix = candidate.suffix.lower()
            if suffix in SCREENSHOT_SUFFIXES:
                _append_unique_path(screenshot_files, candidate)
            elif suffix in VIDEO_SUFFIXES:
                _append_unique_path(video_files, candidate)


def _collect_recursive_artifacts(
    *,
    package_source_dirs: list[Path],
    artifacts_dir: Path | None,
    support_exports_from_artifacts: Path | None,
    existing_package_files: list[Path],
    screenshot_files: list[Path],
    video_files: list[Path],
) -> None:
    roots = list(package_source_dirs)
    if artifacts_dir is not None and artifacts_dir.exists():
        roots.append(artifacts_dir)
    for root in roots:
        root_resolved = root.resolve()
        for candidate in sorted(root.rglob("*.zip")):
            candidate_resolved = candidate.resolve()
            if _is_support_export_child(root_resolved, artifacts_dir, support_exports_from_artifacts, candidate_resolved):
                continue
            if candidate.name.lower() != "failure_bundle.zip":
                _append_unique_path(existing_package_files, candidate)
    _collect_recursive_media(roots, artifacts_dir, support_exports_from_artifacts, screenshot_files, video_files)


def _is_support_export_child(
    root_resolved: Path,
    artifacts_dir: Path | None,
    support_exports_from_artifacts: Path | None,
    candidate_resolved: Path,
) -> bool:
    return bool(
        support_exports_from_artifacts is not None
        and artifacts_dir is not None
        and root_resolved == artifacts_dir.resolve()
        and support_exports_from_artifacts in candidate_resolved.parents
    )


def _collect_recursive_media(
    roots: list[Path],
    artifacts_dir: Path | None,
    support_exports_from_artifacts: Path | None,
    screenshot_files: list[Path],
    video_files: list[Path],
) -> None:
    for root in roots:
        root_resolved = root.resolve()
        for candidate in sorted(root.rglob("*")):
            if not candidate.is_file():
                continue
            if _is_support_export_child(root_resolved, artifacts_dir, support_exports_from_artifacts, candidate.resolve()):
                continue
            suffix = candidate.suffix.lower()
            if suffix in SCREENSHOT_SUFFIXES:
                _append_unique_path(screenshot_files, candidate)
            elif suffix in VIDEO_SUFFIXES:
                _append_unique_path(video_files, candidate)


def _finalize_delivery_state(
    state: dict[str, Any],
    *,
    session_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    package_source_dirs: list[Path],
    existing_package_files: list[Path],
    screenshot_files: list[Path],
    video_files: list[Path],
) -> dict[str, Any]:
    ctcp_dirs = [path for path in package_source_dirs if _looks_like_ctcp_project_dir(path)]
    placeholder_dirs = [path for path in package_source_dirs if _looks_like_placeholder_project_dir(path)]
    screenshots = _filter_public_screenshots(
        _dedupe_paths_by_content([Path(str(path)).resolve() for path in prioritize_screenshot_files(screenshot_files)])
    )
    videos = _dedupe_paths_by_content([Path(str(path)).resolve() for path in prioritize_video_files(video_files)])
    state.update(
        {
            "package_source_dirs": [str(path) for path in package_source_dirs],
            "ctcp_package_source_dirs": [str(path) for path in ctcp_dirs],
            "placeholder_package_source_dirs": [str(path) for path in placeholder_dirs],
            "existing_package_files": [str(path) for path in existing_package_files],
            "final_project_bundle_files": [str(path) for path in existing_package_files if package_bundle_role(path) == "final_project_bundle"],
            "process_bundle_files": [str(path) for path in existing_package_files if package_bundle_role(path) == "process_bundle"],
            "screenshot_files": [str(path) for path in screenshots],
            "video_files": [str(path) for path in videos],
            "project_name_hint": _delivery_project_name_hint(
                session_state=session_state,
                project_context=project_context,
                package_source_dirs=package_source_dirs,
            ),
            "screenshot_ready": bool(screenshots),
            "video_ready": bool(videos),
        }
    )
    _finalize_package_state(state, project_context, package_source_dirs, existing_package_files, ctcp_dirs, placeholder_dirs)
    return state


def _finalize_package_state(
    state: dict[str, Any],
    project_context: dict[str, Any] | None,
    package_source_dirs: list[Path],
    existing_package_files: list[Path],
    ctcp_dirs: list[Path],
    placeholder_dirs: list[Path],
) -> None:
    if existing_package_files:
        state["package_delivery_mode"] = "existing_package"
    elif ctcp_dirs:
        state["package_delivery_mode"] = "zip_existing_ctcp_project"
    elif placeholder_dirs:
        state["package_delivery_mode"] = "materialize_ctcp_scaffold"
    elif package_source_dirs:
        state["package_delivery_mode"] = "zip_existing_project"
    if state["package_delivery_mode"] == "materialize_ctcp_scaffold":
        state["package_structure_hint"] = list(CTCP_SCAFFOLD_STRUCTURE_HINT)
    elif ctcp_dirs:
        state["package_structure_hint"] = _top_level_structure_hint(ctcp_dirs[0]) or list(CTCP_SCAFFOLD_STRUCTURE_HINT)
    elif package_source_dirs:
        state["package_structure_hint"] = _top_level_structure_hint(package_source_dirs[0])
    package_artifact_ready = bool(package_source_dirs or existing_package_files)
    gate_allowed, gate_block_reason = evaluate_package_delivery_gate(project_context)
    quality_ready, quality_reason, quality_score, quality_tier, quality_subject = _evaluate_delivery_quality_gate(
        package_source_dirs=package_source_dirs,
        existing_package_files=existing_package_files,
    )
    state["package_quality_ready"] = bool(quality_ready)
    state["package_quality_score"] = int(quality_score)
    state["package_quality_tier"] = sanitize_inline_text(quality_tier, max_chars=24) or "unknown"
    state["package_quality_subject"] = sanitize_inline_text(quality_subject, max_chars=320)
    state["package_quality_reason"] = sanitize_inline_text(quality_reason, max_chars=180)
    state["package_delivery_allowed"] = bool(package_artifact_ready and gate_allowed and quality_ready)
    if not package_artifact_ready:
        state["package_blocked_reason"] = "package artifact not ready"
    elif not gate_allowed:
        state["package_blocked_reason"] = sanitize_inline_text(gate_block_reason, max_chars=120)
    elif not quality_ready:
        state["package_blocked_reason"] = sanitize_inline_text(quality_reason, max_chars=120)
    state["package_ready"] = bool(state["package_delivery_allowed"])


def collect_public_delivery_state(
    *,
    session_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    source: str,
    support_run_dir: Path | None = None,
) -> dict[str, Any]:
    project_name_hint = _delivery_project_name_hint(session_state=session_state, project_context=project_context, package_source_dirs=[])
    state = _initial_delivery_state(source=source, project_name_hint=project_name_hint)
    package_source_dirs: list[Path] = []
    existing_package_files: list[Path] = []
    screenshot_files: list[Path] = []
    video_files: list[Path] = []
    bound_run_id, bound_run_dir = _resolve_bound_run(session_state=session_state, project_context=project_context)
    artifacts_dir = _add_bound_run_package_sources(
        bound_run_dir=bound_run_dir,
        project_context=project_context,
        package_source_dirs=package_source_dirs,
    )
    if bound_run_dir is not None and bound_run_dir.is_dir():
        state["bound_run_id"] = bound_run_id
        state["bound_run_dir"] = str(bound_run_dir)
    support_exports_from_artifacts = (artifacts_dir / SUPPORT_EXPORTS_REL_DIR.name).resolve() if isinstance(artifacts_dir, Path) else None
    _collect_export_artifacts(
        exports_root=_resolve_exports_root(support_run_dir=support_run_dir, bound_run_dir=bound_run_dir),
        preferred_slugs=_delivery_slug_hints(session_state=session_state, project_context=project_context, project_name_hint=project_name_hint),
        package_source_dirs=package_source_dirs,
        existing_package_files=existing_package_files,
        screenshot_files=screenshot_files,
        video_files=video_files,
    )
    _collect_recursive_artifacts(
        package_source_dirs=package_source_dirs,
        artifacts_dir=artifacts_dir,
        support_exports_from_artifacts=support_exports_from_artifacts,
        existing_package_files=existing_package_files,
        screenshot_files=screenshot_files,
        video_files=video_files,
    )
    return _finalize_delivery_state(
        state,
        session_state=session_state,
        project_context=project_context,
        package_source_dirs=package_source_dirs,
        existing_package_files=existing_package_files,
        screenshot_files=screenshot_files,
        video_files=video_files,
    )


def public_delivery_prompt_context(delivery_state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(delivery_state, dict):
        return {}
    package_source_dirs = [Path(str(x)).name for x in delivery_state.get("package_source_dirs", []) if str(x).strip()]
    existing_packages = [Path(str(x)).name for x in (delivery_state.get("final_project_bundle_files") or delivery_state.get("existing_package_files", [])) if str(x).strip()]
    screenshot_count = len([x for x in delivery_state.get("screenshot_files", []) if str(x).strip()])
    video_count = len([x for x in delivery_state.get("video_files", []) if str(x).strip()])
    return {
        "channel": str(delivery_state.get("channel", "")).strip(),
        "channel_can_send_files": bool(delivery_state.get("channel_can_send_files", False)),
        "package_ready": bool(delivery_state.get("package_ready", False)),
        "package_delivery_allowed": bool(delivery_state.get("package_delivery_allowed", False)),
        "package_blocked_reason": sanitize_inline_text(str(delivery_state.get("package_blocked_reason", "")), max_chars=120),
        "package_quality_ready": bool(delivery_state.get("package_quality_ready", False)),
        "package_quality_score": int(delivery_state.get("package_quality_score", 0) or 0),
        "package_quality_tier": sanitize_inline_text(str(delivery_state.get("package_quality_tier", "")), max_chars=24),
        "package_sources": package_source_dirs[:3],
        "existing_package_files": existing_packages[:3],
        "project_name_hint": sanitize_inline_text(str(delivery_state.get("project_name_hint", "")), max_chars=64),
        "package_delivery_mode": sanitize_inline_text(str(delivery_state.get("package_delivery_mode", "")), max_chars=48),
        "package_structure_hint": [
            sanitize_inline_text(str(x), max_chars=48) for x in delivery_state.get("package_structure_hint", [])[:8]
        ],
        "screenshot_ready": bool(delivery_state.get("screenshot_ready", False)),
        "screenshot_count": int(screenshot_count),
        "video_ready": bool(delivery_state.get("video_ready", False)),
        "video_count": int(video_count),
    }


__all__ = [
    "evaluate_package_delivery_gate",
    "should_attempt_delivery_unblock_advance",
    "collect_public_delivery_state",
    "public_delivery_prompt_context",
]
