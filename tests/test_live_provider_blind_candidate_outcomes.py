from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TESTS_ROOT = Path(__file__).resolve().parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from live_provider_blind_matrix.run_live_provider_blind_matrix import write_blind_review_pack

SUMMARY = Path("tests/live_provider_blind_matrix/generated/live_provider_blind_matrix_summary.json")


class LiveProviderBlindCandidateOutcomesTests(unittest.TestCase):
    def test_benchmark_pass_rule(self) -> None:
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["failed_count"], 0)
        self.assertGreaterEqual(summary["accepted_count"] + summary["repaired_count"], 3)

    def test_review_pack_contains_blind_matrix_summary(self) -> None:
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        write_blind_review_pack(summary)
        text = Path("meta/reports/REVIEW_PACK.md").read_text(encoding="utf-8")
        self.assertIn("Live Provider Blind Matrix Summary", text)
        self.assertIn("live_provider_unit_converter_cli", text)


if __name__ == "__main__":
    unittest.main()
