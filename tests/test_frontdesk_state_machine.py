from __future__ import annotations

import unittest

from frontend.frontdesk_state_machine import (
    FRONTDESK_STATES,
    INTERRUPT_KINDS,
    STATE_DEFINITIONS,
    derive_frontdesk_state,
    prompt_context_from_frontdesk_state,
    reply_strategy_from_frontdesk_state,
)


class FrontdeskStateMachineTests(unittest.TestCase):
    def test_display_state_set_is_render_only(self) -> None:
        expected = {
            "idle",
            "collecting_input",
            "showing_progress",
            "waiting_user_reply",
            "showing_decision",
            "showing_result",
            "showing_error",
        }
        self.assertEqual(set(FRONTDESK_STATES), expected)
        self.assertEqual(set(STATE_DEFINITIONS.keys()), expected)
        self.assertTrue({"style_change", "status_query", "result_query"}.issubset(set(INTERRUPT_KINDS)))

    def test_render_only_progress_ignores_legacy_status_guess(self) -> None:
        session_state = {
            "task_summary": "继续推进项目",
            "bound_run_id": "run-render",
            "session_profile": {"lang_hint": "zh"},
            "project_memory": {"project_brief": "继续推进项目"},
            "project_constraints_memory": {},
            "execution_memory": {},
            "frontdesk_state": {},
        }
        project_context = {
            "run_id": "run-render",
            "status": {
                "run_status": "completed",
                "verify_result": "PASS",
                "needs_user_decision": True,
                "decisions_needed_count": 1,
            },
            "render_snapshot": {
                "visible_state": "EXECUTING",
                "ui_badge": "in_progress",
                "progress_summary": "backend executing",
                "decision_cards": [],
            },
            "current_snapshot": {
                "authoritative_stage": "EXECUTE",
                "current_blocker": "none",
            },
        }

        state = derive_frontdesk_state(
            user_text="继续做",
            conversation_mode="PROJECT_DETAIL",
            session_state=session_state,
            project_context=project_context,
        )

        self.assertEqual(state["state"], "showing_progress")
        self.assertNotEqual(state["state"], "showing_result")
        self.assertNotEqual(state["state"], "showing_decision")

    def test_decision_flow_comes_from_render_or_decision_interface(self) -> None:
        session_state = {
            "task_summary": "继续推进项目",
            "bound_run_id": "run-decision",
            "session_profile": {"lang_hint": "zh"},
            "project_memory": {"project_brief": "继续推进项目"},
            "project_constraints_memory": {},
            "execution_memory": {},
            "frontdesk_state": {},
        }
        project_context = {
            "run_id": "run-decision",
            "render_snapshot": {
                "visible_state": "WAITING_FOR_DECISION",
                "ui_badge": "needs_decision",
                "progress_summary": "waiting for one user choice",
                "decision_cards": [
                    {
                        "decision_id": "d-ui",
                        "question": "这轮先保速度还是先保质量？",
                        "status": "pending",
                    }
                ],
            },
            "current_snapshot": {
                "authoritative_stage": "WAIT_USER_DECISION",
                "current_blocker": "need one decision",
            },
        }

        state = derive_frontdesk_state(
            user_text="继续",
            conversation_mode="PROJECT_DETAIL",
            session_state=session_state,
            project_context=project_context,
        )

        self.assertEqual(state["state"], "showing_decision")
        self.assertIn("保速度", state["waiting_for"])
        self.assertEqual(len(list(state["decision_points"])), 1)

    def test_done_requires_render_done_and_result_payload(self) -> None:
        session_state = {
            "task_summary": "继续推进项目",
            "bound_run_id": "run-done",
            "session_profile": {"lang_hint": "zh"},
            "project_memory": {"project_brief": "继续推进项目"},
            "project_constraints_memory": {},
            "execution_memory": {},
            "frontdesk_state": {},
        }
        base = {
            "run_id": "run-done",
            "render_snapshot": {
                "visible_state": "DONE",
                "ui_badge": "done",
                "progress_summary": "done",
                "decision_cards": [],
            },
            "current_snapshot": {
                "authoritative_stage": "DELIVERED",
                "current_blocker": "none",
            },
        }

        without_payload = derive_frontdesk_state(
            user_text="结果给我",
            conversation_mode="STATUS_QUERY",
            session_state=session_state,
            project_context=dict(base),
        )
        self.assertEqual(without_payload["state"], "showing_progress")

        with_payload_context = dict(base)
        with_payload_context["result_event"] = {"event_type": "event_result", "summary": "done"}
        with_payload = derive_frontdesk_state(
            user_text="结果给我",
            conversation_mode="STATUS_QUERY",
            session_state=session_state,
            project_context=with_payload_context,
        )
        self.assertEqual(with_payload["state"], "showing_result")

    def test_prompt_context_respects_include_task_context_flag(self) -> None:
        context = prompt_context_from_frontdesk_state(
            {
                "state": "showing_result",
                "interrupt_kind": "result_query",
                "current_goal": "继续推进剧情前台",
                "current_scope": "收敛前后台边界",
                "active_task_id": "run-story",
                "resumable_state": "showing_progress",
                "user_style_profile": {
                    "language": "zh",
                    "tone": "natural",
                    "initiative": "balanced",
                    "verbosity": "brief",
                },
            },
            include_task_context=False,
        )
        self.assertEqual(context["state"], "showing_result")
        self.assertEqual(context["current_goal"], "")
        self.assertEqual(context["active_task_id"], "")

    def test_reply_strategy_prefers_render_progress_binding_on_status_query(self) -> None:
        strategy = reply_strategy_from_frontdesk_state(
            {
                "state": "showing_progress",
                "active_task_id": "run-story",
                "current_goal": "继续推进剧情前台",
                "interrupt_kind": "status_query",
            },
            conversation_mode="STATUS_QUERY",
        )
        self.assertTrue(bool(strategy["allow_existing_project_reference"]))
        self.assertTrue(bool(strategy["prefer_frontend_render"]))
        self.assertTrue(bool(strategy["prefer_progress_binding"]))
        self.assertFalse(bool(strategy["allow_code_output"]))

    def test_code_request_sets_allow_code_output_flag(self) -> None:
        state = derive_frontdesk_state(
            user_text="给我贴一段完整代码",
            conversation_mode="PROJECT_DETAIL",
            session_state={
                "task_summary": "继续推进项目",
                "bound_run_id": "run-code",
                "session_profile": {"lang_hint": "zh"},
                "project_memory": {"project_brief": "继续推进项目"},
                "project_constraints_memory": {},
                "execution_memory": {},
                "frontdesk_state": {},
            },
            project_context={
                "run_id": "run-code",
                "render_snapshot": {"visible_state": "EXECUTING", "ui_badge": "in_progress", "decision_cards": []},
                "current_snapshot": {"authoritative_stage": "EXECUTE", "current_blocker": "none"},
            },
        )

        self.assertEqual(str(state.get("interrupt_kind", "")), "code_request")
        self.assertTrue(bool(state.get("allow_code_output", False)))
        strategy = reply_strategy_from_frontdesk_state(state, conversation_mode="PROJECT_DETAIL")
        self.assertTrue(bool(strategy.get("allow_code_output", False)))


if __name__ == "__main__":
    unittest.main()

