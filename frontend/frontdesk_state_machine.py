from __future__ import annotations

import re
from typing import Any, Literal, Mapping

FrontdeskState = Literal[
    "idle",
    "collecting_input",
    "showing_progress",
    "waiting_user_reply",
    "showing_decision",
    "showing_result",
    "showing_error",
]

InterruptKind = Literal[
    "",
    "clarify",
    "redirect",
    "override",
    "sidequest",
    "style_change",
    "status_query",
    "result_query",
]

FRONTDESK_STATES: tuple[FrontdeskState, ...] = (
    "idle",
    "collecting_input",
    "showing_progress",
    "waiting_user_reply",
    "showing_decision",
    "showing_result",
    "showing_error",
)

INTERRUPT_KINDS: tuple[InterruptKind, ...] = (
    "",
    "clarify",
    "redirect",
    "override",
    "sidequest",
    "style_change",
    "status_query",
    "result_query",
)

STATE_DEFINITIONS: dict[FrontdeskState, dict[str, Any]] = {
    "idle": {
        "purpose": "No active task is bound in display layer.",
        "next_states": ["collecting_input", "showing_progress", "waiting_user_reply"],
    },
    "collecting_input": {
        "purpose": "Collect minimal missing user inputs.",
        "next_states": ["waiting_user_reply", "showing_progress", "showing_decision"],
    },
    "showing_progress": {
        "purpose": "Render backend progress without owning execution truth.",
        "next_states": ["showing_decision", "showing_result", "showing_error", "waiting_user_reply"],
    },
    "waiting_user_reply": {
        "purpose": "Wait for user clarification/reply from display flow.",
        "next_states": ["showing_progress", "showing_decision", "showing_error"],
    },
    "showing_decision": {
        "purpose": "Show backend-provided decision cards only.",
        "next_states": ["showing_progress", "showing_result", "showing_error"],
    },
    "showing_result": {
        "purpose": "Show backend-confirmed result/event/artifact outputs.",
        "next_states": ["showing_progress", "idle", "showing_error"],
    },
    "showing_error": {
        "purpose": "Show backend-reported error/recovery states.",
        "next_states": ["waiting_user_reply", "showing_progress", "showing_decision"],
    },
}

_STATUS_QUERY_RE = re.compile(
    r"(进度|状态(?!机)|做到什么程度|做到哪|做到哪一步|现在什么情况|现在怎么样|结果如何|status|progress|update|where are we|what.?s done)",
    re.IGNORECASE,
)
_RESULT_QUERY_RE = re.compile(
    r"(结果|成品|交付|发我|给我看|zip|截图|screenshot|package|deliver|delivery|result|output|ready)",
    re.IGNORECASE,
)
_STYLE_CHANGE_RE = re.compile(
    r"(中文|英文|english|language|语气|口吻|风格|自然一点|别太机械|正式一点|直接一点|详细一点|简短一点|verbosity|tone|initiative|主动一点|少问)",
    re.IGNORECASE,
)
_OVERRIDE_RE = re.compile(r"(别做之前|换成|改成|不要之前|重新换一个|switch to|instead of)", re.IGNORECASE)
_SIDEQUEST_RE = re.compile(r"(顺便|另外|还有一个|与此同时|by the way|also help|another thing)", re.IGNORECASE)
_CLARIFY_RE = re.compile(r"(补充一下|我的意思是|准确来说|更准确地说|补一句|clarify|to clarify|i mean)", re.IGNORECASE)
_REDIRECT_RE = re.compile(r"(先不说这个|先看这个|回到刚才|先聊这个|switch back|let.?s focus on)", re.IGNORECASE)
_STYLE_LANGUAGE_ZH_RE = re.compile(r"(中文|汉语|Chinese)", re.IGNORECASE)
_STYLE_LANGUAGE_EN_RE = re.compile(r"(英文|English)", re.IGNORECASE)
_STYLE_TONE_MAP: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(自然一点|自然些|别太机械|not so mechanical|natural)", re.IGNORECASE), "natural"),
    (re.compile(r"(正式一点|更正式|formal)", re.IGNORECASE), "formal"),
    (re.compile(r"(直接一点|更直接|direct)", re.IGNORECASE), "direct"),
    (re.compile(r"(任务导向|task[- ]?oriented|task driven)", re.IGNORECASE), "task_progressive"),
)
_STYLE_INITIATIVE_MAP: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(主动一点|多推进|更主动|proactive|take initiative)", re.IGNORECASE), "proactive"),
    (re.compile(r"(少主动|别太主动|需要时再问|less proactive|ask only when needed)", re.IGNORECASE), "guarded"),
)
_STYLE_VERBOSITY_MAP: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(简短一点|简洁一点|别太啰嗦|brief|short|concise)", re.IGNORECASE), "brief"),
    (re.compile(r"(详细一点|展开一点|说细一点|detailed|longer)", re.IGNORECASE), "detailed"),
)


