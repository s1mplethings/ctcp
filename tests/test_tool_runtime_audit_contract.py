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


class ToolRuntimeAuditContractTests(unittest.TestCase):
    def _scaffold(self, manifest_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_tool_audit_")
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

    def _events(self, scaffold: Path) -> list[dict[str, object]]:
        return [json.loads(line) for line in (scaffold / "audit" / "events.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_audit_event_written_for_executed_tool(self) -> None:
        scaffold, _td = self._scaffold(H1_MANIFEST)
        output = self._run(scaffold)
        event_ids = {event["event_id"] for event in self._events(scaffold) if event["event_type"] == "tool_decision"}
        self.assertIn(output["tool_results"][0]["audit_event_id"], event_ids)

    def test_audit_event_written_for_blocked_and_unsupported_tool(self) -> None:
        scaffold, _td = self._scaffold(DEVOPS_MANIFEST)
        manifest_path = scaffold / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tools"].append(
            {
                "tool_name": "unknown.synthetic",
                "description": "Unsupported synthetic tool",
                "side_effect_level": "low",
                "requires_approval": False,
                "allowed_callers": ["CoordinatorAgent"],
                "audit_log_required": True,
            }
        )
        manifest["workflows"][0]["tools_called"] = ["unknown.synthetic"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        output = self._run(scaffold)
        decisions = [event for event in self._events(scaffold) if event["event_type"] == "tool_decision"]
        self.assertEqual(output["tool_results"][0]["status"], "unsupported")
        self.assertTrue(any(event["tool_name"] == "unknown.synthetic" and event["decision"] == "unsupported" for event in decisions))

    def test_state_records_unsupported_and_pending_approvals(self) -> None:
        scaffold, _td = self._scaffold(DEVOPS_MANIFEST)
        manifest_path = scaffold / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["tools"].append(
            {
                "tool_name": "unknown.local",
                "description": "Unsupported tool",
                "side_effect_level": "low",
                "requires_approval": False,
                "allowed_callers": ["CoordinatorAgent"],
                "audit_log_required": True,
            }
        )
        manifest["workflows"][0]["tools_called"] = ["unknown.local", "production.rollback.request"]
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self._run(scaffold)
        state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        self.assertTrue(state["unsupported_tools"])
        self.assertTrue(state["pending_approvals"])


if __name__ == "__main__":
    unittest.main()
