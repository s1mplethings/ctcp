from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.validation import (
    ensure_no_full_chat_history,
    optional_dict,
    optional_string_list,
    require_dict,
    require_non_empty_string,
)


@dataclass(frozen=True)
class JobCreateRequest:
    request_id: str
    user_goal: str
    constraints: dict[str, Any]
    attachments: list[str]
    requirement_summary: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "JobCreateRequest":
        doc = require_dict(payload)
        ensure_no_full_chat_history(doc)
        return cls(
            request_id=require_non_empty_string(doc, "request_id"),
            user_goal=require_non_empty_string(doc, "user_goal"),
            constraints=optional_dict(doc, "constraints"),
            attachments=optional_string_list(doc, "attachments"),
            requirement_summary=optional_dict(doc, "requirement_summary"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "user_goal": self.user_goal,
            "constraints": dict(self.constraints),
            "attachments": list(self.attachments),
            "requirement_summary": dict(self.requirement_summary),
        }
