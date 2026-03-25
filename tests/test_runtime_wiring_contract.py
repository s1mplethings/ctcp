from __future__ import annotations

import argparse
import io
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
import scripts.ctcp_support_bot as support_bot


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "triplet_guard" / "runtime_wiring_cases.json"


def _append_jsonl(path: Path, row: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


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

    def test_capability_query_does_not_enter_project_planning_pipeline(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "support_provider_failed",
                "blocked_needs_input": True,
                "needs_input": True,
                "missing_fields": ["runtime_target"],
            },
            task_summary="你是谁",
            raw_reply_text="plan agent command failed rc=2",
            raw_next_question="这轮你希望我优先速度、质量，还是成本？",
            notes={
                "lang": "zh",
                "recent_user_messages": ["你是谁"],
            },
        )
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(state.get("conversation_mode", "")), "CAPABILITY_QUERY")
        self.assertEqual(result.followup_questions, ())
        self.assertEqual(str(state.get("selected_requirement_source", "")), "")
        self.assertIn("CTCP support 入口", result.reply_text)
        self.assertNotIn("速度、质量", result.reply_text)
        self.assertFalse(any(tok in result.reply_text for tok in ("CONTEXT", "PLAN", "PATCH")))

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

    def test_frontend_render_consumes_frontdesk_await_decision_state(self) -> None:
        result = render_frontend_output(
            raw_backend_state={
                "stage": "analysis",
                "has_actionable_goal": True,
                "first_pass_understood": True,
            },
            task_summary="继续优化 VN 前台",
            raw_reply_text="",
            raw_next_question="",
            notes={
                "lang": "zh",
                "recent_user_messages": ["继续优化这个项目"],
                "frontdesk_state": {
                    "state": "AwaitDecision",
                    "active_task_id": "run-vn",
                    "current_goal": "继续优化 VN 前台",
                    "decision_points": [
                        {
                            "decision_id": "d-ui",
                            "question": "这轮你要保留旧 UI，还是直接重做 UI？",
                        }
                    ],
                },
            },
        )
        state = dict(result.pipeline_state or {})
        self.assertEqual(str(dict(state.get("frontdesk_state", {})).get("state", "")), "AwaitDecision")
        self.assertTrue(
            ("重做 UI" in result.reply_text) or any("重做 UI" in q for q in result.followup_questions),
            msg=f"reply={result.reply_text}; questions={result.followup_questions}",
        )

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

    def test_support_bot_process_message_connects_entrypoint_to_support_reply_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_") as td:
            runs_root = Path(td) / "runs"

            class _Rendered:
                visible_state = "UNDERSTOOD"
                reply_text = "收到，我先整理成客户可见的支持答复。"
                followup_questions = ()
                pipeline_state = {
                    "visible_state": "UNDERSTOOD",
                    "selected_requirement_source": "latest_user_message",
                }

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(
                        {
                            "reply_text": "收到，继续推进。missing runtime_target",
                            "next_question": "你最想先盯住哪个点？",
                            "actions": [],
                            "debug_notes": "",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return {"status": "executed", "reason": "ok", "target_path": str(request.get("target_path", ""))}

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "frontend_route_conversation_mode", return_value="PROJECT_DETAIL"
            ), mock.patch.object(
                support_bot, "sync_project_context", side_effect=lambda **kwargs: ({}, kwargs["session_state"])
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", return_value=_Rendered()
            ):
                doc, run_dir = support_bot.process_message(
                    chat_id="runtime-demo",
                    user_text="请帮我做一个客服回复节奏整理项目。",
                    source="stdin",
                )

            self.assertEqual(str(doc["reply_text"]), "收到，我先整理成客户可见的支持答复。")
            self.assertTrue((run_dir / support_bot.SUPPORT_INBOX_REL_PATH).exists())
            self.assertTrue((run_dir / support_bot.SUPPORT_PROMPT_REL_PATH).exists())
            reply_path = run_dir / support_bot.SUPPORT_REPLY_REL_PATH
            self.assertTrue(reply_path.exists())
            saved = json.loads(reply_path.read_text(encoding="utf-8"))
            self.assertEqual(str(saved.get("reply_text", "")), "收到，我先整理成客户可见的支持答复。")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("SUPPORT_REPLY_WRITTEN", events)

    def test_support_bot_process_message_persists_frontdesk_state_snapshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_frontdesk_state_") as td:
            runs_root = Path(td) / "runs"

            def _fake_sync_project_context(**kwargs):  # type: ignore[no-untyped-def]
                session_state = kwargs["session_state"]
                session_state["bound_run_id"] = "r-frontdesk"
                session_state["bound_run_dir"] = "D:/tmp/r-frontdesk"
                session_state["project_memory"]["project_brief"] = "请帮我把前台改成状态机"
                session_state["task_summary"] = "请帮我把前台改成状态机"
                return (
                    {
                        "run_id": "r-frontdesk",
                        "run_dir": "D:/tmp/r-frontdesk",
                        "goal": "请帮我把前台改成状态机",
                        "status": {
                            "run_status": "running",
                            "verify_result": "",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "open", "owner": "", "reason": ""},
                        },
                        "whiteboard": {},
                    },
                    session_state,
                )

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del provider, request, config
                target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(
                        {
                            "reply_text": "我先按状态机这条主线往下推。",
                            "next_question": "",
                            "actions": [],
                            "debug_notes": "",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return {"status": "executed", "reason": "ok"}

            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "frontend_route_conversation_mode", return_value="PROJECT_DETAIL"
            ), mock.patch.object(
                support_bot, "sync_project_context", side_effect=_fake_sync_project_context
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                _doc, run_dir = support_bot.process_message(
                    chat_id="runtime-frontdesk-demo",
                    user_text="请帮我把前台改成状态机",
                    source="stdin",
                )

            session_state = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            frontdesk_state = dict(session_state.get("frontdesk_state", {}))
            latest_support_context = dict(session_state.get("latest_support_context", {}))
            history_layers = dict(session_state.get("history_layers", {}))
            working_memory = dict(history_layers.get("working_memory", {}))
            raw_turns = list(history_layers.get("raw_turns", []))
            self.assertEqual(str(frontdesk_state.get("state", "")), "Execute")
            self.assertEqual(str(frontdesk_state.get("active_task_id", "")), "r-frontdesk")
            self.assertEqual(str(latest_support_context.get("frontdesk_state", "")), "Execute")
            self.assertEqual(str(session_state.get("active_task_id", "")), "r-frontdesk")
            self.assertEqual(str(session_state.get("active_run_id", "")), "r-frontdesk")
            self.assertEqual(str(session_state.get("active_stage", "")), "EXECUTE")
            self.assertEqual(str(session_state.get("latest_message_intent", "")), "continue")
            self.assertEqual(str(working_memory.get("current_stage", "")), "EXECUTE")
            self.assertGreaterEqual(len(raw_turns), 2)

    def test_support_bot_greeting_turn_still_uses_provider_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_greeting_") as td:
            runs_root = Path(td) / "runs"

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                self.assertEqual(provider, "api_agent")
                target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(
                        {
                            "reply_text": "你好，这边在，直接说你这轮要推进什么。",
                            "next_question": "",
                            "actions": [],
                            "debug_notes": "",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return {"status": "executed", "reason": "ok", "target_path": str(request.get("target_path", ""))}

            config = {"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent"}}
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, run_dir = support_bot.process_message(
                    chat_id="runtime-greeting-demo",
                    user_text="你好",
                    source="stdin",
                    provider_override="api_agent",
                )

            self.assertEqual(str(doc.get("provider", "")), "api_agent")
            self.assertTrue((run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH).exists())
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("SUPPORT_PROVIDER_SELECTED", events)

    def test_support_bot_api_failure_wires_into_local_fallback_reply_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_failover_") as td:
            runs_root = Path(td) / "runs"
            observed: list[tuple[str, dict[str, object]]] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                observed.append((provider, dict(request)))
                target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                if provider == "api_agent":
                    return {"status": "exec_failed", "reason": "connect timeout"}
                if provider == "ollama_agent":
                    target.write_text(
                        json.dumps(
                            {
                                "reply_text": "本地这边先继续接住你这轮需求。",
                                "next_question": "",
                                "actions": [],
                                "debug_notes": "",
                            },
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                    return {"status": "executed", "reason": "ok", "target_path": str(request.get("target_path", ""))}
                raise AssertionError(f"unexpected provider: {provider}")

            config = {"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent", "support_local_fallback": "ollama_agent"}}
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ):
                doc, run_dir = support_bot.process_message(
                    chat_id="runtime-failover-demo",
                    user_text="请继续这个项目",
                    source="stdin",
                )

            self.assertEqual([provider for provider, _ in observed], ["api_agent", "ollama_agent"])
            self.assertEqual(str(dict(observed[1][1].get("provider_failover", {})).get("failed_provider", "")), "api_agent")
            self.assertEqual(str(doc.get("provider", "")), "ollama_agent")
            self.assertIn("API", str(doc.get("reply_text", "")))
            self.assertIn("本地", str(doc.get("reply_text", "")))
            reply_path = run_dir / support_bot.SUPPORT_REPLY_REL_PATH
            self.assertTrue(reply_path.exists())
            saved = json.loads(reply_path.read_text(encoding="utf-8"))
            self.assertIn("API", str(saved.get("reply_text", "")))

    def test_support_bot_greeting_stale_context_retries_api_before_local_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_greeting_repair_") as td:
            runs_root = Path(td) / "runs"
            observed: list[tuple[str, dict[str, object]]] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del config
                observed.append((provider, dict(request)))
                target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                if len(observed) == 1:
                    target.write_text(
                        json.dumps(
                            {
                                "reply_text": "您好，我们这边可以继续推进项目方案和开发节奏。",
                                "next_question": "",
                                "actions": [],
                                "debug_notes": "",
                            },
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                else:
                    target.write_text(
                        json.dumps(
                            {
                                "reply_text": "你好，这轮要处理什么你直接说。",
                                "next_question": "",
                                "actions": [],
                                "debug_notes": "",
                            },
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                return {"status": "executed", "reason": "ok", "target_path": str(request.get("target_path", ""))}

            config = {"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent", "support_local_fallback": "ollama_agent"}}
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
                    chat_id="runtime-greeting-repair-demo",
                    user_text="你好",
                    source="stdin",
                )

            self.assertEqual([provider for provider, _ in observed], ["api_agent", "api_agent"])
            self.assertEqual(str(dict(observed[1][1].get("reply_guard", {})).get("guard_reason", "")), "stale project context on greeting reply")
            self.assertEqual(str(doc.get("provider", "")), "api_agent")
            self.assertNotIn("你好，随时可以开始。你说说看要做什么？", str(doc.get("reply_text", "")))

    def test_support_bot_project_turn_calls_bridge_entrypoints_and_consumes_whiteboard_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_bridge_") as td:
            runs_root = Path(td) / "runs"
            support_context = {
                "run_id": "r-demo",
                "run_dir": "D:/tmp/r-demo",
                "goal": "VN 剧情项目",
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
                    "query": "VN 剧情项目",
                    "hits": [{"path": "docs/10_team_mode.md", "start_line": 1, "snippet": "support bot"}],
                    "lookup_error": "",
                    "snapshot": {"path": "artifacts/support_whiteboard.json", "entry_count": 1, "entries": []},
                },
            }

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                self.assertEqual(str(request.get("project_run", {}).get("run_id", "")), "r-demo")
                self.assertEqual(str(request.get("whiteboard", {}).get("path", "")), "artifacts/support_whiteboard.json")
                target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(
                    json.dumps(
                        {
                            "reply_text": "收到，我已经接到后台项目里。",
                            "next_question": "",
                            "actions": [],
                            "debug_notes": "",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )
                return {"status": "executed", "reason": "ok", "target_path": str(request.get("target_path", ""))}

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
                    chat_id="runtime-bridge-demo",
                    user_text="我想做一个帮我整理 VN 剧情节奏的项目。",
                    source="stdin",
                )

            self.assertEqual(str(doc.get("provider_status", "")), "executed")
            new_run_spy.assert_called_once_with(goal="我想做一个帮我整理 VN 剧情节奏的项目。")
            record_spy.assert_called_once()
            advance_spy.assert_called_once_with("r-demo", max_steps=4)
            self.assertEqual(context_spy.call_count, 2)
            session_state = json.loads((run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(session_state.get("bound_run_id", "")), "r-demo")

    def test_support_bot_current_turn_router_does_not_reopen_project_intake_for_short_followup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_turn_router_") as td:
            run_dir = Path(td)
            project_request = "i want to create a project to help me make vn games, especially in clarify storyline"
            _append_jsonl(
                run_dir / support_bot.SUPPORT_INBOX_REL_PATH,
                {
                    "ts": support_bot.now_iso(),
                    "source": "telegram",
                    "text": project_request,
                },
            )
            state = support_bot.default_support_session_state("turn-router-demo")
            state["project_memory"]["project_brief"] = project_request
            state["task_summary"] = project_request
            mode = support_bot.detect_conversation_mode(run_dir, "没有，你先做着", state)
            self.assertEqual(mode, "PROJECT_DETAIL")

    def test_support_bot_bound_run_execution_directive_stays_project_detail_with_constraint_only_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_bound_run_directive_") as td:
            run_dir = Path(td)
            state = support_bot.default_support_session_state("bound-run-directive-demo")
            state["bound_run_id"] = "r-demo"
            state["project_memory"]["project_brief"] = "window开发，然后ui可以使用qt6"
            state["task_summary"] = "window开发，然后ui可以使用qt6"
            mode = support_bot.detect_conversation_mode(run_dir, "你先做出第一版给我看，然后我在做调整", state)
            self.assertEqual(mode, "PROJECT_DETAIL")

    def test_support_bot_capability_query_stays_non_project_mode(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_capability_mode_") as td:
            run_dir = Path(td)
            state = support_bot.default_support_session_state("capability-mode-demo")
            state["project_memory"]["project_brief"] = "我想做一个无人机视频转点云项目"
            state["task_summary"] = "我想做一个无人机视频转点云项目"
            mode = support_bot.detect_conversation_mode(run_dir, "你是谁", state)
            self.assertEqual(mode, "CAPABILITY_QUERY")

    def test_support_bot_stdin_entrypoint_consumes_process_message_output(self) -> None:
        with mock.patch.object(
            support_bot,
            "process_message",
            return_value=({"reply_text": "public reply"}, Path("D:/tmp/support-session")),
        ) as process_spy, mock.patch("sys.stdin", io.StringIO("hello")), mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            rc = support_bot.run_stdin_mode(chat_id="local_demo")

        self.assertEqual(rc, 0)
        process_spy.assert_called_once_with(chat_id="local_demo", user_text="hello", source="stdin", provider_override="")
        self.assertEqual(stdout.getvalue().strip(), "public reply")

    def test_telegram_mode_emits_project_package_document_from_support_actions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_support_tg_delivery_") as td:
            root = Path(td)
            support_run_dir = root / "support-session"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            bound_run_dir = root / "runs" / "bound-vn"
            (bound_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            project_dir = root / "generated_projects" / "vn_story_organizer"
            project_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "main.py").write_text("print('vn')\n", encoding="utf-8")
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

            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "r-vn"
            state["bound_run_dir"] = str(bound_run_dir)
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (bound_run_dir / "artifacts" / "patch_apply.json").write_text(
                json.dumps({"touched_files": ["generated_projects/vn_story_organizer/main.py"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (bound_run_dir / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: generated_projects/vn_story_organizer/\n",
                encoding="utf-8",
            )

            class _FakeTelegram:
                def __init__(self, token: str, timeout_sec: int) -> None:
                    del token, timeout_sec
                    self.sent_messages: list[tuple[int, str]] = []
                    self.sent_documents: list[tuple[int, Path, str]] = []
                    self.calls = 0

                def get_updates(self, offset: int) -> list[dict[str, object]]:
                    del offset
                    self.calls += 1
                    if self.calls == 1:
                        return [{"update_id": 1, "message": {"chat": {"id": 123}, "text": "zip就行"}}]
                    raise KeyboardInterrupt()

                def send_message(self, chat_id: int, text: str) -> None:
                    self.sent_messages.append((chat_id, text))

                def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    self.sent_documents.append((chat_id, file_path, caption))

                def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    raise AssertionError(f"unexpected photo send: {file_path}")

            fake_holder: dict[str, _FakeTelegram] = {}

            def _fake_tg_factory(token: str, timeout_sec: int) -> _FakeTelegram:
                fake_holder["tg"] = _FakeTelegram(token, timeout_sec)
                return fake_holder["tg"]

            with mock.patch.object(support_bot, "TelegramClient", side_effect=_fake_tg_factory), mock.patch.object(
                support_bot, "process_message", return_value=(
                    {"reply_text": "项目包我直接发到当前对话。", "actions": [{"type": "send_project_package", "format": "zip"}]},
                    support_run_dir,
                )
            ) as process_spy, mock.patch.object(
                support_bot, "ROOT", root
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                return_value={
                    "run_id": "r-vn",
                    "run_dir": str(bound_run_dir),
                    "status": {
                        "run_status": "completed",
                        "verify_result": "PASS",
                        "needs_user_decision": False,
                        "decisions_needed_count": 0,
                        "gate": {"state": "closed", "owner": "", "reason": ""},
                    },
                },
            ), mock.patch.object(
                support_bot,
                "_materialize_support_scaffold_project",
                return_value=scaffold_dir,
            ):
                with self.assertRaises(KeyboardInterrupt):
                    support_bot.run_telegram_mode(token="fake", poll_seconds=1, allowlist_raw="")

            fake = fake_holder["tg"]
            self.assertEqual(fake.sent_messages, [(123, "项目包我直接发到当前对话。")])
            self.assertEqual(len(fake.sent_documents), 1)
            self.assertTrue(fake.sent_documents[0][1].exists(), msg=str(fake.sent_documents[0][1]))
            self.assertEqual(fake.sent_documents[0][1].name, "vn_story_organizer_ctcp_project.zip")
            process_spy.assert_called_once_with(chat_id="123", user_text="zip就行", source="telegram", provider_override="")
            manifest = json.loads((support_run_dir / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(len(list(manifest.get("sent", []))), 1)

    def test_run_telegram_mode_does_not_push_no_change_proactive_progress_when_idle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_telegram_proactive_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "run-proactive"
            state["bound_run_dir"] = "D:/tmp/run-proactive"
            state["notification_state"]["last_progress_ts"] = "2026-03-24T00:00:00Z"
            state["notification_state"]["last_progress_hash"] = "legacy-progress-hash"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            running_context = {
                "run_id": "run-proactive",
                "run_dir": "D:/tmp/run-proactive",
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
            blocked_context = {
                "run_id": "run-proactive",
                "run_dir": "D:/tmp/run-proactive",
                "goal": "我想要你继续优化我的vn项目",
                "status": {
                    "run_status": "blocked",
                    "verify_result": "",
                    "gate": {
                        "state": "blocked",
                        "owner": "Contract Guardian",
                        "reason": "waiting for APPROVE review_contract (verdict=BLOCK)",
                    },
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                },
                "whiteboard": {},
            }
            context_calls = {"count": 0}

            def _fake_get_support_context(_run_id: str) -> dict[str, object]:
                context_calls["count"] += 1
                return running_context if context_calls["count"] == 1 else blocked_context

            class _FakeTelegram:
                def __init__(self, token: str, timeout_sec: int) -> None:
                    del token, timeout_sec
                    self.sent_messages: list[tuple[int, str]] = []
                    self.calls = 0

                def get_updates(self, offset: int) -> list[dict[str, object]]:
                    del offset
                    self.calls += 1
                    if self.calls == 1:
                        return []
                    raise KeyboardInterrupt()

                def send_message(self, chat_id: int, text: str) -> None:
                    self.sent_messages.append((chat_id, text))

                def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    raise AssertionError(f"unexpected document send: {file_path} {caption}")

                def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    raise AssertionError(f"unexpected photo send: {file_path} {caption}")

            fake_holder: dict[str, _FakeTelegram] = {}

            def _fake_tg_factory(token: str, timeout_sec: int) -> _FakeTelegram:
                fake_holder["tg"] = _FakeTelegram(token, timeout_sec)
                return fake_holder["tg"]

            with mock.patch.object(support_bot, "TelegramClient", side_effect=_fake_tg_factory), mock.patch.object(
                support_bot, "get_runs_root", return_value=runs_root
            ), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                side_effect=_fake_get_support_context,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ) as advance_spy, mock.patch.object(
                support_bot,
                "build_grounded_status_reply_doc",
                return_value={"reply_text": "合同评审有新进展，我已经同步到当前阶段。", "provider_status": "executed", "actions": []},
            ):
                with self.assertRaises(KeyboardInterrupt):
                    support_bot.run_telegram_mode(token="fake", poll_seconds=1, allowlist_raw="123")

            fake = fake_holder["tg"]
            self.assertEqual(fake.sent_messages, [])
            advance_spy.assert_called_once_with("run-proactive", max_steps=2)
            updated_state = json.loads((support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            notification_state = dict(updated_state.get("notification_state", {}))
            self.assertEqual(str(notification_state.get("last_progress_hash", "")), "legacy-progress-hash")
            self.assertTrue(str(notification_state.get("last_auto_advance_ts", "")))

    def test_run_telegram_mode_read_timeout_logs_are_throttled(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_telegram_timeout_") as td:
            root = Path(td)
            runs_root = root / "runs"

            class _FakeTelegram:
                def __init__(self, token: str, timeout_sec: int) -> None:
                    del token, timeout_sec
                    self.calls = 0

                def clear_webhook(self, drop_pending_updates: bool = False) -> None:
                    del drop_pending_updates

                def get_updates(self, offset: int) -> list[dict[str, object]]:
                    del offset
                    self.calls += 1
                    if self.calls <= 5:
                        raise TimeoutError("The read operation timed out")
                    raise KeyboardInterrupt()

            fake_holder: dict[str, _FakeTelegram] = {}

            def _fake_tg_factory(token: str, timeout_sec: int) -> _FakeTelegram:
                fake_holder["tg"] = _FakeTelegram(token, timeout_sec)
                return fake_holder["tg"]

            stderr_buffer = io.StringIO()
            with mock.patch.object(support_bot, "TelegramClient", side_effect=_fake_tg_factory), mock.patch.object(
                support_bot, "get_runs_root", return_value=runs_root
            ), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot.time,
                "sleep",
                return_value=None,
            ), mock.patch.object(
                support_bot,
                "run_proactive_support_cycle",
                return_value=None,
            ) as proactive_spy, mock.patch("sys.stderr", new=stderr_buffer):
                with self.assertRaises(KeyboardInterrupt):
                    support_bot.run_telegram_mode(token="fake", poll_seconds=1, allowlist_raw="123")

            self.assertEqual(fake_holder["tg"].calls, 6)
            self.assertEqual(proactive_spy.call_count, 5)
            logs = stderr_buffer.getvalue()
            self.assertNotIn("telegram getUpdates error (streak=1)", logs)
            self.assertNotIn("telegram getUpdates error (streak=2)", logs)
            self.assertNotIn("telegram getUpdates error (streak=3)", logs)
            self.assertIn("telegram getUpdates timeout (streak=5)", logs)

    def test_run_proactive_support_cycle_asks_decision_once_for_same_prompt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_decision_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "run-decision"
            state["bound_run_dir"] = "D:/tmp/run-decision"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            decision_context = {
                "run_id": "run-decision",
                "run_dir": "D:/tmp/run-decision",
                "goal": "继续优化 VN 项目",
                "status": {
                    "run_status": "blocked",
                    "verify_result": "",
                    "gate": {"state": "blocked", "owner": "chair", "reason": "waiting for one decision"},
                    "needs_user_decision": True,
                    "decisions_needed_count": 1,
                },
                "decisions": {
                    "count": 1,
                    "decisions": [
                        {"decision_id": "outbox:1", "question_hint": "这轮你要先保速度，还是先保质量？"},
                    ],
                },
                "whiteboard": {},
            }

            class _FakeTelegram:
                def __init__(self) -> None:
                    self.sent_messages: list[tuple[int, str]] = []

                def send_message(self, chat_id: int, text: str) -> None:
                    self.sent_messages.append((chat_id, text))

            fake = _FakeTelegram()
            with mock.patch.object(support_bot, "get_runs_root", return_value=runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                return_value=decision_context,
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "skipped"},
            ) as advance_spy:
                support_bot.run_proactive_support_cycle(fake, allowlist={123})
                support_bot.run_proactive_support_cycle(fake, allowlist={123})

            self.assertEqual(len(fake.sent_messages), 1)
            self.assertEqual(fake.sent_messages[0][0], 123)
            self.assertIn("先拍一个板", fake.sent_messages[0][1])
            self.assertIn("先保速度", fake.sent_messages[0][1])
            advance_spy.assert_not_called()
            updated_state = json.loads((support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            notification_state = dict(updated_state.get("notification_state", {}))
            self.assertTrue(str(notification_state.get("last_decision_prompt_hash", "")))
            self.assertEqual(str(notification_state.get("last_sent_kind", "")), "decision")

    def test_support_bot_rejects_in_repo_run_dir(self) -> None:
        with mock.patch.object(support_bot, "get_runs_root", return_value=ROOT), mock.patch.object(
            support_bot, "get_repo_slug", return_value="ctcp"
        ):
            with self.assertRaises(SystemExit):
                support_bot.session_run_dir("bad-chat")


if __name__ == "__main__":
    unittest.main()
