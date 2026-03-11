from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .conversation_mode_router import (
    ConversationMode,
    can_emit_project_followup,
    compute_task_signal_score,
    has_sufficient_task_signal,
    has_valid_task_summary,
    is_generic_tradeoff_question,
    route_conversation_mode,
)
from .message_sanitizer import sanitize_internal_text
from .missing_info_rewriter import infer_missing_fields_from_text, rewrite_missing_requirements
from .project_manager_mode import (
    build_default_assumptions,
    extract_known_project_facts,
    is_generic_intake_question,
    requirement_information_score,
    select_best_requirement_source,
)
from .state_resolver import VisibleState, resolve_visible_state


@dataclass
class InternalReplyPipelineState:
    conversation_context: dict[str, Any] = field(default_factory=dict)
    conversation_mode: ConversationMode = "SMALLTALK"
    selected_requirement_source: str = ""
    task_summary: str = ""
    known_facts: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    candidate_questions: list[str] = field(default_factory=list)
    draft_reply: str = ""
    review_flags: list[str] = field(default_factory=list)
    sanitized_reply: str = ""
    final_reply: str = ""
    visible_state: VisibleState = "NEEDS_ONE_OR_TWO_DETAILS"
    missing_fields: list[str] = field(default_factory=list)
    redactions: int = 0
    task_signal_score: float = 0.0
    has_sufficient_task_signal: bool = False


@dataclass(frozen=True)
class FrontendRenderResult:
    visible_state: VisibleState
    reply_text: str
    followup_questions: tuple[str, ...]
    missing_fields: tuple[str, ...]
    redactions: int
    pipeline_state: Mapping[str, Any] | None = None


_FORBIDDEN_PUBLIC_TOKENS = (
    "command failed",
    "stack trace",
    "stderr",
    "stdout",
    "exit code",
    "return code",
    "raw prompt",
    "internal prompt",
    "provider log",
    "tool logs",
    "artifact dump",
    "analysis.md",
    "plan_draft.md",
    "blocked_needs_input",
    "waiting for",
    "outbox",
    "run_dir",
    "artifact",
    "patch",
    # Chinese internal terms that must never reach the user
    "\u5f85\u5904\u7406\u7684\u4e8b\u9879",  # 待处理的事项
    "\u9700\u8981\u7684\u4fe1\u606f",  # 需要的信息
    "\u7b49\u5f85\u5fc5\u8981\u8f93\u5165",  # 等待必要输入
    "\u5f53\u524d\u963b\u585e\u9879",  # 当前阻塞项
    "\u9700\u8981\u8865\u5145",  # 需要补充 (when used with colon as label)
)
_FORBIDDEN_PUBLIC_LABEL_RE = re.compile(r"\b(CONTEXT|CONSTRAINTS|EXTERNALS|PLAN|PATCH)\b")
_RC_FIELD_RE = re.compile(r"\b(?:rc|exit[_ ]?code|return[_ ]?code)\s*[:=]?\s*\d+\b", re.IGNORECASE)
_WAITING_INTERNAL_REQUEST_RE = re.compile(r"\bwaiting\s+for\s+[^\s]+\.(?:md|json|patch)\b", re.IGNORECASE)


def _question_block(questions: list[str], *, lang: str) -> str:
    picked = [q.strip() for q in questions if str(q).strip()][:2]
    if not picked:
        return ""
    if len(picked) == 1:
        return picked[0]
    if lang == "en":
        return f"1. {picked[0]}\n2. {picked[1]}"
    return f"1. {picked[0]}\n2. {picked[1]}"


def _join_questions(questions: list[str], *, lang: str) -> str:
    picked = [q.strip() for q in questions if str(q).strip()][:2]
    if not picked:
        return ""
    if lang == "en":
        if len(picked) == 1:
            return picked[0]
        return f"{picked[0]} Also, {picked[1]}"
    if len(picked) == 1:
        return picked[0]
    return f"{picked[0]}另外，{picked[1]}"


def _execution_direction_text(note: Mapping[str, Any], lang: str) -> str:
    explicit = str(note.get("execution_direction", "")).strip()
    if explicit:
        return explicit
    assumptions = note.get("assumptions", {})
    if not isinstance(assumptions, Mapping):
        assumptions = {}
    semantic_plan = str(assumptions.get("semantic_plan", "")).strip()
    if lang == "en":
        if semantic_plan == "integrate_semantic_in_v1":
            return "I will prioritize speed, land a runnable main pipeline first, and integrate semantic capability directly in V1."
        return "I will prioritize speed, land a runnable main pipeline first, and keep semantic capability as an extension path."
    if semantic_plan == "integrate_semantic_in_v1":
        return "接下来我会先按“优先速度、先跑通主流程、语义能力第一版直接接入”的方向整理第一版方案。"
    return "接下来我会先按“优先速度、先跑通主流程、语义能力后接入或并联”的方向整理第一版方案，不先让你补一堆非关键细节。"


