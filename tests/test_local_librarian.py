#!/usr/bin/env python3
from __future__ import annotations

import json
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
import scripts.ctcp_librarian as ctcp_librarian


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _make_minimal_librarian_repo(repo: Path) -> None:
    (repo / "ai_context").mkdir(parents=True, exist_ok=True)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "workspace").mkdir(parents=True, exist_ok=True)
    (repo / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (repo / "ai_context" / "00_AI_CONTRACT.md").write_text("# ai contract\n", encoding="utf-8")
    (repo / "ai_context" / "CTCP_FAST_RULES.md").write_text("# fast rules\n", encoding="utf-8")
    (repo / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
    (repo / "PATCH_README.md").write_text("# patch readme\n", encoding="utf-8")
    (repo / "workspace" / "fixture.txt").write_text("fixture line 1\nfixture line 2\n", encoding="utf-8")


class LocalLibrarianTests(unittest.TestCase):
    def test_search_returns_expected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            (repo / "docs").mkdir(parents=True, exist_ok=True)
            (repo / "docs" / "sample.md").write_text("alpha\nSEARCH_TOKEN\nomega\n", encoding="utf-8")
            rows = local_librarian.search(repo, "SEARCH_TOKEN", k=8)
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

    def test_ctcp_librarian_generates_context_pack_from_file_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_librarian_repo_") as repo_td, tempfile.TemporaryDirectory(
            prefix="ctcp_librarian_run_"
        ) as run_td:
            repo = Path(repo_td)
            run_dir = Path(run_td)
            _make_minimal_librarian_repo(repo)
            _write_json(
                run_dir / "artifacts" / "file_request.json",
                {
                    "schema_version": "ctcp-file-request-v1",
                    "goal": "collect fixture context",
                    "needs": [
                        {
                            "path": "workspace/fixture.txt",
                            "mode": "full",
                        }
                    ],
                    "budget": {"max_files": 8, "max_total_bytes": 20000},
                    "reason": "contract test",
                },
            )

            with mock.patch.object(ctcp_librarian, "ROOT", repo), mock.patch.object(
                ctcp_librarian, "LAST_RUN_POINTER", repo / "meta" / "run_pointers" / "LAST_RUN.txt"
            ), mock.patch.object(
                sys,
                "argv",
                ["ctcp_librarian.py", "--run-dir", str(run_dir)],
            ):
                rc = ctcp_librarian.main()

            self.assertEqual(rc, 0)
            context_path = run_dir / "artifacts" / "context_pack.json"
            self.assertTrue(context_path.exists())
            doc = json.loads(context_path.read_text(encoding="utf-8"))
            self.assertEqual(str(doc.get("schema_version", "")), "ctcp-context-pack-v1")
            self.assertTrue(any(str(row.get("path", "")) == "workspace/fixture.txt" for row in list(doc.get("files", []))))
            self.assertFalse((run_dir / "artifacts" / "context_pack.failure.json").exists())

    def test_ctcp_librarian_compat_build_context_pack_wrapper_supports_stub_runner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_librarian_repo_") as repo_td:
            repo = Path(repo_td)
            _make_minimal_librarian_repo(repo)
            file_request = {
                "schema_version": "ctcp-file-request-v1",
                "goal": "compat wrapper",
                "needs": [{"path": "workspace/fixture.txt", "mode": "full"}],
                "budget": {"max_files": 8, "max_total_bytes": 20000},
                "reason": "stub runner compatibility",
            }

            with mock.patch.object(ctcp_librarian, "ROOT", repo):
                doc = ctcp_librarian._build_context_pack(file_request)

            self.assertEqual(str(doc.get("schema_version", "")), "ctcp-context-pack-v1")
            self.assertTrue(any(str(row.get("path", "")) == "workspace/fixture.txt" for row in list(doc.get("files", []))))

    def test_ctcp_librarian_records_structured_failure_for_invalid_request_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_librarian_repo_") as repo_td, tempfile.TemporaryDirectory(
            prefix="ctcp_librarian_run_"
        ) as run_td:
            repo = Path(repo_td)
            run_dir = Path(run_td)
            _make_minimal_librarian_repo(repo)
            _write_json(
                run_dir / "artifacts" / "file_request.json",
                {
                    "schema_version": "broken-file-request",
                    "goal": "broken request",
                    "needs": [],
                    "budget": {"max_files": 8, "max_total_bytes": 20000},
                    "reason": "contract test",
                },
            )

            with mock.patch.object(ctcp_librarian, "ROOT", repo), mock.patch.object(
                ctcp_librarian, "LAST_RUN_POINTER", repo / "meta" / "run_pointers" / "LAST_RUN.txt"
            ), mock.patch.object(
                sys,
                "argv",
                ["ctcp_librarian.py", "--run-dir", str(run_dir)],
            ):
                rc = ctcp_librarian.main()

            self.assertEqual(rc, 1)
            self.assertFalse((run_dir / "artifacts" / "context_pack.json").exists())
            failure_path = run_dir / "artifacts" / "context_pack.failure.json"
            self.assertTrue(failure_path.exists())
            failure = json.loads(failure_path.read_text(encoding="utf-8"))
            self.assertEqual(str(failure.get("schema_version", "")), "ctcp-context-pack-failure-v1")
            self.assertEqual(str(failure.get("error_code", "")), "invalid_schema")
            self.assertEqual(str(failure.get("stage", "")), "validate_request")
            self.assertIn("ctcp-file-request-v1", str(failure.get("message", "")))


if __name__ == "__main__":
    unittest.main()
