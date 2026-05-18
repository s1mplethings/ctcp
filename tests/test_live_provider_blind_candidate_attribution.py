from __future__ import annotations

import json
import unittest
from pathlib import Path

SUMMARY = Path("tests/live_provider_blind_matrix/generated/live_provider_blind_matrix_summary.json")


class LiveProviderBlindCandidateAttributionTests(unittest.TestCase):
    def test_attribution_exists_for_every_case(self) -> None:
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        for row in summary["cases"]:
            attr_path = Path(row["attribution_path"])
            self.assertTrue(attr_path.exists(), row["project"])
            attr = json.loads(attr_path.read_text(encoding="utf-8"))
            self.assertEqual(attr["generation_mode"], "live_provider_blind_candidate")
            self.assertTrue(attr["blind_case"])
            self.assertEqual(attr["blind_case_name"], row["project"])
            self.assertFalse(attr["used_agent_project"])
            self.assertFalse(attr["used_agent_scaffold"])
            self.assertFalse(attr["used_local_agent_runtime"])

    def test_provider_participation_recorded(self) -> None:
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        self.assertGreaterEqual(summary["provider_request_count"], 5)
        self.assertEqual(summary["provider_project_candidate_count"], 5)
        for row in summary["cases"]:
            attr = row["attribution"]
            self.assertTrue(attr["used_provider_agent"])
            self.assertGreater(int(attr["provider_request_count"]), 0)
            self.assertIn(attr["provider_candidate_outcome"], {"accepted", "repaired", "fallback", "unsupported"})


if __name__ == "__main__":
    unittest.main()
