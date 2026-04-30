from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.providers.project_generation_artifacts import is_project_generation_goal


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _is_project_generation_workflow_id(value: str) -> bool:
    text = str(value or "").strip().lower()
    if text == "wf_project_generation_manifest":
        return True
    return bool(text and ("project_generation" in text or "project-generation" in text))


def is_project_generation_plan_request(*, run_dir: Path, request: dict[str, Any], goal: str) -> bool:
    if is_project_generation_goal(goal):
        return True
    action = str(request.get("action", "")).strip().lower()
    if action not in {"plan_draft", "plan_signed"}:
        return False
    reason = str(request.get("reason", "")).strip().lower()
    if "project-generation" in reason or "project generation" in reason:
        return True
    target_path = str(request.get("target_path", "")).strip().lower()
    if "project-generation" in target_path or "project_generation" in target_path:
        return True
    find_result = _read_json_file(run_dir / "artifacts" / "find_result.json")
    if _is_project_generation_workflow_id(str(find_result.get("selected_workflow_id", ""))):
        return True
    freeze_doc = _read_json_file(run_dir / "artifacts" / "output_contract_freeze.json")
    return _is_project_generation_workflow_id(str(freeze_doc.get("selected_workflow_id", "")))
