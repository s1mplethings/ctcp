from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
for item in (ROOT, TESTS_DIR):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from tools.providers.project_generation_non_web_fast_paths import non_web_project_files
from tools.providers.project_generation_provider_assisted import apply_provider_assistance
from provider_assisted_benchmark.validators.summary import load_or_run_summary


class ProviderAssistedVariationTests(unittest.TestCase):
    def test_provider_assisted_output_differs_from_deterministic_output(self) -> None:
        deterministic = non_web_project_files(
            goal_text="CSV Expense Analyzer CLI with --input --output sample_expenses.csv category totals monthly totals",
            project_id="csv_expense_analyzer",
            project_root="project_output/csv_expense_analyzer",
            workflow_doc_rel="docs/expense_analyzer_workflow.md",
            context_used=[],
            project_archetype="cli_toolkit",
        )
        assisted = apply_provider_assistance(
            goal_text="provider-assisted CSV Expense Analyzer CLI",
            project_id="csv_expense_analyzer",
            project_root="project_output/csv_expense_analyzer",
            deterministic_files=deterministic,
        )
        self.assertNotEqual(set(deterministic), set(assisted.files))
        self.assertIn("project_output/csv_expense_analyzer/provider_assisted_helper.py", assisted.files)

    def test_benchmark_summary_records_variation(self) -> None:
        summary = load_or_run_summary()
        self.assertTrue(summary["provider_assisted_output_differs"])


if __name__ == "__main__":
    unittest.main()
