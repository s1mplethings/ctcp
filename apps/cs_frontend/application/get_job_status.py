from __future__ import annotations

from apps.cs_frontend.gateway.backend_client import BackendClient


def get_job_status(backend_client: BackendClient, job_id: str) -> dict[str, object]:
    return backend_client.get_status(job_id)
