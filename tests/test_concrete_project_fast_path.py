from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.providers import api_agent
from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_business_materializers import materialize_business_files


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


class ConcreteProjectFastPathTests(unittest.TestCase):
    def test_issue_tracker_goal_uses_concrete_fast_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_fast_path_contract_") as td:
            doc = normalize_output_contract_freeze(None, goal=_goal_from_fixture(), run_dir=Path(td))

        self.assertEqual(doc["generation_mode"], "concrete_fast_path")
        self.assertEqual(doc["project_root"], "project_output/local_issue_tracker_api")
        self.assertEqual(doc["startup_entrypoint"], "project_output/local_issue_tracker_api/app.py")
        self.assertIn("project_output/local_issue_tracker_api/issue_store.py", doc["business_files"])

    def test_fast_path_only_matches_issue_tracker_api_goal(self) -> None:
        goal = "Generate a local notes API with README, tests, and SQLite persistence."
        with tempfile.TemporaryDirectory(prefix="ctcp_fast_path_negative_") as td:
            doc = normalize_output_contract_freeze(None, goal=goal, run_dir=Path(td))

        self.assertNotEqual(doc["generation_mode"], "concrete_fast_path")
        self.assertNotEqual(doc["project_root"], "project_output/local_issue_tracker_api")

    def test_fast_path_records_local_materializer_provenance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_fast_path_materialize_") as td:
            run_dir = Path(td)
            goal = _goal_from_fixture()
            contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
            materialize_business_files(run_dir, goal, contract, ["test context"])
            provenance = json.loads((run_dir / contract["project_root"] / "provenance.json").read_text(encoding="utf-8"))

        self.assertEqual(provenance["generation_mode"], "concrete_fast_path")
        self.assertEqual(provenance["provider_authorship"], "not_claimed")
        self.assertTrue(provenance["local_materializer_used"])

    def test_fast_path_source_generation_runs_inside_api_provider_stage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_fast_path_source_stage_") as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            goal = _goal_from_fixture()
            contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
            (artifacts / "output_contract_freeze.json").write_text(json.dumps(contract), encoding="utf-8")
            (artifacts / "context_pack.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-context-pack-v1",
                        "goal": goal,
                        "files": [
                            {
                                "path": "tests/concrete_project_benchmark/fixtures/issue_tracker_api.json",
                                "why": "concrete project benchmark contract",
                                "content": goal,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = api_agent.execute(
                repo_root=Path.cwd(),
                run_dir=run_dir,
                request={
                    "role": "chair",
                    "action": "source_generation",
                    "target_path": "artifacts/source_generation_report.json",
                    "goal": goal,
                },
                config={},
                guardrails_budgets={},
            )
            report = json.loads((artifacts / "source_generation_report.json").read_text(encoding="utf-8"))

        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["provider_mode"], "local_materializer")
        self.assertEqual(report["generation_mode"], "concrete_fast_path")
        self.assertEqual(report["concrete_fast_path_provenance"]["provider_authorship"], "not_claimed")
        self.assertIn("project_output/local_issue_tracker_api/app.py", report["generated_files"])


if __name__ == "__main__":
    unittest.main()
