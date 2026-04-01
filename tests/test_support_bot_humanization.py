from __future__ import annotations

import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import scripts.ctcp_support_bot as support_bot


def _append_jsonl(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_provider_doc(
    run_dir: Path,
    reply_text: str,
    next_question: str = "",
    actions: list[dict[str, object]] | None = None,
) -> None:
    target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "reply_text": reply_text,
                "next_question": next_question,
                "actions": actions or [],
                "debug_notes": "",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class SupportBotHumanizationTests(unittest.TestCase):
    def test_default_support_session_state_contains_active_truth_and_history_layers(self) -> None:
        state = support_bot.default_support_session_state("schema-demo")
        self.assertEqual(str(state.get("active_stage", "")), "INTAKE")
        self.assertEqual(str(state.get("latest_message_intent", "")), "continue")
        self.assertIn("history_layers", state)
        layers = dict(state.get("history_layers", {}))
        self.assertIn("raw_turns", layers)
        self.assertIn("working_memory", layers)
        self.assertIn("task_summary", layers)
        self.assertIn("user_preferences", layers)

    def test_sync_active_task_truth_keeps_mainline_on_smalltalk_interrupt(self) -> None:
        session_state = support_bot.default_support_session_state("mainline-demo")
        session_state["active_task_id"] = "run-vn"
        session_state["active_run_id"] = "run-vn"
        session_state["active_goal"] = "继续优化 VN 前台"
        session_state["bound_run_id"] = "run-vn"
        session_state["bound_run_dir"] = "D:/tmp/run-vn"
        support_bot.sync_active_task_truth(
            session_state,
            user_text="你好",
            source="telegram",
            conversation_mode="GREETING",
            frontdesk_state={
                "state": "InterruptRecover",
                "interrupt_kind": "",
                "current_goal": "继续优化 VN 前台",
                "active_task_id": "run-vn",
            },
            project_context={
                "run_id": "run-vn",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "open", "reason": ""},
                },
                "whiteboard": {},
            },
            delivery_state={},
        )
        self.assertEqual(str(session_state.get("latest_message_intent", "")), "small_talk")
        self.assertEqual(str(session_state.get("active_goal", "")), "继续优化 VN 前台")
        self.assertEqual(str(session_state.get("active_task_id", "")), "run-vn")

    def test_process_message_greeting_routes_through_provider(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_greeting_fast_path_") as td:
            runs_root = Path(td) / "runs"
            calls: list[str] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                calls.append(provider)
                _write_provider_doc(run_dir, "你好，这边可以直接接你的需求。")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=({"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent"}}, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, run_dir = support_bot.process_message(
                    chat_id="greeting-demo",
                    user_text="你好",
                    source="telegram",
                    provider_override="api_agent",
                )

            self.assertEqual(str(doc.get("reply_text", "")), "你好，这边可以直接接你的需求。")
            self.assertEqual(calls, ["api_agent"])
            state = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(state.get("latest_conversation_mode", "")), "GREETING")
            self.assertEqual(str(state.get("provider_runtime_buffer", {}).get("last_provider", "")), "api_agent")

    def test_support_bot_fallback_text_stays_customer_facing(self) -> None:
        text = support_bot.normalize_reply_text("stack trace: command failed rc=7", "")
        self.assertTrue(text.strip())
        self.assertNotIn("项目经理方式推进", text)
        self.assertNotIn("command failed", text.lower())
        self.assertNotIn("\n\n\n", text)

    def test_support_bot_default_prompt_states_boundary_first_goal(self) -> None:
        text = support_bot.default_prompt_template()
        self.assertIn("mechanical safeguards decide the boundary", text)
        self.assertIn("do not require a fixed reply template", text)
        self.assertIn("Primary support reply path is api_agent", text)
        self.assertIn("greeting, capability, or smalltalk turns", text)

    def test_build_support_prompt_treats_capability_query_as_latest_turn_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_capability_prompt_") as td:
            run_dir = Path(td)
            session_state = support_bot.default_support_session_state("capability-demo")
            session_state["project_memory"]["project_brief"] = "我想做一个无人机视频转点云项目"
            prompt = support_bot.build_support_prompt(
                run_dir,
                "capability-demo",
                "你是谁",
                source="telegram",
                conversation_mode="CAPABILITY_QUERY",
                session_state=session_state,
            )

        self.assertIn('"conversation_mode": "CAPABILITY_QUERY"', prompt)
        self.assertIn('"allow_existing_project_reference": false', prompt)
        self.assertIn('"latest_turn_only": true', prompt)

    def test_build_support_prompt_greeting_hides_old_project_and_delivery_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_greeting_prompt_") as td:
            run_dir = Path(td)
            session_state = support_bot.default_support_session_state("greeting-demo")
            session_state["bound_run_id"] = "r-old"
            session_state["bound_run_dir"] = "D:/tmp/r-old"
            session_state["project_memory"]["project_brief"] = "我想要你继续优化我的vn项目"
            session_state["project_constraints_memory"]["constraint_brief"] = "zip交付"
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "我想要你继续优化我的vn项目",
                },
            )
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "你好",
                },
            )
            prompt = support_bot.build_support_prompt(
                run_dir,
                "greeting-demo",
                "你好",
                source="telegram",
                conversation_mode="GREETING",
                session_state=session_state,
                project_context={"run_id": "r-old", "run_dir": "D:/tmp/r-old", "goal": "我想要你继续优化我的vn项目"},
                delivery_state={"channel": "telegram", "channel_can_send_files": True, "package_ready": True, "package_delivery_mode": "existing_package"},
            )

        self.assertIn('"conversation_mode": "GREETING"', prompt)
        self.assertIn('"allow_existing_project_reference": false', prompt)
        self.assertIn('"bound_run_id": ""', prompt)
        self.assertIn('"project_brief": ""', prompt)
        self.assertNotIn('"project_run":', prompt)
        self.assertNotIn('"public_delivery":', prompt)
        self.assertNotIn('我想要你继续优化我的vn项目', prompt)

    def test_build_support_prompt_includes_frontdesk_state_and_style_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_frontdesk_prompt_") as td:
            run_dir = Path(td)
            session_state = support_bot.default_support_session_state("frontdesk-demo")
            session_state["bound_run_id"] = "r-frontdesk"
            session_state["bound_run_dir"] = "D:/tmp/r-frontdesk"
            session_state["project_memory"]["project_brief"] = "我想要你继续优化我的vn项目"
            session_state["task_summary"] = "我想要你继续优化我的vn项目"
            project_context = {
                "run_id": "r-frontdesk",
                "run_dir": "D:/tmp/r-frontdesk",
                "goal": "我想要你继续优化我的vn项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "open", "owner": "", "reason": ""},
                },
                "whiteboard": {},
            }
            support_bot.sync_frontdesk_state(
                session_state,
                user_text="后面用中文回答，简短一点，别太机械",
                conversation_mode="SMALLTALK",
                project_context=project_context,
            )
            prompt = support_bot.build_support_prompt(
                run_dir,
                "frontdesk-demo",
                "后面用中文回答，简短一点，别太机械",
                source="telegram",
                conversation_mode="SMALLTALK",
                session_state=session_state,
                project_context=project_context,
            )

        self.assertIn('"frontdesk_state": {', prompt)
        self.assertIn('"state": "waiting_user_reply"', prompt)
        self.assertIn('"resumable_state": "showing_progress"', prompt)
        self.assertIn('"verbosity": "brief"', prompt)
        self.assertIn('"tone": "natural"', prompt)
        self.assertIn('"current_goal": ""', prompt)
        self.assertIn('"history_layers": {', prompt)
        self.assertIn('"recent_raw_turns": [', prompt)

    def test_default_support_dispatch_config_prefers_api_with_local_fallback(self) -> None:
        cfg = support_bot.default_support_dispatch_config()
        role_providers = dict(cfg.get("role_providers", {}))
        self.assertEqual(str(role_providers.get("support_lead", "")), "api_agent")
        self.assertEqual(str(role_providers.get("support_local_fallback", "")), "ollama_agent")
        self.assertEqual(
            support_bot.support_provider_candidates(cfg),
            ["api_agent", "ollama_agent"],
        )

    def test_build_final_reply_doc_uses_frontend_reply_for_project_turn(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_rendered_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "输入是单目视频，先离线处理，输出PLY。",
                },
            )

            class _Rendered:
                visible_state = "UNDERSTOOD"
                reply_text = "收到，我先按你这轮补充的输入整理成客户可见答复。"
                followup_questions = ()
                pipeline_state = {
                    "visible_state": "UNDERSTOOD",
                    "selected_requirement_source": "latest_user_message",
                }

            provider_doc = {
                "reply_text": "收到，继续推进。missing runtime_target",
                "next_question": "这轮你更关注速度还是质量？",
                "actions": [],
                "debug_notes": "",
            }
            with mock.patch.object(support_bot, "render_frontend_output", return_value=_Rendered()):
                doc = support_bot.build_final_reply_doc(
                    run_dir=run_dir,
                    provider="ollama_agent",
                    provider_result={"status": "executed", "reason": "ok"},
                    provider_doc=provider_doc,
                )

            self.assertEqual(doc["reply_text"], "收到，我先按你这轮补充的输入整理成客户可见答复。")
            self.assertEqual(doc["next_question"], "")
            self.assertIn("selected_requirement=latest_user_message", str(doc["debug_notes"]))

    def test_build_final_reply_doc_runtime_guard_rewrites_low_info_task_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_runtime_guard_low_info_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "继续推进这个项目",
                },
            )
            with mock.patch.object(support_bot, "render_frontend_output", None):
                doc = support_bot.build_final_reply_doc(
                    run_dir=run_dir,
                    provider="api_agent",
                    provider_result={"status": "executed", "reason": "ok"},
                    provider_doc={
                        "reply_text": "好的，我在处理。",
                        "next_question": "",
                        "actions": [],
                        "debug_notes": "",
                    },
                    conversation_mode="PROJECT_DETAIL",
                    task_summary_hint="VN 项目推进",
                    project_context={
                        "run_id": "run-guard-low-info",
                        "status": {
                            "run_status": "running",
                            "verify_result": "",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "open", "owner": "", "reason": ""},
                        },
                        "decisions": {"count": 0, "decisions": []},
                        "whiteboard": {},
                    },
                )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("目前在", reply)
            self.assertIn("下一步", reply)
            guard = dict(doc.get("runtime_progress_guard", {}))
            self.assertTrue(bool(guard.get("applied", False)))
            self.assertIn("low_information_reply", list(guard.get("reasons", [])))

    def test_build_final_reply_doc_runtime_guard_blocks_ungrounded_completion_claim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_runtime_guard_completion_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "现在到哪了",
                },
            )
            with mock.patch.object(support_bot, "render_frontend_output", None):
                doc = support_bot.build_final_reply_doc(
                    run_dir=run_dir,
                    provider="api_agent",
                    provider_result={"status": "executed", "reason": "ok"},
                    provider_doc={
                        "reply_text": "已经完成并可交付了。",
                        "next_question": "",
                        "actions": [],
                        "debug_notes": "",
                    },
                    conversation_mode="STATUS_QUERY",
                    task_summary_hint="VN 项目推进",
                    project_context={
                        "run_id": "run-guard-completion",
                        "status": {
                            "run_status": "running",
                            "verify_result": "",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "open", "owner": "", "reason": ""},
                        },
                        "decisions": {"count": 0, "decisions": []},
                        "whiteboard": {},
                    },
                )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("目前在", reply)
            self.assertNotIn("可交付", reply)
            guard = dict(doc.get("runtime_progress_guard", {}))
            self.assertTrue(bool(guard.get("applied", False)))
            self.assertIn("ungrounded_completion_claim", list(guard.get("reasons", [])))

    def test_build_final_reply_doc_runtime_guard_normalizes_same_state_repeat(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_runtime_guard_repeat_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "继续汇报进度",
                },
            )
            context = {
                "run_id": "run-guard-repeat",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "open", "owner": "", "reason": ""},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }
            with mock.patch.object(support_bot, "render_frontend_output", None):
                first_doc = support_bot.build_final_reply_doc(
                    run_dir=run_dir,
                    provider="api_agent",
                    provider_result={"status": "executed", "reason": "ok"},
                    provider_doc={
                        "reply_text": "继续处理中。",
                        "next_question": "",
                        "actions": [],
                        "debug_notes": "",
                    },
                    conversation_mode="STATUS_QUERY",
                    task_summary_hint="VN 项目推进",
                    project_context=context,
                )
                support_bot.write_json(run_dir / support_bot.SUPPORT_REPLY_REL_PATH, first_doc)
                second_doc = support_bot.build_final_reply_doc(
                    run_dir=run_dir,
                    provider="api_agent",
                    provider_result={"status": "executed", "reason": "ok"},
                    provider_doc={
                        "reply_text": str(first_doc.get("reply_text", "")),
                        "next_question": "",
                        "actions": [],
                        "debug_notes": "",
                    },
                    conversation_mode="STATUS_QUERY",
                    task_summary_hint="VN 项目推进",
                    project_context=context,
                )

            reply = str(second_doc.get("reply_text", ""))
            self.assertIn("当前状态和上一条一致", reply)
            guard = dict(second_doc.get("runtime_progress_guard", {}))
            self.assertTrue(bool(guard.get("applied", False)))
            self.assertIn("repeat_same_state", list(guard.get("reasons", [])))

    def test_build_final_reply_doc_suppresses_garbled_greeting_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_garbled_greeting_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "你好",
                },
            )
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "���ã��������ڽ���֧�ֻỰ",
                    "next_question": "����������һ�¾��������",
                    "actions": [],
                    "debug_notes": "",
                },
                conversation_mode="GREETING",
            )

            self.assertIn("这边没拿到可直接发出的回复", str(doc["reply_text"]))
            self.assertNotIn("���", str(doc["reply_text"]))

    def test_build_final_reply_doc_suppresses_mojibake_greeting_reply_without_replacement_char(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_mojibake_greeting_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "你好",
                },
            )
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "ãܸ˰㿪ʼӾС˵ϷĿ鷽档ܸҸ󣬱ʹЩ߻رĹܣǿԸЧع滮һ",
                    "next_question": "ã־ضϿؼӣʲô",
                    "actions": [],
                    "debug_notes": "",
                },
                conversation_mode="GREETING",
                lang_hint="zh",
            )

            self.assertIn("这边没拿到可直接发出的回复", str(doc["reply_text"]))
            self.assertNotIn("ã", str(doc["reply_text"]))

    def test_build_final_reply_doc_sanitizes_forbidden_raw_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_sanitize_") as td:
            run_dir = Path(td)
            with mock.patch.object(support_bot, "render_frontend_output", None):
                doc = support_bot.build_final_reply_doc(
                    run_dir=run_dir,
                    provider="manual_outbox",
                    provider_result={"status": "exec_failed", "reason": "stack trace: command failed rc=7"},
                    provider_doc={
                        "reply_text": "TRACE: logs/support_bot.stdout.log diff --git",
                        "next_question": "",
                        "actions": [],
                        "debug_notes": "",
                    },
                )

            low = str(doc["reply_text"]).lower()
            self.assertTrue(str(doc["reply_text"]).strip())
            for token in ("trace", "logs/", "diff --git", "stack trace"):
                self.assertNotIn(token, low)

    def test_build_final_reply_doc_strips_delivery_actions_on_greeting_without_delivery_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_greeting_delivery_strip_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "你好",
                },
            )
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "你好，之前项目已经打包好了。",
                    "next_question": "",
                    "actions": [{"type": "send_project_package", "format": "zip"}],
                    "debug_notes": "",
                },
                conversation_mode="GREETING",
                delivery_state={"channel": "telegram", "channel_can_send_files": True, "package_ready": True},
            )

            self.assertEqual(list(doc.get("actions", [])), [])

    def test_process_message_writes_support_reply_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_process_") as td:
            runs_root = Path(td) / "runs"

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                _write_provider_doc(run_dir, "我先接住这件事。", "你最想先盯住哪个点？")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "frontend_route_conversation_mode", return_value="PROJECT_DETAIL"
            ), mock.patch.object(
                support_bot, "sync_project_context", side_effect=lambda **kwargs: ({}, kwargs["session_state"])
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, run_dir = support_bot.process_message(
                    chat_id="humanization-demo",
                    user_text="请帮我做一个客服回复节奏整理项目。",
                    source="stdin",
                )

            self.assertEqual(run_dir, (runs_root / "ctcp" / "support_sessions" / "humanization-demo").resolve())
            self.assertEqual(str(doc["reply_text"]), "我先接住这件事。")
            for rel in (
                support_bot.SUPPORT_INBOX_REL_PATH,
                support_bot.SUPPORT_PROMPT_REL_PATH,
                support_bot.SUPPORT_REPLY_REL_PATH,
            ):
                self.assertTrue((run_dir / rel).exists(), msg=str(rel))
            self.assertTrue((run_dir / "events.jsonl").exists())

    def test_process_message_degrades_from_api_to_local_reply_with_explicit_notice(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_local_fallback_") as td:
            runs_root = Path(td) / "runs"
            calls: list[str] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                calls.append(provider)
                if provider == "api_agent":
                    return {"status": "disabled", "reason": "api disabled"}
                if provider == "ollama_agent":
                    failover = dict(request.get("provider_failover", {}))
                    self.assertEqual(str(failover.get("failed_provider", "")), "api_agent")
                    self.assertIn("api disabled", str(failover.get("failed_reason", "")))
                    _write_provider_doc(run_dir, "我先继续帮你看这轮需求，本地这边能先接住。")
                    return {
                        "status": "executed",
                        "reason": "ok",
                        "target_path": str(request.get("target_path", "")),
                    }
                raise AssertionError(f"unexpected provider: {provider}")

            config = {
                "mode": "manual_outbox",
                "role_providers": {"support_lead": "api_agent", "support_local_fallback": "ollama_agent"},
            }
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, _run_dir = support_bot.process_message(
                    chat_id="outbox-demo",
                    user_text="我想做一个帮我整理VN剧情的项目。",
                    source="stdin",
                )

            self.assertEqual(calls, ["api_agent", "ollama_agent"])
            self.assertEqual(str(doc.get("provider", "")), "ollama_agent")
            self.assertEqual(str(doc.get("provider_status", "")), "executed")
            self.assertIn("API", str(doc.get("reply_text", "")))
            self.assertIn("本地", str(doc.get("reply_text", "")))
            self.assertIn("本地这边能先接住", str(doc.get("reply_text", "")))
            self.assertNotIn("暂时还没连上稳定的回复能力", str(doc.get("reply_text", "")))
            self.assertNotIn("我先帮你整理一下", str(doc.get("reply_text", "")))

    def test_process_message_retries_api_when_greeting_reply_leaks_old_project_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_greeting_repair_") as td:
            runs_root = Path(td) / "runs"
            calls: list[tuple[str, dict[str, object]]] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del config
                calls.append((provider, dict(request)))
                if len(calls) == 1:
                    _write_provider_doc(
                        run_dir,
                        "您好，我们这边可以帮您继续推进引擎项目，先从故事线结构设计开始也可以。",
                    )
                else:
                    self.assertEqual(str(dict(request.get("reply_guard", {})).get("guard_reason", "")), "stale project context on greeting reply")
                    _write_provider_doc(run_dir, "你好，这轮你想先处理什么，直接告诉我。")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            config = {
                "mode": "manual_outbox",
                "role_providers": {"support_lead": "api_agent", "support_local_fallback": "ollama_agent"},
            }
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, _run_dir = support_bot.process_message(
                    chat_id="greeting-repair-demo",
                    user_text="你好",
                    source="stdin",
                )

            self.assertEqual([item[0] for item in calls], ["api_agent", "api_agent"])
            self.assertEqual(str(doc.get("provider", "")), "api_agent")
            self.assertEqual(str(doc.get("reply_text", "")), "你好，这轮你想先处理什么，直接告诉我。")
            self.assertNotIn("引擎项目", str(doc.get("reply_text", "")))
            self.assertNotIn("你好，随时可以开始。你说说看要做什么？", str(doc.get("reply_text", "")))

    def test_process_message_degrades_to_local_when_api_greeting_reply_stays_invalid(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_greeting_local_after_invalid_") as td:
            runs_root = Path(td) / "runs"
            calls: list[str] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del config
                calls.append(provider)
                if provider == "api_agent":
                    _write_provider_doc(
                        run_dir,
                        "您好，我们这边可以帮您继续推进引擎项目，先从故事线结构设计开始也可以。",
                    )
                    return {
                        "status": "executed",
                        "reason": "ok",
                        "target_path": str(request.get("target_path", "")),
                    }
                failover = dict(request.get("provider_failover", {}))
                self.assertEqual(str(failover.get("failed_provider", "")), "api_agent")
                self.assertEqual(str(failover.get("failed_kind", "")), "invalid_reply")
                _write_provider_doc(run_dir, "这边先用本地回复接住你这轮，你直接说当前要处理哪件事。")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            config = {
                "mode": "manual_outbox",
                "role_providers": {"support_lead": "api_agent", "support_local_fallback": "ollama_agent"},
            }
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, _run_dir = support_bot.process_message(
                    chat_id="greeting-local-after-invalid-demo",
                    user_text="你好",
                    source="stdin",
                )

            self.assertEqual(calls, ["api_agent", "api_agent", "ollama_agent"])
            reply = str(doc.get("reply_text", ""))
            self.assertEqual(str(doc.get("provider", "")), "ollama_agent")
            self.assertIn("API", reply)
            self.assertIn("本地", reply)
            self.assertIn("没给到可直接发出的回复", reply)
            self.assertNotIn("没连上", reply)
            self.assertNotIn("你好，随时可以开始。你说说看要做什么？", reply)

    def test_process_message_reports_api_and_local_disconnect_without_old_shell(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_disconnect_notice_") as td:
            runs_root = Path(td) / "runs"

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del run_dir, request, config
                if provider == "api_agent":
                    return {"status": "exec_failed", "reason": "connect timeout"}
                if provider == "ollama_agent":
                    return {"status": "exec_failed", "reason": "local model unavailable"}
                raise AssertionError(f"unexpected provider: {provider}")

            config = {
                "mode": "manual_outbox",
                "role_providers": {"support_lead": "api_agent", "support_local_fallback": "ollama_agent"},
            }
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, _run_dir = support_bot.process_message(
                    chat_id="disconnect-demo",
                    user_text="帮我继续看这个项目",
                    source="stdin",
                )

            reply = str(doc.get("reply_text", ""))
            self.assertEqual(str(doc.get("provider_status", "")), "exec_failed")
            self.assertIn("API", reply)
            self.assertIn("本地", reply)
            self.assertIn("没连上", reply)
            self.assertNotIn("暂时还没连上稳定的回复能力", reply)
            self.assertNotIn("我先帮你整理一下", reply)

    def test_process_message_project_turn_binds_run_and_injects_shared_whiteboard(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_bridge_bind_") as td:
            runs_root = Path(td) / "runs"
            support_context = {
                "run_id": "r-demo",
                "run_dir": "D:/tmp/r-demo",
                "goal": "做一个 VN 项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "", "owner": "", "reason": ""},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {
                    "path": "artifacts/support_whiteboard.json",
                    "query": "帮我理顺 VN 剧情结构",
                    "hits": [{"path": "docs/10_team_mode.md", "start_line": 1, "snippet": "support bot"}],
                    "lookup_error": "",
                    "snapshot": {
                        "path": "artifacts/support_whiteboard.json",
                        "entry_count": 2,
                        "entries": [{"role": "support", "kind": "support_turn", "text": "note"}],
                    },
                },
            }

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                self.assertEqual(str(request.get("project_run", {}).get("run_id", "")), "r-demo")
                self.assertEqual(str(request.get("whiteboard", {}).get("path", "")), "artifacts/support_whiteboard.json")
                self.assertEqual(len(list(request.get("whiteboard", {}).get("hits", []))), 1)
                _write_provider_doc(run_dir, "收到，我已经把这轮信息接到后台项目里。", "你最想先盯哪段剧情？")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "frontend_route_conversation_mode", return_value="PROJECT_DETAIL"
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_new_run", return_value={"run_id": "r-demo", "run_dir": "D:/tmp/r-demo"}
            ) as new_run_spy, mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_record_support_turn", return_value={"whiteboard": support_context["whiteboard"]}
            ) as record_spy, mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_get_support_context", side_effect=[dict(support_context), dict(support_context)]
            ) as context_spy, mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_advance", return_value={"run_id": "r-demo", "status": support_context["status"]}
            ) as advance_spy, mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, run_dir = support_bot.process_message(
                    chat_id="bridge-demo",
                    user_text="我想做一个帮我整理 VN 剧情结构的项目。",
                    source="stdin",
                )

            session_state = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(session_state.get("bound_run_id", "")), "r-demo")
            self.assertEqual(str(doc.get("provider_status", "")), "executed")
            new_run_spy.assert_called_once_with(goal="我想做一个帮我整理 VN 剧情结构的项目。")
            record_spy.assert_called_once()
            advance_spy.assert_called_once_with("r-demo", max_steps=4)
            self.assertEqual(context_spy.call_count, 2)

    def test_process_message_preserves_project_brief_across_low_signal_followup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_memory_isolation_") as td:
            runs_root = Path(td) / "runs"
            project_request = "i want to create a project to help me make vn games, especially in clarify storyline"
            support_context = {
                "run_id": "r-memory",
                "run_dir": "D:/tmp/r-memory",
                "goal": project_request,
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "", "owner": "", "reason": ""},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {"path": "artifacts/support_whiteboard.json", "hits": [], "snapshot": {}},
            }

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                _write_provider_doc(run_dir, "我先接住这件事。", "")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "frontend_route_conversation_mode", side_effect=["PROJECT_INTAKE", "PROJECT_DETAIL"]
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_new_run", return_value={"run_id": "r-memory", "run_dir": "D:/tmp/r-memory"}
            ) as new_run_spy, mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_record_support_turn", return_value={"whiteboard": support_context["whiteboard"]}
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_get_support_context", side_effect=lambda *_args, **_kwargs: dict(support_context)
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_advance", return_value={"run_id": "r-memory", "status": support_context["status"]}
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                _doc1, run_dir = support_bot.process_message(
                    chat_id="memory-demo",
                    user_text=project_request,
                    source="telegram",
                )
                doc2, _run_dir = support_bot.process_message(
                    chat_id="memory-demo",
                    user_text="没有，你先做着",
                    source="telegram",
                )

            state = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(state.get("task_summary", "")), project_request)
            self.assertEqual(str(state.get("project_memory", {}).get("project_brief", "")), project_request)
            self.assertEqual(str(state.get("turn_memory", {}).get("latest_user_turn", "")), "没有，你先做着")
            self.assertEqual(str(state.get("latest_conversation_mode", "")), "PROJECT_DETAIL")
            self.assertEqual(str(doc2.get("provider_status", "")), "executed")
            new_run_spy.assert_called_once_with(goal=project_request)

    def test_process_message_separates_goal_constraints_and_execution_directive_memory(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_memory_zones_") as td:
            runs_root = Path(td) / "runs"
            project_request = "我想做一个帮我理顺 VN 剧情结构的项目。"
            constraint_turn = "window开发，然后ui可以使用qt6"
            directive_turn = "你先做出第一版给我看，然后我在做调整"
            support_context = {
                "run_id": "r-memory-zones",
                "run_dir": "D:/tmp/r-memory-zones",
                "goal": project_request,
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "", "owner": "", "reason": ""},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {"path": "artifacts/support_whiteboard.json", "hits": [], "snapshot": {}},
            }

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                _write_provider_doc(run_dir, "我先接住这件事。", "")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "frontend_route_conversation_mode", side_effect=["PROJECT_INTAKE", "PROJECT_DETAIL", "SMALLTALK"]
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_new_run", return_value={"run_id": "r-memory-zones", "run_dir": "D:/tmp/r-memory-zones"}
            ) as new_run_spy, mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_record_support_turn", return_value={"whiteboard": support_context["whiteboard"]}
            ) as record_spy, mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_get_support_context", side_effect=lambda *_args, **_kwargs: dict(support_context)
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_advance", return_value={"run_id": "r-memory-zones", "status": support_context["status"]}
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                support_bot.process_message(
                    chat_id="memory-zones-demo",
                    user_text=project_request,
                    source="telegram",
                )
                support_bot.process_message(
                    chat_id="memory-zones-demo",
                    user_text=constraint_turn,
                    source="telegram",
                )
                doc3, run_dir = support_bot.process_message(
                    chat_id="memory-zones-demo",
                    user_text=directive_turn,
                    source="telegram",
                )

            state = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(state.get("project_memory", {}).get("project_brief", "")), project_request)
            self.assertEqual(str(state.get("project_constraints_memory", {}).get("constraint_brief", "")), constraint_turn)
            self.assertEqual(str(state.get("execution_memory", {}).get("latest_user_directive", "")), directive_turn)
            self.assertEqual(str(state.get("latest_conversation_mode", "")), "PROJECT_DETAIL")
            self.assertEqual(str(doc3.get("provider_status", "")), "executed")
            self.assertEqual(record_spy.call_count, 3)
            new_run_spy.assert_called_once_with(goal=project_request)

    def test_process_message_api_override_degrades_to_local_on_unusable_api_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_api_strict_") as td:
            runs_root = Path(td) / "runs"
            calls: list[str] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                calls.append(provider)
                if provider == "api_agent":
                    _write_provider_doc(run_dir, "I don\ufffdt have your outline yet, but I can start from a first VN story draft.")
                    return {
                        "status": "executed",
                        "reason": "ok",
                        "target_path": str(request.get("target_path", "")),
                    }
                if provider == "ollama_agent":
                    self.assertEqual(str(dict(request.get("provider_failover", {})).get("failed_provider", "")), "api_agent")
                    _write_provider_doc(run_dir, "I can keep this moving from the local side while the API path is down.")
                    return {
                        "status": "executed",
                        "reason": "ok",
                        "target_path": str(request.get("target_path", "")),
                    }
                raise AssertionError(f"unexpected provider: {provider}")

            config = {
                "mode": "manual_outbox",
                "role_providers": {"support_lead": "api_agent", "support_local_fallback": "ollama_agent"},
            }
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "frontend_route_conversation_mode", return_value="PROJECT_DETAIL"
            ), mock.patch.object(
                support_bot, "sync_project_context", side_effect=lambda **kwargs: ({}, kwargs["session_state"])
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, run_dir = support_bot.process_message(
                    chat_id="api-strict-demo",
                    user_text="i want to create a project for vn storyline support",
                    source="stdin",
                    provider_override="api_agent",
                )

            self.assertEqual(calls, ["api_agent", "ollama_agent"])
            self.assertEqual(str(doc.get("provider", "")), "ollama_agent")
            self.assertNotIn("\ufffd", str(doc.get("reply_text", "")))
            self.assertIn("API", str(doc.get("reply_text", "")))
            self.assertTrue(
                any(token in str(doc.get("reply_text", "")) for token in ("local", "down")),
                msg=str(doc.get("reply_text", "")),
            )
            state = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(state.get("provider_runtime_buffer", {}).get("preferred_provider", "")), "api_agent")

    def test_build_final_reply_doc_uses_bound_run_status_for_waiting_decision_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_bound_status_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "现在这个项目进度到哪了？",
                },
            )

            captured: dict[str, object] = {}

            class _Rendered:
                visible_state = "WAITING_FOR_DECISION"
                reply_text = "现在项目已经接上后台了，下一步需要你先拍一个关键决定。"
                followup_questions = ("你这轮更希望先保速度还是先保剧情完整度？",)
                pipeline_state = {
                    "visible_state": "WAITING_FOR_DECISION",
                    "selected_requirement_source": "latest_user_message",
                }

            def _fake_render(**kwargs):  # type: ignore[no-untyped-def]
                captured.update(kwargs.get("raw_backend_state", {}))
                return _Rendered()

            provider_doc = {
                "reply_text": "收到，继续推进。",
                "next_question": "这轮你更关注速度还是质量？",
                "actions": [],
                "debug_notes": "",
            }
            project_context = {
                "run_id": "r-demo",
                "status": {
                    "run_status": "blocked",
                    "verify_result": "",
                    "needs_user_decision": True,
                    "decisions_needed_count": 1,
                    "gate": {"state": "blocked", "owner": "chair", "reason": "waiting for one decision"},
                },
                "decisions": {"count": 1, "decisions": [{"decision_id": "outbox:1"}]},
                "whiteboard": {"path": "artifacts/support_whiteboard.json", "hits": [], "snapshot": {}},
            }
            with mock.patch.object(support_bot, "render_frontend_output", side_effect=_fake_render):
                doc = support_bot.build_final_reply_doc(
                    run_dir=run_dir,
                    provider="ollama_agent",
                    provider_result={"status": "executed", "reason": "ok"},
                    provider_doc=provider_doc,
                    project_context=project_context,
                    conversation_mode="STATUS_QUERY",
                    task_summary_hint="VN 剧情项目",
                )

            self.assertEqual(str(captured.get("waiting_for_decision", False)).lower(), "true")
            self.assertEqual(int(captured.get("decisions_count", 0) or 0), 1)
            self.assertEqual(str(captured.get("run_status", "")), "blocked")
            self.assertEqual(str(doc.get("reply_text", "")), "现在项目已经接上后台了，下一步需要你先拍一个关键决定。")
            self.assertIn("run_id=r-demo", str(doc.get("debug_notes", "")))

    def test_build_final_reply_doc_rewrites_blocked_first_draft_overpromise(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_blocked_promise_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "我想做一个帮我理顺 VN 剧情结构的项目。",
                },
            )
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "你先做出第一版给我看，然后我在做调整",
                },
            )
            provider_doc = {
                "reply_text": "我们会开始着手开发第一版基于Windows平台，并使用Qt6作为UI框架的初步版本。",
                "next_question": "",
                "actions": [],
                "debug_notes": "",
            }
            project_context = {
                "run_id": "r-blocked",
                "status": {
                    "run_status": "blocked",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "blocked", "owner": "contract_guard", "reason": "waiting for guard clearance"},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {"path": "artifacts/support_whiteboard.json", "hits": [], "snapshot": {}},
            }

            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc=provider_doc,
                project_context=project_context,
                conversation_mode="PROJECT_DETAIL",
                task_summary_hint="我想做一个帮我理顺 VN 剧情结构的项目。",
                lang_hint="zh",
            )

            reply = str(doc.get("reply_text", ""))
            self.assertNotIn("开始着手开发第一版", reply)
            # Gate owner "contract_guard" is an internal agent; the bot
            # should treat this as executing, NOT as user-facing blocked.
            self.assertNotIn("后台还没进入", reply)
            self.assertNotIn("先不对你承诺已经开工", reply)

    def test_build_final_reply_doc_grounds_project_detail_progress_followup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_progress_grounding_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "你能不能重新做一个我之前想要你做的项目",
                },
            )
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "现在做到什么程度了",
                },
            )
            provider_doc = {
                "reply_text": "现在就在往下做。",
                "next_question": "",
                "actions": [],
                "debug_notes": "",
            }
            project_context = {
                "run_id": "r-progress",
                "goal": "你能不能重新做一个我之前想要你做的项目",
                "status": {
                    "run_status": "blocked",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Contract Guardian",
                        "path": "reviews/review_contract.md",
                        "reason": "waiting for APPROVE review_contract (verdict=BLOCK)",
                    },
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {
                    "path": "artifacts/support_whiteboard.json",
                    "hits": [],
                    "snapshot": {
                        "path": "artifacts/support_whiteboard.json",
                        "entry_count": 3,
                        "entries": [
                            {"role": "librarian", "kind": "dispatch_lookup", "text": "lookup completed with 0 hits"},
                            {
                                "role": "cost_controller",
                                "kind": "dispatch_result",
                                "text": "cost_controller/review_cost via api_agent => executed (reviews/review_cost.md)",
                            },
                            {
                                "role": "contract_guardian",
                                "kind": "dispatch_result",
                                "text": "contract_guardian/review_contract via local_exec => exec_failed (reviews/review_contract.md); contract_guard failed",
                            },
                        ],
                    },
                },
            }

            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc=provider_doc,
                project_context=project_context,
                conversation_mode="PROJECT_DETAIL",
                task_summary_hint="你能不能重新做一个我之前想要你做的项目",
                lang_hint="zh",
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("我这边已经接手到后台流程", reply)
            self.assertIn("成本评审已完成", reply)
            self.assertIn("目前在合同评审这个阶段", reply)
            self.assertIn("先把合同评审卡点处理掉", reply)
            self.assertNotEqual(reply.strip(), "现在就在往下做。")

    def test_detect_conversation_mode_treats_previous_project_progress_followup_as_status_query(self) -> None:
        session_state = support_bot.default_support_session_state("6092527664")
        session_state["bound_run_id"] = "r-prev"
        session_state["project_memory"]["project_brief"] = "我想要你继续优化我的vn项目"

        mode = support_bot.detect_conversation_mode(
            Path("."),
            "我想要知道我之前那个项目做成什么样子了",
            session_state,
        )

        self.assertEqual(mode, "STATUS_QUERY")
        self.assertFalse(
            support_bot.should_refresh_project_brief(
                "我想要知道我之前那个项目做成什么样子了",
                "PROJECT_DETAIL",
            )
        )

    def test_model_mode_router_can_reclassify_ambiguous_turn_to_status_query(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_mode_router_apply_") as td:
            run_dir = Path(td)
            support_bot.ensure_layout(run_dir)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "我想做一个 VN 项目",
                },
            )
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "为什么我刚让你做，你就可以直接给我一个包",
                },
            )
            session_state = support_bot.default_support_session_state("mode-router-demo")
            session_state["bound_run_id"] = "r-mode"
            session_state["project_memory"]["project_brief"] = "我想做一个 VN 项目"
            captured_roles: list[str] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del provider, config
                captured_roles.append(str(request.get("role", "")))
                target = run_dir / support_bot.SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(
                        {
                            "mode": "STATUS_QUERY",
                            "confidence": 0.94,
                            "reason": "询问为什么能直接交付，属于进展/状态解释类",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return {"status": "executed", "reason": "ok", "target_path": str(request.get("target_path", ""))}

            with mock.patch.object(support_bot, "execute_provider", side_effect=_fake_execute):
                mode = support_bot.maybe_override_conversation_mode_with_model(
                    run_dir=run_dir,
                    chat_id="mode-router-demo",
                    user_text="为什么我刚让你做，你就可以直接给我一个包",
                    source="telegram",
                    detected_mode="PROJECT_DETAIL",
                    session_state=session_state,
                    config=support_bot.default_support_dispatch_config(),
                )

            self.assertEqual(mode, "STATUS_QUERY")
            self.assertIn("support_mode_router", captured_roles)
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("SUPPORT_MODE_ROUTER_APPLIED", events)

    def test_model_mode_router_falls_back_to_detected_mode_on_low_confidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_mode_router_fallback_") as td:
            run_dir = Path(td)
            support_bot.ensure_layout(run_dir)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "为什么我刚让你做，你就可以直接给我一个包",
                },
            )
            session_state = support_bot.default_support_session_state("mode-router-fallback-demo")
            session_state["bound_run_id"] = "r-mode"
            session_state["project_memory"]["project_brief"] = "我想做一个 VN 项目"

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del provider, config
                target = run_dir / support_bot.SUPPORT_MODE_ROUTER_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(
                        {
                            "mode": "STATUS_QUERY",
                            "confidence": 0.31,
                            "reason": "confidence too low",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return {"status": "executed", "reason": "ok", "target_path": str(request.get("target_path", ""))}

            with mock.patch.object(support_bot, "execute_provider", side_effect=_fake_execute):
                mode = support_bot.maybe_override_conversation_mode_with_model(
                    run_dir=run_dir,
                    chat_id="mode-router-fallback-demo",
                    user_text="为什么我刚让你做，你就可以直接给我一个包",
                    source="telegram",
                    detected_mode="PROJECT_DETAIL",
                    session_state=session_state,
                    config=support_bot.default_support_dispatch_config(),
                )

            self.assertEqual(mode, "PROJECT_DETAIL")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("SUPPORT_MODE_ROUTER_SKIPPED", events)

    def test_build_final_reply_doc_grounds_previous_project_status_followup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_previous_project_status_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "我想要知道我之前那个项目做成什么样子了",
                },
            )
            provider_doc = {
                "reply_text": "你是否方便提供最新的规划文档，或者有什么新的想法和优先需求希望这次优化时重点考虑？",
                "next_question": "",
                "actions": [],
                "debug_notes": "",
            }
            project_context = {
                "run_id": "r-prev-status",
                "goal": "我想要你继续优化我的vn项目",
                "status": {
                    "run_status": "blocked",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {
                    "path": "artifacts/support_whiteboard.json",
                    "hits": [],
                    "snapshot": {
                        "path": "artifacts/support_whiteboard.json",
                        "entry_count": 3,
                        "entries": [
                            {
                                "role": "support",
                                "kind": "support_turn",
                                "text": "telegram_auto_resume PROJECT_DETAIL: 就直接按之前的大纲走就行了",
                            },
                            {
                                "role": "chair",
                                "kind": "dispatch_result",
                                "text": "chair/plan_draft via api_agent => executed (artifacts/analysis.md)",
                            },
                            {
                                "role": "librarian",
                                "kind": "dispatch_result",
                                "text": "librarian/context_pack via local_exec => executed (artifacts/context_pack.json)",
                            },
                        ],
                    },
                },
            }

            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc=provider_doc,
                project_context=project_context,
                conversation_mode="STATUS_QUERY",
                task_summary_hint="我想要你继续优化我的vn项目",
                lang_hint="zh",
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("我这边已经接手到后台流程", reply)
            self.assertIn("目前在方案整理这个阶段", reply)
            self.assertIn("先把方案整理卡点处理掉", reply)
            self.assertNotIn("规划文档", reply)

    def test_build_final_reply_doc_status_query_handles_running_gate_blocked_as_real_blocker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_running_gate_blocked_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "现在是什么情况？",
                },
            )
            provider_doc = {
                "reply_text": "我继续推进中。",
                "next_question": "",
                "actions": [],
                "debug_notes": "",
            }
            project_context = {
                "run_id": "r-running-blocked",
                "goal": "我想要你继续优化我的vn项目",
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
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {"path": "artifacts/support_whiteboard.json", "hits": [], "snapshot": {}},
            }

            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc=provider_doc,
                project_context=project_context,
                conversation_mode="STATUS_QUERY",
                task_summary_hint="我想要你继续优化我的vn项目",
                lang_hint="zh",
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("目前在方案整理这个阶段", reply)
            self.assertIn("先把方案整理卡点处理掉", reply)
            self.assertNotIn("暂时没有新增阻塞", reply)

    def test_sync_project_context_recovers_archived_previous_outline_brief(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_resume_outline_") as td:
            runs_root = Path(td) / "runs"
            current_run_dir = runs_root / "ctcp" / "support_sessions" / "6092527664"
            backup_run_dir = runs_root / "ctcp" / "support_sessions" / "6092527664.backup-20260316-182553"
            (current_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (backup_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

            backup_state = support_bot.default_support_session_state("6092527664")
            backup_state["bound_run_id"] = "old-vn-run"
            backup_state["project_memory"]["project_brief"] = "我想要你继续优化我的vn项目"
            (backup_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(backup_state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            current_state = support_bot.default_support_session_state("6092527664")
            new_run_calls: list[str] = []

            def _fake_new_run(goal: str) -> dict[str, str]:
                new_run_calls.append(goal)
                return {"run_id": "new-vn-run", "run_dir": "D:/tmp/new-vn-run"}

            fake_context = {
                "run_id": "new-vn-run",
                "run_dir": "D:/tmp/new-vn-run",
                "goal": "我想要你继续优化我的vn项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "gate": {"state": "open", "owner": "", "reason": ""},
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                },
                "whiteboard": {},
            }

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_new_run",
                side_effect=_fake_new_run,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_record_support_turn",
                return_value={"ok": True},
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                return_value=fake_context,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ):
                project_context, updated_state = support_bot.sync_project_context(
                    run_dir=current_run_dir,
                    chat_id="6092527664",
                    user_text="就直接按之前的大纲走就行了",
                    source="telegram",
                    conversation_mode="PROJECT_DETAIL",
                    session_state=current_state,
                )

            self.assertEqual(new_run_calls, ["我想要你继续优化我的vn项目"])
            self.assertEqual(str(updated_state.get("bound_run_id", "")), "new-vn-run")
            self.assertEqual(str(updated_state.get("task_summary", "")), "我想要你继续优化我的vn项目")
            self.assertEqual(str(updated_state.get("resume_state", {}).get("last_resume_source_run_id", "")), "old-vn-run")
            self.assertEqual(str(project_context.get("goal", "")), "我想要你继续优化我的vn项目")

    def test_sync_project_context_zip_request_triggers_delivery_unblock_advance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_zip_unblock_advance_") as td:
            run_dir = Path(td)
            support_bot.ensure_layout(run_dir)
            session_state = support_bot.default_support_session_state("zip-demo")
            session_state["bound_run_id"] = "run-zip"
            session_state["bound_run_dir"] = "D:/tmp/run-zip"
            session_state["project_memory"]["project_brief"] = "继续推进 VN 项目"

            blocked_context = {
                "run_id": "run-zip",
                "run_dir": "D:/tmp/run-zip",
                "goal": "继续推进 VN 项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "blocked", "owner": "PatchMaker", "reason": "waiting for diff.patch"},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }
            final_context = {
                "run_id": "run-zip",
                "run_dir": "D:/tmp/run-zip",
                "goal": "继续推进 VN 项目",
                "status": {
                    "run_status": "completed",
                    "verify_result": "PASS",
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "gate": {"state": "closed", "owner": "", "reason": ""},
                },
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {},
            }

            with mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                side_effect=[blocked_context, blocked_context, final_context],
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
                    chat_id="zip-demo",
                    user_text="把项目 zip 发我",
                    source="telegram",
                    conversation_mode="STATUS_QUERY",
                    session_state=session_state,
                )

            advance_spy.assert_called_once_with("run-zip", max_steps=6)
            self.assertEqual(str(project_context.get("status", {}).get("verify_result", "")), "PASS")
            self.assertEqual(str(project_context.get("status", {}).get("run_status", "")), "completed")
            self.assertEqual(str(updated_state.get("bound_run_id", "")), "run-zip")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("SUPPORT_DELIVERY_UNBLOCK_ADVANCE", events)

    def test_build_grounded_status_reply_doc_does_not_repeat_latest_greeting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_greeting_guard_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "你好",
                },
            )
            session_state = support_bot.default_support_session_state("proactive-demo")
            session_state["bound_run_id"] = "run-proactive"
            session_state["project_memory"]["project_brief"] = "我想要你继续优化我的vn项目"
            session_state["session_profile"]["lang_hint"] = "zh"
            project_context = {
                "run_id": "run-proactive",
                "goal": "我想要你继续优化我的vn项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "gate": {
                        "state": "open",
                        "owner": "Chair/Planner",
                        "path": "artifacts/analysis.md",
                        "reason": "waiting for analysis.md",
                    },
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                },
                "whiteboard": {
                    "snapshot": {
                        "entries": [
                            {
                                "kind": "dispatch_result",
                                "text": "chair/plan_draft via api_agent => executed (artifacts/analysis.md)",
                            }
                        ]
                    }
                },
            }

            doc = support_bot.build_grounded_status_reply_doc(
                run_dir=run_dir,
                session_state=session_state,
                project_context=project_context,
            )

            reply = str(doc.get("reply_text", ""))
            self.assertIn("目前在", reply)
            self.assertIn("我会继续处理：", reply)
            self.assertNotIn("你好，随时可以开始", reply)
            self.assertNotEqual(reply.strip(), "你好，随时可以开始。你说说看要做什么？")
        self.assertEqual(str(session_state.get("frontdesk_state", {}).get("state", "")), "idle")

    def test_process_message_greeting_does_not_reset_real_progress_digest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_progress_baseline_guard_") as td:
            runs_root = Path(td) / "runs"

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del provider, request, config
                _write_provider_doc(run_dir, "很高兴收到你的消息。请告诉我你这次需要什么帮助或者遇到了什么问题，我们可以一起推进解决。")
                return {"status": "executed", "reason": "ok"}

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=({"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent"}}, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot,
                "sync_project_context",
                side_effect=lambda **kwargs: ({}, kwargs["session_state"]),
            ):
                session_dir = runs_root / "ctcp" / "support_sessions" / "baseline-demo"
                session_dir.mkdir(parents=True, exist_ok=True)
                state = support_bot.default_support_session_state("baseline-demo")
                state["bound_run_id"] = "run-proactive"
                state["bound_run_dir"] = "D:/tmp/run-proactive"
                state["project_memory"]["project_brief"] = "我想要你继续优化我的vn项目"
                state["notification_state"]["last_progress_hash"] = "existing-real-hash"
                state["notification_state"]["last_progress_ts"] = "2026-03-17T09:00:00Z"
                support_bot.write_json(session_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH, state)

                _doc, run_dir = support_bot.process_message(
                    chat_id="baseline-demo",
                    user_text="你好",
                    source="telegram",
                    provider_override="api_agent",
                )

            saved = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            notification_state = dict(saved.get("notification_state", {}))
            self.assertEqual(str(notification_state.get("last_progress_hash", "")), "existing-real-hash")
            self.assertEqual(str(notification_state.get("last_notified_run_id", "")), "")

    def test_support_controller_decision_prompt_dedup_and_cooldown(self) -> None:
        session_state = support_bot.default_support_session_state("controller-decision")
        session_state["bound_run_id"] = "run-decision"
        project_context = {
            "run_id": "run-decision",
            "status": {
                "run_status": "blocked",
                "verify_result": "",
                "needs_user_decision": True,
                "decisions_needed_count": 1,
                "gate": {"state": "blocked", "owner": "chair", "reason": "请选择交付格式"},
            },
            "decisions": {
                "count": 1,
                "decisions": [{"decision_id": "outbox:1", "question_hint": "你要先要 zip 包，还是先看截图？"}],
            },
            "whiteboard": {},
        }

        binding = support_bot.build_progress_binding(project_context=project_context, task_summary_hint="VN项目")
        self.assertEqual(str(binding.get("active_stage", "")), "WAIT_USER_DECISION")
        self.assertEqual(str(binding.get("stage_exit_condition", "")), "required_user_decision_received")
        report = support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-24T10:00:00Z",
            keepalive_interval_sec=600,
        )
        self.assertEqual(str(report.get("controller_state", "")), "WAIT_USER_DECISION")
        jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(str(jobs[0].get("kind", "")), "decision")
        support_bot.ctcp_support_controller.mark_job_sent(
            session_state,
            jobs[0],
            now_ts="2026-03-24T10:00:00Z",
            cooldown_sec=60,
        )

        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-24T10:00:10Z",
            keepalive_interval_sec=600,
        )
        self.assertEqual(support_bot.ctcp_support_controller.pop_outbound_jobs(session_state), [])

        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-24T10:02:00Z",
            keepalive_interval_sec=600,
        )
        self.assertEqual(support_bot.ctcp_support_controller.pop_outbound_jobs(session_state), [])

        changed_context = dict(project_context)
        changed_context["decisions"] = {
            "count": 1,
            "decisions": [{"decision_id": "outbox:2", "question_hint": "你要先做剧情主线，还是先做UI框架？"}],
        }
        changed_binding = support_bot.build_progress_binding(project_context=changed_context, task_summary_hint="VN项目")
        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=changed_context,
            progress_binding=changed_binding,
            now_ts="2026-03-24T10:03:30Z",
            keepalive_interval_sec=600,
        )
        changed_jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertEqual(len(changed_jobs), 1)
        self.assertEqual(str(changed_jobs[0].get("kind", "")), "decision")

    def test_support_controller_prefers_canonical_runtime_state_over_legacy_status_guess(self) -> None:
        session_state = support_bot.default_support_session_state("controller-canonical-execute")
        session_state["bound_run_id"] = "run-canonical-execute"
        project_context = {
            "run_id": "run-canonical-execute",
            "status": {
                "run_status": "blocked",
                "verify_result": "",
                "needs_user_decision": True,
                "decisions_needed_count": 1,
                "gate": {"state": "blocked", "owner": "chair", "reason": "legacy decision guess"},
            },
            "runtime_state": {
                "phase": "EXECUTE",
                "run_status": "running",
                "verify_result": "",
                "needs_user_decision": False,
                "blocking_reason": "none",
                "pending_decisions": [],
                "error": {"has_error": False},
                "gate": {"state": "open", "owner": "patchmaker", "reason": "working"},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }

        binding = support_bot.build_progress_binding(project_context=project_context, task_summary_hint="VN项目")
        report = support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-30T09:00:00Z",
            keepalive_interval_sec=0,
        )
        self.assertNotEqual(str(report.get("controller_state", "")), "WAIT_USER_DECISION")
        jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertTrue(all(str(item.get("kind", "")) != "decision" for item in jobs))

    def test_support_controller_waits_user_decision_when_canonical_pending_decision_exists(self) -> None:
        session_state = support_bot.default_support_session_state("controller-canonical-decision")
        session_state["bound_run_id"] = "run-canonical-decision"
        project_context = {
            "run_id": "run-canonical-decision",
            "status": {
                "run_status": "running",
                "verify_result": "",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "open", "owner": "", "reason": ""},
            },
            "runtime_state": {
                "phase": "WAIT_USER_DECISION",
                "run_status": "blocked",
                "verify_result": "",
                "needs_user_decision": True,
                "blocking_reason": "请确认交付格式",
                "pending_decisions": [
                    {
                        "decision_id": "outbox:canonical",
                        "question": "你要先看截图还是先收 zip 包？",
                        "status": "pending",
                    }
                ],
                "error": {"has_error": False},
                "gate": {"state": "blocked", "owner": "chair", "reason": "decision required"},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }

        binding = support_bot.build_progress_binding(project_context=project_context, task_summary_hint="VN项目")
        report = support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-30T09:10:00Z",
            keepalive_interval_sec=0,
        )
        self.assertEqual(str(report.get("controller_state", "")), "WAIT_USER_DECISION")
        jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(str(jobs[0].get("kind", "")), "decision")

    def test_support_controller_result_notify_requires_final_ready_status(self) -> None:
        session_state = support_bot.default_support_session_state("controller-result")
        session_state["bound_run_id"] = "run-result"
        not_ready_context = {
            "run_id": "run-result",
            "status": {
                "run_status": "running",
                "verify_result": "PASS",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "open", "owner": "", "reason": ""},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }
        binding = support_bot.build_progress_binding(project_context=not_ready_context, task_summary_hint="VN项目")
        self.assertEqual(str(binding.get("active_stage", "")), "EXECUTE")
        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=not_ready_context,
            progress_binding=binding,
            now_ts="2026-03-24T11:00:00Z",
            keepalive_interval_sec=600,
        )
        jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertTrue(all(str(item.get("kind", "")) != "result" for item in jobs))

        ready_context = {
            "run_id": "run-result",
            "status": {
                "run_status": "completed",
                "verify_result": "PASS",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "closed", "owner": "", "reason": ""},
            },
            "render_snapshot": {
                "visible_state": "DONE",
                "ui_badge": "success",
                "progress_summary": "ready",
            },
            "artifact_manifest": {
                "source_files": ["src/main.py"],
                "doc_files": ["docs/overview.md"],
                "workflow_files": ["PLAN.md"],
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }
        ready_binding = support_bot.build_progress_binding(project_context=ready_context, task_summary_hint="VN项目")
        self.assertEqual(str(ready_binding.get("active_stage", "")), "FINALIZE")
        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=ready_context,
            progress_binding=ready_binding,
            now_ts="2026-03-24T11:20:00Z",
            keepalive_interval_sec=600,
        )
        ready_jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertTrue(any(str(item.get("kind", "")) == "result" for item in ready_jobs))

    def test_support_controller_progress_dedupe_stays_stable_after_support_memory_write(self) -> None:
        session_state = support_bot.default_support_session_state("controller-progress-dedupe")
        session_state["bound_run_id"] = "run-progress"
        session_state["notification_state"]["last_progress_ts"] = "2026-03-24T09:00:00Z"
        session_state["notification_state"]["last_progress_hash"] = "legacy-progress-hash"
        project_context = {
            "run_id": "run-progress",
            "status": {
                "run_status": "running",
                "verify_result": "",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "open", "owner": "chair", "reason": "working"},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }
        binding = support_bot.build_progress_binding(project_context=project_context, task_summary_hint="VN项目")
        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-24T12:00:00Z",
            keepalive_interval_sec=7200,
        )
        jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(str(jobs[0].get("kind", "")), "progress")
        support_bot.ctcp_support_controller.mark_job_sent(
            session_state,
            jobs[0],
            now_ts="2026-03-24T12:00:00Z",
            cooldown_sec=30,
        )
        support_bot.remember_progress_notification(
            session_state,
            project_context=project_context,
            task_summary_hint="VN项目",
            ts="2026-03-24T12:00:00Z",
            status_hash=str(jobs[0].get("status_hash", "")),
        )

        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-24T12:10:00Z",
            keepalive_interval_sec=7200,
        )
        self.assertEqual(support_bot.ctcp_support_controller.pop_outbound_jobs(session_state), [])

    def test_support_controller_does_not_push_progress_immediately_on_status_changed(self) -> None:
        session_state = support_bot.default_support_session_state("controller-progress-throttle")
        session_state["bound_run_id"] = "run-progress"
        session_state["notification_state"]["last_progress_ts"] = "2026-03-24T12:00:00Z"
        session_state["notification_state"]["last_progress_hash"] = "old-hash"
        project_context = {
            "run_id": "run-progress",
            "status": {
                "run_status": "blocked",
                "verify_result": "",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "blocked", "owner": "contract_guard", "reason": "waiting for guard clearance"},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }
        binding = support_bot.build_progress_binding(project_context=project_context, task_summary_hint="VN项目")
        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-24T12:00:30Z",
            keepalive_interval_sec=900,
        )
        self.assertEqual(support_bot.ctcp_support_controller.pop_outbound_jobs(session_state), [])

    def test_support_controller_keepalive_disabled_stays_silent(self) -> None:
        session_state = support_bot.default_support_session_state("controller-keepalive-disabled")
        session_state["bound_run_id"] = "run-progress"
        session_state["notification_state"]["last_progress_ts"] = "2026-03-24T09:00:00Z"
        session_state["notification_state"]["last_progress_hash"] = "legacy-progress-hash"
        project_context = {
            "run_id": "run-progress",
            "status": {
                "run_status": "running",
                "verify_result": "",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "open", "owner": "", "reason": ""},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }
        binding = support_bot.build_progress_binding(project_context=project_context, task_summary_hint="VN项目")
        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=project_context,
            progress_binding=binding,
            now_ts="2026-03-24T12:10:00Z",
            keepalive_interval_sec=0,
        )
        self.assertEqual(support_bot.ctcp_support_controller.pop_outbound_jobs(session_state), [])

    def test_run_stdin_mode_emits_reply_text_only(self) -> None:
        with mock.patch.object(
            support_bot,
            "process_message",
            return_value=({"reply_text": "自然客服答复"}, Path("D:/tmp/support-demo")),
        ), mock.patch("sys.stdin", io.StringIO("hello")), mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            rc = support_bot.run_stdin_mode(chat_id="stdin-demo")

        self.assertEqual(rc, 0)
        self.assertEqual(stdout.getvalue().strip(), "自然客服答复")

    def test_resolve_telegram_token_prefers_explicit_value_then_env(self) -> None:
        with mock.patch.dict("os.environ", {"CTCP_TG_TOKEN": "env-token", "TELEGRAM_BOT_TOKEN": "fallback-token"}, clear=False):
            self.assertEqual(support_bot.resolve_telegram_token("explicit-token"), "explicit-token")
            self.assertEqual(support_bot.resolve_telegram_token(""), "env-token")
        with mock.patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "fallback-token"}, clear=True):
            self.assertEqual(support_bot.resolve_telegram_token(""), "fallback-token")

    def test_main_telegram_mode_requires_token_or_env(self) -> None:
        with mock.patch("sys.argv", ["ctcp_support_bot.py", "telegram"]), mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            rc = support_bot.main()

        self.assertEqual(rc, 1)
        self.assertIn("telegram token missing", stderr.getvalue())

    def test_collect_public_delivery_state_blocks_low_quality_generated_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_state_") as td:
            repo_root = Path(td)
            generated_project = repo_root / "generated_projects" / "vn_story_organizer"
            generated_project.mkdir(parents=True, exist_ok=True)
            (generated_project / "main.py").write_text("print('vn')\n", encoding="utf-8")

            bound_run = repo_root / "runs" / "bound-vn"
            (bound_run / "artifacts").mkdir(parents=True, exist_ok=True)
            (bound_run / "artifacts" / "patch_apply.json").write_text(
                json.dumps({"touched_files": ["generated_projects/vn_story_organizer/main.py"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (bound_run / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: generated_projects/vn_story_organizer/\n",
                encoding="utf-8",
            )

            state = support_bot.default_support_session_state("delivery-demo")
            state["bound_run_id"] = "r-vn"
            state["bound_run_dir"] = str(bound_run)
            with mock.patch.object(support_bot, "ROOT", repo_root):
                delivery = support_bot.collect_public_delivery_state(
                    session_state=state,
                    project_context={
                        "run_id": "r-vn",
                        "run_dir": str(bound_run),
                        "status": {
                            "run_status": "completed",
                            "verify_result": "PASS",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "closed", "owner": "", "reason": ""},
                        },
                    },
                    source="telegram",
                )

            self.assertFalse(bool(delivery.get("package_ready", False)))
            self.assertFalse(bool(delivery.get("package_delivery_allowed", False)))
            self.assertFalse(bool(delivery.get("package_quality_ready", True)))
            self.assertIn("quality score", str(delivery.get("package_blocked_reason", "")))
            self.assertFalse(bool(delivery.get("screenshot_ready", False)))
            self.assertIn(str(generated_project.resolve()), list(delivery.get("package_source_dirs", [])))
            self.assertEqual(str(delivery.get("package_delivery_mode", "")), "materialize_ctcp_scaffold")
            self.assertEqual(str(delivery.get("project_name_hint", "")), "vn_story_organizer")
            self.assertIn("docs/", list(delivery.get("package_structure_hint", [])))

    def test_collect_public_delivery_state_allows_high_quality_generated_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_quality_ok_") as td:
            repo_root = Path(td)
            generated_project = repo_root / "generated_projects" / "vn_story_organizer"
            (generated_project / "docs").mkdir(parents=True, exist_ok=True)
            (generated_project / "meta" / "tasks").mkdir(parents=True, exist_ok=True)
            (generated_project / "scripts").mkdir(parents=True, exist_ok=True)
            (generated_project / "tests").mkdir(parents=True, exist_ok=True)
            (generated_project / "artifacts" / "screenshots").mkdir(parents=True, exist_ok=True)
            (generated_project / "README.md").write_text("# vn_story_organizer\n", encoding="utf-8")
            (generated_project / "manifest.json").write_text("{}", encoding="utf-8")
            (generated_project / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
            (generated_project / "meta" / "tasks" / "CURRENT.md").write_text("# current\n", encoding="utf-8")
            (generated_project / "scripts" / "verify_repo.ps1").write_text("Write-Host ok\n", encoding="utf-8")
            (generated_project / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
            (generated_project / "artifacts" / "test_plan.json").write_text("{}", encoding="utf-8")
            (generated_project / "artifacts" / "test_cases.json").write_text("{}", encoding="utf-8")
            (generated_project / "artifacts" / "test_summary.md").write_text("# summary\n", encoding="utf-8")
            (generated_project / "artifacts" / "demo_trace.md").write_text("# demo\n", encoding="utf-8")
            (generated_project / "artifacts" / "screenshots" / "step01.png").write_bytes(b"\x89PNG\r\n")

            bound_run = repo_root / "runs" / "bound-vn"
            (bound_run / "artifacts").mkdir(parents=True, exist_ok=True)
            (bound_run / "artifacts" / "patch_apply.json").write_text(
                json.dumps({"touched_files": ["generated_projects/vn_story_organizer/README.md"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (bound_run / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: generated_projects/vn_story_organizer/\n",
                encoding="utf-8",
            )

            state = support_bot.default_support_session_state("delivery-demo")
            state["bound_run_id"] = "r-vn"
            state["bound_run_dir"] = str(bound_run)
            with mock.patch.object(support_bot, "ROOT", repo_root):
                delivery = support_bot.collect_public_delivery_state(
                    session_state=state,
                    project_context={
                        "run_id": "r-vn",
                        "run_dir": str(bound_run),
                        "status": {
                            "run_status": "completed",
                            "verify_result": "PASS",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "closed", "owner": "", "reason": ""},
                        },
                    },
                    source="telegram",
                )

            self.assertTrue(bool(delivery.get("package_ready", False)))
            self.assertTrue(bool(delivery.get("package_delivery_allowed", False)))
            self.assertTrue(bool(delivery.get("package_quality_ready", False)))
            self.assertGreaterEqual(int(delivery.get("package_quality_score", 0) or 0), support_bot.SUPPORT_PACKAGE_MIN_QUALITY_SCORE)
            self.assertEqual(str(delivery.get("package_blocked_reason", "")), "")
            self.assertEqual(str(delivery.get("package_delivery_mode", "")), "zip_existing_ctcp_project")

    def test_collect_public_delivery_state_blocks_package_until_final_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_gate_") as td:
            repo_root = Path(td)
            generated_project = repo_root / "generated_projects" / "vn_story_organizer"
            generated_project.mkdir(parents=True, exist_ok=True)
            (generated_project / "main.py").write_text("print('vn')\n", encoding="utf-8")

            bound_run = repo_root / "runs" / "bound-vn"
            (bound_run / "artifacts").mkdir(parents=True, exist_ok=True)
            (bound_run / "artifacts" / "patch_apply.json").write_text(
                json.dumps({"touched_files": ["generated_projects/vn_story_organizer/main.py"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (bound_run / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: generated_projects/vn_story_organizer/\n",
                encoding="utf-8",
            )

            state = support_bot.default_support_session_state("delivery-demo")
            state["bound_run_id"] = "r-vn"
            state["bound_run_dir"] = str(bound_run)
            with mock.patch.object(support_bot, "ROOT", repo_root):
                delivery = support_bot.collect_public_delivery_state(
                    session_state=state,
                    project_context={
                        "run_id": "r-vn",
                        "run_dir": str(bound_run),
                        "status": {
                            "run_status": "running",
                            "verify_result": "",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "open", "owner": "", "reason": ""},
                        },
                    },
                    source="telegram",
                )

            self.assertFalse(bool(delivery.get("package_ready", False)))
            self.assertFalse(bool(delivery.get("package_delivery_allowed", False)))
            self.assertIn("verify_result is not PASS", str(delivery.get("package_blocked_reason", "")))

    def test_build_final_reply_doc_synthesizes_zip_action_and_rewrites_email_handoff(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_action_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "zip就行",
                },
            )
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "我会把整个项目打包成zip文件，稍后发送给你，请确认收件邮箱以便我发送压缩包。",
                    "next_question": "",
                    "actions": [],
                    "debug_notes": "",
                },
                source_hint="telegram",
                conversation_mode="PROJECT_DETAIL",
                delivery_state={
                    "channel_can_send_files": True,
                    "package_ready": True,
                    "package_delivery_allowed": True,
                    "package_blocked_reason": "",
                    "screenshot_ready": False,
                    "package_source_dirs": ["D:/tmp/vn_story_organizer"],
                    "existing_package_files": [],
                    "screenshot_files": [],
                },
            )

            self.assertTrue(any(str(item.get("type", "")) == "send_project_package" for item in list(doc.get("actions", []))))
            self.assertIn("不用再留邮箱", str(doc.get("reply_text", "")))

    def test_build_final_reply_doc_zip_request_blocked_sends_preview_and_confirmation_note(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_preview_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "把项目 zip 发我",
                },
            )
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "我先同步当前进度。",
                    "next_question": "",
                    "actions": [],
                    "debug_notes": "",
                },
                source_hint="telegram",
                conversation_mode="PROJECT_DETAIL",
                delivery_state={
                    "channel_can_send_files": True,
                    "package_ready": False,
                    "package_delivery_allowed": False,
                    "package_blocked_reason": "verify_result is not PASS",
                    "screenshot_ready": True,
                    "package_source_dirs": ["D:/tmp/vn_story_organizer"],
                    "existing_package_files": [],
                    "screenshot_files": ["D:/tmp/vn_story_organizer/artifacts/progress.png"],
                },
            )

            action_types = {str(item.get("type", "")).strip().lower() for item in list(doc.get("actions", []))}
            self.assertNotIn("send_project_package", action_types)
            self.assertIn("send_project_screenshot", action_types)
            self.assertIn("确认“可以发包”", str(doc.get("reply_text", "")))

    def test_build_final_reply_doc_zip_confirmation_after_preview_sends_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_confirm_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "把项目 zip 发我",
                },
            )
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "可以，发吧",
                },
            )
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "收到，我继续推进。",
                    "next_question": "",
                    "actions": [],
                    "debug_notes": "",
                },
                source_hint="telegram",
                conversation_mode="STATUS_QUERY",
                delivery_state={
                    "channel_can_send_files": True,
                    "package_ready": True,
                    "package_delivery_allowed": True,
                    "package_blocked_reason": "",
                    "screenshot_ready": True,
                    "package_source_dirs": ["D:/tmp/vn_story_organizer"],
                    "existing_package_files": ["D:/tmp/vn_story_organizer.zip"],
                    "screenshot_files": ["D:/tmp/vn_story_organizer/artifacts/progress.png"],
                },
            )

            self.assertTrue(any(str(item.get("type", "")) == "send_project_package" for item in list(doc.get("actions", []))))

    def test_public_delivery_prompt_context_exposes_ctcp_scaffold_shape(self) -> None:
        ctx = support_bot.public_delivery_prompt_context(
            {
                "channel": "telegram",
                "channel_can_send_files": True,
                "package_ready": True,
                "package_delivery_allowed": True,
                "package_blocked_reason": "",
                "package_source_dirs": ["D:/tmp/vn_story_organizer"],
                "existing_package_files": [],
                "project_name_hint": "vn_story_organizer",
                "package_delivery_mode": "materialize_ctcp_scaffold",
                "package_structure_hint": list(support_bot.CTCP_SCAFFOLD_STRUCTURE_HINT),
                "screenshot_ready": False,
                "screenshot_files": [],
            }
        )

        self.assertEqual(str(ctx.get("package_delivery_mode", "")), "materialize_ctcp_scaffold")
        self.assertEqual(str(ctx.get("project_name_hint", "")), "vn_story_organizer")
        self.assertTrue(bool(ctx.get("package_delivery_allowed", False)))
        self.assertIn("docs/", list(ctx.get("package_structure_hint", [])))

    def test_build_final_reply_doc_filters_provider_package_action_when_gate_blocked(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_gate_doc_") as td:
            run_dir = Path(td)
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": "把zip发给我",
                },
            )
            doc = support_bot.build_final_reply_doc(
                run_dir=run_dir,
                provider="api_agent",
                provider_result={"status": "executed", "reason": "ok"},
                provider_doc={
                    "reply_text": "我现在发你zip。",
                    "next_question": "",
                    "actions": [{"type": "send_project_package", "format": "zip"}],
                    "debug_notes": "",
                },
                source_hint="telegram",
                conversation_mode="PROJECT_DETAIL",
                delivery_state={
                    "channel_can_send_files": True,
                    "package_ready": False,
                    "package_delivery_allowed": False,
                    "package_blocked_reason": "verify_result is not PASS",
                    "screenshot_ready": False,
                    "package_source_dirs": ["D:/tmp/vn_story_organizer"],
                    "existing_package_files": [],
                    "screenshot_files": [],
                },
            )

            self.assertFalse(any(str(item.get("type", "")) == "send_project_package" for item in list(doc.get("actions", []))))

    def test_emit_public_delivery_materializes_zip_and_sends_document(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_emit_delivery_") as td:
            root = Path(td)
            support_run_dir = root / "support-session"
            project_dir = root / "generated_projects" / "vn_story_organizer"
            project_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "main.py").write_text("print('demo')\n", encoding="utf-8")
            scaffold_dir = root / "exports" / "vn_story_organizer_ctcp_project"
            (scaffold_dir / "docs").mkdir(parents=True, exist_ok=True)
            (scaffold_dir / "meta").mkdir(parents=True, exist_ok=True)
            (scaffold_dir / "scripts").mkdir(parents=True, exist_ok=True)
            (scaffold_dir / "workflow_registry").mkdir(parents=True, exist_ok=True)
            (scaffold_dir / "simlab").mkdir(parents=True, exist_ok=True)
            (scaffold_dir / "README.md").write_text("# vn_story_organizer\n", encoding="utf-8")
            (scaffold_dir / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
            (scaffold_dir / "scripts" / "verify_repo.ps1").write_text("Write-Host ok\n", encoding="utf-8")
            (scaffold_dir / "manifest.json").write_text("{}", encoding="utf-8")

            class _FakeTelegram:
                def __init__(self) -> None:
                    self.sent_documents: list[tuple[int, Path, str]] = []
                    self.sent_photos: list[tuple[int, Path, str]] = []

                def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    self.sent_documents.append((chat_id, file_path, caption))

                def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    self.sent_photos.append((chat_id, file_path, caption))

            fake = _FakeTelegram()
            with mock.patch.object(
                support_bot,
                "_materialize_support_scaffold_project",
                return_value=scaffold_dir,
            ) as scaffold_spy:
                plan = support_bot.emit_public_delivery(
                    fake,  # type: ignore[arg-type]
                    chat_id=123,
                    run_dir=support_run_dir,
                    actions=[{"type": "send_project_package", "format": "zip"}],
                    delivery_state={
                        "channel_can_send_files": True,
                        "package_ready": True,
                        "package_delivery_allowed": True,
                        "package_blocked_reason": "",
                        "screenshot_ready": False,
                        "package_source_dirs": [str(project_dir)],
                        "ctcp_package_source_dirs": [],
                        "placeholder_package_source_dirs": [str(project_dir)],
                        "existing_package_files": [],
                        "screenshot_files": [],
                        "project_name_hint": "vn_story_organizer",
                        "package_delivery_mode": "materialize_ctcp_scaffold",
                        "package_structure_hint": list(support_bot.CTCP_SCAFFOLD_STRUCTURE_HINT),
                    },
                )

            self.assertEqual(len(fake.sent_documents), 1)
            sent_chat, sent_path, caption = fake.sent_documents[0]
            self.assertEqual(sent_chat, 123)
            self.assertTrue(sent_path.exists(), msg=str(sent_path))
            self.assertEqual(sent_path.name, "vn_story_organizer_ctcp_project.zip")
            self.assertIn("zip", caption.lower())
            scaffold_spy.assert_called_once()
            with zipfile.ZipFile(sent_path, "r") as zf:
                names = set(zf.namelist())
            self.assertIn("vn_story_organizer_ctcp_project/README.md", names)
            self.assertIn("vn_story_organizer_ctcp_project/docs/00_CORE.md", names)
            self.assertIn("vn_story_organizer_ctcp_project/scripts/verify_repo.ps1", names)
            manifest = json.loads((support_run_dir / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(len(list(manifest.get("sent", []))), 1)
            self.assertEqual(len(list(plan.get("sent", []))), 1)

    def test_t2p_fast_path_trigger_is_disabled_for_project_create_turn(self) -> None:
        session_state = support_bot.default_support_session_state("single-mainline")
        self.assertFalse(
            support_bot.should_trigger_t2p_state_machine(
                session_state=session_state,
                user_text="我想要你帮我创建一个项目，是一个工具来帮我制作vn游戏",
                source="telegram",
                conversation_mode="PROJECT_DETAIL",
            )
        )
