from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def local_full_stack_validation(
    generated_files: list[str],
    run_dir: Path,
    scan_source_texts: Callable[..., list[str]],
    capability_hits: Callable[..., list[str]],
) -> dict[str, Any] | None:
    normalized_generated = [str(path or "").replace("\\", "/") for path in generated_files]
    cases = {
        "local_task_board_app": {
            "profile": "local_full_stack_app",
            "label": "local full-stack",
            "api_keywords": ("/api/tasks", "do_post", "do_patch", "do_delete"),
            "persistence_keywords": ("sqlite3", "tasks table", "create table"),
        },
        "local_kanban_board_app": {
            "profile": "local_full_stack_kanban_app",
            "label": "local Kanban full-stack",
            "api_keywords": ("/boards", "/cards/", "move_card", "do_patch", "do_delete"),
            "persistence_keywords": ("sqlite3", "boards", "cards"),
        },
    }
    selected = next((config for name, config in cases.items() if any(f"/{name}/" in path for path in normalized_generated)), None)
    if selected is None:
        return None
    source_texts = scan_source_texts(run_dir=run_dir, rel_paths=generated_files)
    evidence = {
        "frontend": [path for path in normalized_generated if path.endswith("/static/index.html") or path.endswith("/static/app.js")],
        "api": capability_hits(source_texts=source_texts, keywords=selected["api_keywords"]),
        "persistence": capability_hits(source_texts=source_texts, keywords=selected["persistence_keywords"]),
    }
    missing = [name for name, hits in evidence.items() if not hits]
    label = selected["label"]
    return {
        "profile": selected["profile"],
        "required": True,
        "passed": not missing,
        "checks": [f"{label} capability detected: {name}" for name, hits in evidence.items() if hits],
        "missing": [f"{label} capability missing: {name}" for name in missing],
        "reasons": [],
        "fallback_detected": False,
        "detected_groups": sorted(evidence.keys()),
        "evidence": evidence,
    }
