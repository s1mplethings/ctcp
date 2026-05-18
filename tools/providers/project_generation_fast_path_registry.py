from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools.providers.project_generation_issue_tracker_fast_path import (
    is_issue_tracker_api_goal,
    issue_tracker_api_defaults,
)
from tools.providers.project_generation_matrix_fast_paths import (
    PROJECTS as MATRIX_PROJECTS,
    concrete_matrix_defaults,
    concrete_project_provenance,
    detect_concrete_matrix_project,
)
from tools.providers.project_generation_full_stack_fast_path import (
    FULL_STACK_PROJECT_IDS,
    detect_full_stack_project,
    full_stack_defaults,
    full_stack_project_provenance,
)
from tools.providers.project_generation_non_web_fast_paths import (
    PROJECTS as NON_WEB_PROJECTS,
    detect_non_web_project,
    non_web_defaults,
    non_web_project_provenance,
)
from tools.providers.project_generation_live_full_candidate import (
    BLIND_CANDIDATE_PROJECTS,
    FULL_CANDIDATE_PROJECTS,
    MEDIUM_CANDIDATE_PROJECTS,
    detect_live_blind_candidate_project,
    detect_live_full_candidate_project,
    detect_live_medium_candidate_project,
    live_full_candidate_defaults,
    live_full_candidate_provenance,
)


@dataclass(frozen=True)
class FastPathMatch:
    project_id: str
    family: str


def detect_fast_path(goal: str) -> FastPathMatch | None:
    live_medium_project = detect_live_medium_candidate_project(goal)
    if live_medium_project:
        return FastPathMatch(live_medium_project, "live_provider_medium_candidate")
    live_blind_project = detect_live_blind_candidate_project(goal)
    if live_blind_project:
        return FastPathMatch(live_blind_project, "live_provider_blind_candidate")
    live_full_project = detect_live_full_candidate_project(goal)
    if live_full_project:
        return FastPathMatch(live_full_project, "live_provider_full_candidate")
    non_web_project = detect_non_web_project(goal)
    if non_web_project:
        return FastPathMatch(non_web_project, "non_web")
    full_stack_project = detect_full_stack_project(goal)
    if full_stack_project:
        return FastPathMatch(full_stack_project, "full_stack")
    matrix_project = detect_concrete_matrix_project(goal)
    if matrix_project:
        return FastPathMatch(matrix_project, "concrete_matrix")
    if is_issue_tracker_api_goal(goal):
        return FastPathMatch("local_issue_tracker_api", "issue_tracker")
    return None


def detect_fast_path_project(goal: str) -> str:
    match = detect_fast_path(goal)
    return match.project_id if match else ""


def fast_path_defaults(project_id: str) -> dict[str, Any]:
    if project_id in FULL_CANDIDATE_PROJECTS or project_id in BLIND_CANDIDATE_PROJECTS or project_id in MEDIUM_CANDIDATE_PROJECTS:
        return live_full_candidate_defaults(project_id)
    if project_id in NON_WEB_PROJECTS:
        return non_web_defaults(project_id)
    if project_id in FULL_STACK_PROJECT_IDS:
        return full_stack_defaults(project_id)
    if project_id in MATRIX_PROJECTS:
        return concrete_matrix_defaults(project_id)
    if project_id == "local_issue_tracker_api":
        return issue_tracker_api_defaults()
    return {}


def fast_path_provenance(project_id: str) -> dict[str, Any]:
    if project_id in FULL_CANDIDATE_PROJECTS or project_id in BLIND_CANDIDATE_PROJECTS or project_id in MEDIUM_CANDIDATE_PROJECTS:
        return live_full_candidate_provenance(project_id)
    if project_id in NON_WEB_PROJECTS:
        return non_web_project_provenance(project_id)
    if project_id in FULL_STACK_PROJECT_IDS:
        return full_stack_project_provenance(project_id)
    return concrete_project_provenance(project_id)


def registered_fast_path_ids() -> list[str]:
    return [
        "local_issue_tracker_api",
        *sorted(FULL_CANDIDATE_PROJECTS.keys()),
        *sorted(BLIND_CANDIDATE_PROJECTS.keys()),
        *sorted(MEDIUM_CANDIDATE_PROJECTS.keys()),
        *sorted(NON_WEB_PROJECTS.keys()),
        *sorted(MATRIX_PROJECTS.keys()),
        *sorted(FULL_STACK_PROJECT_IDS),
    ]
