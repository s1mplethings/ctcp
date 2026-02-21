#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.patch_first import (
    PatchPolicy,
    PatchValidationError,
    apply_patch_safely,
    git_apply_check,
    normalize_repo_relpath,
    validate_diff_against_policy,
)


def _run(argv: list[str], cwd: Path) -> None:
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(argv)}\n{proc.stdout}\n{proc.stderr}")


def _diff_new_file(path: str, added_lines: list[str]) -> str:
    body = "\n".join(f"+{ln}" for ln in added_lines)
    return (
        f"diff --git a/{path} b/{path}\n"
        "new file mode 100644\n"
        "index 0000000..1111111\n"
        "--- /dev/null\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{len(added_lines)} @@\n"
        f"{body}\n"
    )


def _diff_modify(path: str, before: str, after: str) -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"-{before}\n"
        f"+{after}\n"
    )


class PatchFirstTests(unittest.TestCase):
    def test_normalize_rejects_absolute_drive_and_parent(self) -> None:
        with self.assertRaises(PatchValidationError):
            normalize_repo_relpath("/etc/passwd")
        with self.assertRaises(PatchValidationError):
            normalize_repo_relpath("C:/tmp/x.txt")
        with self.assertRaises(PatchValidationError):
            normalize_repo_relpath("../secrets.txt")

    def test_policy_rejects_deny_prefix(self) -> None:
        patch = _diff_new_file("runs/evil.txt", ["evil"])
        policy = PatchPolicy(allow_roots=("runs",), deny_prefixes=("runs",), deny_suffixes=())
        with self.assertRaises(PatchValidationError) as ctx:
            validate_diff_against_policy(patch, policy, ROOT)
        self.assertEqual(ctx.exception.code, "PATCH_POLICY_DENY")
        self.assertIn("deny_prefixes", str(ctx.exception))

    def test_policy_rejects_max_files(self) -> None:
        chunks = [_diff_new_file(f"docs/f{i}.md", ["x"]) for i in range(1, 7)]
        patch = "".join(chunks)
        with self.assertRaises(PatchValidationError) as ctx:
            validate_diff_against_policy(patch, PatchPolicy(max_files=5), ROOT)
        self.assertEqual(ctx.exception.code, "PATCH_POLICY_DENY")
        self.assertIn("max_files", str(ctx.exception))

    def test_policy_rejects_max_added_lines(self) -> None:
        added = [f"line-{i}" for i in range(401)]
        patch = _diff_new_file("docs/too_many_lines.md", added)
        with self.assertRaises(PatchValidationError) as ctx:
            validate_diff_against_policy(patch, PatchPolicy(max_added_lines=400), ROOT)
        self.assertEqual(ctx.exception.code, "PATCH_POLICY_DENY")
        self.assertIn("max_added_lines", str(ctx.exception))

    def test_git_apply_check_fail_and_safe_apply_fail(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _run(["git", "init"], repo)
            _run(["git", "config", "user.email", "test@example.com"], repo)
            _run(["git", "config", "user.name", "patch-first-test"], repo)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            _run(["git", "add", "README.md"], repo)
            _run(["git", "commit", "-m", "init"], repo)

            bad_patch = _diff_modify("README.md", "not-hello", "patched")
            rc, _, _ = git_apply_check(repo, bad_patch)
            self.assertNotEqual(rc, 0)

            result = apply_patch_safely(repo, bad_patch)
            self.assertFalse(result.ok)
            self.assertEqual(result.code, "PATCH_GIT_CHECK_FAIL")

    def test_safe_apply_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _run(["git", "init"], repo)
            _run(["git", "config", "user.email", "test@example.com"], repo)
            _run(["git", "config", "user.name", "patch-first-test"], repo)
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            _run(["git", "add", "README.md"], repo)
            _run(["git", "commit", "-m", "init"], repo)

            good_patch = _diff_modify("README.md", "hello", "patched")
            policy = PatchPolicy(allow_roots=("README.md",), deny_prefixes=(), deny_suffixes=())
            result = apply_patch_safely(repo, good_patch, policy)
            self.assertTrue(result.ok)
            self.assertEqual((repo / "README.md").read_text(encoding="utf-8"), "patched\n")


if __name__ == "__main__":
    unittest.main()
