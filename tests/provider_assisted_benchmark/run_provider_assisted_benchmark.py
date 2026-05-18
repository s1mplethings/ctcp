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
import uuid
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = Path(__file__).resolve().parent
FIXTURES = [
    BENCH_DIR / "fixtures" / "provider_assisted_notes_app.json",
    BENCH_DIR / "fixtures" / "provider_assisted_csv_tool.json",
    BENCH_DIR / "fixtures" / "provider_assisted_kanban_variant.json",
]
GENERATED = BENCH_DIR / "generated"
SUMMARY_PATH = GENERATED / "provider_assisted_summary.json"
REPORT = BENCH_DIR / "benchmark_report.md"
REVIEW_PACK = ROOT / "meta" / "reports" / "REVIEW_PACK.md"
BLIND_SUMMARY_PATH = ROOT / "tests" / "live_provider_blind_matrix" / "generated" / "live_provider_blind_matrix_summary.json"
MEDIUM_SUMMARY_PATH = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str], *, env: dict[str, str], cwd: Path = ROOT, timeout: int = 120) -> dict[str, Any]:
    started = time.time()
    try:
        proc = subprocess.run(
            [str(part) for part in cmd],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
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


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_provider_assisted_benchmark_runs").resolve())
    env["CTCP_ANALYSIS_PROFILE"] = "fast"
    env["CTCP_PROVIDER_ASSISTED"] = "1"
    env["CTCP_FORCE_PROVIDER"] = "mock_agent"
    env.pop("CTCP_PROVIDER_ASSISTED_FIXTURE", None)
    env.pop("CTCP_ALLOW_LOCAL_MAINLINE_PROVIDER", None)
    return env


def _run_dir_from_output(row: dict[str, Any]) -> Path:
    text = f"{row.get('stdout', '')}\n{row.get('stderr', '')}"
    match = re.search(r"run_dir=([^\r\n]+)", text)
    if match:
        return Path(match.group(1).strip()).resolve()
    pointer = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
    if pointer.exists():
        return Path(pointer.read_text(encoding="utf-8").strip()).resolve()
    raise RuntimeError("could not locate run_dir")


def _force_local_dispatch(run_dir: Path) -> None:
    config_path = run_dir / "artifacts" / "dispatch_config.json"
    config = _read_json(config_path) if config_path.exists() else {}
    config["mode"] = "mock_agent"
    role_providers = dict(config.get("role_providers", {})) if isinstance(config.get("role_providers", {}), dict) else {}
    for role in ("chair", "contract_guardian", "cost_controller", "researcher", "patchmaker", "fixer"):
        role_providers[role] = "mock_agent"
    role_providers["librarian"] = "local_exec"
    config["role_providers"] = role_providers
    _write_json(config_path, config)


def _test_env(project_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(project_dir) if not existing else str(project_dir) + os.pathsep + existing
    return env


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
    db_path = project_dir / f"{project}_provider_assisted.db"
    args = [sys.executable, str(project_dir / "app.py"), "--host", "127.0.0.1", "--port", str(port)]
    if project == "markdown_notes_api":
        notes_dir = project_dir / "provider_notes"
        args.extend(["--notes-dir", str(notes_dir)])
        persistence = notes_dir
    else:
        args.extend(["--db", str(db_path)])
        persistence = db_path
    proc = subprocess.Popen(args, cwd=project_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True)
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            status, payload = _http_json("GET", base + "/status")
            if status == 200 and payload.get("status") == "ok":
                return proc, base, persistence
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


def _validate_csv(project_dir: Path) -> dict[str, Any]:
    output = project_dir / "provider_assisted_report.json"
    result = _run(
        [sys.executable, "expense_analyzer.py", "--input", "sample_expenses.csv", "--output", str(output)],
        env=_test_env(project_dir),
        cwd=project_dir,
    )
    report = _read_json(output) if output.exists() else {}
    helper = project_dir / "provider_assisted_helper.py"
    return {
        "passed": result["exit_code"] == 0
        and output.exists()
        and helper.exists()
        and round(float(report.get("category_totals", {}).get("Food", 0)), 2) == 20.0,
        "cli": result,
        "helper_exists": helper.exists(),
        "report": report,
    }


def _validate_notes(project_dir: Path) -> dict[str, Any]:
    proc, base, notes_dir = _start_server(project_dir, "markdown_notes_api")
    try:
        created = _http_json("POST", base + "/notes", {"title": "Provider Notes", "markdown": "# Heading\nProvider assisted body"})
        note_id = created[1].get("id")
        fetched = _http_json("GET", f"{base}/notes/{note_id}")[1].get("note", {})
        query = urllib.parse.quote("Provider")
        searched = _http_json("GET", f"{base}/search?q={query}")[1].get("results", [])
    finally:
        _stop_server(proc)
    helper = project_dir / "provider_note_helpers.py"
    files = list(Path(notes_dir).glob("*.md")) if Path(notes_dir).exists() else []
    return {
        "passed": bool(helper.exists() and files and "# Heading" in str(fetched.get("markdown", "")) and searched),
        "helper_exists": helper.exists(),
        "markdown_files": [str(path) for path in files],
        "fetched": fetched,
    }


def _validate_kanban(project_dir: Path) -> dict[str, Any]:
    proc, base, db_path = _start_server(project_dir, "local_kanban_board_app")
    try:
        html = _http_text(base + "/")
        js = _http_text(base + "/static/app.js")
        helper_js = _http_text(base + "/static/provider_enhancements.js")
        board = _http_json("POST", base + "/boards", {"name": "Provider Board"})[1]
        board_id = board.get("id")
        card = _http_json("POST", f"{base}/boards/{board_id}/cards", {"title": "Provider card", "description": "variant", "column": "todo"})[1]
        card_id = card.get("id")
        moved = _http_json("PATCH", f"{base}/cards/{card_id}/move", {"column": "doing", "position": 1})[1].get("card", {})
    finally:
        _stop_server(proc)
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='cards'").fetchone()[0]
    return {
        "passed": bool("Local Kanban Board" in html and "fetch(" in js and "providerColumnLabel" in helper_js and moved.get("column") == "doing" and tables == 1),
        "frontend": "passed" if "providerColumnLabel" in helper_js else "failed",
        "sqlite": "passed" if tables == 1 else "failed",
        "moved": moved,
    }


def _validate_project(case: str, project: str, run_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    project_dir = run_dir / "project_output" / project
    tests = _run([sys.executable, "-m", "unittest", "discover", "-v"], env=_test_env(project_dir), cwd=project_dir, timeout=90)
    runtime = {
        "provider_assisted_csv_tool": _validate_csv,
        "provider_assisted_notes_app": _validate_notes,
        "provider_assisted_kanban_variant": _validate_kanban,
    }[case](project_dir)
    attribution_path = run_dir / "artifacts" / "generation_attribution.json"
    provenance_path = run_dir / "artifacts" / "project_generation_provenance.json"
    provider_path = run_dir / "artifacts" / "provider_assisted_generation.json"
    attribution = _read_json(attribution_path) if attribution_path.exists() else {}
    provenance = _read_json(provenance_path) if provenance_path.exists() else {}
    provider_doc = _read_json(provider_path) if provider_path.exists() else {}
    command_text = "\n".join(str(row.get("cmd", "")) for row in commands)
    ordinary_mainline = all(token in command_text for token in ("new-run", "status", "advance"))
    no_agent_scaffold = not (project_dir / "run_agent.py").exists() and not (project_dir / "runtime").exists()
    provider_ok = (
        attribution.get("used_provider_agent") is True
        and attribution.get("provider_authorship") == "provider_assisted"
        and attribution.get("generation_mode") == "provider_assisted"
        and bool(attribution.get("provider_assisted_sections"))
        and bool(attribution.get("provider_generated_files"))
        and attribution.get("used_agent_project") is False
        and attribution.get("used_agent_scaffold") is False
        and attribution.get("used_local_agent_runtime") is False
        and attribution.get("used_local_materializer") is True
        and bool(provider_doc.get("provider_generated_files"))
    )
    passed = bool(tests["exit_code"] == 0 and runtime.get("passed") and provider_ok and ordinary_mainline and no_agent_scaffold)
    return {
        "case": case,
        "project": project,
        "status": "passed" if passed else "failed",
        "project_dir": str(project_dir),
        "run_dir": str(run_dir),
        "generated_tests_passed": tests["exit_code"] == 0,
        "runtime_validation": runtime,
        "ordinary_mainline": ordinary_mainline,
        "no_agent_scaffold": no_agent_scaffold,
        "attribution": attribution,
        "attribution_path": str(attribution_path),
        "provenance": provenance,
        "provenance_path": str(provenance_path),
        "provider_assisted_generation": provider_doc,
        "provider_assisted_generation_path": str(provider_path),
        "provider_ok": provider_ok,
        "passed": passed,
    }


def _run_case(path: Path) -> dict[str, Any]:
    fixture = _read_json(path)
    case = str(fixture["case"])
    project = str(fixture["project"])
    env = _env()
    commands: list[dict[str, Any]] = []
    run_id = f"provider-assisted-{case}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    goal = str(fixture["goal"]) + " Use ordinary CTCP new-run/status/advance and source_generation; do not use agent scaffold."
    new_run = _run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", goal, "--run-id", run_id], env=env)
    commands.append(new_run)
    run_dir = _run_dir_from_output(new_run)
    _force_local_dispatch(run_dir)
    commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
    startup = "expense_analyzer.py" if project == "csv_expense_analyzer" else "app.py"
    for _ in range(32):
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=240))
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / startup).exists():
            break
    validation = _validate_project(case, project, run_dir, commands)
    return {"commands": commands, **validation}


