from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
import urllib.parse
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
TESTS_DIR = ROOT / "tests"
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

try:
    from tests.provider_assisted_benchmark import run_provider_assisted_benchmark as base
except ModuleNotFoundError:
    from provider_assisted_benchmark import run_provider_assisted_benchmark as base

BENCH_DIR = Path(__file__).resolve().parent
FIXTURES = [
    BENCH_DIR / "fixtures" / "live_provider_notes_app.json",
    BENCH_DIR / "fixtures" / "live_provider_csv_tool.json",
    BENCH_DIR / "fixtures" / "live_provider_kanban_helper.json",
]
GENERATED = BENCH_DIR / "generated"
SUMMARY_PATH = GENERATED / "live_provider_summary.json"
REPORT = BENCH_DIR / "benchmark_report.md"
REVIEW_PACK = ROOT / "meta" / "reports" / "REVIEW_PACK.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _env() -> dict[str, str]:
    env = base._env()
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_live_provider_benchmark_runs").resolve())
    env["CTCP_LIVE_PROVIDER_ASSISTED"] = "1"
    env["CTCP_LIVE_PROVIDER_MAX_OUTPUT_TOKENS"] = "900"
    env["CTCP_LIVE_PROVIDER_TIMEOUT_SEC"] = str(os.environ.get("CTCP_LIVE_PROVIDER_TIMEOUT_SEC", "45"))
    env.pop("CTCP_PROVIDER_ASSISTED", None)
    env.pop("CTCP_PROVIDER_ASSISTED_FIXTURE", None)
    env.pop("CTCP_LIVE_PROVIDER_FORCE_INVALID", None)
    return env


def _validate_csv(project_dir: Path) -> dict[str, Any]:
    output = project_dir / "live_provider_report.json"
    result = base._run(
        [sys.executable, "expense_analyzer.py", "--input", "sample_expenses.csv", "--output", str(output)],
        env=base._test_env(project_dir),
        cwd=project_dir,
    )
    report = _read_json(output) if output.exists() else {}
    helper = project_dir / "provider_live_helper.py"
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
    proc, base_url, notes_dir = base._start_server(project_dir, "markdown_notes_api")
    try:
        created = base._http_json("POST", base_url + "/notes", {"title": "Live Notes", "markdown": "# Heading\nLive provider body"})
        note_id = created[1].get("id")
        fetched = base._http_json("GET", f"{base_url}/notes/{note_id}")[1].get("note", {})
        query = urllib.parse.quote("Live")
        searched = base._http_json("GET", f"{base_url}/search?q={query}")[1].get("results", [])
    finally:
        base._stop_server(proc)
    helper = project_dir / "provider_live_note_helpers.py"
    files = list(Path(notes_dir).glob("*.md")) if Path(notes_dir).exists() else []
    return {
        "passed": bool(helper.exists() and files and "# Heading" in str(fetched.get("markdown", "")) and searched),
        "helper_exists": helper.exists(),
        "markdown_files": [str(path) for path in files],
        "fetched": fetched,
    }


