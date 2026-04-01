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
from frontend.frontdesk_state_machine import derive_frontdesk_state


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _runtime_project_context(status: dict[str, Any]) -> dict[str, Any]:
    pending = list(status.get("pending_decisions", [])) if isinstance(status.get("pending_decisions", []), list) else []
    context: dict[str, Any] = {
        "run_id": str(status.get("run_id", "")),
        "status": status,
        "runtime_state": dict(status.get("runtime_state", {}) if isinstance(status.get("runtime_state", {}), dict) else {}),
        "decisions": {"count": int(status.get("decisions_needed_count", 0) or 0), "decisions": pending},
        "whiteboard": {},
    }
    run_status = str(status.get("run_status", "")).strip().lower()
    verify_result = str(status.get("verify_result", "")).strip().upper()
    if run_status in {"completed", "done", "pass", "success"} and verify_result == "PASS":
        context["render_snapshot"] = {
            "visible_state": "DONE",
            "ui_badge": "success",
            "progress_summary": "done",
        }
        context["artifact_manifest"] = {
            "source_files": ["src/main.py"],
            "doc_files": ["docs/overview.md"],
            "workflow_files": ["PLAN.md"],
        }
    return context


def _decision_row_by_id(rows: list[dict[str, Any]], decision_id: str) -> dict[str, Any]:
    for item in rows:
        if str(item.get("decision_id", "")) == decision_id:
            return item
    return {}


