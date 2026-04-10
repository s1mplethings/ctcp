from __future__ import annotations

from difflib import SequenceMatcher
import hashlib
import re
from typing import Any, Literal, Mapping

from .recovery_visibility import (
    context_internal_recovery_details,
    context_reply_truth_details,
    context_truth_reply,
    render_internal_recovery_text,
)
from .support_context_view import (
    artifact_labels,
    current_snapshot,
    decision_prompt,
    delivery_summary,
    has_error_truth,
    has_result_truth,
    render_snapshot,
)

ReplyIntent = Literal[
    "progress_update",
    "ask_decision",
    "ask_missing_input",
    "deliver_result",
    "explain_error",
    "guide_recovery",
    "acknowledge_user",
]

_INTERNAL_LOG_TOKENS = (
    "traceback",
    "stack trace",
    "run_dir",
    "logs/",
    "logs\\",
    "stdout",
    "stderr",
    "exception:",
    "failure_bundle",
)

_MECHANICAL_PROGRESS_ZH = (
    "正在处理中",
    "继续处理中",
    "处理中，请稍候",
    "收到，继续推进",
    "好的，我在处理",
)
_MECHANICAL_PROGRESS_EN = (
    "processing",
    "working on it",
    "still in progress",
    "please wait",
)

_DECISION_ASK_HINTS_ZH = ("请确认", "请决定", "需要你拍板", "你更倾向", "你选")
_DECISION_ASK_HINTS_EN = ("please decide", "please confirm", "which option", "what do you prefer")
_ARTIFACT_HINTS = ("artifact", "产出", "文件", ".zip", ".md", ".json", ".png", ".jpg", ".jpeg", ".webp")
_ERROR_LEAK_HINTS = ("traceback", "stack", "exception", "command failed", "stderr", "stdout")
_INTENT_ORDER: tuple[ReplyIntent, ...] = (
    "progress_update",
    "ask_decision",
    "ask_missing_input",
    "deliver_result",
    "explain_error",
    "guide_recovery",
    "acknowledge_user",
)
_INTENT_DEDUPE_THRESHOLD: dict[ReplyIntent, float] = {
    "progress_update": 0.72,
    "ask_decision": 0.9,
    "ask_missing_input": 0.88,
    "deliver_result": 0.84,
    "explain_error": 0.9,
    "guide_recovery": 0.88,
    "acknowledge_user": 0.93,
}
_INTENT_WINDOW: dict[ReplyIntent, int] = {
    "progress_update": 6,
    "ask_decision": 4,
    "ask_missing_input": 4,
    "deliver_result": 4,
    "explain_error": 4,
    "guide_recovery": 4,
    "acknowledge_user": 3,
}
_PROGRESS_SYNONYM_REPLACEMENTS_ZH: tuple[tuple[str, str], ...] = (
    (r"(继续推进|继续处理|继续往下|继续跟进|往下推进|持续推进)", "推进中"),
    (r"(当前|目前|现在)", "当前"),
    (r"(还在|仍在)", "在"),
    (r"(处理中|处理当中|执行中)", "处理中"),
    (r"(同步一下进展|进展同步|状态同步)", "进展同步"),
    (r"(马上|第一时间|尽快)", "很快"),
)
_PROGRESS_SYNONYM_REPLACEMENTS_EN: tuple[tuple[str, str], ...] = (
    (r"(still working|currently working|continuing to work|keep working)", "working"),
    (r"(progress update|quick progress sync|status update)", "progress"),
    (r"(right away|as soon as possible|immediately)", "soon"),
    (r"(moving forward|keep pushing|continuing)", "continuing"),
)
_FILLER_RE = re.compile(
    r"(这边|我这边|我先|我会|然后|一下|哈|呀|呢|吧|嗯|ok|okay|well|just|currently|right now)",
    re.IGNORECASE,
)