def _validate_kanban(project_dir: Path) -> dict[str, Any]:
    proc, base_url, db_path = base._start_server(project_dir, "local_kanban_board_app")
    try:
        html = base._http_text(base_url + "/")
        js = base._http_text(base_url + "/static/app.js")
        helper_js = base._http_text(base_url + "/static/live_provider_enhancements.js")
        board = base._http_json("POST", base_url + "/boards", {"name": "Live Board"})[1]
        board_id = board.get("id")
        card = base._http_json("POST", f"{base_url}/boards/{board_id}/cards", {"title": "Live card", "description": "variant", "column": "todo"})[1]
        card_id = card.get("id")
        moved = base._http_json("PATCH", f"{base_url}/cards/{card_id}/move", {"column": "doing", "position": 1})[1].get("card", {})
    finally:
        base._stop_server(proc)
    with sqlite3.connect(db_path) as conn:
        tables = conn.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='cards'").fetchone()[0]
    return {
        "passed": bool("Local Kanban Board" in html and "fetch(" in js and helper_js.strip() and moved.get("column") == "doing" and tables == 1),
        "frontend": "passed" if helper_js.strip() else "failed",
        "sqlite": "passed" if tables == 1 else "failed",
        "moved": moved,
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


def _validate_project(case: str, project: str, run_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    project_dir = run_dir / "project_output" / project
    tests = base._run([sys.executable, "-m", "unittest", "discover", "-v"], env=base._test_env(project_dir), cwd=project_dir, timeout=90)
    runtime = {
        "live_provider_csv_tool": _validate_csv,
        "live_provider_notes_app": _validate_notes,
        "live_provider_kanban_helper": _validate_kanban,
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
    generated_files = [str(path) for path in attribution.get("provider_generated_files", [])]
    generated_files_exist = bool(generated_files) and all((run_dir / rel).exists() for rel in generated_files)
    validation = attribution.get("provider_validation", {}) if isinstance(attribution.get("provider_validation", {}), dict) else {}
    provider_ok = (
        attribution.get("used_provider_agent") is True
        and attribution.get("provider_authorship") == "provider_assisted"
        and attribution.get("generation_mode") == "live_provider_assisted"
        and attribution.get("provider_name") == "live_provider"
        and attribution.get("live_provider_used") is True
        and int(attribution.get("provider_request_count", 0) or 0) > 0
        and int(attribution.get("provider_fragment_count", 0) or 0) > 0
        and not attribution.get("provider_fallbacks")
        and validation.get("syntax_valid") is True
        and validation.get("fallback_triggered") is False
        and generated_files_exist
        and attribution.get("used_agent_project") is False
        and attribution.get("used_agent_scaffold") is False
        and attribution.get("used_local_agent_runtime") is False
        and attribution.get("used_local_materializer") is True
        and provider_doc.get("live_provider_used") is True
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
    run_id = f"live-provider-{case}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    goal = str(fixture["goal"]) + " Use ordinary CTCP new-run/status/advance and source_generation; do not use agent scaffold."
    new_run = base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", goal, "--run-id", run_id], env=env)
    commands.append(new_run)
    run_dir = _run_dir_from_output(new_run)
    base._force_local_dispatch(run_dir)
    commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
    startup = "expense_analyzer.py" if project == "csv_expense_analyzer" else "app.py"
    for _ in range(32):
        commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=300))
        commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / startup).exists():
            break
    validation = _validate_project(case, project, run_dir, commands)
    return {"commands": commands, **validation}


def _write_report(summary: dict[str, Any]) -> None:
    lines = ["# Live Provider-Assisted Smoke Benchmark", ""]
    lines.append(f"- status: `{summary['status']}`")
    lines.append(f"- passed: `{summary['passed']}/{summary['total']}`")
    lines.append(f"- provider_request_count: `{summary['provider_request_count']}`")
    lines.append(f"- provider_fragment_count: `{summary['provider_fragment_count']}`")
    lines.append("")
    lines.append("## Live Provider Participation")
    lines.append("| Case | Project | Requests | Fragments | Generated Files | Fallbacks | Runtime |")
    lines.append("|---|---|---:|---:|---|---:|---|")
    for row in summary["projects"]:
        attr = row.get("attribution", {})
        lines.append(
            f"| {row['case']} | {row['project']} | `{attr.get('provider_request_count')}` | "
            f"`{attr.get('provider_fragment_count')}` | `{', '.join(attr.get('provider_generated_files', []))}` | "
            f"`{len(attr.get('provider_fallbacks', []))}` | `{row.get('runtime_validation', {}).get('passed')}` |"
        )
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_live_review_pack(summary: dict[str, Any]) -> None:
    lines = [
        "# CTCP Live Provider-Assisted Review Pack",
        "",
        "## Live Provider Participation",
        "| Case | Actually Called | Requests | Fragments | Generated Files | Fallback Count | Syntax Valid | Runtime Valid |",
        "|---|---:|---:|---:|---|---:|---:|---:|",
    ]
    for row in summary.get("projects", []):
        attr = row.get("attribution", {})
        validation = attr.get("provider_validation", {}) if isinstance(attr.get("provider_validation", {}), dict) else {}
        lines.append(
            f"| {row.get('case')} | `{attr.get('live_provider_used')}` | `{attr.get('provider_request_count')}` | "
            f"`{attr.get('provider_fragment_count')}` | `{', '.join(attr.get('provider_generated_files', []))}` | "
            f"`{len(attr.get('provider_fallbacks', []))}` | `{validation.get('syntax_valid')}` | `{validation.get('runtime_valid')}` |"
        )
    lines.extend(
        [
            "",
            "## Deterministic Guardrails",
            "- Ordinary mainline remains `new-run/status/advance`.",
            "- Deterministic materializers own core project structure, server/runtime behavior, persistence, and generated tests.",
            "- Live provider fragments are bounded, safety scanned, syntax checked, and fallback to deterministic output if invalid.",
            "",
            "## Benchmark Summary",
            f"- live provider benchmark: `{summary.get('passed')}/{summary.get('total')}`",
            f"- provider request count: `{summary.get('provider_request_count')}`",
            f"- provider fragment count: `{summary.get('provider_fragment_count')}`",
            f"- report: `{REPORT}`",
            f"- summary: `{SUMMARY_PATH}`",
            "",
            "## Reproduction Commands",
            "- `.\\.venv\\Scripts\\python.exe tests\\live_provider_benchmark\\run_live_provider_benchmark.py`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_generation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_attribution -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_fallback -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_validation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_safety -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_variation -v`",
            "",
            "## Risks For Human Review",
            "- Live provider participation is intentionally limited to small helper/documentation fragments.",
            "- Full provider-authored project generation remains out of scope.",
        ]
    )
    REVIEW_PACK.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    projects = [_run_case(path) for path in FIXTURES]
    passed = sum(1 for row in projects if row["status"] == "passed")
    request_count = sum(int(row.get("attribution", {}).get("provider_request_count", 0) or 0) for row in projects)
    fragment_count = sum(int(row.get("attribution", {}).get("provider_fragment_count", 0) or 0) for row in projects)
    provider_files = {path for row in projects for path in row.get("attribution", {}).get("provider_generated_files", [])}
    variation_detected = any("provider_live" in path or "live_provider" in path for path in provider_files)
    summary = {
        "status": "passed" if passed == len(projects) and request_count > 0 and fragment_count > 0 and variation_detected else "failed",
        "total": len(projects),
        "passed": passed,
        "failed": len(projects) - passed,
        "projects": projects,
        "provider_used": request_count > 0,
        "provider_request_count": request_count,
        "provider_fragment_count": fragment_count,
        "fallbacks": sum(len(row.get("attribution", {}).get("provider_fallbacks", [])) for row in projects),
        "provider_assisted_output_differs": variation_detected,
        "report": str(REPORT),
        "summary": str(SUMMARY_PATH),
        "review_pack": str(REVIEW_PACK),
    }
    _write_json(SUMMARY_PATH, summary)
    _write_report(summary)
    write_live_review_pack(summary)
    public = {
        "status": summary["status"],
        "provider_used": summary["provider_used"],
        "provider_request_count": summary["provider_request_count"],
        "provider_fragment_count": summary["provider_fragment_count"],
        "fallbacks": summary["fallbacks"],
        "runtime_validation": "passed" if all(row.get("runtime_validation", {}).get("passed") for row in projects) else "failed",
        "projects": [{"case": row["case"], "project": row["project"], "status": row["status"]} for row in projects],
        "report": str(REPORT),
        "summary": str(SUMMARY_PATH),
        "review_pack": str(REVIEW_PACK),
    }
    print(json.dumps(public, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
