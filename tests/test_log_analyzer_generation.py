from __future__ import annotations

import json
import subprocess
import sys
import unittest

try:
    from tests.non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests
except ModuleNotFoundError:
    from non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests


class LogAnalyzerGenerationTests(unittest.TestCase):
    def test_log_analyzer_cli_and_tests_pass(self) -> None:
        temp, project, contract = materialize_non_web_project("log_analyzer_cli")
        self.addCleanup(temp.cleanup)
        self.assertEqual(contract["project_id"], "log_analyzer_cli")
        self.assertEqual(contract["project_root"], "project_output/log_analyzer_cli")
        self.assertFalse((project / "run_agent.py").exists())
        self.assertFalse((project / "runtime").exists())
        tests = run_project_tests(project)
        self.assertEqual(tests.returncode, 0, tests.stdout + tests.stderr)
        output = project / "summary.json"
        cli = subprocess.run(
            [sys.executable, "log_analyzer.py", "--input", "sample.log", "--output", str(output)],
            cwd=project,
            env=project_env(project),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        summary = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(summary["level_counts"]["INFO"], 1)
        self.assertEqual(summary["level_counts"]["WARN"], 1)
        self.assertEqual(summary["level_counts"]["ERROR"], 2)
        self.assertEqual(summary["top_errors"][0]["message"], "disk full")


if __name__ == "__main__":
    unittest.main()
