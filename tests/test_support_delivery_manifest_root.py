from __future__ import annotations

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


class SupportDeliveryManifestRootTests(unittest.TestCase):
    def test_collect_public_delivery_state_uses_project_manifest_root_for_generated_project_runs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_delivery_manifest_root_") as td:
            repo_root = Path(td)
            bound_run = repo_root / "runs" / "bound-story"
            generated_project = bound_run / "project_output" / "story_organizer"
            (generated_project / "docs").mkdir(parents=True, exist_ok=True)
            (generated_project / "meta" / "tasks").mkdir(parents=True, exist_ok=True)
            (generated_project / "scripts").mkdir(parents=True, exist_ok=True)
            (generated_project / "tests").mkdir(parents=True, exist_ok=True)
            (generated_project / "artifacts" / "screenshots").mkdir(parents=True, exist_ok=True)
            (bound_run / "artifacts").mkdir(parents=True, exist_ok=True)
            (generated_project / "README.md").write_text("# story_organizer\n", encoding="utf-8")
            (generated_project / "meta" / "manifest.json").write_text("{}", encoding="utf-8")
            (generated_project / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
            (generated_project / "meta" / "tasks" / "CURRENT.md").write_text("# current\n", encoding="utf-8")
            (generated_project / "scripts" / "verify_repo.ps1").write_text("Write-Host ok\n", encoding="utf-8")
            (generated_project / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
            (generated_project / "artifacts" / "test_plan.json").write_text("{}", encoding="utf-8")
            (generated_project / "artifacts" / "test_cases.json").write_text("{}", encoding="utf-8")
            (generated_project / "artifacts" / "test_summary.md").write_text("# summary\n", encoding="utf-8")
            (generated_project / "artifacts" / "demo_trace.md").write_text("# demo\n", encoding="utf-8")
            (generated_project / "artifacts" / "screenshots" / "step01.png").write_bytes(b"\x89PNG\r\n")
            (bound_run / "artifacts" / "PLAN.md").write_text(
                "Status: SIGNED\nScope-Allow: scripts/,tools/,tests/,artifacts/,meta/,docs/\n",
                encoding="utf-8",
            )

            state = support_bot.default_support_session_state("delivery-manifest-root")
            state["bound_run_id"] = "r-story"
            state["bound_run_dir"] = str(bound_run)
            with mock.patch.object(support_bot, "ROOT", repo_root):
                delivery = support_bot.collect_public_delivery_state(
                    session_state=state,
                    project_context={
                        "run_id": "r-story",
                        "run_dir": str(bound_run),
                        "project_manifest": {"project_root": "project_output/story_organizer"},
                        "status": {
                            "run_status": "pass",
                            "verify_result": "PASS",
                            "needs_user_decision": False,
                            "decisions_needed_count": 0,
                            "gate": {"state": "pass", "owner": "", "reason": ""},
                        },
                    },
                    source="telegram",
                )

            self.assertIn(str(generated_project.resolve()), list(delivery.get("package_source_dirs", [])))
            self.assertTrue(bool(delivery.get("package_delivery_allowed", False)))
            self.assertTrue(bool(delivery.get("package_ready", False)))
            self.assertEqual(str(delivery.get("package_delivery_mode", "")), "zip_existing_project")


if __name__ == "__main__":
    unittest.main()
