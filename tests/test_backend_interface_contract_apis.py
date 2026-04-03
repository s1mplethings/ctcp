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


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _make_fake_runtime(run_dir: Path) -> Any:
    state: dict[str, Any] = {
        "run_status": "running",
        "verify_result": "",
        "gate_state": "open",
        "gate_owner": "patchmaker",
        "gate_path": "artifacts/PLAN.md",
        "gate_reason": "working",
    }

    def _sync() -> None:
        _write_json(
            run_dir / "RUN.json",
            {
                "status": state["run_status"],
                "goal": "demo",
                "verify_iterations": 0,
                "max_iterations": 8,
                "max_iterations_source": "test",
            },
        )
        _write_json(
            run_dir / "artifacts" / "verify_report.json",
            {"result": state["verify_result"], "gate": "workflow"},
        )
        _write_json(
            run_dir / "artifacts" / "frontend_request.json",
            {"schema_version": "ctcp-frontend-request-v1", "goal": "demo", "constraints": {}, "attachments": []},
        )

    def _run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
        del cwd
        _sync()
        action = str(cmd[2]) if len(cmd) > 2 else ""
        if action == "status":
            out = "\n".join(
                [
                    f"[ctcp_orchestrate] run_dir={run_dir}",
                    f"[ctcp_orchestrate] run_status={state['run_status']}",
                    f"[ctcp_orchestrate] next={state['gate_state']}",
                    f"[ctcp_orchestrate] owner={state['gate_owner']}",
                    f"[ctcp_orchestrate] path={state['gate_path']}",
                    f"[ctcp_orchestrate] reason={state['gate_reason']}",
                ]
            )
            return {"cmd": " ".join(cmd), "exit_code": 0, "stdout": out + "\n", "stderr": ""}
        if action == "advance":
            return {"cmd": " ".join(cmd), "exit_code": 0, "stdout": "[ctcp_orchestrate] reached max-steps=1\n", "stderr": ""}
        raise AssertionError(f"unexpected action: {action}")

    _sync()
    return state, _run_cmd


