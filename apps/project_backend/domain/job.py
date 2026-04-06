from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from contracts.enums import JobPhase


@dataclass
class JobRecord:
    job_id: str
    request_id: str
    run_id: str
    run_dir: str
    user_goal: str
    project_intent: dict[str, Any] = field(default_factory=dict)
    project_spec: dict[str, Any] = field(default_factory=dict)
    pipeline_summary: dict[str, Any] = field(default_factory=dict)
    delivery_evidence: dict[str, Any] = field(default_factory=dict)
    constraints: dict[str, Any] = field(default_factory=dict)
    phase: JobPhase = JobPhase.CREATED
