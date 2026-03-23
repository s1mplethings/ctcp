from __future__ import annotations

import re
from typing import Any, Literal, Mapping

FrontdeskState = Literal[
    "Idle",
    "IntentDetect",
    "Collect",
    "Clarify",
    "Confirm",
    "Execute",
    "AwaitDecision",
    "ReturnResult",
    "InterruptRecover",
    "StyleAdjust",
    "Error",
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
    "Idle",
    "IntentDetect",
    "Collect",
    "Clarify",
    "Confirm",
    "Execute",
    "AwaitDecision",
    "ReturnResult",
    "InterruptRecover",
    "StyleAdjust",
    "Error",
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
    "Idle": {
        "purpose": "No active task line is currently being worked by the frontdesk.",
        "next_states": ["IntentDetect", "StyleAdjust"],
    },
    "IntentDetect": {
        "purpose": "Classify the latest turn before choosing reply strategy.",
        "next_states": ["Collect", "Clarify", "Confirm", "Execute", "AwaitDecision", "ReturnResult", "InterruptRecover", "StyleAdjust", "Error"],
    },
    "Collect": {
        "purpose": "Capture the minimum task object needed to continue.",
        "next_states": ["Clarify", "Confirm", "Execute", "Error"],
    },
    "Clarify": {
        "purpose": "Ask only the blocking detail or mutually exclusive choice.",
        "next_states": ["Confirm", "Execute", "AwaitDecision", "Error"],
    },
    "Confirm": {
        "purpose": "Lock the current task line before or while entering execution.",
        "next_states": ["Execute", "Clarify", "AwaitDecision", "Error"],
    },
    "Execute": {
        "purpose": "Keep the current task moving and answer from run truth.",
        "next_states": ["AwaitDecision", "ReturnResult", "InterruptRecover", "Error"],
    },
    "AwaitDecision": {
        "purpose": "Surface a concrete user decision without losing the task line.",
        "next_states": ["Execute", "ReturnResult", "Error"],
    },
    "ReturnResult": {
        "purpose": "Return concrete progress or result for the active task.",
        "next_states": ["Execute", "InterruptRecover", "Idle", "Error"],
    },
    "InterruptRecover": {
        "purpose": "Handle interruptions while preserving resumable task state.",
        "next_states": ["Execute", "AwaitDecision", "ReturnResult", "Collect", "StyleAdjust", "Error"],
    },
    "StyleAdjust": {
        "purpose": "Persist style preferences without replacing the active task.",
        "next_states": ["Idle", "IntentDetect", "Execute", "InterruptRecover"],
    },
    "Error": {
        "purpose": "Expose the failing stage in a user-safe way and preserve resumable context.",
        "next_states": ["IntentDetect", "Execute", "AwaitDecision", "ReturnResult"],
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
        "state": "Idle",
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
    raw_state = _norm(data.get("state", ""))
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
                    "status": _norm(row.get("status", "")),
                }
            )
        state["decision_points"] = out_points[:4]
    artifacts = data.get("artifacts", [])
    if isinstance(artifacts, list):
        state["artifacts"] = [_norm(item) for item in artifacts if _norm(item)][:6]
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


def _decision_points_from_project_context(project_context: Mapping[str, Any]) -> list[dict[str, str]]:
    decisions = _as_mapping(project_context.get("decisions", {}))
    rows = decisions.get("decisions", [])
    if not isinstance(rows, list):
        rows = []
    out: list[dict[str, str]] = []
    for item in rows:
        row = _as_mapping(item)
        question = _norm(row.get("question_hint", "") or row.get("question", ""))
        if not question:
            continue
        out.append(
            {
                "decision_id": _norm(row.get("decision_id", "")),
                "question": question,
                "status": _norm(row.get("status", "")),
            }
        )
    if out:
        return out[:4]
    status = _as_mapping(project_context.get("status", {}))
    gate = _as_mapping(status.get("gate", {}))
    if bool(status.get("needs_user_decision", False)):
        question = _norm(gate.get("reason", "")) or "decision required"
        return [{"decision_id": "", "question": question, "status": "pending"}]
    return []


def _artifacts_from_context(project_context: Mapping[str, Any] | None, delivery_state: Mapping[str, Any] | None) -> list[str]:
    out: list[str] = []
    if isinstance(project_context, Mapping):
        run_id = _norm(project_context.get("run_id", ""))
        if run_id:
            out.append(f"run_id={run_id}")
        status = _as_mapping(project_context.get("status", {}))
        verify_result = _norm(status.get("verify_result", ""))
        if verify_result:
            out.append(f"verify={verify_result}")
        whiteboard = _as_mapping(project_context.get("whiteboard", {}))
        path = _norm(whiteboard.get("path", ""))
        if path:
            out.append(path)
    if isinstance(delivery_state, Mapping):
        if bool(delivery_state.get("package_ready", False)):
            out.append("delivery:package_ready")
        if bool(delivery_state.get("screenshot_ready", False)):
            out.append("delivery:screenshot_ready")
    return out[:6]


