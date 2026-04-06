from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contracts.validation import optional_dict, optional_string, optional_string_list, require_dict


def _normalize_item_list(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if value is None:
        return []
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for item in value:
        if isinstance(item, dict):
            rows.append(dict(item))
    return rows


@dataclass(frozen=True)
class DeliveryEvidenceManifest:
    title: str
    status: str
    one_line_result: str
    user_input_summary: str
    user_visible_actions: list[dict[str, Any]] = field(default_factory=list)
    what_user_can_view_now: list[dict[str, Any]] = field(default_factory=list)
    primary_report_path: str = ""
    screenshots: list[dict[str, Any]] = field(default_factory=list)
    demo_media: list[dict[str, Any]] = field(default_factory=list)
    structured_outputs: list[dict[str, Any]] = field(default_factory=list)
    verification_summary: dict[str, Any] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    developer_details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "DeliveryEvidenceManifest":
        doc = require_dict(payload or {}, field="delivery_evidence")
        return cls(
            title=optional_string(doc, "title") or "交付结果",
            status=optional_string(doc, "status") or "unknown",
            one_line_result=optional_string(doc, "one_line_result") or "结果已准备好。",
            user_input_summary=optional_string(doc, "user_input_summary"),
            user_visible_actions=_normalize_item_list(doc, "user_visible_actions"),
            what_user_can_view_now=_normalize_item_list(doc, "what_user_can_view_now"),
            primary_report_path=optional_string(doc, "primary_report_path"),
            screenshots=_normalize_item_list(doc, "screenshots"),
            demo_media=_normalize_item_list(doc, "demo_media"),
            structured_outputs=_normalize_item_list(doc, "structured_outputs"),
            verification_summary=optional_dict(doc, "verification_summary"),
            limitations=optional_string_list(doc, "limitations"),
            next_actions=optional_string_list(doc, "next_actions"),
            developer_details=optional_dict(doc, "developer_details"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "ctcp-delivery-evidence-v1",
            "title": self.title,
            "status": self.status,
            "one_line_result": self.one_line_result,
            "user_input_summary": self.user_input_summary,
            "user_visible_actions": [dict(item) for item in self.user_visible_actions],
            "what_user_can_view_now": [dict(item) for item in self.what_user_can_view_now],
            "primary_report_path": self.primary_report_path,
            "screenshots": [dict(item) for item in self.screenshots],
            "demo_media": [dict(item) for item in self.demo_media],
            "structured_outputs": [dict(item) for item in self.structured_outputs],
            "verification_summary": dict(self.verification_summary),
            "limitations": list(self.limitations),
            "next_actions": list(self.next_actions),
            "developer_details": dict(self.developer_details),
        }
