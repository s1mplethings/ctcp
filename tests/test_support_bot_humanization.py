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

    def test_collect_public_delivery_state_finds_generated_project_package_source(self) -> None:
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
                    project_context=None,
                    source="telegram",
                )

            self.assertTrue(bool(delivery.get("package_ready", False)))
            self.assertFalse(bool(delivery.get("screenshot_ready", False)))
            self.assertIn(str(generated_project.resolve()), list(delivery.get("package_source_dirs", [])))
            self.assertEqual(str(delivery.get("package_delivery_mode", "")), "materialize_ctcp_scaffold")
            self.assertEqual(str(delivery.get("project_name_hint", "")), "vn_story_organizer")
            self.assertIn("docs/", list(delivery.get("package_structure_hint", [])))

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
                    "screenshot_ready": False,
                    "package_source_dirs": ["D:/tmp/vn_story_organizer"],
                    "existing_package_files": [],
                    "screenshot_files": [],
                },
            )

            self.assertTrue(any(str(item.get("type", "")) == "send_project_package" for item in list(doc.get("actions", []))))
            self.assertIn("不用再留邮箱", str(doc.get("reply_text", "")))

    def test_public_delivery_prompt_context_exposes_ctcp_scaffold_shape(self) -> None:
        ctx = support_bot.public_delivery_prompt_context(
            {
                "channel": "telegram",
                "channel_can_send_files": True,
                "package_ready": True,
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
        self.assertIn("docs/", list(ctx.get("package_structure_hint", [])))

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