def _public_delivery_result_text(*, delivery: Mapping[str, str], lang_hint: str) -> str:
    use_en = _norm(lang_hint).lower().startswith("en")
    entry = _norm(delivery.get("startup_entrypoint", ""))
    readme = _norm(delivery.get("startup_readme", "")) or "README.md"
    entry_name = entry.replace("\\", "/").rsplit("/", 1)[-1] if entry else "README 里的启动入口"
    if use_en:
        return (
            "The project is packaged and ready to review.\n\n"
            "Start with the final screenshot, then open the zip package.\n\n"
            f"The zip includes {readme}, the startup entry `{entry_name}`, and the main source code. "
            f"Use the README run instructions first; this is delivered as a runnable project package."
        )
    return (
        "项目已经整理好，可以直接查看和运行。\n\n"
        "你先看成品截图确认界面效果，再打开 zip 包看完整代码。\n\n"
        f"zip 里包含 {readme}、启动入口 `{entry_name}` 和主要代码；运行方式先按 README 说明执行。当前按可运行项目包交付。"
    )


def _norm(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}




def infer_reply_intent(
    *,
    conversation_mode: str = "",
    project_context: Mapping[str, Any] | None = None,
    next_question: str = "",
    provider_status: str = "",
) -> ReplyIntent:
    mode = _norm(conversation_mode).upper()
    render = render_snapshot(project_context)
    current = current_snapshot(project_context)
    visible_state = _norm(render.get("visible_state", "")).upper()
    authoritative_stage = _norm(current.get("authoritative_stage", "")).upper()
    pending_prompt = decision_prompt(project_context)
    provider_low = _norm(provider_status).lower()
    error_truth = has_error_truth(project_context)
    result_truth = has_result_truth(project_context)
    recovery_details = context_internal_recovery_details(project_context)
    reply_truth = context_reply_truth_details(project_context)
    internal_recovery_truth = bool(recovery_details.get("has_internal_recovery", False))

    if visible_state == "WAITING_FOR_DECISION" or authoritative_stage == "WAIT_USER_DECISION" or pending_prompt:
        return "ask_decision"
    if result_truth and not error_truth:
        return "deliver_result"
    if bool(reply_truth.get("has_truth", False)):
        truth_status = str(reply_truth.get("status", ""))
        if truth_status in {"backend_unavailable", "backend_failed"}:
            return "explain_error"
        if truth_status in {"backend_deferred", "backend_blocked", "low_confidence_fallback"}:
            return "guide_recovery"
    if provider_low in {"exec_failed", "failed", "error"} or error_truth:
        return "explain_error"
    if internal_recovery_truth:
        return "guide_recovery"
    if mode in {"PROJECT_INTAKE", "PROJECT_DETAIL"} and _norm(next_question):
        return "ask_missing_input"
    if mode in {"STATUS_QUERY", "PROJECT_DETAIL"} or visible_state in {"EXECUTING", "SHOWING_PROGRESS"}:
        return "progress_update"
    return "acknowledge_user"


