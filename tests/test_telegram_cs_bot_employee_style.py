import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest import mock

from tools.telegram_cs_bot import (
    _humanize_trace_delta,
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
    def test_zh_reply_acks_and_asks_for_missing_details(self) -> None:
        text = "我需要一个非常像真实员工的客服bot"
        out = build_employee_note_reply(text, "zh")
        self.assertIn("结论：", out)
        self.assertIn("方案：", out)
        self.assertIn("下一步：", out)
        self.assertNotIn("为了更像真实员工客服", out)

    def test_en_reply_does_not_force_followup_when_context_is_complete(self) -> None:
        text = (
            "Build a customer support bot for Telegram with human handoff and "
            "FAQ knowledge base import."
        )
        out = build_employee_note_reply(text, "en")
        self.assertIn("Conclusion:", out)
        self.assertIn("Plan:", out)
        self.assertIn("Next:", out)
        self.assertNotIn("please confirm", out.lower())

    def test_trace_delta_customer_summary_zh(self) -> None:
        delta = "\n".join(
            [
                "- 2026-03-01T20:40:00 | Local Orchestrator: VERIFY_STARTED (artifacts/verify_report.json)",
                "- 2026-03-01T20:40:10 | Contract_Guardian: LOCAL_EXEC_COMPLETED (reviews/review_contract.md)",
                "- 2026-03-01T20:40:20 | Local Verifier: LOCAL_EXEC_FAILED (artifacts/verify_report.json)",
            ]
        )
        out = _humanize_trace_delta(delta, "zh")
        self.assertIn("结论：", out)
        self.assertIn("方案：", out)
        self.assertIn("下一步：", out)

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
        self.assertIn("结论：", reply)
        self.assertIn("下一步：", reply)
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
        self.assertIn("结论：", reply)
        self.assertIn("下一步：请问你希望输出点云使用 .ply 还是 .pcd？", reply)
        self.assertNotIn("默认先以 Telegram", reply)

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
                self.assertIn("下一步：你更关注速度还是精度？", fake.messages[0])
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


if __name__ == "__main__":
    unittest.main()
