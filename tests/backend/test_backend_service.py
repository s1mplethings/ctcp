from __future__ import annotations

import unittest

from apps.project_backend.application.service import ProjectBackendService
from apps.project_backend.config import BackendConfig
from contracts.schemas.job_answer import JobAnswerRequest
from contracts.schemas.job_create import JobCreateRequest


class _FakeBridge:
    def __init__(self) -> None:
        self.answers: list[dict[str, object]] = []
        self.created_runs: list[dict[str, object]] = []

    def new_run(
        self,
        *,
        goal: str,
        constraints: dict[str, object],
        attachments: list[str],
        project_intent: dict[str, object] | None = None,
        project_spec: dict[str, object] | None = None,
    ) -> dict[str, object]:
        self.created_runs.append(
            {
                "goal": goal,
                "constraints": dict(constraints),
                "attachments": list(attachments),
                "project_intent": dict(project_intent or {}),
                "project_spec": dict(project_spec or {}),
            }
        )
        return {
            "run_id": "job-demo",
            "run_dir": "D:/tmp/job-demo",
            "goal": goal,
            "constraints": constraints,
            "attachments": attachments,
            "project_intent": project_intent or {},
            "project_spec": project_spec or {},
        }

    def advance(self, *, run_id: str, max_steps: int) -> dict[str, object]:
        return {"run_id": run_id, "max_steps": max_steps}

    def get_status(self, *, run_id: str) -> dict[str, object]:
        return {
            "run_id": run_id,
            "run_status": "running",
            "verify_result": "",
            "needs_user_decision": True,
            "gate": {"state": "blocked", "reason": "need decision"},
        }

    def list_decisions(self, *, run_id: str) -> dict[str, object]:
        return {
            "count": 1,
            "decisions": [
                {
                    "decision_id": "outbox:1",
                    "question_hint": "pick A or B",
                }
            ],
        }

    def submit_decision(self, *, run_id: str, decision: dict[str, object]) -> dict[str, object]:
        self.answers.append(dict(decision))
        return {"ok": True}

    def get_last_report(self, *, run_id: str) -> dict[str, object]:
        return {"verify_report": {"result": "PASS"}, "repo_report_tail": "done"}

    def get_delivery_evidence(self, *, run_id: str) -> dict[str, object]:
        return {
            "title": "job-demo 交付结果",
            "status": "ready",
            "one_line_result": "项目结果已经整理成可直接查看的交付证据。",
            "user_input_summary": "build decoupled architecture MVP",
            "user_visible_actions": [{"label": "打开主报告", "path": "D:/tmp/job-demo/report.html"}],
            "what_user_can_view_now": [{"label": "主报告页", "path": "D:/tmp/job-demo/report.html"}],
            "primary_report_path": "D:/tmp/job-demo/report.html",
            "screenshots": [{"label": "overview", "path": "D:/tmp/job-demo/overview.png"}],
            "demo_media": [{"label": "walkthrough", "path": "D:/tmp/job-demo/demo.gif"}],
            "structured_outputs": [{"label": "result json", "path": "D:/tmp/job-demo/result.json"}],
            "verification_summary": {"status": "passed", "verify_result": "PASS", "one_line": "canonical verify 已通过"},
            "limitations": [],
            "next_actions": ["打开主报告确认结果"],
        }