def render_fallback_reply(
    *,
    intent: ReplyIntent,
    lang_hint: str = "zh",
    project_context: Mapping[str, Any] | None = None,
    next_question: str = "",
    previous_reply_text: str = "",
) -> dict[str, str]:
    use_en = _norm(lang_hint).lower().startswith("en")
    render = render_snapshot(project_context)
    progress = _norm(render.get("progress_summary", ""))
    pending_question = decision_prompt(project_context) or _norm(next_question)
    artifacts = artifact_labels(project_context)
    visible_state = _norm(render.get("visible_state", "")).upper()
    delivery = delivery_summary(project_context)

    if use_en:
        truth_text = context_truth_reply(project_context, lang_hint=lang_hint)
        if intent == "progress_update":
            if progress:
                text = f"Quick progress sync: I am currently handling this step: {progress}. I will update you as soon as something visible changes."
            else:
                text = "Quick progress sync: there is no new visible backend milestone yet. I will update you as soon as there is a confirmed change."
            if _norm(previous_reply_text) == _norm(text):
                text = "No visible milestone changed yet. I will wait for the next concrete backend update before claiming progress."
            return {"reply_text": text, "next_question": ""}
        if intent == "ask_decision":
            question = pending_question or "Which option should I take for this step?"
            if not question.endswith("?"):
                question = f"{question}?"
            text = f"I need one decision from you before I continue: {question}"
            return {"reply_text": text, "next_question": question}
        if intent == "ask_missing_input":
            question = _norm(next_question) or "What is the one most important requirement you want me to lock first?"
            if not question.endswith("?"):
                question = f"{question}?"
            return {"reply_text": f"I am missing one key detail to continue: {question}", "next_question": question}
        if intent == "deliver_result":
            if any(delivery.values()):
                return {"reply_text": _public_delivery_result_text(delivery=delivery, lang_hint=lang_hint), "next_question": ""}
            if artifacts:
                return {"reply_text": _public_delivery_result_text(delivery=delivery, lang_hint=lang_hint), "next_question": ""}
            return {"reply_text": "The result is ready. I can walk you through what was produced and continue with your next preference.", "next_question": ""}
        if intent in {"explain_error", "guide_recovery"}:
            if truth_text:
                return {"reply_text": truth_text, "next_question": ""}
            recovery_details = context_internal_recovery_details(project_context)
            if recovery_details.get("has_internal_recovery", False):
                return {
                    "reply_text": render_internal_recovery_text(
                        lang_hint=lang_hint,
                        blocker=str(recovery_details.get("blocker", "")),
                        next_action=str(recovery_details.get("next_action", "")),
                        retry_count=int(recovery_details.get("retry_count", 0) or 0),
                        max_retries=int(recovery_details.get("max_retries", 0) or 0),
                        recovery_action=str(recovery_details.get("recovery_action", "")),
                    ),
                    "next_question": "",
                }
            return {
                "reply_text": "This round did not produce a customer-ready reply. I can retry from the current step or wait for a clearer backend state.",
                "next_question": "Do you prefer a direct retry or a narrower fallback?",
            }
        return {"reply_text": "Understood. There is no new confirmed backend state to report yet.", "next_question": ""}

    truth_text = context_truth_reply(project_context, lang_hint=lang_hint)
    if intent == "progress_update":
        if progress:
            text = f"同步一下进展：我现在在处理这一步：{progress}。有可见变化我会第一时间告诉你。"
        else:
            text = "同步一下进展：当前还没有新的可见后端里程碑；一旦有确认过的变化我会马上同步你。"
        if _norm(previous_reply_text) == _norm(text):
            text = "当前还没有新的可见里程碑；等后端给出新的实质变化后我再同步你。"
        return {"reply_text": text, "next_question": ""}
    if intent == "ask_decision":
        question = pending_question or "这一步你更希望我优先走哪种方案？"
        if not re.search(r"[?？]$", question):
            question = f"{question}？"
        text = f"现在这一步需要你先拍一个板：{question} 你可以直接回复选项或偏好。"
        return {"reply_text": text, "next_question": question}
    if intent == "ask_missing_input":
        question = _norm(next_question) or "为了继续推进，你现在最希望我先锁定哪个关键要求？"
        if not re.search(r"[?？]$", question):
            question = f"{question}？"
        return {"reply_text": f"我还缺一个关键信息才能继续：{question}", "next_question": question}
    if intent == "deliver_result":
        if any(delivery.values()):
            return {"reply_text": _public_delivery_result_text(delivery=delivery, lang_hint=lang_hint), "next_question": ""}
        if artifacts:
            return {"reply_text": _public_delivery_result_text(delivery=delivery, lang_hint=lang_hint), "next_question": ""}
        if visible_state == "DONE":
            return {"reply_text": _public_delivery_result_text(delivery=delivery, lang_hint=lang_hint), "next_question": ""}
        return {"reply_text": "项目结果已经整理好；我会先给你看成品截图，再给 zip 包和 README 运行说明。", "next_question": ""}
    if intent in {"explain_error", "guide_recovery"}:
        if truth_text:
            return {"reply_text": truth_text, "next_question": ""}
        recovery_details = context_internal_recovery_details(project_context)
        if recovery_details.get("has_internal_recovery", False):
            return {
                "reply_text": render_internal_recovery_text(
                    lang_hint=lang_hint,
                    blocker=str(recovery_details.get("blocker", "")),
                    next_action=str(recovery_details.get("next_action", "")),
                    retry_count=int(recovery_details.get("retry_count", 0) or 0),
                    max_retries=int(recovery_details.get("max_retries", 0) or 0),
                    recovery_action=str(recovery_details.get("recovery_action", "")),
                ),
                "next_question": "",
            }
        return {
            "reply_text": "这轮还没有形成可直接发送的正式回复。你可以让我直接重试，或者等后端给出更明确的状态。",
            "next_question": "你希望我现在直接重试，还是先走简化路径？",
        }
    return {"reply_text": "收到。这轮我先按真实状态同步，不虚构新的进展。", "next_question": ""}


