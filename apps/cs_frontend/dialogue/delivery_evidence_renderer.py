from __future__ import annotations

from pathlib import Path
from typing import Any

from contracts.schemas.delivery_evidence import DeliveryEvidenceManifest


def normalize_delivery_evidence(payload: dict[str, Any] | None) -> dict[str, Any]:
    return DeliveryEvidenceManifest.from_payload(payload).to_payload()


def _item_line(item: dict[str, Any]) -> str:
    label = str(item.get("label", "")).strip() or Path(str(item.get("path", "")).strip()).name or "结果项"
    path = str(item.get("path", "")).strip()
    if path:
        return f"- {label}：{path}"
    return f"- {label}"


def render_delivery_evidence_reply(payload: dict[str, Any] | None) -> str:
    evidence = DeliveryEvidenceManifest.from_payload(payload)
    lines: list[str] = [f"交付结果：{evidence.one_line_result}"]

    if evidence.user_input_summary:
        lines.append(f"你这轮要做的是：{evidence.user_input_summary}")

    view_now = [item for item in evidence.what_user_can_view_now if isinstance(item, dict)]
    if view_now:
        lines.append("现在可以直接看：")
        for item in view_now[:4]:
            lines.append(_item_line(item))

    report_path = str(evidence.primary_report_path or "").strip()
    if report_path:
        lines.append(f"主报告入口：{report_path}")

    verification = dict(evidence.verification_summary)
    verify_one_line = str(verification.get("one_line", "")).strip()
    if verify_one_line:
        lines.append(f"验证结果：{verify_one_line}")

    if evidence.limitations:
        lines.append("当前限制：")
        for item in evidence.limitations[:2]:
            lines.append(f"- {item}")

    if evidence.next_actions:
        lines.append("下一步建议：")
        for item in evidence.next_actions[:3]:
            lines.append(f"- {item}")

    return "\n".join(line for line in lines if str(line).strip())
