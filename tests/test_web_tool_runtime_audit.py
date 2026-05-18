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


class WebToolRuntimeAuditTests(unittest.TestCase):
    def _scaffold(self) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_web_audit_")
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

    def test_web_audit_logs_query_url_and_sources(self) -> None:
        scaffold, _td = self._scaffold()
        runtime_input = scaffold / "runtime_input.json"
        runtime_input.write_text(
            json.dumps({"request": "search public web product category portable air purifier", "query": "portable air purifier"}),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env.update({"CTCP_AGENT_WEB_PROVIDER": "fixture", "CTCP_AGENT_WEB_FIXTURE_PATH": str(WEB_FIXTURE)})
        completed = subprocess.run(
            [sys.executable, str(scaffold / "run_agent.py"), "--input", str(runtime_input)],
            cwd=scaffold,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        events = [json.loads(line) for line in (scaffold / "audit" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
        decisions = [event for event in events if event["event_type"] == "tool_decision"]
        self.assertTrue(any(event["tool_name"] == "web_search" and event["query"] for event in decisions))
        self.assertTrue(any(event["tool_name"] == "fetch_url" and event["url"] for event in decisions))
        self.assertTrue(any(event.get("sources") for event in decisions))
        self.assertTrue(all(event.get("audit_required") for event in decisions))


if __name__ == "__main__":
    unittest.main()