class BackendInterfaceContractApiTests(unittest.TestCase):
    def test_aliases_are_exposed(self) -> None:
        names = [
            "create_run",
            "get_run_status",
            "advance_run",
            "list_pending_decisions",
            "submit_decision",
            "upload_input_artifact",
            "get_last_report",
            "get_support_context",
            "record_support_turn",
            "list_output_artifacts",
            "get_output_artifact_meta",
            "read_output_artifact",
            "get_project_manifest",
            "get_current_state_snapshot",
            "get_render_state_snapshot",
        ]
        for name in names:
            self.assertTrue(hasattr(ctcp_front_bridge, name), msg=name)

    def test_upload_includes_mime_type(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_iface_upload_") as td:
            run_dir = Path(td)
            state, fake = _make_fake_runtime(run_dir)
            del state
            src = run_dir / "tmp_upload.png"
            src.write_bytes(b"\x89PNG\r\n\x1a\n")
            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake
            ):
                row = ctcp_front_bridge.upload_input_artifact("run-x", str(src))
            self.assertIn("mime_type", row)
            self.assertTrue(str(row.get("mime_type", "")).startswith("image/"))

    def test_output_artifact_interfaces_and_snapshot_interfaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_iface_output_") as td:
            run_dir = Path(td)
            state, fake = _make_fake_runtime(run_dir)
            state["gate_reason"] = "waiting for plan"
            # output-like files
            (run_dir / "artifacts" / "analysis.md").parent.mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "analysis.md").write_text("# analysis\n", encoding="utf-8")
            (run_dir / "artifacts" / "preview.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            # input/decision files should be excluded by output interface
            (run_dir / "artifacts" / "frontend_uploads").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "frontend_uploads" / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            (run_dir / "artifacts" / "support_decisions").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "support_decisions" / "outbox_PLAN.md").write_text("x\n", encoding="utf-8")

            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake
            ):
                listing = ctcp_front_bridge.list_output_artifacts("run-x")
                self.assertTrue(int(listing.get("count", 0) or 0) >= 2)
                rels = {str(dict(row).get("rel_path", "")) for row in list(listing.get("artifacts", []))}
                self.assertIn("artifacts/analysis.md", rels)
                self.assertIn("artifacts/preview.png", rels)
                self.assertNotIn("artifacts/frontend_uploads/logo.png", rels)
                self.assertNotIn("artifacts/support_decisions/outbox_PLAN.md", rels)

                meta = ctcp_front_bridge.get_output_artifact_meta("run-x", "artifacts/analysis.md")
                self.assertEqual(str(meta.get("rel_path", "")), "artifacts/analysis.md")
                self.assertTrue(bool(str(meta.get("sha256", ""))))
                self.assertTrue(bool(str(meta.get("mime_type", ""))))

                read_text = ctcp_front_bridge.read_output_artifact("run-x", "artifacts/analysis.md")
                self.assertIn("download_path", read_text)
                self.assertIn("text", read_text)

                manifest = ctcp_front_bridge.get_project_manifest("run-x")
                self.assertIn("run_id", manifest)
                self.assertIn("project_id", manifest)
                self.assertIn("source_files", manifest)
                self.assertIn("doc_files", manifest)
                self.assertIn("workflow_files", manifest)
                self.assertIn("generated_files", manifest)
                self.assertIn("missing_files", manifest)
                self.assertIn("acceptance_files", manifest)
                self.assertIn("project_root", manifest)
                self.assertIn("startup_entrypoint", manifest)
                self.assertIn("startup_readme", manifest)
                self.assertIn("reference_project_mode", manifest)
                self.assertIn("artifacts", manifest)

                current = ctcp_front_bridge.get_current_state_snapshot("run-x")
                self.assertIn("task_id", current)
                self.assertIn("authoritative_stage", current)
                self.assertIn("visible_state", current)
                self.assertIn("current_task_goal", current)

                render = ctcp_front_bridge.get_render_state_snapshot("run-x")
                self.assertIn("task_id", render)
                self.assertIn("visible_state", render)
                self.assertIn("decision_cards", render)
                self.assertIn("progress_summary", render)

    def test_bridge_does_not_peek_outbox_or_questions_for_primary_decision_truth(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_iface_no_file_peek_") as td:
            run_dir = Path(td)
            _state, fake = _make_fake_runtime(run_dir)

            # Legacy files intentionally conflict with canonical runtime snapshot.
            (run_dir / "outbox").mkdir(parents=True, exist_ok=True)
            (run_dir / "outbox" / "legacy_decision.md").write_text(
                "Role: chair\nAction: decision\nTarget-Path: artifacts/support_decisions/legacy.md\nReason: legacy pending\n",
                encoding="utf-8",
            )
            (run_dir / "QUESTIONS.md").write_text("- legacy question should be ignored\\n", encoding="utf-8")
            _write_json(run_dir / "RUN.json", {"status": "blocked", "goal": "legacy"})
            _write_json(run_dir / "artifacts" / "verify_report.json", {"result": "PASS", "gate": "workflow"})

            _write_json(
                run_dir / "artifacts" / "support_runtime_state.json",
                {
                    "schema_version": "ctcp-support-runtime-state-v1",
                    "run_id": "run-x",
                    "run_dir": str(run_dir),
                    "phase": "EXECUTE",
                    "run_status": "running",
                    "blocking_reason": "none",
                    "needs_user_decision": False,
                    "pending_decisions": [],
                    "decisions": [],
                    "latest_result": {"verify_result": "", "verify_gate": "", "iterations": {}, "gate": {}, "status_raw": {}},
                    "error": {"has_error": False},
                    "recovery": {"needed": False, "hint": "", "status": "none"},
                    "gate": {"state": "open", "owner": "", "path": "", "reason": ""},
                    "iterations": {"current": 0, "max": 0, "source": ""},
                    "verify_result": "",
                    "verify_gate": "",
                    "decisions_needed_count": 0,
                    "open_decisions_count": 0,
                    "submitted_decisions_count": 0,
                    "core_hash": "seed",
                    "updated_at": "2026-03-31T00:00:00Z",
                    "snapshot_source": "test",
                },
            )

            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=fake
            ):
                decisions = ctcp_front_bridge.list_pending_decisions("run-x")
                status = ctcp_front_bridge.get_run_status("run-x")

            self.assertEqual(int(decisions.get("count", 0) or 0), 0)
            self.assertFalse(bool(status.get("needs_user_decision", False)))
            self.assertEqual(int(status.get("decisions_needed_count", 0) or 0), 0)


if __name__ == "__main__":
    unittest.main()
