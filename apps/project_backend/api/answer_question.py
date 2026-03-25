from __future__ import annotations

from typing import Any

from apps.project_backend.application.service import ProjectBackendService
from contracts.schemas.job_answer import JobAnswerRequest


def answer_question(service: ProjectBackendService, payload: dict[str, Any]) -> dict[str, Any]:
    request = JobAnswerRequest.from_payload(payload)
    event = service.answer_question(request)
    return event.to_payload()
