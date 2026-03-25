from __future__ import annotations

from typing import Any, Protocol


class BackendTransport(Protocol):
    def submit_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def answer_question(self, payload: dict[str, Any]) -> dict[str, Any]:
        ...

    def get_status(self, job_id: str) -> dict[str, Any]:
        ...

    def get_result(self, job_id: str) -> dict[str, Any]:
        ...

    def poll_events(self, job_id: str) -> list[dict[str, Any]]:
        ...


class _DisconnectedTransport:
    def submit_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        _ = payload
        return {
            "event_type": "event_failure",
            "event_id": "",
            "job_id": "",
            "error_code": "backend_not_connected",
            "message": "backend transport is not connected",
            "details": {},
        }

    def answer_question(self, payload: dict[str, Any]) -> dict[str, Any]:
        _ = payload
        return {
            "event_type": "event_failure",
            "event_id": "",
            "job_id": "",
            "error_code": "backend_not_connected",
            "message": "backend transport is not connected",
            "details": {},
        }

    def get_status(self, job_id: str) -> dict[str, Any]:
        _ = job_id
        return {
            "event_type": "event_failure",
            "event_id": "",
            "job_id": "",
            "error_code": "backend_not_connected",
            "message": "backend transport is not connected",
            "details": {},
        }

    def get_result(self, job_id: str) -> dict[str, Any]:
        _ = job_id
        return {
            "event_type": "event_failure",
            "event_id": "",
            "job_id": "",
            "error_code": "backend_not_connected",
            "message": "backend transport is not connected",
            "details": {},
        }

    def poll_events(self, job_id: str) -> list[dict[str, Any]]:
        _ = job_id
        return []


class BackendClient:
    def __init__(self, transport: BackendTransport | None = None) -> None:
        self.transport = transport or _DisconnectedTransport()

    def submit_job(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.transport.submit_job(payload)

    def answer_question(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.transport.answer_question(payload)

    def get_status(self, job_id: str) -> dict[str, Any]:
        return self.transport.get_status(job_id)

    def get_result(self, job_id: str) -> dict[str, Any]:
        return self.transport.get_result(job_id)

    def poll_events(self, job_id: str) -> list[dict[str, Any]]:
        return self.transport.poll_events(job_id)