def _delivery_ready(delivery_state: Mapping[str, Any] | None) -> bool:
    if not isinstance(delivery_state, Mapping):
        return False
    return bool(delivery_state.get("package_ready", False) or delivery_state.get("screenshot_ready", False))


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
    profile_state = _as_mapping(session.get("session_profile", {}))
    default_language = _norm(profile_state.get("lang_hint", "")).lower()
    previous = normalize_frontdesk_state(session.get("frontdesk_state", {}), default_language)
    status = _as_mapping(_as_mapping(project_context).get("status", {}))
    gate = _as_mapping(status.get("gate", {}))
    project_memory = _as_mapping(session.get("project_memory", {}))
    project_constraints = _as_mapping(session.get("project_constraints_memory", {}))
    execution_memory = _as_mapping(session.get("execution_memory", {}))

    current_goal = (
        _norm(project_memory.get("project_brief", ""))
        or _norm(session.get("task_summary", ""))
        or _norm(_as_mapping(project_context).get("goal", ""))
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
        or _norm(_as_mapping(project_context).get("run_id", ""))
        or _norm(previous.get("active_task_id", ""))
    )
    has_active_task = bool(active_task_id or current_goal)
    run_status = _norm(status.get("run_status", "")).lower()
    verify_result = _norm(status.get("verify_result", "")).upper()
    done = verify_result == "PASS" or run_status in {"pass", "done", "completed"}
    decision_points = _decision_points_from_project_context(_as_mapping(project_context))
    needs_decision = bool(status.get("needs_user_decision", False)) or bool(decision_points)
    blocked_reason = _norm(gate.get("reason", "")) or _norm(_as_mapping(project_context).get("error", ""))
    if not blocked_reason:
        blocked_reason = _norm(_as_mapping(provider_result).get("reason", ""))

    style_profile, style_changed = apply_style_preferences(
        user_text,
        current_profile=previous.get("user_style_profile", {}),
        default_language=default_language,
    )
    interrupt_kind = classify_interrupt_kind(
        user_text=user_text,
        conversation_mode=conversation_mode,
        has_active_task=has_active_task,
        style_changed=style_changed,
        result_ready=done or _delivery_ready(delivery_state),
    )
    normalized_user_text = _norm(user_text)
    if interrupt_kind == "override" and normalized_user_text and normalized_user_text in {current_goal, current_scope}:
        interrupt_kind = ""

    previous_state = _norm(previous.get("state", ""))
    resumable_state = _norm(previous.get("resumable_state", ""))
    if not resumable_state and previous_state not in {"", "Idle", "IntentDetect", "StyleAdjust"}:
        resumable_state = previous_state
    if not resumable_state and has_active_task:
        resumable_state = "Execute"

    error_status = _norm(_as_mapping(provider_result).get("status", "")).lower()
    has_error = bool(_as_mapping(project_context).get("error")) or error_status in {"exec_failed", "failed", "error"}
    mode = _norm(conversation_mode).upper()
    state: FrontdeskState = "IntentDetect"
    state_reason = ""
    waiting_for = ""

    if has_error:
        state = "Error"
        state_reason = "runtime_or_provider_failure"
    elif style_changed:
        state = "StyleAdjust"
        state_reason = "style_profile_updated"
    elif needs_decision or mode == "PROJECT_DECISION_REPLY":
        state = "AwaitDecision"
        state_reason = "user_decision_required"
        if decision_points:
            waiting_for = _norm(decision_points[0].get("question", ""))
    elif interrupt_kind == "result_query" or (mode == "STATUS_QUERY" and done):
        state = "ReturnResult"
        state_reason = "result_or_delivery_requested"
    elif interrupt_kind in {"status_query", "clarify", "redirect", "override", "sidequest"} and has_active_task:
        state = "InterruptRecover"
        state_reason = f"interrupt:{interrupt_kind}"
    elif mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"} and has_active_task:
        state = "InterruptRecover"
        state_reason = "non_project_turn_preserves_active_task"
    elif not current_goal:
        state = "Idle" if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"} else "Collect"
        state_reason = "no_bound_goal"
    elif mode == "PROJECT_INTAKE":
        state = "Collect" if not active_task_id else "Confirm"
        state_reason = "project_intake"
    elif mode == "PROJECT_DETAIL":
        if not current_scope:
            state = "Clarify"
            state_reason = "scope_missing"
        elif active_task_id:
            state = "Execute"
            state_reason = "active_task_detail_followup"
        else:
            state = "Confirm"
            state_reason = "detail_without_bound_run"
    elif mode == "STATUS_QUERY":
        state = "ReturnResult" if done else ("Execute" if active_task_id else "IntentDetect")
        state_reason = "status_followup"
    elif active_task_id:
        state = "ReturnResult" if done else "Execute"
        state_reason = "active_task_present"
    else:
        state = "Confirm"
        state_reason = "goal_present_without_bound_run"

    if state in {"Execute", "AwaitDecision", "ReturnResult", "InterruptRecover", "StyleAdjust"} and not resumable_state and has_active_task:
        resumable_state = "Execute"
    if state == "StyleAdjust" and not resumable_state:
        resumable_state = "Idle"

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
            "artifacts": _artifacts_from_context(project_context, delivery_state),
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
        "Collect",
        "Clarify",
        "Confirm",
        "Execute",
        "AwaitDecision",
        "ReturnResult",
        "InterruptRecover",
        "Error",
    }
    prefer_progress_binding = interrupt in {"status_query", "result_query"} or state["state"] == "ReturnResult" or mode == "STATUS_QUERY"
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
        allow_existing_project_reference = False
    elif interrupt in {"status_query", "result_query"}:
        allow_existing_project_reference = active_task
    else:
        allow_existing_project_reference = active_task and state["state"] not in {"Idle", "IntentDetect", "StyleAdjust"}
    return {
        "allow_existing_project_reference": bool(allow_existing_project_reference),
        "latest_turn_only": not bool(allow_existing_project_reference),
        "prefer_frontend_render": bool(prefer_frontend_render),
        "prefer_progress_binding": bool(prefer_progress_binding),
    }
