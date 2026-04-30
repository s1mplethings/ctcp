from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_front_bridge  # noqa: E402
import ctcp_librarian  # noqa: E402
import ctcp_orchestrate  # noqa: E402


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class MainlineRunContractTests(unittest.TestCase):
    def test_same_run_manifest_records_librarian_adlc_whiteboard_and_bridge(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_mainline_run_") as td:
            run_dir = Path(td).resolve()
            artifacts = run_dir / "artifacts"
            run_id = run_dir.name

            _write_json(
                run_dir / "RUN.json",
                {
                    "schema_version": "ctcp-run-v1",
                    "run_id": run_id,
                    "goal": "prove unified mainline run manifest",
                    "status": "running",
                    "verify_iterations": 0,
                    "max_iterations": 3,
                },
            )
            _write_text(
                artifacts / "guardrails.md",
                "find_mode: resolver_only\nmax_files: 8\nmax_total_bytes: 50000\nmax_iterations: 1\n",
            )
            _write_text(artifacts / "analysis.md", "# Analysis\n")
            _write_json(
                artifacts / "find_result.json",
                {"schema_version": "ctcp-find-result-v1", "selected_workflow_id": "wf_project_generation_manifest"},
            )
            _write_json(
                artifacts / "file_request.json",
                {
                    "schema_version": "ctcp-file-request-v1",
                    "goal": "prove mainline context",
                    "needs": [{"path": "docs/02_workflow.md", "mode": "snippets", "line_ranges": [[1, 80]]}],
                    "budget": {"max_files": 8, "max_total_bytes": 80000},
                    "reason": "mainline run manifest integration test",
                },
            )

            with mock.patch.object(sys, "argv", ["ctcp_librarian.py", "--run-dir", str(run_dir)]):
                self.assertEqual(ctcp_librarian.main(), 0)

            status = ctcp_front_bridge.ctcp_get_status(str(run_dir))
            self.assertEqual(status["run_id"], run_id)

            turn = ctcp_front_bridge.ctcp_record_support_turn(
                str(run_dir),
                text="请确认这次运行已经经过 librarian、ADLC、白板和 bridge。",
                source="test_frontend",
                conversation_mode="STATUS_QUERY",
            )
            self.assertEqual(turn["run_id"], run_id)

            run_doc = json.loads((run_dir / "RUN.json").read_text(encoding="utf-8"))
            run_doc["status"] = "fail"
            run_doc["blocked_reason"] = "simulated_gate_failure"
            _write_json(run_dir / "RUN.json", run_doc)
            self.assertEqual(ctcp_orchestrate.cmd_status(run_dir), 0)

            manifest_path = artifacts / "run_manifest.json"
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(manifest["run_id"], run_id)
            self.assertTrue(manifest["context_pack_present"])
            self.assertEqual(manifest["context_pack_path"], "artifacts/context_pack.json")
            self.assertTrue(str(manifest.get("adlc_phase", "")).strip())
            self.assertTrue(str(manifest.get("adlc_gate_status", "")).strip())
            self.assertTrue(manifest["whiteboard_present"])
            self.assertEqual(manifest["whiteboard_path"], "artifacts/support_whiteboard.json")
            self.assertTrue(manifest["bridge_present"])
            self.assertTrue(manifest["bridge_output_present"])
            self.assertIn("status", manifest["bridge_output_refs"])
            self.assertIn("artifacts/support_frontend_turns.jsonl", manifest["bridge_output_refs"])
            self.assertEqual(manifest["final_status"], "fail")
            self.assertTrue(str(manifest.get("first_failure_gate", "")).strip())
            self.assertIn("project-generation run failed", str(manifest.get("first_failure_reason", "")))

            responsibility_path = artifacts / "run_responsibility_manifest.json"
            self.assertTrue(responsibility_path.exists())
            responsibility = json.loads(responsibility_path.read_text(encoding="utf-8"))
            self.assertEqual(responsibility["run_id"], run_id)
            self.assertEqual(responsibility["chosen_entry"], "scripts/ctcp_orchestrate.py")
            self.assertEqual(responsibility["chosen_workflow"], "wf_project_generation_manifest")
            self.assertIn("core_feature", responsibility.get("stage_owners", {}))
            self.assertIn("internal_runtime_status", responsibility)
            self.assertIn("user_acceptance_status", responsibility)
            self.assertIn("first_failure_point", responsibility)
            self.assertIn("final_verdict", responsibility)


if __name__ == "__main__":
    unittest.main()
