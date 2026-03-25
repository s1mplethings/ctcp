from __future__ import annotations

from apps.project_backend.application.service import ProjectBackendService
from apps.project_backend.config import BackendConfig


def bootstrap_backend(config: BackendConfig | None = None) -> ProjectBackendService:
    return ProjectBackendService(config=config or BackendConfig())