def _filter_missing_fields_with_known_facts(missing_fields: list[str], known_facts: Mapping[str, Any]) -> list[str]:
    if not isinstance(known_facts, Mapping):
        return missing_fields
    out: list[str] = []
    for field in missing_fields:
        name = str(field or "").strip()
        if not name:
            continue
        if name == "input_mode":
            value = str(known_facts.get("input_mode", "unknown"))
            if value not in {"unknown", ""}:
                continue
        if name == "runtime_target":
            value = str(known_facts.get("runtime_target", "unknown"))
            if value not in {"unknown", "", "speed_first_unresolved"}:
                continue
        if name == "semantic_integration_level":
            value = str(known_facts.get("semantic_integration_level", "unknown"))
            if value not in {"unknown", ""}:
                continue
        if name == "output_format":
            value = str(known_facts.get("output_format", "unknown"))
            if value not in {"unknown", ""}:
                continue
        out.append(name)
    return out


def _parse_positive_int(raw: Any, default: int, *, min_value: int, max_value: int) -> int:
    try:
        val = int(raw)
    except Exception:
        return default
    return max(min_value, min(max_value, val))


def _serialize_key_values(rows: Mapping[str, Any]) -> list[str]:
    out: list[str] = []
    for key in sorted(rows.keys()):
        value = str(rows.get(key, "")).strip()
        if not value or value in {"unknown", "Unknown"}:
            continue
        out.append(f"{key}={value}")
    return out


def _dedupe_items(items: list[str], *, limit: int = 2) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = re.sub(r"\s+", " ", str(item or "").strip())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max(1, limit):
            break
    return out


def _question_already_answered(question: str, known_facts: Mapping[str, Any]) -> bool:
    q = str(question or "").lower()
    if not q:
        return True
    input_mode = str(known_facts.get("input_mode", "unknown"))
    runtime_target = str(known_facts.get("runtime_target", "unknown"))
    deployment = str(known_facts.get("deployment_boundary", "unknown"))
    output_format = str(known_facts.get("output_format", "unknown"))
    semantic = str(known_facts.get("semantic_integration_level", "unknown"))
    if any(k in q for k in ("单目", "多视角", "single", "multi-view")) and input_mode not in {"", "unknown"}:
        return True
    if any(k in q for k in ("实时", "离线", "real-time", "offline")) and runtime_target not in {
        "",
        "unknown",
        "speed_first_unresolved",
    }:
        return True
    if any(k in q for k in ("机载", "工作站", "edge", "server")) and deployment not in {"", "unknown"}:
        return True
    if any(k in q for k in ("ply", "las", "pcd", "输出")) and output_format not in {"", "unknown"}:
        return True
    if any(k in q for k in ("语义", "semantic")) and semantic not in {"", "unknown"}:
        return True
    return False


def _extract_user_messages(conversation_context: Mapping[str, Any]) -> list[str]:
    raw = conversation_context.get("user_messages", [])
    if not isinstance(raw, list):
        return []
    return [re.sub(r"\s+", " ", str(x or "").strip()) for x in raw if str(x or "").strip()]


def _pick_hint(options: list[str], seed: str, default: str) -> str:
    rows = [re.sub(r"\s+", " ", str(x or "").strip()) for x in options if re.sub(r"\s+", " ", str(x or "").strip())]
    if not rows:
        return default
    digest = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()
    idx = int(digest[:8], 16) % len(rows)
    return rows[idx]


def _is_generic_opening_question(question: str, lang: str) -> bool:
    q = re.sub(r"\s+", " ", str(question or "").strip())
    if not q:
        return True
    low = q.lower()
    if str(lang).lower() == "en":
        generic_tokens = (
            "what is the specific issue",
            "what should i handle first",
            "what is your top priority",
            "is there anything else i can help",
        )
        return any(tok in low for tok in generic_tokens)
    generic_tokens_zh = (
        "你现在最希望我先解决的一个具体问题是什么",
        "这轮你希望我先处理什么",
        "还有什么我可以帮到你",
        "最高优先级",
    )
    return any(tok in q for tok in generic_tokens_zh)


def _is_internal_question_leak(question: str) -> bool:
    q = re.sub(r"\s+", " ", str(question or "").strip())
    if not q:
        return False
    low = q.lower()
    leak_tokens = (
        "analysis.md",
        "plan_draft.md",
        "outbox",
        "run_dir",
        "artifact",
        "patch",
        "blocked_needs_input",
        "internal prompt",
        "raw prompt",
    )
    if any(tok in low for tok in leak_tokens):
        return True
    return bool(_WAITING_INTERNAL_REQUEST_RE.search(low))


