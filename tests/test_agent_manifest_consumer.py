from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.agent_manifest_consumer import ManifestConsumerError, generate_agent_scaffold, validate_manifest


ROOT = Path(__file__).resolve().parents[1]
DEVOPS_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_devops_incident.json"
PERMISSION_ATTACK_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_permission_attack.json"
H9_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "holdout_generated" / "output_h9_battery_charging_station.json"
H10_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "holdout_generated" / "output_h10_product_launch_coordination.json"


class AgentManifestConsumerTests(unittest.TestCase):
    def _generate(self, manifest_path: Path) -> tuple[Path, dict[str, object], tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_scaffold_")
        out = Path(td.name) / "agent_project"
        result = generate_agent_scaffold(manifest_path, out)
        return out, result, td

    def _dry_run(self, scaffold: Path) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, "run_agent.py", "--dry-run", "--input", "sample_input.json"],
            cwd=scaffold,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def _tool_workflow_text(self, scaffold: Path) -> str:
        parts = []
        for rel in ("tools", "workflows"):
            path = scaffold / rel
            if path.is_dir():
                for child in sorted(path.glob("*.json")):
                    parts.append(child.read_text(encoding="utf-8"))
            else:
                parts.append(path.read_text(encoding="utf-8"))
        return "\n".join(parts).lower().replace("-", "_").replace(" ", "_")

    def test_devops_manifest_generates_scaffold_structure(self) -> None:
        scaffold, result, td = self._generate(DEVOPS_MANIFEST)
        self.addCleanup(td.cleanup)
        self.assertEqual(result["mode"], "agent-scaffold")
        for rel in (
            "manifest.json",
            "README.md",
            "agents",
            "tools",
            "workflows/workflow.json",
            "memory/memory_schema.json",
            "permissions/permissions.json",
            "guardrails/guardrails.json",
            "tests/test_manifest_contract.py",
            "tests/test_permissions.py",
            "tests/test_workflows.py",
            "tests/test_dry_run.py",
            "run_agent.py",
        ):
            self.assertTrue((scaffold / rel).exists(), rel)
        self.assertGreater(len(list((scaffold / "agents").glob("*.json"))), 0)
        self.assertGreater(len(list((scaffold / "tools").glob("*.json"))), 0)

    def test_generated_scaffold_tests_run(self) -> None:
        scaffold, _result, td = self._generate(DEVOPS_MANIFEST)
        self.addCleanup(td.cleanup)
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "tests", "-v"],
            cwd=scaffold,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_run_agent_dry_run_outputs_audit_and_pending_approvals(self) -> None:
        scaffold, _result, td = self._generate(DEVOPS_MANIFEST)
        self.addCleanup(td.cleanup)
        output = self._dry_run(scaffold)
        self.assertEqual(output["mode"], "dry_run")
        self.assertEqual(output["status"], "ok")
        self.assertIn("rollback", output["approval_required_actions"])
        self.assertEqual(output["audit_log_path"], "audit/dry_run_audit.jsonl")
        self.assertTrue((scaffold / "audit" / "dry_run_audit.jsonl").exists())
        self.assertIn("audit_event", output)

    def test_permission_attack_scaffold_preserves_approval_limits(self) -> None:
        scaffold, _result, td = self._generate(PERMISSION_ATTACK_MANIFEST)
        self.addCleanup(td.cleanup)
        permissions = json.loads((scaffold / "permissions" / "permissions.json").read_text(encoding="utf-8"))
        self.assertIn("rollback", permissions["approval_required_for"])
        self.assertIn("refund", permissions["approval_required_for"])
        self.assertTrue(permissions["audit_log_required"])
        output = self._dry_run(scaffold)
        self.assertIn("rollback", output["approval_required_actions"])
        self.assertIn("refund", output["approval_required_actions"])

    def test_h9_battery_charging_scaffold_does_not_contain_billing_or_refund_tools(self) -> None:
        scaffold, _result, td = self._generate(H9_MANIFEST)
        self.addCleanup(td.cleanup)
        text = self._tool_workflow_text(scaffold)
        self.assertNotIn("billing", text)
        self.assertNotIn("refund", text)
        self.assertNotIn("payment", text)
        self.assertIn("device_status", text)
        self.assertIn("maintenance_ticket", text)

    def test_h10_product_launch_scaffold_does_not_contain_rollback_or_incident_tools(self) -> None:
        scaffold, _result, td = self._generate(H10_MANIFEST)
        self.addCleanup(td.cleanup)
        text = self._tool_workflow_text(scaffold)
        self.assertNotIn("rollback", text)
        self.assertNotIn("incident_response", text)
        self.assertIn("launch_coordination", text)
        self.assertIn("prd_extraction", text)

    def test_missing_required_manifest_fields_fail_clearly(self) -> None:
        bad = {"manifest_version": "1.0", "agents": []}
        with self.assertRaisesRegex(ManifestConsumerError, "manifest missing required fields"):
            validate_manifest(bad)

    def test_high_side_effect_tools_are_not_available_in_dry_run(self) -> None:
        scaffold, _result, td = self._generate(PERMISSION_ATTACK_MANIFEST)
        self.addCleanup(td.cleanup)
        manifest = json.loads((scaffold / "manifest.json").read_text(encoding="utf-8"))
        high_tools = {tool["tool_name"] for tool in manifest["tools"] if tool.get("side_effect_level") == "high"}
        output = self._dry_run(scaffold)
        self.assertTrue(high_tools)
        self.assertTrue(high_tools.issubset(set(output["pending_approval_tools"])))
        self.assertTrue(high_tools.isdisjoint(set(output["tools_available"])))

    def test_existing_output_dir_requires_force_and_sentinel(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_scaffold_existing_") as td:
            out = Path(td) / "agent_project"
            out.mkdir()
            (out / "important.txt").write_text("do not overwrite", encoding="utf-8")
            with self.assertRaisesRegex(ManifestConsumerError, "output directory is not empty"):
                generate_agent_scaffold(DEVOPS_MANIFEST, out)
            with self.assertRaisesRegex(ManifestConsumerError, "refusing to overwrite non-scaffold"):
                generate_agent_scaffold(DEVOPS_MANIFEST, out, force=True)

    def test_force_replaces_existing_scaffold_only(self) -> None:
        scaffold, _result, td = self._generate(DEVOPS_MANIFEST)
        self.addCleanup(td.cleanup)
        (scaffold / "old.txt").write_text("replace", encoding="utf-8")
        result = generate_agent_scaffold(DEVOPS_MANIFEST, scaffold, force=True)
        self.assertEqual(result["status"], "pass")
        self.assertFalse((scaffold / "old.txt").exists())


if __name__ == "__main__":
    unittest.main()
