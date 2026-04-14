import re
from typing import Any, Mapping

_PROGRESS_UPDATE_PATTERNS_ZH = (
    re.compile(r"(进度|状态|做到什么程度|做到哪|做到哪一步|到哪了|到哪一步|做了什么|现在什么情况|到什么阶段|卡在哪|先看什么|能先看|有什么能看|有什么可看)"),
)
_PROGRESS_UPDATE_PATTERNS_EN = (
    re.compile(
        r"\b(progress|status|how far|where are we|what(?:'| i)?s done|what has been done|what did you do|what.?s the update|what.?s the status|anything visible|anything to preview|can i see)\b",
        re.IGNORECASE,
    ),
)

_PROGRESS_HUMANIZE_RULES_ZH: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^waiting for file_request\.json$", re.IGNORECASE), "需求整理这一步还没落下来，当前还在等需求清单生成出来"),
    (re.compile(r"^retry planner intake synthesis and verify file_request\.json lands$", re.IGNORECASE), "重试需求整理，并确认需求清单真正生成出来"),
    (re.compile(r"^补齐\s*file_request\.json\s*并继续推进执行阶段$", re.IGNORECASE), "把需求清单整理出来，再继续往下推进当前阶段"),
)
_PROGRESS_HUMANIZE_RULES_EN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^waiting for file_request\.json$", re.IGNORECASE), "the request brief has not landed yet"),
    (re.compile(r"^retry planner intake synthesis and verify file_request\.json lands$", re.IGNORECASE), "retry the request-brief synthesis and confirm it is generated"),
    (re.compile(r"^补齐\s*file_request\.json\s*并继续推进执行阶段$", re.IGNORECASE), "prepare the request brief and continue the current execution step"),
)
_PROGRESS_TOKEN_LABELS_ZH = {
    "file_request.json": "需求清单",
}
_PROGRESS_TOKEN_LABELS_EN = {
    "file_request.json": "request brief",
}


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


def summarize_progress_evidence_refs(proof_refs: Any, *, lang: str) -> str:
    if not isinstance(proof_refs, list):
        return ""
    refs = _dedupe_items([str(item or "").strip() for item in proof_refs], limit=3)
    if not refs:
        return ""
    use_en = str(lang or "").strip().lower().startswith("en")
    labels: list[str] = []
    for ref in refs:
        low = ref.lower().replace("\\", "/")
        if any(token in low for token in ("final-ui", "screenshot", "screen", "preview", ".png", ".jpg", ".jpeg", ".webp", ".bmp")):
            labels.append("a reviewable UI screenshot is ready" if use_en else "成品截图已经可查看")
            continue
        if low.endswith(".zip") or "/support_exports/" in low or "package" in low:
            labels.append("a reviewable package is ready" if use_en else "代码包已经整理好")
            continue
        if any(token in low for token in ("verify_report", "smoke", "test_summary", "acceptance", "demo_trace")):
            labels.append("verification evidence is available" if use_en else "阶段验证结果已经落地")
            continue
        if low.startswith("run_id="):
            labels.append("this run already has a visible checkpoint" if use_en else "当前 run 已经有一轮可查看结果")
            continue
        labels.append(ref)
    visible = _dedupe_items(labels, limit=2)
    if not visible:
        return ""
    if use_en:
        return "Visible checkpoint: " + "; ".join(visible) + "."
    return "目前已经有可直接查看的阶段结果：" + "；".join(visible) + "。"


def humanize_progress_runtime_text(text: str, *, lang: str) -> str:
    raw = re.sub(r"\s+", " ", str(text or "").strip())
    if not raw:
        return ""
    use_en = str(lang or "").strip().lower().startswith("en")
    rules = _PROGRESS_HUMANIZE_RULES_EN if use_en else _PROGRESS_HUMANIZE_RULES_ZH
    for pattern, replacement in rules:
        if pattern.match(raw):
            return replacement

    token_map = _PROGRESS_TOKEN_LABELS_EN if use_en else _PROGRESS_TOKEN_LABELS_ZH
    out = raw
    for needle, replacement in token_map.items():
        out = re.sub(re.escape(needle), replacement, out, flags=re.IGNORECASE)
    if not use_en:
        out = out.replace("继续推进执行阶段", "继续往下推进当前阶段")
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
    blocker = humanize_progress_runtime_text(str(binding.get("current_blocker", "")), lang=lang)
    next_action = humanize_progress_runtime_text(str(binding.get("next_action", "")), lang=lang)
    evidence = summarize_progress_evidence_refs(binding.get("proof_refs", []), lang=lang)
    question_needed = str(binding.get("question_needed", "")).strip().lower() in {"yes", "true", "1"}
    blocking_question = re.sub(r"\s+", " ", str(binding.get("blocking_question", "")).strip()) or re.sub(
        r"\s+", " ", str(fallback_question or "").strip()
    )
    rows: list[str] = []
    questions: list[str] = []

    if lang == "en":
        if done_items:
            rows.append(f"Confirmed progress so far: {'; '.join(done_items)}.")
        if evidence:
            rows.append(evidence)
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
    if evidence:
        rows.append(evidence)
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
