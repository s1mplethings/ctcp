from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.agent_manifest_consumer import generate_agent_scaffold
from tools.agent_manifest_generator import generate_manifest_from_file


ROOT = Path(__file__).resolve().parents[1]
WEB_INPUT = ROOT / "tests" / "agent_runtime_benchmark" / "fixtures" / "research_agent_web.json"
WEB_FIXTURE = ROOT / "tests" / "fixtures" / "web_search_fixture.json"


class AgentPlannerFinalAnswerTests(unittest.TestCase):
    def _scaffold_from_input(self, input_doc: dict[str, object] | Path) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_planner_final_")
        if isinstance(input_doc, Path):
            manifest = generate_manifest_from_file(input_doc)
        else:
            input_path = Path(td.name) / "input.json"
            input_path.write_text(json.dumps(input_doc, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest = generate_manifest_from_file(input_path)
        manifest_path = Path(td.name) / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(manifest_path, out)
        return out, td

    def _write_input(self, scaffold: Path, payload: dict[str, object]) -> Path:
        path = scaffold / "planner_input.json"
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return path

    def _run(self, scaffold: Path, payload: dict[str, object], env: dict[str, str] | None = None) -> tuple[int, dict[str, object]]:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        input_path = self._write_input(scaffold, payload)
        completed = subprocess.run(
            [sys.executable, str(scaffold / "run_agent.py"), "--input", str(input_path)],
            cwd=scaffold,
            env=merged,
            text=True,
            capture_output=True,
            check=False,
        )
        return completed.returncode, json.loads(completed.stdout)

    def test_research_task_final_answer_includes_sources(self) -> None:
        scaffold, td = self._scaffold_from_input(WEB_INPUT)
        self.addCleanup(td.cleanup)
        code, output = self._run(
            scaffold,
            {"request": "search public web product category portable air purifier", "query": "portable air purifier"},
            {"CTCP_AGENT_WEB_PROVIDER": "fixture", "CTCP_AGENT_WEB_FIXTURE_PATH": str(WEB_FIXTURE)},
        )
        self.assertEqual(code, 0, output)
        self.assertEqual(output["status"], "completed")
        self.assertTrue(output["final_answer"]["sources"])
        self.assertTrue(output["sources"])

    def test_product_feedback_task_completes_draft(self) -> None:
        scaffold, td = self._scaffold_from_input(
            {
                "case_id": "product_feedback_task",
                "title": "Product feedback summary",
                "goal": "Create a product feedback agent that collects product feedback, classifies themes, summarizes trends, and writes a weekly report.",
            }
        )
        self.addCleanup(td.cleanup)
        code, output = self._run(scaffold, {"request": "summarize product feedback trends and write weekly report"})
        self.assertEqual(code, 0, output)
        self.assertEqual(output["status"], "completed")
        self.assertIn("weekly_report.write", output["final_answer"]["executed_tools"])
        self.assertIn("deterministic local tools", output["final_answer"]["text"])

    def test_web_derived_answer_without_sources_fails(self) -> None:
        scaffold, td = self._scaffold_from_input(WEB_INPUT)
        self.addCleanup(td.cleanup)
        bad_fixture = Path(td.name) / "bad_web_fixture.json"
        bad_fixture.write_text(json.dumps({"search_index": [], "pages": {}}), encoding="utf-8")
        code, output = self._run(
            scaffold,
            {"request": "search public web product category portable air purifier", "query": "portable air purifier"},
            {"CTCP_AGENT_WEB_PROVIDER": "fixture", "CTCP_AGENT_WEB_FIXTURE_PATH": str(bad_fixture)},
        )
        self.assertEqual(code, 2, output)
        self.assertEqual(output["status"], "failed")
        self.assertEqual(output["reason"], "missing_sources")


if __name__ == "__main__":
    unittest.main()
