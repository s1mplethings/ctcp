from __future__ import annotations

from apps.project_backend.application.service import ProjectBackendService


def get_status(service: ProjectBackendService, job_id: str) -> dict[str, str]:
    event = service.get_status(str(job_id or "").strip())
    return event.to_payload()
