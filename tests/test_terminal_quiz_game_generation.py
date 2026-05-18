from __future__ import annotations

import json
import subprocess
import sys
import unittest

try:
    from tests.non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests
except ModuleNotFoundError:
    from non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests


class TerminalQuizGameGenerationTests(unittest.TestCase):
    def test_terminal_quiz_game_test_mode_and_tests_pass(self) -> None:
        temp, project, contract = materialize_non_web_project("terminal_quiz_game")
        self.addCleanup(temp.cleanup)
        self.assertEqual(contract["project_id"], "terminal_quiz_game")
        self.assertEqual(contract["project_root"], "project_output/terminal_quiz_game")
        self.assertFalse((project / "run_agent.py").exists())
        self.assertFalse((project / "runtime").exists())
        tests = run_project_tests(project)
        self.assertEqual(tests.returncode, 0, tests.stdout + tests.stderr)
        cli = subprocess.run(
            [sys.executable, "quiz_game.py", "--questions", "sample_questions.json", "--test-mode", "--answers", "B,A"],
            cwd=project,
            env=project_env(project),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(cli.returncode, 0, cli.stdout + cli.stderr)
        payload = json.loads(cli.stdout)
        self.assertEqual(payload["score"], 2)
        self.assertEqual(payload["total"], 2)


if __name__ == "__main__":
    unittest.main()
