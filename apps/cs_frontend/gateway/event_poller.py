from __future__ import annotations

from apps.cs_frontend.gateway.backend_client import BackendClient


class EventPoller:
    def __init__(self, backend_client: BackendClient) -> None:
        self.backend_client = backend_client

    def poll(self, job_id: str) -> list[dict[str, object]]:
        return self.backend_client.poll_events(job_id)
