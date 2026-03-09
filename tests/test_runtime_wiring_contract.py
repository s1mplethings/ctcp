from __future__ import annotations

import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_front_api
from frontend.response_composer import render_frontend_output
from tools.telegram_cs_bot import Bot, Config


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "triplet_guard" / "runtime_wiring_cases.json"


def _make_bot(base: Path) -> Bot:
    cfg = Config(
        token="fake",
        allowlist=None,
        repo_root=ROOT.resolve(),
        state_db=base / "state.sqlite3",
        poll_seconds=1,
        tick_seconds=1,
        auto_advance=False,
        api_enabled=False,
        api_model="gpt-4.1-mini",
        api_timeout_sec=10,
        note_ack_path=False,
        progress_push_enabled=False,
    )
    return Bot(cfg)


class RuntimeWiringContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_greeting_only_does_not_enter_project_planning_pipeline(self) -> None:
        greeting = str(self.fixture.get("greeting_input", "你好"))
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_provider_failed",
                "blocked_needs_input": True,
                "needs_input": True,
                "missing_fields": ["runtime_target"],
            },
            task_summary=greeting,
            raw_reply_text="plan agent command failed rc=2",
            raw_next_question="这轮你希望我优先速度、质量，还是成本？",
            notes={
                "lang": "zh",
                "recent_user_messages": [greeting],
            },
        )
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "GREETING")
        self.assertEqual(result.followup_questions, ())
        self.assertEqual(str(state.get("selected_requirement_source", "")), "")
        self.assertNotIn("速度、质量", result.reply_text)
        self.assertNotIn("内部处理异常", result.reply_text)
        self.assertFalse(any(tok in result.reply_text for tok in ("CONTEXT", "PLAN", "PATCH")))
        self.assertTrue(
            any(tok in result.reply_text for tok in ("你好", "请问有什么可以帮到你", "我在")),
            msg=result.reply_text,
        )

    def test_detailed_project_request_enters_project_manager_mode(self) -> None:
        request = str(self.fixture.get("detailed_project_request", "")).strip()
        result = render_frontend_output(
            raw_backend_state={
                "stage": "analysis",
                "has_actionable_goal": True,
                "first_pass_understood": True,
                "needs_input": True,
                "missing_fields": ["input_mode", "runtime_target"],
            },
            task_summary=request,
            raw_reply_text="",
            raw_next_question="请提供更多信息",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想做个项目", request],
            },
        )
        state = dict(result.pipeline_state or {})
        mode = str(state.get("conversation_mode", ""))
        self.assertIn(mode, {"PROJECT_INTAKE", "PROJECT_DETAIL"}, msg=mode)
        self.assertGreaterEqual(len(result.followup_questions), 1)
        self.assertLessEqual(len(result.followup_questions), 2)
        self.assertIn("无人机", result.reply_text)
        self.assertIn("点云", result.reply_text)
        self.assertNotIn("请提供更多信息", result.reply_text)
        self.assertNotIn("什么类型的项目", result.reply_text)
        self.assertFalse(any("什么类型的项目" in q for q in result.followup_questions), msg=result.followup_questions)

    def test_frontend_new_run_path_calls_bridge_entrypoint(self) -> None:
        args = argparse.Namespace(
            goal="build a support bot project",
            constraints_json='{"priority":"speed"}',
            attachment=["artifacts/request.txt"],
        )
        with mock.patch.object(ctcp_front_api, "ctcp_new_run", return_value={"run_id": "r-demo"}) as bridge_spy:
            with mock.patch.object(ctcp_front_api, "_ok", return_value=0) as ok_spy:
                rc = ctcp_front_api._cmd_new_run(args)
        self.assertEqual(rc, 0)
        bridge_spy.assert_called_once_with(
            goal="build a support bot project",
            constraints={"priority": "speed"},
            attachments=["artifacts/request.txt"],
        )
        ok_spy.assert_called_once()

    def test_frontend_status_path_calls_bridge_entrypoint(self) -> None:
        args = argparse.Namespace(run_id="r-demo")
        with mock.patch.object(ctcp_front_api, "ctcp_get_status", return_value={"run_id": "r-demo"}) as bridge_spy:
            with mock.patch.object(ctcp_front_api, "_ok", return_value=0) as ok_spy:
                rc = ctcp_front_api._cmd_get_status(args)
        self.assertEqual(rc, 0)
        bridge_spy.assert_called_once_with("r-demo")
        ok_spy.assert_called_once()

    def test_frontend_advance_path_calls_bridge_entrypoint(self) -> None:
        args = argparse.Namespace(run_id="r-demo", max_steps=3)
        with mock.patch.object(ctcp_front_api, "ctcp_advance", return_value={"run_id": "r-demo"}) as bridge_spy:
            with mock.patch.object(ctcp_front_api, "_ok", return_value=0) as ok_spy:
                rc = ctcp_front_api._cmd_advance(args)
        self.assertEqual(rc, 0)
        bridge_spy.assert_called_once_with("r-demo", max_steps=3)
        ok_spy.assert_called_once()

    def test_telegram_new_run_and_advance_use_bridge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_bridge_") as td:
            base = Path(td)
            run_dir = base / "ctcp" / "r-demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            bot = _make_bot(base)
            try:
                with mock.patch("tools.telegram_cs_bot.bridge_ctcp_new_run", return_value={"run_id": "r-demo", "run_dir": str(run_dir), "status": {"run_status": "running", "gate": {"state": "running"}}}) as new_run_spy, mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_advance",
                    return_value={"run_id": "r-demo", "status": {"run_status": "running", "gate": {"state": "blocked", "owner": "chair", "path": "artifacts/PLAN_draft.md", "reason": "waiting plan_draft"}}},
                ) as advance_spy, mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_get_status",
                    return_value={"run_id": "r-demo", "run_status": "running", "gate": {"state": "running"}, "iterations": {"current": 1}},
                ), mock.patch("tools.telegram_cs_bot.bridge_ctcp_get_last_report", return_value={}), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_list_decisions_needed",
                    return_value={"run_id": "r-demo", "count": 0, "decisions": []},
                ), mock.patch("tools.telegram_cs_bot.bridge_ctcp_submit_decision", return_value={}), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_upload_artifact",
                    return_value={},
                ):
                    rc_new, out_new, _err_new = bot._run_orchestrate(["new-run", "--goal", "build support flow"])
                    rc_adv, out_adv, _err_adv = bot._run_orchestrate(["advance", "--max-steps", "2", "--run-dir", str(run_dir)])

                self.assertEqual(rc_new, 0)
                self.assertIn("run_dir=", out_new)
                self.assertEqual(rc_adv, 0)
                self.assertIn("next=blocked", out_adv)
                new_run_spy.assert_called_once_with(goal="build support flow", constraints={}, attachments=[])
                advance_spy.assert_called_once_with("r-demo", max_steps=2)
            finally:
                bot.close()

    def test_telegram_decision_write_uses_bridge_submit(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_decision_") as td:
            base = Path(td)
            run_dir = base / "ctcp" / "r-demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            bot = _make_bot(base)
            try:
                with mock.patch("tools.telegram_cs_bot.bridge_ctcp_new_run", return_value={}), mock.patch("tools.telegram_cs_bot.bridge_ctcp_advance", return_value={}), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_get_status",
                    return_value={"run_status": "running"},
                ), mock.patch("tools.telegram_cs_bot.bridge_ctcp_get_last_report", return_value={}), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_list_decisions_needed",
                    return_value={"count": 1, "decisions": [{"decision_id": "outbox:q1", "prompt_path": "outbox/Q1.md", "target_path": "artifacts/answers/Q1.md"}]},
                ), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_submit_decision",
                    return_value={"written": True},
                ) as submit_spy, mock.patch("tools.telegram_cs_bot.bridge_ctcp_upload_artifact", return_value={}):
                    mapping = {
                        "run_dir": str(run_dir),
                        "target_path": "artifacts/answers/Q1.md",
                        "prompt_path": "outbox/Q1.md",
                        "prompt_msg_id": 1,
                    }
                    bot._send_customer_reply = mock.Mock(return_value={"reply_text": "ok"})  # type: ignore[method-assign]
                    bot._write_reply(chat_id=123, lang="zh", mapping=mapping, text="确认这个选项", file_id=None)

                submit_spy.assert_called_once()
                args = submit_spy.call_args.args
                self.assertEqual(args[0], "r-demo")
                payload = submit_spy.call_args.args[1]
                self.assertEqual(str(payload.get("prompt_path", "")), "outbox/Q1.md")
                self.assertEqual(str(payload.get("target_path", "")), "artifacts/answers/Q1.md")
                self.assertIn("确认这个选项", str(payload.get("content", "")))
            finally:
                bot.close()

    def test_telegram_status_query_uses_bridge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_status_") as td:
            base = Path(td)
            run_dir = base / "ctcp" / "r-demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "failed"}), encoding="utf-8")
            bot = _make_bot(base)
            try:
                with mock.patch("tools.telegram_cs_bot.bridge_ctcp_new_run", return_value={}), mock.patch("tools.telegram_cs_bot.bridge_ctcp_advance", return_value={}), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_get_status",
                    return_value={"run_status": "running", "gate": {"state": "running"}},
                ) as status_spy, mock.patch("tools.telegram_cs_bot.bridge_ctcp_get_last_report", return_value={}), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_list_decisions_needed",
                    return_value={"count": 0, "decisions": []},
                ), mock.patch("tools.telegram_cs_bot.bridge_ctcp_submit_decision", return_value={}), mock.patch(
                    "tools.telegram_cs_bot.bridge_ctcp_upload_artifact",
                    return_value={},
                ):
                    status = bot._run_status(run_dir)
                self.assertEqual(status, "running")
                status_spy.assert_called_once_with("r-demo")
            finally:
                bot.close()


if __name__ == "__main__":
    unittest.main()
