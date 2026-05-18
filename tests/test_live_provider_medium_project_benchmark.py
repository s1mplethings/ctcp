from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"


class LiveProviderMediumProjectBenchmarkTests(unittest.TestCase):
    def _summary(self) -> dict:
        self.assertTrue(SUMMARY.exists(), "run live_provider_medium_project_benchmark before this test")
        return json.loads(SUMMARY.read_text(encoding="utf-8"))

    def test_medium_benchmark_passed_after_phase20_gate(self) -> None:
        doc = self._summary()
        self.assertEqual(doc.get("status"), "passed")
        self.assertTrue(doc.get("phase20", {}).get("phase20_gate_passed"))
        self.assertGreaterEqual(doc.get("case_count", 0), 4)
        self.assertEqual(doc.get("failed_count"), 0)
        self.assertGreaterEqual(doc.get("accepted_count", 0) + doc.get("repaired_count", 0), 2)
        self.assertLessEqual(doc.get("fallback_count", 0), 1)
        self.assertGreaterEqual(doc.get("provider_project_candidate_count", 0), doc.get("case_count", 0))

    def test_medium_cases_preserve_mainline(self) -> None:
        for row in self._summary().get("cases", []):
            self.assertTrue(row.get("ordinary_mainline"))
            self.assertTrue(row.get("no_agent_scaffold"))
            self.assertEqual(row.get("status"), "passed")
            self.assertTrue(row.get("medium_project_contract_ok"))


if __name__ == "__main__":
    unittest.main()
