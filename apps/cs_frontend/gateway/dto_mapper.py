from __future__ import annotations

from typing import Any

from contracts.schemas.job_answer import JobAnswerRequest
from contracts.schemas.job_create import JobCreateRequest
from shared.ids import new_request_id


class DtoMapper:
    def to_job_create_payload(self, *, user_goal: str, requirement_summary: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "request_id": new_request_id(),
            "user_goal": str(user_goal or "").strip(),
            "project_intent": dict(requirement_summary.get("project_intent", {})),
            "constraints": dict(requirement_summary.get("constraints", {})),
            "attachments": [],
            "requirement_summary": dict(requirement_summary),
        }
        return JobCreateRequest.from_payload(payload).to_payload()

    def to_job_answer_payload(self, *, job_id: str, question_id: str, answer: str) -> dict[str, Any]:
        payload = {
            "request_id": new_request_id(),
            "job_id": str(job_id or "").strip(),
            "question_id": str(question_id or "").strip(),
            "answer_content": str(answer or "").strip(),
            "answer_meta": {},
        }
        return JobAnswerRequest.from_payload(payload).to_payload()
