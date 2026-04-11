import unittest

from frontend.conversation_mode_router import route_conversation_mode
from frontend.missing_info_rewriter import rewrite_missing_requirements
from frontend.project_manager_mode import build_project_manager_context
from frontend.response_composer import render_frontend_output
from frontend.support_reply_policy import render_fallback_reply


class FrontendRenderingBoundaryTests(unittest.TestCase):
    def test_confirmation_turn_with_active_project_routes_to_project_detail(self) -> None:
        mode = route_conversation_mode(
            ["确定"],
            "确定",
            {
                "task_summary": "我想要你继续优化我的剧情项目",
                "run_id": "r-demo",
                "active_stage": "EXECUTE",
            },
        )
        self.assertEqual(mode, "PROJECT_DETAIL")

    def test_confirmation_turn_while_waiting_decision_routes_to_decision_reply(self) -> None:
        mode = route_conversation_mode(
            ["可以"],
            "可以",
            {
                "task_summary": "我想要你继续优化我的剧情项目",
                "run_id": "r-demo",
                "active_stage": "WAIT_USER_DECISION",
                "waiting_for": "请选择交付格式",
            },
        )
        self.assertEqual(mode, "PROJECT_DECISION_REPLY")

    def test_project_intake_generic_opening_question_no_name_error(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
            },
            task_summary="我想要做一个新的项目",
            raw_reply_text="我这边需要你补充一些信息才能继续帮你处理。",
            raw_next_question="还有什么我可以帮到你的吗？",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想要做一个新的项目"],
            },
        )
        self.assertIsInstance(result.reply_text, str)
        self.assertTrue(result.reply_text.strip())
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "PROJECT_INTAKE")

    def test_project_intake_is_not_overridden_by_blocked_without_task_or_waiting_text(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
                "needs_input": True,
                "reason": "waiting for analysis.md",
            },
            task_summary="我想要做一个新的项目",
            raw_reply_text="关于：待处理的事项 需要的信息：waiting for analysis.md",
            raw_next_question="关于：待处理的事项 需要的信息：waiting for analysis.md",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想要做一个新的项目"],
            },
        )
        text = result.reply_text
        self.assertTrue(
            any(tok in text for tok in ("目标、输入和想要什么结果", "我来帮你理")),
            msg=f"intake reply should stay truthful and neutral: {text}",
        )
        self.assertNotIn("待处理的事项", text)
        self.assertNotIn("waiting for", text.lower())
        self.assertNotIn("analysis.md", text.lower())
        self.assertNotIn("outbox", text.lower())
        self.assertLessEqual(len(result.followup_questions), 1)
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "PROJECT_INTAKE")

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

    def test_greeting_can_preserve_raw_model_reply_when_requested(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_turn_local",
                "has_actionable_goal": True,
                "first_pass_understood": True,
            },
            task_summary="你好",
            raw_reply_text="你好，先说你这轮最想推进的一件事，我马上接着做。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["你好"],
                "prefer_raw_reply_text": True,
            },
        )
        self.assertIn("先说你这轮最想推进的一件事", result.reply_text)
        self.assertNotIn("请问有什么可以帮到你", result.reply_text)
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "GREETING")

    def test_capability_query_about_frontend_stays_local_and_mentions_frontend_scope(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_provider_failed",
                "blocked_needs_input": True,
                "needs_input": True,
            },
            task_summary="你能不能按 CTCP 的方式改前端这块",
            raw_reply_text="plan agent command failed rc=9",
            raw_next_question="这轮你希望我优先速度、质量，还是成本？",
            notes={
                "lang": "zh",
                "recent_user_messages": ["你能不能按 CTCP 的方式改前端这块"],
            },
        )
        low = result.reply_text.lower()
        self.assertIn("前端", result.reply_text)
        self.assertIn("回归测试", result.reply_text)
        self.assertNotIn("command failed", low)
        self.assertNotIn("速度、质量", result.reply_text)
        self.assertEqual(result.followup_questions, ())
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "CAPABILITY_QUERY")

    def test_identity_query_uses_capability_reply_instead_of_generic_smalltalk(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_provider_failed",
                "blocked_needs_input": True,
                "needs_input": True,
            },
            task_summary="你是谁",
            raw_reply_text="plan agent command failed rc=3",
            raw_next_question="这轮你希望我优先速度、质量，还是成本？",
            notes={
                "lang": "zh",
                "recent_user_messages": ["你是谁"],
            },
        )
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "CAPABILITY_QUERY")
        self.assertIn("CTCP support 入口", result.reply_text)
        self.assertNotIn("我在，你说。", result.reply_text)
        self.assertEqual(result.followup_questions, ())

    def test_status_query_with_active_task_uses_status_shell_not_generic_kickoff(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "running",
            },
            task_summary="做一个无人机视频转点云项目",
            raw_reply_text="",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["现在进度到哪了"],
            },
        )
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "STATUS_QUERY")
        self.assertIn("项目：做一个无人机视频转点云项目", result.reply_text)
        self.assertNotIn("OK，这就开始", result.reply_text)

    def test_previous_project_status_followup_routes_to_status_query(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "executing",
                "run_status": "blocked",
                "progress_binding": {
                    "current_task_goal": "我想要你继续优化我的剧情项目",
                    "current_phase": "方案整理",
                    "last_confirmed_items": ["项目已接到后台流程"],
                    "current_blocker": "none",
                    "message_purpose": "progress",
                    "question_needed": "no",
                    "next_action": "继续推进当前 run",
                    "proof_refs": ["run_id=demo"],
                },
            },
            task_summary="我想要你继续优化我的剧情项目",
            raw_reply_text="你是否方便提供最新的规划文档？",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想要知道我之前那个项目做成什么样子了"],
            },
        )
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "STATUS_QUERY")
        self.assertIn("我这边已经完成：", result.reply_text)
        self.assertIn("项目已接到后台流程", result.reply_text)
        self.assertNotIn("规划文档", result.reply_text)

    def test_progress_binding_status_query_prefers_concrete_progress_summary(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "executing",
                "run_status": "blocked",
                "progress_binding": {
                    "current_task_goal": "你能不能重新做一个我之前想要你做的项目",
                    "current_phase": "合同评审",
                    "last_confirmed_items": [
                        "项目已接到后台流程",
                        "资料检索已跑过一轮",
                        "成本评审已跑过一轮",
                    ],
                    "current_blocker": "合同评审这一步还没过，后面的推进先停在这里",
                    "message_purpose": "progress",
                    "question_needed": "no",
                    "next_action": "先处理合同评审卡住的点，过掉这一步再继续往下推",
                    "proof_refs": ["run_id=demo"],
                },
            },
            task_summary="你能不能重新做一个我之前想要你做的项目",
            raw_reply_text="这边已经进入处理阶段。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["现在做到什么程度了"],
            },
        )
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "PROJECT_DETAIL")
        self.assertIn("我这边已经完成：", result.reply_text)
        self.assertIn("项目已接到后台流程", result.reply_text)
        self.assertIn("成本评审已跑过一轮", result.reply_text)
        self.assertIn("目前在合同评审这个阶段", result.reply_text)
        self.assertIn("我会继续处理：先处理合同评审卡住的点", result.reply_text)
        self.assertNotEqual(result.reply_text.strip(), "这边已经进入处理阶段。")

    def test_internal_recovery_block_on_project_detail_exposes_real_status(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "executing",
                "run_status": "blocked",
                "reason": "waiting for PLAN_draft.md",
                "progress_binding": {
                    "current_task_goal": "做一个本地可运行的 VN 项目助手 MVP",
                    "current_phase": "方案整理",
                    "last_confirmed_items": [],
                    "current_blocker": "waiting for PLAN_draft.md",
                    "message_purpose": "progress",
                    "question_needed": "no",
                    "next_action": "补齐 PLAN_draft.md 并继续推进方案整理",
                    "proof_refs": ["run_id=demo"],
                },
            },
            task_summary="做一个本地可运行的 VN 项目助手 MVP",
            raw_reply_text="当前遇到内部阻塞，确认这条输入后我可以继续。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": [
                    "做一个本地可运行的 VN 项目助手 MVP：输入角色资料、章节大纲、场景列表，生成一个可视化整理工具。"
                ],
                "frontdesk_state": {
                    "state": "showing_error",
                    "blocked_reason": "waiting for PLAN_draft.md",
                },
            },
        )
        self.assertIn("PLAN_draft.md", result.reply_text)
        self.assertIn("补齐 PLAN_draft.md", result.reply_text)
        self.assertNotIn("确认这条输入后我可以继续", result.reply_text)

    def test_frontend_recovery_reply_surfaces_retry_count_and_recovery_action(self) -> None:
        reply = render_fallback_reply(
            intent="guide_recovery",
            lang_hint="zh",
            project_context={
                "runtime_state": {
                    "phase": "RETRYING",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "recovery": {
                        "needed": True,
                        "status": "retrying",
                        "retry_count": 1,
                        "max_retries": 2,
                        "recovery_action": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                    },
                    "gate": {
                        "state": "blocked",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                        "retry_count": 1,
                        "max_retries": 2,
                        "expected_artifact": "artifacts/PLAN_draft.md",
                        "recovery_action": "retry planner and verify PLAN_draft.md lands with a valid draft contract",
                        "watchdog_status": "retrying",
                    },
                },
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "gate": {
                        "state": "blocked",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                },
            },
        )
        text = str(reply.get("reply_text", ""))
        self.assertIn("已自动重试 1/2 次", text)
        self.assertIn("PLAN_draft.md", text)
        self.assertIn("retry planner", text)

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
            raw_reply_text="收到你的需求，我来帮你整理方案。不过运行目标还需要你确认一下。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "project_name": "SkyMap Flow",
                "manager_questions": ["你更偏向接近实时输出，还是允许离线处理来换更稳定的质量？"],
                "execution_direction": "接下来我会先按“优先速度、先跑通主流程”的方向整理第一版方案。",
            },
        )
        # Model text is preferred over template when it is clean
        self.assertIn("收到你的需求", result.reply_text)
        # Follow-up questions are separate from the model reply text
        self.assertTrue(
            any("接近实时输出" in q for q in result.followup_questions)
            or "接近实时输出" in result.reply_text,
            msg=f"questions={result.followup_questions}, reply={result.reply_text}",
        )
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
            "input_mode": ("输入", "资料"),
            "runtime_target": ("桌面本地", "浏览器页面"),
            "hardware_budget": ("高性能工作站", "普通电脑"),
            "output_format": ("结构化 JSON", "脚手架/脚本"),
            "semantic_integration_level": ("预留接口", "主流程"),
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

    def test_vn_request_does_not_emit_pointcloud_followups(self) -> None:
        ctx = build_project_manager_context(
            [
                "做一个本地可运行的 VN 项目助手 MVP：输入角色资料、章节大纲、场景列表，生成一个可视化整理工具。",
            ],
            lang="zh",
            max_questions=2,
        )
        questions = list(ctx.high_leverage_questions)
        merged = "\n".join(questions)
        self.assertNotIn("单目", merged)
        self.assertNotIn("多视角", merged)
        self.assertNotIn("PLY", merged.upper())
        self.assertNotIn("LAS", merged.upper())
        self.assertTrue(any(token in merged for token in ("Ren'Py", "JSON", "桌面本地工具", "浏览器本地页面")), msg=merged)

    def test_backend_unavailable_reply_is_truthful_not_fake_progress(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_provider_failed",
                "reply_truth_status": "backend_unavailable",
                "reply_truth_reason": "connect timeout",
                "has_actionable_goal": True,
                "first_pass_understood": True,
            },
            task_summary="做一个本地可运行的 VN 项目助手 MVP",
            raw_reply_text="收到，我继续推进。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["做一个本地可运行的 VN 项目助手 MVP"],
            },
        )
        self.assertTrue(
            ("正式回复" in result.reply_text) or ("backend" in result.reply_text.lower()) or ("customer-ready" in result.reply_text.lower()),
            msg=result.reply_text,
        )
        self.assertNotIn("我继续推进", result.reply_text)

    def test_backend_blocked_reply_includes_phase_and_confirmed_progress(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "executing",
                "run_status": "blocked",
                "reply_truth_status": "backend_blocked",
                "reply_truth_reason": "waiting for file_request.json",
                "reply_truth_next_action": "补齐 file_request.json 并继续推进执行阶段",
                "progress_binding": {
                    "current_task_goal": "做一个本地可运行的 VN 项目助手 MVP",
                    "current_phase": "执行推进",
                    "last_confirmed_items": ["项目已接到后台流程", "需求摘要已写入当前 run"],
                    "current_blocker": "waiting for file_request.json",
                    "message_purpose": "progress",
                    "question_needed": "no",
                    "next_action": "补齐 file_request.json 并继续推进执行阶段",
                    "proof_refs": ["run_id=demo"],
                },
            },
            task_summary="做一个本地可运行的 VN 项目助手 MVP",
            raw_reply_text="收到，我继续推进。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["做一个本地可运行的 VN 项目助手 MVP"],
            },
        )
        self.assertIn("当前后端卡在：需求整理这一步还没落下来，当前还在等需求清单生成出来。", result.reply_text)
        self.assertIn("当前阶段：执行推进。", result.reply_text)
        self.assertIn("已确认进展：项目已接到后台流程、需求摘要已写入当前 run。", result.reply_text)
        self.assertIn("下一步我会先处理：把需求清单整理出来，再继续往下推进当前阶段。", result.reply_text)
        self.assertNotIn("我继续推进", result.reply_text)

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

    # --- Agent-first: model text preferred over templates ---

    def test_greeting_uses_model_text_when_available(self) -> None:
        """When the model produces clean greeting text, use it instead of a template."""
        result = render_frontend_output(
            raw_backend_state={"stage": "support_turn_local"},
            task_summary="你好",
            raw_reply_text="嗨，你随时可以告诉我你想做什么，我来帮你安排。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["你好"],
            },
        )
        # Model text should appear, NOT a hint-bank template
        self.assertIn("你随时可以告诉我", result.reply_text)
        self.assertNotIn("你用一句话告诉我这轮项目的目标", result.reply_text)

    def test_intake_uses_model_text_when_available(self) -> None:
        """For PROJECT_INTAKE, model text replaces the intake template."""
        result = render_frontend_output(
            raw_backend_state={"stage": "support_turn_local"},
            task_summary="我想做个新项目",
            raw_reply_text="好的，先跟我讲一下你这轮项目想达成什么效果，我来帮你梳理。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想做个新项目"],
            },
        )
        self.assertIn("先跟我讲一下", result.reply_text)
        # Template should NOT appear
        self.assertNotIn("收到。", result.reply_text.split("\n")[0] if result.reply_text else "")

    def test_template_fallback_when_model_text_empty(self) -> None:
        """When model text is empty, the template fallback is still used."""
        result = render_frontend_output(
            raw_backend_state={"stage": "support_turn_local"},
            task_summary="你好",
            raw_reply_text="",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["你好"],
            },
        )
        # Fallback template should produce a non-empty greeting
        self.assertTrue(result.reply_text.strip())
        # Should be one of the hint-bank greetings
        self.assertTrue(
            any(tok in result.reply_text for tok in ("你好", "我在", "目标")),
            msg=result.reply_text,
        )

    def test_template_fallback_when_model_text_fully_redacted(self) -> None:
        """When model text is all internal junk, it's redacted and template is used."""
        result = render_frontend_output(
            raw_backend_state={
                "stage": "advance_blocked",
                "blocked_needs_input": True,
            },
            task_summary="我想做个新项目",
            raw_reply_text="关于：待处理的事项 需要的信息：waiting for analysis.md",
            raw_next_question="关于：待处理的事项 需要的信息：waiting for analysis.md",
            notes={
                "lang": "zh",
                "recent_user_messages": ["我想做个新项目"],
            },
        )
        # Internal tokens must not appear
        self.assertNotIn("待处理的事项", result.reply_text)
        self.assertNotIn("waiting for", result.reply_text.lower())
        # Fallback template should produce something
        self.assertTrue(result.reply_text.strip())

    def test_project_detail_uses_model_text_over_compose_user_reply(self) -> None:
        """In PROJECT_DETAIL mode, model text is preferred over compose_user_reply template."""
        result = render_frontend_output(
            raw_backend_state={
                "stage": "analysis",
                "has_actionable_goal": True,
                "first_pass_understood": True,
            },
            task_summary="从无人机视频生成点云，优先速度",
            raw_reply_text="我已经开始分析你的需求了，先按速度优先来整理方案。",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["从无人机视频生成点云，优先速度"],
            },
        )
        # Model text should appear directly
        self.assertIn("我已经开始分析", result.reply_text)
        # Template markers should NOT appear
        self.assertNotIn("我理解的是", result.reply_text)

    def test_project_detail_low_signal_raw_reply_falls_back_to_pm_reply(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_turn_local",
                "has_actionable_goal": True,
                "first_pass_understood": True,
                "missing_fields": ["runtime_target"],
            },
            task_summary="我想做从3D视频生成点云文件的工作流，要尽可能快，支持无人机高速建图，语义可插入。",
            raw_reply_text="收到，继续推进。missing runtime_target",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": [
                    "我想做从3D视频生成点云文件的工作流，要尽可能快，支持无人机高速建图，语义可插入。"
                ],
            },
        )
        self.assertIn("我理解的是", result.reply_text)
        self.assertIn("接近实时输出", result.reply_text)
        self.assertNotIn("missing runtime_target", result.reply_text.lower())

    def test_en_greeting_uses_model_text_when_available(self) -> None:
        """English greeting uses model text instead of template."""
        result = render_frontend_output(
            raw_backend_state={"stage": "support_turn_local"},
            task_summary="hello",
            raw_reply_text="Hey! I'm ready to help. What are you working on?",
            raw_next_question="",
            notes={
                "lang": "en",
                "recent_user_messages": ["hello"],
            },
        )
        self.assertIn("I'm ready to help", result.reply_text)
        # Template should not appear
        self.assertNotIn("I'm here.", result.reply_text)


if __name__ == "__main__":
    unittest.main()
