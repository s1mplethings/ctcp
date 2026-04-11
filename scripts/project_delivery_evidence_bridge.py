from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from contracts.schemas.delivery_evidence import DeliveryEvidenceManifest
from frontend.delivery_reply_actions import prioritize_screenshot_files

MANIFEST_REL_PATH = Path("artifacts") / "delivery_evidence_manifest.json"


def _frontend_request_goal(run_dir: Path) -> str:
    path = run_dir / "artifacts" / "frontend_request.json"
    if not path.exists():
        return ""
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    if not isinstance(doc, dict):
        return ""
    return str(doc.get("goal", "")).strip()


def _abs_or_rel_path(run_dir: Path, rel_path: str) -> str:
    rel = str(rel_path or "").strip().replace("\\", "/")
    if not rel:
        return ""
    candidate = Path(rel)
    if candidate.is_absolute():
        return str(candidate)
    return str((run_dir / rel).resolve())


def _artifact_item(run_dir: Path, row: dict[str, Any], *, label: str = "", description: str = "") -> dict[str, Any]:
    rel_path = str(row.get("rel_path", "")).strip()
    return {
        "label": label or Path(rel_path).name,
        "path": _abs_or_rel_path(run_dir, rel_path),
        "rel_path": rel_path,
        "kind": str(row.get("kind", "")).strip(),
        "mime_type": str(row.get("mime_type", "")).strip(),
        "description": description,
    }


def _select_primary_report(run_dir: Path, artifacts: list[dict[str, Any]]) -> str:
    preferred: list[str] = []
    fallback: list[str] = []
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("rel_path", "")).strip()
        suffix = Path(rel).suffix.lower()
        low = rel.lower()
        if suffix == ".html" and "report" in low:
            preferred.append(_abs_or_rel_path(run_dir, rel))
        elif suffix in {".html", ".md"} and ("report" in low or "summary" in low):
            fallback.append(_abs_or_rel_path(run_dir, rel))
    if preferred:
        return preferred[0]
    if fallback:
        return fallback[0]
    return ""


def _select_screenshots(run_dir: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("rel_path", "")).strip()
        suffix = Path(rel).suffix.lower()
        low = rel.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            continue
        if any(
            token in low
            for token in ("screenshot", "timeline", "frame", "preview", "overview", "final", "result", "ui", "home")
        ):
            rows.append(_artifact_item(run_dir, row, description="可直接查看的交付截图"))

    ordered_paths = prioritize_screenshot_files(
        [str(item.get("path") or item.get("rel_path") or "") for item in rows]
    )
    order_index = {path: idx for idx, path in enumerate(ordered_paths)}

    rows.sort(
        key=lambda item: order_index.get(
            str(item.get("path") or item.get("rel_path") or ""),
            9999,
        )
    )
    return rows[:8]


def _select_demo_media(run_dir: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("rel_path", "")).strip()
        suffix = Path(rel).suffix.lower()
        low = rel.lower()
        if suffix in {".gif", ".mp4", ".webm"} and any(token in low for token in ("demo", "walkthrough", "preview", "clip")):
            rows.append(_artifact_item(run_dir, row, description="演示媒体或导出片段"))
    return rows[:8]


def _select_structured_outputs(run_dir: Path, artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in artifacts:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("rel_path", "")).strip()
        suffix = Path(rel).suffix.lower()
        if suffix in {".json", ".csv", ".zip"}:
            rows.append(_artifact_item(run_dir, row, description="结构化结果或可下载交付物"))
    return rows[:8]


def _verification_summary(project_manifest: dict[str, Any], verify_report: dict[str, Any]) -> dict[str, Any]:
    generic = project_manifest.get("generic_validation", {})
    if not isinstance(generic, dict):
        generic = {}
    domain = project_manifest.get("domain_validation", {})
    if not isinstance(domain, dict):
        domain = {}
    verify_result = str(verify_report.get("result", "")).strip().upper()
    passed_checks: list[str] = []
    if verify_result == "PASS":
        passed_checks.append("canonical verify 已通过")
    if bool(generic.get("passed", False)):
        passed_checks.append("generic MVP 校验已通过")
    if bool(domain.get("passed", False)):
        kind = str(domain.get("kind", "")).strip() or "domain"
        passed_checks.append(f"{kind} 领域校验已通过")
    pending_checks: list[str] = []
    if verify_result != "PASS":
        pending_checks.append("canonical verify 未明确通过")
    if not bool(generic.get("passed", False)):
        pending_checks.append("generic MVP 校验未明确通过")
    return {
        "status": "passed" if not pending_checks else ("failed" if verify_result == "FAIL" else "partial"),
        "verify_result": verify_result or "UNKNOWN",
        "passed_checks": passed_checks,
        "pending_checks": pending_checks,
        "one_line": "；".join(passed_checks[:2]) if passed_checks else "验证结果尚未完整收口",
    }


