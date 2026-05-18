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
PERMISSION_ATTACK_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_permission_attack.json"


class AgentRuntimeAuditTests(unittest.TestCase):
    def _scaffold(self, manifest_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_runtime_audit_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(manifest_path, out)
        return out, td

    def _input(self, scaffold: Path, text: str) -> Path:
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

    def _events(self, scaffold: Path) -> list[dict[str, object]]:
        return [json.loads(line) for line in (scaffold / "audit" / "events.jsonl").read_text(encoding="utf-8").splitlines()]

    def test_audit_log_is_created_and_append_only(self) -> None:
        scaffold, td = self._scaffold(H1_MANIFEST)
        self.addCleanup(td.cleanup)
        self._run(scaffold, scaffold / "sample_input.json")
        first = self._events(scaffold)
        self._run(scaffold, scaffold / "sample_input.json")
        second = self._events(scaffold)
        self.assertGreater(len(second), len(first))
        for event in second:
            for key in ("timestamp", "event_type", "agent", "tool", "status", "details"):
                self.assertIn(key, event)

    def test_blocked_and_approval_events_have_evidence(self) -> None:
        scaffold, td = self._scaffold(PERMISSION_ATTACK_MANIFEST)
        self.addCleanup(td.cleanup)
        self._run(scaffold, self._input(scaffold, "incident rollback production outage"))
        events = self._events(scaffold)
        decisions = [event for event in events if event["event_type"] == "tool_decision"]
        self.assertTrue(any(event.get("decision") == "blocked" for event in decisions))
        self.assertTrue(any(event.get("reason") == "prohibited_action" for event in decisions))
        for event in decisions:
            for key in ("tool_name", "decision", "reason", "side_effect_level", "requires_approval"):
                self.assertIn(key, event)

    def test_workflow_transition_is_recorded(self) -> None:
        scaffold, td = self._scaffold(H1_MANIFEST)
        self.addCleanup(td.cleanup)
        self._run(scaffold, scaffold / "sample_input.json")
        events = self._events(scaffold)
        self.assertIn("workflow_transition", {event["event_type"] for event in events})


if __name__ == "__main__":
    unittest.main()
