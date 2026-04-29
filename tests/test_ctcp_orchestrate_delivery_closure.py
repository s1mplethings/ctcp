from __future__ import annotations

import json
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

import scripts.ctcp_orchestrate as orchestrate


class OrchestrateDeliveryClosureTests(unittest.TestCase):
    def test_finish_verify_pass_auto_closes_virtual_delivery_when_artifacts_are_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_orchestrate_delivery_close_") as td:
            run_dir = Path(td)
            project_dir = run_dir / "project_output" / "story_organizer"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "logs").mkdir(parents=True, exist_ok=True)
            (project_dir / "docs").mkdir(parents=True, exist_ok=True)
            (project_dir / "meta" / "tasks").mkdir(parents=True, exist_ok=True)
            (project_dir / "scripts").mkdir(parents=True, exist_ok=True)
            (project_dir / "tests").mkdir(parents=True, exist_ok=True)
            (project_dir / "artifacts" / "screenshots").mkdir(parents=True, exist_ok=True)
            (project_dir / "README.md").write_text("# story_organizer\n", encoding="utf-8")
            (project_dir / "app.py").write_text("print('story')\n", encoding="utf-8")
            (project_dir / "meta" / "manifest.json").write_text("{}", encoding="utf-8")
            (project_dir / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
            (project_dir / "meta" / "tasks" / "CURRENT.md").write_text("# current\n", encoding="utf-8")
            (project_dir / "scripts" / "verify_repo.ps1").write_text("Write-Host ok\n", encoding="utf-8")
            (project_dir / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
            (project_dir / "artifacts" / "test_plan.json").write_text("{}", encoding="utf-8")
            (project_dir / "artifacts" / "test_cases.json").write_text("{}", encoding="utf-8")
            (project_dir / "artifacts" / "test_summary.md").write_text("# summary\n", encoding="utf-8")
            (project_dir / "artifacts" / "demo_trace.md").write_text("# demo\n", encoding="utf-8")
            (project_dir / "artifacts" / "screenshots" / "overview.png").write_bytes(b"\x89PNG\r\n")
            (project_dir / "artifacts" / "screenshots" / "final-ui.png").write_bytes(b"\x89PNG\r\n")
            (run_dir / "artifacts" / "project_manifest.json").write_text(
                json.dumps({"project_root": "project_output/story_organizer"}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            run_doc = {"goal": "story organizer", "status": "running"}
            rc = orchestrate.finish_verify_pass(run_dir, run_doc, rc=0, iteration=1)

            self.assertEqual(rc, 1)
            self.assertEqual(str(run_doc.get("status", "")), "fail")
            gate_report = json.loads((run_dir / "artifacts" / "delivery_gate_report.json").read_text(encoding="utf-8"))
            self.assertFalse(bool(gate_report.get("passed", False)))
            reasons = list(gate_report.get("reasons", []))
            self.assertTrue(bool(reasons), msg=json.dumps(gate_report, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
