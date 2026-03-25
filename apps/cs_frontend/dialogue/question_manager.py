from __future__ import annotations


class QuestionManager:
    def render_question(self, question: dict[str, str]) -> str:
        text = str(question.get("question_text", "")).strip()
        return text or "后端需要一个明确决策，请回复你的选择。"
