from __future__ import annotations

from typing import Any

from apps.project_backend.domain.job import JobRecord
from contracts.schemas.delivery_evidence import DeliveryEvidenceManifest


def fallback_delivery_evidence(*, record: JobRecord, report: dict[str, Any]) -> dict[str, Any]:
    verify_report = report.get("verify_report", {})
    if not isinstance(verify_report, dict):
        verify_report = {}
    verify_result = str(verify_report.get("result", "")).strip().upper()
    status = "ready" if verify_result == "PASS" else "partial"
    goal_summary = str(record.project_intent.get("goal_summary", "")).strip() or str(record.user_goal or "").strip()
    one_line = "项目结果已准备好，可以直接查看报告与导出结果。" if status == "ready" else "项目结果已产出，但验证状态还不完整。"
    manifest = DeliveryEvidenceManifest(
        title=f"{goal_summary[:48] or '项目'} 交付结果",
        status=status,
        one_line_result=one_line,
        user_input_summary=goal_summary,
        user_visible_actions=[],
        what_user_can_view_now=[],
        primary_report_path="",
        screenshots=[],
        demo_media=[],
        structured_outputs=[],
        verification_summary={
            "status": "passed" if verify_result == "PASS" else "partial",
            "verify_result": verify_result or "UNKNOWN",
            "passed_checks": ["canonical verify 已通过"] if verify_result == "PASS" else [],
            "pending_checks": [] if verify_result == "PASS" else ["canonical verify 未明确通过"],
            "one_line": "canonical verify 已通过" if verify_result == "PASS" else "验证状态尚未完整收口",
        },
        limitations=["当前没有桥接层提供的更细交付证据，只保留了最小完成摘要。"],
        next_actions=[
            "先查看主报告或结果目录确认这轮产物是否符合预期",
            "如果要继续提升结果，可以直接补充你下一轮想改的重点",
        ],
        developer_details={
            "run_id": record.run_id,
            "run_dir": record.run_dir,
            "fallback": True,
        },
    )
    return manifest.to_payload()
