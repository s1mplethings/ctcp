from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "tests" / "non_web_project_matrix" / "run_non_web_matrix.py"
SUMMARY = ROOT / "tests" / "non_web_project_matrix" / "generated" / "non_web_matrix_summary.json"


class NonWebProjectMatrixTests(unittest.TestCase):
    def test_non_web_matrix_runs_all_fixtures(self) -> None:
        if not SUMMARY.exists():
            result = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT, capture_output=True, text=True, timeout=900)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        if summary.get("passed") != 4:
            result = subprocess.run([sys.executable, str(RUNNER)], cwd=ROOT, capture_output=True, text=True, timeout=900)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        self.assertEqual(summary["matrix_total"], 4)
        self.assertEqual(summary["passed"], 4)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(
            {row["project"] for row in summary["projects"]},
            {"csv_expense_analyzer", "log_analyzer_cli", "text_utils_package", "terminal_quiz_game"},
        )
        for row in summary["projects"]:
            with self.subTest(project=row["project"]):
                self.assertTrue(row["ordinary_mainline"])
                self.assertTrue(row["no_agent_scaffold"])
                self.assertTrue(row["generated_tests_passed"])
                self.assertTrue(row["runtime_validation"]["passed"])
                self.assertTrue(row["attribution"]["ordinary_mainline"])
                self.assertFalse(row["attribution"]["used_agent_project"])
                self.assertFalse(row["attribution"]["used_agent_scaffold"])


if __name__ == "__main__":
    unittest.main()
