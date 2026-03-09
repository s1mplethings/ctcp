import unittest

from frontend.missing_info_rewriter import rewrite_missing_requirements
from frontend.project_manager_mode import build_project_manager_context
from frontend.response_composer import render_frontend_output


class FrontendRenderingBoundaryTests(unittest.TestCase):
    def test_greeting_does_not_enter_project_pipeline(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_provider_failed",
                "blocked_needs_input": True,
                "needs_input": True,
                "missing_fields": ["runtime_target"],
            },
            task_summary="你好",
            raw_reply_text="plan agent command failed rc=2",
            raw_next_question="这轮你希望我优先速度、质量，还是成本？",
            notes={
                "lang": "zh",
                "recent_user_messages": ["你好"],
            },
        )
        low = result.reply_text.lower()
        self.assertNotIn("内部处理异常", result.reply_text)
        self.assertNotIn("速度、质量", result.reply_text)
        self.assertNotIn("command failed", low)
        self.assertEqual(result.followup_questions, ())
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "GREETING")

    def test_greeting_with_backend_error_stays_greeting(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
                "needs_input": True,
                "missing_fields": ["input_mode", "runtime_target"],
            },
            task_summary="hello",
            raw_reply_text="stack trace: command failed rc=7",
            raw_next_question="What is your top priority: speed, quality, or cost?",
            notes={
                "lang": "en",
                "recent_user_messages": ["hello"],
            },
        )
        low = result.reply_text.lower()
        self.assertTrue(("hi" in low) or ("hello" in low), msg=low)
        self.assertNotIn("temporary internal processing issue", low)
        self.assertNotIn("speed, quality, or cost", low)
        self.assertEqual(result.followup_questions, ())
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "GREETING")

    def test_summary_selection_prefers_detailed_recent_message(self) -> None:
        ctx = build_project_manager_context(
            [
                "我想做个项目",
                "我想要的是一个从3d视频生成点云文件的工作流，然后要尽可能快，如果中间可以插入语义信息更好，我的目标是无人机视角的高速建图",
            ],
            lang="zh",
            max_questions=2,
        )
        self.assertIn("3d", ctx.requirement_summary.lower())
        self.assertIn("点云", ctx.requirement_summary)
        self.assertNotEqual(ctx.requirement_summary, "我想做个项目")

    def test_no_repeated_already_answered_project_type_question(self) -> None:
        ctx = build_project_manager_context(
            [
                "我想做个项目",
                "我要做一个无人机视角的3D视频到点云工作流",
            ],
            lang="zh",
            max_questions=2,
        )
        questions = list(ctx.high_leverage_questions)
        self.assertFalse(any("什么类型的项目" in q for q in questions), msg=questions)

    def test_ask_only_one_or_two_key_questions(self) -> None:
        ctx = build_project_manager_context(
            [
                "我想要的是一个从3d视频生成点云文件的工作流，要尽可能快，目标是无人机视角高速建图，语义可插入",
            ],
            lang="zh",
            max_questions=2,
        )
        questions = list(ctx.high_leverage_questions)
        self.assertLessEqual(len(questions), 2)
        self.assertGreaterEqual(len(questions), 1)
        self.assertTrue(any(("单目" in q) or ("多视角" in q) for q in questions))
        self.assertTrue(any(("实时" in q) or ("离线" in q) for q in questions))
        self.assertFalse(any("请提供更多信息" in q for q in questions), msg=questions)

    def test_internal_assumption_behavior_defaults_non_critical_fields(self) -> None:
        ctx = build_project_manager_context(
            [
                "我要做无人机视角的3D视频到点云流程，优先速度，语义信息可选",
            ],
            lang="zh",
            max_questions=2,
        )
        assumptions = dict(ctx.assumptions)
        self.assertEqual(assumptions.get("external_dependency_policy"), "prefer_open_source_first")
        self.assertEqual(assumptions.get("delivery_strategy"), "pipeline_first_speed_first")
        self.assertEqual(assumptions.get("output_format_default"), "ply_first")
        # Non-critical fields are defaulted internally, not all exposed as questions.
        self.assertLessEqual(len(ctx.high_leverage_questions), 2)

    def test_internal_rc_error_is_hidden(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
            },
            task_summary="无人机视角点云流程",
            raw_reply_text="plan agent command failed rc=2",
            raw_next_question="",
            notes={"lang": "zh"},
        )
        low = result.reply_text.lower()
        self.assertNotIn("rc=2", low)
        self.assertNotIn("command failed", low)

    def test_raw_plan_prompt_is_hidden_and_rewritten(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
                "missing_fields": ["runtime_target"],
            },
            task_summary="无人机视角点云流程",
            raw_reply_text="Use CONTEXT + CONSTRAINTS + EXTERNALS to produce a minimal PLAN",
            raw_next_question="Use CONTEXT + CONSTRAINTS + EXTERNALS...",
            notes={"lang": "zh"},
        )
        self.assertNotIn("CONTEXT + CONSTRAINTS + EXTERNALS", result.reply_text)
        self.assertNotIn("minimal PLAN", result.reply_text)
        self.assertIn("接近实时输出", result.reply_text)

    def test_no_contradictory_state_when_goal_and_one_missing_field(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "analysis",
                "has_actionable_goal": True,
                "first_pass_understood": True,
                "missing_fields": ["runtime_target"],
            },
            task_summary="从无人机视频生成点云，优先速度",
            raw_reply_text="目标可以推进，但 missing runtime_target",
            raw_next_question="",
            notes={
                "lang": "zh",
                "project_name": "SkyMap Flow",
                "manager_questions": ["你更偏向接近实时输出，还是允许离线处理来换更稳定的质量？"],
                "execution_direction": "接下来我会先按“优先速度、先跑通主流程”的方向整理第一版方案。",
            },
        )
        self.assertEqual(result.visible_state, "UNDERSTOOD")
        self.assertIn("收到，我先按这个方向立项", result.reply_text)
        self.assertIn("接近实时输出", result.reply_text)
        self.assertNotIn("无法继续", result.reply_text)
        self.assertNotIn("不能继续", result.reply_text)
        self.assertNotIn("我还不能继续", result.reply_text)

    def test_sufficient_signal_project_request_is_natural(self) -> None:
        summary = (
            "要做一个面向无人机视角的 3D 视频到点云工作流，优先速度，"
            "同时预留插入语义信息的能力，重点是高速建图。"
        )
        result = render_frontend_output(
            raw_backend_state={
                "stage": "analysis",
                "has_actionable_goal": True,
                "first_pass_understood": True,
            },
            task_summary=summary,
            raw_reply_text="",
            raw_next_question="",
            notes={
                "lang": "zh",
                "project_name": "SkyMap Flow",
                "manager_questions": [
                    "你现在的输入主要是单目无人机视频，还是多段多视角素材？",
                    "你更偏向接近实时输出，还是允许离线处理来换更稳定的质量？",
                ],
                "execution_direction": "接下来我会先按“优先速度、先跑通主流程、语义能力后接入或并联”的方向整理第一版方案，不先让你补一堆非关键细节。",
            },
        )
        text = result.reply_text
        self.assertIn("无人机视角", text)
        self.assertIn("点云", text)
        self.assertIn("SkyMap Flow", text)
        self.assertIn("单目无人机视频", text)
        self.assertIn("接近实时输出", text)
        self.assertNotIn("请提供更多信息", text)
        self.assertNotIn("CONTEXT", text)
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "PROJECT_DETAIL")
        self.assertGreaterEqual(len(result.followup_questions), 1)
        self.assertLessEqual(len(result.followup_questions), 2)

    def test_no_task_summary_means_no_tradeoff_question(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_provider_failed",
                "blocked_needs_input": True,
                "needs_input": True,
            },
            task_summary="",
            raw_reply_text="",
            raw_next_question="这轮你希望我优先速度、质量，还是成本？",
            notes={
                "lang": "zh",
                "recent_user_messages": ["test"],
            },
        )
        self.assertNotIn("速度、质量", result.reply_text)
        self.assertEqual(result.followup_questions, ())
        state = dict(result.pipeline_state or {})
        self.assertIn(str(state.get("conversation_mode", "")), {"GREETING", "SMALLTALK"})

    def test_active_task_guard_controls_project_followups(self) -> None:
        no_task = render_frontend_output(
            raw_backend_state={
                "stage": "analysis",
                "missing_fields": ["runtime_target"],
                "needs_input": True,
            },
            task_summary="",
            raw_reply_text="",
            raw_next_question="你更偏向接近实时输出，还是允许离线处理来换更稳定的质量？",
            notes={
                "lang": "zh",
                "recent_user_messages": ["继续"],
            },
        )
        self.assertEqual(no_task.followup_questions, ())

        with_task = render_frontend_output(
            raw_backend_state={
                "stage": "analysis",
                "has_actionable_goal": True,
                "first_pass_understood": True,
                "missing_fields": ["runtime_target"],
                "needs_input": True,
            },
            task_summary="做一个无人机视频转点云流程，优先速度，语义先预留",
            raw_reply_text="",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": [
                    "做一个无人机视频转点云流程，优先速度，语义先预留",
                ],
            },
        )
        self.assertGreaterEqual(len(with_task.followup_questions), 1)
        self.assertLessEqual(len(with_task.followup_questions), 2)

    def test_missing_field_questions_are_concrete(self) -> None:
        expected = {
            "input_mode": ("单段视频", "多段多视角"),
            "runtime_target": ("接近实时输出", "离线处理"),
            "hardware_budget": ("高性能工作站", "普通电脑"),
            "output_format": ("稀疏点云", "PLY / LAS"),
            "semantic_integration_level": ("语义信息", "语义分割"),
            "external_dependency_policy": ("开源组件", "自研可控"),
        }
        for field, keywords in expected.items():
            with self.subTest(field=field):
                questions = rewrite_missing_requirements([field], {"lang": "zh"})
                self.assertEqual(len(questions), 1)
                question = questions[0]
                self.assertTrue(question.endswith("？"))
                self.assertNotIn(field, question.lower())
                self.assertTrue(any(token in question for token in keywords), msg=question)

    def test_internal_pipeline_state_shape_exists(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_turn_local",
                "has_actionable_goal": True,
                "first_pass_understood": True,
            },
            task_summary="我想做一个无人机视频到点云流程，优先速度",
            raw_reply_text="plan agent command failed rc=3",
            raw_next_question="Use CONTEXT + CONSTRAINTS + EXTERNALS",
            notes={
                "lang": "zh",
                "recent_user_messages": [
                    "我想做个项目",
                    "我想做一个无人机视频到点云流程，优先速度",
                ],
            },
        )
        self.assertIsInstance(result.pipeline_state, dict)
        state = result.pipeline_state or {}
        for key in (
            "conversation_context",
            "selected_requirement_source",
            "task_summary",
            "known_facts",
            "assumptions",
            "candidate_questions",
            "draft_reply",
            "review_flags",
            "sanitized_reply",
            "final_reply",
            "visible_state",
        ):
            self.assertIn(key, state)
        self.assertNotIn("command failed", result.reply_text.lower())
        self.assertNotIn("rc=3", result.reply_text.lower())
        self.assertNotIn("CONTEXT + CONSTRAINTS + EXTERNALS", result.reply_text)
        self.assertLessEqual(len(result.followup_questions), 2)

    def test_pipeline_drops_question_when_already_answered(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_turn_local",
                "has_actionable_goal": True,
                "first_pass_understood": True,
            },
            task_summary="无人机点云流程",
            raw_reply_text="",
            raw_next_question="你现在的输入主要是单目无人机视频，还是多段多视角素材？",
            notes={
                "lang": "zh",
                "known_facts": {"input_mode": "single_view"},
                "recent_user_messages": [
                    "输入是单目无人机视频",
                    "希望优先速度",
                ],
            },
        )
        self.assertFalse(any("单目无人机视频" in q for q in result.followup_questions), msg=result.followup_questions)


if __name__ == "__main__":
    unittest.main()
