from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BENCH_DIR = Path(__file__).resolve().parent
FIXTURES = [
    BENCH_DIR / "fixtures" / "live_provider_unit_converter_cli.json",
    BENCH_DIR / "fixtures" / "live_provider_file_renamer_cli.json",
    BENCH_DIR / "fixtures" / "live_provider_markdown_table_formatter.json",
    BENCH_DIR / "fixtures" / "live_provider_json_config_validator.json",
    BENCH_DIR / "fixtures" / "live_provider_static_site_generator.json",
]
GENERATED = BENCH_DIR / "generated"
SUMMARY_PATH = GENERATED / "live_provider_blind_matrix_summary.json"
REPORT_PATH = BENCH_DIR / "benchmark_report.md"
REVIEW_PACK_PATH = ROOT / "meta" / "reports" / "REVIEW_PACK.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None, timeout: int = 120) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {"cmd": cmd, "exit_code": proc.returncode, "stdout": proc.stdout[-3000:], "stderr": proc.stderr[-3000:]}
    except subprocess.TimeoutExpired as exc:
        return {"cmd": cmd, "exit_code": 124, "stdout": str(exc.stdout or "")[-3000:], "stderr": str(exc.stderr or "")[-3000:]}


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["CTCP_RUNS_ROOT"] = str(Path(tempfile.gettempdir()) / "ctcp_live_provider_blind_matrix_runs")
    env["CTCP_LIVE_BLIND_CANDIDATE"] = "1"
    env["CTCP_LIVE_FULL_CANDIDATE_ATTEMPTS"] = "2"
    env["CTCP_LIVE_FULL_CANDIDATE_MAX_OUTPUT_TOKENS"] = "6000"
    env.setdefault("CTCP_LIVE_FULL_CANDIDATE_TIMEOUT_SEC", "90")
    return env


def _run_dir_from_output(row: dict[str, Any]) -> Path:
    text = f"{row.get('stdout', '')}\n{row.get('stderr', '')}"
    for line in text.splitlines():
        if "run_dir=" in line:
            return Path(line.split("run_dir=", 1)[1].strip())
    raise RuntimeError(f"run_dir not found in command output: {text[-1000:]}")


def _generated_tests(project_dir: Path) -> dict[str, Any]:
    return _run([sys.executable, "-m", "unittest", "discover", "-v"], cwd=project_dir, timeout=60)


def _validate_unit_converter(project_dir: Path) -> dict[str, Any]:
    row = _run([sys.executable, "unit_converter.py", "--from", "km", "--to", "miles", "--value", "1", "--json"], cwd=project_dir)
    try:
        payload = json.loads(row["stdout"])
    except Exception:
        payload = {}
    passed = row["exit_code"] == 0 and abs(float(payload.get("result", 0)) - 0.621371) < 0.01
    return {"passed": passed, "payload": payload, "command": row}


