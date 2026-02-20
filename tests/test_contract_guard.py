#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import contract_guard


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True)


def _init_repo(base: Path) -> None:
    _run(["git", "init"], base)
    _run(["git", "config", "user.email", "test@example.com"], base)
    _run(["git", "config", "user.name", "ctcp-test"], base)
    (base / "README.md").write_text("seed\n", encoding="utf-8")
    _run(["git", "add", "README.md"], base)
    _run(["git", "commit", "-m", "init"], base)


def _write_policy(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "allowed_paths:",
                "  - scripts/",
                "  - tests/",
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


@unittest.skipUnless(shutil.which("git"), "git is required")
class ContractGuardTests(unittest.TestCase):
    def test_pass_for_allowed_change(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(repo)
            policy = repo / "contracts" / "allowed_changes.yaml"
            _write_policy(policy)

            target = repo / "scripts" / "x.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("print('ok')\n", encoding="utf-8")
            _run(["git", "add", "scripts/x.py"], repo)

            review = contract_guard.evaluate(
                repo,
                policy_path=policy,
                out_path=repo / "reviews" / "contract_review.json",
            )
            self.assertTrue(review["contract_guard"]["pass"])

    def test_fail_for_blocked_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _init_repo(repo)
            policy = repo / "contracts" / "allowed_changes.yaml"
            _write_policy(policy)

            target = repo / ".github" / "workflows" / "ci.yml"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("name: ci\n", encoding="utf-8")
            _run(["git", "add", ".github/workflows/ci.yml"], repo)

            review = contract_guard.evaluate(
                repo,
                policy_path=policy,
                out_path=repo / "reviews" / "contract_review.json",
            )
            self.assertFalse(review["contract_guard"]["pass"])
            reasons = "\n".join(review["contract_guard"]["reasons"])
            self.assertIn("blocked path touched", reasons)


if __name__ == "__main__":
    unittest.main()

