from __future__ import annotations

import unittest
from pathlib import Path
import sys

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_benchmark.validators.summary import load_or_run_summary


class LiveProviderValidationTests(unittest.TestCase):
    def test_runtime_validation_still_passes(self) -> None:
        summary = load_or_run_summary()
        for row in summary["projects"]:
            self.assertTrue(row["generated_tests_passed"], row["case"])
            self.assertTrue(row["runtime_validation"]["passed"], row["case"])
            self.assertTrue(row["ordinary_mainline"], row["case"])
            self.assertTrue(row["no_agent_scaffold"], row["case"])

    def test_provider_fragments_syntax_validate_without_fallback(self) -> None:
        summary = load_or_run_summary()
        for row in summary["projects"]:
            validation = row["attribution"]["provider_validation"]
            self.assertTrue(validation["syntax_valid"])
            self.assertFalse(validation["fallback_triggered"])
            self.assertEqual(row["attribution"]["provider_fallbacks"], [])


if __name__ == "__main__":
    unittest.main()
