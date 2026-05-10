from __future__ import annotations

from typing import Any


def apply_narrative_project_spec_defaults(spec: dict[str, Any], project_intent: dict[str, Any]) -> None:
    defaults = {
        "core_modules": [
            "story_outline",
            "scene_graph",
            "choice_flow",
            "cast_cards",
            "background_asset_catalog",
            "sprite_asset_catalog",
            "preview_export",
        ],
        "required_outputs": [
            "storyline.txt",
            "scene_script.rpy",
            "background_asset_catalog.json",
            "character_sprite_catalog.json",
            "playable_route_verification.md",
        ],
        "required_pages_or_views": [
            "project_overview",
            "story_outline",
            "scene_graph",
            "character_cast",
            "asset_catalog",
            "playable_preview",
        ],
        "data_models": ["story_outline", "scene", "choice", "character", "asset_placeholder"],
        "key_interactions": ["edit_story", "branch_choice", "bind_character_asset", "export_preview"],
        "export_targets": ["renpy_script_skeleton.rpy", "story_package.json"],
        "acceptance_criteria": list(project_intent.get("acceptance_criteria", []))
        or ["the generated project declares and satisfies its own domain-specific acceptance criteria"],
        "delivery_requirements": ["runnable project package", "startup instructions", "validation evidence"],
        "explicit_non_goals": ["full commercial VN engine", "production art pipeline", "online publishing platform"],
    }
    for key, value in defaults.items():
        if not isinstance(spec.get(key), list) or not spec.get(key):
            spec[key] = list(value)
        elif key == "required_outputs":
            existing = [str(item) for item in spec.get(key, [])]
            spec[key] = [*existing, *[item for item in value if item not in existing]]
    if not isinstance(spec.get("sample_content_plan"), dict):
        spec["sample_content_plan"] = {
            "pipeline_id": "narrative_vn_sample_generation",
            "steps": ["seed_cast", "write_story_outline", "build_scene_graph", "bind_asset_placeholders", "export_preview"],
        }
