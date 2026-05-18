from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

try:
    from tests.non_web_project_matrix import run_non_web_matrix
except ModuleNotFoundError:
    from non_web_project_matrix import run_non_web_matrix
from tools.providers.project_generation_attribution import build_generation_attribution, write_generation_attribution


class GenerationAttributionReportTests(unittest.TestCase):
    def test_generation_attribution_json_has_required_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_attribution_") as temp:
            run_dir = Path(temp)
            provenance = {
                "generation_mode": "concrete_fast_path",
                "project_type": "csv_expense_analyzer",
                "provider_authorship": "not_claimed",
                "local_materializer_used": True,
            }
            attribution = write_generation_attribution(
                run_dir=run_dir,
                project_id="csv_expense_analyzer",
                project_root="project_output/csv_expense_analyzer",
                provenance=provenance,
            )
            path = run_dir / "artifacts" / "generation_attribution.json"
            self.assertTrue(path.exists())
            persisted = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(persisted, attribution)
            self.assertTrue(attribution["ordinary_mainline"])
            self.assertEqual(attribution["entrypoint"], "new-run/status/advance")
            self.assertFalse(attribution["used_agent_project"])
            self.assertFalse(attribution["used_agent_scaffold"])
            self.assertFalse(attribution["used_local_agent_runtime"])
            self.assertTrue(attribution["used_local_materializer"])
            self.assertEqual(attribution["provider_authorship"], "not_claimed")
            self.assertEqual(attribution["analysis_path"], "artifacts/analysis.md")

    def test_benchmark_report_includes_attribution_section(self) -> None:
        attribution = build_generation_attribution(
            run_dir=Path("run"),
            project_id="csv_expense_analyzer",
            project_root="project_output/csv_expense_analyzer",
            provenance={
                "generation_mode": "concrete_fast_path",
                "project_type": "csv_expense_analyzer",
                "provider_authorship": "not_claimed",
                "local_materializer_used": True,
            },
        )
        summary = {
            "matrix_total": 1,
            "passed": 1,
            "failed": 0,
            "projects": [
                {
                    "project": "csv_expense_analyzer",
                    "status": "passed",
                    "project_dir": "project_output/csv_expense_analyzer",
                    "generated_tests_passed": True,
                    "runtime_validation": {"passed": True},
                    "ordinary_mainline": True,
                    "provenance_path": "artifacts/project_generation_provenance.json",
                    "attribution_path": "artifacts/generation_attribution.json",
                    "attribution": attribution,
                }
            ],
        }
        with tempfile.TemporaryDirectory(prefix="ctcp_report_") as temp:
            original = run_non_web_matrix.REPORT
            run_non_web_matrix.REPORT = Path(temp) / "benchmark_report.md"
            try:
                run_non_web_matrix._write_report(summary)
                report = run_non_web_matrix.REPORT.read_text(encoding="utf-8")
            finally:
                run_non_web_matrix.REPORT = original
        self.assertIn("## Attribution", report)
        self.assertIn("used_agent_project", json.dumps(attribution))
        self.assertIn("csv_expense_analyzer", report)


if __name__ == "__main__":
    unittest.main()
