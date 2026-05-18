from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
for item in (ROOT, TESTS_DIR):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_fast_path_registry import detect_fast_path_project
from provider_assisted_benchmark.validators.summary import load_or_run_summary


class ProviderAssistedGenerationTests(unittest.TestCase):
    def test_provider_assisted_mode_enabled_through_output_contract(self) -> None:
        goal = "provider-assisted CSV Expense Analyzer CLI with --input --output sample_expenses.csv category totals monthly totals"
        self.assertEqual(detect_fast_path_project(goal), "csv_expense_analyzer")
        contract = normalize_output_contract_freeze({}, goal=goal)
        self.assertEqual(contract["generation_mode"], "provider_assisted")
        self.assertEqual(contract["project_id"], "csv_expense_analyzer")

    def test_provider_assisted_benchmark_passes_all_cases(self) -> None:
        summary = load_or_run_summary()
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["passed"], 3)
        self.assertTrue(all(row["ordinary_mainline"] for row in summary["projects"]))


if __name__ == "__main__":
    unittest.main()
