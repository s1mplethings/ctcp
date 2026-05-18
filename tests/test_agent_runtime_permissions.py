from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.agent_manifest_consumer import generate_agent_scaffold


ROOT = Path(__file__).resolve().parents[1]
PERMISSION_ATTACK_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_permission_attack.json"
H2_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "holdout_generated" / "output_h2_patient_intake.json"
DEVOPS_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_devops_incident.json"


class AgentRuntimePermissionTests(unittest.TestCase):
    def _scaffold(self, manifest_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_runtime_perm_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(manifest_path, out)
        return out, td

    def _write_input(self, scaffold: Path, text: str) -> Path:
        path = scaffold / "runtime_input.json"
        path.write_text(json.dumps({"request": text}), encoding="utf-8")
        return path

    def _run(self, scaffold: Path, input_path: Path) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, str(scaffold / "run_agent.py"), "--input", str(input_path)],
            cwd=scaffold,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def test_high_risk_tools_are_blocked_and_pending_approval(self) -> None:
        scaffold, td = self._scaffold(PERMISSION_ATTACK_MANIFEST)
        self.addCleanup(td.cleanup)
        output = self._run(scaffold, self._write_input(scaffold, "incident rollback refund production outage"))
        blocked = {row["tool"]: row["reason"] for row in output["blocked_tools"]}
        pending = {row["tool"] for row in output["pending_approvals"]}
        self.assertIn("production.rollback.request", blocked)
        self.assertIn("production.rollback.request", pending)
        self.assertEqual(output["status"], "blocked")

    def test_requires_approval_tool_enters_pending_approval(self) -> None:
        scaffold, td = self._scaffold(H2_MANIFEST)
        self.addCleanup(td.cleanup)
        output = self._run(scaffold, self._write_input(scaffold, "patient symptom urgent screen medical history"))
        pending = {row["tool"] for row in output["pending_approvals"]}
        self.assertIn("urgent_symptom.screen", pending)
        self.assertEqual(output["status"], "blocked")

    def test_unknown_tool_is_blocked_without_crash(self) -> None:
        scaffold, td = self._scaffold(DEVOPS_MANIFEST)
        self.addCleanup(td.cleanup)
        manifest_path = scaffold / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tools"].append(
            {
                "tool_name": "totally.synthetic",
                "description": "Unsupported synthetic tool",
                "side_effect_level": "low",
                "requires_approval": False,
                "allowed_callers": ["CoordinatorAgent"],
                "audit_log_required": True,
            }
        )
        manifest["workflows"][0]["tools_called"] = ["totally.synthetic"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        output = self._run(scaffold, self._write_input(scaffold, "plain request"))
        self.assertEqual(output["status"], "blocked")
        self.assertEqual(output["blocked_tools"][0]["reason"], "unsupported_tool")

    def test_allowed_callers_mismatch_is_permission_denied(self) -> None:
        scaffold, td = self._scaffold(DEVOPS_MANIFEST)
        self.addCleanup(td.cleanup)
        manifest_path = scaffold / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tools"][0]["allowed_callers"] = ["OtherAgent"]
        manifest["workflows"][0]["tools_called"] = [manifest["tools"][0]["tool_name"]]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        output = self._run(scaffold, self._write_input(scaffold, "plain request"))
        self.assertEqual(output["blocked_tools"][0]["reason"], "permission_denied")


if __name__ == "__main__":
    unittest.main()
