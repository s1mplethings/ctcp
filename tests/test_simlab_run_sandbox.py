from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from simlab import run as simlab_run


class SimlabSandboxTests(unittest.TestCase):
    def test_copy_repo_skips_runtime_artifacts_but_keeps_plan(self) -> None:
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src = Path(src_dir)
            dst = Path(dst_dir) / "sandbox"

            (src / "README.md").write_text("sandbox baseline\n", encoding="utf-8")
            (src / "artifacts" / "PLAN.md").parent.mkdir(parents=True, exist_ok=True)
            (src / "artifacts" / "PLAN.md").write_text("Status: SIGNED\n", encoding="utf-8")
            runtime_dir = (
                src
                / "artifacts"
                / "backend_interface_non_narrative"
                / "manual_web_service_run"
                / "project_output"
            )
            runtime_dir.mkdir(parents=True, exist_ok=True)
            (runtime_dir / "generated.txt").write_text("runtime output\n", encoding="utf-8")
            (src / "artifacts" / "test_step_1_session.json").write_text("{}", encoding="utf-8")

            simlab_run.copy_repo(src, dst)

            self.assertTrue((dst / "README.md").exists())
            self.assertTrue((dst / "artifacts" / "PLAN.md").exists())
            self.assertFalse((dst / "artifacts" / "backend_interface_non_narrative").exists())
            self.assertFalse((dst / "artifacts" / "test_step_1_session.json").exists())

    def test_git_baseline_sets_longpaths_and_raises_on_failed_add(self) -> None:
        calls: list[str] = []

        def fake_run_cmd(cmd: str, cwd: Path, env: dict[str, str] | None = None) -> simlab_run.CmdResult:
            del cwd, env
            calls.append(cmd)
            if cmd == "git add -A":
                return simlab_run.CmdResult(rc=1, stdout="", stderr="add failed", cmd=cmd)
            return simlab_run.CmdResult(rc=0, stdout="", stderr="", cmd=cmd)

        with tempfile.TemporaryDirectory() as repo_dir:
            repo = Path(repo_dir)
            with mock.patch.object(simlab_run, "run_cmd", side_effect=fake_run_cmd):
                with self.assertRaisesRegex(RuntimeError, "git add -A"):
                    simlab_run.git_baseline(repo)

        self.assertEqual(
            calls[:5],
            [
                "git init",
                "git config core.longpaths true",
                "git config user.email simlab@example.local",
                "git config user.name simlab-runner",
                "git add -A",
            ],
        )


if __name__ == "__main__":
    unittest.main()