def _entry_hint_bank(lang: str, rag_hints: Mapping[str, Any] | None = None) -> dict[str, list[str]]:
    if str(lang).lower() == "en":
        base = {
            "greet_open": [
                "Hi, I'm here.",
                "Hello, I'm online and ready.",
                "Hey, I'm here with you.",
            ],
            "greet_next": [
                "What can I help you with?",
                "Tell me your target and I'll help structure it.",
                "You can share your project goal and I'll shape it into an executable plan.",
            ],
            "status_idle": [
                "There is no active task yet.",
                "I don't have an active project bound yet.",
            ],
            "status_active": [
                "I'm tracking your active task now.",
                "Your current task is still in progress on my side.",
            ],
            "intake_open": [
                "Understood.",
                "Got it.",
                "Thanks, received.",
            ],
            "intake_next": [
                "Share the project goal, input, and expected output in one sentence.",
                "Give me one concise line with target, input, and output; I'll convert it into an executable plan.",
                "Tell me what to build, what goes in, and what should come out, and I'll structure the first plan.",
            ],
            "smalltalk": [
                "I'm here and ready to help.",
                "I'm here with you. Tell me what you want to handle first.",
                "I'm online. Send your goal and I'll pick it up.",
            ],
            "blocked_no_task": [
                "I got your message. Share this round's concrete goal and I'll continue immediately.",
                "I received this. Tell me the exact goal for this round and I'll move forward now.",
            ],
        }
    else:
        base = {
            "greet_open": [
                "你好，我在。",
                "你好，我在线。",
                "你好，收到你的消息。",
            ],
            "greet_next": [
                "你直接说这轮目标，我马上接着处理。",
                "把你现在最优先的一件事告诉我，我立刻推进。",
                "你可以直接给目标和预期结果，我会整理成可执行方案。",
            ],
            "status_idle": [
                "当前还没有进行中的任务。",
                "我这边还没绑定进行中的项目。",
            ],
            "status_active": [
                "我在跟进当前任务。",
                "你这边的任务我还在持续推进。",
            ],
            "intake_open": [
                "收到。",
                "明白。",
                "已收到。",
            ],
            "intake_next": [
                "你用一句话告诉我这轮项目的目标、输入和期望输出，我先帮你整理成可执行方案。",
                "你直接给我“做什么、输入是什么、输出要什么”，我来先收拢成第一版执行方案。",
                "把这轮项目目标、输入和期望结果发我一句话版本，我先帮你立项整理。",
            ],
            "smalltalk": [
                "我在。你现在最优先要推进哪一件事？",
                "收到，我在线。你说目标，我马上开始。",
                "我在，直接发这轮目标就行。",
            ],
            "blocked_no_task": [
                "我已收到。你先补充这轮要达成的具体目标，我就继续推进。",
                "我收到你的消息了。你给我这轮明确目标，我马上继续处理。",
            ],
        }
    if isinstance(rag_hints, Mapping):
        for key, value in rag_hints.items():
            if not isinstance(value, list):
                continue
            hints = [re.sub(r"\s+", " ", str(x or "").strip()) for x in value if re.sub(r"\s+", " ", str(x or "").strip())]
            if hints:
                base[str(key)] = hints
    return base