def _norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def default_style_profile(default_language: str = "") -> dict[str, str]:
    return {
        "language": _norm(default_language).lower() or "auto",
        "tone": "task_progressive",
        "initiative": "balanced",
        "verbosity": "normal",
    }


def default_frontdesk_state(default_language: str = "") -> dict[str, Any]:
    return {
        "state": "idle",
        "interrupt_kind": "",
        "current_goal": "",
        "current_scope": "",
        "active_task_id": "",
        "waiting_for": "",
        "user_style_profile": default_style_profile(default_language),
        "decision_points": [],
        "artifacts": [],
        "blocked_reason": "",
        "resumable_state": "",
        "latest_conversation_mode": "",
        "state_reason": "",
    }


def normalize_style_profile(raw: Any, default_language: str = "") -> dict[str, str]:
    profile = default_style_profile(default_language)
    if isinstance(raw, Mapping):
        for key in ("language", "tone", "initiative", "verbosity"):
            value = _norm(raw.get(key, ""))
            if value:
                profile[key] = value.lower()
    return profile


def normalize_frontdesk_state(raw: Any, default_language: str = "") -> dict[str, Any]:
    state = default_frontdesk_state(default_language)
    data = raw if isinstance(raw, Mapping) else {}
    raw_state = _norm(data.get("state", "")).lower()
    if raw_state in FRONTDESK_STATES:
        state["state"] = raw_state
    raw_interrupt = _norm(data.get("interrupt_kind", ""))
    if raw_interrupt in INTERRUPT_KINDS:
        state["interrupt_kind"] = raw_interrupt
    for key in (
        "current_goal",
        "current_scope",
        "active_task_id",
        "waiting_for",
        "blocked_reason",
        "resumable_state",
        "latest_conversation_mode",
        "state_reason",
    ):
        state[key] = _norm(data.get(key, state[key]))
    state["user_style_profile"] = normalize_style_profile(data.get("user_style_profile", {}), default_language)
    decision_points = data.get("decision_points", [])
    if isinstance(decision_points, list):
        out_points: list[dict[str, str]] = []
        for item in decision_points:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if not question:
                continue
            out_points.append(
                {
                    "decision_id": _norm(row.get("decision_id", "")),
                    "question": question,
                    "status": _norm(row.get("status", "")) or "pending",
                }
            )
        state["decision_points"] = out_points[:8]
    artifacts = data.get("artifacts", [])
    if isinstance(artifacts, list):
        state["artifacts"] = [_norm(item) for item in artifacts if _norm(item)][:8]
    return state


def apply_style_preferences(text: str, current_profile: Mapping[str, Any] | None = None, default_language: str = "") -> tuple[dict[str, str], bool]:
    profile = normalize_style_profile(current_profile or {}, default_language)
    raw = _norm(text)
    if not raw:
        return profile, False
    original = dict(profile)
    if _STYLE_LANGUAGE_ZH_RE.search(raw):
        profile["language"] = "zh"
    elif _STYLE_LANGUAGE_EN_RE.search(raw):
        profile["language"] = "en"
    for pattern, tone in _STYLE_TONE_MAP:
        if pattern.search(raw):
            profile["tone"] = tone
            break
    for pattern, initiative in _STYLE_INITIATIVE_MAP:
        if pattern.search(raw):
            profile["initiative"] = initiative
            break
    for pattern, verbosity in _STYLE_VERBOSITY_MAP:
        if pattern.search(raw):
            profile["verbosity"] = verbosity
            break
    return profile, profile != original


