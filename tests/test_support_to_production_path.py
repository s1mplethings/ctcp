from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_front_bridge
import scripts.ctcp_support_bot as support_bot


SUPPORT_FRONTEND_TURNS_REL = Path("artifacts") / "support_frontend_turns.jsonl"
SUPPORT_WHITEBOARD_REL = Path("artifacts") / "support_whiteboard.json"


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = raw.strip()
        if not text:
            continue
        rows.append(json.loads(text))
    return rows


def _write_provider_doc(run_dir: Path, reply_text: str, next_question: str = "") -> None:
    target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "reply_text": reply_text,
                "next_question": next_question,
                "actions": [],
                "debug_notes": "",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _fake_librarian_hits(query: str) -> list[dict[str, Any]]:
    return [
        {
            "path": "docs/10_team_mode.md",
            "start_line": 1,
            "snippet": f"support path query={query[:32]}",
        }
    ]


def _make_fake_orchestrate_runtime(run_dir: Path, *, run_id: str, goal: str) -> tuple[dict[str, Any], Any]:
    state: dict[str, Any] = {
        "run_id": run_id,
        "goal": goal,
        "run_status": "running",
        "verify_result": "",
        "gate_state": "dispatch",
        "gate_owner": "patchmaker",
        "gate_path": "artifacts/PLAN.md",
        "gate_reason": "waiting for next production step",
        "new_run_calls": 0,
        "advance_calls": 0,
        "last_max_steps": 0,
    }

    def _sync_run_artifacts() -> None:
        _write_json(
            run_dir / "RUN.json",
            {
                "status": state["run_status"],
                "goal": state["goal"],
                "verify_iterations": 0,
                "max_iterations": 8,
                "max_iterations_source": "test",
            },
        )
        _write_json(
            run_dir / "artifacts" / "verify_report.json",
            {
                "result": state["verify_result"],
                "gate": "workflow",
            },
        )
        _write_json(
            run_dir / "artifacts" / "frontend_request.json",
            {
                "schema_version": "ctcp-frontend-request-v1",
                "ts": "2026-03-12T00:00:00Z",
                "goal": state["goal"],
                "constraints": {},
                "attachments": [],
            },
        )

    def _fake_run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
        del cwd
        action = str(cmd[2]) if len(cmd) > 2 else ""
        if action == "new-run":
            state["new_run_calls"] += 1
            if "--goal" in cmd:
                state["goal"] = str(cmd[cmd.index("--goal") + 1])
            _sync_run_artifacts()
            return {
                "cmd": " ".join(cmd),
                "exit_code": 0,
                "stdout": f"[ctcp_orchestrate] run_dir={run_dir}\n",
                "stderr": "",
            }
        if action == "status":
            _sync_run_artifacts()
            stdout = "\n".join(
                [
                    f"[ctcp_orchestrate] run_dir={run_dir}",
                    f"[ctcp_orchestrate] run_status={state['run_status']}",
                    f"[ctcp_orchestrate] next={state['gate_state']}",
                    f"[ctcp_orchestrate] owner={state['gate_owner']}",
                    f"[ctcp_orchestrate] path={state['gate_path']}",
                    f"[ctcp_orchestrate] reason={state['gate_reason']}",
                ]
            )
            return {
                "cmd": " ".join(cmd),
                "exit_code": 0,
                "stdout": stdout + "\n",
                "stderr": "",
            }
        if action == "advance":
            state["advance_calls"] += 1
            if "--max-steps" in cmd:
                state["last_max_steps"] = int(cmd[cmd.index("--max-steps") + 1])
            _sync_run_artifacts()
            return {
                "cmd": " ".join(cmd),
                "exit_code": 0,
                "stdout": f"[ctcp_orchestrate] reached max-steps={state['last_max_steps']}\n",
                "stderr": "",
            }
        raise AssertionError(f"unexpected orchestrate action: {action}")

    _sync_run_artifacts()
    return state, _fake_run_cmd


