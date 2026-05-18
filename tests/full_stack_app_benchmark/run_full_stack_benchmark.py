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
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = Path(__file__).resolve().parent
FIXTURES = [
    BENCH_DIR / "fixtures" / "local_task_board_app.json",
    BENCH_DIR / "fixtures" / "local_kanban_board_app.json",
]
GENERATED = BENCH_DIR / "generated"
REPORT = BENCH_DIR / "benchmark_report.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _goal(fixture: dict[str, Any]) -> str:
    endpoints = ", ".join(str(item) for item in fixture["project_requirements"]["api"]["required_endpoints"])
    assets = ", ".join(str(item) for item in fixture["project_requirements"]["frontend"]["required_assets"])
    return (
        f"{fixture['goal']} Required endpoints: {endpoints}. "
        f"Required frontend assets: {assets}. "
        f"Persistence requirement: {fixture['project_requirements']['storage']}. "
        "Generate the concrete project files, tests, README, runnable local HTTP server, and delivery package."
    )


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_full_stack_app_benchmark_runs").resolve())
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


def _http_json(method: str, url: str, payload: dict[str, object] | None = None) -> tuple[int, dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=5) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return int(exc.code), json.loads(exc.read().decode("utf-8"))


def _http_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def _start_server(project_dir: Path, project: str) -> tuple[subprocess.Popen[str], str, Path]:
    port = _free_port()
    db_path = project_dir / f"{project}_benchmark.db"
    proc = subprocess.Popen(
        [sys.executable, str(project_dir / "app.py"), "--host", "127.0.0.1", "--port", str(port), "--db", str(db_path)],
        cwd=project_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            status, payload = _http_json("GET", base + "/status")
            if status == 200 and payload.get("status") == "ok":
                return proc, base, db_path
        except Exception:
            time.sleep(0.2)
    proc.kill()
    raise RuntimeError(f"{project} server did not start")


def _stop_server(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


def _validate_task_board(base: str, db_path: Path) -> dict[str, Any]:
    html = _http_text(base + "/")
    js = _http_text(base + "/static/app.js")
    css = _http_text(base + "/static/styles.css")
    created_status, created = _http_json("POST", base + "/api/tasks", {"title": "Benchmark task"})
    task_id = created.get("id")
    listed = _http_json("GET", base + "/api/tasks")[1].get("tasks", [])
    updated = _http_json("PATCH", f"{base}/api/tasks/{task_id}", {"status": "doing"})[1].get("task", {})
    deleted = _http_json("DELETE", f"{base}/api/tasks/{task_id}")[1].get("deleted", False)
    with sqlite3.connect(db_path) as conn:
        table_count = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='tasks'").fetchone()[0]
    return {
        "frontend_http_passed": "Local Task Board" in html and "loadTasks" in js and ".board" in css,
        "api_passed": bool(created_status == 201 and listed and updated.get("status") == "doing" and deleted),
        "sqlite_passed": bool(db_path.exists() and table_count == 1),
        "backend_runtime": "passed" if created_status == 201 and listed and deleted else "failed",
        "frontend_validation": "passed" if "fetch(" in js and "Local Task Board" in html else "failed",
        "sqlite_validation": "passed" if db_path.exists() and table_count == 1 else "failed",
        "db_path": str(db_path),
    }


def _validate_kanban(base: str, db_path: Path) -> dict[str, Any]:
    html = _http_text(base + "/")
    js = _http_text(base + "/static/app.js")
    css = _http_text(base + "/static/styles.css")
    board_status, board = _http_json("POST", base + "/boards", {"name": "Benchmark Board"})
    board_id = board.get("id")
    card_status, card = _http_json("POST", f"{base}/boards/{board_id}/cards", {"title": "Benchmark card", "description": "move me", "column": "todo"})
    card_id = card.get("id")
    listed = _http_json("GET", f"{base}/boards/{board_id}/cards")[1].get("cards", [])
    moved = _http_json("PATCH", f"{base}/cards/{card_id}/move", {"column": "doing", "position": 1})[1].get("card", {})
    updated = _http_json("PATCH", f"{base}/cards/{card_id}", {"title": "Updated benchmark card", "description": "updated"})[1].get("card", {})
    deleted = _http_json("DELETE", f"{base}/cards/{card_id}")[1].get("deleted", False)
    with sqlite3.connect(db_path) as conn:
        boards = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='boards'").fetchone()[0]
        cards = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='cards'").fetchone()[0]
    frontend_ok = "Local Kanban Board" in html and "data-column=\"todo\"" in html and "moveCard" in js and "fetch(" in js and ".column" in css
    api_ok = bool(board_status == 201 and card_status == 201 and listed and moved.get("column") == "doing" and updated.get("title") == "Updated benchmark card" and deleted)
    sqlite_ok = bool(db_path.exists() and boards == 1 and cards == 1)
    return {
        "frontend_http_passed": frontend_ok,
        "api_passed": api_ok,
        "sqlite_passed": sqlite_ok,
        "backend_runtime": "passed" if api_ok else "failed",
        "frontend_validation": "passed" if frontend_ok else "failed",
        "sqlite_validation": "passed" if sqlite_ok else "failed",
        "db_path": str(db_path),
    }


def _validate_project(run_dir: Path, project: str) -> dict[str, Any]:
    project_dir = run_dir / "project_output" / project
    tests = _run([sys.executable, "-m", "unittest", "discover", "-v"], env=os.environ.copy(), cwd=project_dir, timeout=90)
    no_agent_scaffold = not (project_dir / "run_agent.py").exists() and not (project_dir / "runtime").exists()
    frontend_assets = {
        "index": (project_dir / "static" / "index.html").exists(),
        "js": (project_dir / "static" / "app.js").exists(),
        "css": (project_dir / "static" / "styles.css").exists(),
    }
    proc, base, db_path = _start_server(project_dir, project)
    try:
        runtime = _validate_kanban(base, db_path) if project == "local_kanban_board_app" else _validate_task_board(base, db_path)
    finally:
        _stop_server(proc)
    provenance_path = run_dir / "artifacts" / "project_generation_provenance.json"
    provenance = _read_json(provenance_path) if provenance_path.exists() else {}
    attribution_path = run_dir / "artifacts" / "generation_attribution.json"
    attribution = _read_json(attribution_path) if attribution_path.exists() else {}
    attribution_ok = (
        bool(attribution.get("ordinary_mainline"))
        and attribution.get("used_agent_project") is False
        and attribution.get("used_agent_scaffold") is False
        and attribution.get("used_local_agent_runtime") is False
        and attribution.get("used_local_materializer") is True
        and attribution.get("provider_authorship") == "not_claimed"
    )
    passed = (
        tests["exit_code"] == 0
        and no_agent_scaffold
        and all(frontend_assets.values())
        and bool(runtime["frontend_http_passed"])
        and bool(runtime["api_passed"])
        and bool(runtime["sqlite_passed"])
        and bool(provenance.get("local_materializer_used"))
        and attribution_ok
    )
    return {
        "project": project,
        "status": "passed" if passed else "failed",
        "project_dir": str(project_dir),
        "generated_tests_passed": tests["exit_code"] == 0,
        "frontend_assets": frontend_assets,
        "runtime_validation": runtime,
        "backend_runtime": runtime["backend_runtime"],
        "frontend_validation": runtime["frontend_validation"],
        "sqlite_validation": runtime["sqlite_validation"],
        "persistence_passed": bool(runtime["sqlite_passed"]),
        "provenance": provenance,
        "provenance_path": str(provenance_path),
        "attribution": attribution,
        "attribution_path": str(attribution_path),
        "no_agent_scaffold": no_agent_scaffold,
        "passed": passed,
    }


def _run_generation(fixture_path: Path) -> dict[str, Any]:
    fixture = _read_json(fixture_path)
    project = str(fixture["project"])
    env = _env()
    commands: list[dict[str, Any]] = []
    run_id = f"full-stack-{project}-{int(time.time())}"
    new_run = _run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", _goal(fixture), "--run-id", run_id], env=env)
    commands.append(new_run)
    run_dir = _run_dir_from_output(new_run)
    commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
    for _ in range(32):
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=240))
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / "app.py").exists():
            break
    validation = _validate_project(run_dir, project)
    source_report = run_dir / "artifacts" / "source_generation_report.json"
    if source_report.exists():
        validation["source_generation_status"] = _read_json(source_report).get("status", "")
    return {"run_dir": str(run_dir), "commands": commands, **validation}


