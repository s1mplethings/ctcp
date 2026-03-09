import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from tools.telegram_cs_bot import (
    _humanize_trace_delta,
    _role_switch_ack,
    ApiDecision,
    Bot,
    Config,
    build_user_reply_payload,
    build_employee_note_reply,
    describe_artifact_for_customer,
)


class _FakeTg:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, *, chat_id, text, reply_to=None, markup=None):
        self.messages.append(str(text))
        return {"message_id": len(self.messages)}

    def send_doc(self, *, chat_id, path, caption="", reply_to=None):
        self.messages.append(f"[DOC] {caption}")
        return {"message_id": len(self.messages)}

    def edit(self, *, chat_id, msg_id, text):
        self.messages.append(str(text))

    def answer_cb(self, cb_id, text=""):
        self.messages.append(str(text))


class TelegramCsBotEmployeeStyleTests(unittest.TestCase):
    def test_zh_reply_enters_execution_when_goal_is_actionable(self) -> None:
        text = "我需要一个非常像真实员工的客服bot"
        out = build_employee_note_reply(text, "zh")
        # New behaviour: natural conversational output, no section labels.
        self.assertNotIn("结论：", out)
        self.assertNotIn("方案：", out)
        self.assertNotIn("下一步：", out)
        self.assertIn("客服bot", out)  # brief is echoed back
        # Customer-facing: asks for more detail rather than project-style follow-ups
        self.assertNotIn("渠道", out)
        self.assertNotIn("转人工", out)
        self.assertNotIn("FAQ", out)
        self.assertNotIn("收到，了解你想咨询的是", out)
        self.assertIn("目标很清晰", out)
        self.assertIn("直接进入处理", out)
        self.assertNotIn("现有项目延续 / 新需求 / 报错排查", out)

    def test_zh_reply_keeps_lane_question_for_ambiguous_request(self) -> None:
        out = build_employee_note_reply("帮我处理一下", "zh")
        self.assertIn("现有项目延续 / 新需求 / 报错排查", out)

    def test_team_manager_mode_reply_is_manager_style(self) -> None:
        out = build_employee_note_reply(
            "我想做一个无人机视角的高速建图工作流",
            "zh",
            collab_role="team_manager",
        )
        self.assertIn("团队经理", out)
        self.assertIn("里程碑", out)
        self.assertNotIn("现有项目延续 / 新需求 / 报错排查", out)

    def test_team_manager_mode_asks_single_priority_when_ambiguous(self) -> None:
        out = build_employee_note_reply("帮我处理一下", "zh", collab_role="team_manager")
        self.assertIn("唯一最高优先级", out)
        self.assertIn("速度 / 质量 / 成本", out)

    def test_role_switch_ack_team_manager(self) -> None:
        reply, question = _role_switch_ack("zh", "team_manager")
        self.assertIn("团队经理模式", reply)
        self.assertIn("最高优先级", question)

    def test_en_reply_does_not_force_followup_when_context_is_complete(self) -> None:
        text = (
            "Build a customer support bot for Telegram with human handoff and "
            "FAQ knowledge base import."
        )
        out = build_employee_note_reply(text, "en")
        # New behaviour: natural conversational output, no section labels.
        self.assertNotIn("Conclusion:", out)
        self.assertNotIn("Plan:", out)
        self.assertNotIn("Next:", out)
        # Customer-facing: provides a helpful acknowledgement
        self.assertIn("Got it", out)

    def test_continuation_note_reply_is_not_generic_chitchat(self) -> None:
        text = "你现在手头还有我的项目吗"
        out = build_employee_note_reply(text, "zh")
        self.assertIn("继续", out)
        self.assertNotIn("方便的话再补充一些细节", out)
        self.assertNotIn("接着聊", out)

    def test_trace_delta_customer_summary_zh(self) -> None:
        delta = "\n".join(
            [
                "- 2026-03-01T20:40:00 | Local Orchestrator: VERIFY_STARTED (artifacts/verify_report.json)",
                "- 2026-03-01T20:40:10 | Contract_Guardian: LOCAL_EXEC_COMPLETED (reviews/review_contract.md)",
                "- 2026-03-01T20:40:20 | Local Verifier: LOCAL_EXEC_FAILED (artifacts/verify_report.json)",
            ]
        )
        out = _humanize_trace_delta(delta, "zh")
        # New behaviour: no section labels, natural prose.
        self.assertNotIn("结论：", out)
        self.assertNotIn("方案：", out)
        self.assertNotIn("下一步：", out)
        self.assertTrue(len(out) > 10)  # not empty

    def test_artifact_description_is_customer_friendly(self) -> None:
        self.assertEqual(describe_artifact_for_customer("artifacts/PLAN_draft.md", "zh"), "项目方案草稿")
        self.assertEqual(
            describe_artifact_for_customer("artifacts/verify_report.json", "en"),
            "verification report",
        )

    def test_reply_payload_sanitizes_internal_tokens_and_keeps_ops(self) -> None:
        mixed = "\n".join(
            [
                "进展更新：guardrails_written（guardrails.md）",
                "进展更新：run_created（RUN.json）",
                "结论：已推进",
                "方案：继续",
                "下一步：请确认 `RUN.json`",
            ]
        )
        payload = build_user_reply_payload(
            reply_text=mixed,
            next_question="是否继续？",
            lang="zh",
            ops_status={"event_key": "guardrails_written"},
        )
        reply = str(payload["reply_text"])
        self.assertNotIn("guardrails_written", reply)
        self.assertNotIn("RUN.json", reply)
        self.assertNotIn("guardrails", reply.lower())
        # Section labels are stripped; only the content value remains.
        self.assertNotIn("结论：", reply)
        self.assertIn("已推进", reply)
        self.assertIn("是否继续？", reply)  # question appended naturally
        ops = payload.get("ops_status", {})
        self.assertEqual(ops.get("event_key"), "guardrails_written")
        self.assertTrue(isinstance(ops.get("removed_internal_lines"), list))

    def test_reply_payload_uses_extracted_question_without_telegram_default(self) -> None:
        payload = build_user_reply_payload(
            reply_text="请问你希望输出点云使用 .ply 还是 .pcd？",
            next_question="",
            lang="zh",
            ops_status={},
        )
        reply = str(payload["reply_text"])
        # New behaviour: text passes through without being wrapped in labeled sections.
        self.assertIn("请问你希望输出点云使用 .ply 还是 .pcd？", reply)
        self.assertNotIn("结论：", reply)  # no forced section labels
        self.assertNotIn("默认先以 Telegram", reply)
        # No longer injects old project-style default question
        self.assertNotIn("关键目标", reply)

    def test_reply_payload_filters_mojibake_replacement_chars(self) -> None:
        payload = build_user_reply_payload(
            reply_text=(
                "���ã���л������������Ҫ����һ������Ŀ\n\n"
                "为了让这一轮闭环，�������������һ������������？"
            ),
            next_question="�������������Ŀ����？",
            lang="zh",
            ops_status={},
        )
        reply = str(payload["reply_text"])
        self.assertNotIn("�", reply)
        self.assertIn("我正在帮你处理中", reply)
        # Garbled follow-up should be downgraded to safe default and not forced as pending question.
        self.assertEqual(str(payload.get("next_question", "")), "")

    def test_smalltalk_payload_does_not_append_default_assumption(self) -> None:
        payload = build_user_reply_payload(
            reply_text="你好！请问有什么可以帮到你的吗？",
            next_question="",
            lang="zh",
            ops_status={"intent": "smalltalk", "source_text": "你好"},
        )
        reply = str(payload.get("reply_text", ""))
        self.assertNotIn("我先按默认方案继续推进", reply)
        self.assertNotIn("我先把这一步做下去", reply)

    def test_api_note_reply_and_followup_are_merged_into_single_message(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_api_merge_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
                state_db=base / "state.sqlite3",
                poll_seconds=1,
                tick_seconds=1,
                auto_advance=False,
                api_enabled=True,
                api_model="gpt-4.1-mini",
                api_timeout_sec=10,
                note_ack_path=False,
                progress_push_enabled=False,
            )
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                bot._api_route = lambda _run, _lang, _text: ApiDecision(  # type: ignore[method-assign]
                    intent="note",
                    reply="我已经理解你的目标。",
                    note="",
                    summary="",
                    steps=1,
                    follow_up="你更关注速度还是精度？",
                )
                handled = bot._handle_bound_api(chat_id=111, lang="zh", run_dir=run_dir, text="目标是高速点云建图")
                self.assertTrue(handled)
                self.assertEqual(len(fake.messages), 1)
                self.assertIn("你更关注速度还是精度？", fake.messages[0])
            finally:
                bot.close()

    def test_note_ack_path_is_quiet_by_default(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_note_quiet_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
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
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                chat_id = 101
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "新增退款问答流程"}})
                transcript = "\n".join(fake.messages)
                self.assertNotIn("USER_NOTES", transcript)
                self.assertNotIn("artifacts/", transcript)
                notes = (run_dir / "artifacts" / "USER_NOTES.md").read_text(encoding="utf-8", errors="replace")
                self.assertIn("新增退款问答流程", notes)
            finally:
                bot.close()

    def test_note_ack_path_can_be_enabled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_note_loud_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
                state_db=base / "state.sqlite3",
                poll_seconds=1,
                tick_seconds=1,
                auto_advance=False,
                api_enabled=False,
                api_model="gpt-4.1-mini",
                api_timeout_sec=10,
                note_ack_path=True,
                progress_push_enabled=False,
            )
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                chat_id = 102
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "新增退款问答流程"}})
                transcript = "\n".join(fake.messages)
                self.assertNotIn("USER_NOTES", transcript)
                self.assertNotIn("artifacts/", transcript)
                ops = (run_dir / "logs" / "telegram_cs_bot.ops.jsonl").read_text(encoding="utf-8", errors="replace")
                self.assertIn("notes_path", ops)
            finally:
                bot.close()

    def test_advance_blocked_is_throttled_and_not_repeated(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_blocked_throttle_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
                state_db=base / "state.sqlite3",
                poll_seconds=1,
                tick_seconds=1,
                auto_advance=True,
                api_enabled=False,
                api_model="gpt-4.1-mini",
                api_timeout_sec=10,
                note_ack_path=False,
                progress_push_enabled=False,
            )
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                chat_id = 150
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")

                blocked = "\n".join(
                    [
                        "[ctcp_orchestrate] run_status=running",
                        "[ctcp_orchestrate] next=blocked",
                        "[ctcp_orchestrate] owner=chair",
                        "[ctcp_orchestrate] path=artifacts/PLAN_draft.md",
                        "[ctcp_orchestrate] reason=waiting plan_draft",
                    ]
                )
                bot._run_orchestrate = lambda _args: (0, blocked, "")  # type: ignore[method-assign]
                bot._advance_once(chat_id, run_dir, 1)
                bot._advance_once(chat_id, run_dir, 1)

                self.assertEqual(len(fake.messages), 1)
                self.assertIn("补充", fake.messages[0])
                self.assertNotIn("继续自动推进可以吗", fake.messages[0])
                state = json.loads((run_dir / "artifacts" / "support_session_state.json").read_text(encoding="utf-8", errors="replace"))
                self.assertTrue(str(state.get("blocked_signature", "")).strip())
            finally:
                bot.close()

    def test_command_advance_skips_second_auto_advance_in_same_turn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_advance_once_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
                state_db=base / "state.sqlite3",
                poll_seconds=1,
                tick_seconds=1,
                auto_advance=True,
                api_enabled=False,
                api_model="gpt-4.1-mini",
                api_timeout_sec=10,
                note_ack_path=False,
                progress_push_enabled=False,
            )
            bot = Bot(cfg)
            bot.tg = _FakeTg()
            try:
                chat_id = 151
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                flags: list[bool] = []
                bot._advance_once = lambda _cid, _rd, _steps: None  # type: ignore[method-assign]
                bot._scan_push = (  # type: ignore[method-assign]
                    lambda _cid, _rd, allow_auto_advance=True: (flags.append(bool(allow_auto_advance)) or {"questions": 0, "agent_dispatch": 0, "normal": 0, "agent_results": 0})
                )
                bot._handle_command(chat_id, "zh", "/advance 1")
                self.assertEqual(flags, [False])
            finally:
                bot.close()

    def test_config_load_forces_full_auto(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_cfg_") as td:
            state_db = str(Path(td) / "state.sqlite3")
            with mock.patch.dict(
                os.environ,
                {
                    "CTCP_TG_BOT_TOKEN": "fake-token",
                    "CTCP_TG_STATE_DB": state_db,
                    "CTCP_TG_AUTO_ADVANCE": "0",
                },
                clear=False,
            ):
                cfg = Config.load()
            self.assertTrue(cfg.auto_advance)

    def test_scan_push_auto_advance_when_idle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_auto_idle_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
                state_db=base / "state.sqlite3",
                poll_seconds=1,
                tick_seconds=1,
                auto_advance=True,
                api_enabled=False,
                api_model="gpt-4.1-mini",
                api_timeout_sec=10,
                note_ack_path=False,
                progress_push_enabled=False,
            )
            bot = Bot(cfg)
            bot.tg = _FakeTg()
            try:
                chat_id = 103
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                calls: list[tuple[int, int]] = []
                bot._advance_once = lambda cid, rd, steps: calls.append((cid, steps))  # type: ignore[method-assign]
                bot._scan_push(chat_id, run_dir)
                self.assertEqual(calls, [(chat_id, 1)])
            finally:
                bot.close()

    def test_scan_push_skips_internal_support_provider_prompts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_support_internal_skip_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            outbox = run_dir / "outbox"
            outbox.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            (outbox / "001_router.md").write_text(
                "\n".join(
                    [
                        "Role: support_lead_router",
                        "Action: route",
                        "Target-Path: artifacts/support_router.provider.json",
                        "Type: question",
                        "Prompt: support router.provider",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            (outbox / "002_reply.md").write_text(
                "\n".join(
                    [
                        "Role: support_lead_reply",
                        "Action: reply",
                        "Target-Path: artifacts/support_reply.provider.json",
                        "Prompt: support reply.provider",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
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
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                chat_id = 188
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                stats = bot._scan_push(chat_id, run_dir, allow_auto_advance=False)
                self.assertEqual(fake.messages, [])
                self.assertEqual(stats, {"questions": 0, "agent_dispatch": 0, "normal": 0, "agent_results": 0})
                self.assertEqual(bot._collect_prompts(run_dir), [])
            finally:
                bot.close()

    def test_scan_push_keeps_non_internal_prompt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_support_prompt_keep_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            outbox = run_dir / "outbox"
            outbox.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            (outbox / "001_plan.md").write_text(
                "\n".join(
                    [
                        "Role: chair",
                        "Action: plan_signed",
                        "Target-Path: artifacts/PLAN.md",
                        "Prompt: 请确认当前方案细节",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            cfg = Config(
                token="fake",
                allowlist=None,
                repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
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
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                chat_id = 189
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                stats = bot._scan_push(chat_id, run_dir, allow_auto_advance=False)
                self.assertEqual(stats["normal"], 1)
                self.assertEqual(len(fake.messages), 1)
                self.assertIn("请确认当前方案细节", fake.messages[0])
            finally:
                bot.close()


if __name__ == "__main__":
    unittest.main()
