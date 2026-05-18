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


class AgentRuntimeStateTests(unittest.TestCase):
    def _scaffold(self, manifest_path: Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_runtime_state_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(manifest_path, out)
        return out, td

    def _input(self, scaffold: Path, text: str) -> Path:
        path = scaffold / "runtime_input.json"
        path.write_text(json.dumps({"request": text}), encoding="utf-8")
        return path

    def _run(self, scaffold: Path, input_path: Path, dry: bool = False) -> dict[str, object]:
        args = [sys.executable, str(scaffold / "run_agent.py")]
        if dry:
            args.append("--dry-run")
        args += ["--input", str(input_path)]
        completed = subprocess.run(args, cwd=scaffold, text=True, capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def test_runtime_state_schema_is_created(self) -> None:
        scaffold, td = self._scaffold(H1_MANIFEST)
        self.addCleanup(td.cleanup)
        self._run(scaffold, scaffold / "sample_input.json")
        state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        for key in (
            "current_agent",
            "current_workflow_state",
            "completed_steps",
            "executed_tools",
            "blocked_tools",
            "pending_approvals",
            "unsupported_tools",
            "last_tool_results",
            "memory",
            "last_updated_at",
        ):
            self.assertIn(key, state)

    def test_second_run_reads_existing_runtime_state(self) -> None:
        scaffold, td = self._scaffold(H1_MANIFEST)
        self.addCleanup(td.cleanup)
        first = self._run(scaffold, scaffold / "sample_input.json")
        first_state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        second = self._run(scaffold, scaffold / "sample_input.json")
        second_state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        self.assertEqual(first["workflow_state"], first_state["current_workflow_state"])
        self.assertEqual(second["workflow_state"], second_state["current_workflow_state"])
        self.assertGreaterEqual(len(second_state["completed_steps"]), len(first_state["completed_steps"]))

    def test_dry_run_does_not_change_existing_runtime_state(self) -> None:
        scaffold, td = self._scaffold(H1_MANIFEST)
        self.addCleanup(td.cleanup)
        self._run(scaffold, scaffold / "sample_input.json")
        before = (scaffold / "runtime_state.json").read_text(encoding="utf-8")
        self._run(scaffold, scaffold / "sample_input.json", dry=True)
        after = (scaffold / "runtime_state.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_pending_approvals_are_not_lost_on_resume(self) -> None:
        scaffold, td = self._scaffold(PERMISSION_ATTACK_MANIFEST)
        self.addCleanup(td.cleanup)
        input_path = self._input(scaffold, "incident rollback production outage")
        self._run(scaffold, input_path)
        first_state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        self._run(scaffold, input_path)
        second_state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        self.assertTrue(first_state["pending_approvals"])
        self.assertEqual(first_state["pending_approvals"], second_state["pending_approvals"])


if __name__ == "__main__":
    unittest.main()
