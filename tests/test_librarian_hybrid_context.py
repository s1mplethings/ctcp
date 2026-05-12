from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.ctcp_librarian as ctcp_librarian
from tools.librarian_context_pack import build_context_pack, build_librarian_context_pack


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _make_repo(repo: Path) -> None:
    (repo / "ai_context").mkdir(parents=True, exist_ok=True)
    (repo / "docs").mkdir(parents=True, exist_ok=True)
    (repo / "meta" / "reports" / "archive").mkdir(parents=True, exist_ok=True)
    (repo / "library_docs" / "typer").mkdir(parents=True, exist_ok=True)
    (repo / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
    (repo / "PATCH_README.md").write_text("# patch readme\n", encoding="utf-8")
    (repo / "ai_context" / "00_AI_CONTRACT.md").write_text("# ai contract\n", encoding="utf-8")
    (repo / "ai_context" / "CTCP_FAST_RULES.md").write_text("# fast rules\n", encoding="utf-8")
    (repo / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
    (repo / "docs" / "source_generation_library_first.md").write_text(
        "source_generation must use library_first glue code and provider authored files.\n",
        encoding="utf-8",
    )
    (repo / "meta" / "reports" / "archive" / "failure.md").write_text(
        "source_generation blocked failure: missing typer import and custom table renderer.\n",
        encoding="utf-8",
    )
    (repo / "library_docs" / "typer" / "commands.md").write_text(
        "Typer command routing uses typer.Typer and avoids manual sys.argv parsing.\n",
        encoding="utf-8",
    )


class LibrarianHybridContextTests(unittest.TestCase):
    def test_sparse_request_emits_hybrid_trace_selected_context_and_constraints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_librarian_hybrid_repo_") as td:
            repo = Path(td)
            _make_repo(repo)
            file_request = {
                "schema_version": "ctcp-file-request-v1",
                "goal": "source_generation library_first typer failure repair context",
                "needs": [],
                "budget": {"max_files": 12, "max_total_bytes": 40000},
                "reason": "source_generation library_first",
                "project_domain": "local_cli_app",
            }

            doc = build_context_pack(file_request, repo_root=repo, get_repo_slug_fn=lambda _root: "fixture")

            trace = dict(doc.get("retrieval_trace", {}))
            self.assertEqual(trace.get("schema_version"), "ctcp-retrieval-trace-v1")
            stages = [row.get("stage") for row in trace.get("stages", []) if isinstance(row, dict)]
            self.assertIn("keyword_search", stages)
            self.assertIn("token_vector_search", stages)
            selected_paths = [row.get("source") for row in doc.get("selected_context", []) if isinstance(row, dict)]
            self.assertIn("library_docs/typer/commands.md", selected_paths)
            self.assertIn("meta/reports/archive/failure.md", selected_paths)
            constraints = "\n".join(str(item) for item in doc.get("constraints_for_downstream_agents", []))
            self.assertIn("Librarian provides evidence", constraints)
            self.assertIn("library", constraints.lower())

    def test_librarian_companion_pack_shape_is_derived_from_context_pack(self) -> None:
        context_pack = {
            "schema_version": "ctcp-context-pack-v1",
            "goal": "VN CLI",
            "selected_context": [{"source": "library_docs/typer/commands.md", "snippets": ["typer.Typer"]}],
            "constraints_for_downstream_agents": ["Use libraries directly."],
            "missing_context": [],
            "retrieval_trace": {"schema_version": "ctcp-retrieval-trace-v1", "selected": []},
            "knowledge_summary": {"boundary": "evidence_only_not_task_assignment"},
        }

        doc = build_librarian_context_pack(context_pack)

        self.assertEqual(doc["schema_version"], "ctcp-librarian-context-pack-v1")
        self.assertEqual(doc["query"], "VN CLI")
        self.assertEqual(doc["context_pack_ref"], "artifacts/context_pack.json")
        self.assertGreater(doc["confidence"], 0)

    def test_ctcp_librarian_writes_companion_librarian_context_pack(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_librarian_hybrid_repo_") as repo_td, tempfile.TemporaryDirectory(
            prefix="ctcp_librarian_hybrid_run_"
        ) as run_td:
            repo = Path(repo_td)
            run_dir = Path(run_td)
            _make_repo(repo)
            _write_json(
                run_dir / "artifacts" / "file_request.json",
                {
                    "schema_version": "ctcp-file-request-v1",
                    "goal": "source_generation library_first typer failure repair context",
                    "needs": [],
                    "budget": {"max_files": 12, "max_total_bytes": 40000},
                    "reason": "source_generation library_first",
                },
            )

            with mock.patch.object(ctcp_librarian, "ROOT", repo), mock.patch.object(
                ctcp_librarian, "LAST_RUN_POINTER", repo / "meta" / "run_pointers" / "LAST_RUN.txt"
            ), mock.patch.object(sys, "argv", ["ctcp_librarian.py", "--run-dir", str(run_dir)]):
                rc = ctcp_librarian.main()

            self.assertEqual(rc, 0)
            context_pack = json.loads((run_dir / "artifacts" / "context_pack.json").read_text(encoding="utf-8"))
            librarian_pack = json.loads((run_dir / "artifacts" / "librarian_context_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(context_pack["schema_version"], "ctcp-context-pack-v1")
            self.assertEqual(librarian_pack["schema_version"], "ctcp-librarian-context-pack-v1")
            self.assertEqual(librarian_pack["retrieval_trace"]["schema_version"], "ctcp-retrieval-trace-v1")


if __name__ == "__main__":
    unittest.main()