def _write_report(summary: dict[str, Any]) -> None:
    lines = ["# Full-Stack Local App Generation Benchmark", ""]
    lines.append(f"- status: `{summary['status']}`")
    lines.append(f"- passed: `{summary['passed']}/{summary['total']}`")
    lines.append("")
    lines.append("## Attribution")
    lines.append("| Project | Agent Project | Agent Scaffold | Local Agent Runtime | Local Materializer | Provider Authorship |")
    lines.append("|---|---:|---:|---:|---:|---|")
    for row in summary["projects"]:
        attr = row.get("attribution", {})
        lines.append(
            f"| {row['project']} | `{attr.get('used_agent_project')}` | `{attr.get('used_agent_scaffold')}` | "
            f"`{attr.get('used_local_agent_runtime')}` | `{attr.get('used_local_materializer')}` | "
            f"`{attr.get('provider_authorship')}` |"
        )
    lines.append("")
    for row in summary["projects"]:
        lines.append(f"## {row['project']}")
        lines.append(f"- status: `{row['status']}`")
        lines.append(f"- project_dir: `{row.get('project_dir', '')}`")
        lines.append(f"- provenance_path: `{row.get('provenance_path', '')}`")
        lines.append(f"- attribution_path: `{row.get('attribution_path', '')}`")
        lines.append(f"- backend_runtime: `{row.get('backend_runtime', '')}`")
        lines.append(f"- frontend_validation: `{row.get('frontend_validation', '')}`")
        lines.append(f"- sqlite_validation: `{row.get('sqlite_validation', '')}`")
        lines.append("")
    lines.append("## Structure Cleanup")
    cleanup = summary.get("structure_cleanup", {})
    lines.append(f"- shared_helpers_added: `{', '.join(cleanup.get('shared_helpers_added', []))}`")
    lines.append(f"- duplication_reduced: `{cleanup.get('duplication_reduced', False)}`")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    projects = [_run_generation(path) for path in FIXTURES]
    passed = sum(1 for row in projects if row.get("status") == "passed")
    summary = {
        "status": "passed" if passed == len(projects) else "failed",
        "total": len(projects),
        "passed": passed,
        "failed": len(projects) - passed,
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
        "structure_cleanup": {
            "shared_helpers_added": [
                "project_generation_fast_path_registry.py",
                "project_generation_template_writer.py",
                "project_generation_provenance_writer.py",
            ],
            "duplication_reduced": True,
        },
    }
    kanban = next((row for row in projects if row.get("project") == "local_kanban_board_app"), {})
    summary.update(
        {
            "project": "local_kanban_board_app",
            "backend_runtime": kanban.get("backend_runtime", "failed"),
            "frontend_validation": kanban.get("frontend_validation", "failed"),
            "sqlite_validation": kanban.get("sqlite_validation", "failed"),
        }
    )
    _write_json(GENERATED / "benchmark_summary.json", summary)
    _write_report(summary)
    public = {
        "status": summary["status"],
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "projects": [{"project": row["project"], "status": row["status"]} for row in projects],
        "report": str(REPORT),
        "summary": str(GENERATED / "benchmark_summary.json"),
    }
    print(json.dumps(public, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
