import unittest

from tools.telegram_cs_bot import (
    _humanize_trace_delta,
    build_employee_note_reply,
    describe_artifact_for_customer,
)


class TelegramCsBotEmployeeStyleTests(unittest.TestCase):
    def test_zh_reply_acks_and_asks_for_missing_details(self) -> None:
        text = "我需要一个非常像真实员工的客服bot"
        out = build_employee_note_reply(text, "zh")
        self.assertIn("收到", out)
        self.assertIn("请再确认", out)

    def test_en_reply_does_not_force_followup_when_context_is_complete(self) -> None:
        text = (
            "Build a customer support bot for Telegram with human handoff and "
            "FAQ knowledge base import."
        )
        out = build_employee_note_reply(text, "en")
        self.assertIn("Understood", out)
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
        self.assertIn("进展更新", out)
        self.assertIn("刚做完", out)
        self.assertIn("关键问题", out)

    def test_artifact_description_is_customer_friendly(self) -> None:
        self.assertEqual(describe_artifact_for_customer("artifacts/PLAN_draft.md", "zh"), "项目方案草稿")
        self.assertEqual(
            describe_artifact_for_customer("artifacts/verify_report.json", "en"),
            "verification report",
        )


if __name__ == "__main__":
    unittest.main()
