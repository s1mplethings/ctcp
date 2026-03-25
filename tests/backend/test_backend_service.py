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

    def new_run(self, *, goal: str, constraints: dict[str, object], attachments: list[str]) -> dict[str, object]:
        self.created_runs.append(
            {
                "goal": goal,
                "constraints": dict(constraints),
                "attachments": list(attachments),
            }
        )
        return {"run_id": "job-demo", "run_dir": "D:/tmp/job-demo", "goal": goal, "constraints": constraints, "attachments": attachments}

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


class BackendServiceTests(unittest.TestCase):
    def test_create_job_emits_status_and_question_events(self) -> None:
        bridge = _FakeBridge()
        service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        req = JobCreateRequest.from_payload(
            {
                "request_id": "req-1",
                "user_goal": "build decoupled architecture",
                "constraints": {
                    "project_domain": "vn_reasoning_game",
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
        self.assertEqual(str(forwarded_constraints.get("project_domain", "")), "vn_reasoning_game")
        self.assertEqual(str(forwarded_constraints.get("worldline_management", "")), "required")
        self.assertEqual(str(forwarded_constraints.get("diagram_support", "")), "required")

    def test_create_job_backend_test_default_output_emits_result_without_question(self) -> None:
        bridge = _FakeBridge()
        service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        req = JobCreateRequest.from_payload(
            {
                "request_id": "req-default-output",
                "user_goal": "backend test default output",
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

    def test_answer_question_consumes_structured_answer(self) -> None:
        bridge = _FakeBridge()
        service = ProjectBackendService(config=BackendConfig(), bridge=bridge)
        create_req = JobCreateRequest.from_payload(
            {
                "request_id": "req-2",
                "user_goal": "build decoupled architecture",
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
