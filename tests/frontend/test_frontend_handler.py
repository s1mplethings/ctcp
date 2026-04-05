from __future__ import annotations

import unittest

from apps.cs_frontend.application.handle_user_message import FrontendMessageHandler
from apps.cs_frontend.config import FrontendConfig
from apps.cs_frontend.storage.pending_question_store import PendingQuestionStore
from apps.cs_frontend.storage.session_store import SessionStore


class _StubBackendClient:
    def __init__(self) -> None:
        self.submitted_payloads: list[dict[str, object]] = []
        self.answered_payloads: list[dict[str, object]] = []
        self._events: dict[str, list[dict[str, object]]] = {}

    def submit_job(self, payload: dict[str, object]) -> dict[str, object]:
        self.submitted_payloads.append(dict(payload))
        job_id = "job-front"
        self._events[job_id] = [
            {"event_type": "event_status", "event_id": "evt-1", "job_id": job_id, "phase": "created", "summary": "job created"},
            {"event_type": "event_question", "event_id": "evt-2", "job_id": job_id, "question_id": "q-1", "question_text": "need one decision"},
        ]
        return {"event_type": "event_status", "job_id": job_id}

    def answer_question(self, payload: dict[str, object]) -> dict[str, object]:
        self.answered_payloads.append(dict(payload))
        job_id = str(payload.get("job_id", ""))
        self._events[job_id] = [
            {"event_type": "event_status", "event_id": "evt-3", "job_id": job_id, "phase": "generation", "summary": "continue"}
        ]
        return {"event_type": "event_status", "job_id": job_id}

    def get_status(self, job_id: str) -> dict[str, object]:
        return {"event_type": "event_status", "job_id": job_id, "phase": "generation", "summary": "continue"}

    def get_result(self, job_id: str) -> dict[str, object]:
        return {"event_type": "event_result", "job_id": job_id, "summary": "done", "artifacts": {}}

    def poll_events(self, job_id: str) -> list[dict[str, object]]:
        rows = self._events.get(job_id, [])
        self._events[job_id] = []
        return list(rows)


class FrontendHandlerTests(unittest.TestCase):
    def test_project_like_message_submits_structured_job_create_payload(self) -> None:
        backend = _StubBackendClient()
        handler = FrontendMessageHandler(
            config=FrontendConfig(),
            backend_client=backend,
            session_store=SessionStore(),
            pending_question_store=PendingQuestionStore(),
        )
        event = handler.handle_user_message(
            session_id="s1",
            text="帮我做一个VN推理游戏项目，可以记录整理世界线并支持画图。",
            source="cli",
        )
        self.assertTrue(backend.submitted_payloads)
        payload = backend.submitted_payloads[0]
        self.assertIn("request_id", payload)
        self.assertIn("user_goal", payload)
        self.assertNotIn("chat_history", payload)
        requirement_summary = payload.get("requirement_summary", {})
        self.assertIsInstance(requirement_summary, dict)
        constraints = requirement_summary.get("constraints", {})
        self.assertIsInstance(constraints, dict)
        self.assertEqual(str(constraints.get("project_domain", "")), "story_reasoning_game")
        self.assertEqual(str(constraints.get("worldline_management", "")), "required")
        self.assertEqual(str(constraints.get("diagram_support", "")), "required")
        self.assertIn("need one decision", event.reply_text)

    def test_backend_test_default_output_intent_is_serialized_as_constraints(self) -> None:
        backend = _StubBackendClient()
        handler = FrontendMessageHandler(
            config=FrontendConfig(),
            backend_client=backend,
            session_store=SessionStore(),
            pending_question_store=PendingQuestionStore(),
        )
        handler.handle_user_message(
            session_id="s-backend-default",
            text="我想做一个项目，全自动先保留客服触发，测试后端的时候直接默认输出。",
            source="cli",
        )
        payload = backend.submitted_payloads[0]
        requirement_summary = payload.get("requirement_summary", {})
        self.assertIsInstance(requirement_summary, dict)
        constraints = requirement_summary.get("constraints", {})
        self.assertIsInstance(constraints, dict)
        self.assertTrue(bool(constraints.get("backend_test_default_output", False)))
        self.assertEqual(str(constraints.get("delivery_trigger_mode", "")), "support")

    def test_pending_question_answer_is_sent_as_structured_answer(self) -> None:
        backend = _StubBackendClient()
        handler = FrontendMessageHandler(
            config=FrontendConfig(),
            backend_client=backend,
            session_store=SessionStore(),
            pending_question_store=PendingQuestionStore(),
        )
        handler.handle_user_message(session_id="s2", text="我想做一个后端系统", source="cli")
        event = handler.handle_user_message(session_id="s2", text="选A", source="cli")
        self.assertEqual(len(backend.answered_payloads), 1)
        answer_payload = backend.answered_payloads[0]
        self.assertEqual(str(answer_payload.get("question_id", "")), "q-1")
        self.assertEqual(str(answer_payload.get("answer_content", "")), "选A")
        self.assertIn("我已进入执行阶段", event.reply_text)
        self.assertNotIn("当前阶段", event.reply_text)


if __name__ == "__main__":
    unittest.main()
