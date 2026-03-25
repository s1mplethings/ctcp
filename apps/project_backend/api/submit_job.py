from __future__ import annotations

from typing import Any

from apps.project_backend.application.service import ProjectBackendService
from contracts.schemas.job_create import JobCreateRequest


def submit_job(service: ProjectBackendService, payload: dict[str, Any]) -> dict[str, Any]:
    request = JobCreateRequest.from_payload(payload)
    event = service.create_job(request)
    return event.to_payload()
