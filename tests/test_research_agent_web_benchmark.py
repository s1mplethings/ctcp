from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "agent_runtime_benchmark"))

from run_runtime_benchmark import CASES, _case_result  # noqa: E402


class ResearchAgentWebBenchmarkTests(unittest.TestCase):
    def test_research_agent_web_case_passes_with_fixture_provider(self) -> None:
        spec = next(case for case in CASES if case["case"] == "research_agent_web")
        result = _case_result(spec)
        self.assertEqual(result["status"], "pass", result["failed_assertions"])
        self.assertIn("web_search", result["executed_tools"])
        self.assertIn("fetch_url", result["executed_tools"])


if __name__ == "__main__":
    unittest.main()
