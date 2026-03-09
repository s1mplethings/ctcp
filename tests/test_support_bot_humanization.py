import json
import re
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

from tools.telegram_cs_bot import (
    Bot,
    Config,
    SUPPORT_HANDOFF_TRACE_REL,
    SUPPORT_ROUTER_TRACE_REL,
    build_user_reply_payload,
    default_support_session_state,
    load_support_session_state,
    save_support_session_state,
    sanitize_customer_reply_text,
    smalltalk_reply,
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


class SupportBotHumanizationTests(unittest.TestCase):
    def test_sanitize_still_filters_internal_markers(self) -> None:
        raw = "\n".join(
            [
                "TRACE: guardrails_written",
                "run_created in RUN.json",
                "logs/telegram_cs_bot.ops.jsonl",
                "结论：已经推进到下一步",
            ]
        )
        cleaned, removed = sanitize_customer_reply_text(raw, "zh")
        low = cleaned.lower()
        self.assertNotIn("trace", low)
        self.assertNotIn("guardrails_written", low)
        self.assertNotIn("run.json", low)
        self.assertNotIn("logs/", low)
        self.assertTrue(removed)

    def test_payload_is_paragraph_style_and_not_list_style(self) -> None:
        raw = "\n".join(
            [
                "结论：我已接手。",
                "- 先确认渠道",
                "- 再确认转人工策略",
                "1. 最后同步节奏",
            ]
        )
        payload = build_user_reply_payload(
            reply_text=raw,
            next_question="",
            lang="zh",
            style_hint={"opener": "我先说明：", "transition": "我现在推进", "closer": "为了继续往前推，", "seed": "t1"},
            ops_status={},
        )
        reply = str(payload.get("reply_text", ""))
        self.assertIn("\n\n", reply)
        list_like = [ln for ln in reply.splitlines() if LIST_RE.match(ln)]
        self.assertFalse(list_like, msg=reply)

    def test_router_to_handoff_writes_structured_trace_and_passes_brief(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_human_") as td:
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
            bot.tg = _FakeTg()
            captured: dict[str, str] = {}
            try:
                chat_id = 201
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")

                bot._load_support_dispatch_config = lambda _run_dir: (  # type: ignore[method-assign]
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {
                            "support_lead_router": "mock_agent",
                            "support_lead_handoff": "mock_agent",
                            "support_lead_reply": "mock_agent",
                        },
                    },
                    "ok",
                )

                def fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                    target = run_dir / str(request["target_path"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if str(request["role"]) == "support_lead_router":
                        target.write_text(
                            json.dumps(
                                {
                                    "route": "api",
                                    "reason": "needs patch-level execution",
                                    "followup_question": "你希望先产出 patch 还是先给计划？",
                                    "handoff_brief": "brief: patch-first request from customer",
                                    "risk_flags": ["needs_patch"],
                                    "confidence": 0.92,
                                },
                                ensure_ascii=False,
                            ),
                            encoding="utf-8",
                        )
                        return {"status": "executed", "target_path": request["target_path"]}
                    if str(request["role"]) == "support_lead_handoff":
                        captured["reason"] = str(request.get("reason", ""))
                        target.write_text(
                            json.dumps(
                                {
                                    "reply_text": "结论：我已接手这次 patch 诉求。\n\n方案：我现在先按 patch-first 路径推进，并保持输出可直接验收。\n\n下一步：你希望我先修最影响验收的一处吗？",
                                    "next_question": "你希望我先修最影响验收的一处吗？",
                                    "actions": [],
                                    "debug_notes": "",
                                },
                                ensure_ascii=False,
                            ),
                            encoding="utf-8",
                        )
                        return {"status": "executed", "target_path": request["target_path"]}
                    raise AssertionError(f"unexpected role: {request.get('role')}")

                bot._execute_support_provider = fake_execute  # type: ignore[method-assign]

                handled = bot._handle_support_turn(chat_id=chat_id, lang="zh", run_dir=run_dir, text="请直接改代码并给我 patch")
                self.assertTrue(handled)
                router_trace = run_dir / SUPPORT_ROUTER_TRACE_REL
                handoff_trace = run_dir / SUPPORT_HANDOFF_TRACE_REL
                self.assertTrue(router_trace.exists())
                self.assertTrue(handoff_trace.exists())
                self.assertIn("\"route\": \"api\"", router_trace.read_text(encoding="utf-8", errors="replace"))
                self.assertIn("brief: patch-first request", handoff_trace.read_text(encoding="utf-8", errors="replace"))
                self.assertIn("brief: patch-first request", captured.get("reason", ""))
            finally:
                bot.close()

    def test_smalltalk_fast_path_prefers_human_reply_and_uses_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_smalltalk_") as td:
            base = Path(td)
            run_dir = base / "run_demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
            state = default_support_session_state()
            state["memory_slots"] = {
                "customer_name": "",
                "preferred_style": "",
                "current_topic": "客服bot真人化",
                "last_request": "",
            }
            state["user_goal"] = "客服bot真人化"
            save_support_session_state(run_dir, state)
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
                chat_id = 302
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "你好"}})
                self.assertEqual(len(fake.messages), 1)
                reply = fake.messages[0]
                self.assertNotIn("客服bot真人化", reply)
                self.assertIn("请问有什么可以帮到你", reply)
                self.assertNotIn("patch", reply.lower())
                self.assertNotIn("路径推进", reply)
            finally:
                bot.close()

    def test_send_customer_reply_dedupes_repeated_question(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_dedupe_q_") as td:
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
                chat_id = 303
                bot._send_customer_reply(
                    chat_id=chat_id,
                    lang="zh",
                    run_dir=run_dir,
                    stage="test_first_question",
                    reply_text="我已经开始处理。",
                    next_question="你更关注速度还是精度？",
                    ops_status={"source_text": "我想做客服bot"},
                )
                bot._send_customer_reply(
                    chat_id=chat_id,
                    lang="zh",
                    run_dir=run_dir,
                    stage="test_repeat_question",
                    reply_text="我会继续推进。",
                    next_question="你更关注速度还是精度？",
                    ops_status={"source_text": "继续"},
                )
                self.assertEqual(len(fake.messages), 2)
                self.assertIn("你更关注速度还是精度", fake.messages[0])
                self.assertNotIn("你更关注速度还是精度", fake.messages[1])
            finally:
                bot.close()

    def test_send_customer_reply_clears_stale_question_when_frontend_understood(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_clear_stale_q_") as td:
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
                chat_id = 304

                class _Rendered:
                    visible_state = "UNDERSTOOD"
                    reply_text = "收到，我先按这个方向立项并继续推进。"
                    followup_questions = ()
                    missing_fields = ()
                    redactions = 0
                    pipeline_state = {"visible_state": "UNDERSTOOD"}

                with mock.patch("tools.telegram_cs_bot.frontend_render_frontend_output", return_value=_Rendered()):
                    payload = bot._send_customer_reply(
                        chat_id=chat_id,
                        lang="zh",
                        run_dir=run_dir,
                        stage="support_turn_local",
                        reply_text="收到，我先按这个方向立项并继续推进。",
                        next_question="这轮你希望我优先速度、质量，还是成本？",
                        ops_status={"source_text": "输入是单目机载视频，先离线批处理，输出PLY"},
                    )
                self.assertEqual(len(fake.messages), 1)
                self.assertNotIn("速度、质量", fake.messages[0])
                self.assertEqual(str(payload.get("next_question", "")), "")
            finally:
                bot.close()

    def test_support_state_updates_memory_slots_from_user_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_memory_slots_") as td:
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
            bot.tg = _FakeTg()
            try:
                bot._send_customer_reply(
                    chat_id=304,
                    lang="zh",
                    run_dir=run_dir,
                    stage="memory_slot_extract",
                    reply_text="收到，我来处理。",
                    next_question="",
                    ops_status={"source_text": "你可以叫我小张，回复简短一点。我主要想做客服bot真人化。"},
                )
                state = json.loads((run_dir / "artifacts" / "support_session_state.json").read_text(encoding="utf-8", errors="replace"))
                slots = state.get("memory_slots", {})
                self.assertEqual(str(slots.get("customer_name", "")), "小张")
                self.assertEqual(str(slots.get("preferred_style", "")), "concise")
                self.assertIn("客服bot真人化", str(slots.get("current_topic", "")))
                self.assertIn("客服bot真人化", str(slots.get("last_request", "")))
            finally:
                bot.close()

    def test_smalltalk_reply_ignores_trivial_topic_hint(self) -> None:
        state = default_support_session_state()
        state["user_goal"] = "你好"
        reply = smalltalk_reply("你好", "zh", state)
        self.assertNotIn("推进“你好”", reply)
        self.assertIn("请问有什么可以帮到你", reply)

    def test_smalltalk_reply_does_not_echo_raw_goal_sentence(self) -> None:
        state = default_support_session_state()
        state["user_goal"] = "我想要你帮我做一个项目可以吗"
        reply = smalltalk_reply("你好", "zh", state)
        self.assertIn("请问有什么可以帮到你", reply)
        self.assertNotIn("我想要你帮我做一个项目可以吗", reply)
        self.assertNotIn("我们可以接着聊", reply)

    def test_smalltalk_does_not_set_user_goal_but_real_request_can_set(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_goal_guard_") as td:
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
            bot.tg = _FakeTg()
            try:
                bot._send_customer_reply(
                    chat_id=305,
                    lang="zh",
                    run_dir=run_dir,
                    stage="smalltalk_first_turn",
                    reply_text="你好！请问有什么可以帮到你的吗？",
                    next_question="",
                    ops_status={"source_text": "你好"},
                )
                state_1 = json.loads((run_dir / "artifacts" / "support_session_state.json").read_text(encoding="utf-8", errors="replace"))
                self.assertEqual(str(state_1.get("user_goal", "")), "")
                self.assertEqual(str(state_1.get("execution_goal", "")), "")
                self.assertEqual(str(state_1.get("execution_next_action", "")), "")

                bot._send_customer_reply(
                    chat_id=305,
                    lang="zh",
                    run_dir=run_dir,
                    stage="real_request_turn",
                    reply_text="收到，我来推进你的客服bot改造。",
                    next_question="",
                    ops_status={"source_text": "我想做一个更像真人的客服bot"},
                )
                state_2 = json.loads((run_dir / "artifacts" / "support_session_state.json").read_text(encoding="utf-8", errors="replace"))
                self.assertIn("客服bot", str(state_2.get("user_goal", "")))
                self.assertIn("客服bot", str(state_2.get("execution_goal", "")))
                self.assertTrue(str(state_2.get("execution_next_action", "")).strip())
            finally:
                bot.close()

    def test_unbound_smalltalk_does_not_create_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_unbound_smalltalk_") as td:
            base = Path(td)
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
                chat_id = 399
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "你好"}})
                session = bot.db.get_session(chat_id)
                self.assertEqual(str(session.get("run_dir", "")).strip(), "")
                self.assertTrue(fake.messages)
                self.assertIn("请问有什么可以帮到你", fake.messages[-1])
            finally:
                bot.close()

    def test_smalltalk_in_bound_run_pauses_auto_advance_temporarily(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_smalltalk_pause_") as td:
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
                chat_id = 398
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "你好"}})
                state = load_support_session_state(run_dir)
                pause_until = float(state.get("auto_advance_pause_until_ts", 0.0) or 0.0)
                self.assertGreater(pause_until, time.time())
                self.assertFalse(bot._allow_auto_advance(run_dir))
            finally:
                bot.close()

    def test_cancel_run_intent_clears_previous_session(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_cancel_run_") as td:
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
                chat_id = 306
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "我现在不想要继续之前那个项目你可以先清理一下吗"}})
                session = bot.db.get_session(chat_id)
                self.assertEqual(str(session.get("run_dir", "")).strip(), "")
                self.assertTrue(fake.messages)
                reply = fake.messages[-1]
                self.assertIn("\n\n", reply)
                self.assertIn("保存", reply)
                q_count = reply.count("?") + reply.count("？")
                self.assertEqual(q_count, 1)
                actions_log = (run_dir / "artifacts" / "support_actions.jsonl").read_text(encoding="utf-8", errors="replace")
                self.assertIn("archive_run_and_unbind", actions_log)
                for phrase in ("收到，了解你想咨询的是", "方便的话再补充一些细节", "为了不耽误进度", "我记得你在推进"):
                    self.assertNotIn(phrase, reply)
            finally:
                bot.close()

    def test_reply_prompt_contains_execution_focus(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_exec_focus_") as td:
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
            try:
                state = default_support_session_state()
                state["execution_goal"] = "把客服bot改得更像真人"
                state["execution_next_action"] = "先明确口吻与记忆策略，再落最小改动并验证"
                text = bot._build_support_reply_prompt(
                    chat_id=306,
                    lang="zh",
                    run_dir=run_dir,
                    user_text="请继续推进",
                    state=state,
                    route_doc={"route": "local"},
                    style_hint={"opener": "", "transition": "", "closer": "", "seed": "t"},
                )
                self.assertIn("execution_focus", text)
                self.assertIn("把客服bot改得更像真人", text)
                self.assertIn("先明确口吻与记忆策略", text)
            finally:
                bot.close()

    def test_full_project_dialogue_replaces_mojibake_with_project_kickoff_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_project_dialogue_") as td:
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
                chat_id = 307
                bot.db.bind_run(chat_id, run_dir)
                bot.db.set_lang(chat_id, "zh")

                bot._load_support_dispatch_config = lambda _run_dir: (  # type: ignore[method-assign]
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {
                            "support_lead_router": "mock_agent",
                            "support_lead_handoff": "mock_agent",
                            "support_lead_reply": "mock_agent",
                        },
                    },
                    "ok",
                )

                def fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                    target = run_dir / str(request["target_path"])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    role = str(request.get("role", ""))
                    if role == "support_lead_router":
                        target.write_text(
                            json.dumps(
                                {
                                    "route": "api",
                                    "reason": "handoff for project creation",
                                    "followup_question": "",
                                    "handoff_brief": "customer wants to create a project",
                                    "risk_flags": [],
                                    "confidence": 0.82,
                                },
                                ensure_ascii=False,
                            ),
                            encoding="utf-8",
                        )
                        return {"status": "executed", "target_path": request["target_path"]}
                    if role == "support_lead_handoff":
                        target.write_text(
                            json.dumps(
                                {
                                    "reply_text": "���ã������������������",
                                    "next_question": "���������",
                                    "actions": [],
                                    "debug_notes": "",
                                },
                                ensure_ascii=False,
                            ),
                            encoding="utf-8",
                        )
                        return {"status": "executed", "target_path": request["target_path"]}
                    raise AssertionError(f"unexpected role: {role}")

                bot._execute_support_provider = fake_execute  # type: ignore[method-assign]

                # Turn 1: greeting
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "你好"}})
                # Turn 2: project creation request
                bot.process_update({"message": {"chat": {"id": chat_id}, "text": "我想要创建一个项目"}})

                self.assertGreaterEqual(len(fake.messages), 2)
                project_reply = fake.messages[-1]
                self.assertIn("帮你", project_reply)
                self.assertIn("项目", project_reply)
                self.assertNotIn("最小版本", project_reply)
                self.assertNotIn("Web 项目", project_reply)
                self.assertNotIn("我已经推进到下一里程碑", project_reply)
            finally:
                bot.close()

    def test_send_customer_reply_hides_internal_workflow_text(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_hide_internal_") as td:
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
                bot._send_customer_reply(
                    chat_id=600,
                    lang="zh",
                    run_dir=run_dir,
                    stage="advance_blocked",
                    reply_text="plan agent command failed rc=2",
                    next_question="Use CONTEXT + CONSTRAINTS + EXTERNALS to produce a minimal PLAN",
                    ops_status={
                        "source_text": "我要做无人机视角的3D视频到点云工作流，优先速度",
                        "missing_fields": ["runtime_target"],
                        "reason": "plan agent command failed rc=2",
                    },
                )
                self.assertEqual(len(fake.messages), 1)
                text = fake.messages[0]
                self.assertNotIn("rc=2", text.lower())
                self.assertNotIn("command failed", text.lower())
                self.assertNotIn("CONTEXT + CONSTRAINTS + EXTERNALS", text)
                self.assertIn("接近实时输出", text)
            finally:
                bot.close()

    def test_send_customer_reply_prefers_understood_with_one_followup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_understood_") as td:
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
                user_goal = "我想做从3D视频生成点云文件的工作流，要尽可能快，支持无人机高速建图，语义可插入。"
                bot._send_customer_reply(
                    chat_id=601,
                    lang="zh",
                    run_dir=run_dir,
                    stage="support_turn_local",
                    reply_text="收到，继续推进。missing runtime_target",
                    next_question="",
                    ops_status={
                        "source_text": user_goal,
                        "has_actionable_goal": True,
                        "first_pass_understood": True,
                        "missing_fields": ["runtime_target"],
                    },
                )
                self.assertEqual(len(fake.messages), 1)
                text = fake.messages[0]
                self.assertIn("收到，我先按这个方向立项", text)
                self.assertIn("接近实时输出", text)
                self.assertNotIn("无法继续", text)
                self.assertNotIn("不能继续", text)
            finally:
                bot.close()

    def test_send_customer_reply_prefers_detailed_requirement_over_vague_history(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_best_requirement_") as td:
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
                bot._append_support_inbox(run_dir, "user", "我想做个项目", "zh")
                detail = "我想要的是一个从3d视频生成点云文件的工作流，然后要尽可能快，目标是无人机视角高速建图，语义可插入。"
                bot._send_customer_reply(
                    chat_id=602,
                    lang="zh",
                    run_dir=run_dir,
                    stage="support_turn_local",
                    reply_text="收到，继续推进。",
                    next_question="你想做什么类型的项目？",
                    ops_status={
                        "source_text": detail,
                        "has_actionable_goal": True,
                        "first_pass_understood": True,
                    },
                )
                self.assertEqual(len(fake.messages), 1)
                text = fake.messages[0]
                self.assertIn("3d", text.lower())
                self.assertIn("点云", text)
                self.assertIn("无人机", text)
                self.assertNotIn("我想做个项目", text)
                self.assertNotIn("你想做什么类型的项目", text)
            finally:
                bot.close()

    def test_send_customer_reply_does_not_repeat_already_answered_key_questions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_no_repeat_questions_") as td:
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
                answered = "输入是单目无人机视频，优先接近实时输出。"
                bot._append_support_inbox(run_dir, "user", answered, "zh")
                bot._send_customer_reply(
                    chat_id=603,
                    lang="zh",
                    run_dir=run_dir,
                    stage="support_turn_local",
                    reply_text="继续推进。missing input_mode missing runtime_target",
                    next_question="你现在的输入主要是单目无人机视频，还是多段多视角素材？",
                    ops_status={
                        "source_text": answered,
                        "has_actionable_goal": True,
                        "first_pass_understood": True,
                        "missing_fields": ["input_mode", "runtime_target"],
                    },
                )
                text = fake.messages[0]
                self.assertNotIn("单目无人机视频，还是多段多视角素材", text)
                self.assertNotIn("接近实时输出，还是允许离线处理", text)
            finally:
                bot.close()

    def test_send_customer_reply_asks_at_most_two_key_questions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_two_questions_") as td:
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
                user_goal = "我要做无人机视角3D视频到点云流程，优先速度，语义信息可插入。"
                bot._send_customer_reply(
                    chat_id=604,
                    lang="zh",
                    run_dir=run_dir,
                    stage="support_turn_local",
                    reply_text="收到，继续推进。",
                    next_question="请提供更多信息",
                    ops_status={
                        "source_text": user_goal,
                        "has_actionable_goal": True,
                        "first_pass_understood": True,
                    },
                )
                text = fake.messages[0]
                q_count = text.count("？") + text.count("?")
                self.assertLessEqual(q_count, 2, msg=text)
                self.assertNotIn("请提供更多信息", text)
            finally:
                bot.close()


LIST_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s+")


if __name__ == "__main__":
    unittest.main()
