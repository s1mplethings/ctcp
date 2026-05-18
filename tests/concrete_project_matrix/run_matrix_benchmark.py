from __future__ import annotations

import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
GENERATED = Path(__file__).resolve().parent / "generated"
REPORT = Path(__file__).resolve().parent / "benchmark_report.md"
PROJECTS = ("todo_rest_api", "markdown_notes_api", "simple_auth_api")
FIXTURE_BY_PROJECT = {
    "todo_rest_api": "todo_api.json",
    "markdown_notes_api": "notes_api.json",
    "simple_auth_api": "auth_api.json",
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _goal_from_fixture(path: Path) -> str:
    fixture = _read_json(path)
    endpoints = ", ".join(str(item) for item in fixture["project_requirements"]["api"]["required_endpoints"])
    storage = str(fixture["project_requirements"]["storage"])
    return (
        f"{fixture['goal']} Required endpoints: {endpoints}. "
        f"Persistence requirement: {storage}. "
        "Generate the concrete project files, tests, README, runnable local HTTP server, and delivery package."
    )


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_concrete_project_matrix_runs").resolve())
    env["CTCP_ANALYSIS_PROFILE"] = "fast"
    env.pop("CTCP_FORCE_PROVIDER", None)
    env.pop("CTCP_ALLOW_LOCAL_MAINLINE_PROVIDER", None)
    return env


def _run(cmd: list[str], *, env: dict[str, str], cwd: Path = ROOT, timeout: int = 120) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "exit_code": int(proc.returncode),
            "duration_seconds": round(time.time() - started, 3),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "exit_code": 124,
            "duration_seconds": round(time.time() - started, 3),
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "timed_out": True,
        }


def _run_dir_from_output(row: dict[str, Any]) -> Path:
    text = f"{row.get('stdout', '')}\n{row.get('stderr', '')}"
    match = re.search(r"run_dir=([^\r\n]+)", text)
    if match:
        return Path(match.group(1).strip()).resolve()
    pointer = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
    if pointer.exists():
        return Path(pointer.read_text(encoding="utf-8").strip()).resolve()
    raise RuntimeError("could not locate run_dir")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(method: str, url: str, payload: dict[str, object] | None = None, token: str = "") -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=5) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode("utf-8"))


def _start_server(project: str, project_dir: Path) -> tuple[subprocess.Popen[str], str, Path]:
    port = _free_port()
    evidence = project_dir / f"matrix_{project}"
    cmd = [sys.executable, str(project_dir / "app.py"), "--host", "127.0.0.1", "--port", str(port)]
    persistence_path = evidence
    if project in {"todo_rest_api", "simple_auth_api"}:
        persistence_path = evidence.with_suffix(".db")
        cmd += ["--db", str(persistence_path)]
    if project == "markdown_notes_api":
        cmd += ["--notes-dir", str(evidence)]
    proc = subprocess.Popen(cmd, cwd=project_dir, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 20
    while time.time() < deadline:
        if proc.poll() is not None:
            detail = ""
            try:
                detail = (proc.stderr.read() if proc.stderr else "")[-800:]
            except Exception:
                detail = ""
            raise RuntimeError(f"{project} server exited before readiness: {detail}")
        try:
            status, payload = _http_json("GET", base + "/status")
            if status == 200 and payload.get("status") == "ok":
                return proc, base, persistence_path
        except Exception:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError(f"{project} server did not start")


def _validate_todo(project_dir: Path) -> dict[str, Any]:
    proc, base, db_path = _start_server("todo_rest_api", project_dir)
    try:
        created = _http_json("POST", base + "/todos", {"title": "Matrix todo"})[1]
        todo_id = created["id"]
        listed = _http_json("GET", base + "/todos")[1]["todos"]
        updated = _http_json("PATCH", f"{base}/todos/{todo_id}", {"completed": True})[1]["todo"]
        deleted = _http_json("DELETE", f"{base}/todos/{todo_id}")[1]["deleted"]
        with sqlite3.connect(db_path) as conn:
            table_count = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='todos'").fetchone()[0]
        return {"passed": bool(listed and updated["completed"] and deleted and table_count == 1), "db_path": str(db_path)}
    finally:
        _stop_server(proc)


def _validate_notes(project_dir: Path) -> dict[str, Any]:
    proc, base, notes_dir = _start_server("markdown_notes_api", project_dir)
    try:
        keep = _http_json("POST", base + "/notes", {"title": "Keep", "markdown": "# Keep\nmatrix term"})[1]["id"]
        doomed = _http_json("POST", base + "/notes", {"title": "Delete", "markdown": "temporary"})[1]["id"]
        search = _http_json("GET", base + "/search?q=" + urllib.parse.quote("matrix"))[1]["results"]
        updated = _http_json("PATCH", f"{base}/notes/{keep}", {"markdown": "Updated **markdown** matrix"})[1]["note"]
        deleted = _http_json("DELETE", f"{base}/notes/{doomed}")[1]["deleted"]
        md_files = list(notes_dir.glob("*.md"))
        content_ok = any("Updated **markdown**" in path.read_text(encoding="utf-8") for path in md_files)
        return {"passed": bool(search and "Updated" in updated["markdown"] and deleted and content_ok), "notes_dir": str(notes_dir), "file_count": len(md_files)}
    finally:
        _stop_server(proc)


def _validate_auth(project_dir: Path) -> dict[str, Any]:
    proc, base, db_path = _start_server("simple_auth_api", project_dir)
    try:
        unauth = _http_json("GET", base + "/me")[0]
        registered = _http_json("POST", base + "/register", {"username": "ada", "password": "secret"})[0]
        login_status, login = _http_json("POST", base + "/login", {"username": "ada", "password": "secret"})
        token = str(login.get("token", ""))
        me = _http_json("GET", base + "/me", token=token)
        with sqlite3.connect(db_path) as conn:
            sessions = conn.execute("SELECT count(*) FROM sessions").fetchone()[0]
        logout = _http_json("POST", base + "/logout", token=token)[1]["logged_out"]
        after = _http_json("GET", base + "/me", token=token)[0]
        return {"passed": bool(unauth == 401 and registered == 201 and login_status == 200 and me[1]["user"]["username"] == "ada" and sessions >= 1 and logout and after == 401), "db_path": str(db_path)}
    finally:
        _stop_server(proc)


def _stop_server(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _validate_project(project: str, run_dir: Path) -> dict[str, Any]:
    project_dir = run_dir / "project_output" / project
    tests = _run([sys.executable, "-m", "unittest", "discover", "-v"], env=os.environ.copy(), cwd=project_dir, timeout=90)
    runtime = {
        "todo_rest_api": _validate_todo,
        "markdown_notes_api": _validate_notes,
        "simple_auth_api": _validate_auth,
    }[project](project_dir)
    provenance_path = run_dir / "artifacts" / "project_generation_provenance.json"
    provenance = _read_json(provenance_path) if provenance_path.exists() else {}
    attribution_path = run_dir / "artifacts" / "generation_attribution.json"
    attribution = _read_json(attribution_path) if attribution_path.exists() else {}
    no_agent_scaffold = not (project_dir / "run_agent.py").exists() and not (project_dir / "runtime").exists()
    attribution_ok = (
        bool(attribution.get("ordinary_mainline"))
        and attribution.get("used_agent_project") is False
        and attribution.get("used_agent_scaffold") is False
        and attribution.get("used_local_agent_runtime") is False
        and attribution.get("used_local_materializer") is True
        and attribution.get("provider_authorship") == "not_claimed"
    )
    return {
        "project_dir": str(project_dir),
        "generated_tests_passed": tests["exit_code"] == 0,
        "runtime_validation": runtime,
        "persistence_passed": bool(runtime.get("passed")),
        "provenance": provenance,
        "provenance_path": str(provenance_path),
        "attribution": attribution,
        "attribution_path": str(attribution_path),
        "no_agent_scaffold": no_agent_scaffold,
        "passed": tests["exit_code"] == 0 and bool(runtime.get("passed")) and no_agent_scaffold and bool(provenance.get("local_materializer_used")) and attribution_ok,
    }


def _run_case(fixture_path: Path) -> dict[str, Any]:
    fixture = _read_json(fixture_path)
    project = str(fixture["project"])
    env = _env()
    commands: list[dict[str, Any]] = []
    run_id = f"matrix-{project}-{int(time.time())}"
    new_run = _run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", _goal_from_fixture(fixture_path), "--run-id", run_id], env=env)
    commands.append(new_run)
    run_dir = _run_dir_from_output(new_run)
    commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
    for _ in range(30):
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=240))
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / "app.py").exists():
            break
    validation = _validate_project(project, run_dir)
    status = "passed" if validation["passed"] else "failed"
    return {"project": project, "status": status, "run_dir": str(run_dir), "commands": commands, **validation}


