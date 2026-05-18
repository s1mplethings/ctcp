from __future__ import annotations

import json
import subprocess
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

import scripts.ctcp_orchestrate as orchestrate


FIXTURES = ROOT / "tests" / "agent_factory_benchmark" / "fixtures"
HOLDOUT_FIXTURES = ROOT / "tests" / "agent_factory_benchmark" / "holdout_fixtures"


class AgentProjectOrchestratorE2ETests(unittest.TestCase):
    def _run_agent_project(self, input_path: Path) -> tuple[Path, dict[str, object], tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_project_orch_")
        out = Path(td.name) / "agent_project"
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                "agent-project",
                "--input",
                str(input_path),
                "--output-dir",
                str(out),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        report = json.loads((out / "pipeline_report.json").read_text(encoding="utf-8"))
        return out, report, td

    def _manifest_text(self, out: Path) -> str:
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        surface = {
            "agents": [
                {key: agent.get(key) for key in ("name", "role", "goal", "scope", "tools")}
                for agent in manifest.get("agents", [])
                if isinstance(agent, dict)
            ],
            "tools": [
                {key: tool.get(key) for key in ("tool_name", "description", "side_effect_level", "requires_approval")}
                for tool in manifest.get("tools", [])
                if isinstance(tool, dict)
            ],
            "workflows": [
                {key: state.get(key) for key in ("state_name", "tools_called", "responsible_agent")}
                for state in manifest.get("workflows", [])
                if isinstance(state, dict)
            ],
        }
        return json.dumps(surface, ensure_ascii=False).lower().replace("-", "_").replace(" ", "_")

    def test_agent_project_subcommand_runs_end_to_end(self) -> None:
        out, report, td = self._run_agent_project(FIXTURES / "input_devops_incident.json")
        self.addCleanup(td.cleanup)
        self.assertEqual(report["status"], "passed")
        self.assertTrue((out / "manifest.json").exists())
        self.assertTrue((out / "scaffold" / "run_agent.py").exists())
        self.assertTrue((out / "scaffold" / "runtime_state.json").exists())
        self.assertTrue((out / "scaffold" / "audit" / "events.jsonl").exists())

    def test_permission_attack_through_agent_project_keeps_approval(self) -> None:
        out, _report, td = self._run_agent_project(FIXTURES / "input_permission_attack.json")
        self.addCleanup(td.cleanup)
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        approvals = set(manifest["permissions"]["approval_required_for"])
        self.assertIn("rollback", approvals)
        self.assertIn("refund", approvals)
        self.assertTrue(manifest["permissions"]["audit_log_required"])

    def test_h9_agent_project_does_not_trigger_billing_refund(self) -> None:
        out, _report, td = self._run_agent_project(HOLDOUT_FIXTURES / "input_h9_battery_charging_station.json")
        self.addCleanup(td.cleanup)
        text = self._manifest_text(out)
        self.assertNotIn("billing", text)
        self.assertNotIn("refund", text)
        self.assertNotIn("payment", text)
        self.assertIn("device_status", text)

    def test_h10_agent_project_does_not_trigger_rollback_incident(self) -> None:
        out, _report, td = self._run_agent_project(HOLDOUT_FIXTURES / "input_h10_product_launch_coordination.json")
        self.addCleanup(td.cleanup)
        text = self._manifest_text(out)
        self.assertNotIn("rollback", text)
        self.assertNotIn("incident_response", text)
        self.assertIn("launch_coordination", text)

    def test_existing_output_dir_is_not_silently_overwritten_and_force_allows_rebuild(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_project_existing_orch_") as td:
            out = Path(td) / "agent_project"
            out.mkdir()
            (out / "important.txt").write_text("do not overwrite", encoding="utf-8")
            base_cmd = [
                sys.executable,
                str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                "agent-project",
                "--input",
                str(FIXTURES / "input_devops_incident.json"),
                "--output-dir",
                str(out),
            ]
            blocked = subprocess.run(base_cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(blocked.returncode, 2)
            self.assertIn("output directory is not empty", blocked.stderr)
            forced = subprocess.run(base_cmd + ["--force"], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(forced.returncode, 0, forced.stderr or forced.stdout)
            self.assertFalse((out / "important.txt").exists())

    def test_invalid_input_has_clear_error_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_project_bad_orch_") as td:
            root = Path(td)
            bad = root / "bad.json"
            out = root / "agent_project"
            bad.write_text("{not-json", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                    "agent-project",
                    "--input",
                    str(bad),
                    "--output-dir",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            report = json.loads((out / "pipeline_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["failed_step"], "manifest_generation")

    def test_agent_manifest_subcommand_still_available(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_project_manifest_still_") as td:
            root = Path(td)
            input_path = root / "input.json"
            output_path = root / "manifest.json"
            input_path.write_text(json.dumps({"goal": "Create a product feedback agent"}), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                    "agent-manifest",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertTrue(output_path.exists())

    def test_missing_mode_does_not_trigger_agent_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_project_missing_mode_") as td:
            root = Path(td)
            input_path = root / "input.json"
            out = root / "agent_project"
            input_path.write_text(json.dumps({"goal": "Create a DevOps incident agent"}), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "--input", str(input_path), "--output-dir", str(out)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertFalse(out.exists())

    def test_normal_new_run_dispatch_is_not_agent_project_mode(self) -> None:
        with mock.patch.object(orchestrate, "cmd_new_run", return_value=0) as new_run:
            with mock.patch.object(sys, "argv", ["ctcp_orchestrate.py", "new-run", "--goal", "build a todo app"]):
                self.assertEqual(orchestrate.main(), 0)
        new_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
