from __future__ import annotations

import unittest

from apps.cs_frontend.application.handle_user_message import FrontendMessageHandler
from apps.cs_frontend.config import FrontendConfig
from apps.cs_frontend.gateway.backend_client import BackendClient
from apps.cs_frontend.storage.pending_question_store import PendingQuestionStore
from apps.cs_frontend.storage.session_store import SessionStore
from apps.project_backend.application.service import ProjectBackendService
from apps.project_backend.config import BackendConfig


class _BridgeIntegrationStub:
    def __init__(self) -> None:
        self._decision_done = False
        self.created_runs: list[dict[str, object]] = []

    def new_run(self, *, goal: str, constraints: dict[str, object], attachments: list[str]) -> dict[str, object]:
        self.created_runs.append(
            {
                "goal": goal,
                "constraints": dict(constraints),
                "attachments": list(attachments),
            }
        )
        return {"run_id": "job-int", "run_dir": "D:/tmp/job-int"}

    def advance(self, *, run_id: str, max_steps: int) -> dict[str, object]:
        return {"run_id": run_id, "max_steps": max_steps}

    def get_status(self, *, run_id: str) -> dict[str, object]:
        if self._decision_done:
            return {
                "run_id": run_id,
                "run_status": "pass",
                "verify_result": "PASS",
                "needs_user_decision": False,
                "gate": {"state": "ready_verify", "reason": "verify done"},
            }
        return {
            "run_id": run_id,
            "run_status": "running",
            "verify_result": "",
            "needs_user_decision": True,
            "gate": {"state": "blocked", "reason": "need decision"},
        }

    def list_decisions(self, *, run_id: str) -> dict[str, object]:
        if self._decision_done:
            return {"count": 0, "decisions": []}
        return {
            "count": 1,
            "decisions": [{"decision_id": "d-1", "question_hint": "pick one"}],
        }

    def submit_decision(self, *, run_id: str, decision: dict[str, object]) -> dict[str, object]:
        self._decision_done = True
        return {"ok": True}

    def get_last_report(self, *, run_id: str) -> dict[str, object]:
        return {"verify_report": {"result": "PASS"}, "repo_report_tail": "all good"}


class _InProcessTransport:
    def __init__(self, service: ProjectBackendService) -> None:
        self.service = service

    def submit_job(self, payload: dict[str, object]) -> dict[str, object]:
        from apps.project_backend.api.submit_job import submit_job

        return submit_job(self.service, payload)

    def answer_question(self, payload: dict[str, object]) -> dict[str, object]:
        from apps.project_backend.api.answer_question import answer_question

        return answer_question(self.service, payload)

    def get_status(self, job_id: str) -> dict[str, object]:
        from apps.project_backend.api.get_status import get_status

        return get_status(self.service, job_id)

    def get_result(self, job_id: str) -> dict[str, object]:
        from apps.project_backend.api.get_result import get_result

        return get_result(self.service, job_id)

    def poll_events(self, job_id: str) -> list[dict[str, object]]:
        return self.service.poll_events(job_id)


class FrontendBackendIntegrationTests(unittest.TestCase):
    def test_frontend_backend_question_answer_flow(self) -> None:
        bridge = _BridgeIntegrationStub()
        backend_service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        backend_client = BackendClient(transport=_InProcessTransport(backend_service))
        handler = FrontendMessageHandler(
            config=FrontendConfig(),
            backend_client=backend_client,
            session_store=SessionStore(),
            pending_question_store=PendingQuestionStore(),
        )

        first = handler.handle_user_message(
            session_id="int",
            text="我想做一个VN推理游戏工具，能记录整理世界线并支持画图。",
            source="cli",
        )
        self.assertIn("pick one", first.reply_text)
        self.assertTrue(bridge.created_runs)
        first_constraints = bridge.created_runs[0].get("constraints", {})
        self.assertEqual(str(first_constraints.get("project_domain", "")), "story_reasoning_game")
        self.assertEqual(str(first_constraints.get("worldline_management", "")), "required")
        self.assertEqual(str(first_constraints.get("diagram_support", "")), "required")

        second = handler.handle_user_message(session_id="int", text="选择默认方案", source="cli")
        self.assertTrue(
            ("我已进入执行阶段" in second.reply_text) or ("结果已准备好" in second.reply_text),
            msg=second.reply_text,
        )

    def test_frontend_backend_backend_test_default_output_flow(self) -> None:
        bridge = _BridgeIntegrationStub()
        backend_service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        backend_client = BackendClient(transport=_InProcessTransport(backend_service))
        handler = FrontendMessageHandler(
            config=FrontendConfig(),
            backend_client=backend_client,
            session_store=SessionStore(),
            pending_question_store=PendingQuestionStore(),
        )

        first = handler.handle_user_message(
            session_id="int-default-output",
            text="我想做一个项目，全自动先保留客服触发，测试后端的时候直接默认输出。",
            source="cli",
        )
        self.assertIn("结果已准备好", first.reply_text)
        self.assertTrue(bridge.created_runs)
        first_constraints = bridge.created_runs[0].get("constraints", {})
        self.assertTrue(bool(first_constraints.get("backend_test_default_output", False)))
        self.assertEqual(str(first_constraints.get("delivery_trigger_mode", "")), "support")


if __name__ == "__main__":
    unittest.main()