def _compose_entry_reply(
    *,
    mode: ConversationMode,
    lang: str,
    has_active_task: bool,
    latest_user_message: str = "",
    rag_hints: Mapping[str, Any] | None = None,
) -> str:
    low_lang = str(lang).lower()
    latest = re.sub(r"\s+", " ", str(latest_user_message or "").strip())
    seed = f"{mode}|{low_lang}|{latest}"
    hints = _entry_hint_bank(low_lang, rag_hints)
    if low_lang == "en":
        if mode == "GREETING":
            open_line = _pick_hint(hints.get("greet_open", []), seed + "|o", "Hi, I'm here.")
            next_line = _pick_hint(hints.get("greet_next", []), seed + "|n", "What can I help you with?")
            return f"{open_line} {next_line}"
        if mode == "STATUS_QUERY":
            if has_active_task:
                status = _pick_hint(hints.get("status_active", []), seed + "|sa", "I'm tracking your active task now.")
                return f"{status} Share one update you want me to apply first."
            status = _pick_hint(hints.get("status_idle", []), seed + "|si", "There is no active task yet.")
            return f"{status} Tell me your goal and I will start immediately."
        if mode == "PROJECT_INTAKE":
            open_line = _pick_hint(hints.get("intake_open", []), seed + "|io", "Understood.")
            next_line = _pick_hint(
                hints.get("intake_next", []),
                seed + "|in",
                "Share the project goal, input, and expected output in one sentence.",
            )
            return f"{open_line} {next_line}"
        return _pick_hint(hints.get("smalltalk", []), seed + "|s", "I'm here and ready to help.")
    if mode == "GREETING":
        open_line = _pick_hint(hints.get("greet_open", []), seed + "|o", "你好，我在。")
        next_line = _pick_hint(hints.get("greet_next", []), seed + "|n", "你直接说这轮目标，我马上接着处理。")
        return f"{open_line}{next_line}"
    if mode == "STATUS_QUERY":
        if has_active_task:
            status = _pick_hint(hints.get("status_active", []), seed + "|sa", "我在跟进当前任务。")
            return f"{status}你告诉我这轮最想先推进的一点，我马上接着做。"
        status = _pick_hint(hints.get("status_idle", []), seed + "|si", "当前还没有进行中的任务。")
        return f"{status}你把目标发我，我马上开始。"
    if mode == "PROJECT_INTAKE":
        open_line = _pick_hint(hints.get("intake_open", []), seed + "|io", "收到。")
        next_line = _pick_hint(
            hints.get("intake_next", []),
            seed + "|in",
            "你用一句话告诉我这轮项目的目标、输入和期望输出，我先帮你整理成可执行方案。",
        )
        return f"{open_line}{next_line}"
    return _pick_hint(hints.get("smalltalk", []), seed + "|s", "我在。你可以直接说你现在想先处理哪件事。")


def _tradeoff_question_relevant(task_summary: str, known_facts: Mapping[str, Any]) -> bool:
    summary = re.sub(r"\s+", " ", str(task_summary or "").strip())
    if has_valid_task_summary(summary):
        return True
    if not isinstance(known_facts, Mapping):
        return False
    project_type = str(known_facts.get("project_type", "unknown")).strip().lower()
    return bool(project_type and project_type != "unknown")


def _stage_requirement_extraction(
    state: InternalReplyPipelineState,
    *,
    notes: Mapping[str, Any],
    lang: str,
) -> InternalReplyPipelineState:
    user_messages = _extract_user_messages(state.conversation_context)
    selected = select_best_requirement_source(user_messages) if user_messages else ""
    base_summary = re.sub(r"\s+", " ", str(state.task_summary or "").strip())
    if selected:
        selected_score = requirement_information_score(selected)
        base_score = requirement_information_score(base_summary)
        # Prefer richer recent requirement text to avoid early vague-summary bias.
        if (not base_summary) or (selected_score + 0.2 >= base_score):
            state.task_summary = selected
    state.selected_requirement_source = selected

    known_facts_map: dict[str, Any] = {}
    raw_known = notes.get("known_facts", {})
    if isinstance(raw_known, Mapping):
        for key, value in raw_known.items():
            known_facts_map[str(key)] = value
    derived = extract_known_project_facts(user_messages, state.selected_requirement_source or state.task_summary)
    for key, value in derived.items():
        prev = str(known_facts_map.get(key, "unknown"))
        if (not prev) or prev in {"unknown", "Unknown"}:
            known_facts_map[key] = value

    assumptions_map: dict[str, Any] = {}
    raw_assumptions = notes.get("assumptions", {})
    if isinstance(raw_assumptions, Mapping):
        for key, value in raw_assumptions.items():
            assumptions_map[str(key)] = value
    if not assumptions_map:
        assumptions_map = build_default_assumptions(known_facts_map)

    state.conversation_context["known_facts_map"] = known_facts_map
    state.conversation_context["assumptions_map"] = assumptions_map
    state.conversation_context["lang"] = lang
    state.known_facts = _serialize_key_values(known_facts_map)
    state.assumptions = _serialize_key_values(assumptions_map)
    return state


