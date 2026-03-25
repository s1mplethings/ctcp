from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.validation import optional_dict, require_dict, require_non_empty_string


@dataclass(frozen=True)
class JobAnswerRequest:
    request_id: str
    job_id: str
    question_id: str
    answer_content: Any
    answer_meta: dict[str, Any]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "JobAnswerRequest":
        doc = require_dict(payload)
        return cls(
            request_id=require_non_empty_string(doc, "request_id"),
            job_id=require_non_empty_string(doc, "job_id"),
            question_id=require_non_empty_string(doc, "question_id"),
            answer_content=doc.get("answer_content", ""),
            answer_meta=optional_dict(doc, "answer_meta"),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "job_id": self.job_id,
            "question_id": self.question_id,
            "answer_content": self.answer_content,
            "answer_meta": dict(self.answer_meta),
        }
