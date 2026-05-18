from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_full_candidate_benchmark.validators.summary import load_or_run_summary
from tools.providers.project_generation_live_full_candidate import apply_live_full_candidate, deterministic_candidate_files


class LiveProviderFullCandidateFallbackTests(unittest.TestCase):
    def test_invalid_provider_candidate_falls_back(self) -> None:
        old = os.environ.get("CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID")
        os.environ["CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID"] = "1"
        try:
            root = "project_output/live_provider_text_stats_cli"
            fallback = deterministic_candidate_files("live_provider_text_stats_cli", root, "live_provider_full_candidate forced invalid")
            result = apply_live_full_candidate(
                goal_text="live_provider_full_candidate live_provider_text_stats_cli",
                project_id="live_provider_text_stats_cli",
                project_root=root,
                deterministic_files=fallback,
            )
        finally:
            if old is None:
                os.environ.pop("CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID", None)
            else:
                os.environ["CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID"] = old
        self.assertFalse(result.metadata["provider_candidate_accepted"])
        self.assertTrue(result.metadata["fallback_triggered"])
        self.assertTrue(result.files)

    def test_benchmark_fallback_case_passes(self) -> None:
        summary = load_or_run_summary()
        row = next(item for item in summary["cases"] if item["case"] == "invalid_provider_candidate_fallback")
        self.assertEqual(row["status"], "passed")
        self.assertTrue(row["attribution"]["fallback_triggered"])


if __name__ == "__main__":
    unittest.main()

