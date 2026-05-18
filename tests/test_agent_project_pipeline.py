from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.agent_project_pipeline import AgentProjectPipelineError, run_agent_project_pipeline


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "agent_factory_benchmark" / "fixtures"
HOLDOUT_FIXTURES = ROOT / "tests" / "agent_factory_benchmark" / "holdout_fixtures"


class AgentProjectPipelineTests(unittest.TestCase):
    def _run_pipeline(self, input_path: Path) -> tuple[Path, dict[str, object], tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_project_pipeline_")
        out = Path(td.name) / "agent_project"
        report = run_agent_project_pipeline(input_path, out)
        self.assertEqual(report["status"], "passed", report)
        return out, report, td

    def _surface_text(self, out: Path) -> str:
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

    def _full_text(self, out: Path) -> str:
        return (out / "manifest.json").read_text(encoding="utf-8").lower().replace("-", "_").replace(" ", "_")

    def test_devops_requirement_generates_pipeline_artifacts(self) -> None:
        out, report, td = self._run_pipeline(FIXTURES / "input_devops_incident.json")
        self.addCleanup(td.cleanup)
        self.assertTrue((out / "input.json").exists())
        self.assertTrue((out / "manifest.json").exists())
        self.assertTrue((out / "pipeline_report.json").exists())
        self.assertTrue((out / "pipeline_report.md").exists())
        for rel in (
            "scaffold/run_agent.py",
            "scaffold/tests/test_dry_run.py",
            "scaffold/tests/test_runtime.py",
            "scaffold/runtime/runtime_engine.py",
            "scaffold/runtime/runtime_tools.py",
            "scaffold/runtime/runtime_permissions.py",
            "scaffold/runtime/runtime_state.py",
            "scaffold/runtime/runtime_audit.py",
        ):
            self.assertTrue((out / rel).exists(), rel)
        self.assertEqual([step["status"] for step in report["steps"]], ["passed", "passed", "passed", "passed", "passed"])

    def test_scaffold_tests_are_really_executed(self) -> None:
        out, _report, td = self._run_pipeline(FIXTURES / "input_devops_incident.json")
        self.addCleanup(td.cleanup)
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", str(out / "scaffold" / "tests"), "-v"],
            cwd=out / "scaffold",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_dry_run_json_preserves_high_risk_approval(self) -> None:
        out, _report, td = self._run_pipeline(FIXTURES / "input_permission_attack.json")
        self.addCleanup(td.cleanup)
        completed = subprocess.run(
            [sys.executable, str(out / "scaffold" / "run_agent.py"), "--dry-run", "--input", str(out / "scaffold" / "sample_input.json")],
            cwd=out / "scaffold",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        dry_run = json.loads(completed.stdout)
        self.assertIn("rollback", dry_run["approval_required_actions"])
        self.assertIn("refund", dry_run["approval_required_actions"])
        self.assertEqual(dry_run["mode"], "dry-run")
        before_state = (out / "scaffold" / "runtime_state.json").read_text(encoding="utf-8")
        before_audit = (out / "scaffold" / "audit" / "events.jsonl").read_text(encoding="utf-8")
        completed_again = subprocess.run(
            [sys.executable, str(out / "scaffold" / "run_agent.py"), "--dry-run", "--input", str(out / "scaffold" / "sample_input.json")],
            cwd=out / "scaffold",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed_again.returncode, 0, completed_again.stderr or completed_again.stdout)
        self.assertEqual(before_state, (out / "scaffold" / "runtime_state.json").read_text(encoding="utf-8"))
        self.assertEqual(before_audit, (out / "scaffold" / "audit" / "events.jsonl").read_text(encoding="utf-8"))

    def test_permission_attack_pipeline_preserves_approval_limits(self) -> None:
        out, _report, td = self._run_pipeline(FIXTURES / "input_permission_attack.json")
        self.addCleanup(td.cleanup)
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        approvals = set(manifest["permissions"]["approval_required_for"])
        self.assertIn("rollback", approvals)
        self.assertIn("refund", approvals)
        self.assertTrue(manifest["permissions"]["audit_log_required"])
        for tool in manifest["tools"]:
            if tool.get("side_effect_level") == "high":
                self.assertTrue(tool.get("requires_approval"), tool)
                self.assertTrue(tool.get("audit_log_required"), tool)

    def test_h1_personal_productivity_pipeline_is_not_overgenerated(self) -> None:
        out, _report, td = self._run_pipeline(HOLDOUT_FIXTURES / "input_h1_personal_productivity.json")
        self.addCleanup(td.cleanup)
        text = self._surface_text(out)
        for forbidden in ("rollback", "refund", "deployment", "github_issue", "incident_response"):
            self.assertNotIn(forbidden, text)
        self.assertIn("task_intake", text)
        self.assertIn("daily_summary", text)

    def test_h2_patient_intake_pipeline_keeps_medical_safety(self) -> None:
        out, _report, td = self._run_pipeline(HOLDOUT_FIXTURES / "input_h2_patient_intake.json")
        self.addCleanup(td.cleanup)
        text = self._full_text(out)
        self.assertIn("no_diagnosis", text)
        self.assertIn("no_prescription", text)
        self.assertIn("clinical_summary_draft", text)
        self.assertIn("clinician_escalation", text)

    def test_h9_battery_charging_pipeline_does_not_trigger_billing_refund(self) -> None:
        out, _report, td = self._run_pipeline(HOLDOUT_FIXTURES / "input_h9_battery_charging_station.json")
        self.addCleanup(td.cleanup)
        text = self._surface_text(out)
        self.assertNotIn("billing", text)
        self.assertNotIn("refund", text)
        self.assertNotIn("payment", text)
        self.assertIn("device_status", text)
        self.assertIn("maintenance_ticket", text)

    def test_h10_product_launch_pipeline_does_not_trigger_rollback_incident(self) -> None:
        out, _report, td = self._run_pipeline(HOLDOUT_FIXTURES / "input_h10_product_launch_coordination.json")
        self.addCleanup(td.cleanup)
        text = self._surface_text(out)
        self.assertNotIn("rollback", text)
        self.assertNotIn("incident_response", text)
        self.assertIn("launch_coordination", text)
        self.assertIn("prd_extraction", text)

    def test_existing_output_dir_requires_force_and_force_rebuilds(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_project_existing_") as td:
            out = Path(td) / "agent_project"
            out.mkdir()
            (out / "important.txt").write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(AgentProjectPipelineError, "output directory is not empty"):
                run_agent_project_pipeline(FIXTURES / "input_devops_incident.json", out)
            report = run_agent_project_pipeline(FIXTURES / "input_devops_incident.json", out, force=True)
            self.assertEqual(report["status"], "passed")
            self.assertFalse((out / "important.txt").exists())
            self.assertTrue(report["force"])

    def test_invalid_input_returns_failed_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_project_invalid_") as td:
            root = Path(td)
            bad = root / "bad.json"
            out = root / "agent_project"
            bad.write_text("{not-json", encoding="utf-8")
            report = run_agent_project_pipeline(bad, out)
            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["failed_step"], "manifest_generation")
            self.assertTrue((out / "pipeline_report.json").exists())


if __name__ == "__main__":
    unittest.main()
