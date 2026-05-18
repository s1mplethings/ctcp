from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.agent_manifest_consumer import generate_agent_scaffold


ROOT = Path(__file__).resolve().parents[1]
H1_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "holdout_generated" / "output_h1_personal_productivity.json"


class AgentPlannerLoopTests(unittest.TestCase):
    def _scaffold(self) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_planner_loop_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(H1_MANIFEST, out)
        return out, td

    def _run(self, scaffold: Path, env: dict[str, str] | None = None, dry_run: bool = False) -> tuple[int, dict[str, object]]:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        cmd = [sys.executable, str(scaffold / "run_agent.py"), "--input", str(scaffold / "sample_input.json")]
        if dry_run:
            cmd.insert(2, "--dry-run")
        completed = subprocess.run(cmd, cwd=scaffold, env=merged, text=True, capture_output=True, check=False)
        return completed.returncode, json.loads(completed.stdout)

    def test_deterministic_planner_selected_by_default_and_writes_trace(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        code, output = self._run(scaffold)
        self.assertEqual(code, 0, output)
        self.assertEqual(output["planner_mode"], "deterministic")
        self.assertEqual(output["planner_trace_path"], "planner_trace.json")
        trace = json.loads((scaffold / "planner_trace.json").read_text(encoding="utf-8"))
        self.assertTrue(trace)
        self.assertLessEqual(len(trace), 5)

    def test_dry_run_does_not_execute_planner_tools_or_write_trace(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        code, output = self._run(scaffold, dry_run=True)
        self.assertEqual(code, 0, output)
        self.assertEqual(output["mode"], "dry-run")
        self.assertFalse((scaffold / "planner_trace.json").exists())
        self.assertFalse((scaffold / "runtime_state.json").exists())

    def test_max_steps_exceeded_fails_clearly(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        code, output = self._run(scaffold, {"CTCP_AGENT_MAX_STEPS": "1"})
        self.assertEqual(code, 2, output)
        self.assertEqual(output["status"], "failed")
        self.assertEqual(output["reason"], "planner_max_steps_exceeded")

    def test_provider_planner_without_provider_returns_clear_failure(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        code, output = self._run(scaffold, {"CTCP_AGENT_PLANNER": "provider"})
        self.assertEqual(code, 2, output)
        self.assertEqual(output["planner_mode"], "provider")
        self.assertEqual(output["reason"], "provider_planner_unavailable")
        self.assertEqual(output["tool_results"], [])


if __name__ == "__main__":
    unittest.main()
