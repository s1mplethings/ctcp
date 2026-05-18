from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.providers.project_generation_fast_path_registry import detect_fast_path
from tools.providers.project_generation_live_full_candidate import BLIND_CANDIDATE_PROJECTS


SUMMARY = Path("tests/live_provider_blind_matrix/generated/live_provider_blind_matrix_summary.json")


def load_summary() -> dict:
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


class LiveProviderBlindMatrixTests(unittest.TestCase):
    def test_blind_matrix_summary_runs_all_fixtures(self) -> None:
        summary = load_summary()
        self.assertEqual(summary["status"], "passed")
        self.assertEqual(summary["case_count"], 5)
        self.assertEqual({row["project"] for row in summary["cases"]}, set(BLIND_CANDIDATE_PROJECTS))

    def test_blind_projects_route_to_provider_candidate_family(self) -> None:
        match = detect_fast_path("Generate live_provider_blind_candidate live_provider_unit_converter_cli")
        self.assertIsNotNone(match)
        self.assertEqual(match.family, "live_provider_blind_candidate")

    def test_no_agent_scaffold_artifacts_in_outputs(self) -> None:
        for row in load_summary()["cases"]:
            self.assertTrue(row["no_agent_scaffold"], row["project"])
            project_dir = Path(row["project_dir"])
            self.assertFalse((project_dir / "run_agent.py").exists())
            self.assertFalse((project_dir / "runtime").exists())


if __name__ == "__main__":
    unittest.main()
