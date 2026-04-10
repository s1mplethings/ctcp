import re
from typing import Any, Mapping


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def render_snapshot(project_context: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = _as_mapping(project_context)
    for key in ("render_snapshot", "render_state_snapshot", "render_state"):
        row = _as_mapping(source.get(key, {}))
        if row:
            return row
    return {}


def current_snapshot(project_context: Mapping[str, Any] | None) -> Mapping[str, Any]:
    source = _as_mapping(project_context)
    for key in ("current_snapshot", "current_state_snapshot", "current_state"):
        row = _as_mapping(source.get(key, {}))
        if row:
            return row
    return {}


def decision_prompt(project_context: Mapping[str, Any] | None) -> str:
    source = _as_mapping(project_context)
    render = render_snapshot(source)
    cards = render.get("decision_cards", [])
    if isinstance(cards, list):
        for item in cards:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if question:
                return question
    runtime = _as_mapping(source.get("runtime_state", {}))
    rows = runtime.get("pending_decisions", [])
    if isinstance(rows, list):
        for item in rows:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if question:
                return question
    decisions = _as_mapping(source.get("decisions", {}))
    rows = decisions.get("decisions", [])
    if isinstance(rows, list):
        for item in rows:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if question:
                return question
    return ""


def artifact_labels(project_context: Mapping[str, Any] | None) -> list[str]:
    source = _as_mapping(project_context)
    out: list[str] = []
    seen: set[str] = set()

    def _add(raw: Any) -> None:
        text = _norm(raw)
        if not text:
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        out.append(text)

    manifest = _as_mapping(source.get("artifact_manifest", {}))
    for key in ("artifacts", "entries", "files"):
        rows = manifest.get(key, [])
        if isinstance(rows, list):
            for item in rows:
                row = _as_mapping(item)
                _add(row.get("path", "") or row.get("name", "") or row.get("artifact_id", ""))

    outputs = _as_mapping(source.get("output_artifacts", {}))
    rows = outputs.get("artifacts", [])
    if isinstance(rows, list):
        for item in rows:
            row = _as_mapping(item)
            _add(row.get("path", "") or row.get("name", "") or row.get("artifact_id", ""))

    result_event = _as_mapping(source.get("result_event", {}))
    rows = result_event.get("artifacts", [])
    if isinstance(rows, list):
        for item in rows:
            row = _as_mapping(item)
            _add(row.get("path", "") or row.get("name", "") or row.get("artifact_id", ""))

    return out[:6]


def delivery_summary(project_context: Mapping[str, Any] | None) -> dict[str, str]:
    source = _as_mapping(project_context)
    manifest = _as_mapping(source.get("project_manifest", {}))
    return {
        "project_root": _norm(manifest.get("project_root", "")),
        "startup_entrypoint": _norm(manifest.get("startup_entrypoint", "")),
        "startup_readme": _norm(manifest.get("startup_readme", "")),
    }


def has_error_truth(project_context: Mapping[str, Any] | None) -> bool:
    source = _as_mapping(project_context)
    render = render_snapshot(source)
    if _norm(render.get("visible_state", "")).upper() == "ERROR":
        return True
    runtime = _as_mapping(source.get("runtime_state", {}))
    run_status = _norm(runtime.get("run_status", "")).lower()
    if run_status in {"error", "failed", "fail", "aborted"}:
        return True
    error = _as_mapping(runtime.get("error", {}))
    if bool(error.get("has_error", False)):
        return True
    status = _as_mapping(source.get("status", {}))
    run_status = _norm(status.get("run_status", "")).lower()
    return run_status in {"error", "failed", "fail", "aborted"}


def has_result_truth(project_context: Mapping[str, Any] | None) -> bool:
    source = _as_mapping(project_context)
    render = render_snapshot(source)
    visible_state = _norm(render.get("visible_state", "")).upper()
    if visible_state == "DONE":
        return True
    status = _as_mapping(source.get("status", {}))
    runtime = _as_mapping(source.get("runtime_state", {}))
    run_status = _norm(runtime.get("run_status", "") or status.get("run_status", "")).lower()
    done_like = run_status in {"done", "pass", "completed", "success"}
    result_event = _as_mapping(source.get("result_event", {}))
    if result_event:
        result_status = _norm(result_event.get("status", "") or result_event.get("verify_result", "")).lower()
        if (not result_status) or result_status in {"done", "pass", "completed", "success"}:
            return True
    if not done_like:
        return False
    if _as_mapping(source.get("artifact_manifest", {})):
        return True
    outputs = _as_mapping(source.get("output_artifacts", {}))
    rows = outputs.get("artifacts", [])
    return isinstance(rows, list) and bool(rows)
