from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers.project_generation_model_budget import (
    build_model_budget,
    choose_model_tier,
    write_model_budget_artifact,
)


class ProjectGenerationModelBudgetTests(unittest.TestCase):
    def test_stage_policy_uses_strong_only_for_uncertainty(self) -> None:
        self.assertEqual(choose_model_tier(stage="intent_director")["tier"], "tier_3_strong")
        self.assertEqual(choose_model_tier(stage="library_plan")["tier"], "tier_2_medium")
        self.assertEqual(choose_model_tier(stage="file_author")["tier"], "tier_1_cheap")
        self.assertEqual(choose_model_tier(stage="validation")["tier"], "tier_0_local")

    def test_same_file_failed_twice_escalates_file_author(self) -> None:
        choice = choose_model_tier(
            stage="file_author",
            file_task={"path": "project_output/vn/src/vn/cli.py", "primary_libraries": ["typer"]},
            failure_count=2,
        )

        self.assertEqual(choice["tier"], "tier_2_medium")
        self.assertTrue(choice["escalated"])
        self.assertEqual(choice["reason"], "same_file_failed_twice")
        self.assertEqual(choice["path"], "project_output/vn/src/vn/cli.py")

    def test_budget_artifact_records_file_tasks(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_model_budget_") as td:
            run_dir = Path(td)
            budget = write_model_budget_artifact(
                run_dir=run_dir,
                file_tasks=[
                    {
                        "path": "project_output/vn/src/vn/models.py",
                        "implementation_mode": "library_glue",
                        "primary_libraries": ["pydantic"],
                    }
                ],
            )

            path = run_dir / "artifacts" / "model_budget.json"
            self.assertTrue(path.exists())
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(doc["schema_version"], "ctcp-model-budget-v1")
            self.assertEqual(budget["path"], "artifacts/model_budget.json")
            file_choices = [row for row in doc["stage_choices"] if row.get("stage") == "file_author"]
            self.assertEqual(file_choices[0]["tier"], "tier_1_cheap")
            self.assertEqual(file_choices[0]["primary_libraries"], ["pydantic"])

    def test_build_model_budget_accepts_extra_chunked_choices(self) -> None:
        budget = build_model_budget(extra_stage_choices=[{"stage": "file_author", "tier": "tier_1_cheap", "reason": "chunked_batch"}])

        self.assertTrue(any(row.get("reason") == "chunked_batch" for row in budget["stage_choices"]))


if __name__ == "__main__":
    unittest.main()
