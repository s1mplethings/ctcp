from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = Path(__file__).resolve().parent
FIXTURES = BENCH_DIR / "fixtures"
GENERATED = BENCH_DIR / "generated"
REPORT = BENCH_DIR / "benchmark_report.md"
SUMMARY_PATH = GENERATED / "non_web_matrix_summary.json"
REVIEW_PACK = ROOT / "meta" / "reports" / "REVIEW_PACK.md"
PROJECTS = (
    "csv_expense_analyzer",
    "log_analyzer_cli",
    "text_utils_package",
    "terminal_quiz_game",
)
FIXTURE_BY_PROJECT = {
    "csv_expense_analyzer": "csv_expense_analyzer.json",
    "log_analyzer_cli": "log_analyzer.json",
    "text_utils_package": "text_utils_package.json",
    "terminal_quiz_game": "terminal_quiz_game.json",
}
STARTUP_BY_PROJECT = {
    "csv_expense_analyzer": "expense_analyzer.py",
    "log_analyzer_cli": "log_analyzer.py",
    "text_utils_package": "text_utils/__init__.py",
    "terminal_quiz_game": "quiz_game.py",
}


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
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_non_web_project_matrix_runs").resolve())
    env["CTCP_ANALYSIS_PROFILE"] = "fast"
    env.pop("CTCP_FORCE_PROVIDER", None)
    env.pop("CTCP_ALLOW_LOCAL_MAINLINE_PROVIDER", None)
    return env


def _goal_from_fixture(path: Path) -> str:
    fixture = _read_json(path)
    return (
        f"{fixture['goal']} "
        "Use the ordinary CTCP project generation mainline and write project_output artifacts, "
        "generated tests, provenance, attribution, and runnable local validation files."
    )


def _run_dir_from_output(row: dict[str, Any]) -> Path:
    text = f"{row.get('stdout', '')}\n{row.get('stderr', '')}"
    match = re.search(r"run_dir=([^\r\n]+)", text)
    if match:
        return Path(match.group(1).strip()).resolve()
    pointer = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
    if pointer.exists():
        return Path(pointer.read_text(encoding="utf-8").strip()).resolve()
    raise RuntimeError("could not locate run_dir")


