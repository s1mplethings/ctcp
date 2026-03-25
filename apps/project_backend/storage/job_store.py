from __future__ import annotations

from apps.project_backend.domain.job import JobRecord


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}

    def put(self, job: JobRecord) -> None:
        self._jobs[job.job_id] = job

    def get(self, job_id: str) -> JobRecord:
        return self._jobs[job_id]

    def has(self, job_id: str) -> bool:
        return job_id in self._jobs
