from __future__ import annotations

import unittest
from pathlib import Path
import sys

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_benchmark.validators.summary import load_or_run_summary


class LiveProviderGenerationTests(unittest.TestCase):
    def test_live_provider_benchmark_passes_all_cases(self) -> None:
        summary = load_or_run_summary()
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["passed"], 3)
        self.assertTrue(summary["provider_used"])

    def test_live_provider_actually_called_and_recorded(self) -> None:
        summary = load_or_run_summary()
        self.assertGreater(summary["provider_request_count"], 0)
        self.assertGreater(summary["provider_fragment_count"], 0)
        for row in summary["projects"]:
            attr = row["attribution"]
            self.assertEqual(attr["generation_mode"], "live_provider_assisted")
            self.assertEqual(attr["provider_name"], "live_provider")
            self.assertTrue(attr["live_provider_used"])

    def test_generated_files_exist(self) -> None:
        summary = load_or_run_summary()
        for row in summary["projects"]:
            run_dir = Path(row["run_dir"])
            generated = row["attribution"]["provider_generated_files"]
            self.assertTrue(generated)
            for rel in generated:
                self.assertTrue((run_dir / rel).exists(), rel)


if __name__ == "__main__":
    unittest.main()
