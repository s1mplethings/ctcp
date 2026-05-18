from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"


class LiveProviderMediumProjectValidationTests(unittest.TestCase):
    def test_generated_tests_and_runtime_validators_run(self) -> None:
        doc = json.loads(SUMMARY.read_text(encoding="utf-8"))
        for row in doc.get("cases", []):
            self.assertEqual(row.get("generated_tests", {}).get("exit_code"), 0)
            self.assertTrue(row.get("runtime_validation", {}).get("passed"))
        for row in doc.get("cases", []):
            if row.get("outcome") in {"accepted", "repaired"}:
                self.assertGreaterEqual(float(row.get("provider_authored_file_ratio", 0.0)), 0.6)


if __name__ == "__main__":
    unittest.main()
