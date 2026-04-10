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
    is_capability_query,
    is_generic_tradeoff_question,
    is_project_execution_followup,
    route_conversation_mode,
)
from .frontdesk_state_machine import normalize_frontdesk_state
from .message_sanitizer import sanitize_internal_text
from .missing_info_rewriter import infer_missing_fields_from_text, rewrite_missing_requirements
from .progress_reply import (
    compose_progress_update_reply,
    is_progress_update_request,
    looks_like_progress_grounded_reply,
    normalize_progress_binding,
)
from .project_domain_profile import DOMAIN_POINTCLOUD, DOMAIN_VISUAL_NOVEL
from .project_manager_mode import (
    build_default_assumptions,
    extract_known_project_facts,
    is_generic_intake_question,
    requirement_information_score,
    select_best_requirement_source,
)
from .recovery_visibility import (
    apply_frontdesk_truth_state,
    backend_truth_details,
    render_backend_truth_text,
    render_internal_recovery_text,
    reply_truth_note_fields,
)
from .state_resolver import VISIBLE_STATES, VisibleState, resolve_visible_state

try:
    from bridge.render_adapter import to_frontend_binding as shared_state_to_frontend_binding
except Exception:
    shared_state_to_frontend_binding = None  # type: ignore[assignment]


@dataclass
class InternalReplyPipelineState:
    conversation_context: dict[str, Any] = field(default_factory=dict)
    conversation_mode: ConversationMode = "SMALLTALK"
    frontdesk_state: dict[str, Any] = field(default_factory=dict)
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
    known_facts = note.get("known_facts", {})
    if not isinstance(known_facts, Mapping):
        known_facts = {}
    project_type = str(known_facts.get("project_type", "")).strip().lower()
    assumptions = note.get("assumptions", {})
    if not isinstance(assumptions, Mapping):
        assumptions = {}
    semantic_plan = str(assumptions.get("semantic_plan", "")).strip()
    if lang == "en":
        if project_type == DOMAIN_VISUAL_NOVEL:
            return "Next I will lock the smallest runnable VN workbench path first: structured asset entry, scene ordering, and a first export target."
        if project_type != DOMAIN_POINTCLOUD:
            return "Next I will lock the smallest runnable user flow first, then keep non-critical extensions behind that main path."
        if semantic_plan == "integrate_semantic_in_v1":
            return "I will prioritize speed, land a runnable main pipeline first, and integrate semantic capability directly in V1."
        return "I will prioritize speed, land a runnable main pipeline first, and keep semantic capability as an extension path."
    if project_type == DOMAIN_VISUAL_NOVEL:
        return "接下来我会先按“本地可运行、资料录入与场景整理优先、先锁定一条导出路径”的方向整理第一版方案。"
    if project_type != DOMAIN_POINTCLOUD:
        return "接下来我会先按“先跑通最小可用主流程，再补非关键扩展”的方向整理第一版方案。"
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
    project_type = str(known_facts.get("project_type", "")).strip().lower()
    input_mode = str(known_facts.get("input_mode", "unknown"))
    runtime_target = str(known_facts.get("runtime_target", "unknown"))
    deployment = str(known_facts.get("deployment_boundary", "unknown"))
    output_format = str(known_facts.get("output_format", "unknown"))
    semantic = str(known_facts.get("semantic_integration_level", "unknown"))
    if project_type == DOMAIN_POINTCLOUD:
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
    if project_type == DOMAIN_VISUAL_NOVEL:
        if any(k in q for k in ("角色卡", "章节", "场景", "资料")) and input_mode not in {"", "unknown"}:
            return True
        if any(k in q for k in ("ren'py", "renpy", "json", "导出", "脚本")) and output_format not in {"", "unknown"}:
            return True
        if any(k in q for k in ("桌面", "浏览器", "本地", "desktop", "browser")) and runtime_target not in {"", "unknown"}:
            return True
        return False
    if any(k in q for k in ("桌面", "浏览器", "命令行", "desktop", "browser", "cli")) and runtime_target not in {"", "unknown"}:
        return True
    if any(k in q for k in ("json", "脚本", "脚手架", "导出", "输出")) and output_format not in {"", "unknown"}:
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


