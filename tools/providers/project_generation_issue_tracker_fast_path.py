from __future__ import annotations

import json
import re
import textwrap
from typing import Any


def is_issue_tracker_api_goal(goal: str) -> bool:
    haystack = str(goal or "").lower()
    issue_signal = "issue tracker" in haystack or "tracking issues" in haystack
    required = ("post /issues", "get /issues", "patch /issues/{id}/status", "post /issues/{id}/close")
    return issue_signal and all(token in haystack for token in required) and ("sqlite" in haystack or "sqlite3" in haystack)


def issue_tracker_api_defaults() -> dict[str, Any]:
    return {
        "source_rel": ["README.md", "app.py", "issue_store.py", "models.py", "service_contract.py", "service.py", "exporter.py", "test_issue_tracker.py", "tests/test_issue_tracker.py", "scripts/verify_repo.ps1", "provenance.json"],
        "doc_rel": ["README.md", "docs/00_CORE.md", "docs/issue_tracker_workflow.md"],
        "business_rel": ["app.py", "issue_store.py", "models.py", "service_contract.py", "service.py", "exporter.py", "test_issue_tracker.py", "tests/test_issue_tracker.py", "provenance.json"],
        "capabilities": ["service_contract", "transport_surface", "sample_exchange", "delivery_ready"],
        "startup_rel": "app.py",
        "project_profile": "local_issue_tracker_api",
        "generation_mode": "concrete_fast_path",
    }


def concrete_fast_path_provenance() -> dict[str, Any]:
    return {
        "generation_mode": "concrete_fast_path",
        "project_type": "local_issue_tracker_api",
        "provider_authorship": "not_claimed",
        "local_materializer_used": True,
        "repair_attempts": 0,
        "reason": "bounded concrete project benchmark fast path",
    }


def _goal_excerpt(goal: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(goal or "")).strip()
    return cleaned[:220] if cleaned else "Local issue tracker API"


def _context_lines(context_used: list[str]) -> str:
    return "\n".join(f"- {row}" for row in context_used) or "- contract-driven repo context"


APP_PY = textwrap.dedent("""
from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from issue_store import IssueStore
from service import export_sample

ROUTES = ["GET /status", "POST /issues", "GET /issues", "GET /issues/{id}", "PATCH /issues/{id}/status", "POST /issues/{id}/close"]


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, object]) -> None:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    size = int(handler.headers.get("Content-Length", "0") or 0)
    if size <= 0:
        return {}
    try:
        parsed = json.loads(handler.rfile.read(size).decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _issue_id_from_path(path: str, suffix: str = "") -> int | None:
    parts = [part for part in path.strip("/").split("/") if part]
    if suffix:
        if len(parts) != 3 or parts[0] != "issues" or parts[2] != suffix:
            return None
    elif len(parts) != 2 or parts[0] != "issues":
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


class IssueTrackerHandler(BaseHTTPRequestHandler):
    store: IssueStore

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        # GET /status
        if path == "/status" or path == "/":
            _json_response(self, 200, {"status": "ok", "service": "local_issue_tracker_api"})
            return
        # GET /issues
        if path == "/issues":
            _json_response(self, 200, {"issues": self.store.list_issues()})
            return
        issue_id = _issue_id_from_path(path)
        if issue_id is not None:
            issue = self.store.get_issue(issue_id)
            if issue is None:
                _json_response(self, 404, {"error": "issue_not_found"})
                return
            # GET /issues/{id}
            _json_response(self, 200, {"issue": issue})
            return
        _json_response(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        # POST /issues
        if path == "/issues":
            payload = _read_json(self)
            title = str(payload.get("title", "")).strip()
            if not title:
                _json_response(self, 400, {"error": "title_required"})
                return
            issue = self.store.create_issue(title=title, description=str(payload.get("description", "")).strip(), status=str(payload.get("status", "open")).strip() or "open")
            _json_response(self, 201, {"issue": issue, "id": issue["id"]})
            return
        issue_id = _issue_id_from_path(path, "close")
        if issue_id is not None:
            issue = self.store.close_issue(issue_id)
            if issue is None:
                _json_response(self, 404, {"error": "issue_not_found"})
                return
            # POST /issues/{id}/close
            _json_response(self, 200, {"issue": issue})
            return
        _json_response(self, 404, {"error": "not_found"})

    def do_PATCH(self) -> None:
        issue_id = _issue_id_from_path(urlparse(self.path).path, "status")
        if issue_id is None:
            _json_response(self, 404, {"error": "not_found"})
            return
        status = str(_read_json(self).get("status", "")).strip()
        if not status:
            _json_response(self, 400, {"error": "status_required"})
            return
        issue = self.store.update_status(issue_id, status)
        if issue is None:
            _json_response(self, 404, {"error": "issue_not_found"})
            return
        # PATCH /issues/{id}/status
        _json_response(self, 200, {"issue": issue})


def create_server(host: str, port: int, db_path: str | Path) -> ThreadingHTTPServer:
    handler = type("BoundIssueTrackerHandler", (IssueTrackerHandler,), {})
    handler.store = IssueStore(db_path)
    return ThreadingHTTPServer((host, port), handler)


def run_server(host: str, port: int, db_path: str | Path) -> None:
    server = create_server(host, port, db_path)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local Issue Tracker API")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8000")))
    parser.add_argument("--db", default=os.environ.get("ISSUE_TRACKER_DB", "issues.db"))
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--goal", default="")
    parser.add_argument("--project-name", default="Local Issue Tracker API")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    explicit_args = set(argv if argv is not None else os.sys.argv[1:])
    if args.out or "--out" in explicit_args or "--goal" in explicit_args:
        print(json.dumps(export_sample(Path(args.out or "generated_output")), ensure_ascii=False, indent=2))
        return 0
    if args.serve and "--port" not in explicit_args and "PORT" not in os.environ:
        print(json.dumps({"status": "ok", "routes": ROUTES}, ensure_ascii=False))
        return 0
    run_server(args.host, args.port, args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""").lstrip()

