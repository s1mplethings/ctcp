from __future__ import annotations

import re
from typing import Any, Iterable, Literal, Mapping

from .project_manager_mode import requirement_information_score

ConversationMode = Literal[
    "GREETING",
    "SMALLTALK",
    "CAPABILITY_QUERY",
    "PROJECT_INTAKE",
    "PROJECT_DETAIL",
    "PROJECT_DECISION_REPLY",
    "STATUS_QUERY",
]

_GREETING_ZH_EXACT = {
    "你好",
    "您好",
    "嗨",
    "哈喽",
    "在吗",
    "晚上好",
    "下午好",
    "早上好",
    "早",
    "喂",
}
_GREETING_EN_EXACT = {
    "hi",
    "hello",
    "hey",
    "yo",
    "ping",
    "test",
    "testing",
    "?",
}
_SMALLTALK_ZH = {
    "谢谢",
    "感谢",
    "辛苦了",
}
_CAPABILITY_ZH = {
    "你是谁",
    "你能做什么",
    "怎么用",
}
_SMALLTALK_EN = {
    "thanks",
    "thank you",
}
_CAPABILITY_EN = {
    "who are you",
    "what can you do",
    "how to use",
}

_PROJECT_EXECUTION_FOLLOWUP_ZH = (
    "先开始做",
    "先开始吧",
    "先做",
    "先做出",
    "做出第一版",
    "先出第一版",
    "先出一版",
    "开始做项目",
    "开始做吧",
    "按这个做",
    "你先做",
    "你可以先开始",
    "后面我再补",
    "后面有了我再补",
    "我再调整",
    "后面再调整",
    "继续做",
    "继续推进",
)

