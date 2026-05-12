from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.providers import api_source_chunking
from tools.providers.project_generation_contracts import (
    CONTRACT_GRAPH_ARTIFACT,
    converge_contract_graph,
    extract_contract_graph,
    load_generation_contract_context,
    validate_contract_graph,
    write_generation_contract_artifacts,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class GenerationConsistencyTests(unittest.TestCase):
    def test_contract_snapshots_extract_reconcile_and_repair_generated_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_generation_contracts_") as td:
            run_dir = Path(td)
            project = run_dir / "project_output" / "issue_api"
            _write(
                project / "src" / "issue_api" / "service.py",
                "\n".join(
                    [
                        "class IssueService:",
                        "    def __init__(self, db_path=':memory:'):",
                        "        self.db_path = db_path",
                        "    def create_issue(self, title, description):",
                        "        return {'id': 1, 'title': title, 'description': description}",
                        "    def get_issues(self):",
                        "        return []",
                        "    def get_issue(self, issue_id):",
                        "        return {'id': issue_id}",
                        "    def update_issue_status(self, issue_id, status):",
                        "        return {'id': issue_id, 'status': status}",
                    ]
                )
                + "\n",
            )
            _write(
                project / "src" / "issue_api" / "app.py",
                "\n".join(
                    [
                        "from issue_api.service import IssueService",
                        "def parse_path(path, pattern):",
                        "    return {'id': '1'} if pattern in {'/issues/{id}', '/issues/{id}/status'} else None",
                        "def create_app(service_inst):",
                        "    class Handler:",
                        "        def do_GET(self):",
                        "            path = '/issues'",
                        "            if path == '/issues':",
                        "                service_inst.list_issues()",
                        "            parse_path(path, '/issues/{id}')",
                        "        def do_POST(self):",
                        "            path = '/issues'",
                        "            if path == '/issues':",
                        "                service_inst.create_issue('a', 'b')",
                        "            parse_path(path, '/issues/{id}/close')",
                        "        def do_PATCH(self):",
                        "            path = '/issues/1/status'",
                        "            parse_path(path, '/issues/{id}/status')",
                        "            service_inst.update_status('1', 'closed')",
                        "    return Handler",
                    ]
                )
                + "\n",
            )
            _write(
                project / "tests" / "test_service.py",
                "\n".join(
                    [
                        "import os",
                        "import tempfile",
                        "from issue_api.service import IssueService",
                        "class TestIssueService:",
                        "    def setup_method(self):",
                        "        self.db_fd, self.db_path = tempfile.mkstemp()",
                        "        self.service = IssueService()",
                        "    def test_all(self):",
                        "        assert self.service.get_all_issues() == []",
                        "        titles = []",
                        "        self.assertIn('Sample Issue 1', titles)",
                        "    def teardown_method(self):",
                        "        os.close(self.db_fd)",
                        "        os.unlink(self.db_path)",
                    ]
                )
                + "\n",
            )
            _write(
                project / "src" / "issue_api" / "seed.py",
                "\n".join(
                    [
                        "def seed_sample_data(service):",
                        "    sample_issues = [",
                        "        {\"title\": \"Other\", \"description\": \"Other\"}",
                        "    ]",
                        "    for issue in sample_issues:",
                        "        service.create_issue(issue['title'], issue['description'])",
                    ]
                )
                + "\n",
            )
            _write(
                project / "scripts" / "run_project_web.py",
                "\n".join(
                    [
                        "import argparse",
                        "def main():",
                        "    parser = argparse.ArgumentParser()",
                        "    parser.add_argument('--serve', action='store_true')",
                        "    args = parser.parse_args()",
                        "    if args.serve:",
                        "        run_server(port=8000)",
                    ]
                )
                + "\n",
            )

            report = write_generation_contract_artifacts(
                run_dir,
                project_root="project_output/issue_api",
                entrypoint="project_output/issue_api/scripts/run_project_web.py",
                repair=True,
            )

            self.assertEqual(report["status"], "passed", report)
            self.assertTrue((run_dir / "artifacts" / "generated_symbols.json").exists())
            self.assertTrue((run_dir / "artifacts" / "generated_routes.json").exists())
            self.assertTrue((run_dir / "artifacts" / "runtime_contract.json").exists())
            self.assertTrue((run_dir / CONTRACT_GRAPH_ARTIFACT).exists())
            self.assertTrue((run_dir / "artifacts" / "reconciliation_report.json").exists())
            graph = json.loads((run_dir / CONTRACT_GRAPH_ARTIFACT).read_text(encoding="utf-8"))
            symbols = json.loads((run_dir / "artifacts" / "generated_symbols.json").read_text(encoding="utf-8"))
            routes = json.loads((run_dir / "artifacts" / "generated_routes.json").read_text(encoding="utf-8"))
            runtime = json.loads((run_dir / "artifacts" / "runtime_contract.json").read_text(encoding="utf-8"))
            self.assertEqual(graph["schema_version"], "ctcp-contract-graph-v1")
            self.assertTrue(graph["graph_hash"])
            self.assertEqual(graph["validation"]["status"], "passed")
            self.assertTrue(report["converged"])
            self.assertGreaterEqual(len(report["iterations"]), 2)
            self.assertIn("IssueService", symbols)
            self.assertIn("get_all_issues", symbols["IssueService"]["methods"])
            self.assertIn({"method": "GET", "path": "/issues", "handler": "src/issue_api/app.py:do_GET"}, routes["routes"])
            self.assertIn({"method": "PATCH", "path": "/issues/{id}/status", "handler": "src/issue_api/app.py:do_PATCH"}, routes["routes"])
            self.assertNotIn("--host", runtime["supported_cli_args"])
            self.assertEqual(runtime["default_port"], 8000)
            service_text = (project / "src" / "issue_api" / "service.py").read_text(encoding="utf-8")
            self.assertIn("def get_all_issues(self, *args, **kwargs):", service_text)
            self.assertIn("return self.get_issues(*args, **kwargs)", service_text)
            test_text = (project / "tests" / "test_service.py").read_text(encoding="utf-8")
            seed_text = (project / "src" / "issue_api" / "seed.py").read_text(encoding="utf-8")
            self.assertIn("self.db_fd = -1", test_text)
            self.assertIn('"title": "Sample Issue 1"', seed_text)

    def test_later_batch_prompt_consumes_shared_contract_snapshots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_contract_prompt_") as td:
            run_dir = Path(td)
            _write(
                run_dir / "artifacts" / "contract_graph.json",
                json.dumps(
                    {
                        "schema_version": "ctcp-contract-graph-v1",
                        "graph_hash": "abc123",
                        "nodes": {"method:IssueService.get_issues": {"kind": "symbol.method"}},
                    }
                ),
            )
            _write(
                run_dir / "artifacts" / "generated_symbols.json",
                json.dumps(
                    {
                        "schema_version": "ctcp-generated-symbols-v1",
                        "IssueService": {"type": "class", "methods": ["get_issues"]},
                        "symbols": {"IssueService": {"type": "class", "methods": ["get_issues"]}},
                    }
                ),
            )
            context = load_generation_contract_context(run_dir)
            prompt = api_source_chunking._batch_prompt(
                "base",
                ["project_output/app/tests/test_service.py"],
                2,
                3,
                interfaces={},
                contract_context=context,
            )

            self.assertIn("Current Shared Generation Contracts", prompt)
            self.assertIn("contract_graph.json", prompt)
            self.assertIn("get_issues", prompt)
            self.assertIn("single source of truth", prompt)

    def test_contract_graph_validation_reports_typed_drift_and_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_contract_graph_") as td:
            run_dir = Path(td)
            project = run_dir / "project_output" / "issue_api"
            _write(
                project / "src" / "issue_api" / "service.py",
                "\n".join(
                    [
                        "import sqlite3",
                        "class IssueService:",
                        "    def __init__(self):",
                        "        self._conn = sqlite3.connect(':memory:')",
                        "    def get_issues(self):",
                        "        with sqlite3.connect(':memory:') as conn:",
                        "            return Issue.from_row(conn.execute('select 1').fetchone())",
                    ]
                )
                + "\n",
            )
            _write(
                project / "src" / "issue_api" / "app.py",
                "\n".join(
                    [
                        "from issue_api.service import IssueService",
                        "def do_GET():",
                        "    service = IssueService()",
                        "    service.list_issues()",
                        "    return '/issues'",
                    ]
                )
                + "\n",
            )
            _write(
                project / "scripts" / "run_project_web.py",
                "def main():\n    pass\n",
            )

            graph = extract_contract_graph(run_dir, project_root="project_output/issue_api")
            validation = validate_contract_graph(graph, symbols={"conflicts": []})
            issue_types = {issue["type"] for issue in validation["issues"]}

            self.assertIn("symbol.missing_method", issue_types)
            self.assertIn("db.sqlite_row_factory_missing", issue_types)
            self.assertIn("resource.lifecycle_close_missing", issue_types)
            self.assertIn("src/issue_api/app.py", validation["targeted_regeneration_scope"])
            self.assertIn("src/issue_api/service.py", validation["targeted_regeneration_scope"])

    def test_contract_graph_convergence_writes_hash_iterations_and_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_contract_convergence_") as td:
            run_dir = Path(td)
            project = run_dir / "project_output" / "issue_api"
            _write(
                project / "src" / "issue_api" / "service.py",
                "\n".join(
                    [
                        "class IssueService:",
                        "    def get_issues(self):",
                        "        return []",
                    ]
                )
                + "\n",
            )
            _write(
                project / "src" / "issue_api" / "app.py",
                "\n".join(
                    [
                        "from issue_api.service import IssueService",
                        "def main():",
                        "    service = IssueService()",
                        "    return service.list_issues()",
                    ]
                )
                + "\n",
            )

            report = converge_contract_graph(run_dir, project_root="project_output/issue_api", repair=True)
            graph = json.loads((run_dir / CONTRACT_GRAPH_ARTIFACT).read_text(encoding="utf-8"))

            self.assertEqual(report["status"], "passed", report)
            self.assertTrue(report["converged"])
            self.assertTrue(report["graph_hash"])
            self.assertTrue(graph["graph_hash"])
            self.assertIn("iterations", report)
            self.assertIn("targeted_regeneration_scope", report)
            self.assertIn("def list_issues(self, *args, **kwargs):", (project / "src" / "issue_api" / "service.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
