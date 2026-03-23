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
    def test_minimum_state_set_is_present(self) -> None:
        expected = {
            "Idle",
            "IntentDetect",
            "Collect",
            "Clarify",
            "Confirm",
            "Execute",
            "AwaitDecision",
            "ReturnResult",
            "InterruptRecover",
            "StyleAdjust",
            "Error",
        }
        self.assertEqual(set(FRONTDESK_STATES), expected)
        self.assertEqual(set(STATE_DEFINITIONS.keys()), expected)
        self.assertTrue({"style_change", "status_query", "result_query"}.issubset(set(INTERRUPT_KINDS)))

    def test_derive_frontdesk_state_enters_await_decision_when_run_needs_user_choice(self) -> None:
        session_state = {
            "task_summary": "继续优化 VN 前台",
            "bound_run_id": "run-vn",
            "session_profile": {"lang_hint": "zh"},
            "project_memory": {"project_brief": "继续优化 VN 前台"},
            "project_constraints_memory": {},
            "execution_memory": {},
            "frontdesk_state": {},
        }
        project_context = {
            "run_id": "run-vn",
            "goal": "继续优化 VN 前台",
            "status": {
                "run_status": "blocked",
                "verify_result": "",
                "needs_user_decision": True,
                "gate": {"reason": "请确认保留旧 UI 还是重做 UI"},
            },
            "decisions": {
                "decisions": [
                    {
                        "decision_id": "d-ui",
                        "question_hint": "这轮你要保留旧 UI，还是直接重做 UI？",
                    }
                ]
            },
        }

        state = derive_frontdesk_state(
            user_text="继续做这个项目",
            conversation_mode="PROJECT_DETAIL",
            session_state=session_state,
            project_context=project_context,
        )

        self.assertEqual(state["state"], "AwaitDecision")
        self.assertEqual(state["active_task_id"], "run-vn")
        self.assertIn("重做 UI", state["waiting_for"])
        self.assertEqual(len(list(state["decision_points"])), 1)

    def test_style_change_updates_profile_and_preserves_resumable_execute(self) -> None:
        session_state = {
            "task_summary": "继续优化 VN 前台",
            "bound_run_id": "run-vn",
            "session_profile": {"lang_hint": "zh"},
            "project_memory": {"project_brief": "继续优化 VN 前台"},
            "project_constraints_memory": {},
            "execution_memory": {},
            "frontdesk_state": {
                "state": "Execute",
                "current_goal": "继续优化 VN 前台",
                "active_task_id": "run-vn",
                "user_style_profile": {
                    "language": "auto",
                    "tone": "task_progressive",
                    "initiative": "balanced",
                    "verbosity": "normal",
                },
            },
        }
        project_context = {
            "run_id": "run-vn",
            "goal": "继续优化 VN 前台",
            "status": {
                "run_status": "running",
                "verify_result": "",
                "needs_user_decision": False,
                "gate": {"reason": ""},
            },
        }

        state = derive_frontdesk_state(
            user_text="后面用中文回答，简短一点，别太机械",
            conversation_mode="SMALLTALK",
            session_state=session_state,
            project_context=project_context,
        )

        self.assertEqual(state["state"], "StyleAdjust")
        self.assertEqual(state["interrupt_kind"], "style_change")
        self.assertEqual(state["resumable_state"], "Execute")
        profile = dict(state["user_style_profile"])
        self.assertEqual(profile.get("language"), "zh")
        self.assertEqual(profile.get("verbosity"), "brief")
        self.assertEqual(profile.get("tone"), "natural")

    def test_reply_strategy_hides_project_context_for_greeting_interrupt(self) -> None:
        strategy = reply_strategy_from_frontdesk_state(
            {
                "state": "InterruptRecover",
                "active_task_id": "run-vn",
                "current_goal": "继续优化 VN 前台",
                "interrupt_kind": "",
            },
            conversation_mode="GREETING",
        )

        self.assertFalse(bool(strategy["allow_existing_project_reference"]))
        self.assertTrue(bool(strategy["latest_turn_only"]))

    def test_reply_strategy_prefers_progress_binding_for_status_interrupt(self) -> None:
        strategy = reply_strategy_from_frontdesk_state(
            {
                "state": "InterruptRecover",
                "active_task_id": "run-vn",
                "current_goal": "继续优化 VN 前台",
                "interrupt_kind": "status_query",
            },
            conversation_mode="STATUS_QUERY",
        )

        self.assertTrue(bool(strategy["allow_existing_project_reference"]))
        self.assertTrue(bool(strategy["prefer_frontend_render"]))
        self.assertTrue(bool(strategy["prefer_progress_binding"]))

    def test_prompt_context_omits_task_slots_when_project_reference_is_not_allowed(self) -> None:
        context = prompt_context_from_frontdesk_state(
            {
                "state": "StyleAdjust",
                "interrupt_kind": "style_change",
                "current_goal": "继续优化 VN 前台",
                "current_scope": "先收紧前台状态机",
                "active_task_id": "run-vn",
                "resumable_state": "Execute",
                "user_style_profile": {
                    "language": "zh",
                    "tone": "natural",
                    "initiative": "balanced",
                    "verbosity": "brief",
                },
            },
            include_task_context=False,
        )

        self.assertEqual(context["state"], "StyleAdjust")
        self.assertEqual(context["current_goal"], "")
        self.assertEqual(context["active_task_id"], "")
        self.assertEqual(dict(context["user_style_profile"])["verbosity"], "brief")
        self.assertEqual(context["resumable_state"], "Execute")


if __name__ == "__main__":
    unittest.main()