def _stage_project_manager_draft(
    state: InternalReplyPipelineState,
    *,
    raw_backend_state: Mapping[str, Any],
    raw_reply_text: str,
    raw_next_question: str,
    notes: Mapping[str, Any],
    lang: str,
) -> InternalReplyPipelineState:
    known_facts = state.conversation_context.get("known_facts_map", {})
    if not isinstance(known_facts, Mapping):
        known_facts = {}
    mode = str(state.conversation_mode or "").strip().upper()
    active_task_context: dict[str, Any] = {
        "task_summary": state.task_summary,
        "conversation_mode": mode,
    }
    if isinstance(known_facts, Mapping):
        active_task_context["known_facts"] = dict(known_facts)
    allow_followup = bool(notes.get("allow_project_followup", True)) and can_emit_project_followup(active_task_context)

    merged_raw = "\n".join(
        x for x in [raw_reply_text, raw_next_question, str(raw_backend_state.get("reason", ""))] if str(x).strip()
    )
    explicit_missing = raw_backend_state.get("missing_fields", [])
    if isinstance(explicit_missing, str):
        explicit_missing = [explicit_missing]
    if not isinstance(explicit_missing, list):
        explicit_missing = []
    missing_fields = [str(x).strip() for x in explicit_missing if str(x).strip()]
    for inferred in infer_missing_fields_from_text(merged_raw):
        if inferred not in missing_fields:
            missing_fields.append(inferred)
    missing_fields = _filter_missing_fields_with_known_facts(missing_fields, known_facts)
    state.missing_fields = missing_fields if allow_followup else []

    max_questions = _parse_positive_int(notes.get("max_questions", 2), default=2, min_value=1, max_value=2)
    manager_questions = [str(x).strip() for x in notes.get("manager_questions", []) if str(x).strip()]
    prefer_explicit_question = bool(notes.get("prefer_explicit_next_question", False))
    prefer_raw_reply_text = bool(notes.get("prefer_raw_reply_text", False))
    candidate_questions: list[str] = []
    explicit_question = sanitize_internal_text(raw_next_question).text.strip()
    if allow_followup and prefer_explicit_question and explicit_question and not is_generic_intake_question(explicit_question, lang):
        candidate_questions = [explicit_question]
    elif allow_followup and manager_questions:
        for q in manager_questions:
            sq = sanitize_internal_text(q).text.strip()
            if not sq or is_generic_intake_question(sq, lang):
                continue
            candidate_questions.append(sq)

    if allow_followup and not candidate_questions:
        candidate_questions = rewrite_missing_requirements(
            state.missing_fields,
            {"lang": lang, "task_summary": state.task_summary, "max_questions": max_questions},
        )

    if allow_followup and not candidate_questions:
        sanitized_q = explicit_question
        generic = {"还有什么我可以帮到你的吗？", "is there anything else i can help you with?"}
        if sanitized_q and sanitized_q.lower() not in generic and not is_generic_intake_question(sanitized_q, lang):
            candidate_questions = [sanitized_q]

    filtered_questions = [q for q in candidate_questions if not _question_already_answered(q, known_facts)]
    if filtered_questions:
        non_tradeoff = [q for q in filtered_questions if not is_generic_tradeoff_question(q)]
        if non_tradeoff:
            filtered_questions = non_tradeoff
        elif not _tradeoff_question_relevant(state.task_summary, known_facts):
            filtered_questions = []
    state.candidate_questions = _dedupe_items(filtered_questions, limit=max_questions)

    raw_state = dict(raw_backend_state)
    raw_state["missing_count"] = len(state.missing_fields)
    raw_state["has_actionable_goal"] = bool(raw_backend_state.get("has_actionable_goal", False) or state.task_summary)
    if not has_valid_task_summary(active_task_context):
        raw_state["blocked_needs_input"] = False
        raw_state["needs_input"] = False
        raw_state["missing_count"] = 0
    state.visible_state = resolve_visible_state(raw_state)
    if mode in {"GREETING", "SMALLTALK", "STATUS_QUERY", "PROJECT_INTAKE"} and state.visible_state in {
        "BLOCKED_NEEDS_INPUT",
        "WAITING_FOR_DECISION",
    }:
        state.visible_state = "UNDERSTOOD"
    raw_sanitized = sanitize_internal_text(raw_reply_text)
    if prefer_raw_reply_text and raw_sanitized.text.strip():
        state.draft_reply = raw_sanitized.text.strip()
    else:
        state.draft_reply = compose_user_reply(
            visible_state=state.visible_state,
            task_summary=state.task_summary,
            followup_questions=state.candidate_questions,
            notes={
                **dict(notes),
                "lang": lang,
                "backend_temporary_failure": bool(
                    raw_sanitized.redactions > 0
                    and state.visible_state == "BLOCKED_NEEDS_INPUT"
                    and has_valid_task_summary(active_task_context)
                ),
                "allow_internal_error_rewrite": bool(has_valid_task_summary(active_task_context)),
            },
        )
    return state


def _contains_state_contradiction(text: str) -> bool:
    low = str(text or "").lower()
    if not low:
        return False
    executing_markers = ("已开始", "执行中", "started execution", "moving on")
    blocked_markers = ("不能继续", "无法继续", "cannot continue", "can't continue")
    return any(x in low for x in executing_markers) and any(x in low for x in blocked_markers)