def _write_report(summary: dict[str, Any]) -> None:
    lines = ["# Provider-Assisted Generation Benchmark", ""]
    lines.append(f"- status: `{summary['status']}`")
    lines.append(f"- passed: `{summary['passed']}/{summary['total']}`")
    lines.append("")
    lines.append("## Provider Participation Summary")
    lines.append("| Case | Project | Provider Used | Sections | Generated Files | Fallbacks | Runtime |")
    lines.append("|---|---|---:|---|---|---:|---|")
    for row in summary["projects"]:
        attr = row.get("attribution", {})
        lines.append(
            f"| {row['case']} | {row['project']} | `{attr.get('used_provider_agent')}` | "
            f"`{', '.join(attr.get('provider_assisted_sections', []))}` | "
            f"`{', '.join(attr.get('provider_generated_files', []))}` | "
            f"`{len(attr.get('provider_fallbacks', []))}` | `{row.get('runtime_validation', {}).get('passed')}` |"
        )
    lines.append("")
    for row in summary["projects"]:
        lines.append(f"## {row['case']}")
        lines.append(f"- status: `{row['status']}`")
        lines.append(f"- project_dir: `{row.get('project_dir', '')}`")
        lines.append(f"- attribution_path: `{row.get('attribution_path', '')}`")
        lines.append(f"- provider_assisted_generation_path: `{row.get('provider_assisted_generation_path', '')}`")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_review_pack(summary: dict[str, Any]) -> None:
    lines = [
        "# CTCP Provider-Assisted Review Pack",
        "",
        "## Provider Participation Summary",
        "| Case | Provider Used | Provider Authorship | Generated Files | Fallback Count | Runtime Valid |",
        "|---|---:|---|---|---:|---:|",
    ]
    for row in summary["projects"]:
        attr = row.get("attribution", {})
        validation = attr.get("provider_validation", {})
        lines.append(
            f"| {row['case']} | `{attr.get('used_provider_agent')}` | `{attr.get('provider_authorship')}` | "
            f"`{', '.join(attr.get('provider_generated_files', []))}` | `{len(attr.get('provider_fallbacks', []))}` | "
            f"`{validation.get('runtime_valid')}` |"
        )
    lines.extend(
        [
            "",
            "## Deterministic Guardrails",
            "- Ordinary mainline remains `new-run/status/advance`.",
            "- Core structure, persistence, generated tests, and runtime validators remain deterministic.",
            "- Provider fragments are bounded, syntax checked, safety filtered, and fallback to deterministic output if invalid.",
            "",
            "## Benchmark Summary",
            f"- provider-assisted benchmark: `{summary['passed']}/{summary['total']}`",
            f"- report: `{REPORT}`",
            f"- summary: `{SUMMARY_PATH}`",
            "",
            "## Reproduction Commands",
            "- `.\\.venv\\Scripts\\python.exe tests\\provider_assisted_benchmark\\run_provider_assisted_benchmark.py`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_generation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_attribution -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_fallback -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_validation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_provider_assisted_variation -v`",
            "",
            "## Risks For Human Review",
            "- Provider-assisted mode is fixture/local-provider backed in this phase; it is not autonomous provider-authored generation.",
            "- Deterministic fallback remains required for reproducibility.",
        ]
    )
    if BLIND_SUMMARY_PATH.exists():
        try:
            blind_summary = json.loads(BLIND_SUMMARY_PATH.read_text(encoding="utf-8"))
        except Exception:
            blind_summary = {}
        if blind_summary.get("status") == "passed":
            lines.extend(
                [
                    "",
                    "## Live Provider Blind Matrix Summary",
                    f"- status: `{blind_summary.get('status')}`",
                    f"- cases: `{blind_summary.get('case_count')}`",
                    f"- provider_request_count: `{blind_summary.get('provider_request_count')}`",
                    f"- provider_project_candidate_count: `{blind_summary.get('provider_project_candidate_count')}`",
                    f"- accepted/repaired/fallback/unsupported/failed: "
                    f"`{blind_summary.get('accepted_count')}/{blind_summary.get('repaired_count')}/"
                    f"{blind_summary.get('fallback_count')}/{blind_summary.get('unsupported_count')}/"
                    f"{blind_summary.get('failed_count')}`",
                    "",
                    "| Case | Outcome | Status |",
                    "|---|---|---|",
                ]
            )
            for row in blind_summary.get("cases", []):
                lines.append(f"| {row.get('project')} | `{row.get('outcome')}` | `{row.get('status')}` |")
    if MEDIUM_SUMMARY_PATH.exists():
        try:
            medium_summary = json.loads(MEDIUM_SUMMARY_PATH.read_text(encoding="utf-8"))
        except Exception:
            medium_summary = {}
        if medium_summary.get("status") == "passed":
            phase20 = medium_summary.get("phase20", {}) if isinstance(medium_summary.get("phase20", {}), dict) else {}
            lines.extend(
                [
                    "",
                    "## Phase 20 Acceptance Hardening Summary",
                    f"- new accepted/repaired/fallback counts: `{phase20.get('accepted_count')}/{phase20.get('repaired_count')}/{phase20.get('fallback_count')}`",
                    f"- acceptance_rate: `{phase20.get('acceptance_rate')}`",
                    f"- accepted_or_repaired_rate: `{phase20.get('accepted_or_repaired_rate')}`",
                    f"- gate passed: `{phase20.get('phase20_gate_passed')}`",
                    "- fixture lowering: `no`",
                    "",
                    "## Phase 21B Medium Candidate Recovery Summary",
                    f"- status: `{medium_summary.get('status')}`",
                    f"- cases: `{medium_summary.get('case_count')}`",
                    f"- accepted/repaired/fallback/failed: `{medium_summary.get('accepted_count')}/{medium_summary.get('repaired_count')}/{medium_summary.get('fallback_count')}/{medium_summary.get('failed_count')}`",
                    f"- provider request count: `{medium_summary.get('provider_request_count')}`",
                    f"- provider project candidate count: `{medium_summary.get('provider_project_candidate_count')}`",
                    "- ordinary mainline: `new-run/status/advance`",
                    "- agent-project/scaffold substitution: `no`",
                    "",
                    "| Case | Outcome | Provider Ratio | Runtime |",
                    "|---|---|---:|---:|",
                ]
            )
            for row in medium_summary.get("cases", []):
                lines.append(f"| {row.get('project')} | `{row.get('outcome')}` | `{row.get('provider_authored_file_ratio')}` | `{row.get('runtime_validation', {}).get('passed')}` |")
    REVIEW_PACK.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    projects = [_run_case(path) for path in FIXTURES]
    passed = sum(1 for row in projects if row["status"] == "passed")
    csv_row = next((row for row in projects if row["case"] == "provider_assisted_csv_tool"), {})
    provider_files = set(csv_row.get("attribution", {}).get("provider_generated_files", []))
    variation_detected = any(path.endswith("provider_assisted_helper.py") for path in provider_files)
    summary = {
        "status": "passed" if passed == len(projects) and variation_detected else "failed",
        "total": len(projects),
        "passed": passed,
        "failed": len(projects) - passed,
        "projects": projects,
        "provider_assisted_output_differs": variation_detected,
        "report": str(REPORT),
        "summary": str(SUMMARY_PATH),
        "review_pack": str(REVIEW_PACK),
    }
    _write_json(SUMMARY_PATH, summary)
    _write_report(summary)
    _write_review_pack(summary)
    public = {
        "status": summary["status"],
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "provider_assisted_output_differs": summary["provider_assisted_output_differs"],
        "projects": [{"case": row["case"], "project": row["project"], "status": row["status"]} for row in projects],
        "report": str(REPORT),
        "summary": str(SUMMARY_PATH),
        "review_pack": str(REVIEW_PACK),
    }
    print(json.dumps(public, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
