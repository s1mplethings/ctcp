from __future__ import annotations

import unittest
from pathlib import Path
import sys

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_benchmark.validators.summary import load_or_run_summary


class LiveProviderVariationTests(unittest.TestCase):
    def test_live_provider_output_differs_from_deterministic_output(self) -> None:
        summary = load_or_run_summary()
        self.assertTrue(summary["provider_assisted_output_differs"])
        generated = {path for row in summary["projects"] for path in row["attribution"]["provider_generated_files"]}
        self.assertTrue(any("provider_live" in path or "live_provider" in path for path in generated))


if __name__ == "__main__":
    unittest.main()
