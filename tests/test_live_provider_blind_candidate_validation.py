from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.providers.project_generation_blind_candidate import blind_candidate_files
from tools.providers.project_generation_live_full_candidate import validate_candidate_runtime

SUMMARY = Path("tests/live_provider_blind_matrix/generated/live_provider_blind_matrix_summary.json")


class LiveProviderBlindCandidateValidationTests(unittest.TestCase):
    def test_generated_tests_and_runtime_validators_pass(self) -> None:
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        for row in summary["cases"]:
            self.assertEqual(row["generated_tests"]["exit_code"], 0, row["project"])
            self.assertTrue(row["runtime_validation"]["passed"], row["project"])

    def test_project_specific_validator_layer_accepts_baselines(self) -> None:
        for project in (
            "live_provider_unit_converter_cli",
            "live_provider_file_renamer_cli",
            "live_provider_markdown_table_formatter",
            "live_provider_json_config_validator",
            "live_provider_static_site_generator",
        ):
            result = validate_candidate_runtime(project, blind_candidate_files(project))
            self.assertTrue(result["generated_tests_passed"], project)
            self.assertTrue(result["runtime_validation_passed"], project)


if __name__ == "__main__":
    unittest.main()