class _FakeRuntime:
    def __init__(self, run_dir: Path, *, run_id: str, goal: str = "acceptance") -> None:
        self.run_dir = run_dir
        self.state: dict[str, Any] = {
            "run_id": run_id,
            "goal": goal,
            "run_status": "running",
            "verify_result": "",
            "gate_state": "open",
            "gate_owner": "patchmaker",
            "gate_path": "artifacts/PLAN.md",
            "gate_reason": "working",
            "last_max_steps": 0,
            "decisions": [],
        }
        self.sync()

    def set(self, **kwargs: Any) -> None:
        self.state.update(kwargs)
        self._consume_submitted_decisions_if_resumed()
        self.sync()

    def _now_ts(self) -> str:
        return "2026-03-30T00:00:00Z"

    def _consume_submitted_decisions_if_resumed(self) -> None:
        run_status = str(self.state.get("run_status", "")).strip().lower()
        if run_status not in {"running", "in_progress", "working", "completed", "done", "pass", "success"}:
            return
        rows = self.state.get("decisions", [])
        if not isinstance(rows, list):
            return
        changed = False
        for item in rows:
            if not isinstance(item, dict):
                continue
            if str(item.get("status", "")).strip().lower() != "submitted":
                continue
            item["status"] = "consumed"
            item["consumed_at"] = self._now_ts()
            changed = True
        if changed:
            self.state["decisions"] = rows

    def write_outbox_decision(
        self,
        *,
        stem: str = "decision_1",
        target_path: str = "artifacts/support_decisions/decision_1.md",
        question: str = "Choose delivery format",
        reason: str = "Need your choice to continue",
    ) -> Path:
        path = self.run_dir / "outbox" / f"{stem}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(
                [
                    "Role: chair/planner",
                    "Action: decide",
                    f"Target-Path: {target_path}",
                    f"Reason: {reason}",
                    f"Question: {question}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        decision_id = f"outbox:{stem}"
        row = {
            "decision_id": decision_id,
            "kind": "outbox_md",
            "prompt_path": f"outbox/{stem}.md",
            "role": "chair/planner",
            "action": "decide",
            "target_path": target_path,
            "reason": reason,
            "question": question,
            "expected_format": "markdown",
            "schema": {"type": "string"},
            "status": "pending",
            "created_at": self._now_ts(),
            "submitted_at": "",
            "consumed_at": "",
        }
        rows = self.state.get("decisions", [])
        if not isinstance(rows, list):
            rows = []
        rows = [item for item in rows if not (isinstance(item, dict) and str(item.get("decision_id", "")) == decision_id)]
        rows.append(row)
        self.state["decisions"] = rows
        self.sync()
        return path

    def sync(self) -> None:
        _write_json(
            self.run_dir / "RUN.json",
            {
                "status": self.state["run_status"],
                "goal": self.state["goal"],
                "verify_iterations": 0,
                "max_iterations": 8,
                "max_iterations_source": "test",
            },
        )
        _write_json(
            self.run_dir / "artifacts" / "verify_report.json",
            {
                "result": self.state["verify_result"],
                "gate": "workflow",
            },
        )
        _write_json(
            self.run_dir / "artifacts" / "frontend_request.json",
            {
                "schema_version": "ctcp-frontend-request-v1",
                "goal": self.state["goal"],
                "constraints": {},
                "attachments": [],
            },
        )
        decisions = self.state.get("decisions", [])
        if not isinstance(decisions, list):
            decisions = []
        existing_runtime = _read_json(self.run_dir / "artifacts" / "support_runtime_state.json")
        if isinstance(existing_runtime, dict) and str(existing_runtime.get("schema_version", "")) == "ctcp-support-runtime-state-v1":
            existing_rows = existing_runtime.get("decisions", [])
            if isinstance(existing_rows, list):
                merged: dict[str, dict[str, Any]] = {}
                for item in decisions:
                    if not isinstance(item, dict):
                        continue
                    decision_id = str(item.get("decision_id", "")).strip()
                    if not decision_id:
                        continue
                    merged[decision_id] = dict(item)
                for item in existing_rows:
                    if not isinstance(item, dict):
                        continue
                    decision_id = str(item.get("decision_id", "")).strip()
                    if not decision_id:
                        continue
                    current = merged.get(decision_id, {})
                    current_status = str(current.get("status", "")).strip().lower()
                    existing_status = str(item.get("status", "")).strip().lower()
                    if existing_status in {"submitted", "consumed"} and current_status == "pending":
                        current["status"] = existing_status
                        current["submitted_at"] = str(item.get("submitted_at", "")).strip()
                        current["consumed_at"] = str(item.get("consumed_at", "")).strip()
                    if not current:
                        current = dict(item)
                    merged[decision_id] = current
                decisions = list(merged.values())
                self.state["decisions"] = decisions
        pending_user = [
            item for item in decisions
            if isinstance(item, dict) and str(item.get("status", "")).strip().lower() == "pending"
        ]
        open_rows = [
            item for item in decisions
            if isinstance(item, dict) and str(item.get("status", "")).strip().lower() in {"pending", "submitted"}
        ]
        submitted_rows = [
            item for item in decisions
            if isinstance(item, dict) and str(item.get("status", "")).strip().lower() == "submitted"
        ]
        run_status = str(self.state.get("run_status", "")).strip().lower()
        verify_result = str(self.state.get("verify_result", "")).strip().upper()
        gate_state = str(self.state.get("gate_state", "")).strip().lower()
        if verify_result == "PASS" and run_status in {"completed", "done", "pass", "success"} and not pending_user:
            phase = "FINALIZE"
        elif pending_user:
            phase = "WAIT_USER_DECISION"
        elif run_status in {"running", "in_progress", "working"}:
            phase = "EXECUTE"
        elif run_status in {"fail", "failed", "error", "aborted"}:
            phase = "RECOVER"
        elif gate_state in {"error", "failed"}:
            phase = "RECOVER"
        else:
            phase = "PLAN"
        has_error = bool(run_status in {"fail", "failed", "error", "aborted"} or gate_state in {"error", "failed"} or verify_result == "FAIL")
        blocking_reason = "none"
        if pending_user:
            first = pending_user[0]
            blocking_reason = str(first.get("question", "") or first.get("reason", "") or "decision_required")
        elif submitted_rows:
            blocking_reason = "decision_submitted_waiting_backend_consume"
        elif has_error:
            blocking_reason = str(self.state.get("gate_reason", "")).strip() or "runtime_error"
        _write_json(
            self.run_dir / "artifacts" / "support_runtime_state.json",
            {
                "schema_version": "ctcp-support-runtime-state-v1",
                "run_id": self.state["run_id"],
                "run_dir": str(self.run_dir),
                "phase": phase,
                "run_status": run_status,
                "blocking_reason": blocking_reason,
                "needs_user_decision": bool(len(pending_user) > 0),
                "pending_decisions": open_rows,
                "decisions": decisions,
                "latest_result": {
                    "verify_result": verify_result,
                    "verify_gate": "workflow",
                    "iterations": {"current": 0, "max": 8, "source": "test"},
                    "gate": {
                        "state": self.state["gate_state"],
                        "owner": self.state["gate_owner"],
                        "path": self.state["gate_path"],
                        "reason": self.state["gate_reason"],
                    },
                    "status_raw": {},
                },
                "error": {
                    "has_error": has_error,
                    "code": run_status if has_error else "",
                    "message": str(self.state.get("gate_reason", "")).strip() if has_error else "",
                },
                "recovery": {
                    "needed": bool(has_error or submitted_rows),
                    "hint": "run ctcp_advance after decision consumption" if submitted_rows else ("inspect verify report and failure bundle" if has_error else ""),
                    "status": "required" if (has_error or submitted_rows) else "none",
                },
                "gate": {
                    "state": self.state["gate_state"],
                    "owner": self.state["gate_owner"],
                    "path": self.state["gate_path"],
                    "reason": self.state["gate_reason"],
                },
                "iterations": {"current": 0, "max": 8, "source": "test"},
                "verify_result": verify_result,
                "verify_gate": "workflow",
                "decisions_needed_count": len(pending_user),
                "open_decisions_count": len(open_rows),
                "submitted_decisions_count": len(submitted_rows),
                "core_hash": "test-core-hash",
                "updated_at": self._now_ts(),
                "snapshot_source": "canonical_snapshot",
            },
        )

    def run_cmd(self, cmd: list[str], cwd: Path) -> dict[str, Any]:
        del cwd
        action = str(cmd[2]) if len(cmd) > 2 else ""
        if action == "status":
            self.sync()
            stdout = "\n".join(
                [
                    f"[ctcp_orchestrate] run_dir={self.run_dir}",
                    f"[ctcp_orchestrate] run_status={self.state['run_status']}",
                    f"[ctcp_orchestrate] next={self.state['gate_state']}",
                    f"[ctcp_orchestrate] owner={self.state['gate_owner']}",
                    f"[ctcp_orchestrate] path={self.state['gate_path']}",
                    f"[ctcp_orchestrate] reason={self.state['gate_reason']}",
                ]
            )
            return {"cmd": " ".join(cmd), "exit_code": 0, "stdout": stdout + "\n", "stderr": ""}
        if action == "advance":
            if "--max-steps" in cmd:
                self.state["last_max_steps"] = int(cmd[cmd.index("--max-steps") + 1])
            self.sync()
            return {
                "cmd": " ".join(cmd),
                "exit_code": 0,
                "stdout": f"[ctcp_orchestrate] reached max-steps={self.state['last_max_steps']}\n",
                "stderr": "",
            }
        raise AssertionError(f"unexpected orchestrate action: {action}")


class RuntimeStateContractAcceptanceTests(unittest.TestCase):
    def test_layer1_contract_fields_and_legacy_snapshot_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer1_contract_") as td:
            run_dir = Path(td)
            fake = _FakeRuntime(run_dir, run_id="r-layer1-contract")
            _write_json(
                run_dir / "artifacts" / "support_runtime_state.json",
                {
                    "schema_version": "legacy-v0",
                    "phase": "WAIT_USER_DECISION",
                    "needs_user_decision": True,
                    "pending_decisions": [{"decision_id": "legacy-only"}],
                    "updated_at": "2026-03-01T00:00:00Z",
                },
            )
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake.run_cmd
            ):
                status = ctcp_front_bridge.ctcp_get_status("r-layer1-contract")

            runtime = dict(status.get("runtime_state", {}))
            self.assertEqual(str(runtime.get("schema_version", "")), "ctcp-support-runtime-state-v1")
            for key in (
                "phase",
                "run_status",
                "blocking_reason",
                "needs_user_decision",
                "pending_decisions",
                "latest_result",
                "error",
                "recovery",
                "updated_at",
            ):
                self.assertIn(key, runtime)
            self.assertEqual(str(runtime.get("snapshot_source", "")), "backend_interface_snapshot")
            self.assertEqual(str(status.get("phase", "")), "EXECUTE")
            self.assertFalse(bool(status.get("needs_user_decision", False)))

    def test_layer1_decision_lifecycle_pending_submitted_consumed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer1_lifecycle_") as td:
            run_dir = Path(td)
            fake = _FakeRuntime(run_dir, run_id="r-layer1-lifecycle")
            fake.set(run_status="blocked", gate_state="blocked", gate_owner="chair", gate_reason="need decision")
            fake.write_outbox_decision(stem="format", target_path="artifacts/support_decisions/format.md")
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake.run_cmd
            ):
                first = ctcp_front_bridge.ctcp_get_status("r-layer1-lifecycle")
                self.assertTrue(bool(first.get("needs_user_decision", False)))
                decisions = ctcp_front_bridge.ctcp_list_decisions_needed("r-layer1-lifecycle")
                self.assertEqual(int(decisions.get("count", 0) or 0), 1)
                row = dict(list(decisions.get("decisions", []))[0])
                self.assertEqual(str(row.get("status", "")), "pending")
                submit = ctcp_front_bridge.ctcp_submit_decision(
                    "r-layer1-lifecycle",
                    {"decision_id": str(row.get("decision_id", "")), "content": "zip"},
                )
                self.assertEqual(str(submit.get("decision_status", "")), "submitted")
                self.assertFalse(bool(submit.get("backend_acknowledged", False)))
                after_submit = ctcp_front_bridge.ctcp_get_status("r-layer1-lifecycle")
                pending_rows = list(dict(after_submit.get("runtime_state", {})).get("pending_decisions", []))
                submitted = _decision_row_by_id([dict(item) for item in pending_rows], str(row.get("decision_id", "")))
                self.assertEqual(str(submitted.get("status", "")), "submitted")
                self.assertFalse(bool(after_submit.get("needs_user_decision", False)))
                fake.set(run_status="running", gate_state="open", gate_owner="patchmaker", gate_reason="continue")
                consumed = ctcp_front_bridge.ctcp_get_status("r-layer1-lifecycle")
                all_rows = list(dict(consumed.get("runtime_state", {})).get("decisions", []))
                consumed_row = _decision_row_by_id([dict(item) for item in all_rows], str(row.get("decision_id", "")))
                self.assertEqual(str(consumed_row.get("status", "")), "consumed")
                self.assertEqual(str(consumed.get("phase", "")), "EXECUTE")