_PROJECT_EXECUTION_FOLLOWUP_EN = (
    "go ahead and start",
    "start the project",
    "make a first draft",
    "make the first draft",
    "make a first version",
    "build the first version",
    "first version",
    "first draft",
    "first pass",
    "you can start first",
    "i'll adjust later",
    "i will adjust later",
    "keep building",
)
_STATUS_PATTERNS = (
    re.compile(r"(进度|状态|还在做吗|进行到哪|卡住|阻塞|当前项目|有没有在进行)"),
    re.compile(r"(什么情况|做好了吗|完成了吗|好了没|生成了.{0,4}吗|弄好了吗|搞定了吗|做完了吗|出来了吗|结果.{0,4}(怎|如何|出))"),
    re.compile(r"(之前|原来).*(项目|方案|大纲).*(进度|状态|做到什么程度|做到哪|做到哪一步|做成什么样|做得怎么样|现在怎么样|现在什么情况)"),
    re.compile(r"\b(status|progress|blocked|stuck|what.?s running|running now|is it done|finished|ready)\b", re.IGNORECASE),
    re.compile(
        r"\b(previous|earlier|old)\b.{0,24}\b(project|plan|outline)\b.{0,24}\b(status|progress|done|ready|finished|latest)\b",
        re.IGNORECASE,
    ),
)
_PROJECT_INTENT_PATTERNS = (
    re.compile(r"(做一个|做个|新建|创建|搭建|开发|实现).{0,20}(项目|流程|系统|工具|机器人|bot|游戏|应用)"),
    re.compile(r"\b(build|create|start|implement|develop)\b.{0,24}\b(project|workflow|pipeline|system|tool|bot|game|app)\b", re.IGNORECASE),
)
_PROJECT_DOMAIN_TOKENS = (
    "项目",
    "流程",
    "工作流",
    "系统",
    "工具",
    "点云",
    "无人机",
    "语义",
    "建图",
    "视频",
    "游戏",
    "剧情",
    "角色",
    "故事",
    "视觉小说",
    "workflow",
    "pipeline",
    "point cloud",
    "drone",
    "uav",
    "semantic",
    "realtime",
    "real-time",
    "offline",
    "ply",
    "las",
    "pcd",
    "game",
    "visual novel",
    "storyline",
    "character",
)
_CONSTRAINT_TOKENS = (
    "优先速度",
    "优先质量",
    "优先成本",
    "速度",
    "质量",
    "成本",
    "实时",
    "离线",
    "预算",
    "latency",
    "speed",
    "quality",
    "cost",
    "offline",
    "real-time",
    "realtime",
    "budget",
)
_DECISION_HINTS = (
    "优先",
    "先",
    "选",
    "选择",
    "prefer",
    "choose",
    "pick",
)
_TRADEOFF_HINTS = (
    "速度",
    "质量",
    "成本",
    "speed",
    "quality",
    "cost",
)


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _is_punctuation_or_probe(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    if re.fullmatch(r"[\?\!？！。，,.\s~～]+", raw):
        return True
    low = raw.lower()
    if low in {"?", "？", "test", "testing", "ping"}:
        return True
    return False


def is_greeting_only(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    low = raw.lower()
    if _is_punctuation_or_probe(raw):
        return True
    if raw in _GREETING_ZH_EXACT or low in _GREETING_EN_EXACT:
        return True
    if re.fullmatch(r"(你好|您好|嗨|哈喽|在吗|晚上好|下午好|早上好)[!！。.\?？]*", raw):
        return True
    if re.fullmatch(r"(hi|hello|hey)[!.\?]*", low):
        return True
    return False


def _is_smalltalk(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    if is_greeting_only(raw):
        return False
    low = raw.lower()
    if raw in _SMALLTALK_ZH or low in _SMALLTALK_EN:
        return True
    if len(raw) <= 16 and any(raw.startswith(x) for x in ("谢谢", "感谢")):
        return True
    if len(low) <= 32 and any(low.startswith(x) for x in ("thanks", "thank")):
        return True
    return False


def is_capability_query(text: str) -> bool:
    raw = _norm(text)
    if not raw or is_greeting_only(raw):
        return False
    low = raw.lower()
    if raw in _CAPABILITY_ZH or low in _CAPABILITY_EN:
        return True
    if any(token in raw for token in ("你是谁", "你是做什么的", "你能做什么", "怎么用", "怎么开始")):
        return True
    if ("你能" in raw or "可以" in raw) and any(token in raw for token in ("做什么", "前端", "界面", "网页", "web")):
        return True
    if any(
        token in low
        for token in (
            "who are you",
            "what can you do",
            "how to use",
            "how do i use this",
            "how should i use this",
            "how do we start",
            "can you change the frontend",
            "can you work on the frontend",
            "can you modify the frontend",
            "can you handle frontend",
            "can you help with frontend",
        )
    ):
        return True
    return low.startswith("can you") and any(token in low for token in ("frontend", "front-end", "ui", "web"))


def _is_status_query(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    return any(p.search(raw) for p in _STATUS_PATTERNS)


def is_status_query(text: str) -> bool:
    return _is_status_query(text)


def _contains_any_token(text: str, tokens: Iterable[str]) -> bool:
    raw = _norm(text)
    low = raw.lower()
    for token in tokens:
        if (token in raw) or (token.lower() in low):
            return True
    return False


def _looks_project_intent(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    if any(p.search(raw) for p in _PROJECT_INTENT_PATTERNS):
        return True
    if raw.startswith(("我想做", "我要做", "我想要做", "帮我做", "请帮我做")) and len(raw) >= 6:
        return True
    low = raw.lower()
    if low.startswith(("i want to build", "i need to build", "build ", "create ", "start ")) and len(low) >= 12:
        return True
    return False


def _contains_domain_signal(text: str) -> bool:
    return _contains_any_token(text, _PROJECT_DOMAIN_TOKENS)


def _contains_constraint_signal(text: str) -> bool:
    return _contains_any_token(text, _CONSTRAINT_TOKENS)


def _is_decision_reply(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    low = raw.lower()
    speed_hit = ("速度" in raw) or ("speed" in low)
    quality_hit = ("质量" in raw) or ("quality" in low)
    cost_hit = ("成本" in raw) or ("cost" in low)
    tradeoff_dims = int(speed_hit) + int(quality_hit) + int(cost_hit)
    if tradeoff_dims < 2:
        return False
    has_decision = any(tok in raw for tok in _DECISION_HINTS) or any(tok in low for tok in _DECISION_HINTS)
    has_choice_connector = ("还是" in raw) or bool(re.search(r"\bor\b", low))
    return has_decision or has_choice_connector


def compute_task_signal_score(messages: Iterable[str]) -> float:
    rows = [_norm(x) for x in messages if _norm(x)]
    if not rows:
        return 0.0
    latest = rows[-1]
    if is_greeting_only(latest) or is_capability_query(latest):
        return 0.0
    base = requirement_information_score(latest)
    best_recent = max(requirement_information_score(x) for x in rows[-4:])
    score = max(base, best_recent * 0.9)
    if _looks_project_intent(latest):
        score += 0.8
    if _contains_domain_signal(latest):
        score += 0.8
    if _contains_constraint_signal(latest):
        score += 0.6
    if len(latest) >= 20:
        score += 0.3
    return min(10.0, score)


def has_sufficient_task_signal(messages: Iterable[str], threshold: float = 2.4) -> bool:
    return compute_task_signal_score(messages) >= float(threshold)


def has_valid_task_summary(state: Mapping[str, Any] | str | None) -> bool:
    if state is None:
        return False
    if isinstance(state, str):
        summary = _norm(state)
    elif isinstance(state, Mapping):
        candidates = (
            state.get("task_summary", ""),
            state.get("selected_requirement_source", ""),
            state.get("user_goal", ""),
            state.get("execution_goal", ""),
            state.get("last_request", ""),
        )
        summary = ""
        for item in candidates:
            text = _norm(str(item or ""))
            if text:
                summary = text
                break
    else:
        return False
    if not summary:
        return False
    if is_greeting_only(summary) or _is_smalltalk(summary) or is_capability_query(summary):
        return False
    if requirement_information_score(summary) >= 1.4:
        return True
    return _looks_project_intent(summary) or _contains_domain_signal(summary)


def has_active_project_binding(state: Mapping[str, Any] | None) -> bool:
    if not isinstance(state, Mapping):
        return False
    candidates = (
        state.get("run_id", ""),
        state.get("bound_run_id", ""),
        state.get("active_run_id", ""),
    )
    return any(_norm(str(item or "")) for item in candidates)


def is_project_execution_followup(text: str) -> bool:
    raw = _norm(text)
    if not raw:
        return False
    if is_greeting_only(raw) or _is_smalltalk(raw) or _is_status_query(raw):
        return False
    low = raw.lower()
    if any(token in raw for token in _PROJECT_EXECUTION_FOLLOWUP_ZH):
        return True
    if any(token in low for token in _PROJECT_EXECUTION_FOLLOWUP_EN):
        return True
    return False


def can_emit_project_followup(state: Mapping[str, Any] | None) -> bool:
    if not isinstance(state, Mapping):
        return False
    if not has_valid_task_summary(state):
        return False
    mode = str(state.get("conversation_mode", "")).strip().upper()
    if mode and not mode.startswith("PROJECT_"):
        return False
    return True


def is_generic_tradeoff_question(text: str) -> bool:
    q = _norm(text)
    if not q:
        return False
    low = q.lower()
    zh_tradeoff = ("速度" in q and "质量" in q) and ("成本" in q)
    en_tradeoff = ("speed" in low and "quality" in low) and ("cost" in low)
    if zh_tradeoff or en_tradeoff:
        return True
    if "top priority" in low and ("speed" in low or "quality" in low or "cost" in low):
        return True
    if "最高优先级" in q and any(k in q for k in ("速度", "质量", "成本")):
        return True
    return False


def route_conversation_mode(
    messages: Iterable[str],
    latest_user_message: str,
    active_task_state: Mapping[str, Any] | None,
) -> ConversationMode:
    latest = _norm(latest_user_message)
    rows = [_norm(x) for x in messages if _norm(x)]
    if latest and (not rows or rows[-1] != latest):
        rows.append(latest)

    if is_greeting_only(latest):
        return "GREETING"
    if _is_status_query(latest):
        return "STATUS_QUERY"
    if is_capability_query(latest):
        return "CAPABILITY_QUERY"
    if _is_smalltalk(latest):
        return "SMALLTALK"

    has_active_task = has_valid_task_summary(active_task_state)
    has_active_binding = has_active_project_binding(active_task_state)
    has_project_context = has_active_task or has_active_binding
    if _is_decision_reply(latest) and has_project_context:
        return "PROJECT_DECISION_REPLY"
    if has_project_context and is_project_execution_followup(latest):
        return "PROJECT_DETAIL"

    if has_sufficient_task_signal(rows):
        if _contains_domain_signal(latest) or _contains_constraint_signal(latest):
            return "PROJECT_DETAIL"
        return "PROJECT_INTAKE"

    if _looks_project_intent(latest):
        return "PROJECT_INTAKE"

    if has_active_task and latest:
        return "PROJECT_DETAIL"

    return "SMALLTALK"
