from __future__ import annotations

from typing import Any

from apps.project_backend.application.service import ProjectBackendService


def run_http_request(service: ProjectBackendService, route: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Minimal in-process HTTP facade placeholder for boundary tests."""
    path = str(route or "").strip().lower()
    if path == "submit_job":
        from .submit_job import submit_job

        return submit_job(service, payload)
    if path == "answer_question":
        from .answer_question import answer_question

        return answer_question(service, payload)
    if path == "get_status":
        from .get_status import get_status

        return get_status(service, str(payload.get("job_id", "")))
    if path == "get_result":
        from .get_result import get_result

        return get_result(service, str(payload.get("job_id", "")))
    raise ValueError(f"unsupported route: {route}")