def classify_interrupt_kind(
    *,
    user_text: str,
    conversation_mode: str,
    has_active_task: bool,
    style_changed: bool = False,
    result_ready: bool = False,
) -> InterruptKind:
    raw = _norm(user_text)
    mode = _norm(conversation_mode).upper()
    if not raw:
        return ""
    if style_changed or _STYLE_CHANGE_RE.search(raw):
        return "style_change"
    if mode == "STATUS_QUERY" or _STATUS_QUERY_RE.search(raw):
        if result_ready or _RESULT_QUERY_RE.search(raw):
            return "result_query"
        return "status_query"
    if not has_active_task:
        return ""
    if _OVERRIDE_RE.search(raw):
        return "override"
    if _SIDEQUEST_RE.search(raw):
        return "sidequest"
    if _REDIRECT_RE.search(raw):
        return "redirect"
    if _CLARIFY_RE.search(raw):
        return "clarify"
    return ""


def _render_snapshot(project_context: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("render_snapshot", "render_state_snapshot", "render_state"):
        candidate = project_context.get(key, {})
        if isinstance(candidate, Mapping) and candidate:
            return candidate
    return {}


def _current_snapshot(project_context: Mapping[str, Any]) -> Mapping[str, Any]:
    for key in ("current_snapshot", "current_state_snapshot", "current_state"):
        candidate = project_context.get(key, {})
        if isinstance(candidate, Mapping) and candidate:
            return candidate
    return {}


def _decision_points_from_project_context(project_context: Mapping[str, Any]) -> list[dict[str, str]]:
    render = _as_mapping(_render_snapshot(project_context))
    decision_cards = render.get("decision_cards", [])
    if isinstance(decision_cards, list):
        out: list[dict[str, str]] = []
        for item in decision_cards:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if not question:
                continue
            out.append(
                {
                    "decision_id": _norm(row.get("decision_id", "")),
                    "question": question,
                    "status": _norm(row.get("status", "")) or "pending",
                }
            )
        if out:
            return out[:8]

    decisions = _as_mapping(project_context.get("decisions", {}))
    rows = decisions.get("decisions", [])
    if isinstance(rows, list):
        out = []
        for item in rows:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if not question:
                continue
            out.append(
                {
                    "decision_id": _norm(row.get("decision_id", "")),
                    "question": question,
                    "status": _norm(row.get("status", "")) or "pending",
                }
            )
        if out:
            return out[:8]

    runtime_state = _as_mapping(project_context.get("runtime_state", {}))
    runtime_rows = runtime_state.get("pending_decisions", [])
    if isinstance(runtime_rows, list):
        out = []
        for item in runtime_rows:
            row = _as_mapping(item)
            question = _norm(row.get("question", "") or row.get("question_hint", ""))
            if not question:
                continue
            out.append(
                {
                    "decision_id": _norm(row.get("decision_id", "")),
                    "question": question,
                    "status": _norm(row.get("status", "")) or "pending",
                }
            )
        if out:
            return out[:8]
    return []


def _artifacts_from_context(project_context: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(project_context, Mapping):
        return []
    out: list[str] = []
    listing = project_context.get("output_artifacts", {})
    rows = []
    if isinstance(listing, Mapping):
        value = listing.get("artifacts", [])
        rows = value if isinstance(value, list) else []
    for item in rows[:6]:
        row = _as_mapping(item)
        rel = _norm(row.get("rel_path", ""))
        if rel:
            out.append(rel)
    manifest = _as_mapping(project_context.get("artifact_manifest", {}))
    for key in ("source_files", "doc_files", "workflow_files"):
        value = manifest.get(key, [])
        if isinstance(value, list):
            for path in value:
                normalized = _norm(path)
                if normalized and normalized not in out:
                    out.append(normalized)
                    if len(out) >= 8:
                        return out
    run_id = _norm(project_context.get("run_id", ""))
    if run_id and (not out):
        out.append(f"run_id={run_id}")
    return out[:8]


def derive_frontdesk_state(
    *,
    user_text: str,
    conversation_mode: str,
    session_state: Mapping[str, Any] | None,
    project_context: Mapping[str, Any] | None = None,
    delivery_state: Mapping[str, Any] | None = None,
    provider_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    session = _as_mapping(session_state)
    project = _as_mapping(project_context)
    profile_state = _as_mapping(session.get("session_profile", {}))
    default_language = _norm(profile_state.get("lang_hint", "")).lower()
    previous = normalize_frontdesk_state(session.get("frontdesk_state", {}), default_language)

    render = _as_mapping(_render_snapshot(project))
    current = _as_mapping(_current_snapshot(project))
    runtime_state = _as_mapping(project.get("runtime_state", {}))

    project_memory = _as_mapping(session.get("project_memory", {}))
    project_constraints = _as_mapping(session.get("project_constraints_memory", {}))
    execution_memory = _as_mapping(session.get("execution_memory", {}))

    current_goal = (
        _norm(project_memory.get("project_brief", ""))
        or _norm(session.get("task_summary", ""))
        or _norm(project.get("goal", ""))
        or _norm(previous.get("current_goal", ""))
    )
    current_scope = (
        _norm(project_constraints.get("constraint_brief", ""))
        or _norm(execution_memory.get("latest_user_directive", ""))
        or _norm(previous.get("current_scope", ""))
        or current_goal
    )
    active_task_id = (
        _norm(session.get("bound_run_id", ""))
        or _norm(project.get("run_id", ""))
        or _norm(previous.get("active_task_id", ""))
    )
    has_active_task = bool(active_task_id or current_goal)

    style_profile, style_changed = apply_style_preferences(
        user_text,
        current_profile=previous.get("user_style_profile", {}),
        default_language=default_language,
    )

    decision_points = _decision_points_from_project_context(project)
    pending_decision_points = [
        row for row in decision_points if _norm(_as_mapping(row).get("status", "")).lower() in {"", "pending"}
    ]

    visible_state = _norm(render.get("visible_state", "")).upper()
    ui_badge = _norm(render.get("ui_badge", "")).lower()
    followup_questions = render.get("followup_questions", [])
    if not isinstance(followup_questions, list):
        followup_questions = []

    decision_from_render = bool(render.get("decision_cards", [])) if isinstance(render.get("decision_cards", []), list) else False
    needs_decision = bool(pending_decision_points) or decision_from_render or visible_state == "WAITING_FOR_DECISION"

    authoritative_stage = _norm(current.get("authoritative_stage", "")).upper() or _norm(runtime_state.get("phase", "")).upper()
    has_error = (
        visible_state in {"BLOCKED_NEEDS_INPUT", "ERROR"}
        or ui_badge in {"error", "failed"}
        or authoritative_stage in {"FAILED"}
        or bool(_as_mapping(runtime_state.get("error", {})).get("has_error", False))
        or _norm(_as_mapping(provider_result).get("status", "")).lower() in {"exec_failed", "failed", "error"}
    )

    result_event = _as_mapping(project.get("result_event", {}))
    artifact_manifest = _as_mapping(project.get("artifact_manifest", {}))
    output_artifacts = _as_mapping(project.get("output_artifacts", {}))
    output_rows = output_artifacts.get("artifacts", [])
    has_output_payload = isinstance(output_rows, list) and len(output_rows) > 0
    has_result_payload = bool(result_event) or bool(artifact_manifest) or bool(has_output_payload)
    done_from_render = visible_state == "DONE"

    blocked_reason = (
        _norm(current.get("current_blocker", ""))
        or _norm(render.get("progress_summary", ""))
        or _norm(previous.get("blocked_reason", ""))
    )

    mode = _norm(conversation_mode).upper()
    interrupt_kind = classify_interrupt_kind(
        user_text=user_text,
        conversation_mode=conversation_mode,
        has_active_task=has_active_task,
        style_changed=style_changed,
        result_ready=bool(done_from_render and has_result_payload),
    )

    state: FrontdeskState = "showing_progress"
    state_reason = "render_progress"
    waiting_for = ""

    if has_error:
        state = "showing_error"
        state_reason = "backend_error_or_blocked"
    elif needs_decision or mode == "PROJECT_DECISION_REPLY":
        state = "showing_decision"
        state_reason = "backend_decision_required"
        if pending_decision_points:
            waiting_for = _norm(pending_decision_points[0].get("question", ""))
        elif decision_points:
            waiting_for = _norm(decision_points[0].get("question", ""))
    elif done_from_render and has_result_payload:
        state = "showing_result"
        state_reason = "backend_render_done_with_payload"
    elif style_changed:
        state = "waiting_user_reply"
        state_reason = "style_profile_updated"
    elif not current_goal:
        state = "idle" if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"} else "collecting_input"
        state_reason = "goal_missing"
    elif mode == "PROJECT_INTAKE":
        state = "collecting_input"
        state_reason = "project_intake"
    elif mode == "PROJECT_DETAIL" and followup_questions:
        state = "waiting_user_reply"
        state_reason = "render_followup_question"
        waiting_for = _norm(followup_questions[0]) if followup_questions else ""
    elif visible_state in {"UNDERSTOOD", "EXECUTING", ""}:
        state = "showing_progress"
        state_reason = "render_progress"
    else:
        state = "showing_progress"
        state_reason = "default_render_progress"

    if state == "showing_result" and (not has_result_payload):
        state = "showing_progress"
        state_reason = "render_done_without_payload"

    resumable_state = ""
    if state in {"showing_progress", "showing_decision", "waiting_user_reply", "showing_result"} and has_active_task:
        resumable_state = "showing_progress"

    return normalize_frontdesk_state(
        {
            "state": state,
            "interrupt_kind": interrupt_kind,
            "current_goal": current_goal,
            "current_scope": current_scope,
            "active_task_id": active_task_id,
            "waiting_for": waiting_for or _norm(previous.get("waiting_for", "")),
            "user_style_profile": style_profile,
            "decision_points": decision_points,
            "artifacts": _artifacts_from_context(project_context),
            "blocked_reason": blocked_reason,
            "resumable_state": resumable_state,
            "latest_conversation_mode": mode,
            "state_reason": state_reason,
        },
        default_language,
    )


def prompt_context_from_frontdesk_state(frontdesk_state: Mapping[str, Any] | None, *, include_task_context: bool) -> dict[str, Any]:
    state = normalize_frontdesk_state(frontdesk_state or {})
    contract = STATE_DEFINITIONS.get(state["state"], {})
    context = {
        "state": state["state"],
        "interrupt_kind": state["interrupt_kind"],
        "latest_conversation_mode": state["latest_conversation_mode"],
        "state_reason": state["state_reason"],
        "waiting_for": state["waiting_for"],
        "user_style_profile": dict(state["user_style_profile"]),
        "resumable_state": state["resumable_state"],
        "state_contract": {
            "purpose": contract.get("purpose", ""),
            "next_states": list(contract.get("next_states", [])),
        },
    }
    if include_task_context:
        context.update(
            {
                "current_goal": state["current_goal"],
                "current_scope": state["current_scope"],
                "active_task_id": state["active_task_id"],
                "decision_points": list(state["decision_points"]),
                "artifacts": list(state["artifacts"]),
                "blocked_reason": state["blocked_reason"],
            }
        )
    else:
        context.update(
            {
                "current_goal": "",
                "current_scope": "",
                "active_task_id": "",
                "decision_points": [],
                "artifacts": [],
                "blocked_reason": "",
            }
        )
    return context


def reply_strategy_from_frontdesk_state(
    frontdesk_state: Mapping[str, Any] | None,
    *,
    conversation_mode: str,
) -> dict[str, Any]:
    state = normalize_frontdesk_state(frontdesk_state or {})
    mode = _norm(conversation_mode).upper()
    active_task = bool(state["active_task_id"])
    interrupt = state["interrupt_kind"]
    prefer_frontend_render = state["state"] in {
        "collecting_input",
        "showing_progress",
        "waiting_user_reply",
        "showing_decision",
        "showing_result",
        "showing_error",
    }
    prefer_progress_binding = interrupt in {"status_query", "result_query"} or state["state"] in {"showing_progress", "showing_result"} or mode == "STATUS_QUERY"
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        allow_existing_project_reference = False
    elif interrupt in {"status_query", "result_query"}:
        allow_existing_project_reference = active_task
    else:
        allow_existing_project_reference = active_task and state["state"] not in {"idle", "collecting_input"}
    return {
        "allow_existing_project_reference": bool(allow_existing_project_reference),
        "latest_turn_only": not bool(allow_existing_project_reference),
        "prefer_frontend_render": bool(prefer_frontend_render),
        "prefer_progress_binding": bool(prefer_progress_binding),
    }
