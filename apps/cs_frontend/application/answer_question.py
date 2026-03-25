from __future__ import annotations

from apps.cs_frontend.gateway.backend_client import BackendClient


def answer_question(backend_client: BackendClient, payload: dict[str, object]) -> dict[str, object]:
    return backend_client.answer_question(payload)
