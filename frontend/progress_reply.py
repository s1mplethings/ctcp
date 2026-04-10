import re
from typing import Any, Mapping

_PROGRESS_UPDATE_PATTERNS_ZH = (
    re.compile(r"(进度|状态|做到什么程度|做到哪|做到哪一步|到哪了|到哪一步|做了什么|现在什么情况|到什么阶段|卡在哪)"),
)
_PROGRESS_UPDATE_PATTERNS_EN = (
    re.compile(
        r"\b(progress|status|how far|where are we|what(?:'| i)?s done|what has been done|what did you do|what.?s the update|what.?s the status)\b",
        re.IGNORECASE,
    ),
)


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


def is_progress_update_request(text: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if not raw:
        return False
    low = raw.lower()
    return any(p.search(raw) for p in _PROGRESS_UPDATE_PATTERNS_ZH) or any(p.search(low) for p in _PROGRESS_UPDATE_PATTERNS_EN)


def looks_like_progress_grounded_reply(text: str, *, lang: str) -> bool:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if not raw:
        return False
    low = raw.lower()
    if str(lang or "").strip().lower().startswith("en"):
        markers = ("current", "status", "phase", "progress", "blocked", "completed", "next step", "next action")
        return any(marker in low for marker in markers)
    markers = ("当前", "目前", "状态", "阶段", "进展", "卡点", "阻塞", "已完成", "下一步")
    return any(marker in raw for marker in markers)


def normalize_progress_binding(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        return {}
    done_items = [
        re.sub(r"\s+", " ", str(item or "").strip())
        for item in raw.get("last_confirmed_items", [])
        if re.sub(r"\s+", " ", str(item or "").strip())
    ] if isinstance(raw.get("last_confirmed_items", []), list) else []
    proof_refs = [
        re.sub(r"\s+", " ", str(item or "").strip())
        for item in raw.get("proof_refs", [])
        if re.sub(r"\s+", " ", str(item or "").strip())
    ] if isinstance(raw.get("proof_refs", []), list) else []
    normalized = {
        "current_task_goal": re.sub(r"\s+", " ", str(raw.get("current_task_goal", "")).strip()),
        "current_phase": re.sub(r"\s+", " ", str(raw.get("current_phase", "")).strip()),
        "last_confirmed_items": done_items,
        "current_blocker": re.sub(r"\s+", " ", str(raw.get("current_blocker", "")).strip()),
        "message_purpose": re.sub(r"\s+", " ", str(raw.get("message_purpose", "")).strip()),
        "question_needed": re.sub(r"\s+", " ", str(raw.get("question_needed", "")).strip().lower()),
        "next_action": re.sub(r"\s+", " ", str(raw.get("next_action", "")).strip()),
        "blocking_question": re.sub(r"\s+", " ", str(raw.get("blocking_question", "")).strip()),
        "proof_refs": proof_refs,
    }
    if not any(
        (
            normalized["current_task_goal"],
            normalized["current_phase"],
            normalized["last_confirmed_items"],
            normalized["current_blocker"],
            normalized["next_action"],
            normalized["blocking_question"],
            normalized["proof_refs"],
        )
    ):
        return {}
    return normalized


def compose_progress_update_reply(
    *,
    binding: Mapping[str, Any],
    visible_state: str,
    lang: str,
    fallback_question: str = "",
) -> tuple[str, list[str]]:
    done_items = _dedupe_items(list(binding.get("last_confirmed_items", []) or []), limit=3)
    phase = re.sub(r"\s+", " ", str(binding.get("current_phase", "")).strip())
    blocker = re.sub(r"\s+", " ", str(binding.get("current_blocker", "")).strip())
    next_action = re.sub(r"\s+", " ", str(binding.get("next_action", "")).strip())
    question_needed = str(binding.get("question_needed", "")).strip().lower() in {"yes", "true", "1"}
    blocking_question = re.sub(r"\s+", " ", str(binding.get("blocking_question", "")).strip()) or re.sub(
        r"\s+", " ", str(fallback_question or "").strip()
    )
    rows: list[str] = []
    questions: list[str] = []

    if lang == "en":
        if done_items:
            rows.append(f"Confirmed progress so far: {'; '.join(done_items)}.")
        if blocker and blocker.lower() != "none":
            if phase:
                rows.append(f"Current phase: {phase}. The blocker is {blocker}.")
            else:
                rows.append(f"The current blocker is {blocker}.")
        else:
            phase_text = phase or ("delivery" if visible_state == "DONE" else "execution")
            rows.append(f"Current phase: {phase_text}. There is no extra blocker right now.")
        if next_action:
            rows.append(f"Next I will {next_action}.")
        if question_needed and blocking_question:
            rows.append(f"Before I continue, I need your call on this: {blocking_question}")
            questions = [blocking_question]
        return "\n\n".join([row for row in rows if row]).strip(), questions

    if done_items:
        rows.append("我这边已经完成：" + "、".join(done_items) + "。")
    if blocker and blocker.lower() != "none":
        if phase:
            rows.append(f"目前在{phase}这个阶段，当前卡点是：{blocker}。")
        else:
            rows.append(f"当前卡点是：{blocker}。")
    else:
        phase_text = phase or ("结果整理/交付" if visible_state == "DONE" else "执行推进")
        rows.append(f"目前在{phase_text}这个阶段，主流程还在推进，暂时没有新增阻塞。")
    if next_action:
        rows.append(f"下一步我会继续处理：{next_action}。")
    if question_needed and blocking_question:
        rows.append(f"继续前我这边还差你拍板这个点：{blocking_question}")
        questions = [blocking_question]
    return "\n\n".join([row for row in rows if row]).strip(), questions
