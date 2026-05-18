from __future__ import annotations

import os
import unittest

from tools.providers.project_generation_provider_assisted import apply_provider_assistance


class LiveProviderFallbackTests(unittest.TestCase):
    def test_invalid_live_provider_output_falls_back(self) -> None:
        old_force = os.environ.get("CTCP_LIVE_PROVIDER_FORCE_INVALID")
        old_live = os.environ.get("CTCP_LIVE_PROVIDER_ASSISTED")
        try:
            os.environ["CTCP_LIVE_PROVIDER_FORCE_INVALID"] = "1"
            os.environ["CTCP_LIVE_PROVIDER_ASSISTED"] = "1"
            deterministic = {"project_output/csv_expense_analyzer/README.md": "# CSV\n"}
            result = apply_provider_assistance(
                goal_text="live_provider_assisted CSV Expense Analyzer CLI",
                project_id="csv_expense_analyzer",
                project_root="project_output/csv_expense_analyzer",
                deterministic_files=deterministic,
            )
        finally:
            if old_force is None:
                os.environ.pop("CTCP_LIVE_PROVIDER_FORCE_INVALID", None)
            else:
                os.environ["CTCP_LIVE_PROVIDER_FORCE_INVALID"] = old_force
            if old_live is None:
                os.environ.pop("CTCP_LIVE_PROVIDER_ASSISTED", None)
            else:
                os.environ["CTCP_LIVE_PROVIDER_ASSISTED"] = old_live
        self.assertEqual(result.files, deterministic)
        self.assertEqual(result.metadata["generation_mode"], "live_provider_assisted")
        self.assertTrue(result.metadata["live_provider_used"])
        self.assertTrue(result.metadata["provider_validation"]["fallback_triggered"])
        self.assertTrue(result.metadata["provider_fallbacks"])


if __name__ == "__main__":
    unittest.main()
