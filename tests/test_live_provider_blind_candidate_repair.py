from __future__ import annotations

import json
import unittest
from pathlib import Path

SUMMARY = Path("tests/live_provider_blind_matrix/generated/live_provider_blind_matrix_summary.json")


class LiveProviderBlindCandidateRepairTests(unittest.TestCase):
    def test_bounded_repair_attempts_are_recorded(self) -> None:
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        self.assertGreaterEqual(summary["accepted_count"] + summary["repaired_count"], 4)
        self.assertLessEqual(summary["fallback_count"], 1)
        self.assertEqual(summary["failed_count"], 0)
        for row in summary["cases"]:
            attempts = int(row["attribution"].get("provider_repair_attempt_count", 0) or 0)
            self.assertLessEqual(attempts, 1)
            if row["outcome"] == "repaired":
                self.assertEqual(attempts, 1)
                self.assertTrue(row["attribution"].get("repair_validation_passed"))

    def test_fallback_is_recorded_when_used(self) -> None:
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        self.assertGreaterEqual(summary["fallback_count"], 0)
        for row in summary["cases"]:
            if row["outcome"] == "fallback":
                self.assertTrue(row["attribution"].get("fallback_triggered"))
                self.assertTrue(row["attribution"].get("provider_fallbacks"))


if __name__ == "__main__":
    unittest.main()
