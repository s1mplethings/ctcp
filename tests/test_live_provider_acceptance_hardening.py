from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "tests" / "live_provider_blind_matrix" / "generated" / "live_provider_blind_matrix_summary.json"
REGISTRY = ROOT / "tools" / "providers" / "project_generation_fast_path_registry.py"


class LiveProviderAcceptanceHardeningTests(unittest.TestCase):
    def _summary(self) -> dict:
        self.assertTrue(SUMMARY.exists(), "run live_provider_blind_matrix before this test")
        return json.loads(SUMMARY.read_text(encoding="utf-8"))

    def test_phase20_gate_counts(self) -> None:
        doc = self._summary()
        self.assertTrue(doc.get("phase20_gate_passed"))
        self.assertGreaterEqual(doc.get("accepted_count", 0), 2)
        self.assertGreaterEqual(doc.get("accepted_count", 0) + doc.get("repaired_count", 0), 4)
        self.assertLessEqual(doc.get("fallback_count", 0), 1)
        self.assertEqual(doc.get("failed_count"), 0)
        self.assertIn("acceptance_rate", doc)
        self.assertIn("accepted_or_repaired_rate", doc)

    def test_no_blind_dedicated_fast_path_family(self) -> None:
        text = REGISTRY.read_text(encoding="utf-8")
        self.assertIn("live_provider_blind_candidate", text)
        self.assertNotIn("unit_converter_fast_path", text)
        self.assertNotIn("file_renamer_fast_path", text)
        self.assertNotIn("static_site_generator_fast_path", text)


if __name__ == "__main__":
    unittest.main()