class BackendServiceTests(unittest.TestCase):
    def test_create_job_emits_status_and_question_events(self) -> None:
        bridge = _FakeBridge()
        service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        req = JobCreateRequest.from_payload(
            {
                "request_id": "req-1",
                "user_goal": "build decoupled architecture",
                "project_intent": {
                    "goal_summary": "build decoupled architecture MVP",
                    "target_user": "engineering team",
                    "problem_to_solve": "separate frontend and backend cleanly",
                    "mvp_scope": ["job creation", "status flow"],
                    "required_inputs": ["user goal"],
                    "required_outputs": ["runnable backend"],
                    "hard_constraints": [],
                    "assumptions": ["start with the smallest working slice"],
                    "open_questions": [],
                    "acceptance_criteria": ["one job can run end to end"],
                },
                "constraints": {
                    "project_domain": "story_reasoning_game",
                    "worldline_management": "required",
                    "diagram_support": "required",
                },
                "attachments": [],
                "requirement_summary": {"mode": "PROJECT_DETAIL"},
            }
        )
        event = service.create_job(req)
        self.assertEqual(event.job_id, "job-demo")
        events = service.poll_events("job-demo")
        event_types = [str(item.get("event_type", "")) for item in events]
        self.assertIn("event_status", event_types)
        self.assertIn("event_question", event_types)
        self.assertTrue(bridge.created_runs)
        forwarded_constraints = bridge.created_runs[0].get("constraints", {})
        forwarded_intent = bridge.created_runs[0].get("project_intent", {})
        self.assertEqual(str(forwarded_constraints.get("project_domain", "")), "story_reasoning_game")
        self.assertEqual(str(forwarded_constraints.get("worldline_management", "")), "required")
        self.assertEqual(str(forwarded_constraints.get("diagram_support", "")), "required")
        self.assertEqual(str(dict(forwarded_intent).get("goal_summary", "")), "build decoupled architecture MVP")

    def test_create_job_backend_test_default_output_emits_result_without_question(self) -> None:
        bridge = _FakeBridge()
        service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        req = JobCreateRequest.from_payload(
            {
                "request_id": "req-default-output",
                "user_goal": "backend test default output",
                "project_intent": {
                    "goal_summary": "backend test default output",
                    "target_user": "test runner",
                    "problem_to_solve": "prove backend can emit default result",
                    "mvp_scope": ["direct default output"],
                    "required_inputs": ["test trigger"],
                    "required_outputs": ["result event"],
                    "hard_constraints": [],
                    "assumptions": [],
                    "open_questions": [],
                    "acceptance_criteria": ["result event is emitted"],
                },
                "constraints": {
                    "backend_test_default_output": True,
                    "delivery_trigger_mode": "support",
                },
                "attachments": [],
                "requirement_summary": {"mode": "PROJECT_DETAIL"},
            }
        )
        event = service.create_job(req)
        self.assertEqual(str(event.phase), "done")
        events = service.poll_events("job-demo")
        event_types = [str(item.get("event_type", "")) for item in events]
        self.assertIn("event_result", event_types)
        self.assertNotIn("event_question", event_types)
        result_event = next(item for item in events if str(item.get("event_type", "")) == "event_result")
        delivery_evidence = result_event.get("delivery_evidence", {})
        self.assertIsInstance(delivery_evidence, dict)
        self.assertEqual(str(delivery_evidence.get("status", "")), "ready")
        self.assertEqual(str(delivery_evidence.get("primary_report_path", "")), "D:/tmp/job-demo/report.html")
        self.assertIn("verification_summary", delivery_evidence)

    def test_answer_question_consumes_structured_answer(self) -> None:
        bridge = _FakeBridge()
        service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        create_req = JobCreateRequest.from_payload(
            {
                "request_id": "req-2",
                "user_goal": "build decoupled architecture",
                "project_intent": {
                    "goal_summary": "build decoupled architecture MVP",
                    "target_user": "engineering team",
                    "problem_to_solve": "separate frontend and backend cleanly",
                    "mvp_scope": ["job creation", "status flow"],
                    "required_inputs": ["user goal"],
                    "required_outputs": ["runnable backend"],
                    "hard_constraints": [],
                    "assumptions": [],
                    "open_questions": [],
                    "acceptance_criteria": ["one job can run end to end"],
                },
                "constraints": {},
                "attachments": [],
                "requirement_summary": {"mode": "PROJECT_DETAIL"},
            }
        )
        service.create_job(create_req)
        answer_req = JobAnswerRequest.from_payload(
            {
                "request_id": "req-3",
                "job_id": "job-demo",
                "question_id": "outbox:1",
                "answer_content": "choose A",
                "answer_meta": {"source": "user"},
            }
        )
        service.answer_question(answer_req)
        self.assertEqual(len(bridge.answers), 1)
        self.assertEqual(str(bridge.answers[0].get("decision_id", "")), "outbox:1")


if __name__ == "__main__":
    unittest.main()
