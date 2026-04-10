from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.ctcp_support_bot as support_bot


def _blocked_project_context(
    *,
    run_id: str,
    goal: str,
    phase: str,
    gate_path: str,
    gate_reason: str,
    recovery: dict[str, object] | None = None,
) -> dict[str, object]:
    gate = {
        "state": "blocked",
        "owner": "Chair/Planner",
        "path": gate_path,
        "reason": gate_reason,
    }
    runtime_recovery = recovery if isinstance(recovery, dict) else {"needed": False, "hint": "", "status": "none"}
    runtime_state = {
        "phase": phase,
        "run_status": "running",
        "blocking_reason": gate_reason,
        "gate": dict(gate),
        "needs_user_decision": False,
        "decisions_needed_count": 0,
        "recovery": runtime_recovery,
    }
    return {
        "run_id": run_id,
        "run_dir": f"D:/tmp/{run_id}",
        "goal": goal,
        "status": {
            "run_status": "running",
            "verify_result": "",
            "gate": dict(gate),
            "needs_user_decision": False,
            "decisions_needed_count": 0,
            "runtime_state": dict(runtime_state),
        },
        "runtime_state": runtime_state,
        "decisions": {"count": 0, "decisions": []},
        "whiteboard": {},
    }


class SupportProactiveRecoveryRegressionTests(unittest.TestCase):
    def test_run_proactive_support_cycle_clears_stale_bound_run_and_surfaces_recovery_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_stale_run_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "stale-run"
            state["bound_run_dir"] = "D:/tmp/stale-run"
            state["project_memory"]["project_brief"] = "我想要你继续优化我的剧情项目"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            captured: dict[str, object] = {}

            class _FakeTelegram:
                pass

            def _fake_emit(**kwargs: object) -> list[dict[str, object]]:
                captured["project_context"] = kwargs.get("project_context")
                return []

            with mock.patch.object(
                support_bot,
                "get_runs_root",
                return_value=runs_root,
            ), mock.patch.object(
                support_bot,
                "get_repo_slug",
                return_value="ctcp",
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                side_effect=RuntimeError("run_id not found: stale-run"),
            ), mock.patch.object(
                support_bot.ctcp_support_controller,
                "decide_and_queue",
                return_value=None,
            ), mock.patch.object(
                support_bot,
                "_emit_controller_outbound_jobs",
                side_effect=_fake_emit,
            ):
                support_bot.run_proactive_support_cycle(_FakeTelegram(), {123})

            updated_state = json.loads((support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(updated_state.get("bound_run_id", "")), "")
            self.assertEqual(str(updated_state.get("active_stage", "")), "RECOVER")
            self.assertIn("run_id not found", str(updated_state.get("active_blocker", "")))
            project_context = dict(captured.get("project_context", {}))
            self.assertEqual(str(dict(project_context.get("runtime_state", {})).get("phase", "")), "RECOVER")
            self.assertIn("重新绑定", str(dict(project_context.get("support_recovery", {})).get("hint", "")))

    def test_run_proactive_support_cycle_retries_missing_plan_draft_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_plan_retry_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "run-plan"
            state["bound_run_dir"] = "D:/tmp/run-plan"
            state["project_memory"]["project_brief"] = "我想要你继续优化我的剧情项目"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            blocked_context = {
                "run_id": "run-plan",
                "run_dir": "D:/tmp/run-plan",
                "goal": "我想要你继续优化我的剧情项目",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                },
                "runtime_state": {
                    "phase": "RECOVER",
                    "run_status": "running",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/PLAN_draft.md",
                        "reason": "waiting for PLAN_draft.md",
                    },
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "recovery": {
                        "needed": True,
                        "hint": "retry planner to generate PLAN_draft.md",
                        "status": "retry_ready",
                    },
                },
                "whiteboard": {},
            }
            captured: dict[str, object] = {}

            class _FakeTelegram:
                pass

            def _fake_emit(**kwargs: object) -> list[dict[str, object]]:
                captured["project_context"] = kwargs.get("project_context")
                return []

            with mock.patch.object(
                support_bot,
                "get_runs_root",
                return_value=runs_root,
            ), mock.patch.object(
                support_bot,
                "get_repo_slug",
                return_value="ctcp",
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                side_effect=[blocked_context, blocked_context],
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ) as advance_spy, mock.patch.object(
                support_bot.ctcp_support_controller,
                "decide_and_queue",
                return_value=None,
            ), mock.patch.object(
                support_bot,
                "_emit_controller_outbound_jobs",
                side_effect=_fake_emit,
            ):
                support_bot.run_proactive_support_cycle(_FakeTelegram(), {123})

            advance_spy.assert_called_once_with("run-plan", max_steps=4)
            project_context = dict(captured.get("project_context", {}))
            recovery = dict(project_context.get("support_recovery", {}))
            self.assertEqual(str(recovery.get("status", "")), "retrying")
            self.assertIn("PLAN_draft.md", str(recovery.get("hint", "")))

    def test_run_proactive_support_cycle_advances_missing_file_request_gate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_file_request_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "run-file-request"
            state["bound_run_dir"] = "D:/tmp/run-file-request"
            state["project_memory"]["project_brief"] = "做一个本地可运行的 VN 项目助手 MVP"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            blocked_context = {
                "run_id": "run-file-request",
                "run_dir": "D:/tmp/run-file-request",
                "goal": "做一个本地可运行的 VN 项目助手 MVP",
                "status": {
                    "run_status": "running",
                    "verify_result": "",
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/file_request.json",
                        "reason": "waiting for file_request.json",
                    },
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                },
                "runtime_state": {
                    "phase": "EXECUTE",
                    "run_status": "running",
                    "blocking_reason": "waiting for file_request.json",
                    "gate": {
                        "state": "blocked",
                        "owner": "Chair/Planner",
                        "path": "artifacts/file_request.json",
                        "reason": "waiting for file_request.json",
                    },
                    "needs_user_decision": False,
                    "decisions_needed_count": 0,
                    "recovery": {"needed": False, "hint": "", "status": "none"},
                },
                "whiteboard": {},
            }
            captured: dict[str, object] = {}

            class _FakeTelegram:
                pass

            def _fake_emit(**kwargs: object) -> list[dict[str, object]]:
                captured["project_context"] = kwargs.get("project_context")
                return []

            with mock.patch.object(
                support_bot,
                "get_runs_root",
                return_value=runs_root,
            ), mock.patch.object(
                support_bot,
                "get_repo_slug",
                return_value="ctcp",
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                side_effect=[blocked_context, blocked_context],
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ) as advance_spy, mock.patch.object(
                support_bot.ctcp_support_controller,
                "decide_and_queue",
                return_value=None,
            ), mock.patch.object(
                support_bot,
                "_emit_controller_outbound_jobs",
                side_effect=_fake_emit,
            ):
                support_bot.run_proactive_support_cycle(_FakeTelegram(), {123})

            advance_spy.assert_called_once_with("run-file-request", max_steps=2)
            project_context = dict(captured.get("project_context", {}))
            self.assertEqual(
                str(dict(project_context.get("runtime_state", {})).get("blocking_reason", "")),
                "waiting for file_request.json",
            )

    def test_run_proactive_support_cycle_refreshes_session_truth_after_auto_advance_without_push(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_refresh_truth_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "run-refresh"
            state["bound_run_dir"] = "D:/tmp/run-refresh"
            state["project_memory"]["project_brief"] = "做一个本地可运行的 VN 项目助手 MVP"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            blocked_plan_context = _blocked_project_context(
                run_id="run-refresh",
                goal="做一个本地可运行的 VN 项目助手 MVP",
                phase="RECOVER",
                gate_path="artifacts/PLAN_draft.md",
                gate_reason="waiting for PLAN_draft.md",
                recovery={"needed": True, "hint": "retry planner to generate PLAN_draft.md", "status": "retry_ready"},
            )
            blocked_contract_context = _blocked_project_context(
                run_id="run-refresh",
                goal="做一个本地可运行的 VN 项目助手 MVP",
                phase="EXECUTE",
                gate_path="artifacts/output_contract_freeze.json",
                gate_reason="waiting for output_contract_freeze",
            )

            class _FakeTelegram:
                pass

            with mock.patch.object(
                support_bot,
                "get_runs_root",
                return_value=runs_root,
            ), mock.patch.object(
                support_bot,
                "get_repo_slug",
                return_value="ctcp",
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                side_effect=[blocked_plan_context, blocked_contract_context],
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_advance",
                return_value={"status": "advanced"},
            ), mock.patch.object(
                support_bot.ctcp_support_controller,
                "decide_and_queue",
                return_value=None,
            ), mock.patch.object(
                support_bot,
                "_emit_controller_outbound_jobs",
                return_value=[],
            ):
                support_bot.run_proactive_support_cycle(_FakeTelegram(), {123})

            updated_state = json.loads((support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertIn("output_contract_freeze", str(updated_state.get("active_blocker", "")))
            latest = dict(updated_state.get("latest_support_context", {}))
            self.assertIn("output_contract_freeze", str(latest.get("active_blocker", "")))
            self.assertEqual(str(latest.get("conversation_mode", "")), "STATUS_QUERY")

    def test_run_proactive_support_cycle_refreshes_session_truth_for_invalid_source_generation_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_source_invalid_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "run-source-invalid"
            state["bound_run_dir"] = "D:/tmp/run-source-invalid"
            state["project_memory"]["project_brief"] = "做一个本地可运行的 VN 项目助手 MVP"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            blocked_source_context = _blocked_project_context(
                run_id="run-source-invalid",
                goal="做一个本地可运行的 VN 项目助手 MVP",
                phase="BLOCKED_HARD",
                gate_path="artifacts/source_generation_report.json",
                gate_reason="generic_validation.passed must be true",
                recovery={
                    "needed": True,
                    "hint": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                    "status": "blocked_hard",
                    "expected_artifact": "artifacts/source_generation_report.json",
                    "recovery_action": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                },
            )
            blocked_source_context["runtime_state"]["gate"]["watchdog_status"] = "blocked_hard"
            blocked_source_context["runtime_state"]["gate"]["expected_artifact"] = "artifacts/source_generation_report.json"
            blocked_source_context["runtime_state"]["gate"]["expected_exists"] = True

            class _FakeTelegram:
                pass

            with mock.patch.object(
                support_bot,
                "get_runs_root",
                return_value=runs_root,
            ), mock.patch.object(
                support_bot,
                "get_repo_slug",
                return_value="ctcp",
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                return_value=blocked_source_context,
            ), mock.patch.object(
                support_bot.ctcp_support_controller,
                "decide_and_queue",
                return_value=None,
            ), mock.patch.object(
                support_bot,
                "_emit_controller_outbound_jobs",
                return_value=[],
            ):
                support_bot.run_proactive_support_cycle(_FakeTelegram(), {123})

            updated_state = json.loads((support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertIn("generic_validation.passed must be true", str(updated_state.get("active_blocker", "")))
            self.assertIn("repair invalid generated sources", str(updated_state.get("active_next_action", "")))
            self.assertEqual(str(updated_state.get("active_stage", "")), "BLOCKED_HARD")
            latest = dict(updated_state.get("latest_support_context", {}))
            self.assertIn("generic_validation.passed must be true", str(latest.get("active_blocker", "")))
            self.assertEqual(str(latest.get("active_stage", "")), "BLOCKED_HARD")

    def test_run_proactive_support_cycle_persists_latest_truth_and_requeues_job_when_send_times_out(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_proactive_send_timeout_") as td:
            root = Path(td)
            runs_root = root / "runs"
            support_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "run-source-timeout"
            state["bound_run_dir"] = "D:/tmp/run-source-timeout"
            state["project_memory"]["project_brief"] = "做一个本地可运行的 VN 项目助手 MVP"
            state["notification_state"]["last_progress_ts"] = "2026-04-09T00:00:00Z"
            (support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            blocked_source_context = _blocked_project_context(
                run_id="run-source-timeout",
                goal="做一个本地可运行的 VN 项目助手 MVP",
                phase="BLOCKED_HARD",
                gate_path="artifacts/source_generation_report.json",
                gate_reason="generic_validation.passed must be true",
                recovery={
                    "needed": True,
                    "hint": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                    "status": "blocked_hard",
                    "expected_artifact": "artifacts/source_generation_report.json",
                    "recovery_action": "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes",
                },
            )
            blocked_source_context["runtime_state"]["gate"]["watchdog_status"] = "blocked_hard"
            blocked_source_context["runtime_state"]["gate"]["expected_artifact"] = "artifacts/source_generation_report.json"
            blocked_source_context["runtime_state"]["gate"]["expected_exists"] = True
            blocked_source_context["runtime_state"]["gate"]["recovery_action"] = "inspect generated project runtime probes, repair invalid generated sources, and regenerate source_generation_report.json until generic_validation passes"
            blocked_source_context["runtime_state"]["error"] = {
                "has_error": True,
                "code": "blocked_hard",
                "message": "generic_validation.passed must be true",
            }

            class _FakeTelegram:
                pass

            def _fake_decide_and_queue(session_state: dict[str, object], **kwargs: object) -> dict[str, object]:
                queue = session_state.setdefault("outbound_queue", {})
                queue["jobs"] = [
                    {
                        "id": "error:run-source-timeout:1",
                        "kind": "error",
                        "run_id": "run-source-timeout",
                        "status_hash": "hash-source-timeout",
                        "reason": "runtime_error",
                        "message_hash": "hash-source-timeout",
                        "decision_prompt": "",
                        "decision_prompt_hash": "",
                        "created_ts": support_bot.now_iso(),
                    }
                ]
                queue["pending_ids"] = ["error:run-source-timeout:1"]
                return {"controller_state": "ERROR_RECOVERY", "reason": "runtime_error", "jobs": list(queue["jobs"]), "status_hash": "hash-source-timeout"}

            with mock.patch.object(
                support_bot,
                "get_runs_root",
                return_value=runs_root,
            ), mock.patch.object(
                support_bot,
                "get_repo_slug",
                return_value="ctcp",
            ), mock.patch.object(
                support_bot.ctcp_front_bridge,
                "ctcp_get_support_context",
                return_value=blocked_source_context,
            ), mock.patch.object(
                support_bot.ctcp_support_controller,
                "decide_and_queue",
                side_effect=_fake_decide_and_queue,
            ), mock.patch.object(
                support_bot,
                "emit_public_message",
                side_effect=TimeoutError("telegram send timed out"),
            ):
                support_bot.run_proactive_support_cycle(_FakeTelegram(), {123})

            updated_state = json.loads((support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(str(updated_state.get("active_stage", "")), "BLOCKED_HARD")
            self.assertIn("generic_validation.passed must be true", str(updated_state.get("active_blocker", "")))
            self.assertIn("repair invalid generated sources", str(updated_state.get("active_next_action", "")))
            outbound_queue = dict(updated_state.get("outbound_queue", {}))
            jobs = outbound_queue.get("jobs", [])
            self.assertTrue(isinstance(jobs, list) and jobs)
            self.assertEqual(str(jobs[0].get("id", "")), "error:run-source-timeout:1")


if __name__ == "__main__":
    unittest.main()
