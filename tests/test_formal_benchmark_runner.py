from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import formal_benchmark_runner as runner


class FormalBenchmarkRunnerEnduranceTests(unittest.TestCase):
    def _write_json(self, path: Path, data: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def _make_endurance_run(self, root: Path) -> tuple[Path, Path]:
        run_dir = root / "ctcp" / "20260424-200630-107859-orchestrate"
        support_dir = root / "ctcp" / "support_sessions" / "indie-studio-endurance-sanitized-20260424"
        screenshots_dir = run_dir / "project_output" / "5-20-bug" / "artifacts" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        self._write_json(run_dir / "RUN.json", {"status": "pass", "goal": runner.ENDURANCE_GOAL})
        self._write_json(
            support_dir / "artifacts" / "support_session_state.json",
            {
                "bound_run_id": run_dir.name,
                "bound_run_dir": str(run_dir),
            },
        )
        (run_dir / "api_calls.jsonl").write_text(
            json.dumps({"status": "OK", "request_id": "req_1"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        self._write_json(
            run_dir / "artifacts" / "find_result.json",
            {
                "selected_workflow_id": "wf_project_generation_manifest",
                "decision": {"project_generation_goal": True},
            },
        )
        self._write_json(
            run_dir / "artifacts" / "project_spec.json",
            {
                "project_domain": "indie_studio_production_hub",
                "project_type": "indie_studio_hub",
                "project_archetype": "indie_studio_hub_web",
                "build_profile": "high_quality_extended",
                "product_depth": "extended",
                "required_pages": 13,
                "required_screenshots": 10,
                "package_name": "project_5_20_bug",
            },
        )
        self._write_json(
            run_dir / "artifacts" / "output_contract_freeze.json",
            {
                "project_domain": "indie_studio_production_hub",
                "project_type": "indie_studio_hub",
                "project_archetype": "indie_studio_hub_web",
                "build_profile": "high_quality_extended",
                "product_depth": "extended",
                "required_pages": 13,
                "required_screenshots": 10,
                "package_name": "project_5_20_bug",
            },
        )
        self._write_json(
            run_dir / "artifacts" / "source_generation_report.json",
            {
                "status": "pass",
                "package_name": "project_5_20_bug",
                "generic_validation": {
                    "passed": True,
                    "python_syntax": {"passed": True},
                },
            },
        )
        self._write_json(run_dir / "artifacts" / "project_manifest.json", {"package_name": "project_5_20_bug"})
        self._write_json(
            run_dir / "artifacts" / "deliverable_index.json",
            {
                "final_package_path": "artifacts/final_project_bundle.zip",
                "evidence_bundle_path": "artifacts/intermediate_evidence_bundle.zip",
            },
        )
        self._write_json(run_dir / "artifacts" / "verify_report.json", {"result": "PASS"})
        self._write_json(
            run_dir / "artifacts" / "support_public_delivery.json",
            {
                "completion_gate": {
                    "passed": True,
                    "cold_replay_passed": True,
                    "replay_report_path": "artifacts/delivery_replay/replay_report.json",
                    "replay_screenshot_path": "artifacts/delivery_replay/replayed.png",
                },
                "overall_completion": {"passed": True},
                "replay_report": {
                    "overall_pass": True,
                    "startup_pass": True,
                    "minimal_flow_pass": True,
                    "report_path": "artifacts/delivery_replay/replay_report.json",
                    "replay_screenshot_path": "artifacts/delivery_replay/replayed.png",
                    "first_failure_stage": "",
                },
                "internal_runtime_status": "PASS",
                "user_acceptance_status": "PASS",
            },
        )
        (run_dir / "artifacts" / "provider_ledger.jsonl").write_text(
            "\n".join(
                [
                    json.dumps(
                        {
                            "role": "chair",
                            "action": "output_contract_freeze",
                            "provider_used": "api_agent",
                            "external_api_used": True,
                            "request_id": "req_freeze",
                            "fallback_used": False,
                            "local_function_used": "",
                            "status": "executed",
                            "verdict": "api_executed",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "role": "chair",
                            "action": "source_generation",
                            "provider_used": "api_agent",
                            "external_api_used": True,
                            "request_id": "req_source",
                            "fallback_used": False,
                            "local_function_used": "",
                            "status": "executed",
                            "verdict": "api_executed",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "role": "chair",
                            "action": "artifact_manifest_build",
                            "provider_used": "api_agent",
                            "external_api_used": True,
                            "request_id": "req_manifest",
                            "fallback_used": False,
                            "local_function_used": "",
                            "status": "executed",
                            "verdict": "api_executed",
                        },
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        {
                            "role": "chair",
                            "action": "deliver",
                            "provider_used": "api_agent",
                            "external_api_used": True,
                            "request_id": "req_deliver",
                            "fallback_used": False,
                            "local_function_used": "",
                            "status": "executed",
                            "verdict": "api_executed",
                        },
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        acceptance_dir = run_dir / "artifacts" / "acceptance" / "20260424T200946_chair_output_contract_freeze"
        self._write_json(acceptance_dir / "request.json", {"step": "chair_output_contract_freeze"})
        self._write_json(acceptance_dir / "result.json", {"passed": True, "fallback_used": False})
        self._write_json(acceptance_dir / "acceptance.json", {"passed": True})
        (run_dir / "artifacts" / "acceptance" / "ledger.jsonl").write_text(
            json.dumps({"step": "chair_output_contract_freeze", "passed": True}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        screenshot_files = []
        for name in [
            "final-ui.png",
            "02-project_list.png",
            "03-project_overview.png",
            "04-milestone_backlog.png",
            "05-task_board.png",
            "06-task_list.png",
            "07-task_detail.png",
            "08-asset_library.png",
            "09-asset_detail.png",
            "10-bug_tracker.png",
        ]:
            path = screenshots_dir / name
            path.write_bytes(b"png")
            screenshot_files.append(f"project_output/5-20-bug/artifacts/screenshots/{name}")
        self._write_json(
            run_dir / "artifacts" / "extended_coverage_ledger.json",
            {
                "passed": True,
                "implemented_pages": [
                    "dashboard",
                    "project_list",
                    "project_overview",
                    "milestone_backlog",
                    "task_board",
                    "task_list",
                    "task_detail",
                    "asset_library",
                    "asset_detail",
                    "bug_tracker",
                    "build_release_center",
                    "activity_feed",
                    "docs_center",
                    "project_settings",
                ],
                "documentation_files": [
                    "project_output/5-20-bug/docs/feature_matrix.md",
                    "project_output/5-20-bug/docs/page_map.md",
                    "project_output/5-20-bug/docs/data_model_summary.md",
                    "project_output/5-20-bug/docs/milestone_plan.md",
                    "project_output/5-20-bug/docs/startup_guide.md",
                    "project_output/5-20-bug/docs/replay_guide.md",
                    "project_output/5-20-bug/docs/mid_stage_review.md",
                ],
                "screenshot_files": screenshot_files,
                "coverage": {
                    "pages": {"required": 13, "actual": 14, "passed": True},
                    "screenshots": {"required": 10, "actual": 10, "passed": True},
                    "feature_matrix": {"passed": True},
                    "page_map": {"passed": True},
                    "data_model_summary": {"passed": True},
                    "milestone_plan": {"passed": True},
                    "startup_guide": {"passed": True},
                    "replay_guide": {"passed": True},
                    "mid_stage_review": {"passed": True},
                    "search": {"passed": True},
                    "import_export": {"passed": True},
                    "dashboard_or_project_overview": {"passed": True},
                    "asset_library": {"passed": True},
                    "asset_detail": {"passed": True},
                    "bug_tracker": {"passed": True},
                    "build_release_center": {"passed": True},
                    "docs_center": {"passed": True},
                },
            },
        )
        (run_dir / "artifacts" / "final_project_bundle.zip").write_bytes(b"zip")
        (run_dir / "artifacts" / "intermediate_evidence_bundle.zip").write_bytes(b"zip")
        return run_dir, support_dir

    def test_build_summary_endurance_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, support_dir = self._make_endurance_run(Path(tmp))
            summary = runner.build_summary("endurance", run_dir)
            self.assertEqual(summary["verdict"], "PASS")
            self.assertEqual(summary["project_domain"], "indie_studio_production_hub")
            self.assertEqual(summary["package_name"], "project_5_20_bug")
            self.assertEqual(summary["support_session_dir"], str(support_dir))
            self.assertEqual(summary["internal_runtime_status"], "PASS")
            self.assertEqual(summary["user_acceptance_status"], "PASS")
            self.assertEqual(summary["extended_coverage_summary"]["screenshot_count"], 10)
            self.assertTrue(bool(summary["provider_ledger_summary"]["all_critical_steps_api"]))

    def test_build_summary_endurance_fails_without_provider_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, _ = self._make_endurance_run(Path(tmp))
            (run_dir / "artifacts" / "provider_ledger.jsonl").unlink()
            summary = runner.build_summary("endurance", run_dir)
            self.assertEqual(summary["verdict"], "FAIL")
            self.assertEqual(summary["first_failure_point"], "provider ledger critical steps are API")

    def test_archive_golden_endurance_copies_core_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir, _ = self._make_endurance_run(root)
            summary = runner.build_summary("endurance", run_dir)
            summary_json = root / "benchmark_endurance_summary.json"
            summary_md = root / "benchmark_endurance_summary.md"
            runner._write_json(summary_json, summary)
            runner._write_markdown_summary(summary, summary_md)
            golden_dir = runner.archive_golden("endurance", run_dir, summary_json, summary_md, root / "goldens")
            self.assertTrue((golden_dir / "output_contract_freeze.json").exists())
            self.assertTrue((golden_dir / "provider_ledger.jsonl").exists())
            self.assertTrue((golden_dir / "provider_ledger_summary.json").exists())
            self.assertTrue((golden_dir / "source_generation_report.json").exists())
            self.assertTrue((golden_dir / "project_manifest.json").exists())
            self.assertTrue((golden_dir / "deliverable_index.json").exists())
            self.assertTrue((golden_dir / "support_public_delivery.json").exists())
            self.assertTrue((golden_dir / "verify_report.json").exists())
            self.assertTrue((golden_dir / "final_project_bundle.zip").exists())
            self.assertTrue((golden_dir / "intermediate_evidence_bundle.zip").exists())
            self.assertTrue((golden_dir / "benchmark_endurance_summary.json").exists())
            self.assertTrue((golden_dir / "benchmark_endurance_summary.md").exists())
            screenshot_files = sorted((golden_dir / "screenshots").glob("*.png"))
            self.assertEqual(len(screenshot_files), 10)


if __name__ == "__main__":
    unittest.main()
