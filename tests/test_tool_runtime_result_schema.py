from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.agent_manifest_consumer import generate_agent_scaffold


ROOT = Path(__file__).resolve().parents[1]
H1_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "holdout_generated" / "output_h1_personal_productivity.json"
DEVOPS_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_devops_incident.json"


TOOL_RESULT_FIELDS = {
    "tool_name",
    "status",
    "reason",
    "side_effect_level",
    "requires_approval",
    "output",
    "audit_event_id",
    "duration_ms",
}


class ToolRuntimeResultSchemaTests(unittest.TestCase):
    def _scaffold(self, manifest_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_tool_result_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(manifest_path, out)
        self.addCleanup(td.cleanup)
        return out, td

    def _run(self, scaffold: Path) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, str(scaffold / "run_agent.py"), "--input", "sample_input.json"],
            cwd=scaffold,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def test_tool_result_schema_present_for_executed_tool(self) -> None:
        scaffold, _td = self._scaffold(H1_MANIFEST)
        output = self._run(scaffold)
        self.assertTrue(output["tool_results"])
        result = output["tool_results"][0]
        self.assertTrue(TOOL_RESULT_FIELDS.issubset(result))
        self.assertEqual(result["status"], "executed")
        self.assertTrue(result["audit_event_id"])

    def test_tool_result_schema_present_for_blocked_tool(self) -> None:
        scaffold, _td = self._scaffold(DEVOPS_MANIFEST)
        manifest_path = scaffold / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tools"].append(
            {
                "tool_name": "production.rollback.request",
                "description": "Rollback production",
                "side_effect_level": "high",
                "requires_approval": True,
                "allowed_callers": ["CoordinatorAgent"],
                "audit_log_required": True,
            }
        )
        manifest["workflows"][0]["tools_called"] = ["production.rollback.request"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        output = self._run(scaffold)
        result = output["tool_results"][0]
        self.assertTrue(TOOL_RESULT_FIELDS.issubset(result))
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "prohibited_action")


if __name__ == "__main__":
    unittest.main()
