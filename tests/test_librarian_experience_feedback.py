from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.librarian_experience import build_librarian_experience_record, write_librarian_experience_feedback
from tools.librarian_retrieval import build_hybrid_retrieval, selected_context_from_trace


class LibrarianExperienceFeedbackTests(unittest.TestCase):
    def test_blocked_report_writes_retrievable_experience_record(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_experience_") as td:
            run_dir = Path(td)
            report = {
                "stage": "source_generation",
                "status": "blocked",
                "project_domain": "vn_project_assistant",
                "scaffold_family": "cli_app",
                "library_plan_path": "artifacts/library_plan.json",
                "file_manifest_path": "artifacts/file_manifest.json",
                "model_budget_path": "artifacts/model_budget.json",
                "blocking_reason": "production source generation lacks provider-authored business files",
                "generic_validation": {"passed": False, "reasons": ["startup probe failed"]},
                "library_usage_verification": {"passed": False, "reasons": ["typer import missing"]},
            }

            feedback = write_librarian_experience_feedback(run_dir=run_dir, report=report)

            record_path = run_dir / feedback["record_path"]
            recipe_path = run_dir / feedback["recipe_path"]
            self.assertTrue(record_path.exists())
            self.assertTrue(recipe_path.exists())
            record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(record["schema_version"], "ctcp-librarian-experience-record-v1")
            self.assertIn("library_usage_verification", record["retrieval_text"])
            trace = build_hybrid_retrieval(
                repo_root=run_dir,
                query="source_generation vn typer provider-authored repair library usage",
                task_type="source_generation",
                project_domain="vn_project_assistant",
            )
            selected = selected_context_from_trace(trace)
            self.assertTrue(any(row["source"] == "artifacts/librarian_experience_record.json" for row in selected))

    def test_success_record_preserves_library_first_lesson(self) -> None:
        record = build_librarian_experience_record(
            report={
                "stage": "source_generation",
                "status": "pass",
                "project_domain": "cli_app",
                "scaffold_family": "single_package_cli_app",
                "library_plan_path": "artifacts/library_plan.json",
                "file_manifest_path": "artifacts/file_manifest.json",
            }
        )

        self.assertEqual(record["status"], "pass")
        self.assertTrue(any("library_plan" in lesson for lesson in record["lessons"]))
        self.assertIn("source_generation experience", record["retrieval_text"])


if __name__ == "__main__":
    unittest.main()