def _contains_internal_leak(text: str) -> bool:
    low = _norm(text).lower()
    if not low:
        return False
    return any(token in low for token in _INTERNAL_LOG_TOKENS)


def _looks_mechanical(text: str, *, intent: ReplyIntent) -> bool:
    raw = _norm(text)
    low = raw.lower()
    if not raw:
        return True
    if intent == "progress_update":
        if any(marker in raw for marker in _MECHANICAL_PROGRESS_ZH):
            return True
        if any(marker in low for marker in _MECHANICAL_PROGRESS_EN):
            return True
    return False


def _semantic_fingerprint(text: str) -> str:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", "", _norm(text).lower())
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def default_reply_dedupe_memory(*, max_entries: int = 48) -> dict[str, Any]:
    by_intent: dict[str, list[dict[str, Any]]] = {}
    for intent in _INTENT_ORDER:
        by_intent[intent] = []
    return {
        "schema_version": "ctcp-reply-dedupe-memory-v1",
        "turn_index": 0,
        "max_entries": max(12, min(200, int(max_entries or 48))),
        "by_intent": by_intent,
    }


def normalize_reply_dedupe_memory(raw: Mapping[str, Any] | None, *, max_entries: int = 48) -> dict[str, Any]:
    out = default_reply_dedupe_memory(max_entries=max_entries)
    if not isinstance(raw, Mapping):
        return out
    by_intent = raw.get("by_intent", {})
    if not isinstance(by_intent, Mapping):
        by_intent = {}
    cap = max(12, min(200, int(raw.get("max_entries", max_entries) or max_entries)))
    out["max_entries"] = cap
    out["turn_index"] = int(raw.get("turn_index", 0) or 0)
    normalized: dict[str, list[dict[str, Any]]] = {}
    for intent in _INTENT_ORDER:
        rows = by_intent.get(intent, [])
        if not isinstance(rows, list):
            rows = []
        mapped: list[dict[str, Any]] = []
        for item in rows[-cap:]:
            if not isinstance(item, Mapping):
                continue
            mapped.append(
                {
                    "intent": _norm(item.get("intent", intent)).lower() or intent,
                    "template_id": _norm(item.get("template_id", ""))[:80],
                    "normalized_text": _norm(item.get("normalized_text", ""))[:800],
                    "rendered_text": _norm(item.get("rendered_text", ""))[:1200],
                    "timestamp": _norm(item.get("timestamp", ""))[:40],
                    "turn_id": int(item.get("turn_id", 0) or 0),
                    "provider_mode": _norm(item.get("provider_mode", ""))[:32],
                    "source_kind": _norm(item.get("source_kind", ""))[:24],
                    "sent": bool(item.get("sent", True)),
                    "context_signature": _norm(item.get("context_signature", ""))[:120],
                    "semantic_fingerprint": _norm(item.get("semantic_fingerprint", ""))[:80],
                }
            )
        normalized[intent] = mapped
    out["by_intent"] = normalized
    return out


