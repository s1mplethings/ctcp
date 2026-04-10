from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.ctcp_support_bot as support_bot


def _append_jsonl(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


class SupportSessionRecoveryRegressionTests(unittest.TestCase):
    def test_build_final_reply_doc_project_detail_internal_block_is_not_rendered_as_user_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_project_detail_internal_block_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "做一个本地可运行的 VN 项目助手 MVP",
                },
            )
            project_context = {
                "run_id": "r-plan-retry",
                "goal": "做一个本地可运行的 VN 项目助手 MVP",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                },
                "runtime_state": {
                    "phase": "RECOVER",
                    "run_status": "running",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                    "recovery": {
                        "needed": True,
                        "hint": "补齐 PLAN_draft.md 并继续推进方案整理",
                        "status": "retry_ready",
                    },
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "当前遇到内部阻塞，确认这条输入后我可以继续。",
                    "next_question": "",
                    "actions": [],
                    "debug_notes": "",
                },
                project_context=project_context,
                conversation_mode="PROJECT_DETAIL",
                task_summary_hint="做一个本地可运行的 VN 项目助手 MVP",
                lang_hint="zh",
                frontdesk_state={
                    "state": "showing_error",
                    "blocked_reason": "waiting for PLAN_draft.md",
                    "next_action": "补齐 PLAN_draft.md 并继续推进方案整理",
                },
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("PLAN_draft.md", reply)
            self.assertIn("补齐 PLAN_draft.md", reply)
            self.assertNotIn("确认这条输入后我可以继续", reply)

    def test_build_final_reply_doc_status_query_surfaces_plan_recovery_hint_not_generic_continue(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_plan_recovery_status_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "现在做到什么程度了",
                },
            )
            project_context = {
                "run_id": "r-plan-retry",
                "goal": "我想要你继续优化我的剧情项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                },
                "runtime_state": {
                    "phase": "RECOVER",
                    "run_status": "running",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                    "recovery": {
                        "needed": True,
                        "hint": "retry planner to generate PLAN_draft.md",
                        "status": "retry_ready",
                    },
                },
                "support_recovery": {
                    "needed": True,
                    "hint": "已重试一次方案整理；接下来继续补齐 PLAN_draft.md，若仍缺失就转入明确恢复状态",
                    "status": "retrying",
                    "last_attempt": "已重试一次方案整理",
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }

            doc = support_bot.build_grounded_status_reply_doc(
                run_dir=run_dir,
                session_state=support_bot.default_support_session_state("plan-retry"),
                project_context=project_context,
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("方案整理", reply)
            self.assertIn("已重试一次方案整理", reply)
            self.assertIn("PLAN_draft.md", reply)
            self.assertNotEqual(reply.strip(), "收到，我会继续推进。")

    def test_build_grounded_status_reply_doc_surfaces_watchdog_retry_count_and_next_recovery_action(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_watchdog_status_") as td:
            run_dir = Path(td)
            session_state = support_bot.default_support_session_state("watchdog-status")
            project_context = {
                "run_id": "r-watchdog",
                "goal": "做一个本地可运行的预算记录项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                        "retry_count": 1,
                        "max_retries": 2,
                        "expected_artifact": "artifacts/PLAN_draft.md",
                        "recovery_action": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                        "watchdog_status": "retrying",
                    },
                },
                "runtime_state": {
                    "phase": "RETRYING",
                    "run_status": "running",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                        "retry_count": 1,
                        "max_retries": 2,
                        "expected_artifact": "artifacts/PLAN_draft.md",
                        "recovery_action": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                        "watchdog_status": "retrying",
                    },
                    "recovery": {
                        "needed": True,
                        "hint": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                        "status": "retrying",
                        "retry_count": 1,
                        "max_retries": 2,
                        "expected_artifact": "artifacts/PLAN_draft.md",
                        "recovery_action": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                        "last_attempt": "已自动重试 1/2 次，目标仍是 PLAN_draft.md",
                    },
                },
                "support_recovery": {
                    "needed": True,
                    "hint": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                    "status": "retrying",
                    "retry_count": 1,
                    "max_retries": 2,
                    "expected_artifact": "artifacts/PLAN_draft.md",
                    "recovery_action": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                    "last_attempt": "已自动重试 1/2 次，目标仍是 PLAN_draft.md",
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }

            doc = support_bot.build_grounded_status_reply_doc(
                run_dir=run_dir,
                session_state=session_state,
                project_context=project_context,
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("已自动重试 1/2 次", reply)
            self.assertIn("PLAN_draft.md", reply)
            self.assertIn("retry planner", reply)
            self.assertNotEqual(reply.strip(), "收到，我会继续推进。")

    def test_build_grounded_status_reply_doc_surfaces_invalid_source_generation_report_blocker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_source_generation_block_") as td:
            run_dir = Path(td)
            session_state = support_bot.default_support_session_state("source-generation-block")
            project_context = {
                "run_id": "r-source-invalid",
                "goal": "做一个本地可运行的 VN 项目助手 MVP",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/source_generation_report.json",
                        "reason": "generic_validation.passed must be true",
                        "expected_artifact": "artifacts/source_generation_report.json",
                        "expected_exists": True,
                        "recovery_action": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                        "watchdog_status": "blocked_hard",
                    },
                },
                "runtime_state": {
                    "phase": "BLOCKED_HARD",
                    "run_status": "running",
                    "blocking_reason": "generic_validation.passed must be true",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/source_generation_report.json",
                        "reason": "generic_validation.passed must be true",
                        "expected_artifact": "artifacts/source_generation_report.json",
                        "expected_exists": True,
                        "recovery_action": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                        "watchdog_status": "blocked_hard",
                    },
                    "recovery": {
                        "needed": True,
                        "hint": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                        "status": "blocked_hard",
                        "expected_artifact": "artifacts/source_generation_report.json",
                        "recovery_action": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                    },
                },
                "support_recovery": {
                    "needed": True,
                    "hint": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                    "status": "blocked_hard",
                    "expected_artifact": "artifacts/source_generation_report.json",
                    "recovery_action": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }

            doc = support_bot.build_grounded_status_reply_doc(
                run_dir=run_dir,
                session_state=session_state,
                project_context=project_context,
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("source_generation_report.json", reply)
            self.assertIn("generic_validation.passed must be true", reply)
            self.assertIn("repair invalid generated sources", reply)
            self.assertNotEqual(reply.strip(), "收到，我会继续推进。")

    def test_sync_project_context_rebinds_stale_run_from_saved_goal_instead_of_confirmation_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_stale_rebind_") as td:
            run_dir = Path(td)
            support_bot.ensure_layout(run_dir)
            session_state = support_bot.default_support_session_state("stale-rebind")
            session_state["bound_run_id"] = "stale-run"
            session_state["bound_run_dir"] = "D:/tmp/stale-run"
            session_state["project_memory"]["project_brief"] = "我想要你继续优化我的剧情项目"
            session_state["task_summary"] = "我想要你继续优化我的剧情项目"

            new_run_calls: list[str] = []

            def _fake_new_run(*, goal: str) -> dict[str, object]:
                new_run_calls.append(goal)
                return {"run_id": "new-story-run", "run_dir": "D:/tmp/new-story-run"}

            def _fake_get_support_context(run_id: str) -> dict[str, object]:
                if run_id == "stale-run":
                    raise RuntimeError("run_id not found: stale-run")
                return {
                    "run_id": run_id,
                    "run_dir": "D:/tmp/new-story-run",
                    "goal": "我想要你继续优化我的剧情项目",
                    "status": {
                        "run_status": "running",
                        "verify_result": "",
                        "needs_user_decision": False,
                        "decisions_needed_count": 0,
                        "gate": {"state": "open", "owner": "", "reason": ""},
                    },
                    "runtime_state": {
                        "phase": "EXECUTE",
                        "run_status": "running",
                        "blocking_reason": "none",
                        "needs_user_decision": False,
                        "decisions_needed_count": 0,
                        "gate": {"state": "open", "owner": "", "reason": ""},
                        "recovery": {"needed": False, "hint": "", "status": "none"},
                    },
                    "decisions": {"count": 0, "decisions": []},
                    "whiteboard": {},
                }

            with mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_new_run",
                side_effect=_fake_new_run,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                side_effect=_fake_get_support_context,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_record_support_turn",
                return_value={"ok": True},
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ):
                project_context, updated_state = support_bot.sync_project_context(
                    run_dir=run_dir,
                    chat_id="stale-rebind",
                    user_text="确定",
                    source="telegram",
                    conversation_mode="PROJECT_DETAIL",
                    session_state=session_state,
                )

            self.assertEqual(new_run_calls, ["我想要你继续优化我的剧情项目"])
            self.assertEqual(str(updated_state.get("bound_run_id", "")), "new-story-run")
            self.assertEqual(str(project_context.get("goal", "")), "我想要你继续优化我的剧情项目")
            self.assertNotEqual(str(project_context.get("goal", "")), "确定")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("SUPPORT_STALE_RUN_RECOVERED", events)

    def test_sync_project_context_confirmation_with_bound_run_reuses_existing_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_confirm_reuse_") as td:
            run_dir = Path(td)
            support_bot.ensure_layout(run_dir)
            session_state = support_bot.default_support_session_state("confirm-reuse")
            session_state["bound_run_id"] = "run-existing"
            session_state["bound_run_dir"] = "D:/tmp/run-existing"
            session_state["project_memory"]["project_brief"] = "我想要你继续优化我的剧情项目"

            project_context_doc = {
                "run_id": "run-existing",
                "run_dir": "D:/tmp/run-existing",
                "goal": "我想要你继续优化我的剧情项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "open", "owner": "", "reason": ""},
                },
                "runtime_state": {
                    "phase": "EXECUTE",
                    "run_status": "running",
                    "blocking_reason": "none",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "open", "owner": "", "reason": ""},
                    "recovery": {"needed": False, "hint": "", "status": "none"},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }

            with mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_new_run",
            ) as new_run_spy, mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                return_value=project_context_doc,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_record_support_turn",
                return_value={"ok": True},
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ) as advance_spy:
                project_context, updated_state = support_bot.sync_project_context(
                    run_dir=run_dir,
                    chat_id="confirm-reuse",
                    user_text="确定",
                    source="telegram",
                    conversation_mode="PROJECT_DETAIL",
                    session_state=session_state,
                )

            new_run_spy.assert_not_called()
            advance_spy.assert_called_once_with("run-existing", max_steps=1)
            self.assertEqual(str(updated_state.get("bound_run_id", "")), "run-existing")
            self.assertEqual(str(project_context.get("run_id", "")), "run-existing")

    def test_sync_project_context_continue_advances_current_run_not_new_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_continue_existing_") as td:
            run_dir = Path(td)
            support_bot.ensure_layout(run_dir)
            session_state = support_bot.default_support_session_state("continue-existing")
            session_state["bound_run_id"] = "run-existing"
            session_state["bound_run_dir"] = "D:/tmp/run-existing"
            session_state["project_memory"]["project_brief"] = "我想要你继续优化我的剧情项目"

            blocked_context = {
                "run_id": "run-existing",
                "run_dir": "D:/tmp/run-existing",
                "goal": "我想要你继续优化我的剧情项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                },
                "runtime_state": {
                    "phase": "RECOVER",
                    "run_status": "running",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                    "recovery": {
                        "needed": True,
                        "hint": "retry planner to generate PLAN_draft.md",
                        "status": "retry_ready",
                    },
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }

            with mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_new_run",
            ) as new_run_spy, mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                return_value=blocked_context,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_record_support_turn",
                return_value={"ok": True},
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ) as advance_spy:
                project_context, updated_state = support_bot.sync_project_context(
                    run_dir=run_dir,
                    chat_id="continue-existing",
                    user_text="继续",
                    source="telegram",
                    conversation_mode="PROJECT_DETAIL",
                    session_state=session_state,
                )

            new_run_spy.assert_not_called()
            advance_spy.assert_called_once_with("run-existing", max_steps=1)
            self.assertEqual(str(updated_state.get("bound_run_id", "")), "run-existing")
            self.assertEqual(str(project_context.get("run_id", "")), "run-existing")


if __name__ == "__main__":
    unittest.main()