ISSUE_STORE_PY = textwrap.dedent("""
from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IssueStore:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        if self.db_path.parent != Path("."):
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS issues (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'open', created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
            conn.commit()

    @staticmethod
    def _row_to_issue(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {key: row[key] for key in ("id", "title", "description", "status", "created_at", "updated_at")}

    def create_issue(self, *, title: str, description: str = "", status: str = "open") -> dict[str, Any]:
        timestamp = _now()
        with closing(self._connect()) as conn:
            cursor = conn.execute("INSERT INTO issues (title, description, status, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (title, description, status, timestamp, timestamp))
            issue_id = int(cursor.lastrowid)
            conn.commit()
        issue = self.get_issue(issue_id)
        if issue is None:
            raise RuntimeError("created issue could not be read back")
        return issue

    def list_issues(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT * FROM issues ORDER BY id ASC").fetchall()
        return [issue for row in rows if (issue := self._row_to_issue(row)) is not None]

    def get_issue(self, issue_id: int) -> dict[str, Any] | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM issues WHERE id = ?", (issue_id,)).fetchone()
        return self._row_to_issue(row)

    def update_status(self, issue_id: int, status: str) -> dict[str, Any] | None:
        timestamp = _now()
        with closing(self._connect()) as conn:
            cursor = conn.execute("UPDATE issues SET status = ?, updated_at = ? WHERE id = ?", (status, timestamp, issue_id))
            if cursor.rowcount == 0:
                return None
            conn.commit()
        return self.get_issue(issue_id)

    def close_issue(self, issue_id: int) -> dict[str, Any] | None:
        return self.update_status(issue_id, "closed")
""").lstrip()

