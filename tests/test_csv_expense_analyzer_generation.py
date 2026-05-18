from __future__ import annotations

import json
import subprocess
import sys
import unittest

try:
    from tests.non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests
except ModuleNotFoundError:
    from non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests


class CsvExpenseAnalyzerGenerationTests(unittest.TestCase):
    def test_csv_expense_analyzer_cli_and_tests_pass(self) -> None:
        temp, project, contract = materialize_non_web_project("csv_expense_analyzer")
        self.addCleanup(temp.cleanup)
        self.assertEqual(contract["project_id"], "csv_expense_analyzer")
        self.assertEqual(contract["project_root"], "project_output/csv_expense_analyzer")
        self.assertFalse((project / "run_agent.py").exists())
        self.assertFalse((project / "runtime").exists())
        tests = run_project_tests(project)
        self.assertEqual(tests.returncode, 0, tests.stdout + tests.stderr)
        output = project / "report.json"
        cli = subprocess.run(
            [sys.executable, "expense_analyzer.py", "--input", "sample_expenses.csv", "--output", str(output)],
            cwd=project,
            env=project_env(project),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["row_count"], 3)
        self.assertAlmostEqual(report["category_totals"]["Food"], 20.0)
        self.assertAlmostEqual(report["monthly_totals"]["2026-01"], 32.5)


if __name__ == "__main__":
    unittest.main()
