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
FIXTURE = ROOT / "tests" / "concrete_project_benchmark" / "fixtures" / "issue_tracker_api.json"


def _goal_from_fixture() -> str:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    endpoints = ", ".join(str(item) for item in fixture["project_requirements"]["api"]["required_endpoints"])
    statuses = ", ".join(str(item) for item in fixture["project_requirements"]["issue_model"]["valid_statuses"])
    return (
        f"{fixture['goal']} Required endpoints: {endpoints}. "
        f"Use SQLite persistence. Valid issue statuses: {statuses}. "
        "Generate the concrete project files, tests, README, runnable local HTTP server, and delivery package."
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(method: str, url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def _materialize_project() -> tuple[tempfile.TemporaryDirectory[str], Path]:
    temp = tempfile.TemporaryDirectory(prefix="ctcp_issue_tracker_runtime_")
    run_dir = Path(temp.name)
    goal = _goal_from_fixture()
    contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
    materialize_business_files(run_dir, goal, contract, ["test context"])
    return temp, run_dir / str(contract["project_root"])


class ConcreteProjectRuntimeContractTests(unittest.TestCase):
    def test_app_supports_host_port_and_server_stays_alive(self) -> None:
        temp, project = _materialize_project()
        self.addCleanup(temp.cleanup)
        port = _free_port()
        db_path = project / "runtime_test_issues.db"
        proc = subprocess.Popen(
            [sys.executable, str(project / "app.py"), "--host", "127.0.0.1", "--port", str(port), "--db", str(db_path)],
            cwd=project,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.addCleanup(lambda: proc.kill() if proc.poll() is None else None)
        base = f"http://127.0.0.1:{port}"
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                if _http_json("GET", base + "/status")["status"] == "ok":
                    break
            except Exception:
                time.sleep(0.2)
        else:
            self.fail("server did not start")

        created = _http_json("POST", base + "/issues", {"title": "Runtime issue", "description": "Created by test"})
        issue_id = str(created["id"])
        self.assertEqual(_http_json("GET", base + "/issues")["issues"][0]["title"], "Runtime issue")
        self.assertEqual(_http_json("GET", f"{base}/issues/{issue_id}")["issue"]["id"], int(issue_id))
        self.assertEqual(_http_json("PATCH", f"{base}/issues/{issue_id}/status", {"status": "in_progress"})["issue"]["status"], "in_progress")
        self.assertEqual(_http_json("POST", f"{base}/issues/{issue_id}/close")["issue"]["status"], "closed")
        self.assertTrue(db_path.exists())
        self.assertIsNone(proc.poll())

        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
