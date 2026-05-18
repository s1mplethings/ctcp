from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_business_materializers import materialize_business_files
from tools.providers.project_generation_contracts import write_generation_contract_artifacts


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "concrete_project_benchmark" / "fixtures" / "issue_tracker_api.json"


def _goal_from_fixture() -> str:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    endpoints = ", ".join(str(item) for item in fixture["project_requirements"]["api"]["required_endpoints"])
    statuses = ", ".join(str(item) for item in fixture["project_requirements"]["issue_model"]["valid_statuses"])
    return (
        f"{fixture['goal']} Required endpoints: {endpoints}. "
        f"Use SQLite persistence. Valid issue statuses: {statuses}. "
        "Generate the concrete project files, tests, README, runnable local HTTP server, and delivery package."
    )


def _materialize_issue_tracker_project() -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
    temp = tempfile.TemporaryDirectory(prefix="ctcp_issue_tracker_contract_")
    run_dir = Path(temp.name)
    goal = _goal_from_fixture()
    contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
    materialize_business_files(run_dir, goal, contract, ["test context"])
    write_generation_contract_artifacts(
        run_dir,
        project_root=str(contract["project_root"]),
        entrypoint=str(contract["startup_entrypoint"]),
        repair=True,
    )
    return temp, run_dir / str(contract["project_root"]), contract


class IssueTrackerGenerationContractTests(unittest.TestCase):
    def test_generated_project_is_not_agent_scaffold(self) -> None:
        temp, project, _contract = _materialize_issue_tracker_project()
        self.addCleanup(temp.cleanup)

        self.assertTrue((project / "README.md").exists())
        self.assertTrue((project / "app.py").exists())
        self.assertTrue((project / "issue_store.py").exists())
        self.assertFalse((project / "run_agent.py").exists())
        self.assertFalse((project / "agent_manifest.json").exists())

    def test_generated_routes_include_issue_tracker_endpoints(self) -> None:
        temp, project, _contract = _materialize_issue_tracker_project()
        self.addCleanup(temp.cleanup)
        run_dir = project.parents[1]
        routes = json.loads((run_dir / "artifacts" / "generated_routes.json").read_text(encoding="utf-8"))
        route_keys = {f"{row['method']} {row['path']}" for row in routes["routes"]}

        self.assertIn("POST /issues", route_keys)
        self.assertIn("GET /issues", route_keys)
        self.assertIn("GET /issues/{id}", route_keys)
        self.assertIn("PATCH /issues/{id}/status", route_keys)
        self.assertIn("POST /issues/{id}/close", route_keys)

    def test_generated_tests_pass(self) -> None:
        temp, project, _contract = _materialize_issue_tracker_project()
        self.addCleanup(temp.cleanup)
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-v"],
            cwd=project,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