def _raw_project_reply_has_internal_marker(text: str) -> bool:
    low = re.sub(r"\s+", " ", str(text or "").strip()).lower()
    if not low:
        return False
    return bool(re.search(r"\bmissing(?:\s+required)?\s+[a-z0-9_]+\b", low))


def _is_low_signal_project_reply(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if not raw:
        return True
    low = raw.lower()
    generic_zh = (
        "收到，继续推进",
        "继续推进。",
        "我会继续推进",
        "我继续推进",
        "我先继续处理",
        "收到，目标很清晰",
    )
    generic_en = (
        "continue moving this forward",
        "keep moving forward",
        "goal is clear",
    )
    if any(token in raw for token in generic_zh):
        return True
    if any(token in low for token in generic_en):
        return True
    return requirement_information_score(raw) < 1.6


# Tokens indicating the reply discusses a specific project; used to catch
# model hallucination on greeting/smalltalk turns.
_PROJECT_CONTENT_LEAK_TOKENS_ZH = (
    "项目", "开发", "原型", "第一版", "设计", "实现", "功能模块",
    "需求", "方案", "架构", "部署", "框架", "代码",
)
_PROJECT_CONTENT_LEAK_TOKENS_EN = (
    "project", "prototype", "first version", "development", "implementation",
    "design", "feature module", "requirement", "architecture", "deployment",
    "framework", "codebase",
)


def _reply_leaks_project_context(reply_text: str, user_message: str) -> bool:
    """Return True when the model reply references specific project content
    that the user did not mention — indicates hallucination from stale context."""
    reply = re.sub(r"\s+", " ", str(reply_text or "")).strip()
    user = re.sub(r"\s+", " ", str(user_message or "")).strip()
    if not reply:
        return False
    reply_low = reply.lower()
    user_low = user.lower()
    leak_count = 0
    for token in _PROJECT_CONTENT_LEAK_TOKENS_ZH:
        if token in reply and token not in user:
            leak_count += 1
    for token in _PROJECT_CONTENT_LEAK_TOKENS_EN:
        if token in reply_low and token not in user_low:
            leak_count += 1
    return leak_count >= 2


def _should_fallback_from_raw_project_reply(
    *,
    raw_reply_text: str,
    sanitized_reply_text: str,
    task_summary: str,
    prefer_raw_reply_text: bool,
) -> bool:
    if prefer_raw_reply_text:
        return False
    if _raw_project_reply_has_internal_marker(raw_reply_text):
        return True
    if not sanitized_reply_text.strip():
        return True
    if has_valid_task_summary(task_summary) and _is_low_signal_project_reply(sanitized_reply_text):
        return True
    return False


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


def _capability_query_kind(text: str) -> str:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if not raw:
        return ""
    low = raw.lower()
    if any(token in raw for token in ("你是谁", "你是做什么的")) or any(token in low for token in ("who are you", "what are you")):
        return "identity"
    if any(token in raw for token in ("怎么用", "怎么开始", "怎么配合")) or any(
        token in low for token in ("how to use", "how do i use", "how should i use", "how do we start")
    ):
        return "usage"
    if any(token in raw for token in ("你能做什么", "你到底能帮我做什么", "能不能改前端", "改前端吗", "前端这块")):
        return "frontend" if _capability_mentions_frontend(raw) else "capability"
    if ("你能" in raw or "可以" in raw) and any(token in raw for token in ("做什么", "前端", "界面", "网页", "web")):
        return "frontend" if _capability_mentions_frontend(raw) else "capability"
    if any(
        token in low
        for token in (
            "what can you do",
            "what can you help with",
            "can you change the frontend",
            "can you work on the frontend",
            "can you modify the frontend",
            "can you handle frontend",
            "can you help with frontend",
        )
    ):
        return "frontend" if _capability_mentions_frontend(raw) else "capability"
    if low.startswith("can you") and any(token in low for token in ("frontend", "front-end", "ui", "web")):
        return "frontend"
    if is_capability_query(raw):
        return "frontend" if _capability_mentions_frontend(raw) else "capability"
    return ""


def _capability_mentions_frontend(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    low = raw.lower()
    return any(token in raw for token in ("前端", "界面", "网页")) or any(
        token in low for token in ("frontend", "front-end", "ui", "web")
    )


def _compose_capability_reply(*, lang: str, latest_user_message: str) -> str:
    kind = _capability_query_kind(latest_user_message)
    mentions_frontend = kind == "frontend" or _capability_mentions_frontend(latest_user_message)
    if str(lang).lower() == "en":
        if kind == "identity":
            return (
                "I'm the CTCP support entry here. I first sort whether this turn is greeting, capability, project work, or status, "
                "then keep the next step on that lane. You can tell me the goal directly or point at the path you want changed."
            )
        if kind == "usage":
            return (
                "Send me the goal or current blocker directly. If it's a project turn, I will first lock the goal, inputs, and expected result, "
                "then move into the next concrete step."
            )
        if mentions_frontend:
            return (
                "Yes. I can work on frontend behavior, bridge-safe execution handoff, and the matching regression tests. "
                "Tell me which screen or reply path you want changed first, and I will narrow the scope before editing."
            )
        return (
            "I can help clarify the goal, adjust frontend or execution behavior, add regression tests, and carry the change through verification. "
            "Tell me which part you want to change first, and I will narrow it down."
        )
    if kind == "identity":
        return (
            "我是这里的 CTCP support 入口，会先判断这轮是寒暄、能力咨询、项目需求还是进度追问，再按对应链路往下接。"
            "你现在可以直接说目标，或者告诉我想改哪条回复/流程。"
        )
    if kind == "usage":
        return (
            "你直接发目标或当前卡点就行。"
            "如果是项目类，我会先收目标、输入和想要的结果，再往下一步推进。"
        )
    if mentions_frontend:
        return (
            "可以。我能按现有 CTCP 边界处理前端表现、桥接内的执行接入和对应回归测试。"
            "你直接说想改哪一段界面或哪条回复链路，我先帮你收拢范围再动手。"
        )
    return (
        "可以。我能先帮你收拢目标，再改前端或执行链路、补回归测试，并把验证一起跑完。"
        "你直接说现在最想先改哪一块，我就按范围开始。"
    )


def _entry_hint_bank(lang: str, rag_hints: Mapping[str, Any] | None = None) -> dict[str, list[str]]:
    """Return empty lists - no preset messages, rely 100% on API generated content."""
    return {
        "greet_open": [],
        "greet_next": [],
        "status_idle": [],
        "status_active": [],
        "intake_open": [],
        "intake_next": [],
        "smalltalk": [],
        "blocked_no_task": [],
    }


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
        if mode == "CAPABILITY_QUERY":
            return _compose_capability_reply(lang=low_lang, latest_user_message=latest)
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
        if mode == "SMALLTALK" and _capability_query_kind(latest):
            return _compose_capability_reply(lang=low_lang, latest_user_message=latest)
        return _pick_hint(hints.get("smalltalk", []), seed + "|s", "I'm here and ready to help.")
    if mode == "GREETING":
        open_line = _pick_hint(hints.get("greet_open", []), seed + "|o", "你好！")
        next_line = _pick_hint(hints.get("greet_next", []), seed + "|n", "有什么需要帮忙的？")
        return f"{open_line}{next_line}"
    if mode == "CAPABILITY_QUERY":
        return _compose_capability_reply(lang=low_lang, latest_user_message=latest)
    if mode == "STATUS_QUERY":
        if has_active_task:
            status = _pick_hint(hints.get("status_active", []), seed + "|sa", "你的任务我还在跟着。")
            return f"{status}有什么想先调整的吗？"
        status = _pick_hint(hints.get("status_idle", []), seed + "|si", "目前没有在做的任务。")
        return f"{status}你说目标，我马上开始。"
    if mode == "PROJECT_INTAKE":
        open_line = _pick_hint(hints.get("intake_open", []), seed + "|io", "收到。")
        next_line = _pick_hint(
            hints.get("intake_next", []),
            seed + "|in",
            "简单说一下目标、输入和想要什么结果，我来帮你理。",
        )
        return f"{open_line}{next_line}"
    if mode == "SMALLTALK" and _capability_query_kind(latest):
        return _compose_capability_reply(lang=low_lang, latest_user_message=latest)
    return _pick_hint(hints.get("smalltalk", []), seed + "|s", "在的，有什么需要？")


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
        preserve_base_summary = bool(base_summary) and has_valid_task_summary(base_summary) and is_project_execution_followup(selected)
        # Prefer richer recent requirement text to avoid early vague-summary bias.
        if (not preserve_base_summary) and ((not base_summary) or (selected_score + 0.2 >= base_score)):
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

    merged_raw = "\n".join(x for x in [raw_reply_text, raw_next_question, str(raw_backend_state.get("reason", ""))] if str(x).strip())
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
    progress_binding = normalize_progress_binding(raw_backend_state.get("progress_binding", {}))
    internal_blocker = str(progress_binding.get("current_blocker", "")).strip() or str(raw_state.get("reason", "")).strip() or str(raw_state.get("blocking_reason", "")).strip()
    recovery_next_action = str(progress_binding.get("next_action", "")).strip() or str(raw_state.get("next_action", "")).strip()
    reply_truth = backend_truth_details(raw_state)
    reply_truth_next_action = str(reply_truth.get("next_action", "")).strip() or recovery_next_action
    state.visible_state = resolve_visible_state(raw_state)
    if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY", "STATUS_QUERY", "PROJECT_INTAKE"} and state.visible_state in {
        "BLOCKED_NEEDS_INPUT",
        "WAITING_FOR_DECISION",
    }:
        state.visible_state = "UNDERSTOOD"
    internal_gate_block = (
        str(raw_state.get("run_status", "")).lower() == "blocked"
        and not raw_state.get("blocked_needs_input")
    )
    force_state_grounded_reply = (
        state.visible_state in {"BLOCKED_NEEDS_INPUT", "WAITING_FOR_DECISION"}
        and bool(
            raw_state.get("run_status") or raw_state.get("waiting_for_decision") or raw_state.get("blocked_needs_input")
        )
    ) or internal_gate_block or bool(reply_truth.get("has_truth", False))
    raw_sanitized = sanitize_internal_text(raw_reply_text)
    raw_text = raw_sanitized.text.strip()
    truth_notes = reply_truth_note_fields(
        raw_state,
        internal_blocker=internal_blocker,
        next_action=reply_truth_next_action,
        temporary_failure=bool(
            raw_sanitized.redactions > 0
            and state.visible_state == "BLOCKED_NEEDS_INPUT"
            and has_valid_task_summary(active_task_context)
        ),
        allow_internal_error_rewrite=bool(has_valid_task_summary(active_task_context)),
    )
    if raw_text and not force_state_grounded_reply:
        if not _should_fallback_from_raw_project_reply(
            raw_reply_text=raw_reply_text,
            sanitized_reply_text=raw_text,
            task_summary=state.task_summary,
            prefer_raw_reply_text=prefer_raw_reply_text,
        ):
            # Agent-first when the raw project reply is specific and free of
            # internal markers. Low-signal placeholders should yield to the
            # frontend-reviewed PM reply.
            state.draft_reply = raw_text
        else:
            state.draft_reply = compose_user_reply(
                visible_state=state.visible_state,
                task_summary=state.task_summary,
                followup_questions=state.candidate_questions,
                notes={
                    **dict(notes),
                    "lang": lang,
                    "known_facts": dict(known_facts),
                    **truth_notes,
                },
            )
    else:
        state.draft_reply = compose_user_reply(
            visible_state=state.visible_state,
            task_summary=state.task_summary,
            followup_questions=state.candidate_questions,
            notes={
                **dict(notes),
                "lang": lang,
                "known_facts": dict(known_facts),
                **truth_notes,
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
            "I'm on it. I need one decision from you before I continue."
            if lang == "en"
            else "收到，有一个地方需要你来定一下。"
        )
    return state


def _stage_final_emission(state: InternalReplyPipelineState) -> InternalReplyPipelineState:
    final = re.sub(r"\n{3,}", "\n\n", str(state.sanitized_reply or "").strip())
    if not final:
        final = str(state.draft_reply or "").strip()
    if not final:
        final = (
            "Got it, working on it."
            if state.conversation_context.get("lang", "zh") == "en"
            else "收到，在处理了。"
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
    frontdesk_state = normalize_frontdesk_state(note.get("frontdesk_state", {}), lang)
    frontdesk_question = ""
    decision_points = frontdesk_state.get("decision_points", [])
    if isinstance(decision_points, list):
        for item in decision_points:
            if not isinstance(item, Mapping):
                continue
            question = re.sub(r"\s+", " ", str(item.get("question", "")).strip())
            if question:
                frontdesk_question = question
                break
    raw_backend = dict(raw_backend_state)
    frontdesk_name = str(frontdesk_state.get("state", "")).strip().lower()
    frontdesk_interrupt = str(frontdesk_state.get("interrupt_kind", "")).strip().lower()
    is_decision_state = frontdesk_name in {"showing_decision", "awaitdecision"}
    is_result_state = frontdesk_name in {"showing_result", "returnresult"}
    is_recoverish_state = frontdesk_name in {"showing_error", "interruptrecover"}
    if is_decision_state:
        raw_backend["waiting_for_decision"] = True
        raw_backend["decisions_count"] = max(int(raw_backend.get("decisions_count", 0) or 0), max(1, len(decision_points)))
        if frontdesk_question and not str(raw_next_question or "").strip():
            raw_next_question = frontdesk_question
    elif is_result_state:
        raw_backend["stage"] = str(raw_backend.get("stage", "")).strip() or "done"
    raw_backend, raw_next_question = apply_frontdesk_truth_state(
        raw_backend,
        frontdesk_state=frontdesk_state,
        raw_next_question=frontdesk_question or raw_next_question,
    )

    shared_binding: dict[str, Any] = {}
    if shared_state_to_frontend_binding is not None:
        try:
            shared_binding = shared_state_to_frontend_binding(
                note.get("shared_state_current", {}),
                note.get("shared_state_render", {}),
            )
        except Exception:
            shared_binding = {}
    shared_backend = shared_binding.get("backend_state", {})
    if isinstance(shared_backend, Mapping):
        raw_backend.update(dict(shared_backend))
    shared_followups = shared_binding.get("followup_questions", [])
    if not str(raw_next_question or "").strip() and isinstance(shared_followups, list) and shared_followups:
        raw_next_question = str(shared_followups[0]).strip()
    shared_summary = re.sub(r"\s+", " ", str(shared_binding.get("task_summary", "")).strip())
    if shared_summary and not re.sub(r"\s+", " ", str(task_summary or "").strip()):
        task_summary = shared_summary
        active_task_state.setdefault("task_summary", shared_summary)
    preferred_visible_state = re.sub(r"\s+", " ", str(shared_binding.get("visible_state", "")).strip()).upper()
    if preferred_visible_state and (preferred_visible_state not in VISIBLE_STATES):
        preferred_visible_state = ""

    mode = route_conversation_mode(
        user_messages,
        latest_user_message,
        active_task_state,
    )
    if is_decision_state:
        mode = "PROJECT_DECISION_REPLY"
    elif (is_result_state or is_recoverish_state) and frontdesk_interrupt in {"status_query", "result_query"}:
        mode = "STATUS_QUERY"
    signal_score = compute_task_signal_score(user_messages + ([latest_user_message] if latest_user_message else []))
    has_signal = has_sufficient_task_signal(user_messages + ([latest_user_message] if latest_user_message else []))
    has_active_task = has_valid_task_summary(active_task_state)
    state = InternalReplyPipelineState(
        conversation_context={
            "user_messages": list(user_messages),
            "raw_backend_state": dict(raw_backend),
            "latest_user_message": latest_user_message,
            "has_active_task": has_active_task,
        },
        conversation_mode=mode,
        frontdesk_state=dict(frontdesk_state),
        task_summary=re.sub(r"\s+", " ", str(task_summary or "").strip()),
        task_signal_score=float(signal_score),
        has_sufficient_task_signal=bool(has_signal),
    )
    state.conversation_context["conversation_mode"] = mode
    state.conversation_context["frontdesk_state"] = dict(frontdesk_state)
    state.conversation_context["task_signal_score"] = float(signal_score)
    state.conversation_context["has_sufficient_task_signal"] = bool(has_signal)
    if shared_binding:
        state.conversation_context["shared_state_consumed"] = True
        state.review_flags.append("shared_state_binding_consumed")
    progress_binding = normalize_progress_binding(raw_backend.get("progress_binding", {}))
    progress_requested = bool(progress_binding) and (
        mode == "STATUS_QUERY"
        or is_progress_update_request(latest_user_message)
        or ((is_recoverish_state or is_result_state) and frontdesk_interrupt in {"status_query", "result_query"})
    )

    if progress_requested:
        raw_state = dict(raw_backend)
        raw_state["has_actionable_goal"] = bool(
            raw_backend.get("has_actionable_goal", False) or state.task_summary or progress_binding.get("current_task_goal")
        )
        raw_state["first_pass_understood"] = bool(raw_backend.get("first_pass_understood", False) or progress_binding)
        if preferred_visible_state in VISIBLE_STATES:
            state.visible_state = preferred_visible_state  # type: ignore[assignment]
        else:
            state.visible_state = resolve_visible_state(raw_state)
        if state.visible_state == "NEEDS_ONE_OR_TWO_DETAILS":
            state.visible_state = "EXECUTING"
        progress_reply, progress_questions = compose_progress_update_reply(
            binding=progress_binding,
            visible_state=state.visible_state,
            lang=lang,
            fallback_question=frontdesk_question or raw_next_question,
        )
        raw_progress = sanitize_internal_text(raw_reply_text).text.strip()
        prefer_raw_progress = (
            bool(raw_progress)
            and (not _raw_project_reply_has_internal_marker(raw_progress))
            and (not _is_low_signal_project_reply(raw_progress))
            and looks_like_progress_grounded_reply(raw_progress, lang=lang)
        )
        if prefer_raw_progress:
            state.review_flags.append("progress_binding_agent_reply_preferred")
            state.draft_reply = raw_progress
            state.candidate_questions = progress_questions[:1] if progress_questions else []
        else:
            state.review_flags.append("progress_binding_consumed")
            state.candidate_questions = progress_questions
            state.draft_reply = progress_reply
        state = _stage_consistency_review(state, notes=note, lang=lang)
        state = _stage_safety_sanitization(state, lang=lang)
        state = _stage_final_emission(state)
        return state
    if is_decision_state:
        state.visible_state = "WAITING_FOR_DECISION"
        if frontdesk_question:
            state.candidate_questions = [frontdesk_question]
        state.draft_reply = compose_user_reply(
            visible_state=state.visible_state,
            task_summary=state.task_summary,
            followup_questions=state.candidate_questions,
            notes={"lang": lang},
        )
        state.review_flags.append("frontdesk_await_decision_consumed")
        state = _stage_consistency_review(state, notes=note, lang=lang)
        state = _stage_safety_sanitization(state, lang=lang)
        state = _stage_final_emission(state)
        return state

    non_project_modes = {"GREETING", "SMALLTALK", "CAPABILITY_QUERY", "STATUS_QUERY", "PROJECT_INTAKE"}
    if mode in non_project_modes:
        if mode == "STATUS_QUERY" and has_active_task:
            resolved_visible_state = preferred_visible_state if preferred_visible_state in VISIBLE_STATES else resolve_visible_state(raw_backend)
            if resolved_visible_state in {"WAITING_FOR_DECISION", "BLOCKED_NEEDS_INPUT", "DONE", "EXECUTING"}:
                state.visible_state = resolved_visible_state
            else:
                state.visible_state = "EXECUTING"
            raw_sanitized = sanitize_internal_text(raw_reply_text)
            raw_text = raw_sanitized.text.strip()
            if raw_text and not _reply_leaks_project_context(raw_text, latest_user_message):
                state.draft_reply = raw_text
            else:
                status_head = compose_user_reply(
                    visible_state=state.visible_state,
                    task_summary=state.task_summary,
                    followup_questions=[],
                    notes={"lang": lang, **reply_truth_note_fields(raw_backend)},
                )
                summary_text = re.sub(r"\s+", " ", str(state.task_summary or "")).strip()
                if summary_text:
                    if lang == "en":
                        state.draft_reply = f"{status_head}\n\nProject: {summary_text}"
                    else:
                        state.draft_reply = f"{status_head}\n\n项目：{summary_text}"
                else:
                    state.draft_reply = status_head
            state = _stage_consistency_review(state, notes=note, lang=lang)
            state = _stage_safety_sanitization(state, lang=lang)
            state = _stage_final_emission(state)
            return state
        else:
            state.visible_state = "UNDERSTOOD"
        raw_sanitized = sanitize_internal_text(raw_reply_text)
        raw_text = raw_sanitized.text.strip()
        reply_truth = backend_truth_details(raw_backend)
        if raw_text and mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"} and _reply_leaks_project_context(raw_text, latest_user_message):
            raw_text = ""
        if raw_text and not (mode == "PROJECT_INTAKE" and bool(reply_truth.get("has_truth", False))):
            state.draft_reply = raw_text
        else:
            if mode == "PROJECT_INTAKE" and bool(reply_truth.get("has_truth", False)):
                state.draft_reply = compose_user_reply(
                    visible_state="UNDERSTOOD",
                    task_summary=state.task_summary,
                    followup_questions=[],
                    notes={"lang": lang, **reply_truth_note_fields(reply_truth)},
                )
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
            if (not _is_generic_opening_question(explicit_question, lang)) and ((not is_generic_tradeoff_question(explicit_question)) or allow_tradeoff):
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
        raw_backend_state=raw_backend,
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
        "frontdesk_state": dict(state.frontdesk_state),
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


def _user_reply_hint_bank(lang: str) -> dict[str, list[str]]:
    """Return empty lists - no preset messages, rely 100% on API generated content."""
    return {
        "done": [],
        "waiting_decision": [],
        "blocked_input": [],
        "blocked_internal": [],
        "blocked_temp_fail": [],
        "executing": [],
        "understood": [],
        "needs_details": [],
    }


def _user_reply_hint_defaults(lang: str) -> dict[str, str]:
    if str(lang or "").strip().lower() == "en":
        return {
            "done": "Done. I can move to the next step whenever you are ready.",
            "waiting_decision": "I need one decision from you before I continue.",
            "blocked_input": "I need one key detail to continue this task.",
            "blocked_internal": "The backend is blocked right now, but this step does not need extra input from you.",
            "blocked_temp_fail": "There is still no customer-ready reply for this turn, so I am only syncing the confirmed state.",
            "executing": "The task is still moving, and I will sync the next visible change instead of guessing progress.",
            "understood": "Understood.",
            "needs_details": "I need one or two key details before I proceed.",
        }
    return {
        "done": "已完成当前步骤，你确认后我继续下一步。",
        "waiting_decision": "我这边需要你确认一个决策点再继续。",
        "blocked_input": "我还缺一个关键信息，补上后我就继续推进。",
        "blocked_internal": "当前后台有阻塞，但这一步不需要你额外补信息。",
        "blocked_temp_fail": "当前还没有可直接发送的正式回复，我先只同步已经确认的状态。",
        "executing": "当前还在推进中；一有新的可见变化我就马上同步你。",
        "understood": "收到。",
        "needs_details": "我还需要一到两个关键细节再往下走。",
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
    internal_blocked_reply = render_internal_recovery_text(
        lang_hint=lang,
        blocker=str(note.get("internal_blocker", "") or note.get("current_blocker", "") or note.get("blocked_reason", "")),
        next_action=str(note.get("recovery_next_action", "") or note.get("next_action", "") or note.get("recovery_hint", "")),
    )
    reply_truth = backend_truth_details(note)
    if bool(reply_truth.get("has_truth", False)):
        truth_status = str(reply_truth.get("status", ""))
        if truth_status in {
            "backend_unavailable",
            "backend_deferred",
            "backend_failed",
            "backend_blocked",
            "low_confidence_fallback",
        }:
            return render_backend_truth_text(
                lang_hint=lang,
                status=truth_status,
                reason=str(reply_truth.get("reason", "")),
                next_action=str(reply_truth.get("next_action", "")),
                source_confidence=str(reply_truth.get("source_confidence", "")),
                current_phase=str(reply_truth.get("current_phase", "")),
                last_confirmed_items=reply_truth.get("last_confirmed_items", []),
            )

    bank = _user_reply_hint_bank(lang)
    defaults = _user_reply_hint_defaults(lang)
    seed = f"{visible_state}|{lang}|{summary}"

    if visible_state == "DONE":
        return _pick_hint(bank["done"], seed, defaults["done"])
    if visible_state == "WAITING_FOR_DECISION":
        head = _pick_hint(bank["waiting_decision"], seed, defaults["waiting_decision"])
        if joined_q:
            return f"{head}\n\n{joined_q}"
        return head
    if visible_state == "BLOCKED_NEEDS_INPUT":
        if not allow_internal_error_rewrite:
            head = _pick_hint(bank["blocked_input"], seed, defaults["blocked_input"])
            if joined_q:
                return f"{head}\n\n{joined_q}"
            return head
        if temporary_failure:
            head = _pick_hint(bank["blocked_temp_fail"], seed, defaults["blocked_temp_fail"])
        elif (not joined_q) and (
            str(note.get("internal_blocker", "")).strip()
            or str(note.get("current_blocker", "")).strip()
            or str(note.get("blocked_reason", "")).strip()
            or str(note.get("recovery_next_action", "")).strip()
            or str(note.get("next_action", "")).strip()
            or str(note.get("recovery_hint", "")).strip()
        ):
            return internal_blocked_reply
        else:
            head = _pick_hint(bank["blocked_internal"], seed, defaults["blocked_internal"])
        if joined_q:
            return f"{head}\n\n{joined_q}"
        return head
    if visible_state == "EXECUTING":
        body = _pick_hint(bank["executing"], seed, defaults["executing"])
        if joined_q:
            return f"{body}\n\n{joined_q}"
        return body
    if visible_state == "UNDERSTOOD":
        head = _pick_hint(bank["understood"], seed, defaults["understood"])
        rows = [head]
        if summary:
            if lang == "en":
                rows.append(f"My current understanding: {summary}")
            else:
                rows.append(f"我理解的是：{summary}")
        if project_name:
            if lang == "en":
                rows.append(f"Temporary project name: {project_name}.")
            else:
                rows.append(f"临时项目名：{project_name}。")
        rows.append(execution_direction)
        if questions_block:
            if lang == "en":
                rows.append(f"A couple things that affect the approach:\n{questions_block}")
            else:
                rows.append(f"有两个点会影响方案方向，先确认一下：\n{questions_block}")
        return "\n\n".join(rows)
    # NEEDS_ONE_OR_TWO_DETAILS
    head = _pick_hint(bank["needs_details"], seed, defaults["needs_details"])
    if joined_q:
        return f"{head}\n\n{joined_q}"
    return head


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
