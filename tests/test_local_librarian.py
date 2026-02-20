#!/usr/bin/env python3
from __future__ import annotations

import tempfile
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


if __name__ == "__main__":
    unittest.main()

