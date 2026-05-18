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


class AgentRuntimeLoopTests(unittest.TestCase):
    def _scaffold(self, manifest_path: Path = H1_MANIFEST) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_runtime_loop_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(manifest_path, out)
        return out, td

    def _run(self, scaffold: Path, *extra: str) -> tuple[int, dict[str, object]]:
        completed = subprocess.run(
            [sys.executable, str(scaffold / "run_agent.py"), *extra],
            cwd=scaffold,
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(completed.stdout)
        return completed.returncode, payload

    def test_dry_run_success_without_side_effects(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        code, output = self._run(scaffold, "--dry-run", "--input", "sample_input.json")
        self.assertEqual(code, 0, output)
        self.assertEqual(output["mode"], "dry-run")
        self.assertIn("workflow_entry_state", output)
        self.assertIn("available_tools", output)
        self.assertIn("blocked_tools", output)
        self.assertIn("pending_approvals", output)
        self.assertFalse((scaffold / "runtime_state.json").exists())
        self.assertFalse((scaffold / "audit" / "events.jsonl").exists())

    def test_real_run_executes_local_tool_and_advances_workflow(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        code, output = self._run(scaffold, "--input", "sample_input.json")
        self.assertEqual(code, 0, output)
        self.assertEqual(output["mode"], "run")
        self.assertEqual(output["status"], "completed")
        self.assertTrue(output["executed_tools"])
        self.assertTrue((scaffold / "runtime_state.json").exists())
        state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        self.assertNotEqual(state["current_workflow_state"], output.get("workflow_entry_state"))
        self.assertIn("intake", state["completed_steps"])
        self.assertTrue((scaffold / "audit" / "events.jsonl").exists())

    def test_guardrails_active_are_recorded(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        _code, output = self._run(scaffold, "--input", "sample_input.json")
        self.assertTrue(output["guardrails_active"])

    def test_invalid_manifest_fails_clearly(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        (scaffold / "manifest.json").write_text(json.dumps({"manifest_version": "1.0"}), encoding="utf-8")
        code, output = self._run(scaffold, "--input", "sample_input.json")
        self.assertEqual(code, 2)
        self.assertEqual(output["status"], "failed")
        self.assertIn("manifest missing required fields", str(output["error"]))


if __name__ == "__main__":
    unittest.main()