def _stage_consistency_review(
    state: InternalReplyPipelineState,
    *,
    notes: Mapping[str, Any],
    lang: str,
) -> InternalReplyPipelineState:
    if len(state.candidate_questions) > 2:
        state.review_flags.append("questions_trimmed_to_two")
        state.candidate_questions = state.candidate_questions[:2]
    if _contains_state_contradiction(state.draft_reply):
        state.review_flags.append("state_contradiction_rewritten")
        state.draft_reply = compose_user_reply(
            visible_state=state.visible_state,
            task_summary=state.task_summary,
            followup_questions=state.candidate_questions,
            notes={**dict(notes), "lang": lang},
        )
    if _FORBIDDEN_PUBLIC_LABEL_RE.search(state.draft_reply):
        state.review_flags.append("internal_labels_detected")
    return state


def _strip_forbidden_public_lines(text: str) -> tuple[str, int]:
    rows = str(text or "").splitlines()
    kept: list[str] = []
    redactions = 0
    for row in rows:
        line = str(row or "").strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        low = line.lower()
        if any(tok in low for tok in _FORBIDDEN_PUBLIC_TOKENS):
            redactions += 1
            continue
        if _FORBIDDEN_PUBLIC_LABEL_RE.search(line):
            redactions += 1
            continue
        if _RC_FIELD_RE.search(line):
            redactions += 1
            continue
        if _WAITING_INTERNAL_REQUEST_RE.search(low):
            redactions += 1
            continue
        kept.append(line)
    while kept and kept[0] == "":
        kept.pop(0)
    while kept and kept[-1] == "":
        kept.pop()
    return "\n".join(kept).strip(), redactions


def _stage_safety_sanitization(state: InternalReplyPipelineState, *, lang: str) -> InternalReplyPipelineState:
    sanitized = sanitize_internal_text(state.draft_reply)
    text, redactions = _strip_forbidden_public_lines(sanitized.text or state.draft_reply)
    total_redactions = int(sanitized.redactions or 0) + redactions
    if total_redactions > 0:
        state.review_flags.append("safety_redaction_applied")
    state.redactions = total_redactions
    if text:
        state.sanitized_reply = text
    else:
        state.sanitized_reply = (
            "I'm on it. I need one key decision from you to continue safely."
            if lang == "en"
            else "我已经接手了。为了稳妥继续推进，我需要你确认一个关键选择。"
        )
    return state


def _stage_final_emission(state: InternalReplyPipelineState) -> InternalReplyPipelineState:
    final = re.sub(r"\n{3,}", "\n\n", str(state.sanitized_reply or "").strip())
    if not final:
        final = str(state.draft_reply or "").strip()
    if not final:
        final = (
            "I'm on it and will keep this moving."
            if state.conversation_context.get("lang", "zh") == "en"
            else "我已接手并会继续推进。"
        )
    state.final_reply = final
    return state


