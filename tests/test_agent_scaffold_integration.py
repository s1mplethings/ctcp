from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scripts.ctcp_orchestrate as orchestrate


class AgentScaffoldIntegrationTests(unittest.TestCase):
    def _run_scaffold(self, manifest_path: Path) -> tuple[Path, dict[str, object], tempfile.TemporaryDirectory[str]]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_agent_scaffold_orch_")
        out = Path(td.name) / "agent_project"
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                "agent-scaffold",
                "--manifest",
                str(manifest_path),
                "--output-dir",
                str(out),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return out, json.loads(completed.stdout), td

    def _dry_run(self, scaffold: Path) -> dict[str, object]:
        completed = subprocess.run(
            [sys.executable, "run_agent.py", "--dry-run", "--input", "sample_input.json"],
            cwd=scaffold,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
        return json.loads(completed.stdout)

    def test_agent_scaffold_subcommand_generates_scaffold_and_dry_run(self) -> None:
        manifest_path = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_devops_incident.json"
        scaffold, result, td = self._run_scaffold(manifest_path)
        self.addCleanup(td.cleanup)
        self.assertEqual(result["mode"], "agent-scaffold")
        self.assertTrue((scaffold / "manifest.json").exists())
        output = self._dry_run(scaffold)
        self.assertEqual(output["status"], "ok")

    def test_permission_attack_through_scaffold_subcommand_keeps_approval(self) -> None:
        manifest_path = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_permission_attack.json"
        scaffold, _result, td = self._run_scaffold(manifest_path)
        self.addCleanup(td.cleanup)
        output = self._dry_run(scaffold)
        self.assertIn("rollback", output["approval_required_actions"])
        self.assertIn("refund", output["approval_required_actions"])
        self.assertTrue(output["audit_log_required"])

    def test_agent_scaffold_invalid_manifest_has_clear_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_scaffold_bad_") as td:
            root = Path(td)
            manifest = root / "bad.json"
            out = root / "agent_project"
            manifest.write_text(json.dumps({"manifest_version": "1.0"}), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                    "agent-scaffold",
                    "--manifest",
                    str(manifest),
                    "--output-dir",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("[ctcp_orchestrate][agent-scaffold][error]", completed.stderr)
            self.assertFalse(out.exists())

    def test_agent_scaffold_existing_output_dir_is_not_silently_overwritten(self) -> None:
        manifest_path = ROOT / "tests" / "agent_factory_benchmark" / "generated" / "output_devops_incident.json"
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_scaffold_existing_orch_") as td:
            out = Path(td) / "agent_project"
            out.mkdir()
            (out / "important.txt").write_text("do not overwrite", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                    "agent-scaffold",
                    "--manifest",
                    str(manifest_path),
                    "--output-dir",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 2)
            self.assertIn("output directory is not empty", completed.stderr)

    def test_agent_manifest_subcommand_still_available(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_agent_manifest_still_") as td:
            root = Path(td)
            input_path = root / "input.json"
            output_path = root / "manifest.json"
            input_path.write_text(json.dumps({"goal": "Create a product feedback agent"}), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "ctcp_orchestrate.py"),
                    "agent-manifest",
                    "--input",
                    str(input_path),
                    "--output",
                    str(output_path),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)
            self.assertTrue(output_path.exists())

    def test_normal_new_run_dispatch_is_not_agent_scaffold_mode(self) -> None:
        with mock.patch.object(orchestrate, "cmd_new_run", return_value=0) as new_run:
            with mock.patch.object(sys, "argv", ["ctcp_orchestrate.py", "new-run", "--goal", "build a todo app"]):
                self.assertEqual(orchestrate.main(), 0)
        new_run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