def _limitations(
    *,
    primary_report_path: str,
    screenshots: list[dict[str, Any]],
    demo_media: list[dict[str, Any]],
    verification_summary: dict[str, Any],
    project_manifest: dict[str, Any],
) -> list[str]:
    rows: list[str] = []
    if not primary_report_path:
        rows.append("当前还没有明确的主报告入口")
    if not screenshots:
        rows.append("当前没有可直接展示的截图证据")
    if not demo_media:
        rows.append("当前没有演示 gif/视频，用户只能看静态结果")
    if str(verification_summary.get("status", "")).strip() != "passed":
        rows.append("验证状态还不是完全通过，需结合 verify 结果继续确认")
    domain = project_manifest.get("domain_validation", {})
    if isinstance(domain, dict) and not bool(domain.get("passed", False)):
        rows.append("领域专用验收还不够完整")
    return rows[:4]


def build_delivery_evidence_manifest(
    *,
    run_id: str,
    run_dir: Path,
    project_manifest: dict[str, Any],
    artifacts: list[dict[str, Any]],
    verify_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    verify_doc = dict(verify_report or {})
    intent = project_manifest.get("project_intent", {})
    if not isinstance(intent, dict):
        intent = {}
    goal_summary = str(intent.get("goal_summary", "")).strip() or _frontend_request_goal(run_dir) or "项目交付结果"
    project_root = str(project_manifest.get("project_root", "")).strip()
    title_subject = Path(project_root).name if project_root else (goal_summary[:48] or run_id)
    primary_report_path = _select_primary_report(run_dir, artifacts)
    screenshots = _select_screenshots(run_dir, artifacts)
    demo_media = _select_demo_media(run_dir, artifacts)
    structured_outputs = _select_structured_outputs(run_dir, artifacts)
    verification_summary = _verification_summary(project_manifest, verify_doc)
    status = "ready" if str(verification_summary.get("status", "")).strip() == "passed" else "partial"
    view_now: list[dict[str, Any]] = []
    if primary_report_path:
        view_now.append({"label": "主报告页", "path": primary_report_path, "kind": "report"})
    view_now.extend(screenshots[:3])
    if demo_media:
        view_now.append(demo_media[0])

    actions: list[dict[str, Any]] = []
    if primary_report_path:
        actions.append({"label": "打开主报告", "path": primary_report_path, "description": "先查看整体结果和候选清单"})
    if screenshots:
        actions.append({"label": "查看截图", "path": str(Path(screenshots[0].get("path", "")).parent), "description": "快速预览结果证据"})
    if demo_media:
        actions.append({"label": "播放演示媒体", "path": str(demo_media[0].get("path", "")), "description": "查看 gif/视频或导出片段"})
    if structured_outputs:
        actions.append({"label": "查看结构化结果", "path": str(structured_outputs[0].get("path", "")), "description": "查看 json/csv/zip 等结果文件"})

    limitations = _limitations(
        primary_report_path=primary_report_path,
        screenshots=screenshots,
        demo_media=demo_media,
        verification_summary=verification_summary,
        project_manifest=project_manifest,
    )
    next_actions = [
        "先打开主报告确认结果摘要、截图和结构化输出是否符合你的预期",
        "如果要继续使用当前结果，优先查看导出片段或结构化结果文件",
        "如果要继续提需求，可以直接说明要提升识别精度、改界面展示，或切换到更强模型版本",
    ]

    one_line_result = "项目结果已经整理成可直接查看的交付证据，你现在可以直接打开报告、截图和结果文件。"
    if status != "ready":
        one_line_result = "项目已经产出可查看结果，但验证或展示证据还不够完整。"

    manifest = DeliveryEvidenceManifest(
        title=f"{title_subject} 交付结果",
        status=status,
        one_line_result=one_line_result,
        user_input_summary=goal_summary,
        user_visible_actions=actions,
        what_user_can_view_now=view_now,
        primary_report_path=primary_report_path,
        screenshots=screenshots,
        demo_media=demo_media,
        structured_outputs=structured_outputs,
        verification_summary=verification_summary,
        limitations=limitations,
        next_actions=next_actions,
        developer_details={
            "run_id": run_id,
            "run_dir": str(run_dir),
            "manifest_source": str(project_manifest.get("manifest_source", "")),
            "project_root": project_root,
        },
    )
    return manifest.to_payload()


def write_delivery_evidence_manifest(run_dir: Path, manifest: dict[str, Any]) -> str:
    target = run_dir / MANIFEST_REL_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return MANIFEST_REL_PATH.as_posix()
