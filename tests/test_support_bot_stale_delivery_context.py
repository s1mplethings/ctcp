from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.ctcp_support_bot as support_bot


class SupportBotStaleDeliveryContextTests(unittest.TestCase):
    def test_sync_project_context_new_create_turn_supersedes_completed_bound_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_new_create_supersedes_done_") as td:
            run_dir = Path(td)
            support_bot.ensure_layout(run_dir)
            session_state = support_bot.default_support_session_state("new-create-demo")
            session_state["bound_run_id"] = "old-vn-run"
            session_state["bound_run_dir"] = "D:/tmp/old-vn-run"
            session_state["project_memory"]["project_brief"] = "做一个本地可运行的 VN 项目助手"
            user_text = "你帮我做一个本地可运行的 VN 项目助手，可以梳理故事逻辑的时间线，可以生成背景，立绘"
            old_done_context = {
                "run_id": "old-vn-run",
                "run_dir": "D:/tmp/old-vn-run",
                "goal": "做一个本地可运行的 VN 项目助手",
                "status": {
                    "run_status": "completed",
                    "verify_result": "PASS",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "closed", "owner": "", "reason": ""},
                },
                "render_snapshot": {"visible_state": "DONE"},
                "whiteboard": {},
            }
            new_context = {
                "run_id": "new-vn-run",
                "run_dir": "D:/tmp/new-vn-run",
                "goal": user_text,
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "open", "owner": "", "reason": ""},
                },
                "whiteboard": {},
                "created": {"run_id": "new-vn-run", "run_dir": "D:/tmp/new-vn-run"},
                "recorded_turn": {"status": "recorded"},
                "advance": {"status": "advanced"},
            }

            with mock.patch.object(
                support_bot,
                "fetch_support_context_with_recovery",
                return_value=(old_done_context, False),
            ), mock.patch.object(
                support_bot,
                "maybe_recover_previous_outline_context",
                side_effect=lambda **kwargs: (kwargs["project_context"], kwargs["session_state"], None),
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_sync_support_project_turn",
                return_value=new_context,
            ) as sync_spy:
                project_context, updated_state = support_bot.sync_project_context(
                    run_dir=run_dir,
                    chat_id="new-create-demo",
                    user_text=user_text,
                    source="telegram",
                    conversation_mode="PROJECT_DETAIL",
                    session_state=session_state,
                )

            sync_spy.assert_called_once()
            sync_kwargs = dict(sync_spy.call_args.kwargs)
            self.assertEqual(str(sync_kwargs.get("run_id", "")), "")
            self.assertEqual(str(sync_kwargs.get("create_goal", "")), user_text)
            self.assertEqual(str(project_context.get("run_id", "")), "new-vn-run")
            self.assertEqual(str(updated_state.get("bound_run_id", "")), "new-vn-run")
            self.assertEqual(str(updated_state.get("bound_run_dir", "")), "D:/tmp/new-vn-run")
            self.assertEqual(str(updated_state.get("active_goal", "")), user_text)
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("SUPPORT_COMPLETED_RUN_SUPERSEDED_FOR_NEW_REQUEST", events)


if __name__ == "__main__":
    unittest.main()