def _semantic_normalize(text: str, *, intent: ReplyIntent) -> str:
    raw = _norm(text).lower()
    if not raw:
        return ""
    raw = _FILLER_RE.sub(" ", raw)
    if intent == "progress_update":
        for pattern, repl in _PROGRESS_SYNONYM_REPLACEMENTS_ZH:
            raw = re.sub(pattern, repl, raw, flags=re.IGNORECASE)
        for pattern, repl in _PROGRESS_SYNONYM_REPLACEMENTS_EN:
            raw = re.sub(pattern, repl, raw, flags=re.IGNORECASE)
    raw = re.sub(r"[，。！？!?;；:：,.\-_/\\()（）\[\]{}\"'`~]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def _token_jaccard(a: str, b: str) -> float:
    aa = {item for item in a.split(" ") if item}
    bb = {item for item in b.split(" ") if item}
    if not aa or not bb:
        return 0.0
    inter = len(aa & bb)
    union = len(aa | bb)
    if union <= 0:
        return 0.0
    return inter / float(union)


def _char_ngram_jaccard(a: str, b: str, *, n: int = 2) -> float:
    aa = re.sub(r"\s+", "", a)
    bb = re.sub(r"\s+", "", b)
    if len(aa) < n or len(bb) < n:
        return 0.0
    sa = {aa[i : i + n] for i in range(0, len(aa) - n + 1)}
    sb = {bb[i : i + n] for i in range(0, len(bb) - n + 1)}
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def _semantic_similarity(a: str, b: str) -> float:
    aa = _norm(a).lower()
    bb = _norm(b).lower()
    if not aa or not bb:
        return 0.0
    seq = SequenceMatcher(None, aa, bb).ratio()
    jac = _token_jaccard(aa, bb)
    cjac = _char_ngram_jaccard(aa, bb, n=2)
    return max(seq, jac, cjac)


def _progress_context_signature(project_context: Mapping[str, Any] | None) -> str:
    source = _as_mapping(project_context)
    render = render_snapshot(source)
    current = current_snapshot(source)
    runtime = _as_mapping(source.get("runtime_state", {}))
    status = _as_mapping(source.get("status", {}))
    artifacts = artifact_labels(source)
    payload = {
        "visible_state": _norm(render.get("visible_state", "")).upper(),
        "progress": _norm(render.get("progress_summary", "")),
        "phase": _norm(current.get("authoritative_stage", "") or runtime.get("phase", "")).upper(),
        "blocker": _norm(current.get("current_blocker", "") or runtime.get("blocking_reason", "") or status.get("blocking_reason", "")),
        "next_action": _norm(current.get("next_action", "") or runtime.get("next_action", "")),
        "decision_prompt": _norm(decision_prompt(source)),
        "artifact_count": len(artifacts),
        "run_status": _norm(runtime.get("run_status", "") or status.get("run_status", "")).lower(),
    }
    raw = "|".join(f"{k}={payload[k]}" for k in sorted(payload.keys()))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _decision_context_signature(project_context: Mapping[str, Any] | None, question: str) -> str:
    source = _as_mapping(project_context)
    prompt = _norm(question) or decision_prompt(source)
    return _semantic_fingerprint(prompt)


def _error_context_signature(project_context: Mapping[str, Any] | None) -> str:
    source = _as_mapping(project_context)
    runtime = _as_mapping(source.get("runtime_state", {}))
    status = _as_mapping(source.get("status", {}))
    error = _as_mapping(runtime.get("error", {}))
    gate = _as_mapping(status.get("gate", {}))
    base = "|".join(
        [
            _norm(error.get("code", "")),
            _norm(error.get("message", "")),
            _norm(gate.get("reason", "")),
            _norm(runtime.get("blocking_reason", "")),
            _norm(runtime.get("run_status", "") or status.get("run_status", "")),
        ]
    )
    return _semantic_fingerprint(base)


def _result_context_signature(project_context: Mapping[str, Any] | None) -> str:
    source = _as_mapping(project_context)
    artifacts = artifact_labels(source)
    if not artifacts:
        return ""
    return _semantic_fingerprint("|".join(sorted(artifacts)))


def _template_id_for(
    *,
    intent: ReplyIntent,
    project_context: Mapping[str, Any] | None,
    text: str,
    question: str,
) -> str:
    if intent == "progress_update":
        sig = _progress_context_signature(project_context)[:8]
        return f"progress_update:status:{sig}"
    if intent == "ask_decision":
        decision_sig = _decision_context_signature(project_context, question)[:10]
        return f"ask_decision:question:{decision_sig}"
    if intent == "ask_missing_input":
        qsig = _semantic_fingerprint(question or text)[:10]
        return f"ask_missing_input:gap:{qsig}"
    if intent == "deliver_result":
        rsig = _result_context_signature(project_context)[:10]
        return f"deliver_result:artifact:{rsig or 'none'}"
    if intent in {"explain_error", "guide_recovery"}:
        esig = _error_context_signature(project_context)[:10]
        return f"{intent}:error:{esig or 'none'}"
    return f"acknowledge_user:general:{_semantic_fingerprint(text)[:10]}"


def _downgrade_text(
    *,
    intent: ReplyIntent,
    lang_hint: str,
    project_context: Mapping[str, Any] | None,
    next_question: str,
    previous_reply_text: str,
) -> tuple[str, str]:
    use_en = _norm(lang_hint).lower().startswith("en")
    question = _norm(next_question)
    truth_text = context_truth_reply(project_context, lang_hint=lang_hint)
    if truth_text:
        return truth_text, ""
    if intent == "progress_update":
        if use_en:
            text = "No visible update yet. I will wait for the next confirmed backend change."
        else:
            text = "暂无新的可见变化；等后端给出下一条确认状态后我再同步。"
        return text, ""
    if intent == "ask_decision":
        prompt = decision_prompt(project_context) or question
        if use_en:
            short = f"I still need your decision to continue: {prompt or 'Which option should I take?'}"
            return short, prompt if prompt.endswith("?") else (f"{prompt}?" if prompt else "Which option should I take?")
        short = f"我还需要你拍板后才能继续：{prompt or '这一步你更希望我走哪种方案？'}"
        if prompt and not re.search(r"[?？]$", prompt):
            prompt = f"{prompt}？"
        return short, prompt
    if intent == "deliver_result":
        artifacts = artifact_labels(project_context)
        if artifacts:
            if use_en:
                return _public_delivery_result_text(delivery=delivery_summary(project_context), lang_hint=lang_hint), ""
            return _public_delivery_result_text(delivery=delivery_summary(project_context), lang_hint=lang_hint), ""
        if use_en:
            return _public_delivery_result_text(delivery=delivery_summary(project_context), lang_hint=lang_hint), ""
        return _public_delivery_result_text(delivery=delivery_summary(project_context), lang_hint=lang_hint), ""
    if intent in {"explain_error", "guide_recovery"}:
        if use_en:
            return "Issue state is unchanged. There is still no clearer backend result than before.", "Retry now or wait for a clearer backend result?"
        return "问题状态暂时未变；目前还没有比刚才更清楚的后端结果。", "你要我现在直接重试，还是等更明确的后端结果？"
    if use_en:
        return "Acknowledged. There is no new confirmed state yet.", ""
    return "收到。目前还没有新的确认状态。", ""


def _select_context_signature(intent: ReplyIntent, project_context: Mapping[str, Any] | None, question: str) -> str:
    if intent == "progress_update":
        return _progress_context_signature(project_context)
    if intent == "ask_decision":
        return _decision_context_signature(project_context, question)
    if intent == "deliver_result":
        return _result_context_signature(project_context)
    if intent in {"explain_error", "guide_recovery"}:
        return _error_context_signature(project_context)
    return ""


def _append_memory_entry(
    *,
    memory: dict[str, Any],
    intent: ReplyIntent,
    template_id: str,
    normalized_text: str,
    rendered_text: str,
    timestamp: str,
    provider_mode: str,
    source_kind: str,
    sent: bool,
    context_signature: str,
) -> dict[str, Any]:
    by_intent = memory.get("by_intent", {})
    if not isinstance(by_intent, dict):
        by_intent = {}
        memory["by_intent"] = by_intent
    rows = by_intent.get(intent, [])
    if not isinstance(rows, list):
        rows = []
    turn_id = int(memory.get("turn_index", 0) or 0) + 1
    memory["turn_index"] = turn_id
    row = {
        "intent": intent,
        "template_id": template_id,
        "normalized_text": normalized_text,
        "rendered_text": _norm(rendered_text),
        "timestamp": _norm(timestamp),
        "turn_id": turn_id,
        "provider_mode": _norm(provider_mode),
        "source_kind": _norm(source_kind),
        "sent": bool(sent),
        "context_signature": _norm(context_signature),
        "semantic_fingerprint": _semantic_fingerprint(normalized_text),
    }
    rows.append(row)
    cap = max(12, min(200, int(memory.get("max_entries", 48) or 48)))
    by_intent[intent] = rows[-cap:]
    return row


def _question_is_explicit(text: str) -> bool:
    raw = _norm(text)
    low = raw.lower()
    if not raw:
        return False
    if re.search(r"[?？]", raw):
        return True
    zh_question_markers = ("还是", "哪个", "哪种", "是否", "要不要", "吗", "呢")
    en_question_markers = ("which", "what", "whether", "do you", "would you", "prefer")
    if any(marker in raw for marker in zh_question_markers):
        return True
    if any(marker in low for marker in en_question_markers):
        return True
    return False


def _append_artifact_hint(text: str, artifacts: list[str], *, lang_hint: str) -> str:
    raw = _norm(text)
    if not artifacts:
        return raw
    low = raw.lower()
    if any(marker in raw for marker in _ARTIFACT_HINTS) or any(marker in low for marker in _ARTIFACT_HINTS):
        return raw
    use_en = _norm(lang_hint).lower().startswith("en")
    artifact_line = ", ".join(artifacts[:3])
    if use_en:
        note = f"Produced artifacts: {artifact_line}."
    else:
        note = f"本轮已产出文件：{artifact_line}。"
    return note if not raw else f"{raw}\n\n{note}"


def _policy_delivery_result_text(text: str, project_context: Mapping[str, Any] | None, *, lang_hint: str) -> tuple[str, str]:
    delivery = delivery_summary(project_context)
    if any(delivery.values()):
        return _public_delivery_result_text(delivery=delivery, lang_hint=lang_hint), "delivery_result_humanized"
    artifacts = artifact_labels(project_context)
    if artifacts:
        updated = _append_artifact_hint(text, artifacts, lang_hint=lang_hint)
        if updated != text:
            return updated, "artifact_hint_added"
    return text, ""


def enforce_reply_policy(
    *,
    reply_text: str,
    next_question: str,
    conversation_mode: str = "",
    lang_hint: str = "",
    project_context: Mapping[str, Any] | None = None,
    provider_status: str = "",
    previous_reply_text: str = "",
    forced_intent: str = "",
    reply_memory: Mapping[str, Any] | None = None,
    now_ts: str = "",
    provider_mode: str = "",
    source_kind: str = "",
    allow_suppress: bool = False,
) -> dict[str, Any]:
    intent: ReplyIntent
    if forced_intent in {
        "progress_update",
        "ask_decision",
        "ask_missing_input",
        "deliver_result",
        "explain_error",
        "guide_recovery",
        "acknowledge_user",
    }:
        intent = forced_intent  # type: ignore[assignment]
    else:
        intent = infer_reply_intent(
            conversation_mode=conversation_mode,
            project_context=project_context,
            next_question=next_question,
            provider_status=provider_status,
        )
    reasons: list[str] = []
    text = _norm(reply_text)
    question = _norm(next_question)
    fallback_used = False
    dedupe_action = "send"
    suppress = False
    similarity_max = 0.0

    if not text:
        reasons.append("empty_reply")
    if _contains_internal_leak(text):
        reasons.append("internal_leak")
    if _looks_mechanical(text, intent=intent):
        reasons.append("mechanical_reply")

    if reasons:
        fallback = render_fallback_reply(
            intent=("explain_error" if "internal_leak" in reasons else intent),
            lang_hint=lang_hint,
            project_context=project_context,
            next_question=question,
            previous_reply_text=previous_reply_text,
        )
        text = _norm(fallback.get("reply_text", ""))
        question = _norm(fallback.get("next_question", ""))
        fallback_used = True

    if intent == "ask_decision":
        pending_prompt = decision_prompt(project_context) or question
        if (not question) and pending_prompt:
            question = pending_prompt
            reasons.append("decision_prompt_promoted")
        merged = f"{text} {question}".strip()
        if not _question_is_explicit(merged):
            fallback = render_fallback_reply(
                intent="ask_decision",
                lang_hint=lang_hint,
                project_context=project_context,
                next_question=question or pending_prompt,
                previous_reply_text=previous_reply_text,
            )
            text = _norm(fallback.get("reply_text", ""))
            question = _norm(fallback.get("next_question", ""))
            fallback_used = True
            reasons.append("decision_not_explicit")

    if intent == "deliver_result":
        text, reason = _policy_delivery_result_text(text, project_context, lang_hint=lang_hint)
        if reason:
            reasons.append(reason)

    if intent in {"explain_error", "guide_recovery"}:
        low = text.lower()
        if any(token in low for token in _ERROR_LEAK_HINTS):
            fallback = render_fallback_reply(
                intent="guide_recovery",
                lang_hint=lang_hint,
                project_context=project_context,
                next_question=question,
                previous_reply_text=previous_reply_text,
            )
            text = _norm(fallback.get("reply_text", ""))
            question = _norm(fallback.get("next_question", ""))
            fallback_used = True
            reasons.append("error_humanized")

    if previous_reply_text:
        prev_fp = _semantic_fingerprint(previous_reply_text)
        current_fp = _semantic_fingerprint(text)
        if prev_fp and current_fp and prev_fp == current_fp:
            fallback = render_fallback_reply(
                intent=intent,
                lang_hint=lang_hint,
                project_context=project_context,
                next_question=question,
                previous_reply_text=previous_reply_text,
            )
            text = _norm(fallback.get("reply_text", "")) or text
            question = _norm(fallback.get("next_question", "")) or question
            fallback_used = True
            reasons.append("repeated_semantics")

    template_id = _template_id_for(intent=intent, project_context=project_context, text=text, question=question)
    normalized_semantic = _semantic_normalize(f"{text} {question}".strip(), intent=intent)
    memory = normalize_reply_dedupe_memory(reply_memory)
    by_intent = memory.get("by_intent", {})
    recent_rows = []
    if isinstance(by_intent, Mapping):
        rows = by_intent.get(intent, [])
        if isinstance(rows, list):
            recent_rows = [dict(item) for item in rows if isinstance(item, Mapping)][-max(1, _INTENT_WINDOW[intent]) :]
    threshold = _INTENT_DEDUPE_THRESHOLD[intent]
    context_signature = _select_context_signature(intent, project_context, question)
    latest_row = recent_rows[-1] if recent_rows else {}
    same_template_recent = False
    same_context_recent = False
    for row in recent_rows:
        row_text = _semantic_normalize(str(row.get("normalized_text", "")), intent=intent)
        score = _semantic_similarity(normalized_semantic, row_text)
        similarity_max = max(similarity_max, score)
        if str(row.get("template_id", "")) == template_id:
            same_template_recent = True
        if context_signature and str(row.get("context_signature", "")) == context_signature:
            same_context_recent = True
    is_near_duplicate = similarity_max >= threshold or same_template_recent

    if intent == "progress_update":
        progress_unchanged = bool(context_signature and str(latest_row.get("context_signature", "")) == context_signature)
        if progress_unchanged and is_near_duplicate:
            reasons.append("progress_no_new_info")
            if allow_suppress:
                suppress = True
                dedupe_action = "suppress"
            else:
                downgraded_text, downgraded_q = _downgrade_text(
                    intent=intent,
                    lang_hint=lang_hint,
                    project_context=project_context,
                    next_question=question,
                    previous_reply_text=previous_reply_text,
                )
                text = _norm(downgraded_text) or text
                question = _norm(downgraded_q)
                dedupe_action = "downgrade"
    elif intent == "ask_decision":
        if same_context_recent and is_near_duplicate:
            reasons.append("decision_same_question")
            if allow_suppress:
                suppress = True
                dedupe_action = "suppress"
            else:
                downgraded_text, downgraded_q = _downgrade_text(
                    intent=intent,
                    lang_hint=lang_hint,
                    project_context=project_context,
                    next_question=question,
                    previous_reply_text=previous_reply_text,
                )
                text = _norm(downgraded_text) or text
                question = _norm(downgraded_q) or question
                dedupe_action = "downgrade"
    elif is_near_duplicate:
        reasons.append("near_duplicate")
        if allow_suppress and intent in {"acknowledge_user"}:
            suppress = True
            dedupe_action = "suppress"
        else:
            downgraded_text, downgraded_q = _downgrade_text(
                intent=intent,
                lang_hint=lang_hint,
                project_context=project_context,
                next_question=question,
                previous_reply_text=previous_reply_text,
            )
            text = _norm(downgraded_text) or text
            question = _norm(downgraded_q) or question
            dedupe_action = "downgrade"

    if suppress:
        text = ""
        question = ""

    normalized_semantic = _semantic_normalize(f"{text} {question}".strip(), intent=intent)
    recorded = _append_memory_entry(
        memory=memory,
        intent=intent,
        template_id=template_id,
        normalized_text=normalized_semantic,
        rendered_text=f"{text} {question}".strip(),
        timestamp=_norm(now_ts),
        provider_mode=_norm(provider_mode),
        source_kind=_norm(source_kind) or ("fallback" if fallback_used else "provider"),
        sent=bool((not suppress) and bool(text)),
        context_signature=context_signature,
    )

    return {
        "reply_text": text,
        "next_question": question,
        "intent": intent,
        "template_id": template_id,
        "dedupe_action": dedupe_action,
        "suppressed": suppress,
        "similarity_max": round(similarity_max, 4),
        "normalized_text": normalized_semantic,
        "memory_entry": recorded,
        "reply_memory": memory,
        "fallback_used": fallback_used,
        "reasons": reasons[:8],
    }
