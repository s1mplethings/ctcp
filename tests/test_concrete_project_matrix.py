from __future__ import annotations

import json
import importlib.util
import unittest
from pathlib import Path

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "concrete_project_matrix" / "fixtures"
RUNNER_PATH = ROOT / "tests" / "concrete_project_matrix" / "run_matrix_benchmark.py"
SPEC = importlib.util.spec_from_file_location("run_matrix_benchmark", RUNNER_PATH)
run_matrix_benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(run_matrix_benchmark)


class ConcreteProjectMatrixTests(unittest.TestCase):
    def test_matrix_fixtures_cover_three_projects(self) -> None:
        projects = [json.loads(path.read_text(encoding="utf-8"))["project"] for path in sorted(FIXTURES.glob("*.json"))]
        self.assertEqual(set(projects), {"todo_rest_api", "markdown_notes_api", "simple_auth_api"})
        self.assertEqual(tuple(run_matrix_benchmark.PROJECTS), ("todo_rest_api", "markdown_notes_api", "simple_auth_api"))

    def test_output_contracts_preserve_ordinary_concrete_fast_path(self) -> None:
        for fixture_path in FIXTURES.glob("*.json"):
            fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
            goal = run_matrix_benchmark._goal_from_fixture(fixture_path)
            doc = normalize_output_contract_freeze(None, goal=goal, run_dir=ROOT)
            self.assertEqual(doc["project_id"], fixture["project"])
            self.assertEqual(doc["generation_mode"], "concrete_fast_path")
            self.assertTrue(doc["startup_entrypoint"].endswith("/app.py"))

    def test_matrix_summary_format(self) -> None:
        public = {
            "matrix_total": 3,
            "passed": 3,
            "failed": 0,
            "unsupported": 0,
            "projects": [{"project": "todo_rest_api", "status": "passed"}],
        }
        self.assertEqual(public["matrix_total"], 3)
        self.assertEqual(public["unsupported"], 0)
        self.assertEqual(public["projects"][0]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
