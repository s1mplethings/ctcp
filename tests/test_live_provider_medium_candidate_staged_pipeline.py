from __future__ import annotations

import unittest

from tools.providers.project_generation_medium_candidate import (
    MEDIUM_CANDIDATE_PROJECTS,
    medium_file_batches,
    medium_project_contract,
    medium_plan_prompt,
    normalize_medium_plan,
)


class LiveProviderMediumCandidateStagedPipelineTests(unittest.TestCase):
    def test_plan_prompt_and_validation_cover_required_files(self) -> None:
        project = "live_provider_inventory_manager_app"
        prompt = medium_plan_prompt(project, "build inventory")
        self.assertIn("Stage 1", prompt)
        self.assertIn("file_manifest", prompt)
        plan, validation = normalize_medium_plan(
            project,
            {
                "project_name": project,
                "project_type": "fullstack_local_app",
                "architecture": "http.server plus sqlite",
                "data_model": ["Product"],
                "api_routes": ["/products"],
                "frontend_features": ["list products"],
                "test_plan": ["store tests"],
                "file_manifest": [item for batch in medium_file_batches(project) for item in batch],
            },
        )
        self.assertTrue(validation["provider_plan_valid"])
        self.assertTrue(validation["provider_manifest_valid"])
        self.assertEqual(validation["provider_manifest_file_count"], 7)
        self.assertIn("app.py", plan["file_manifest"])

    def test_phase22_medium_cases_are_registered(self) -> None:
        self.assertIn("live_provider_event_booking_app", MEDIUM_CANDIDATE_PROJECTS)
        self.assertIn("live_provider_invoice_manager_app", MEDIUM_CANDIDATE_PROJECTS)
        for project in ("live_provider_event_booking_app", "live_provider_invoice_manager_app"):
            contract = medium_project_contract(project)
            self.assertIn("app.py", contract["required_files"])
            self.assertGreaterEqual(len(contract["routes"]), 7)


if __name__ == "__main__":
    unittest.main()