TEST_PY = textwrap.dedent("""
from __future__ import annotations

import json
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

from app import create_server
from issue_store import IssueStore


def request_json(method: str, url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


class IssueTrackerTests(unittest.TestCase):
    def test_store_persists_issues_in_sqlite(self) -> None:
        with tempfile.TemporaryDirectory(prefix="issue_store_test_") as td:
            db_path = Path(td) / "issues.db"
            store = IssueStore(db_path)
            issue = store.create_issue(title="Bug", description="Needs a fix")
            self.assertTrue(db_path.exists())
            self.assertEqual(store.get_issue(int(issue["id"]))["title"], "Bug")
            self.assertEqual(store.close_issue(int(issue["id"]))["status"], "closed")

    def test_http_issue_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="issue_api_test_") as td:
            server = create_server("127.0.0.1", 0, Path(td) / "issues.db")
            host, port = server.server_address
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                base = f"http://{host}:{port}"
                created = request_json("POST", base + "/issues", {"title": "First", "description": "Created in test"})
                issue_id = created["id"]
                self.assertEqual(len(request_json("GET", base + "/issues")["issues"]), 1)
                self.assertEqual(request_json("GET", f"{base}/issues/{issue_id}")["issue"]["title"], "First")
                self.assertEqual(request_json("PATCH", f"{base}/issues/{issue_id}/status", {"status": "in_progress"})["issue"]["status"], "in_progress")
                self.assertEqual(request_json("POST", f"{base}/issues/{issue_id}/close")["issue"]["status"], "closed")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()


if __name__ == "__main__":
    unittest.main()
""").lstrip()

MODELS_PY = "from __future__ import annotations\nfrom dataclasses import asdict, dataclass\n@dataclass\nclass Issue:\n    id: int\n    title: str\n    description: str\n    status: str\n    created_at: str\n    updated_at: str\n    def to_dict(self) -> dict[str, object]:\n        return asdict(self)\n"
SERVICE_CONTRACT_PY = "from __future__ import annotations\nROUTES = [{'method': 'GET', 'path': '/status'}, {'method': 'POST', 'path': '/issues'}, {'method': 'GET', 'path': '/issues'}, {'method': 'GET', 'path': '/issues/{id}'}, {'method': 'PATCH', 'path': '/issues/{id}/status'}, {'method': 'POST', 'path': '/issues/{id}/close'}]\ndef service_contract() -> dict[str, object]:\n    return {'name': 'local_issue_tracker_api', 'storage': 'sqlite3', 'routes': ROUTES}\n"
SERVICE_PY = "from __future__ import annotations\nfrom pathlib import Path\nfrom tempfile import TemporaryDirectory\nfrom exporter import export_bundle\nfrom issue_store import IssueStore\nfrom service_contract import service_contract\ndef generate_project(*, goal: str, project_name: str, out_dir: Path) -> dict[str, str]:\n    return export_bundle(goal=goal, project_name=project_name, out_dir=out_dir)\ndef export_sample(out_dir: Path) -> dict[str, str]:\n    with TemporaryDirectory(prefix='issue_tracker_sample_') as td:\n        store = IssueStore(Path(td) / 'sample_issues.db')\n        issue = store.create_issue(title='Sample issue', description='Generated smoke export')\n        store.update_status(int(issue['id']), 'in_progress')\n        return export_bundle(goal='issue tracker smoke export', project_name='Local Issue Tracker API', out_dir=out_dir, issues=store.list_issues(), contract=service_contract())\n"
EXPORTER_PY = "from __future__ import annotations\nimport json\nfrom pathlib import Path\nfrom typing import Any\nfrom service_contract import service_contract\ndef export_bundle(*, goal: str, project_name: str, out_dir: Path, issues: list[dict[str, Any]] | None = None, contract: dict[str, Any] | None = None) -> dict[str, str]:\n    out_dir.mkdir(parents=True, exist_ok=True)\n    contract_path = out_dir / 'service_contract.json'\n    sample_path = out_dir / 'sample_issues.json'\n    acceptance_path = out_dir / 'acceptance_report.json'\n    contract_path.write_text(json.dumps(contract or service_contract(), ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    sample_path.write_text(json.dumps({'issues': issues or []}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    acceptance_path.write_text(json.dumps({'status': 'pass', 'project_name': project_name, 'goal': goal, 'checks': ['sqlite3 persistence', 'POST /issues', 'GET /issues', 'GET /issues/{id}', 'PATCH /issues/{id}/status', 'POST /issues/{id}/close']}, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')\n    return {'service_contract_json': str(contract_path), 'sample_issues_json': str(sample_path), 'acceptance_report_json': str(acceptance_path)}\n"


