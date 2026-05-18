from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from pathlib import Path

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_business_materializers import materialize_business_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "concrete_project_matrix" / "fixtures" / "todo_api.json"


def _goal() -> str:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    endpoints = ", ".join(fixture["project_requirements"]["api"]["required_endpoints"])
    return f"{fixture['goal']} Required endpoints: {endpoints}. Persistence requirement: {fixture['project_requirements']['storage']}."


def _materialize() -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
    temp = tempfile.TemporaryDirectory(prefix="ctcp_todo_generation_")
    run_dir = Path(temp.name)
    contract = normalize_output_contract_freeze(None, goal=_goal(), run_dir=run_dir)
    materialize_business_files(run_dir, _goal(), contract, ["matrix fixture"])
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


class TodoApiGenerationTests(unittest.TestCase):
    def test_todo_project_contract_is_not_issue_tracker_clone(self) -> None:
        temp, project, contract = _materialize()
        self.addCleanup(temp.cleanup)
        self.assertEqual(contract["project_id"], "todo_rest_api")
        self.assertTrue((project / "todo_store.py").exists())
        self.assertFalse((project / "issue_store.py").exists())
        self.assertFalse((project / "run_agent.py").exists())

    def test_generated_tests_and_runtime_crud_pass(self) -> None:
        temp, project, _contract = _materialize()
        self.addCleanup(temp.cleanup)
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=project, capture_output=True, text=True, timeout=60)
        self.assertEqual(tests.returncode, 0, tests.stdout + tests.stderr)
        port = _port()
        db_path = project / "todo_test.db"
        proc = subprocess.Popen([sys.executable, str(project / "app.py"), "--host", "127.0.0.1", "--port", str(port), "--db", str(db_path)], cwd=project)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    if _json("GET", base + "/status")["status"] == "ok":
                        break
                except Exception:
                    time.sleep(0.1)
            created = _json("POST", base + "/todos", {"title": "Test"})
            todo_id = created["id"]
            self.assertEqual(len(_json("GET", base + "/todos")["todos"]), 1)
            self.assertTrue(_json("PATCH", f"{base}/todos/{todo_id}", {"completed": True})["todo"]["completed"])
            self.assertTrue(_json("DELETE", f"{base}/todos/{todo_id}")["deleted"])
            self.assertTrue(db_path.exists())
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
