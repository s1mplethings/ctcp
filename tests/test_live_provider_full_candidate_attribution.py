from __future__ import annotations

import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_full_candidate_benchmark.validators.summary import load_or_run_summary


class LiveProviderFullCandidateAttributionTests(unittest.TestCase):
    def test_attribution_records_provider_candidate_state(self) -> None:
        summary = load_or_run_summary()
        for row in summary["cases"]:
            attr = row["attribution"]
            self.assertEqual(attr["generation_mode"], "live_provider_full_candidate")
            self.assertEqual(attr["provider_authorship"], "provider_candidate_authored")
            self.assertIn("provider_candidate_accepted", attr)
            self.assertIn("fallback_triggered", attr)
            self.assertIn("provider_candidate_validation", attr)

    def test_accepted_cases_record_generated_files(self) -> None:
        summary = load_or_run_summary()
        accepted = [row for row in summary["cases"] if row["attribution"]["provider_candidate_accepted"]]
        self.assertGreaterEqual(len(accepted), 2)
        for row in accepted:
            run_dir = Path(row["run_dir"])
            for rel in row["attribution"]["provider_generated_files"]:
                self.assertTrue((run_dir / rel).exists(), rel)

    def test_fallback_case_records_fallback_reason(self) -> None:
        summary = load_or_run_summary()
        row = next(item for item in summary["cases"] if item["case"] == "invalid_provider_candidate_fallback")
        attr = row["attribution"]
        self.assertFalse(attr["provider_candidate_accepted"])
        self.assertTrue(attr["fallback_triggered"])
        self.assertTrue(attr["provider_fallbacks"])


if __name__ == "__main__":
    unittest.main()

