from __future__ import annotations

import unittest

from tools.providers.project_generation_live_full_candidate import safety_scan


class LiveProviderFullCandidateSafetyTests(unittest.TestCase):
    def test_rejects_eval_exec_subprocess_network_tokens(self) -> None:
        scan = safety_scan(
            {
                "main.py": "eval('bad')\n",
                "other.py": "import subprocess\n",
                "net.py": "import urllib.request\n",
            }
        )
        self.assertFalse(scan["passed"])
        reasons = " ".join(row["reason"] for row in scan["rows"])
        self.assertIn("eval(", reasons)
        self.assertIn("subprocess", reasons)
        self.assertIn("urllib", reasons)

    def test_allows_plain_stdlib_logic(self) -> None:
        scan = safety_scan({"main.py": "def add(a, b):\n    return a + b\n"})
        self.assertTrue(scan["passed"])


if __name__ == "__main__":
    unittest.main()

