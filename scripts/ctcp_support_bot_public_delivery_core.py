#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

from frontend.delivery_reply_actions import prioritize_screenshot_files, prioritize_video_files
from scripts.support_delivery_bundle_helpers import package_bundle_role
from scripts.ctcp_support_bot_constants import *  # noqa: F403
from scripts.ctcp_support_bot_provider import read_json_doc, sanitize_inline_text
from scripts.ctcp_support_bot_session_state import current_project_brief

def _support_bot_host_module() -> Any:
    for name in ("scripts.ctcp_support_bot", "ctcp_support_bot", "__main__"):
        module = sys.modules.get(name)
        if module is not None and module is not sys.modules.get(__name__):
            return module
    return None


def _repo_root() -> Path:
    module = _support_bot_host_module()
    raw = getattr(module, "ROOT", ROOT) if module is not None else ROOT
    return Path(raw).resolve()

def _existing_path(raw: str) -> Path | None:
    text = str(raw or "").strip()
    if not text:
        return None
    candidate = Path(text).expanduser()
    if not candidate.is_absolute():
        candidate = (_repo_root() / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if candidate.exists():
        return candidate
    return None

def _append_unique_path(paths: list[Path], candidate: Path | None) -> None:
    if candidate is None:
        return
    resolved = candidate.resolve()
    if resolved not in paths:
        paths.append(resolved)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _dedupe_paths_by_content(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[str] = set()
    for raw in paths:
        try:
            candidate = raw.resolve()
        except Exception:
            candidate = Path(str(raw)).resolve()
        marker = f"path:{candidate}"
        try:
            if candidate.exists() and candidate.is_file():
                stat = candidate.stat()
                marker = f"sha256:{stat.st_size}:{_sha256_file(candidate)}"
        except Exception:
            marker = f"path:{candidate}"
        if marker in seen:
            continue
        seen.add(marker)
        out.append(candidate)
    return out


def _is_blocked_public_screenshot(candidate: Path) -> bool:
    try:
        resolved = candidate.resolve()
    except Exception:
        resolved = Path(str(candidate)).resolve()
    normalized = resolved.as_posix().lower()
    if any(marker in normalized for marker in _PUBLIC_SCREENSHOT_BLOCKED_PATH_MARKERS):
        return True
    name = resolved.name.lower()
    if any(marker in name for marker in _PUBLIC_SCREENSHOT_BLOCKED_NAME_MARKERS):
        return True
    return False


def _filter_public_screenshots(paths: list[Path]) -> list[Path]:
    out: list[Path] = []
    for candidate in paths:
        if _is_blocked_public_screenshot(candidate):
            continue
        out.append(candidate)
    return out


def _parse_scope_allow_roots(plan_path: Path) -> list[Path]:
    roots: list[Path] = []
    if not plan_path.exists():
        return roots
    for raw in plan_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line.lower().startswith("scope-allow:"):
            continue
        payload = line.split(":", 1)[1]
        for item in payload.split(","):
            rel = item.strip()
            if not rel or rel in {".", "./"}:
                continue
            _append_unique_path(roots, _existing_path(rel))
    return roots


_REPO_INTERNAL_DELIVERY_ROOTS = {
    ".git",
    ".github",
    ".agent_private",
    ".agents",
    "agents",
    "ai_context",
    "apps",
    "artifacts",
    "bridge",
    "build",
    "build_lite",
    "build_verify",
    "contracts",
    "ctcp_adapters",
    "docs",
    "llm_core",
    "meta",
    "scripts",
    "simlab",
    "tests",
    "tools",
    "web",
    "workflow_registry",
}


def _is_public_delivery_source_dir(candidate: Path) -> bool:
    if not candidate.exists() or not candidate.is_dir():
        return False
    resolved = candidate.resolve()
    if _looks_like_ctcp_project_dir(resolved) or _looks_like_placeholder_project_dir(resolved):
        return True
    try:
        rel = resolved.relative_to(_repo_root())
    except Exception:
        return True
    parts = [part for part in rel.parts if part]
    if not parts:
        return False
    head = parts[0].lower()
    if head == "generated_projects":
        return True
    return head not in _REPO_INTERNAL_DELIVERY_ROOTS

def _generated_project_roots_from_patch_apply(bound_run_dir: Path) -> list[Path]:
    roots: list[Path] = []
    doc = read_json_doc(bound_run_dir / "artifacts" / "patch_apply.json")
    touched = doc.get("touched_files", []) if isinstance(doc, dict) else []
    if not isinstance(touched, list):
        touched = []
    for item in touched:
        rel = str(item or "").strip().replace("\\", "/")
        if not rel:
            continue
        parts = [part for part in rel.split("/") if part]
        if len(parts) >= 2 and parts[0] == "generated_projects":
            _append_unique_path(roots, _existing_path("/".join(parts[:2])))
    return roots

def _declared_project_root_from_context(bound_run_dir: Path, project_context: dict[str, Any] | None) -> Path | None:
    if not isinstance(project_context, dict):
        return None
    manifest = project_context.get("project_manifest", {})
    if not isinstance(manifest, dict):
        return None
    rel = str(manifest.get("project_root", "")).strip()
    if not rel:
        return None
    candidate = (bound_run_dir / Path(rel)).resolve()
    try:
        candidate.relative_to(bound_run_dir.resolve())
    except Exception:
        return None
    if not candidate.exists() or not candidate.is_dir():
        return None
    return candidate

def _delivery_project_slug(raw: str) -> str:
    text = str(raw or "").strip().lower().replace("\\", "/")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:64] or "project"

def _top_level_structure_hint(root: Path, max_items: int = 8) -> list[str]:
    if not root.exists() or not root.is_dir():
        return []
    items: list[str] = []
    for node in sorted(root.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())):
        items.append(node.name + ("/" if node.is_dir() else ""))
        if len(items) >= max(1, int(max_items)):
            break
    return items

