#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "scripts" / "workflows" / "adlc_self_improve_core.py"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _must_run(cmd: list[str], cwd: Path) -> None:
    proc = _run(cmd, cwd)
    if proc.returncode != 0:
        raise AssertionError(
            "command failed\n"
            f"cmd={cmd}\n"
            f"stdout={proc.stdout}\n"
            f"stderr={proc.stderr}\n"
        )


def _init_repo(repo: Path) -> None:
    _must_run(["git", "init"], repo)
    _must_run(["git", "config", "user.email", "test@example.com"], repo)
    _must_run(["git", "config", "user.name", "ctcp-test"], repo)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "target.txt").write_text("hello\n", encoding="utf-8")
    (repo / "contracts").mkdir(parents=True, exist_ok=True)
    (repo / "contracts" / "allowed_changes.yaml").write_text(
        "\n".join(
            [
                "allowed_paths:",
                "  - docs/",
                "  - contracts/",
                "blocked_paths:",
                "  - .github/",
                "max_files: 10",
                "max_added_lines: 200",
                "max_deleted_lines: 200",
                "max_total_lines: 200",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _must_run(["git", "add", "docs/target.txt", "contracts/allowed_changes.yaml"], repo)
    _must_run(["git", "commit", "-m", "init"], repo)


def _write(repo: Path, rel: str, text: str) -> Path:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _workflow_cmd(
    *,
    repo: Path,
    run_id: str,
    verify_cmd: str,
    plan_cmd: str = "",
    patch_cmd: str = "",
) -> list[str]:
    cmd = [
        sys.executable,
        str(WORKFLOW),
        "--repo",
        str(repo),
        "--goal",
        "external-requirements",
        "--max-rounds",
        "1",
        "--run-id",
        run_id,
        "--verify-cmd",
        verify_cmd,
    ]
    if plan_cmd.strip():
        cmd += ["--plan-cmd", plan_cmd]
    if patch_cmd.strip():
        cmd += ["--patch-cmd", patch_cmd]
    return cmd


@unittest.skipUnless(shutil.which("git"), "git is required")
class SelfImproveExternalRequirementTests(unittest.TestCase):
    def test_default_mode_requires_plan_and_patch_commands(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(repo)
            verify_script = _write(repo, "verify_ok.py", "raise SystemExit(0)\n")
            verify_cmd = f"python {verify_script.name}"

            proc = _run(
                _workflow_cmd(repo=repo, run_id="r1", verify_cmd=verify_cmd),
                repo,
            )
            self.assertNotEqual(proc.returncode, 0)

            run_dir = repo / "runs" / "adlc_self_improve_core" / "r1"
            error_text = (run_dir / "logs" / "error.txt").read_text(encoding="utf-8")
            state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            self.assertIn("SDDAI_PLAN_CMD/--plan-cmd required", error_text)
            self.assertIn("SDDAI_PLAN_CMD/--plan-cmd required", state.get("last_error", ""))
            self.assertEqual(state.get("phase"), "stop")

    def test_invalid_external_patch_fails_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(repo)
            verify_script = _write(repo, "verify_ok.py", "raise SystemExit(0)\n")
            plan_script = _write(
                repo,
                "plan_ok.py",
                "\n".join(
                    [
                        "import pathlib",
                        "import sys",
                        "ctx = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')",
                        "cons = pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')",
                        "fixb = pathlib.Path(sys.argv[3]).read_text(encoding='utf-8')",
                        "print('# PLAN FROM EXTERNAL')",
                        "print('')",
                        "print(f'- context_chars: {len(ctx)}')",
                        "print(f'- constraints_chars: {len(cons)}')",
                        "print(f'- fix_brief_chars: {len(fixb)}')",
                        "",
                    ]
                ),
            )
            patch_script = _write(
                repo,
                "patch_invalid.py",
                "print('this is not a unified diff')\n",
            )
            verify_cmd = f"python {verify_script.name}"
            plan_cmd = (
                f'python "{plan_script.name}" '
                '"{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}"'
            )
            patch_cmd = f'python "{patch_script.name}" "{{PLAN_PATH}}"'

            proc = _run(
                _workflow_cmd(
                    repo=repo,
                    run_id="r2",
                    verify_cmd=verify_cmd,
                    plan_cmd=plan_cmd,
                    patch_cmd=patch_cmd,
                ),
                repo,
            )
            self.assertNotEqual(proc.returncode, 0)

            run_dir = repo / "runs" / "adlc_self_improve_core" / "r2"
            error_text = (run_dir / "logs" / "error.txt").read_text(encoding="utf-8")
            patch_stdout = (run_dir / "logs" / "patch_cmd.stdout.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("diff --git", error_text)
            self.assertIn("not a unified diff", patch_stdout)
            self.assertFalse((run_dir / "logs" / "verify_stdout.txt").exists())
            self.assertEqual((repo / "docs" / "target.txt").read_text(encoding="utf-8"), "hello\n")

    def test_external_plan_and_patch_can_complete_round(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(repo)
            verify_script = _write(repo, "verify_ok.py", "raise SystemExit(0)\n")
            plan_script = _write(
                repo,
                "plan_ok.py",
                "\n".join(
                    [
                        "import pathlib",
                        "import sys",
                        "ctx = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8')",
                        "cons = pathlib.Path(sys.argv[2]).read_text(encoding='utf-8')",
                        "fixb = pathlib.Path(sys.argv[3]).read_text(encoding='utf-8')",
                        "print('# PLAN FROM EXTERNAL')",
                        "print('')",
                        "print(f'- context_chars: {len(ctx)}')",
                        "print(f'- constraints_chars: {len(cons)}')",
                        "print(f'- fix_brief_chars: {len(fixb)}')",
                        "",
                    ]
                ),
            )
            patch_script = _write(
                repo,
                "patch_ok.py",
                "\n".join(
                    [
                        "print('diff --git a/docs/target.txt b/docs/target.txt')",
                        "print('--- a/docs/target.txt')",
                        "print('+++ b/docs/target.txt')",
                        "print('@@ -1 +1 @@')",
                        "print('-hello')",
                        "print('+hello patched')",
                        "",
                    ]
                ),
            )
            verify_cmd = f"python {verify_script.name}"
            plan_cmd = (
                f'python "{plan_script.name}" '
                '"{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}"'
            )
            patch_cmd = (
                f'python "{patch_script.name}" '
                '"{PLAN_PATH}" "{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}"'
            )

            proc = _run(
                _workflow_cmd(
                    repo=repo,
                    run_id="r3",
                    verify_cmd=verify_cmd,
                    plan_cmd=plan_cmd,
                    patch_cmd=patch_cmd,
                ),
                repo,
            )
            self.assertEqual(proc.returncode, 0, msg=f"stdout={proc.stdout}\nstderr={proc.stderr}")

            run_dir = repo / "runs" / "adlc_self_improve_core" / "r3"
            self.assertTrue((run_dir / "outbox" / "PLAN.md").exists())
            self.assertTrue((run_dir / "outbox" / "CONTEXT.md").exists())
            self.assertTrue((run_dir / "outbox" / "CONSTRAINTS.md").exists())
            self.assertTrue((run_dir / "outbox" / "FIX_BRIEF.md").exists())
            self.assertTrue((run_dir / "logs" / "plan_cmd.stdout.txt").exists())
            self.assertTrue((run_dir / "logs" / "patch_cmd.stdout.txt").exists())
            self.assertTrue((run_dir / "logs" / "verify_stdout.txt").exists())
            self.assertIn(
                "PLAN FROM EXTERNAL",
                (run_dir / "outbox" / "PLAN.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (repo / "docs" / "target.txt").read_text(encoding="utf-8"),
                "hello patched\n",
            )
            state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state.get("phase"), "done")


if __name__ == "__main__":
    unittest.main()