def _test_env(project_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(project_dir) if not existing else str(project_dir) + os.pathsep + existing
    return env


def _validate_csv(project_dir: Path) -> dict[str, Any]:
    output = project_dir / "benchmark_report.json"
    result = _run(
        [sys.executable, "expense_analyzer.py", "--input", "sample_expenses.csv", "--output", str(output)],
        env=_test_env(project_dir),
        cwd=project_dir,
    )
    report = _read_json(output) if output.exists() else {}
    passed = (
        result["exit_code"] == 0
        and output.exists()
        and round(float(report.get("category_totals", {}).get("Food", 0)), 2) == 20.0
        and round(float(report.get("monthly_totals", {}).get("2026-01", 0)), 2) == 32.5
    )
    return {"passed": passed, "cli": result, "output_path": str(output), "report": report}


def _validate_log(project_dir: Path) -> dict[str, Any]:
    output = project_dir / "summary.json"
    result = _run(
        [sys.executable, "log_analyzer.py", "--input", "sample.log", "--output", str(output)],
        env=_test_env(project_dir),
        cwd=project_dir,
    )
    summary = _read_json(output) if output.exists() else {}
    levels = summary.get("level_counts", {})
    top_errors = summary.get("top_errors", [])
    passed = (
        result["exit_code"] == 0
        and output.exists()
        and levels.get("INFO") == 1
        and levels.get("WARN") == 1
        and levels.get("ERROR") == 2
        and bool(top_errors)
        and top_errors[0].get("message") == "disk full"
    )
    return {"passed": passed, "cli": result, "output_path": str(output), "summary": summary}


def _validate_text_utils(project_dir: Path) -> dict[str, Any]:
    snippet = (
        "import json; from text_utils import slugify, word_count, extract_keywords, normalize_whitespace; "
        "print(json.dumps({'slug': slugify('Hello, CTCP World!'), 'words': word_count('one two two'), "
        "'keywords': extract_keywords('The quick brown fox jumps quick'), "
        "'norm': normalize_whitespace('  a\\n b\\t c  ')}))"
    )
    result = _run([sys.executable, "-c", snippet], env=_test_env(project_dir), cwd=project_dir)
    payload = json.loads(result["stdout"].strip()) if result["exit_code"] == 0 and result["stdout"].strip() else {}
    passed = (
        result["exit_code"] == 0
        and payload.get("slug") == "hello-ctcp-world"
        and payload.get("words") == 3
        and "quick" in payload.get("keywords", [])
        and payload.get("norm") == "a b c"
    )
    return {"passed": passed, "import_result": result, "payload": payload}


def _validate_quiz(project_dir: Path) -> dict[str, Any]:
    result = _run(
        [sys.executable, "quiz_game.py", "--questions", "sample_questions.json", "--test-mode", "--answers", "B,A"],
        env=_test_env(project_dir),
        cwd=project_dir,
    )
    payload = json.loads(result["stdout"].strip()) if result["exit_code"] == 0 and result["stdout"].strip() else {}
    passed = result["exit_code"] == 0 and payload.get("score") == 2 and payload.get("total") == 2
    return {"passed": passed, "cli": result, "payload": payload}


def _validate_project(project: str, run_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    project_dir = run_dir / "project_output" / project
    tests = _run([sys.executable, "-m", "unittest", "discover", "-v"], env=_test_env(project_dir), cwd=project_dir, timeout=90)
    runtime = {
        "csv_expense_analyzer": _validate_csv,
        "log_analyzer_cli": _validate_log,
        "text_utils_package": _validate_text_utils,
        "terminal_quiz_game": _validate_quiz,
    }[project](project_dir)
    provenance_path = run_dir / "artifacts" / "project_generation_provenance.json"
    attribution_path = run_dir / "artifacts" / "generation_attribution.json"
    provenance = _read_json(provenance_path) if provenance_path.exists() else {}
    attribution = _read_json(attribution_path) if attribution_path.exists() else {}
    analysis_path = run_dir / "artifacts" / "analysis.md"
    source_report = run_dir / "artifacts" / "source_generation_report.json"
    no_agent_scaffold = not (project_dir / "run_agent.py").exists() and not (project_dir / "runtime").exists()
    command_text = "\n".join(str(row.get("cmd", "")) for row in commands)
    ordinary_mainline = all(token in command_text for token in ("new-run", "status", "advance"))
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
        and bool(runtime.get("passed"))
        and no_agent_scaffold
        and ordinary_mainline
        and analysis_path.exists()
        and source_report.exists()
        and attribution_ok
        and bool(provenance.get("local_materializer_used"))
    )
    return {
        "project": project,
        "status": "passed" if passed else "failed",
        "project_dir": str(project_dir),
        "generated_tests_passed": tests["exit_code"] == 0,
        "runtime_validation": runtime,
        "persistence_validation": runtime,
        "provenance": provenance,
        "provenance_path": str(provenance_path),
        "attribution": attribution,
        "attribution_path": str(attribution_path),
        "analysis_path": str(analysis_path),
        "source_generation_report_path": str(source_report),
        "no_agent_scaffold": no_agent_scaffold,
        "ordinary_mainline": ordinary_mainline,
        "passed": passed,
    }


def _write_project_review_pack(run_dir: Path, row: dict[str, Any]) -> None:
    attribution = row.get("attribution", {})
    lines = [
        "# Generation Review Pack",
        "",
        f"- project: `{row['project']}`",
        f"- status: `{row['status']}`",
        f"- ordinary_mainline: `{row.get('ordinary_mainline', False)}`",
        f"- used_agent_project: `{attribution.get('used_agent_project')}`",
        f"- used_agent_scaffold: `{attribution.get('used_agent_scaffold')}`",
        f"- used_local_agent_runtime: `{attribution.get('used_local_agent_runtime')}`",
        f"- used_local_materializer: `{attribution.get('used_local_materializer')}`",
        f"- provider_authorship: `{attribution.get('provider_authorship')}`",
        f"- project_output_path: `{row.get('project_dir', '')}`",
        f"- attribution_path: `{row.get('attribution_path', '')}`",
    ]
    target = run_dir / "artifacts" / "review_pack.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_case(project: str) -> dict[str, Any]:
    fixture_path = FIXTURES / FIXTURE_BY_PROJECT[project]
    env = _env()
    commands: list[dict[str, Any]] = []
    run_id = f"non-web-{project}-{int(time.time())}"
    new_run = _run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", _goal_from_fixture(fixture_path), "--run-id", run_id], env=env)
    commands.append(new_run)
    run_dir = _run_dir_from_output(new_run)
    commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
    startup = STARTUP_BY_PROJECT[project]
    for _ in range(30):
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=240))
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / startup).exists():
            break
    validation = _validate_project(project, run_dir, commands)
    _write_project_review_pack(run_dir, validation)
    return {"run_dir": str(run_dir), "commands": commands, **validation}


