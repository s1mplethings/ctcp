from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

try:
    from tests.non_web_project_matrix import run_non_web_matrix
except ModuleNotFoundError:
    from non_web_project_matrix import run_non_web_matrix


class ReviewPackGenerationTests(unittest.TestCase):
    def test_review_pack_includes_required_review_fields(self) -> None:
        summary = {
            "matrix_total": 1,
            "passed": 1,
            "failed": 0,
            "unsupported": 0,
            "projects": [
                {
                    "project": "csv_expense_analyzer",
                    "status": "passed",
                    "attribution": {
                        "ordinary_mainline": True,
                        "used_agent_project": False,
                        "used_agent_scaffold": False,
                        "used_local_agent_runtime": False,
                        "used_local_materializer": True,
                        "provider_authorship": "not_claimed",
                    },
                }
            ],
        }
        with tempfile.TemporaryDirectory(prefix="ctcp_review_pack_") as temp:
            original = run_non_web_matrix.REVIEW_PACK
            run_non_web_matrix.REVIEW_PACK = Path(temp) / "REVIEW_PACK.md"
            try:
                run_non_web_matrix._write_review_pack(summary)
                self.assertTrue(run_non_web_matrix.REVIEW_PACK.exists())
                text = run_non_web_matrix.REVIEW_PACK.read_text(encoding="utf-8")
            finally:
                run_non_web_matrix.REVIEW_PACK = original
        self.assertIn("CTCP Phase 15 Review Pack", text)
        self.assertIn("Modified Files", text)
        self.assertIn("Benchmark Summary", text)
        self.assertIn("Risks For Human Review", text)
        self.assertIn("csv_expense_analyzer", text)
        self.assertIn("used_agent_project", text)
        self.assertIn("not_claimed", text)
        self.assertLessEqual(len(text.splitlines()), 250)


if __name__ == "__main__":
    unittest.main()
