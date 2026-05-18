from __future__ import annotations

import json
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
import unittest
from pathlib import Path

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_business_materializers import materialize_business_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "full_stack_app_benchmark" / "fixtures" / "local_kanban_board_app.json"


def _goal() -> str:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    endpoints = ", ".join(fixture["project_requirements"]["api"]["required_endpoints"])
    assets = ", ".join(fixture["project_requirements"]["frontend"]["required_assets"])
    return f"{fixture['goal']} Required endpoints: {endpoints}. Required frontend assets: {assets}. Persistence requirement: {fixture['project_requirements']['storage']}."


def _materialize() -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
    temp = tempfile.TemporaryDirectory(prefix="ctcp_kanban_generation_", ignore_cleanup_errors=True)
    run_dir = Path(temp.name)
    contract = normalize_output_contract_freeze(None, goal=_goal(), run_dir=run_dir)
    materialize_business_files(run_dir, _goal(), contract, ["kanban fixture"])
    return temp, run_dir / str(contract["project_root"]), contract


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _json(method: str, url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


class KanbanAppGenerationTests(unittest.TestCase):
    def test_kanban_fast_path_contract_and_assets(self) -> None:
        temp, project, contract = _materialize()
        self.addCleanup(temp.cleanup)
        self.assertEqual(contract["project_id"], "local_kanban_board_app")
        self.assertEqual(contract["project_root"], "project_output/local_kanban_board_app")
        self.assertTrue((project / "static" / "index.html").exists())
        self.assertTrue((project / "static" / "app.js").exists())
        self.assertTrue((project / "static" / "styles.css").exists())
        self.assertTrue((project / "kanban_store.py").exists())
        self.assertFalse((project / "run_agent.py").exists())
        self.assertFalse((project / "runtime").exists())
        self.assertEqual(json.loads((project / "provenance.json").read_text(encoding="utf-8"))["project_type"], "local_kanban_board_app")

    def test_generated_tests_and_kanban_runtime_pass(self) -> None:
        temp, project, _contract = _materialize()
        self.addCleanup(temp.cleanup)
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=project, capture_output=True, text=True, timeout=60)
        self.assertEqual(tests.returncode, 0, tests.stdout + tests.stderr)
        port = _port()
        db_path = Path(tempfile.gettempdir()) / f"ctcp_kanban_{port}.db"
        if db_path.exists():
            db_path.unlink()
        proc = subprocess.Popen([sys.executable, str(project / "app.py"), "--host", "127.0.0.1", "--port", str(port), "--db", str(db_path)], cwd=project)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    if _json("GET", base + "/status")["status"] == "ok":
                        break
                except Exception:
                    time.sleep(0.1)
            html = _text(base + "/")
            js = _text(base + "/static/app.js")
            self.assertIn("Local Kanban Board", html)
            self.assertIn("fetch(", js)
            self.assertIn("moveCard", js)
            board = _json("POST", base + "/boards", {"name": "Focused Board"})
            board_id = board["id"]
            card = _json("POST", f"{base}/boards/{board_id}/cards", {"title": "Focused card", "description": "test", "column": "todo"})
            card_id = card["id"]
            self.assertEqual(len(_json("GET", f"{base}/boards/{board_id}/cards")["cards"]), 1)
            self.assertEqual(_json("PATCH", f"{base}/cards/{card_id}/move", {"column": "doing", "position": 1})["card"]["column"], "doing")
            self.assertEqual(_json("PATCH", f"{base}/cards/{card_id}", {"title": "Updated"})["card"]["title"], "Updated")
            self.assertTrue(_json("DELETE", f"{base}/cards/{card_id}")["deleted"])
            with sqlite3.connect(db_path) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='boards'").fetchone()[0], 1)
                self.assertEqual(conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='cards'").fetchone()[0], 1)
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)
            else:
                proc.wait(timeout=5)
            time.sleep(0.2)
            try:
                db_path.unlink()
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