class SupportToProductionPathTests(unittest.TestCase):
    def test_level1_bridge_writes_support_turn_into_production_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_path_level1_") as td:
            run_dir = Path(td)
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge.ctcp_dispatch.local_librarian,
                "search",
                side_effect=lambda repo_root, query, k=4: _fake_librarian_hits(str(query)),
            ):
                result = ctcp_front_bridge.ctcp_record_support_turn(
                    "r-progressive",
                    text="我想做一个帮我理顺 VN 剧情结构的项目。",
                    source="support_bot",
                    chat_id="demo-chat",
                    conversation_mode="PROJECT_DETAIL",
                )

            turns = _read_jsonl(run_dir / SUPPORT_FRONTEND_TURNS_REL)
            self.assertEqual(len(turns), 1)
            self.assertEqual(str(turns[0].get("conversation_mode", "")), "PROJECT_DETAIL")
            self.assertEqual(str(result.get("written_path", "")), SUPPORT_FRONTEND_TURNS_REL.as_posix())
            whiteboard = dict(result.get("whiteboard", {}))
            self.assertEqual(str(whiteboard.get("path", "")), SUPPORT_WHITEBOARD_REL.as_posix())
            self.assertEqual(len(list(whiteboard.get("hits", []))), 1)
            self.assertEqual(int(whiteboard.get("snapshot", {}).get("entry_count", 0) or 0), 2)
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("FRONT_SUPPORT_TURN_WRITTEN", events)

    def test_level2_bridge_reads_production_truth_back_into_support_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_path_level2_") as td:
            run_dir = Path(td)
            state, fake_run_cmd = _make_fake_orchestrate_runtime(
                run_dir,
                run_id="r-progressive",
                goal="VN 剧情结构项目",
            )
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge,
                "_run_cmd",
                side_effect=fake_run_cmd,
            ), mock.patch.object(
                ctcp_front_bridge.ctcp_dispatch.local_librarian,
                "search",
                side_effect=lambda repo_root, query, k=4: _fake_librarian_hits(str(query)),
            ):
                ctcp_front_bridge.ctcp_record_support_turn(
                    "r-progressive",
                    text="先把 VN 剧情主线梳理清楚。",
                    source="support_bot",
                    chat_id="demo-chat",
                    conversation_mode="PROJECT_DETAIL",
                )
                context = ctcp_front_bridge.ctcp_get_support_context("r-progressive")

            self.assertEqual(str(context.get("goal", "")), "VN 剧情结构项目")
            self.assertEqual(str(context.get("status", {}).get("run_status", "")), "running")
            self.assertEqual(str(context.get("status", {}).get("gate", {}).get("state", "")), str(state["gate_state"]))
            self.assertEqual(str(context.get("frontend_request", {}).get("goal", "")), "VN 剧情结构项目")
            self.assertEqual(str(context.get("whiteboard", {}).get("path", "")), SUPPORT_WHITEBOARD_REL.as_posix())
            self.assertEqual(len(list(context.get("whiteboard", {}).get("hits", []))), 1)

    def test_level3_support_entry_creates_binds_and_advances_production_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_path_level3_") as td:
            base_dir = Path(td)
            session_runs_root = base_dir / "support_runs_root"
            production_run = base_dir / "ctcp_runs" / "r-progressive"
            state, fake_run_cmd = _make_fake_orchestrate_runtime(
                production_run,
                run_id="r-progressive",
                goal="placeholder",
            )

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del config
                self.assertEqual(provider, "api_agent")
                self.assertEqual(str(request.get("project_run", {}).get("run_id", "")), "r-progressive")
                self.assertEqual(str(request.get("whiteboard", {}).get("path", "")), SUPPORT_WHITEBOARD_REL.as_posix())
                self.assertGreaterEqual(int(request.get("whiteboard", {}).get("snapshot", {}).get("entry_count", 0) or 0), 2)
                _write_provider_doc(run_dir, "收到，我已经把你的项目需求接到后台 run。")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            config = {"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent"}}
            with mock.patch.object(support_bot, "get_runs_root", return_value=session_runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "_run_cmd", side_effect=fake_run_cmd
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "_resolve_latest_run_dir", return_value=production_run
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "_resolve_run_dir", return_value=production_run
            ), mock.patch.object(
                support_bot.ctcp_front_bridge.ctcp_dispatch.local_librarian,
                "search",
                side_effect=lambda repo_root, query, k=4: _fake_librarian_hits(str(query)),
            ):
                doc, support_session_dir = support_bot.process_message(
                    chat_id="progressive-demo",
                    user_text="我想做一个帮我整理 VN 剧情结构的项目。",
                    source="stdin",
                )

            self.assertEqual(int(state.get("new_run_calls", 0) or 0), 1)
            self.assertEqual(int(state.get("advance_calls", 0) or 0), 1)
            self.assertEqual(int(state.get("last_max_steps", 0) or 0), 4)
            self.assertTrue((production_run / "artifacts" / "frontend_request.json").exists())
            self.assertTrue((production_run / SUPPORT_FRONTEND_TURNS_REL).exists())
            self.assertTrue((production_run / SUPPORT_WHITEBOARD_REL).exists())
            self.assertTrue((support_session_dir / support_bot.SUPPORT_REPLY_REL_PATH).exists())
            session_state = json.loads((support_session_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(session_state.get("bound_run_id", "")), "r-progressive")
            self.assertEqual(str(doc.get("reply_text", "")), "收到，我已经把你的项目需求接到后台 run。")
            production_events = (production_run / "events.jsonl").read_text(encoding="utf-8", errors="replace")
            self.assertIn("FRONT_SUPPORT_TURN_WRITTEN", production_events)

    def test_level4_bound_status_query_reuses_production_run_truth(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_path_level4_") as td:
            base_dir = Path(td)
            session_runs_root = base_dir / "support_runs_root"
            production_run = base_dir / "ctcp_runs" / "r-progressive"
            state, fake_run_cmd = _make_fake_orchestrate_runtime(
                production_run,
                run_id="r-progressive",
                goal="placeholder",
            )
            observed_statuses: list[str] = []

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del config
                self.assertEqual(provider, "api_agent")
                project_run = request.get("project_run", {})
                observed_statuses.append(str(project_run.get("status", {}).get("run_status", "")))
                if len(observed_statuses) == 1:
                    _write_provider_doc(run_dir, "收到，我已经把项目需求接到后台 run。")
                else:
                    _write_provider_doc(run_dir, "当前项目还在继续推进。")
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            config = {"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent"}}
            with mock.patch.object(support_bot, "get_runs_root", return_value=session_runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "_run_cmd", side_effect=fake_run_cmd
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "_resolve_latest_run_dir", return_value=production_run
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "_resolve_run_dir", return_value=production_run
            ), mock.patch.object(
                support_bot.ctcp_front_bridge.ctcp_dispatch.local_librarian,
                "search",
                side_effect=lambda repo_root, query, k=4: _fake_librarian_hits(str(query)),
            ):
                support_bot.process_message(
                    chat_id="progressive-status-demo",
                    user_text="我想做一个帮我整理 VN 剧情结构的项目。",
                    source="stdin",
                )
                doc, _support_session_dir = support_bot.process_message(
                    chat_id="progressive-status-demo",
                    user_text="现在进度到哪了？",
                    source="stdin",
                )

            self.assertEqual(int(state.get("new_run_calls", 0) or 0), 1)
            self.assertEqual(int(state.get("advance_calls", 0) or 0), 1)
            self.assertEqual(observed_statuses, ["running", "running"])
            turns = _read_jsonl(production_run / SUPPORT_FRONTEND_TURNS_REL)
            self.assertEqual(len(turns), 2)
            self.assertEqual(str(doc.get("reply_text", "")), "当前项目还在继续推进。")

    def test_bridge_canonical_runtime_state_and_decision_submission_requires_backend_consume(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_bridge_canonical_") as td:
            run_dir = Path(td)
            state, fake_run_cmd = _make_fake_orchestrate_runtime(run_dir, run_id="r-canonical", goal="决策链路验证")
            state["run_status"] = "blocked"
            state["gate_state"] = "blocked"
            state["gate_owner"] = "chair"
            state["gate_reason"] = "请确认交付格式"
            outbox_prompt = run_dir / "outbox" / "decision_format.md"
            outbox_prompt.parent.mkdir(parents=True, exist_ok=True)
            outbox_prompt.write_text(
                "\n".join(
                    [
                        "Role: chair/planner",
                        "Action: decide",
                        "Target-Path: artifacts/answers/delivery_format.md",
                        "Reason: choose delivery format",
                        "Question: 你这轮是先要 zip 包，还是先看截图？",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake_run_cmd
            ):
                status_before = ctcp_front_bridge.ctcp_get_status("r-canonical")
                self.assertEqual(str(status_before.get("phase", "")), "WAIT_USER_DECISION")
                self.assertTrue(bool(status_before.get("needs_user_decision", False)))

                decisions = ctcp_front_bridge.ctcp_list_decisions_needed("r-canonical")
                self.assertEqual(int(decisions.get("count", 0)), 1)
                row = dict(list(decisions.get("decisions", []))[0])
                self.assertEqual(str(row.get("status", "")), "pending")
                self.assertTrue(bool(str(row.get("decision_id", ""))))
                self.assertTrue(bool(str(row.get("question", ""))))
                self.assertTrue(bool(str(row.get("target_path", ""))))
                self.assertTrue(bool(str(row.get("expected_format", ""))))
                self.assertIn("created_at", row)
                self.assertIn("submitted_at", row)
                self.assertIn("consumed_at", row)

                submit = ctcp_front_bridge.ctcp_submit_decision(
                    "r-canonical",
                    {"decision_id": str(row.get("decision_id", "")), "content": "先给我 zip 包"},
                )
                self.assertTrue(bool(submit.get("written", False)))
                self.assertEqual(str(submit.get("decision_status", "")), "submitted")
                self.assertFalse(bool(submit.get("backend_acknowledged", False)))

                status_submitted = ctcp_front_bridge.ctcp_get_status("r-canonical")
                self.assertFalse(bool(status_submitted.get("needs_user_decision", False)))
                pending_after_submit = list(
                    dict(status_submitted.get("runtime_state", {})).get("pending_decisions", [])
                )
                self.assertTrue(any(str(dict(item).get("status", "")) == "submitted" for item in pending_after_submit))

                state["run_status"] = "running"
                state["gate_state"] = "open"
                state["gate_owner"] = "patchmaker"
                state["gate_reason"] = "continuing execution"
                consumed_status = ctcp_front_bridge.ctcp_get_status("r-canonical")
                decisions_after_consume = list(
                    dict(consumed_status.get("runtime_state", {})).get("decisions", [])
                )
                decision_rows = [dict(item) for item in decisions_after_consume if str(dict(item).get("decision_id", "")) == str(row.get("decision_id", ""))]
                self.assertTrue(decision_rows)
                self.assertEqual(str(decision_rows[0].get("status", "")), "consumed")

                state["run_status"] = "completed"
                state["verify_result"] = "PASS"
                state["gate_state"] = "closed"
                state["gate_reason"] = "done"
                final_status = ctcp_front_bridge.ctcp_get_status("r-canonical")
                self.assertEqual(str(final_status.get("phase", "")), "FINALIZE")
                self.assertEqual(int(final_status.get("decisions_needed_count", 0) or 0), 0)

    def test_bridge_failure_state_does_not_reintroduce_previous_pending_decisions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_bridge_failure_") as td:
            run_dir = Path(td)
            state, fake_run_cmd = _make_fake_orchestrate_runtime(run_dir, run_id="r-failed", goal="失败恢复验证")
            state["run_status"] = "fail"
            state["gate_state"] = "error"
            state["gate_reason"] = "verify failed"
            runtime_state_path = run_dir / "artifacts" / "support_runtime_state.json"
            runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
            runtime_state_path.write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-support-runtime-state-v1",
                        "run_id": "r-failed",
                        "run_dir": str(run_dir),
                        "phase": "EXECUTE",
                        "run_status": "blocked",
                        "blocking_reason": "decision_submitted_waiting_backend_consume",
                        "needs_user_decision": False,
                        "pending_decisions": [
                            {
                                "decision_id": "outbox:old",
                                "kind": "outbox_prompt",
                                "question": "旧决策",
                                "target_path": "artifacts/answers/old.md",
                                "expected_format": "text",
                                "schema": {"type": "string"},
                                "status": "submitted",
                                "created_at": "2026-03-29T00:00:00Z",
                                "submitted_at": "2026-03-29T00:01:00Z",
                                "consumed_at": "",
                                "submission_state_hash": "legacy-hash",
                            }
                        ],
                        "decisions": [],
                        "latest_result": {},
                        "error": {"has_error": False, "code": "", "message": ""},
                        "recovery": {"needed": False, "hint": "", "status": "none"},
                        "gate": {"state": "blocked", "owner": "chair", "path": "", "reason": "legacy"},
                        "iterations": {"current": 0, "max": 8, "source": "test"},
                        "verify_result": "",
                        "verify_gate": "",
                        "decisions_needed_count": 0,
                        "open_decisions_count": 1,
                        "submitted_decisions_count": 1,
                        "core_hash": "legacy-hash",
                        "updated_at": "2026-03-29T00:01:00Z",
                        "snapshot_source": "canonical_snapshot",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake_run_cmd
            ):
                status = ctcp_front_bridge.ctcp_get_status("r-failed")
                self.assertEqual(str(status.get("phase", "")), "RECOVER")
                self.assertTrue(bool(dict(status.get("error", {})).get("has_error", False)))
                self.assertEqual(int(status.get("decisions_needed_count", 0) or 0), 0)
                pending_rows = list(dict(status.get("runtime_state", {})).get("pending_decisions", []))
                self.assertEqual(len(pending_rows), 0)


if __name__ == "__main__":
    unittest.main()