def run_internal_reply_pipeline(
    *,
    raw_backend_state: Mapping[str, Any],
    task_summary: str,
    raw_reply_text: str,
    raw_next_question: str,
    notes: Mapping[str, Any] | None = None,
) -> InternalReplyPipelineState:
    note = dict(notes or {})
    lang = str(note.get("lang", "zh")).strip().lower() or "zh"
    user_messages = list(note.get("recent_user_messages", []) or [])
    latest_user_message = re.sub(r"\s+", " ", str(note.get("latest_user_message", "")).strip())
    if not latest_user_message:
        for item in reversed(user_messages):
            text = re.sub(r"\s+", " ", str(item or "").strip())
            if text:
                latest_user_message = text
                break
    if not latest_user_message:
        latest_user_message = re.sub(r"\s+", " ", str(task_summary or "").strip())
    active_state_raw = note.get("active_task_state", {})
    active_task_state: dict[str, Any] = dict(active_state_raw) if isinstance(active_state_raw, Mapping) else {}
    if re.sub(r"\s+", " ", str(task_summary or "").strip()):
        active_task_state.setdefault("task_summary", re.sub(r"\s+", " ", str(task_summary or "").strip()))
    mode = route_conversation_mode(
        user_messages,
        latest_user_message,
        active_task_state,
    )
    signal_score = compute_task_signal_score(user_messages + ([latest_user_message] if latest_user_message else []))
    has_signal = has_sufficient_task_signal(user_messages + ([latest_user_message] if latest_user_message else []))
    has_active_task = has_valid_task_summary(active_task_state)
    state = InternalReplyPipelineState(
        conversation_context={
            "user_messages": list(user_messages),
            "raw_backend_state": dict(raw_backend_state),
            "latest_user_message": latest_user_message,
            "has_active_task": has_active_task,
        },
        conversation_mode=mode,
        task_summary=re.sub(r"\s+", " ", str(task_summary or "").strip()),
        task_signal_score=float(signal_score),
        has_sufficient_task_signal=bool(has_signal),
    )
    state.conversation_context["conversation_mode"] = mode
    state.conversation_context["task_signal_score"] = float(signal_score)
    state.conversation_context["has_sufficient_task_signal"] = bool(has_signal)

    non_project_modes = {"GREETING", "SMALLTALK", "STATUS_QUERY", "PROJECT_INTAKE"}
    if mode in non_project_modes:
        prefer_raw_reply_text = bool(note.get("prefer_raw_reply_text", False))
        if mode == "STATUS_QUERY" and has_active_task:
            state.visible_state = "EXECUTING"
        else:
            state.visible_state = "UNDERSTOOD"
        raw_sanitized = sanitize_internal_text(raw_reply_text)
        if prefer_raw_reply_text and raw_sanitized.text.strip():
            state.draft_reply = raw_sanitized.text.strip()
        else:
            state.draft_reply = _compose_entry_reply(
                mode=mode,
                lang=lang,
                has_active_task=has_active_task,
                latest_user_message=latest_user_message,
                rag_hints=note.get("entry_hint_bank") if isinstance(note.get("entry_hint_bank"), Mapping) else None,
            )
        explicit_question = sanitize_internal_text(raw_next_question).text.strip()
        if mode == "PROJECT_INTAKE" and explicit_question and not is_generic_intake_question(explicit_question, lang):
            allow_tradeoff = has_valid_task_summary({"task_summary": state.task_summary, "conversation_mode": mode})
            if (not _is_generic_opening_question(explicit_question, lang)) and (
                (not is_generic_tradeoff_question(explicit_question)) or allow_tradeoff
            ):
                if not _is_internal_question_leak(explicit_question):
                    state.candidate_questions = _dedupe_items([explicit_question], limit=1)
        if state.candidate_questions:
            if mode == "PROJECT_INTAKE":
                lead = "Also, " if lang == "en" else "另外，"
                state.draft_reply = f"{state.draft_reply}\n\n{lead}{state.candidate_questions[0]}"
            else:
                state.draft_reply = f"{state.draft_reply}\n\n{state.candidate_questions[0]}"
        state = _stage_consistency_review(state, notes=note, lang=lang)
        state = _stage_safety_sanitization(state, lang=lang)
        state = _stage_final_emission(state)
        return state

    state = _stage_requirement_extraction(state, notes=note, lang=lang)
    state = _stage_project_manager_draft(
        state,
        raw_backend_state=raw_backend_state,
        raw_reply_text=raw_reply_text,
        raw_next_question=raw_next_question,
        notes={
            **note,
            "allow_project_followup": bool(has_signal),
        },
        lang=lang,
    )
    state = _stage_consistency_review(state, notes=note, lang=lang)
    state = _stage_safety_sanitization(state, lang=lang)
    state = _stage_final_emission(state)
    return state


def _pipeline_state_to_dict(state: InternalReplyPipelineState) -> dict[str, Any]:
    return {
        "conversation_context": dict(state.conversation_context),
        "conversation_mode": state.conversation_mode,
        "selected_requirement_source": state.selected_requirement_source,
        "task_summary": state.task_summary,
        "known_facts": list(state.known_facts),
        "assumptions": list(state.assumptions),
        "candidate_questions": list(state.candidate_questions),
        "draft_reply": state.draft_reply,
        "review_flags": list(state.review_flags),
        "sanitized_reply": state.sanitized_reply,
        "final_reply": state.final_reply,
        "visible_state": state.visible_state,
        "missing_fields": list(state.missing_fields),
        "redactions": int(state.redactions),
        "task_signal_score": float(state.task_signal_score),
        "has_sufficient_task_signal": bool(state.has_sufficient_task_signal),
    }


