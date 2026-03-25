from __future__ import annotations

from apps.project_backend.application.service import ProjectBackendService


def get_result(service: ProjectBackendService, job_id: str) -> dict[str, object]:
    event = service.get_result(str(job_id or "").strip())
    return event.to_payload()
