from __future__ import annotations

import os
import unittest

from tools.providers.project_generation_non_web_fast_paths import non_web_project_files
from tools.providers.project_generation_provider_assisted import apply_provider_assistance


class ProviderAssistedFallbackTests(unittest.TestCase):
    def test_invalid_provider_output_falls_back_to_deterministic_files(self) -> None:
        files = non_web_project_files(
            goal_text="CSV Expense Analyzer CLI with --input --output sample_expenses.csv category totals monthly totals",
            project_id="csv_expense_analyzer",
            project_root="project_output/csv_expense_analyzer",
            workflow_doc_rel="docs/expense_analyzer_workflow.md",
            context_used=[],
            project_archetype="cli_toolkit",
        )
        old = os.environ.get("CTCP_PROVIDER_ASSISTED_FIXTURE")
        os.environ["CTCP_PROVIDER_ASSISTED_FIXTURE"] = "invalid"
        try:
            result = apply_provider_assistance(
                goal_text="provider-assisted CSV Expense Analyzer CLI",
                project_id="csv_expense_analyzer",
                project_root="project_output/csv_expense_analyzer",
                deterministic_files=files,
            )
        finally:
            if old is None:
                os.environ.pop("CTCP_PROVIDER_ASSISTED_FIXTURE", None)
            else:
                os.environ["CTCP_PROVIDER_ASSISTED_FIXTURE"] = old
        self.assertEqual(result.files, files)
        self.assertTrue(result.metadata["provider_validation"]["fallback_triggered"])
        self.assertTrue(result.metadata["provider_fallbacks"])


if __name__ == "__main__":
    unittest.main()