class BridgeBehaviorAcceptanceTests(unittest.TestCase):
    def test_layer2_canonical_submitted_overrides_legacy_outbox_pending_guess(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer2_priority_") as td:
            run_dir = Path(td)
            fake = _FakeRuntime(run_dir, run_id="r-layer2-priority")
            fake.set(run_status="blocked", gate_state="blocked", gate_owner="chair", gate_reason="need choice")
            outbox_path = fake.write_outbox_decision(stem="delivery", target_path="artifacts/support_decisions/delivery.md")
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake.run_cmd
            ):
                before = ctcp_front_bridge.ctcp_list_decisions_needed("r-layer2-priority")
                self.assertEqual(int(before.get("count", 0) or 0), 1)
                row = dict(list(before.get("decisions", []))[0])
                submit = ctcp_front_bridge.ctcp_submit_decision(
                    "r-layer2-priority",
                    {"decision_id": str(row.get("decision_id", "")), "content": "send zip first"},
                )
                self.assertEqual(str(submit.get("decision_status", "")), "submitted")
                self.assertFalse(bool(submit.get("backend_acknowledged", False)))
                after_submit = ctcp_front_bridge.ctcp_get_status("r-layer2-priority")
                self.assertEqual(int(after_submit.get("decisions_needed_count", 0) or 0), 0)
                pending_rows = [dict(item) for item in list(dict(after_submit.get("runtime_state", {})).get("pending_decisions", []))]
                submitted = _decision_row_by_id(pending_rows, str(row.get("decision_id", "")))
                self.assertEqual(str(submitted.get("status", "")), "submitted")
                self.assertTrue(outbox_path.exists())
                listed = ctcp_front_bridge.ctcp_list_decisions_needed("r-layer2-priority")
                self.assertEqual(int(listed.get("count", 0) or 0), 0)
                self.assertEqual(int(listed.get("submitted_count", 0) or 0), 1)

    def test_layer2_submitted_not_consumed_until_runtime_state_advances(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer2_ack_") as td:
            run_dir = Path(td)
            fake = _FakeRuntime(run_dir, run_id="r-layer2-ack")
            fake.set(run_status="blocked", gate_state="blocked", gate_owner="chair", gate_reason="need choice")
            fake.write_outbox_decision(stem="runtime", target_path="artifacts/support_decisions/runtime.md")
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake.run_cmd
            ):
                rows = list(ctcp_front_bridge.ctcp_list_decisions_needed("r-layer2-ack").get("decisions", []))
                decision_id = str(dict(rows[0]).get("decision_id", ""))
                submit = ctcp_front_bridge.ctcp_submit_decision(
                    "r-layer2-ack",
                    {"decision_id": decision_id, "content": "option-a"},
                )
                self.assertFalse(bool(submit.get("backend_acknowledged", False)))
                stable = ctcp_front_bridge.ctcp_get_status("r-layer2-ack")
                self.assertEqual(str(stable.get("blocking_reason", "")), "decision_submitted_waiting_backend_consume")
                stable_rows = [dict(item) for item in list(dict(stable.get("runtime_state", {})).get("decisions", []))]
                self.assertEqual(str(_decision_row_by_id(stable_rows, decision_id).get("status", "")), "submitted")
                fake.set(run_status="running", gate_state="open", gate_owner="patchmaker", gate_reason="resumed")
                advanced = ctcp_front_bridge.ctcp_get_status("r-layer2-ack")
                advanced_rows = [dict(item) for item in list(dict(advanced.get("runtime_state", {})).get("decisions", []))]
                self.assertEqual(str(_decision_row_by_id(advanced_rows, decision_id).get("status", "")), "consumed")
                self.assertNotEqual(str(advanced.get("blocking_reason", "")), "decision_submitted_waiting_backend_consume")