def _looks_like_ctcp_project_dir(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    required = (
        root / "README.md",
        root / "docs",
        root / "meta",
        root / "scripts",
        root / "manifest.json",
    )
    return all(path.exists() for path in required)

def _looks_like_placeholder_project_dir(root: Path) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    top_files = {node.name.lower() for node in root.iterdir() if node.is_file()}
    top_dirs = {node.name.lower() for node in root.iterdir() if node.is_dir()}
    if {"docs", "meta", "scripts"} & top_dirs:
        return False
    if "manifest.json" in top_files:
        return False
    total_files = sum(1 for node in root.rglob("*") if node.is_file())
    return total_files <= 4 and bool({"main.py", "app.py", "readme.md"} & top_files)

def _has_any_file(root: Path, pattern: str) -> bool:
    if not root.exists() or not root.is_dir():
        return False
    for path in root.rglob(pattern):
        if path.is_file():
            return True
    return False

def _has_screenshot_or_reason(artifacts_dir: Path) -> bool:
    screenshots_dir = artifacts_dir / "screenshots"
    if screenshots_dir.exists() and screenshots_dir.is_dir():
        for path in screenshots_dir.rglob("*"):
            if path.is_file() and path.suffix.lower() in SCREENSHOT_SUFFIXES:
                return True
    reason_file = artifacts_dir / "screenshots_not_available_reason.txt"
    if reason_file.exists() and reason_file.is_file():
        return True
    demo_trace = artifacts_dir / "demo_trace.md"
    if demo_trace.exists() and demo_trace.is_file():
        low = demo_trace.read_text(encoding="utf-8", errors="replace").lower()
        if "screenshots_not_available_reason" in low:
            return True
    return False

def _score_delivery_project_quality(root: Path) -> dict[str, Any]:
    artifacts_dir = root / "artifacts"
    checks = [
        ("readme", (root / "README.md").exists(), 10),
        ("manifest", (root / "manifest.json").exists() or (root / "meta" / "manifest.json").exists(), 10),
        ("docs_dir", (root / "docs").is_dir(), 8),
        ("meta_dir", (root / "meta").is_dir(), 8),
        ("scripts_dir", (root / "scripts").is_dir(), 8),
        ("verify_entry", (root / "scripts" / "verify_repo.ps1").exists() or (root / "scripts" / "verify_repo.sh").exists(), 8),
        ("tests_dir", (root / "tests").is_dir(), 10),
        ("test_case_file", _has_any_file(root / "tests", "test_*.py"), 8),
        (
            "showcase_core",
            (artifacts_dir / "test_plan.json").exists()
            and (artifacts_dir / "test_cases.json").exists()
            and (artifacts_dir / "test_summary.md").exists()
            and (artifacts_dir / "demo_trace.md").exists(),
            15,
        ),
        ("showcase_visual", _has_screenshot_or_reason(artifacts_dir), 15),
    ]
    score = sum(weight for _, ok, weight in checks if ok)
    tier = "low"
    if score >= 85:
        tier = "high"
    elif score >= SUPPORT_PACKAGE_MIN_QUALITY_SCORE:
        tier = "medium"
    elif score >= 50:
        tier = "scaffold"
    missing = [check_id for check_id, ok, _ in checks if not ok]
    return {
        "root": str(root),
        "score": int(score),
        "tier": tier,
        "missing_checks": missing,
    }

def _evaluate_delivery_quality_gate(
    *,
    package_source_dirs: list[Path],
    existing_package_files: list[Path],
) -> tuple[bool, str, int, str, str]:
    if existing_package_files and (not package_source_dirs):
        return True, "", 100, "trusted_existing_package", ""
    if not package_source_dirs:
        return False, "package source missing", 0, "unknown", ""
    reports = [_score_delivery_project_quality(path) for path in package_source_dirs if path.exists() and path.is_dir()]
    if not reports:
        return False, "package source missing", 0, "unknown", ""
    best = max(reports, key=lambda item: int(item.get("score", 0)))
    score = int(best.get("score", 0))
    tier = str(best.get("tier", "unknown"))
    subject = str(best.get("root", ""))
    if score < SUPPORT_PACKAGE_MIN_QUALITY_SCORE:
        return (
            False,
            f"package quality score {score} < {SUPPORT_PACKAGE_MIN_QUALITY_SCORE}; need fuller implementation evidence",
            score,
            tier,
            subject,
        )
    return True, "", score, tier, subject

def _delivery_project_name_hint(
    *,
    session_state: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    package_source_dirs: list[Path],
) -> str:
    for path in package_source_dirs:
        name = _delivery_project_slug(path.name)
        if name:
            return name
    if isinstance(project_context, dict):
        for key in ("goal", "run_id"):
            value = _delivery_project_slug(str(project_context.get(key, "")).strip())
            if value and value != "project":
                return value
    if isinstance(session_state, dict):
        brief = _delivery_project_slug(current_project_brief(session_state))
        if brief and brief != "project":
            return brief
        run_id = _delivery_project_slug(str(session_state.get("bound_run_id", "")).strip())
        if run_id and run_id != "project":
            return run_id
    return "project"

def can_channel_send_files(source: str) -> bool:
    return str(source or "").strip().lower() in {"telegram", "virtual_delivery", "e2e_virtual_delivery"}

__all__ = [
    "_existing_path",
    "_append_unique_path",
    "_sha256_file",
    "_dedupe_paths_by_content",
    "_is_blocked_public_screenshot",
    "_filter_public_screenshots",
    "_parse_scope_allow_roots",
    "_is_public_delivery_source_dir",
    "_generated_project_roots_from_patch_apply",
    "_declared_project_root_from_context",
    "_delivery_project_slug",
    "_top_level_structure_hint",
    "_looks_like_ctcp_project_dir",
    "_looks_like_placeholder_project_dir",
    "_has_any_file",
    "_has_screenshot_or_reason",
    "_score_delivery_project_quality",
    "_evaluate_delivery_quality_gate",
    "_delivery_project_name_hint",
    "can_channel_send_files",
]
