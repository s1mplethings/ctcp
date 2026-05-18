from __future__ import annotations

from tools.providers.project_generation_full_stack_fast_path import full_stack_project_files
from tools.providers.project_generation_issue_tracker_fast_path import issue_tracker_api_files
from tools.providers.project_generation_matrix_fast_paths import concrete_matrix_project_files
from tools.providers.project_generation_non_web_fast_paths import PROJECTS as NON_WEB_PROJECTS, non_web_project_files
from tools.providers.project_generation_provider_assisted import apply_provider_assistance
from tools.providers.project_generation_live_full_candidate import (
    BLIND_CANDIDATE_PROJECTS,
    FULL_CANDIDATE_PROJECTS,
    MEDIUM_CANDIDATE_PROJECTS,
    apply_live_full_candidate,
    deterministic_candidate_files,
)


def try_fast_path_project_files(
    *,
    goal_text: str,
    project_id: str,
    project_root: str,
    workflow_doc_rel: str,
    context_used: list[str],
    project_archetype: str,
) -> dict[str, str] | None:
    def _maybe_assist(files: dict[str, str] | None) -> dict[str, str] | None:
        if files is None:
            return None
        if project_id in FULL_CANDIDATE_PROJECTS or project_id in BLIND_CANDIDATE_PROJECTS or project_id in MEDIUM_CANDIDATE_PROJECTS:
            return apply_live_full_candidate(
                goal_text=goal_text,
                project_id=project_id,
                project_root=project_root,
                deterministic_files=files,
                project_archetype=project_archetype,
            ).files
        return apply_provider_assistance(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            deterministic_files=files,
        ).files

    if project_id in NON_WEB_PROJECTS:
        return _maybe_assist(non_web_project_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
        ))
    if project_id in FULL_CANDIDATE_PROJECTS or project_id in BLIND_CANDIDATE_PROJECTS or project_id in MEDIUM_CANDIDATE_PROJECTS:
        return _maybe_assist(deterministic_candidate_files(
            project_id,
            project_root,
            goal_text,
            project_archetype,
        ))
    if project_id in {"local_task_board_app", "local_kanban_board_app"}:
        return _maybe_assist(full_stack_project_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
        ))
    if project_id in {"todo_rest_api", "markdown_notes_api", "simple_auth_api"}:
        return _maybe_assist(concrete_matrix_project_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
        ))
    if project_id == "local_issue_tracker_api":
        return _maybe_assist(issue_tracker_api_files(
            goal_text=goal_text,
            project_id=project_id,
            project_root=project_root,
            workflow_doc_rel=workflow_doc_rel,
            context_used=context_used,
            project_archetype=project_archetype,
        ))
    return None
