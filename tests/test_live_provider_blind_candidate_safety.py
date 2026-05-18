from __future__ import annotations

import unittest

from tools.providers.project_generation_candidate_validation import candidate_safety_validation, manifest_validation


class LiveProviderBlindCandidateSafetyTests(unittest.TestCase):
    def test_path_safety_enforced(self) -> None:
        doc = {"files": [{"path": "../bad.py", "content": "print('bad')"}]}
        result = manifest_validation("live_provider_unit_converter_cli", doc)
        self.assertFalse(result["manifest_valid"])
        self.assertFalse(result["paths_safe"])

    def test_safety_scan_rejects_unsafe_code(self) -> None:
        result = candidate_safety_validation({"unit_converter.py": "eval('bad')\n"})
        self.assertFalse(result["passed"])
        self.assertIn("forbidden_token", result["rows"][0]["reason"])


if __name__ == "__main__":
    unittest.main()
