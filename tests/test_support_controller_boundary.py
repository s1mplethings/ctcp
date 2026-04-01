from __future__ import annotations

import unittest

from scripts import ctcp_support_controller


class SupportControllerBoundaryTests(unittest.TestCase):
    def test_controller_waits_for_render_decision_card_not_legacy_status_flag(self) -> None:
        session_state: dict[str, object] = {}
        project_context = {
            "run_id": "r-decide",
            "status": {
                "needs_user_decision": True,
                "decisions_needed_count": 2,
                "gate": {"state": "blocked", "reason": "legacy status says blocked"},
            },
            "render_snapshot": {
                "visible_state": "EXECUTING",
                "ui_badge": "in_progress",
                "decision_cards": [],
                "progress_summary": "working",
            },
            "current_snapshot": {
                "authoritative_stage": "EXECUTE",
                "current_blocker": "none",
            },
            "result_event": {},
            "artifact_manifest": {},
            "output_artifacts": {"artifacts": []},
        }

        report = ctcp_support_controller.decide_and_queue(session_state, project_context=project_context, now_ts="2026-03-31T12:00:00Z")
        self.assertNotEqual(str(report.get("controller_state", "")), "WAIT_USER_DECISION")
        self.assertEqual(ctcp_support_controller.pop_outbound_jobs(session_state), [])

    def test_controller_decision_prompt_comes_from_render_snapshot(self) -> None:
        session_state: dict[str, object] = {}
        project_context = {
            "run_id": "r-decide",
            "render_snapshot": {
                "visible_state": "WAITING_FOR_DECISION",
                "ui_badge": "needs_decision",
                "decision_cards": [
                    {
                        "decision_id": "d-1",
                        "question": "先保速度还是先保质量？",
                        "status": "pending",
                    }
                ],
                "progress_summary": "need one user choice",
            },
            "current_snapshot": {
                "authoritative_stage": "WAIT_USER_DECISION",
                "current_blocker": "need one decision",
            },
            "output_artifacts": {"artifacts": []},
        }

        report = ctcp_support_controller.decide_and_queue(session_state, project_context=project_context, now_ts="2026-03-31T12:00:00Z")
        self.assertEqual(str(report.get("controller_state", "")), "WAIT_USER_DECISION")
        jobs = ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(str(jobs[0].get("kind", "")), "decision")
        self.assertIn("速度", str(jobs[0].get("decision_prompt", "")))

    def test_controller_result_requires_render_done_plus_payload(self) -> None:
        session_state: dict[str, object] = {}
        base_context = {
            "run_id": "r-result",
            "render_snapshot": {
                "visible_state": "DONE",
                "ui_badge": "done",
                "decision_cards": [],
                "progress_summary": "done",
            },
            "current_snapshot": {
                "authoritative_stage": "DELIVERED",
                "current_blocker": "none",
            },
            "output_artifacts": {"artifacts": []},
        }

        report_without_payload = ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=dict(base_context),
            now_ts="2026-03-31T12:00:00Z",
        )
        self.assertNotEqual(str(report_without_payload.get("controller_state", "")), "NOTIFY_RESULT")
        self.assertEqual(ctcp_support_controller.pop_outbound_jobs(session_state), [])

        with_payload = dict(base_context)
        with_payload["result_event"] = {"event_type": "event_result", "summary": "done"}
        report_with_payload = ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=with_payload,
            now_ts="2026-03-31T12:01:00Z",
        )
        self.assertEqual(str(report_with_payload.get("controller_state", "")), "NOTIFY_RESULT")
        jobs = ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(str(jobs[0].get("kind", "")), "result")


if __name__ == "__main__":
    unittest.main()
