"""Acceptance tests for legacy CS dialogue cleanup and bridge integration.

Covers 5 scenarios from the repair task:
  1. New project intake → clean reply, no internal terms
  2. Stale blocked state → still clean intake reply
  3. Results intent detection
  4. describe_artifact_for_customer no longer returns internal terms
  5. looks_like_new_goal catches explicit project creation requests
"""

import unittest

from frontend.response_composer import render_frontend_output
from tools.telegram_cs_bot import (
    describe_artifact_for_customer,
    detect_intent,
    looks_like_new_goal,
)


# ---------- internal tokens that must NEVER appear in user-facing text ----------
_FORBIDDEN_ZH = (
    "待处理的事项",
    "需要的信息",
    "等待必要输入",
    "当前阻塞项",
    "需要补充",
)
_FORBIDDEN_EN = (
    "pending task",
    "analysis.md",
)


def _assert_no_internal_leak(test: unittest.TestCase, text: str) -> None:
    """Helper: assert that *text* contains no internal tokens."""
    for tok in _FORBIDDEN_ZH:
        test.assertNotIn(tok, text, msg=f"Chinese internal token leaked: {tok}")
    low = text.lower()
    for tok in _FORBIDDEN_EN:
        test.assertNotIn(tok, low, msg=f"English internal token leaked: {tok}")
    test.assertNotIn("waiting for", low)
    test.assertNotIn("outbox", low)


class TestNewProjectIntakeClean(unittest.TestCase):
    """Scenario 1: user says '我想要做一个新的项目' → PROJECT_INTAKE, no internal terms."""

    def test_intake_reply_is_clean(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
            },
            task_summary="我想要做一个新的项目",
            raw_reply_text="关于：待处理的事项 需要的信息：waiting for analysis.md",
            raw_next_question="关于：待处理的事项 需要的信息：waiting for analysis.md",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想要做一个新的项目"],
            },
        )
        _assert_no_internal_leak(self, result.reply_text)
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "PROJECT_INTAKE")

    def test_intake_reply_en_is_clean(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
                "reason": "waiting for analysis.md",
            },
            task_summary="I want to start a new project",
            raw_reply_text="Currently blocked on: pending task. Required input: analysis.md",
            raw_next_question="Do you have an analysis.md?",
            notes={
                "lang": "en",
                "recent_user_messages": ["I want to start a new project"],
            },
        )
        _assert_no_internal_leak(self, result.reply_text)


class TestStaleBlockedStatePurged(unittest.TestCase):
    """Scenario 2: stale blocked state in backend → intake still clean."""

    def test_blocked_state_does_not_leak(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
                "needs_input": True,
                "reason": "waiting for analysis.md",
                "missing_fields": ["runtime_target"],
            },
            task_summary="我想要做一个新的项目",
            raw_reply_text="当前阻塞项：某模块 需要补充：analysis.md",
            raw_next_question="请提供 analysis.md",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想要做一个新的项目"],
            },
        )
        _assert_no_internal_leak(self, result.reply_text)
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "PROJECT_INTAKE")


