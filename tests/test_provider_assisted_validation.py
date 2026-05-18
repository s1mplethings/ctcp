from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
for item in (ROOT, TESTS_DIR):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from tools.providers.project_generation_provider_assisted import validate_provider_fragments
from provider_assisted_benchmark.validators.summary import load_or_run_summary


class ProviderAssistedValidationTests(unittest.TestCase):
    def test_safety_filter_blocks_forbidden_shell_fragment(self) -> None:
        validation = validate_provider_fragments({"bad.py": "import subprocess\nsubprocess.run(['echo', 'x'])\n"})
        self.assertFalse(validation["syntax_valid"])
        self.assertTrue(validation["fallback_triggered"])

    def test_runtime_validation_passes_for_benchmark_outputs(self) -> None:
        summary = load_or_run_summary()
        for row in summary["projects"]:
            self.assertTrue(row["runtime_validation"]["passed"], row["case"])
            self.assertTrue(row["generated_tests_passed"], row["case"])
            self.assertTrue(row["provider_ok"], row["case"])


if __name__ == "__main__":
    unittest.main()
