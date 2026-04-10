from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scripts.ctcp_support_bot as support_bot


class SupportPublicDeliveryStateTests(unittest.TestCase):
    def test_collect_public_delivery_state_blocks_low_quality_generated_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_state_") as td:
            repo_root = Path(td)
            generated_project = repo_root / "generated_projects" / "story_organizer"
            generated_project.mkdir(parents=True, exist_ok=True)
            (generated_project / "main.py").write_text("print('story')\n", encoding="utf-8")

            bound_run = repo_root / "runs" / "bound-story"
            (bound_run / "artifacts").mkdir(parents=True, exist_ok=True)
            (bound_run / "artifacts" / "patch_apply.json").write_text(
                json.dumps({"touched_files": ["generated_projects/story_organizer/main.py"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (bound_run / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: generated_projects/story_organizer/\n",
                encoding="utf-8",
            )

            state = support_bot.default_support_session_state("delivery-demo")
            state["bound_run_id"] = "r-story"
            state["bound_run_dir"] = str(bound_run)
            with mock.patch.object(support_bot, "ROOT", repo_root):
                delivery = support_bot.collect_public_delivery_state(
                    session_state=state,
                    project_context={
                        "run_id": "r-story",
                        "run_dir": str(bound_run),
                        "status": {
                            "run_status": "completed",
                            "verify_result": "PASS",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "closed", "owner": "", "reason": ""},
                        },
                    },
                    source="telegram",
                )

            self.assertFalse(bool(delivery.get("package_ready", False)))
            self.assertFalse(bool(delivery.get("package_delivery_allowed", False)))
            self.assertFalse(bool(delivery.get("package_quality_ready", True)))
            self.assertIn("quality score", str(delivery.get("package_blocked_reason", "")))
            self.assertFalse(bool(delivery.get("screenshot_ready", False)))
            self.assertIn(str(generated_project.resolve()), list(delivery.get("package_source_dirs", [])))
            self.assertEqual(str(delivery.get("package_delivery_mode", "")), "materialize_ctcp_scaffold")
            self.assertEqual(str(delivery.get("project_name_hint", "")), "story_organizer")
            self.assertIn("docs/", list(delivery.get("package_structure_hint", [])))

    def test_collect_public_delivery_state_allows_high_quality_generated_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_quality_ok_") as td:
            repo_root = Path(td)
            generated_project = repo_root / "generated_projects" / "story_organizer"
            (generated_project / "docs").mkdir(parents=True, exist_ok=True)
            (generated_project / "meta" / "tasks").mkdir(parents=True, exist_ok=True)
            (generated_project / "scripts").mkdir(parents=True, exist_ok=True)
            (generated_project / "tests").mkdir(parents=True, exist_ok=True)
            (generated_project / "artifacts" / "screenshots").mkdir(parents=True, exist_ok=True)
            (generated_project / "README.md").write_text("# story_organizer\n", encoding="utf-8")
            (generated_project / "manifest.json").write_text("{}", encoding="utf-8")
            (generated_project / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
            (generated_project / "meta" / "tasks" / "CURRENT.md").write_text("# current\n", encoding="utf-8")
            (generated_project / "scripts" / "verify_repo.ps1").write_text("Write-Host ok\n", encoding="utf-8")
            (generated_project / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
            (generated_project / "artifacts" / "test_plan.json").write_text("{}", encoding="utf-8")
            (generated_project / "artifacts" / "test_cases.json").write_text("{}", encoding="utf-8")
            (generated_project / "artifacts" / "test_summary.md").write_text("# summary\n", encoding="utf-8")
            (generated_project / "artifacts" / "demo_trace.md").write_text("# demo\n", encoding="utf-8")
            (generated_project / "artifacts" / "screenshots" / "step01.png").write_bytes(b"\x89PNG\r\n")

            bound_run = repo_root / "runs" / "bound-story"
            (bound_run / "artifacts").mkdir(parents=True, exist_ok=True)
            (bound_run / "artifacts" / "patch_apply.json").write_text(
                json.dumps({"touched_files": ["generated_projects/story_organizer/README.md"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (bound_run / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: generated_projects/story_organizer/\n",
                encoding="utf-8",
            )

            state = support_bot.default_support_session_state("delivery-demo")
            state["bound_run_id"] = "r-story"
            state["bound_run_dir"] = str(bound_run)
            with mock.patch.object(support_bot, "ROOT", repo_root):
                delivery = support_bot.collect_public_delivery_state(
                    session_state=state,
                    project_context={
                        "run_id": "r-story",
                        "run_dir": str(bound_run),
                        "status": {
                            "run_status": "completed",
                            "verify_result": "PASS",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "closed", "owner": "", "reason": ""},
                        },
                    },
                    source="telegram",
                )

            self.assertTrue(bool(delivery.get("package_ready", False)))
            self.assertTrue(bool(delivery.get("package_delivery_allowed", False)))
            self.assertTrue(bool(delivery.get("package_quality_ready", False)))
            self.assertGreaterEqual(int(delivery.get("package_quality_score", 0) or 0), support_bot.SUPPORT_PACKAGE_MIN_QUALITY_SCORE)
            self.assertEqual(str(delivery.get("package_blocked_reason", "")), "")
            self.assertEqual(str(delivery.get("package_delivery_mode", "")), "zip_existing_ctcp_project")

    def test_collect_public_delivery_state_ignores_repo_internal_scope_allow_roots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_internal_scope_") as td:
            repo_root = Path(td)
            for rel in ("scripts", "tools", "tests", "artifacts", "meta", "docs"):
                (repo_root / rel).mkdir(parents=True, exist_ok=True)
            (repo_root / "artifacts" / "preview.png").write_bytes(b"\x89PNG\r\n")

            bound_run = repo_root / "runs" / "bound-story"
            (bound_run / "artifacts").mkdir(parents=True, exist_ok=True)
            (bound_run / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: scripts/,tools/,tests/,artifacts/,meta/,docs/\n",
                encoding="utf-8",
            )

            state = support_bot.default_support_session_state("delivery-internal-demo")
            state["bound_run_id"] = "r-story"
            state["bound_run_dir"] = str(bound_run)
            with mock.patch.object(support_bot, "ROOT", repo_root):
                delivery = support_bot.collect_public_delivery_state(
                    session_state=state,
                    project_context={
                        "run_id": "r-story",
                        "run_dir": str(bound_run),
                        "status": {
                            "run_status": "running",
                            "verify_result": "",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "blocked", "owner": "PatchMaker", "reason": "waiting for diff.patch"},
                        },
                    },
                    source="telegram",
                )

            self.assertEqual(list(delivery.get("package_source_dirs", [])), [])
            self.assertFalse(bool(delivery.get("screenshot_ready", False)))
            self.assertEqual(str(delivery.get("package_delivery_mode", "")), "")
            self.assertEqual(str(delivery.get("package_blocked_reason", "")), "package artifact not ready")


if __name__ == "__main__":
    unittest.main()
