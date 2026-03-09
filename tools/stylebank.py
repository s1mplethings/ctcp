from __future__ import annotations

import hashlib
from typing import Any


def _normalize_intent(intent: str) -> str:
    text = str(intent or "").strip().lower()
    if not text:
        return "general"
    return text


def _style_bank(lang: str) -> dict[str, list[str]]:
    if str(lang).lower() == "en":
        return {
            "openers": [
                "Thanks for the update.",
                "I have your request and I'm on it.",
                "I understand what you need.",
                "I synced your priority and can move now.",
            ],
            "transitions": [
                "I will push the next step now.",
                "I can move this forward right away.",
                "I will continue from here and keep momentum.",
                "I will lock the next move in this turn.",
            ],
            "closers": [
                "To avoid delay,",
                "To keep this moving,",
                "To close this turn cleanly,",
                "Before I lock the next checkpoint,",
            ],
            "questions": [
                "Could you confirm one key detail first?",
                "Can you share one missing detail so I can proceed faster?",
                "Could you confirm your top priority for this step?",
            ],
        }
    return {
        "openers": [
            "我收到你的需求了。",
            "这件事我已经接住并开始处理。",
            "你的重点我已经对齐。",
            "我理解你的目标，现在就往前推进。",
        ],
        "transitions": [
            "我会先把这一轮关键动作落下去。",
            "我现在就把下一步推进起来。",
            "我会在这一轮先把节奏拉起来。",
            "我会马上按可执行路径继续推进。",
        ],
        "closers": [
            "为了不耽误进度，",
            "为了让这一轮闭环，",
            "为了继续往前推，",
            "为了先把产出做出来，",
        ],
        "questions": [
            "你先确认一个关键点可以吗？",
            "你补一条关键信息，我就能更快推进，可以吗？",
            "你先确认这一步的最高优先级，可以吗？",
        ],
    }


def choose_variants(
    *,
    chat_id: int,
    intent: str,
    turn_index: int,
    style_seed: str,
    lang: str,
) -> dict[str, str]:
    normalized_intent = _normalize_intent(intent)
    turn = max(1, int(turn_index))
    seed_text = str(style_seed or "").strip() or normalized_intent
    key = f"{chat_id}|{normalized_intent}|{turn}|{seed_text}"
    digest = hashlib.sha256(key.encode("utf-8", errors="replace")).hexdigest()
    bank = _style_bank(lang)
    openers = bank.get("openers", [""])
    transitions = bank.get("transitions", [""])
    closers = bank.get("closers", [""])
    questions = bank.get("questions", [""])
    i0 = int(digest[0:8], 16)
    i1 = int(digest[8:16], 16)
    i2 = int(digest[16:24], 16)
    i3 = int(digest[24:32], 16)
    resolved_seed = seed_text[:64]
    return {
        "opener": openers[i0 % len(openers)],
        "transition": transitions[i1 % len(transitions)],
        "closer": closers[i2 % len(closers)],
        "question_style": questions[i3 % len(questions)],
        "intent": normalized_intent,
        "style_seed": resolved_seed,
        "seed": digest[:12],
    }


def choose_variants_from_state(
    *,
    chat_id: int,
    turn_index: int,
    route_doc: dict[str, Any] | None,
    state: dict[str, Any] | None,
    lang: str,
) -> dict[str, str]:
    route_doc = route_doc or {}
    state = state or {}
    intent = str(route_doc.get("intent", "")).strip() or str(state.get("last_intent", "")).strip() or "general"
    style_seed = (
        str(route_doc.get("style_seed", "")).strip()
        or str(state.get("last_style_seed", "")).strip()
        or str(state.get("style_seed", "")).strip()
    )
    return choose_variants(chat_id=chat_id, intent=intent, turn_index=turn_index, style_seed=style_seed, lang=lang)
