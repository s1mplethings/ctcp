import unittest

from tools.telegram_cs_bot import detect_intent, is_cleanup_project_request, looks_like_new_goal


class TelegramCsBotIntentMatrixTests(unittest.TestCase):
    def test_detect_intent_matrix(self) -> None:
        cases: list[tuple[str, str, str]] = [
            ("查看进度", "debug", ""),
            ("看进度", "debug", ""),
            ("调试一下", "debug", ""),
            ("debug please", "debug", ""),
            ("现在在做什么", "status", ""),
            ("当前项目进度", "status", ""),
            ("你现在手头还有我的项目吗", "status", ""),
            ("progress update", "status", ""),
            ("blocked now", "status", ""),
            ("继续推进", "advance", "1"),
            ("retry now", "advance", "1"),
            ("失败包", "bundle", ""),
            ("failure bundle", "bundle", ""),
            ("给我验证报告", "report", ""),
            ("verify report", "report", ""),
            ("需要我决定什么", "decision", ""),
            ("need me to decide", "decision", ""),
            ("待办有什么", "outbox", ""),
            ("outbox", "outbox", ""),
            ("英文", "lang", "en"),
            ("English please", "lang", "en"),
            ("中文", "lang", "zh"),
            ("switch to chinese", "lang", "zh"),
            ("先清理一下", "cancel_run", "先清理一下"),
            ("clear previous run", "cancel_run", "clear previous run"),
            ("delete previous session", "cancel_run", "delete previous session"),
            ("我想做一个新的客服机器人项目", "note", "我想做一个新的客服机器人项目"),
        ]
        for text, expected_intent, expected_value in cases:
            with self.subTest(text=text):
                intent, val = detect_intent(text)
                self.assertEqual(intent, expected_intent)
                if expected_intent in {"lang", "advance"}:
                    self.assertEqual(val, expected_value)
                elif expected_intent in {"note", "cancel_run"}:
                    self.assertEqual(val, expected_value)
                else:
                    self.assertEqual(val, "")

    def test_cleanup_request_matrix(self) -> None:
        positives = [
            "先清理一下",
            "清理之前的项目",
            "不想继续之前那个项目，先清理一下",
            "清空当前会话",
            "删除旧的run记录",
            "删掉之前那个任务",
            "重置当前项目",
            "clear previous run",
            "delete previous session",
            "cancel previous project",
            "stop current task",
            "drop old run",
        ]
        negatives = [
            "查看进度",
            "我想创建一个项目",
            "帮我做一个客服bot",
            "what is running now",
            "hello",
            "thanks",
            "report please",
            "need me to decide",
            "outbox",
            "继续推进",
        ]
        for text in positives:
            with self.subTest(kind="positive", text=text):
                self.assertTrue(is_cleanup_project_request(text), msg=text)
        for text in negatives:
            with self.subTest(kind="negative", text=text):
                self.assertFalse(is_cleanup_project_request(text), msg=text)

    def test_looks_like_new_goal_matrix(self) -> None:
        positives = [
            "我想要做一个新的客服机器人项目",
            "我要做一个退款自动回复流程",
            "帮我做一个客服机器人项目",
            "请帮我搭一个售后对话系统",
            "目标是提升客服满意度",
            "我需要一个支持多语言的客服项目",
            "I want to build a support bot for Telegram",
            "I need a customer support workflow for refund handling",
            "create a new project for support automation",
            "start over from scratch with a new support flow",
        ]
        negatives = [
            "你好",
            "谢谢",
            "查看进度",
            "继续",
            "outbox",
            "report",
            "need me to decide",
            "help",
            "ok",
            "yes",
        ]
        for text in positives:
            with self.subTest(kind="positive", text=text):
                self.assertTrue(looks_like_new_goal(text), msg=text)
        for text in negatives:
            with self.subTest(kind="negative", text=text):
                self.assertFalse(looks_like_new_goal(text), msg=text)


if __name__ == "__main__":
    unittest.main()
