from __future__ import annotations

import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_full_candidate_benchmark.validators.summary import load_or_run_summary
from tools.providers.project_generation_fast_path_registry import detect_fast_path
from tools.providers.project_generation_provider_assisted import provider_assisted_generation_mode


class LiveProviderFullCandidateGenerationTests(unittest.TestCase):
    def test_mode_exists_and_detects_projects(self) -> None:
        goal = "Create live_provider_full_candidate live_provider_text_stats_cli"
        self.assertEqual(provider_assisted_generation_mode(goal), "live_provider_full_candidate")
        self.assertEqual(detect_fast_path(goal).project_id, "live_provider_text_stats_cli")

    def test_benchmark_passes_all_cases(self) -> None:
        summary = load_or_run_summary()
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["passed"], 3)

    def test_ordinary_mainline_and_no_agent_scaffold(self) -> None:
        summary = load_or_run_summary()
        for row in summary["cases"]:
            self.assertTrue(row["ordinary_mainline"])
            self.assertTrue(row["no_agent_scaffold"])
            self.assertFalse(row["attribution"]["used_agent_project"])
            self.assertFalse(row["attribution"]["used_agent_scaffold"])

    def test_live_provider_actually_called(self) -> None:
        summary = load_or_run_summary()
        self.assertGreater(summary["provider_request_count"], 0)
        self.assertGreater(summary["provider_project_candidate_count"], 0)
        for row in summary["cases"]:
            self.assertTrue(row["attribution"]["live_provider_used"])
            self.assertGreater(row["attribution"]["provider_request_count"], 0)


if __name__ == "__main__":
    unittest.main()