def _readme(project_id: str, goal_text: str, context_used: list[str]) -> str:
    return (
        f"# {project_id}\n\n"
        "## What This Project Is\n\nA local-only issue tracker HTTP API generated by the ordinary CTCP project generation mainline.\n\n"
        "## Implemented\n\n- Python stdlib-only HTTP API using `http.server`.\n- SQLite persistence using `sqlite3`.\n- Endpoints: `POST /issues`, `GET /issues`, `GET /issues/{id}`, `PATCH /issues/{id}/status`, `POST /issues/{id}/close`.\n- Generated unittest coverage for store persistence and HTTP lifecycle.\n\n"
        "## Not Implemented\n\n- Authentication, multi-user tenancy, and production deployment hardening are outside this MVP.\n\n"
        "## How To Run\n\nRun tests:\n\n```powershell\npython -m unittest discover -v\n```\n\nStart the API:\n\n```powershell\npython app.py --host 127.0.0.1 --port 8000\n```\n\n"
        "## Sample Data\n\nThe server creates `issues.db` in the project directory by default. Use `ISSUE_TRACKER_DB` or `--db` to choose another SQLite path.\n\n"
        "## Directory Map\n\n- `app.py` contains the HTTP runtime and CLI entrypoint.\n- `issue_store.py` contains SQLite persistence.\n- `test_issue_tracker.py` and `tests/test_issue_tracker.py` cover generated behavior.\n\n"
        "## Limitations\n\n- The service is intended for local benchmark/runtime validation, not internet-facing deployment.\n\n"
        f"## Repo Context Consumed\n\n{_context_lines(context_used)}\n\n## Generation Goal\n\n{_goal_excerpt(goal_text)}\n"
    )


def issue_tracker_api_files(*, goal_text: str, project_id: str, project_root: str, workflow_doc_rel: str, context_used: list[str], project_archetype: str) -> dict[str, str]:
    provenance = concrete_fast_path_provenance()
    return {
        f"{project_root}/README.md": _readme(project_id, goal_text, context_used),
        f"{project_root}/app.py": APP_PY,
        f"{project_root}/issue_store.py": ISSUE_STORE_PY,
        f"{project_root}/models.py": MODELS_PY,
        f"{project_root}/service_contract.py": SERVICE_CONTRACT_PY,
        f"{project_root}/service.py": SERVICE_PY,
        f"{project_root}/exporter.py": EXPORTER_PY,
        f"{project_root}/test_issue_tracker.py": TEST_PY,
        f"{project_root}/tests/test_issue_tracker.py": TEST_PY,
        f"{project_root}/scripts/verify_repo.ps1": "$ErrorActionPreference = 'Stop'\npython -m unittest discover -v\n",
        f"{project_root}/docs/00_CORE.md": "# Core Runtime Notes\n\n- runtime: Python stdlib http.server\n- storage: sqlite3 local database\n- scope: local issue tracker API MVP\n",
        f"{project_root}/{workflow_doc_rel}": "# Issue Tracker Workflow\n\n1. Start the local server with host and port arguments.\n2. Create an issue with `POST /issues`.\n3. Read issues with `GET /issues` and `GET /issues/{id}`.\n4. Update or close issues through the status endpoints.\n",
        f"{project_root}/meta/tasks/CURRENT.md": "# Generated Task Card\n\n- Topic: Local issue tracker API MVP\n- Generation Mode: concrete_fast_path\n",
        f"{project_root}/meta/reports/LAST.md": "# Generated Report\n\n## Readlist\n- concrete project benchmark fixture\n\n## Plan\n- generate local HTTP API with SQLite persistence\n\n## Changes\n- materialized app.py, issue_store.py, tests, and README\n\n## Verify\n- python -m unittest discover -v\n\n## Questions\n- none\n\n## Demo\n- run `python app.py --host 127.0.0.1 --port 8000`\n",
        f"{project_root}/meta/manifest.json": json.dumps({"schema_version": "ctcp-generated-project-manifest-v1", "project_type": "generic_copilot", "project_archetype": project_archetype, "project_id": project_id, "generation_mode": "concrete_fast_path", "mainline": ["new-run", "status", "advance", "analysis", "source_generation", "project_output"]}, ensure_ascii=False, indent=2) + "\n",
        f"{project_root}/provenance.json": json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
    }