def _write_report(summary: dict[str, Any]) -> None:
    lines = ["# Concrete Project Generalization Matrix", ""]
    lines.append(f"- total: `{summary['matrix_total']}`")
    lines.append(f"- passed: `{summary['passed']}`")
    lines.append(f"- failed: `{summary['failed']}`")
    lines.append("")
    lines.append("## Attribution")
    lines.append("| Project | Agent Project | Agent Scaffold | Local Agent Runtime | Local Materializer | Provider Authorship |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for project in summary["projects"]:
        attr = project.get("attribution", {})
        lines.append(
            f"| {project['project']} | `{attr.get('used_agent_project')}` | `{attr.get('used_agent_scaffold')}` | "
            f"`{attr.get('used_local_agent_runtime')}` | `{attr.get('used_local_materializer')}` | "
            f"`{attr.get('provider_authorship')}` |"
        )
    lines.append("")
    for project in summary["projects"]:
        lines.append(f"## {project['project']}")
        lines.append(f"- status: `{project['status']}`")
        lines.append(f"- project_dir: `{project.get('project_dir', '')}`")
        lines.append(f"- provenance_path: `{project.get('provenance_path', '')}`")
        lines.append(f"- attribution_path: `{project.get('attribution_path', '')}`")
        lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    projects = [_run_case(FIXTURES / FIXTURE_BY_PROJECT[name]) for name in PROJECTS]
    passed = sum(1 for row in projects if row["status"] == "passed")
    summary = {
        "matrix_total": 3,
        "passed": passed,
        "failed": 3 - passed,
        "unsupported": 0,
        "projects": projects,
        "attribution_summary": [
            {
                "project": row["project"],
                "used_agent_project": row.get("attribution", {}).get("used_agent_project"),
                "used_agent_scaffold": row.get("attribution", {}).get("used_agent_scaffold"),
                "used_local_agent_runtime": row.get("attribution", {}).get("used_local_agent_runtime"),
                "used_local_materializer": row.get("attribution", {}).get("used_local_materializer"),
                "provider_authorship": row.get("attribution", {}).get("provider_authorship"),
            }
            for row in projects
        ],
        "report": str(REPORT),
    }
    _write_json(GENERATED / "matrix_summary.json", summary)
    _write_report(summary)
    public = {"matrix_total": 3, "passed": passed, "failed": 3 - passed, "unsupported": 0, "projects": [{"project": row["project"], "status": row["status"]} for row in projects], "report": str(REPORT)}
    print(json.dumps(public, ensure_ascii=False, indent=2))
    return 0 if passed == 3 else 1


if __name__ == "__main__":
    raise SystemExit(main())
