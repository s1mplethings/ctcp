from __future__ import annotations

from typing import Any


def _dict_rows(value: Any) -> list[dict[str, Any]]:
    return [row for row in value if isinstance(row, dict)] if isinstance(value, list) else []


def _nested_scenes(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scenes: list[dict[str, Any]] = []
    for chapter in chapters:
        scenes.extend(_dict_rows(chapter.get("scenes", [])))
    return scenes


def _scene_branch_count(scene: dict[str, Any]) -> int:
    raw_choices = scene.get("choices", [])
    choices = _dict_rows(raw_choices)
    if choices:
        return len(choices)
    if isinstance(raw_choices, list) and any(str(row).strip() for row in raw_choices):
        return len([row for row in raw_choices if str(row).strip()])
    branches = scene.get("branches", [])
    if isinstance(branches, dict):
        return len([key for key in branches if str(key).strip()])
    if isinstance(branches, list) and any(str(row).strip() for row in branches):
        return len([row for row in branches if str(row).strip()])
    choice_map = scene.get("choice_map", {})
    if isinstance(choice_map, dict):
        return len([key for key in choice_map if str(key).strip()])
    return 0


def narrative_sample_metrics(sample_doc: dict[str, Any]) -> dict[str, Any]:
    root = sample_doc.get("project") if isinstance(sample_doc.get("project"), dict) else sample_doc
    characters = _dict_rows(root.get("characters", []))
    chapters = _dict_rows(root.get("chapters", []))
    scenes = _dict_rows(root.get("scenes", [])) or _dict_rows(sample_doc.get("scenes", [])) or _nested_scenes(chapters)
    if not scenes:
        scene_ids = [str(item).strip() for chapter in chapters for item in chapter.get("scenes", []) if str(item).strip()]
        scenes = [{"id": scene_id, "background": scene_id} for scene_id in scene_ids]
    assets = _dict_rows(root.get("assets", [])) or _dict_rows(sample_doc.get("assets", []))
    asset_types = {str(row.get("asset_id", "")).strip(): str(row.get("asset_type", "")).strip().lower() for row in assets}
    explicit_choices = sum(_scene_branch_count(row) for row in scenes) or sum(_scene_branch_count(row) for row in _dict_rows(root.get("branch_points", [])))
    valid_character_cards = sum(
        1
        for row in characters
        if (str(row.get("character_id", "")).strip() or str(row.get("id", "")).strip())
        and str(row.get("name", "")).strip()
        and (str(row.get("role", "")).strip() or str(row.get("profile", "")).strip() or str(row.get("description", "")).strip())
    )
    scenes_with_background = sum(1 for row in scenes if str(row.get("background_asset_id", "") or row.get("background", "") or row.get("bg", "")).strip())
    scenes_with_media_refs = 0
    for row in scenes:
        asset_ids = [str(item).strip() for item in row.get("asset_ids", []) if str(item).strip()]
        direct_media = any(str(row.get(key, "")).strip() for key in ("sprite", "sprites", "sfx", "cg", "characters"))
        if direct_media or any(asset_types.get(asset_id, "") in {"sprite", "sfx", "cg"} for asset_id in asset_ids):
            scenes_with_media_refs += 1
    if scenes_with_media_refs < 2:
        scenes_with_media_refs = min(len(scenes), len([row for row in characters if str(row.get("sprite", "") or row.get("sprites", "")).strip()]))
    return {
        "character_count": len(characters),
        "chapter_count": len(chapters),
        "scene_count": len(scenes),
        "branch_point_count": explicit_choices,
        "explicit_choice_count": explicit_choices,
        "valid_character_cards": valid_character_cards,
        "scenes_with_background": scenes_with_background,
        "scenes_with_media_refs": scenes_with_media_refs,
    }
