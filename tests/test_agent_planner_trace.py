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
TRACE_FIELDS = {"step_index", "planner_mode", "decision", "tool_name", "reason", "input", "observed_result_status"}


class AgentPlannerTraceTests(unittest.TestCase):
    def _scaffold(self) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_planner_trace_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(H1_MANIFEST, out)
        return out, td

    def _run(self, scaffold: Path) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, str(scaffold / "run_agent.py"), "--input", str(scaffold / "sample_input.json")],
            cwd=scaffold,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def test_planner_trace_schema_is_written(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        output = self._run(scaffold)
        trace_path = scaffold / str(output["planner_trace_path"])
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        self.assertTrue(trace)
        self.assertTrue(all(TRACE_FIELDS.issubset(step) for step in trace))
        self.assertEqual(trace[-1]["decision"], "final_answer")

    def test_runtime_state_records_planner_metadata(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        self._run(scaffold)
        state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["planner"]["mode"], "deterministic")
        self.assertEqual(state["planner"]["trace_path"], "planner_trace.json")
        self.assertGreaterEqual(state["planner"]["step_count"], 1)

    def test_audit_includes_planner_tool_decisions(self) -> None:
        scaffold, td = self._scaffold()
        self.addCleanup(td.cleanup)
        self._run(scaffold)
        events = [
            json.loads(line)
            for line in (scaffold / "audit" / "events.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertTrue(any(event.get("event_type") == "tool_decision" for event in events))


if __name__ == "__main__":
    unittest.main()