def compose_user_reply(
    visible_state: VisibleState,
    task_summary: str,
    followup_questions: list[str] | tuple[str, ...],
    notes: Mapping[str, Any] | None = None,
) -> str:
    note = notes if isinstance(notes, Mapping) else {}
    lang = str(note.get("lang", "zh")).strip().lower()
    summary = str(task_summary or "").strip()
    questions = [str(x).strip() for x in followup_questions if str(x).strip()][:2]
    questions_block = _question_block(questions, lang=lang)
    joined_q = _join_questions(questions, lang=lang)
    project_name = str(note.get("project_name", "")).strip()
    temporary_failure = bool(note.get("backend_temporary_failure", False))
    execution_direction = _execution_direction_text(note, lang)
    allow_internal_error_rewrite = bool(note.get("allow_internal_error_rewrite", True))

    if lang == "en":
        if visible_state == "DONE":
            return "This round is complete and the latest result is ready. I can give you a concise summary and next-step options."
        if visible_state == "WAITING_FOR_DECISION":
            head = "We have reached a decision checkpoint."
            if joined_q:
                return f"{head}\n\n{joined_q}"
            return f"{head}\n\nPlease confirm the next choice and I will continue immediately."
        if visible_state == "BLOCKED_NEEDS_INPUT":
            if not allow_internal_error_rewrite:
                if joined_q:
                    return f"I got your request. To continue safely, I need one quick confirmation: {joined_q}"
                return "I got your request. Share the concrete goal for this round and I will continue immediately."
            head = "I hit a temporary internal processing issue while preparing the first plan, so I will not send invalid internal output."
            if joined_q:
                return f"{head}\n\nTo keep momentum, I need two quick confirmations: {joined_q}"
            return f"{head}\n\nPlease share one or two key constraints and I will resume."
        if visible_state == "EXECUTING":
            body = "Got it. I have started execution and I am moving on the current plan."
            if joined_q:
                return f"{body}\n\nTo reduce rework, I need one quick confirmation: {joined_q}"
            return body
        if visible_state == "UNDERSTOOD":
            rows = ["Got it. I will set this up in project-manager mode and move it forward now."]
            if summary:
                rows.append(f"My current understanding: {summary}")
            if project_name:
                rows.append(f"Temporary project name: {project_name}.")
            rows.append(execution_direction)
            if questions_block:
                rows.append(f"Two points can change the technical route, so I need quick confirmation:\n{questions_block}")
            return "\n\n".join(rows)
        # NEEDS_ONE_OR_TWO_DETAILS
        head = "I understand the direction and can proceed, but I need one or two key details to avoid rework."
        if joined_q:
            return f"{head}\n\n{joined_q}"
        return f"{head}\n\nPlease share the top priority and target runtime."

    # Chinese (default)
    if visible_state == "DONE":
        return "这一轮已经完成，最新结果也准备好了。我可以马上给你一个精简总结和下一步建议。"
    if visible_state == "WAITING_FOR_DECISION":
        head = "我这边已经推进到需要你拍板的节点。"
        if joined_q:
            return f"{head}\n\n{joined_q}"
        return f"{head}\n\n你确认这个选择后，我会立刻继续推进。"
    if visible_state == "BLOCKED_NEEDS_INPUT":
        if not allow_internal_error_rewrite:
            if joined_q:
                return f"我已收到你的需求。为了稳妥继续推进，我先确认一点：{joined_q}"
            return "我已收到你的需求。你告诉我这轮具体目标，我马上继续推进。"
        head = "我这边在整理首轮方案时遇到一次内部处理异常，我先不把无效结果发给你。"
        if temporary_failure and joined_q:
            return f"{head}\n\n为了继续推进，我需要确认两个关键参数：{joined_q}"
        if joined_q:
            return f"{head}\n\n为了继续推进，我还需要确认两项信息：{joined_q}"
        return f"{head}\n\n你先补充一到两个关键参数，我马上恢复推进。"
    if visible_state == "EXECUTING":
        body = "收到，我已经开始处理，会按当前确认的信息继续推进。"
        if joined_q:
            return f"{body}\n\n为了减少返工，我还想确认一点：{joined_q}"
        return body
    if visible_state == "UNDERSTOOD":
        rows = ["收到，我先按这个方向立项并帮你推进。"]
        if summary:
            rows.append(f"目前我理解的是：{summary}")
        if project_name:
            rows.append(f"我先给你一个临时项目名：{project_name}。")
        rows.append(execution_direction)
        if questions_block:
            rows.append(f"不过有两个点会直接影响方案路线，我先确认一下：\n{questions_block}")
        return "\n\n".join(rows)
    # NEEDS_ONE_OR_TWO_DETAILS
    head = "我已经理解大方向了，接下来只差一到两个关键参数就能更稳地继续推进。"
    if joined_q:
        return f"{head}\n\n{joined_q}"
    return f"{head}\n\n你先告诉我输入形态和运行目标，我马上开工。"


def render_frontend_output(
    *,
    raw_backend_state: Mapping[str, Any],
    task_summary: str,
    raw_reply_text: str,
    raw_next_question: str,
    notes: Mapping[str, Any] | None = None,
) -> FrontendRenderResult:
    note = dict(notes or {})
    state = run_internal_reply_pipeline(
        raw_backend_state=raw_backend_state,
        task_summary=task_summary,
        raw_reply_text=raw_reply_text,
        raw_next_question=raw_next_question,
        notes=note,
    )

    return FrontendRenderResult(
        visible_state=state.visible_state,
        reply_text=state.final_reply,
        followup_questions=tuple(state.candidate_questions[:2]),
        missing_fields=tuple(state.missing_fields),
        redactions=state.redactions,
        pipeline_state=_pipeline_state_to_dict(state),
    )