class SupportFrontdeskMappingAcceptanceTests(unittest.TestCase):
    def test_layer3_execute_polling_stays_stable_and_does_not_repeat_progress(self) -> None:
        session_state = support_bot.default_support_session_state("accept-layer3-execute")
        session_state["bound_run_id"] = "run-layer3-execute"
        session_state["notification_state"]["last_progress_ts"] = "2026-03-30T08:00:00Z"
        context = {
            "run_id": "run-layer3-execute",
            "status": {
                "run_status": "running",
                "verify_result": "",
                "needs_user_decision": False,
                "decisions_needed_count": 0,
                "gate": {"state": "open", "owner": "patchmaker", "reason": "working"},
            },
            "runtime_state": {
                "phase": "EXECUTE",
                "run_status": "running",
                "verify_result": "",
                "needs_user_decision": False,
                "pending_decisions": [],
                "blocking_reason": "none",
                "error": {"has_error": False},
                "gate": {"state": "open", "owner": "patchmaker", "reason": "working"},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }
        binding = support_bot.build_progress_binding(project_context=context, task_summary_hint="acceptance")
        first = support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=context,
            progress_binding=binding,
            now_ts="2026-03-30T09:00:00Z",
            keepalive_interval_sec=600,
        )
        first_jobs = support_bot.ctcp_support_controller.pop_outbound_jobs(session_state)
        self.assertEqual(str(first.get("controller_state", "")), "NOTIFY_PROGRESS")
        self.assertEqual(len(first_jobs), 1)
        self.assertEqual(str(first_jobs[0].get("kind", "")), "progress")
        support_bot.ctcp_support_controller.mark_job_sent(
            session_state,
            first_jobs[0],
            now_ts="2026-03-30T09:00:00Z",
            cooldown_sec=0,
        )
        support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=context,
            progress_binding=binding,
            now_ts="2026-03-30T09:00:10Z",
            keepalive_interval_sec=600,
        )
        self.assertEqual(support_bot.ctcp_support_controller.pop_outbound_jobs(session_state), [])

        frontdesk_session = {
            "task_summary": "acceptance",
            "bound_run_id": "run-layer3-execute",
            "session_profile": {"lang_hint": "en"},
            "project_memory": {"project_brief": "acceptance"},
            "project_constraints_memory": {},
            "execution_memory": {},
            "frontdesk_state": {},
        }
        first_state = derive_frontdesk_state(
            user_text="continue work",
            conversation_mode="PROJECT_DETAIL",
            session_state=frontdesk_session,
            project_context=context,
        )
        frontdesk_session["frontdesk_state"] = dict(first_state)
        second_state = derive_frontdesk_state(
            user_text="continue work",
            conversation_mode="PROJECT_DETAIL",
            session_state=frontdesk_session,
            project_context=context,
        )
        self.assertEqual(first_state["state"], "showing_progress")
        self.assertEqual(second_state["state"], "showing_progress")
        self.assertEqual(str(second_state.get("state_reason", "")), str(first_state.get("state_reason", "")))

    def test_layer3_wait_decision_submitted_finalize_and_error_mapping(self) -> None:
        session_state = support_bot.default_support_session_state("accept-layer3-mapping")
        session_state["bound_run_id"] = "run-layer3-mapping"
        wait_context = {
            "run_id": "run-layer3-mapping",
            "status": {
                "run_status": "blocked",
                "verify_result": "",
                "needs_user_decision": True,
                "decisions_needed_count": 1,
                "gate": {"state": "blocked", "owner": "chair", "reason": "choose format"},
            },
            "runtime_state": {
                "phase": "WAIT_USER_DECISION",
                "run_status": "blocked",
                "verify_result": "",
                "needs_user_decision": True,
                "blocking_reason": "choose format",
                "pending_decisions": [{"decision_id": "d-1", "question": "zip or screenshots", "status": "pending"}],
                "error": {"has_error": False},
                "gate": {"state": "blocked", "owner": "chair", "reason": "choose format"},
            },
            "decisions": {"count": 0, "decisions": []},
            "whiteboard": {},
        }
        binding_wait = support_bot.build_progress_binding(project_context=wait_context, task_summary_hint="acceptance")
        report_wait = support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=wait_context,
            progress_binding=binding_wait,
            now_ts="2026-03-30T09:30:00Z",
            keepalive_interval_sec=0,
        )
        self.assertEqual(str(report_wait.get("controller_state", "")), "WAIT_USER_DECISION")
        self.assertEqual(str(binding_wait.get("active_stage", "")), "WAIT_USER_DECISION")
        self.assertEqual(str(binding_wait.get("question_needed", "")), "yes")

        submitted_context = dict(wait_context)
        submitted_context["runtime_state"] = {
            "phase": "EXECUTE",
            "run_status": "blocked",
            "verify_result": "",
            "needs_user_decision": False,
            "blocking_reason": "decision_submitted_waiting_backend_consume",
            "pending_decisions": [{"decision_id": "d-1", "question": "zip or screenshots", "status": "submitted"}],
            "error": {"has_error": False},
            "gate": {"state": "blocked", "owner": "chair", "reason": "waiting consume"},
        }
        submitted_context["status"] = {
            "run_status": "blocked",
            "verify_result": "",
            "needs_user_decision": False,
            "decisions_needed_count": 0,
            "gate": {"state": "blocked", "owner": "chair", "reason": "waiting consume"},
        }
        binding_submitted = support_bot.build_progress_binding(project_context=submitted_context, task_summary_hint="acceptance")
        report_submitted = support_bot.ctcp_support_controller.decide_and_queue(
            session_state,
            project_context=submitted_context,
            progress_binding=binding_submitted,
            now_ts="2026-03-30T09:31:00Z",
            keepalive_interval_sec=0,
        )
        self.assertNotEqual(str(report_submitted.get("controller_state", "")), "WAIT_USER_DECISION")
        self.assertIn("后端消费确认", str(binding_submitted.get("current_blocker", "")))

        frontdesk_session = {
            "task_summary": "acceptance",
            "bound_run_id": "run-layer3-mapping",
            "session_profile": {"lang_hint": "en"},
            "project_memory": {"project_brief": "acceptance"},
            "project_constraints_memory": {},
            "execution_memory": {},
            "frontdesk_state": {},
        }
        wait_state = derive_frontdesk_state(
            user_text="continue work",
            conversation_mode="PROJECT_DETAIL",
            session_state=frontdesk_session,
            project_context=wait_context,
        )
        self.assertEqual(wait_state["state"], "showing_decision")
        submitted_state = derive_frontdesk_state(
            user_text="continue work",
            conversation_mode="PROJECT_DETAIL",
            session_state=frontdesk_session,
            project_context=submitted_context,
        )
        self.assertEqual(submitted_state["state"], "showing_progress")

        done_context = dict(submitted_context)
        done_context["runtime_state"] = {
            "phase": "FINALIZE",
            "run_status": "completed",
            "verify_result": "PASS",
            "needs_user_decision": False,
            "blocking_reason": "none",
            "pending_decisions": [],
            "error": {"has_error": False},
            "gate": {"state": "closed", "owner": "", "reason": ""},
        }
        done_context["status"] = {
            "run_status": "completed",
            "verify_result": "PASS",
            "needs_user_decision": False,
            "decisions_needed_count": 0,
            "gate": {"state": "closed", "owner": "", "reason": ""},
        }
        done_context["render_snapshot"] = {
            "visible_state": "DONE",
            "ui_badge": "success",
            "progress_summary": "done",
        }
        done_context["artifact_manifest"] = {
            "source_files": ["src/main.py"],
            "doc_files": ["docs/overview.md"],
            "workflow_files": ["PLAN.md"],
        }
        done_state = derive_frontdesk_state(
            user_text="continue work",
            conversation_mode="PROJECT_DETAIL",
            session_state=frontdesk_session,
            project_context=done_context,
        )
        self.assertEqual(done_state["state"], "showing_result")

        error_context = dict(done_context)
        error_context["runtime_state"] = {
            "phase": "RECOVER",
            "run_status": "fail",
            "verify_result": "FAIL",
            "needs_user_decision": False,
            "blocking_reason": "verify failed",
            "pending_decisions": [],
            "error": {"has_error": True, "message": "verify failed"},
            "gate": {"state": "error", "owner": "verify", "reason": "verify failed"},
        }
        error_context["status"] = {
            "run_status": "fail",
            "verify_result": "FAIL",
            "needs_user_decision": False,
            "decisions_needed_count": 0,
            "gate": {"state": "error", "owner": "verify", "reason": "verify failed"},
        }
        error_state = derive_frontdesk_state(
            user_text="continue work",
            conversation_mode="PROJECT_DETAIL",
            session_state=frontdesk_session,
            project_context=error_context,
        )
        self.assertEqual(error_state["state"], "showing_error")