def _validate_file_renamer(project_dir: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ctcp_blind_rename_") as tmp:
        root = Path(tmp)
        sample = root / "a.txt"
        sample.write_text("x", encoding="utf-8")
        row = _run([sys.executable, str(project_dir / "file_renamer.py"), "--directory", str(root), "--prefix", "pre_", "--dry-run"], cwd=project_dir)
        passed = row["exit_code"] == 0 and "pre_a.txt" in row["stdout"] and sample.exists() and not (root / "pre_a.txt").exists()
    return {"passed": passed, "command": row}


def _validate_markdown_table(project_dir: Path) -> dict[str, Any]:
    out = project_dir / "table.md"
    if out.exists():
        out.unlink()
    row = _run([sys.executable, "markdown_table_formatter.py", "--input", "sample.csv", "--output", str(out)], cwd=project_dir)
    text = out.read_text(encoding="utf-8") if out.exists() else ""
    return {"passed": row["exit_code"] == 0 and "Name" in text and "Amount" in text and "Coffee" in text and "|" in text, "output": text, "command": row}


def _validate_config_validator(project_dir: Path) -> dict[str, Any]:
    script = (
        "from config_validator import validate_config, explain_errors\n"
        "ok = validate_config({'name':'demo','enabled':True})\n"
        "bad = validate_config({'enabled':'yes'})\n"
        "assert ok['valid'] is True and ok['config']['retries'] == 3\n"
        "assert bad['valid'] is False and explain_errors(bad['errors'])\n"
    )
    row = _run([sys.executable, "-c", script], cwd=project_dir)
    return {"passed": row["exit_code"] == 0, "command": row}


def _validate_static_site(project_dir: Path) -> dict[str, Any]:
    out = project_dir / "site_out"
    if out.exists():
        shutil.rmtree(out)
    row = _run([sys.executable, "site_generator.py", "--input", "content", "--output", str(out)], cwd=project_dir)
    page = out / "index.html"
    text = page.read_text(encoding="utf-8") if page.exists() else ""
    return {"passed": row["exit_code"] == 0 and "<html" in text.lower(), "output": text[:500], "command": row}


VALIDATORS = {
    "live_provider_unit_converter_cli": _validate_unit_converter,
    "live_provider_file_renamer_cli": _validate_file_renamer,
    "live_provider_markdown_table_formatter": _validate_markdown_table,
    "live_provider_json_config_validator": _validate_config_validator,
    "live_provider_static_site_generator": _validate_static_site,
}


def _validate_project(fixture: dict[str, Any], run_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    project = str(fixture["project"])
    project_dir = run_dir / "project_output" / project
    attribution_path = run_dir / "artifacts" / "generation_attribution.json"
    attribution = _read_json(attribution_path) if attribution_path.exists() else {}
    tests = _generated_tests(project_dir) if project_dir.exists() else {"exit_code": 1, "stdout": "", "stderr": "missing_project_dir"}
    runtime = VALIDATORS[project](project_dir) if project_dir.exists() else {"passed": False, "reason": "missing_project_dir"}
    command_text = "\n".join(" ".join(row.get("cmd", [])) for row in commands)
    ordinary_mainline = all(token in command_text for token in ("new-run", "status", "advance"))
    no_agent_scaffold = not (project_dir / "run_agent.py").exists() and not (project_dir / "runtime").exists()
    outcome = str(attribution.get("provider_candidate_outcome", "failed") or "failed")
    attribution_ok = (
        attribution.get("generation_mode") == "live_provider_blind_candidate"
        and attribution.get("blind_case") is True
        and attribution.get("blind_case_name") == project
        and attribution.get("used_agent_project") is False
        and attribution.get("used_agent_scaffold") is False
        and attribution.get("used_local_agent_runtime") is False
        and attribution.get("used_provider_agent") is True
        and int(attribution.get("provider_request_count", 0) or 0) > 0
        and outcome in {"accepted", "repaired", "fallback", "unsupported"}
    )
    passed = bool(
        project_dir.exists()
        and no_agent_scaffold
        and ordinary_mainline
        and attribution_ok
        and tests["exit_code"] == 0
        and runtime.get("passed") is True
    )
    return {
        "case": fixture["case"],
        "project": project,
        "status": "passed" if passed else "failed",
        "outcome": outcome,
        "project_dir": str(project_dir),
        "attribution_path": str(attribution_path),
        "attribution": attribution,
        "generated_tests": tests,
        "runtime_validation": runtime,
        "ordinary_mainline": ordinary_mainline,
        "no_agent_scaffold": no_agent_scaffold,
    }


def _run_case(path: Path) -> dict[str, Any]:
    fixture = _read_json(path)
    project = str(fixture["project"])
    run_id = f"blind-{project}-{int(time.time() * 1000)}"
    goal = str(fixture["goal"]) + " Use ordinary CTCP new-run/status/advance and source_generation; do not use agent scaffold."
    env = _env()
    commands: list[dict[str, Any]] = []
    new_run = _run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", goal, "--run-id", run_id], env=env, timeout=180)
    commands.append(new_run)
    if new_run["exit_code"] != 0:
        return {"case": fixture["case"], "project": project, "status": "failed", "commands": commands, "reason": "new_run_failed"}
    run_dir = _run_dir_from_output(new_run)
    commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env, timeout=90))
    for _ in range(16):
        commands.append(_run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=420))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / str(fixture["startup"])).exists():
            break
    result = _validate_project(fixture, run_dir, commands)
    result["commands"] = commands
    result["run_dir"] = str(run_dir)
    return result


