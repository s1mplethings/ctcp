#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_dispatch
import ctcp_orchestrate
import project_generation_gate
import resolve_workflow
from llm_core.providers import api_provider
from ctcp_adapters.ctcp_artifact_normalizers import _normalize_plan_md
from tools.providers.project_generation_artifacts import build_intermediate_evidence_bundle, normalize_output_contract_freeze, normalize_source_generation


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class PlaneLiteBenchmarkRegressionTests(unittest.TestCase):
    def test_plane_lite_goals_resolve_to_project_generation_lane(self) -> None:
        goals = [
            "Build a lightweight local-first task collaboration platform for a small team.",
            "给我们做一个轻量任务协作平台，本地优先，小团队用，像 Plane-lite / Focalboard-lite。",
        ]
        for goal in goals:
            with self.subTest(goal=goal):
                result = resolve_workflow.resolve(goal=goal, repo=ROOT)
                self.assertEqual(result.get("selected_workflow_id"), "wf_project_generation_manifest")
                self.assertTrue(bool(dict(result.get("decision", {})).get("project_generation_goal", False)))

    def test_route_mismatch_blocks_before_contract_review_approval(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "guardrails.md").write_text(
                "find_mode: resolver_only\nmax_files: 20\nmax_total_bytes: 200000\nmax_iterations: 3\n",
                encoding="utf-8",
            )
            (artifacts / "analysis.md").write_text("# analysis\n", encoding="utf-8")
            _write_json(
                artifacts / "find_result.json",
                {
                    "schema_version": "ctcp-find-result-v1",
                    "selected_workflow_id": "wf_project_generation_manifest",
                    "decision": {"project_generation_goal": False},
                },
            )
            gate = ctcp_orchestrate.current_gate(
                run_dir,
                {"goal": "Build a lightweight local-first task collaboration platform for a small team."},
            )
            self.assertEqual(gate.get("owner"), "Chair/Planner")
            self.assertEqual(gate.get("path"), "artifacts/file_request.json")
            self.assertIn("waiting for file_request.json", str(gate.get("reason", "")))

    def test_project_generation_plan_requires_delivery_evidence(self) -> None:
        thin_plan = "Status: DRAFT\nGoal: Build a lightweight local-first task collaboration platform.\n"
        self.assertFalse(project_generation_gate.plan_has_project_generation_delivery_requirements(thin_plan))

        normalized = _normalize_plan_md(
            "Status: DRAFT\n",
            signed=False,
            goal="Build a lightweight local-first task collaboration platform for a small team.",
        )
        self.assertTrue(project_generation_gate.plan_has_project_generation_delivery_requirements(normalized))
        self.assertIn("final_package", normalized)
        self.assertIn("final_screenshot", normalized)

    def test_plane_lite_output_contract_is_team_task_pm_not_generic_web_service(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            doc = normalize_output_contract_freeze(
                {},
                goal="Build a lightweight local-first task collaboration platform for a small team.",
                run_dir=run_dir,
            )
            self.assertEqual(doc.get("delivery_shape"), "web_first")
            self.assertEqual(doc.get("project_domain"), "team_task_management")
            self.assertEqual(doc.get("scaffold_family"), "team_task_pm")
            self.assertEqual(doc.get("project_type"), "team_task_pm")
            self.assertEqual(doc.get("project_archetype"), "team_task_pm_web")
            self.assertEqual(dict(doc.get("capability_plan", {})).get("family_key"), "team_task_pm_web")
            spec = dict(doc.get("project_spec", {}))
            self.assertIn("kanban_board", list(spec.get("required_pages_or_views", [])))
            self.assertIn("comment_on_task", list(spec.get("key_interactions", [])))
            self.assertIn("activity_feed", list(spec.get("required_pages_or_views", [])))
            self.assertIn("gantt or roadmap planning", list(spec.get("explicit_non_goals", [])))

    def test_indie_studio_hub_team_signal_is_not_downgraded_to_generic(self) -> None:
        goal = (
            "I want to create Indie Studio Production Hub. "
            "Rough user goal: I want a local collaboration platform for an indie game team of roughly 5 to 15 people, "
            "including designers, programmers, artists, and testers. I do not want only a normal task board. "
            "I want tasks, assets, bugs, and version progress together. "
            "Required independent docs include feature matrix, page map, and data model summary."
        )
        with tempfile.TemporaryDirectory() as td:
            doc = normalize_output_contract_freeze({}, goal=goal, run_dir=Path(td))
            self.assertEqual(doc.get("project_domain"), "indie_studio_production_hub")
            self.assertEqual(doc.get("scaffold_family"), "indie_studio_hub")
            self.assertEqual(doc.get("project_type"), "indie_studio_hub")
            self.assertEqual(doc.get("project_archetype"), "indie_studio_hub_web")
            self.assertEqual(doc.get("required_screenshots"), 10)
            spec = dict(doc.get("project_spec", {}))
            for view in ("asset_library", "asset_detail", "bug_tracker", "build_release_center", "docs_center"):
                self.assertIn(view, list(spec.get("required_pages_or_views", [])))
            for rel in ("docs/milestone_plan.md", "docs/startup_guide.md", "docs/replay_guide.md", "docs/mid_stage_review.md"):
                self.assertTrue(any(str(path).endswith(rel) for path in list(doc.get("doc_files", []))), rel)
            self.assertNotEqual(doc.get("project_type"), "generic_copilot")

    def test_patchmaker_exec_failure_does_not_dispatch_in_mainline(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _write_json(artifacts / "dispatch_config.json", ctcp_dispatch.default_dispatch_config_doc({"patchmaker": "api_agent"}))
            (artifacts / "guardrails.md").write_text(
                "max_files: 20\nmax_total_bytes: 200000\n",
                encoding="utf-8",
            )
            gate = {
                "state": "blocked",
                "owner": "PatchMaker",
                "path": "artifacts/diff.patch",
                "reason": "waiting for diff.patch",
            }
            original = ctcp_dispatch.core_router.dispatch_execute
            try:
                ctcp_dispatch.core_router.dispatch_execute = lambda **_: {
                    "status": "exec_failed",
                    "reason": "OpenAI API HTTP 403: Key usage limit exceeded",
                    "target_path": "artifacts/diff.patch",
                }
                result = ctcp_dispatch.dispatch_once(
                    run_dir,
                    {"goal": "repair fallback test"},
                    gate,
                    ROOT,
                )
            finally:
                ctcp_dispatch.core_router.dispatch_execute = original

            self.assertEqual(result.get("status"), "no_request")
            self.assertFalse((artifacts / "diff.patch").exists())

    def test_formal_api_only_patchmaker_exec_failure_still_has_no_request(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _write_json(artifacts / "dispatch_config.json", ctcp_dispatch.default_dispatch_config_doc({"patchmaker": "api_agent"}))
            gate = {
                "state": "blocked",
                "owner": "PatchMaker",
                "path": "artifacts/diff.patch",
                "reason": "waiting for diff.patch",
            }
            original = ctcp_dispatch.core_router.dispatch_execute
            old_formal = os.environ.get("CTCP_FORMAL_API_ONLY")
            os.environ["CTCP_FORMAL_API_ONLY"] = "1"
            try:
                ctcp_dispatch.core_router.dispatch_execute = lambda **_: {
                    "status": "exec_failed",
                    "reason": "OpenAI API HTTP 403: Key usage limit exceeded",
                    "target_path": "artifacts/diff.patch",
                    "provider": "api_agent",
                    "chosen_provider": "api_agent",
                }
                result = ctcp_dispatch.dispatch_once(
                    run_dir,
                    {"goal": "formal fallback test"},
                    gate,
                    ROOT,
                )
            finally:
                ctcp_dispatch.core_router.dispatch_execute = original
                if old_formal is None:
                    os.environ.pop("CTCP_FORMAL_API_ONLY", None)
                else:
                    os.environ["CTCP_FORMAL_API_ONLY"] = old_formal

            self.assertEqual(result.get("status"), "no_request")
            self.assertFalse((artifacts / "diff.patch").exists())
            self.assertFalse((artifacts / "provider_ledger_summary.json").exists())

    def test_review_provider_error_writes_failed_acceptance_not_ok(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _write_json(artifacts / "dispatch_config.json", ctcp_dispatch.default_dispatch_config_doc({"contract_guardian": "api_agent"}))
            gate = {
                "state": "blocked",
                "owner": "Contract Guardian",
                "path": "artifacts/reviews/review_contract.md",
                "reason": "review contract",
            }
            original = ctcp_dispatch.core_router.dispatch_execute
            try:
                ctcp_dispatch.core_router.dispatch_execute = lambda **_: {
                    "status": "exec_failed",
                    "reason": "Remote end closed connection without response",
                    "target_path": "artifacts/reviews/review_contract.md",
                    "fallback_used": True,
                    "chosen_provider": "api_agent",
                }
                result = ctcp_dispatch.dispatch_once(
                    run_dir,
                    {"goal": "Build a lightweight local-first task collaboration platform for a small team."},
                    gate,
                    ROOT,
                )
            finally:
                ctcp_dispatch.core_router.dispatch_execute = original

            self.assertEqual(result.get("status"), "exec_failed")
            ledger = (artifacts / "acceptance" / "ledger.jsonl").read_text(encoding="utf-8")
            row = json.loads(ledger.strip().splitlines()[-1])
            self.assertFalse(bool(row.get("passed", True)))
            self.assertEqual(row.get("result"), "ERR")

    def test_delivery_completion_blockers_include_failed_gate_and_entrypoint_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _write_json(artifacts / "project_manifest.json", {"schema_version": "ctcp-project-manifest-v1"})
            _write_json(
                artifacts / "support_public_delivery.json",
                {
                    "completion_gate": {"passed": False, "cold_replay_passed": False},
                    "replay_report": {"first_failure_stage": "entrypoint_missing"},
                    "overall_completion": {"passed": False},
                },
            )
            blockers = ctcp_orchestrate._delivery_completion_blockers(run_dir)
            self.assertIn("support_public_delivery completion_gate.passed=false", blockers)
            self.assertIn("support_public_delivery cold replay failed", blockers)
            self.assertIn("delivery cold replay entrypoint_missing", blockers)

    def test_intermediate_evidence_bundle_includes_acceptance_and_trace_chain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            for rel in (
                "artifacts/find_result.json",
                "artifacts/project_spec.json",
                "artifacts/output_contract_freeze.json",
                "artifacts/source_generation_report.json",
                "artifacts/verify_report.json",
                "artifacts/support_public_delivery.json",
            ):
                _write_json(run_dir / rel, {"path": rel})
            (run_dir / "TRACE.md").write_text("# trace\n", encoding="utf-8")
            (run_dir / "events.jsonl").write_text("{}\n", encoding="utf-8")
            (run_dir / "api_calls.jsonl").write_text("{}\n", encoding="utf-8")
            accept_dir = artifacts / "acceptance" / "step"
            accept_dir.mkdir(parents=True, exist_ok=True)
            _write_json(accept_dir / "request.json", {"request": True})
            _write_json(accept_dir / "result.json", {"status": "executed"})
            _write_json(accept_dir / "acceptance.json", {"passed": True})
            (artifacts / "acceptance" / "ledger.jsonl").write_text('{"passed":true}\n', encoding="utf-8")
            rel = build_intermediate_evidence_bundle(run_dir)
            self.assertEqual(rel, "artifacts/intermediate_evidence_bundle.zip")
            import zipfile

            with zipfile.ZipFile(run_dir / rel) as zf:
                names = set(zf.namelist())
            self.assertIn("artifacts/acceptance/step/request.json", names)
            self.assertIn("artifacts/acceptance/ledger.jsonl", names)
            self.assertIn("artifacts/output_contract_freeze.json", names)
            self.assertIn("api_calls.jsonl", names)

    def test_true_api_fallback_is_not_step_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _write_json(artifacts / "dispatch_config.json", ctcp_dispatch.default_dispatch_config_doc({"chair": "api_agent"}))
            gate = {
                "state": "blocked",
                "owner": "Chair/Planner",
                "path": "artifacts/workflow_generation_report.json",
                "reason": "waiting for workflow_generation",
            }

            original_execute = ctcp_dispatch.core_router.dispatch_execute
            old_force = os.environ.get("CTCP_FORCE_PROVIDER")
            os.environ["CTCP_FORCE_PROVIDER"] = "api_agent"
            try:
                def fake_execute(**kwargs):
                    target = Path(kwargs["run_dir"]) / "artifacts" / "workflow_generation_report.json"
                    target.write_text(json.dumps({"status": "pass"}) + "\n", encoding="utf-8")
                    return {
                        "status": "executed",
                        "target_path": "artifacts/workflow_generation_report.json",
                        "fallback_used": True,
                        "fallback_reason": "OpenAI API request failed: TLS error",
                        "chosen_provider": "api_agent",
                        "provider_mode": "remote",
                    }

                ctcp_dispatch.core_router.dispatch_execute = fake_execute
                result = ctcp_dispatch.dispatch_once(
                    run_dir,
                    {"goal": "Build a lightweight local-first task collaboration platform for a small team."},
                    gate,
                    ROOT,
                )
            finally:
                ctcp_dispatch.core_router.dispatch_execute = original_execute
                if old_force is None:
                    os.environ.pop("CTCP_FORCE_PROVIDER", None)
                else:
                    os.environ["CTCP_FORCE_PROVIDER"] = old_force

            self.assertEqual(result.get("status"), "executed")
            ledger = (artifacts / "acceptance" / "ledger.jsonl").read_text(encoding="utf-8")
            row = json.loads(ledger.strip().splitlines()[-1])
            self.assertFalse(bool(row.get("passed", True)))
            self.assertIn("api_fallback_not_allowed", row.get("reasons", []))

    def test_intermediate_evidence_bundle_includes_root_reviews(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            reviews = run_dir / "reviews"
            reviews.mkdir(parents=True, exist_ok=True)
            (reviews / "review_contract.md").write_text("# Contract Review\n\nVerdict: APPROVE\n", encoding="utf-8")
            (reviews / "review_cost.md").write_text("# Cost Review\n\nVerdict: APPROVE\n", encoding="utf-8")
            rel = build_intermediate_evidence_bundle(run_dir)
            import zipfile

            with zipfile.ZipFile(run_dir / rel) as zf:
                names = set(zf.namelist())
            self.assertIn("reviews/review_contract.md", names)
            self.assertIn("reviews/review_cost.md", names)

    def test_high_quality_plane_lite_freezes_extended_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            goal = (
                "Build a high-quality extended Plane-lite / Focalboard-lite task collaboration platform "
                "with feature matrix, page map, data model summary, and at least 8 screenshots."
            )
            doc = normalize_output_contract_freeze({}, goal=goal, run_dir=run_dir)
            self.assertEqual(doc.get("build_profile"), "high_quality_extended")
            self.assertEqual(doc.get("product_depth"), "extended")
            self.assertEqual(doc.get("required_pages"), 8)
            self.assertEqual(doc.get("required_screenshots"), 8)
            self.assertTrue(bool(doc.get("require_feature_matrix", False)))
            self.assertTrue(bool(doc.get("require_page_map", False)))
            self.assertTrue(bool(doc.get("require_data_model_summary", False)))
            spec = dict(doc.get("project_spec", {}))
            self.assertEqual(spec.get("build_profile"), "high_quality_extended")
            self.assertIn("dashboard", list(spec.get("required_pages_or_views", [])))
            self.assertIn("project_settings", list(spec.get("required_pages_or_views", [])))
            self.assertIn("search_tasks", list(spec.get("key_interactions", [])))

    def test_high_quality_source_generation_writes_extended_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _write_json(
                artifacts / "context_pack.json",
                {
                    "files": [
                        {
                            "path": "docs/41_low_capability_project_generation.md",
                            "why": "contract",
                            "content": "project generation context",
                        }
                    ]
                },
            )
            goal = (
                "Build a high-quality extended Plane-lite / Focalboard-lite task collaboration platform "
                "with feature matrix, page map, data model summary, search, import/export, and at least 8 screenshots."
            )
            freeze = normalize_output_contract_freeze({}, goal=goal, run_dir=run_dir)
            _write_json(artifacts / "output_contract_freeze.json", freeze)
            report = normalize_source_generation({}, goal=goal, run_dir=run_dir)
            self.assertEqual(report.get("status"), "pass")
            ledger = json.loads((artifacts / "extended_coverage_ledger.json").read_text(encoding="utf-8"))
            self.assertTrue(bool(ledger.get("passed", False)))
            self.assertGreaterEqual(len(list(ledger.get("implemented_pages", []))), 8)
            self.assertGreaterEqual(len(list(ledger.get("screenshot_files", []))), 8)
            for rel in ("docs/feature_matrix.md", "docs/page_map.md", "docs/data_model_summary.md"):
                self.assertTrue((run_dir / freeze["project_root"] / rel).exists(), rel)

    def test_high_quality_delivery_gate_blocks_missing_extended_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _write_json(
                artifacts / "output_contract_freeze.json",
                {
                    "schema_version": "ctcp-project-output-contract-v1",
                    "build_profile": "high_quality_extended",
                    "project_type": "team_task_pm",
                    "project_domain": "team_task_management",
                    "project_archetype": "team_task_pm_web",
                },
            )
            _write_json(
                artifacts / "support_public_delivery.json",
                {
                    "completion_gate": {"passed": True, "cold_replay_passed": True},
                    "overall_completion": {"passed": True},
                },
            )
            blockers = ctcp_orchestrate._delivery_completion_blockers(run_dir)
            self.assertIn("extended coverage ledger missing", blockers)

    def test_chair_deliver_retries_transient_tls_before_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            logs_dir = run_dir / "logs"
            target_path = run_dir / "artifacts" / "deliverable_index.json"
            prompt_path = run_dir / "outbox" / "AGENT_PROMPT_chair_deliver.md"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text("deliver\n", encoding="utf-8")

            calls: list[int] = []
            original_run_command = api_provider._run_command
            old_attempts = os.environ.get("CTCP_DELIVER_API_MAX_ATTEMPTS")
            old_delay = os.environ.get("CTCP_DELIVER_API_RETRY_BASE_DELAY_SEC")
            os.environ["CTCP_DELIVER_API_MAX_ATTEMPTS"] = "3"
            os.environ["CTCP_DELIVER_API_RETRY_BASE_DELAY_SEC"] = "0"

            def fake_run_command(*args, **kwargs):
                calls.append(1)
                if len(calls) == 1:
                    return subprocess.CompletedProcess(
                        args="fake",
                        returncode=1,
                        stdout="",
                        stderr="OpenAI API request failed: [SSL: TLSV1_ALERT_PROTOCOL_VERSION] tlsv1 alert protocol version",
                    )
                return subprocess.CompletedProcess(args="fake", returncode=0, stdout='{"stage":"deliver"}', stderr="")

            class Hooks:
                @staticmethod
                def record_failure_review(run_dir: Path, reason: str) -> Path:
                    path = run_dir / "reviews" / "review_failure.md"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(reason, encoding="utf-8")
                    return path

                @staticmethod
                def normalize_target_payload(**kwargs):
                    return str(kwargs.get("raw_text", "")) + "\n", ""

            try:
                api_provider._run_command = fake_run_command
                result = api_provider._run_agent_phase(
                    template="fake-agent",
                    placeholders={},
                    repo_root=ROOT,
                    run_dir=run_dir,
                    logs_dir=logs_dir,
                    prompt_text="deliver",
                    api_call_env={},
                    hooks=Hooks(),
                    request={"role": "chair", "action": "deliver", "target_path": "artifacts/deliverable_index.json"},
                    target_path=target_path,
                    target_rel="artifacts/deliverable_index.json",
                    prompt_path=prompt_path,
                )
            finally:
                api_provider._run_command = original_run_command
                if old_attempts is None:
                    os.environ.pop("CTCP_DELIVER_API_MAX_ATTEMPTS", None)
                else:
                    os.environ["CTCP_DELIVER_API_MAX_ATTEMPTS"] = old_attempts
                if old_delay is None:
                    os.environ.pop("CTCP_DELIVER_API_RETRY_BASE_DELAY_SEC", None)
                else:
                    os.environ["CTCP_DELIVER_API_RETRY_BASE_DELAY_SEC"] = old_delay

            self.assertEqual(len(calls), 2)
            self.assertEqual(result.get("status"), "executed")
            self.assertFalse(bool(result.get("fallback_used", False)))
            self.assertEqual(result.get("api_retry_attempts"), 2)
            self.assertTrue((logs_dir / "agent.attempt_01.stderr").exists())
            self.assertTrue((logs_dir / "agent.attempt_02.stdout").exists())
            self.assertTrue((logs_dir / "agent_retry.jsonl").exists())
            self.assertTrue(target_path.exists())


if __name__ == "__main__":
    unittest.main()

