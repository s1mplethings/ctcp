from __future__ import annotations

import json
import subprocess
import sys
import unittest

try:
    from tests.non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests
except ModuleNotFoundError:
    from non_web_project_matrix.validators.direct_checks import materialize_non_web_project, project_env, run_project_tests


class TextUtilsPackageGenerationTests(unittest.TestCase):
    def test_text_utils_package_imports_and_tests_pass(self) -> None:
        temp, project, contract = materialize_non_web_project("text_utils_package")
        self.addCleanup(temp.cleanup)
        self.assertEqual(contract["project_id"], "text_utils_package")
        self.assertEqual(contract["project_root"], "project_output/text_utils_package")
        self.assertFalse((project / "run_agent.py").exists())
        self.assertFalse((project / "runtime").exists())
        tests = run_project_tests(project)
        self.assertEqual(tests.returncode, 0, tests.stdout + tests.stderr)
        snippet = (
            "import json; from text_utils import slugify, word_count, extract_keywords, normalize_whitespace; "
            "print(json.dumps({'slug': slugify('Hello, CTCP World!'), 'words': word_count('one two two'), "
            "'keywords': extract_keywords('The quick brown fox jumps quick'), "
            "'norm': normalize_whitespace('  a\\n b\\t c  ')}))"
        )
        proc = subprocess.run(
            [sys.executable, "-c", snippet],
            cwd=project,
            env=project_env(project),
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["slug"], "hello-ctcp-world")
        self.assertEqual(payload["words"], 3)
        self.assertIn("quick", payload["keywords"])
        self.assertEqual(payload["norm"], "a b c")


if __name__ == "__main__":
    unittest.main()
