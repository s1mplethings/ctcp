#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.retrieval import repo_search as new_search
from tools import local_librarian as old_search


class LlmCoreRepoSearchTests(unittest.TestCase):
    def test_new_search_repo_context_returns_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs").mkdir(parents=True, exist_ok=True)
            (repo / "docs" / "sample.md").write_text("alpha\nSEARCH_TOKEN\nomega\n", encoding="utf-8")
            rows = new_search.search_repo_context(repo, "SEARCH_TOKEN", k=8)
        self.assertEqual(len(rows), 1)
        first = rows[0]
        self.assertIn("path", first)
        self.assertIn("start_line", first)
        self.assertIn("end_line", first)
        self.assertIn("snippet", first)
        self.assertEqual(str(first["path"]), "docs/sample.md")
        self.assertGreaterEqual(int(first["start_line"]), 1)
        self.assertGreaterEqual(int(first["end_line"]), int(first["start_line"]))
        self.assertIn("SEARCH_TOKEN", str(first["snippet"]))

    def test_old_shim_keeps_python_fallback_patch_surface(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs").mkdir(parents=True, exist_ok=True)
            (repo / "docs" / "sample.md").write_text("alpha\nMATCH_TOKEN\nomega\n", encoding="utf-8")
            with mock.patch("tools.local_librarian.shutil.which", return_value=None):
                rows = old_search.search(repo, "MATCH_TOKEN", k=8)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["path"], "docs/sample.md")
        self.assertIn("MATCH_TOKEN", rows[0]["snippet"])

    def test_old_shim_keeps_rg_glob_surface(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs").mkdir(parents=True, exist_ok=True)

            captured: dict[str, list[str]] = {}

            def _fake_run(cmd, **kwargs):
                captured["cmd"] = list(cmd)
                return subprocess.CompletedProcess(cmd, 1, "", "")

            with mock.patch("tools.local_librarian.shutil.which", return_value="rg"):
                with mock.patch("tools.local_librarian.subprocess.run", side_effect=_fake_run):
                    rows = old_search.search(repo, "TOKEN", k=8)
        self.assertEqual(rows, [])
        self.assertIn("!**/.agent_private/**", captured.get("cmd", []))
        self.assertIs(old_search.search, new_search.search)


if __name__ == "__main__":
    unittest.main()