class EndToEndReplayAcceptanceTests(unittest.TestCase):
    def test_layer4_replay_execute_to_done(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer4_done_") as td:
            run_dir = Path(td)
            fake = _FakeRuntime(run_dir, run_id="r-layer4-done")
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake.run_cmd
            ):
                running = ctcp_front_bridge.ctcp_get_status("r-layer4-done")
                self.assertEqual(str(running.get("phase", "")), "EXECUTE")
                self.assertEqual(int(running.get("decisions_needed_count", 0) or 0), 0)
                fake.set(run_status="completed", verify_result="PASS", gate_state="closed", gate_owner="", gate_reason="done")
                done = ctcp_front_bridge.ctcp_get_status("r-layer4-done")
                self.assertEqual(str(done.get("phase", "")), "FINALIZE")
                self.assertEqual(int(done.get("decisions_needed_count", 0) or 0), 0)
                context = _runtime_project_context(done)
                session = {
                    "task_summary": "acceptance",
                    "bound_run_id": str(done.get("run_id", "")),
                    "session_profile": {"lang_hint": "en"},
                    "project_memory": {"project_brief": "acceptance"},
                    "project_constraints_memory": {},
                    "execution_memory": {},
                    "frontdesk_state": {},
                }
                frontdesk = derive_frontdesk_state(
                    user_text="continue work",
                    conversation_mode="STATUS_QUERY",
                    session_state=session,
                    project_context=context,
                )
                self.assertEqual(frontdesk["state"], "showing_result")

    def test_layer4_replay_decision_mid_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer4_decision_") as td:
            run_dir = Path(td)
            fake = _FakeRuntime(run_dir, run_id="r-layer4-decision")
            fake.set(run_status="blocked", gate_state="blocked", gate_owner="chair", gate_reason="need decision")
            fake.write_outbox_decision(stem="midway", target_path="artifacts/support_decisions/midway.md")
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake.run_cmd
            ):
                blocked = ctcp_front_bridge.ctcp_get_status("r-layer4-decision")
                self.assertTrue(bool(blocked.get("needs_user_decision", False)))
                session_state = support_bot.default_support_session_state("accept-layer4-decision")
                session_state["bound_run_id"] = str(blocked.get("run_id", ""))
                report = support_bot.ctcp_support_controller.decide_and_queue(
                    session_state,
                    project_context=_runtime_project_context(blocked),
                    progress_binding=support_bot.build_progress_binding(
                        project_context=_runtime_project_context(blocked), task_summary_hint="acceptance"
                    ),
                    now_ts="2026-03-30T10:00:00Z",
                    keepalive_interval_sec=0,
                )
                self.assertEqual(str(report.get("controller_state", "")), "WAIT_USER_DECISION")
                decision_row = dict(list(ctcp_front_bridge.ctcp_list_decisions_needed("r-layer4-decision").get("decisions", []))[0])
                submit = ctcp_front_bridge.ctcp_submit_decision(
                    "r-layer4-decision",
                    {"decision_id": str(decision_row.get("decision_id", "")), "content": "zip first"},
                )
                self.assertFalse(bool(submit.get("backend_acknowledged", False)))
                submitted = ctcp_front_bridge.ctcp_get_status("r-layer4-decision")
                self.assertFalse(bool(submitted.get("needs_user_decision", False)))
                fake.set(run_status="running", gate_state="open", gate_owner="patchmaker", gate_reason="continuing")
                resumed = ctcp_front_bridge.ctcp_get_status("r-layer4-decision")
                rows = [dict(item) for item in list(dict(resumed.get("runtime_state", {})).get("decisions", []))]
                self.assertEqual(
                    str(_decision_row_by_id(rows, str(decision_row.get("decision_id", ""))).get("status", "")),
                    "consumed",
                )

    def test_layer4_replay_old_residue_does_not_pollute_next_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer4_residue_") as td:
            root = Path(td)
            run_a = root / "r-a"
            run_b = root / "r-b"
            runtime_a = _FakeRuntime(run_a, run_id="r-a")
            runtime_b = _FakeRuntime(run_b, run_id="r-b")
            runtime_a.set(run_status="blocked", gate_state="blocked", gate_owner="chair", gate_reason="need decision")
            runtime_a.write_outbox_decision(stem="old", target_path="artifacts/support_decisions/old.md")

            def _resolve(run_id: str) -> Path:
                if run_id == "r-a":
                    return run_a
                if run_id == "r-b":
                    return run_b
                raise AssertionError(f"unexpected run_id {run_id}")

            def _run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
                if str(run_a) in [str(item) for item in cmd]:
                    return runtime_a.run_cmd(cmd, cwd)
                if str(run_b) in [str(item) for item in cmd]:
                    return runtime_b.run_cmd(cmd, cwd)
                raise AssertionError(f"unexpected cmd: {cmd}")

            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", side_effect=_resolve), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=_run_cmd
            ):
                status_a = ctcp_front_bridge.ctcp_get_status("r-a")
                status_b = ctcp_front_bridge.ctcp_get_status("r-b")
                self.assertEqual(int(status_a.get("decisions_needed_count", 0) or 0), 1)
                self.assertEqual(int(status_b.get("decisions_needed_count", 0) or 0), 0)
                self.assertEqual(len(list(status_b.get("pending_decisions", []))), 0)

    def test_layer4_replay_failure_recover_then_execute(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_accept_layer4_recover_") as td:
            run_dir = Path(td)
            fake = _FakeRuntime(run_dir, run_id="r-layer4-recover")
            fake.set(run_status="fail", verify_result="FAIL", gate_state="error", gate_owner="verify", gate_reason="verify failed")
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake.run_cmd
            ):
                failed = ctcp_front_bridge.ctcp_get_status("r-layer4-recover")
                self.assertEqual(str(failed.get("phase", "")), "RECOVER")
                self.assertTrue(bool(dict(failed.get("error", {})).get("has_error", False)))
                fail_context = _runtime_project_context(failed)
                session = {
                    "task_summary": "acceptance",
                    "bound_run_id": str(failed.get("run_id", "")),
                    "session_profile": {"lang_hint": "en"},
                    "project_memory": {"project_brief": "acceptance"},
                    "project_constraints_memory": {},
                    "execution_memory": {},
                    "frontdesk_state": {},
                }
                fail_frontdesk = derive_frontdesk_state(
                    user_text="continue work",
                    conversation_mode="STATUS_QUERY",
                    session_state=session,
                    project_context=fail_context,
                )
                self.assertEqual(fail_frontdesk["state"], "showing_error")
                fake.set(run_status="running", verify_result="", gate_state="open", gate_owner="patchmaker", gate_reason="recovered")
                recovered = ctcp_front_bridge.ctcp_get_status("r-layer4-recover")
                self.assertEqual(str(recovered.get("phase", "")), "EXECUTE")
                self.assertEqual(int(recovered.get("decisions_needed_count", 0) or 0), 0)
                recover_frontdesk = derive_frontdesk_state(
                    user_text="continue work",
                    conversation_mode="PROJECT_DETAIL",
                    session_state=session,
                    project_context=_runtime_project_context(recovered),
                )
                self.assertEqual(recover_frontdesk["state"], "showing_progress")


if __name__ == "__main__":
    unittest.main()
