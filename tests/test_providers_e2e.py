#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
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

import ctcp_dispatch


def _run(cmd: list[str], cwd: Path) -> None:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise AssertionError(
            "command failed\n"
            f"cmd={cmd}\n"
            f"stdout={proc.stdout}\n"
            f"stderr={proc.stderr}\n"
        )


def _init_repo(repo: Path) -> None:
    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "ctcp-test"], repo)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "docs" / "target.txt").write_text("hello\n", encoding="utf-8")
    (repo / "contracts").mkdir(parents=True, exist_ok=True)
    (repo / "contracts" / "allowed_changes.yaml").write_text(
        "\n".join(
            [
                "allowed_paths:",
                "  - docs/",
                "  - contracts/",
                "  - tests/",
                "blocked_paths:",
                "  - .github/",
                "max_files: 20",
                "max_added_lines: 400",
                "max_deleted_lines: 400",
                "max_total_lines: 400",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _run(["git", "add", "docs/target.txt", "contracts/allowed_changes.yaml"], repo)
    _run(["git", "commit", "-m", "init"], repo)


@unittest.skipUnless(shutil.which("git"), "git is required")
class ProviderE2ETests(unittest.TestCase):
    def test_api_agent_and_guardian_local_exec_flow(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(repo)
            run_dir = repo / "runs" / "provider_e2e" / "r1"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

            dispatch_cfg = {
                "schema_version": "ctcp-dispatch-config-v1",
                "mode": "manual_outbox",
                "role_providers": {
                    "contract_guardian": "local_exec",
                    "patchmaker": "api_agent",
                    "fixer": "api_agent",
                },
                "budgets": {"max_outbox_prompts": 8},
            }
            (run_dir / "artifacts" / "dispatch_config.json").write_text(
                json.dumps(dispatch_cfg, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            run_doc = {"goal": "provider e2e"}

            agent_script = repo / "agent_stub.py"
            agent_script.write_text(
                "\n".join(
                    [
                        "print('# Contract Review')",
                        "print('')",
                        "print('Verdict: APPROVE')",
                        "print('')",
                        "print('Blocking Reasons:')",
                        "print('- none')",
                        "print('')",
                        "print('Required Fix/Artifacts:')",
                        "print('- none')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            guard_gate = {
                "state": "blocked",
                "owner": "Contract Guardian",
                "path": "reviews/review_contract.md",
                "reason": "waiting for review_contract.md",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_AGENT_CMD": f'"{sys.executable}" "{agent_script}"',
                    "OPENAI_API_KEY": "dummy-key",
                    "OPENAI_BASE_URL": "http://127.0.0.1:1/v1",
                },
                clear=False,
            ):
                guard_result = ctcp_dispatch.dispatch_once(run_dir, run_doc, guard_gate, repo)
            self.assertEqual(guard_result.get("status"), "executed", msg=str(guard_result))
            self.assertTrue((run_dir / "reviews" / "review_contract.md").exists())

            plan_script = repo / "plan_stub.py"
            plan_script.write_text("print('# PLAN\\n- step: dummy')\n", encoding="utf-8")
            patch_script = repo / "patch_stub.py"
            patch_script.write_text(
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
                encoding="utf-8",
            )

            patch_gate = {
                "state": "blocked",
                "owner": "PatchMaker",
                "path": "artifacts/diff.patch",
                "reason": "waiting for diff.patch",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "dummy-key",
                    "OPENAI_BASE_URL": "http://127.0.0.1:1/v1",
                    "SDDAI_PLAN_CMD": f'"{sys.executable}" "{plan_script}"',
                    "SDDAI_PATCH_CMD": f'"{sys.executable}" "{patch_script}"',
                },
                clear=False,
            ):
                patch_result = ctcp_dispatch.dispatch_once(run_dir, run_doc, patch_gate, repo)

            self.assertEqual(patch_result.get("status"), "executed", msg=str(patch_result))
            plan_out = run_dir / "outbox" / "PLAN.md"
            patch_out = run_dir / "outbox" / "diff.patch"
            target_patch = run_dir / "artifacts" / "diff.patch"
            self.assertTrue(plan_out.exists())
            self.assertTrue(patch_out.exists())
            self.assertTrue(target_patch.exists())
            self.assertTrue(patch_out.read_text(encoding="utf-8").startswith("diff --git"))
            self.assertTrue((run_dir / "logs" / "plan_agent.stdout").exists())
            self.assertTrue((run_dir / "logs" / "plan_agent.stderr").exists())
            self.assertTrue((run_dir / "logs" / "patch_agent.stdout").exists())
            self.assertTrue((run_dir / "logs" / "patch_agent.stderr").exists())
            self.assertTrue((run_dir / "outbox" / "CONTEXT.md").exists())
            self.assertTrue((run_dir / "outbox" / "CONSTRAINTS.md").exists())
            self.assertTrue((run_dir / "outbox" / "FIX_BRIEF.md").exists())
            self.assertTrue((run_dir / "outbox" / "EXTERNALS.md").exists())


if __name__ == "__main__":
    unittest.main()