def _write_report(summary: dict[str, Any]) -> None:
    lines = [
        "# Live Provider Blind Matrix Benchmark",
        "",
        "## Summary",
        f"- status: `{summary['status']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- accepted_count: `{summary['accepted_count']}`",
        f"- repaired_count: `{summary['repaired_count']}`",
        f"- fallback_count: `{summary['fallback_count']}`",
        f"- unsupported_count: `{summary['unsupported_count']}`",
        f"- failed_count: `{summary['failed_count']}`",
        f"- provider_request_count: `{summary['provider_request_count']}`",
        f"- provider_project_candidate_count: `{summary['provider_project_candidate_count']}`",
        f"- acceptance_rate: `{summary['acceptance_rate']}`",
        f"- accepted_or_repaired_rate: `{summary['accepted_or_repaired_rate']}`",
        f"- phase20_gate_passed: `{summary['phase20_gate_passed']}`",
        "",
        "## Cases",
    ]
    for row in summary["cases"]:
        lines.append(f"- `{row['project']}`: status=`{row['status']}`, outcome=`{row.get('outcome', 'failed')}`")
    lines.extend(["", "## Attribution"])
    for row in summary["cases"]:
        lines.append(f"- `{row['project']}`: `{row.get('attribution_path', '')}`")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_blind_review_pack(summary: dict[str, Any]) -> None:
    REVIEW_PACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# CTCP Review Pack",
        "",
        "## Live Provider Blind Matrix Summary",
        "",
        f"- cases: `{summary.get('case_count')}`",
        f"- provider request count: `{summary.get('provider_request_count')}`",
        f"- provider project candidate count: `{summary.get('provider_project_candidate_count')}`",
        f"- accepted count: `{summary.get('accepted_count')}`",
        f"- repaired count: `{summary.get('repaired_count')}`",
        f"- fallback count: `{summary.get('fallback_count')}`",
        f"- unsupported count: `{summary.get('unsupported_count')}`",
        f"- failed count: `{summary.get('failed_count')}`",
        f"- acceptance rate: `{summary.get('acceptance_rate')}`",
        f"- accepted or repaired rate: `{summary.get('accepted_or_repaired_rate')}`",
        f"- Phase 20 gate passed: `{summary.get('phase20_gate_passed')}`",
        "- ordinary mainline: `new-run/status/advance`",
        "- agent-project/scaffold substitution: `no`",
        "- bounded repair: max `1` attempt per project",
        "",
        "| Case | Outcome | Status | Attribution |",
        "|---|---:|---:|---|",
    ]
    for row in summary.get("cases", []):
        lines.append(f"| `{row.get('project')}` | `{row.get('outcome')}` | `{row.get('status')}` | `{row.get('attribution_path')}` |")
    lines.extend([
        "",
        "## Risk Notes",
        "- Blind provider candidates remain limited to small stdlib Python projects with explicit validators.",
        "- Deterministic repair/fallback is recorded in attribution and does not bypass generated tests or runtime validation.",
        "",
        "## Reproduction Commands",
        "- `.\\.venv\\Scripts\\python.exe tests\\live_provider_blind_matrix\\run_live_provider_blind_matrix.py`",
        "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_blind_matrix -v`",
    ])
    REVIEW_PACK_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    cases = [_run_case(path) for path in FIXTURES]
    accepted = sum(1 for row in cases if row.get("outcome") == "accepted")
    repaired = sum(1 for row in cases if row.get("outcome") == "repaired")
    fallback = sum(1 for row in cases if row.get("outcome") == "fallback")
    unsupported = sum(1 for row in cases if row.get("outcome") == "unsupported")
    failed = sum(1 for row in cases if row.get("status") != "passed")
    request_count = sum(int(row.get("attribution", {}).get("provider_request_count", 0) or 0) for row in cases)
    candidate_count = sum(int(row.get("attribution", {}).get("provider_project_candidate_count", 0) or 0) for row in cases)
    repair_attempts = sum(int(row.get("attribution", {}).get("provider_repair_attempt_count", 0) or 0) for row in cases)
    acceptance_rate = round(accepted / max(len(cases), 1), 3)
    accepted_or_repaired_rate = round((accepted + repaired) / max(len(cases), 1), 3)
    phase20_gate_passed = bool(
        accepted >= 2
        and accepted + repaired >= 4
        and fallback <= 1
        and failed == 0
    )
    status = "passed" if len(cases) == 5 and phase20_gate_passed else "failed"
    summary = {
        "status": status,
        "case_count": len(cases),
        "accepted_count": accepted,
        "repaired_count": repaired,
        "fallback_count": fallback,
        "unsupported_count": unsupported,
        "failed_count": failed,
        "provider_request_count": request_count,
        "provider_project_candidate_count": candidate_count,
        "repair_attempt_count": repair_attempts,
        "acceptance_rate": acceptance_rate,
        "accepted_or_repaired_rate": accepted_or_repaired_rate,
        "phase20_gate_passed": phase20_gate_passed,
        "cases": cases,
        "summary": str(SUMMARY_PATH),
    }
    _write_json(SUMMARY_PATH, summary)
    _write_report(summary)
    write_blind_review_pack(summary)
    print(json.dumps({k: summary[k] for k in ("status", "case_count", "accepted_count", "repaired_count", "fallback_count", "unsupported_count", "failed_count", "provider_request_count", "provider_project_candidate_count", "repair_attempt_count", "acceptance_rate", "accepted_or_repaired_rate", "phase20_gate_passed")}, indent=2))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
