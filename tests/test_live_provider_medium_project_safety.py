from __future__ import annotations

import unittest

from tools.providers.project_generation_live_full_candidate import normalize_candidate_manifest, safety_scan


class LiveProviderMediumProjectSafetyTests(unittest.TestCase):
    def test_medium_path_safety_rejects_traversal(self) -> None:
        files, validation = normalize_candidate_manifest(
            "live_provider_inventory_manager_app",
            {"files": [{"path": "../app.py", "content": "print('bad')"}]},
        )
        self.assertFalse(validation["manifest_valid"])
        self.assertFalse(files)

    def test_medium_safety_scan_rejects_unsafe_code(self) -> None:
        result = safety_scan({"app.py": "import subprocess\n"})
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
