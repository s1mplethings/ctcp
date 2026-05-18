from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import unittest
from pathlib import Path

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_business_materializers import materialize_business_files


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "concrete_project_matrix" / "fixtures" / "auth_api.json"


def _goal() -> str:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    endpoints = ", ".join(fixture["project_requirements"]["api"]["required_endpoints"])
    return f"{fixture['goal']} Required endpoints: {endpoints}. Persistence requirement: {fixture['project_requirements']['storage']}."


def _materialize() -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, object]]:
    temp = tempfile.TemporaryDirectory(prefix="ctcp_auth_generation_")
    run_dir = Path(temp.name)
    contract = normalize_output_contract_freeze(None, goal=_goal(), run_dir=run_dir)
    materialize_business_files(run_dir, _goal(), contract, ["matrix fixture"])
    return temp, run_dir / str(contract["project_root"]), contract


def _port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _json(method: str, url: str, payload: dict[str, object] | None = None, token: str = "") -> tuple[int, dict[str, object]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class AuthApiGenerationTests(unittest.TestCase):
    def test_auth_project_has_hashing_and_protected_endpoint(self) -> None:
        temp, project, contract = _materialize()
        self.addCleanup(temp.cleanup)
        self.assertEqual(contract["project_id"], "simple_auth_api")
        source = (project / "auth_store.py").read_text(encoding="utf-8")
        self.assertIn("pbkdf2_hmac", source)
        self.assertIn("sessions", source)
        self.assertFalse((project / "run_agent.py").exists())

    def test_generated_tests_and_runtime_auth_flow_pass(self) -> None:
        temp, project, _contract = _materialize()
        self.addCleanup(temp.cleanup)
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=project, capture_output=True, text=True, timeout=60)
        self.assertEqual(tests.returncode, 0, tests.stdout + tests.stderr)
        port = _port()
        db_path = project / "auth_test.db"
        proc = subprocess.Popen([sys.executable, str(project / "app.py"), "--host", "127.0.0.1", "--port", str(port), "--db", str(db_path)], cwd=project)
        try:
            base = f"http://127.0.0.1:{port}"
            for _ in range(50):
                try:
                    if _json("GET", base + "/status")[1]["status"] == "ok":
                        break
                except Exception:
                    time.sleep(0.1)
            self.assertEqual(_json("GET", base + "/me")[0], 401)
            self.assertEqual(_json("POST", base + "/register", {"username": "ada", "password": "secret"})[0], 201)
            status, login = _json("POST", base + "/login", {"username": "ada", "password": "secret"})
            self.assertEqual(status, 200)
            token = str(login["token"])
            self.assertEqual(_json("GET", base + "/me", token=token)[1]["user"]["username"], "ada")
            self.assertTrue(_json("POST", base + "/logout", token=token)[1]["logged_out"])
            self.assertEqual(_json("GET", base + "/me", token=token)[0], 401)
            self.assertTrue(db_path.exists())
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
