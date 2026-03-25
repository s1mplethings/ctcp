from __future__ import annotations

from apps.cs_frontend.domain.presentable_event import PresentableEvent


class ResponseRenderer:
    def from_backend_events(self, events: list[dict[str, object]]) -> PresentableEvent:
        if not events:
            return PresentableEvent(reply_text="收到，我会继续推进。", events=[])

        latest = events[-1]
        etype = str(latest.get("event_type", ""))
        if etype == "event_question":
            return PresentableEvent(reply_text=str(latest.get("question_text", "需要你补充一个决定。")), events=events)
        if etype == "event_result":
            return PresentableEvent(reply_text="任务已完成，结果已准备好。", events=events)
        if etype == "event_failure":
            return PresentableEvent(reply_text="执行出现问题，我正在修复并会及时同步。", events=events)
        phase = str(latest.get("phase", "")).strip().lower()
        if phase == "waiting_answer":
            return PresentableEvent(reply_text="我需要你做一个选择，回复后我会继续执行。", events=events)
        if phase in {"done"}:
            return PresentableEvent(reply_text="任务已完成，结果已准备好。", events=events)
        if phase in {"failed"}:
            return PresentableEvent(reply_text="执行遇到问题，我正在尝试修复。", events=events)
        if phase in {"created", "analyze", "planning", "context", "generation", "verification", "repair"}:
            return PresentableEvent(reply_text="我已进入执行阶段，会在需要你决策或结果就绪时立即通知你。", events=events)
        return PresentableEvent(reply_text="任务正在处理中，我会持续跟进并同步关键进展。", events=events)
