#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import local_librarian


class LocalLibrarianTests(unittest.TestCase):
    def test_search_returns_expected_fields(self) -> None:
        rows = local_librarian.search(ROOT, "def search(repo_root", k=8)
        self.assertTrue(rows, "expected at least one search result")
        first = rows[0]
        self.assertIn("path", first)
        self.assertIn("start_line", first)
        self.assertIn("end_line", first)
        self.assertIn("snippet", first)
        self.assertTrue(str(first["path"]).strip())
        self.assertGreaterEqual(int(first["start_line"]), 1)
        self.assertGreaterEqual(int(first["end_line"]), int(first["start_line"]))
        self.assertTrue(str(first["snippet"]).strip())

    def test_python_fallback_when_rg_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs").mkdir(parents=True, exist_ok=True)
            (repo / "docs" / "sample.md").write_text("alpha\nMATCH_TOKEN\nomega\n", encoding="utf-8")
            with mock.patch("tools.local_librarian.shutil.which", return_value=None):
                rows = local_librarian.search(repo, "MATCH_TOKEN", k=8)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["path"], "docs/sample.md")
            self.assertIn("MATCH_TOKEN", rows[0]["snippet"])

    def test_private_dir_is_excluded_from_python_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs" / ".agent_private").mkdir(parents=True, exist_ok=True)
            (repo / "docs" / "visible.md").write_text("alpha\nSECRET_TOKEN\nomega\n", encoding="utf-8")
            (repo / "docs" / ".agent_private" / "hidden.md").write_text(
                "alpha\nSECRET_TOKEN\nomega\n",
                encoding="utf-8",
            )
            with mock.patch("tools.local_librarian.shutil.which", return_value=None):
                rows = local_librarian.search(repo, "SECRET_TOKEN", k=8)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["path"], "docs/visible.md")

    def test_rg_search_adds_skip_globs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs").mkdir(parents=True, exist_ok=True)

            captured: dict[str, list[str]] = {}

            def _fake_run(cmd, **kwargs):
                captured["cmd"] = list(cmd)
                return subprocess.CompletedProcess(cmd, 1, "", "")

            with mock.patch("tools.local_librarian.shutil.which", return_value="rg"):
                with mock.patch("tools.local_librarian.subprocess.run", side_effect=_fake_run):
                    rows = local_librarian.search(repo, "TOKEN", k=8)
            self.assertEqual(rows, [])
            self.assertIn("!**/.agent_private/**", captured.get("cmd", []))


if __name__ == "__main__":
    unittest.main()
