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
RESEARCH_INPUT = ROOT / "tests" / "agent_runtime_benchmark" / "fixtures" / "research_agent_web.json"
WEB_FIXTURE = ROOT / "tests" / "fixtures" / "web_search_fixture.json"


class WebToolRuntimeResultTests(unittest.TestCase):
    def _scaffold(self) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_web_results_")
        root = Path(td.name)
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(generate_manifest_from_file(RESEARCH_INPUT), indent=2), encoding="utf-8")
        out = root / "scaffold"
        generate_agent_scaffold(manifest_path, out)
        for path in (out / "runtime_state.json", out / "audit" / "events.jsonl"):
            if path.exists():
                path.unlink()
        self.addCleanup(td.cleanup)
        return out, td

    def _input(self, scaffold: Path) -> Path:
        path = scaffold / "runtime_input.json"
        path.write_text(
            json.dumps({"request": "search public web product category portable air purifier", "query": "portable air purifier", "max_results": 2}),
            encoding="utf-8",
        )
        return path

    def _run(
        self,
        scaffold: Path,
        env: dict[str, str] | None = None,
        expected_returncodes: tuple[int, ...] = (0,),
    ) -> dict[str, object]:
        merged = os.environ.copy()
        if env:
            merged.update(env)
        completed = subprocess.run(
            [sys.executable, str(scaffold / "run_agent.py"), "--input", str(self._input(scaffold))],
            cwd=scaffold,
            env=merged,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertIn(completed.returncode, expected_returncodes, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def test_web_provider_unavailable_returns_failed_tool_result(self) -> None:
        scaffold, _td = self._scaffold()
        output = self._run(scaffold, {"CTCP_AGENT_WEB_PROVIDER": ""}, expected_returncodes=(2,))
        first = output["tool_results"][0]
        self.assertEqual(first["tool_name"], "web_search")
        self.assertEqual(first["status"], "failed")
        self.assertEqual(first["reason"], "web_provider_unavailable")

    def test_fixture_provider_returns_sources_for_web_search_and_fetch_url(self) -> None:
        scaffold, _td = self._scaffold()
        output = self._run(scaffold, {"CTCP_AGENT_WEB_PROVIDER": "fixture", "CTCP_AGENT_WEB_FIXTURE_PATH": str(WEB_FIXTURE)})
        results = {row["tool_name"]: row for row in output["tool_results"]}
        self.assertEqual(results["web_search"]["status"], "executed")
        self.assertTrue(results["web_search"]["output"]["sources"])
        self.assertEqual(results["fetch_url"]["status"], "executed")
        self.assertTrue(results["fetch_url"]["output"]["source"])
        self.assertTrue(output["sources"])
        state = json.loads((scaffold / "runtime_state.json").read_text(encoding="utf-8"))
        self.assertTrue(any(row["tool_name"] == "web_search" for row in state["last_tool_results"]))

    def test_web_derived_output_without_sources_fails(self) -> None:
        scaffold, td = self._scaffold()
        bad_fixture = Path(td.name) / "bad_web_fixture.json"
        bad_fixture.write_text(json.dumps({"search_index": [], "pages": {}}), encoding="utf-8")
        output = self._run(
            scaffold,
            {"CTCP_AGENT_WEB_PROVIDER": "fixture", "CTCP_AGENT_WEB_FIXTURE_PATH": str(bad_fixture)},
            expected_returncodes=(2,),
        )
        first = output["tool_results"][0]
        self.assertEqual(first["status"], "failed")
        self.assertEqual(first["reason"], "missing_sources")


if __name__ == "__main__":
    unittest.main()