class TestResultsIntentDetection(unittest.TestCase):
    """Scenario 3: user asks for results / deliverables."""

    def test_results_zh_phrases(self) -> None:
        phrases = [
            "给我结果",
            "项目文件",
            "最终结果",
            "产物",
            "交付物",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                intent, _ = detect_intent(phrase)
                self.assertEqual(intent, "results", msg=f"'{phrase}' should → results")

    def test_results_en_phrases(self) -> None:
        phrases = [
            "give me the result",
            "deliverable",
            "final output",
            "send me the result",
        ]
        for phrase in phrases:
            with self.subTest(phrase=phrase):
                intent, _ = detect_intent(phrase)
                self.assertEqual(intent, "results", msg=f"'{phrase}' should → results")


class TestDescribeArtifactNoLeak(unittest.TestCase):
    """Scenario 4: describe_artifact_for_customer defaults are clean."""

    def test_default_zh_is_clean(self) -> None:
        label = describe_artifact_for_customer("some/unknown/file.txt", "zh")
        self.assertEqual(label, "你的请求")
        self.assertNotIn("待处理的事项", label)

    def test_default_en_is_clean(self) -> None:
        label = describe_artifact_for_customer("some/unknown/file.txt", "en")
        self.assertEqual(label, "your request")
        self.assertNotIn("pending task", label.lower())

    def test_known_artifacts_still_work(self) -> None:
        self.assertEqual(describe_artifact_for_customer("artifacts/plan.md", "zh"), "签署后的执行计划")
        self.assertEqual(describe_artifact_for_customer("artifacts/diff.patch", "en"), "code change patch")


class TestLooksLikeNewGoalCatchesProjectCreation(unittest.TestCase):
    """Scenario 5: looks_like_new_goal correctly flags project creation requests."""

    def test_explicit_creation_requests(self) -> None:
        positives = [
            "我想要做一个新的项目",
            "帮我做一个客服机器人项目",
            "I want to build a support bot for Telegram",
            "create a new project for support automation",
            "start over from scratch with a new support flow",
        ]
        for text in positives:
            with self.subTest(text=text):
                self.assertTrue(looks_like_new_goal(text), msg=f"Should be new goal: {text}")

    def test_non_goal_phrases_rejected(self) -> None:
        negatives = [
            "你好",
            "查看进度",
            "继续",
            "report",
            "ok",
        ]
        for text in negatives:
            with self.subTest(text=text):
                self.assertFalse(looks_like_new_goal(text), msg=f"Should NOT be new goal: {text}")


class TestAutoContineNeverAsks(unittest.TestCase):
    """The bot must auto-continue instead of asking 'shall I continue?'."""

    def test_default_next_question_is_empty(self) -> None:
        from tools.telegram_cs_bot import _default_next_question
        self.assertEqual(_default_next_question("zh"), "")
        self.assertEqual(_default_next_question("en"), "")

    def test_normalize_suppresses_continue_questions_zh(self) -> None:
        from tools.telegram_cs_bot import _normalize_next_question
        cases = [
            "还有什么我可以帮到你的吗？",
            "还有其他需要我帮忙的吗？",
            "需要我继续尝试吗？",
            "要我继续吗？",
            "我继续帮你处理，还是先等你确认一下？",
            "还有其他需要补充的吗？",
            "还有什么需要我帮忙的？",
        ]
        for text in cases:
            with self.subTest(text=text):
                result = _normalize_next_question(text, "zh")
                self.assertEqual(result, "", msg=f"Should be suppressed: {text!r} → {result!r}")

    def test_normalize_suppresses_continue_questions_en(self) -> None:
        from tools.telegram_cs_bot import _normalize_next_question
        cases = [
            "Is there anything else I can help you with?",
            "Would you like me to keep going?",
            "Should I continue?",
            "Want me to continue?",
            "Would you like me to keep trying?",
            "Should I keep auto-advancing this run?",
        ]
        for text in cases:
            with self.subTest(text=text):
                result = _normalize_next_question(text, "en")
                self.assertEqual(result, "", msg=f"Should be suppressed: {text!r} → {result!r}")

    def test_normalize_keeps_substantive_questions(self) -> None:
        from tools.telegram_cs_bot import _normalize_next_question
        cases = [
            ("你更偏向接近实时输出，还是允许离线处理？", "zh"),
            ("What is your top priority: speed, quality, or cost?", "en"),
            ("你这次用的是单目视频还是多视角素材？", "zh"),
        ]
        for text, lang in cases:
            with self.subTest(text=text):
                result = _normalize_next_question(text, lang)
                self.assertTrue(result.strip(), msg=f"Should be kept: {text!r} → {result!r}")


if __name__ == "__main__":
    unittest.main()