def _write_report(summary: dict[str, Any]) -> None:
    lines = ["# Non-Web Project Type Matrix", ""]
    lines.append(f"- matrix_total: `{summary['matrix_total']}`")
    lines.append(f"- passed: `{summary['passed']}`")
    lines.append(f"- failed: `{summary['failed']}`")
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
        lines.append(f"- generated_tests_passed: `{row.get('generated_tests_passed')}`")
        lines.append(f"- runtime_validation: `{row.get('runtime_validation', {}).get('passed')}`")
        lines.append(f"- ordinary_mainline: `{row.get('ordinary_mainline')}`")
        lines.append(f"- provenance_path: `{row.get('provenance_path', '')}`")
        lines.append(f"- attribution_path: `{row.get('attribution_path', '')}`")
        lines.append("")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_review_pack(summary: dict[str, Any]) -> None:
    rows = summary.get("projects", [])
    lines = [
        "# CTCP Phase 15 Review Pack",
        "",
        "## Purpose",
        "Validate ordinary concrete project generation across non-web project types and expose generation attribution evidence.",
        "",
        "## Modified Files",
        "| Area | Paths |",
        "|---|---|",
        "| generation | `tools/providers/project_generation_attribution.py`, `tools/providers/project_generation_non_web_fast_paths.py`, `tools/providers/project_generation_fast_path_registry.py` |",
        "| materialization | `tools/providers/project_generation_artifacts.py`, `tools/providers/project_generation_generic_materializers.py`, `tools/providers/project_generation_source_stage.py`, `tools/providers/project_generation_template_writer.py` |",
        "| benchmarks | `tests/non_web_project_matrix/`, concrete/full-stack benchmark runners |",
        "| docs/meta | `README.md`, `docs/project_generation.md`, `docs/concrete_project_pipeline.md`, `meta/reports/REVIEW_PACK.md` |",
        "",
        "## New Project Types",
        "| Project | Runtime | Validation |",
        "|---|---|---|",
        "| CSV Expense Analyzer CLI | argparse + csv | CLI report totals and generated tests |",
        "| Log Analyzer CLI | argparse + log parser | JSON level counts/top errors and generated tests |",
        "| Text Utilities Python Package | importable package | function imports and generated tests |",
        "| Terminal Quiz Game | CLI test mode | deterministic score and generated tests |",
        "",
        "## Attribution Evidence",
        "| Project | ordinary_mainline | used_agent_project | used_agent_scaffold | used_local_agent_runtime | used_local_materializer | provider_authorship |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        attr = row.get("attribution", {})
        lines.append(
            f"| {row['project']} | `{attr.get('ordinary_mainline')}` | `{attr.get('used_agent_project')}` | "
            f"`{attr.get('used_agent_scaffold')}` | `{attr.get('used_local_agent_runtime')}` | "
            f"`{attr.get('used_local_materializer')}` | `{attr.get('provider_authorship')}` |"
        )
    lines.extend(
        [
            "",
            "## Benchmark Summary",
            "| Benchmark | Result |",
            "|---|---|",
            f"| non_web_project_matrix | `{summary.get('passed')}/{summary.get('matrix_total')}` |",
            "| concrete_project_benchmark | run during final verification |",
            "| concrete_project_matrix | run during final verification |",
            "| full_stack_app_benchmark | run during final verification |",
            "| agent planner/runtime/factory | run during final verification |",
            "",
            "## Failures And Skips",
            f"- non-web failed: `{summary.get('failed')}`",
            f"- non-web unsupported: `{summary.get('unsupported')}`",
            "",
            "## Artifact Paths",
            f"- non-web report: `{REPORT}`",
            f"- non-web summary: `{SUMMARY_PATH}`",
            "- per-run attribution: `<run_dir>/artifacts/generation_attribution.json`",
            "- per-run review pack: `<run_dir>/artifacts/review_pack.md`",
            "",
            "## Reproduction Commands",
            "- `.\\.venv\\Scripts\\python.exe tests\\non_web_project_matrix\\run_non_web_matrix.py`",
            "- `.\\.venv\\Scripts\\python.exe tests\\full_stack_app_benchmark\\run_full_stack_benchmark.py`",
            "- `.\\.venv\\Scripts\\python.exe tests\\concrete_project_matrix\\run_matrix_benchmark.py`",
            "- `.\\.venv\\Scripts\\python.exe tests\\concrete_project_benchmark\\run_concrete_project_benchmark.py`",
            "",
            "## Risks For Human Review",
            "- Fast paths are deterministic local materializers; provider source authorship remains `not_claimed`.",
            "- The matrix broadens project types but does not prove arbitrary project generation.",
            "- Non-web validation intentionally avoids HTTP/server contracts.",
            "",
            "## Next Steps",
            "- Add more non-web categories such as data transform libraries, desktop scripts, and file converters.",
            "- Compare provider-authored output against local materializer output in a separate attribution benchmark.",
        ]
    )
    REVIEW_PACK.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    projects = [_run_case(project) for project in PROJECTS]
    passed = sum(1 for row in projects if row["status"] == "passed")
    summary = {
        "matrix_total": len(PROJECTS),
        "passed": passed,
        "failed": len(PROJECTS) - passed,
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
        "review_pack": str(REVIEW_PACK),
    }
    _write_json(SUMMARY_PATH, summary)
    _write_report(summary)
    _write_review_pack(summary)
    public = {
        "matrix_total": summary["matrix_total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "unsupported": 0,
        "projects": [{"project": row["project"], "status": row["status"]} for row in projects],
        "report": str(REPORT),
        "summary": str(SUMMARY_PATH),
        "review_pack": str(REVIEW_PACK),
    }
    print(json.dumps(public, ensure_ascii=False, indent=2))
    return 0 if passed == len(PROJECTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
