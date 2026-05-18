from __future__ import annotations

import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_full_candidate_benchmark.validators.summary import load_or_run_summary
from tools.providers.project_generation_live_full_candidate import normalize_candidate_manifest, validate_candidate_runtime


class LiveProviderFullCandidateValidationTests(unittest.TestCase):
    def test_runtime_validation_passes_for_generated_projects(self) -> None:
        summary = load_or_run_summary()
        for row in summary["cases"]:
            self.assertTrue(row["generated_tests_passed"])
            self.assertTrue(row["runtime_validation"]["passed"])

    def test_candidate_manifest_path_safety(self) -> None:
        files, validation = normalize_candidate_manifest(
            "live_provider_text_stats_cli",
            {"files": [{"path": "../bad.py", "content": "print('bad')"}]},
        )
        self.assertFalse(files)
        self.assertFalse(validation["manifest_valid"])
        self.assertFalse(validation["paths_safe"])

    def test_validation_schema_contains_required_bools(self) -> None:
        summary = load_or_run_summary()
        for row in summary["cases"]:
            validation = row["attribution"]["provider_candidate_validation"]
            for key in ("manifest_valid", "paths_safe", "safety_scan_passed", "syntax_valid", "generated_tests_passed", "runtime_validation_passed"):
                self.assertIn(key, validation)


if __name__ == "__main__":
    unittest.main()

