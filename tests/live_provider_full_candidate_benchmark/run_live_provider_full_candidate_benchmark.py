from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
import uuid
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
    BENCH_DIR / "fixtures" / "live_provider_text_stats_cli.json",
    BENCH_DIR / "fixtures" / "live_provider_password_policy_package.json",
    BENCH_DIR / "fixtures" / "invalid_provider_candidate_fallback.json",
]
GENERATED = BENCH_DIR / "generated"
SUMMARY_PATH = GENERATED / "live_provider_full_candidate_summary.json"
REPORT = BENCH_DIR / "benchmark_report.md"
REVIEW_PACK = ROOT / "meta" / "reports" / "REVIEW_PACK.md"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _env(force_invalid: bool = False) -> dict[str, str]:
    env = base._env()
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_live_provider_full_candidate_runs").resolve())
    env["CTCP_LIVE_FULL_CANDIDATE"] = "1"
    env["CTCP_LIVE_FULL_CANDIDATE_MAX_OUTPUT_TOKENS"] = str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_MAX_OUTPUT_TOKENS", "3000"))
    env["CTCP_LIVE_FULL_CANDIDATE_TIMEOUT_SEC"] = str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_TIMEOUT_SEC", "45"))
    env["CTCP_LIVE_FULL_CANDIDATE_ATTEMPTS"] = str(os.environ.get("CTCP_LIVE_FULL_CANDIDATE_ATTEMPTS", "2"))
    env.pop("CTCP_PROVIDER_ASSISTED", None)
    env.pop("CTCP_PROVIDER_ASSISTED_FIXTURE", None)
    env.pop("CTCP_LIVE_PROVIDER_ASSISTED", None)
    env.pop("CTCP_LIVE_PROVIDER_FORCE_INVALID", None)
    if force_invalid:
        env["CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID"] = "1"
    else:
        env.pop("CTCP_LIVE_FULL_CANDIDATE_FORCE_INVALID", None)
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


def _validate_text_stats(project_dir: Path) -> dict[str, Any]:
    out = project_dir / "live_provider_stats.json"
    result = base._run([sys.executable, "text_stats.py", "--input", "sample.txt", "--output", str(out)], env=base._test_env(project_dir), cwd=project_dir, timeout=60)
    data = _read_json(out) if out.exists() else {}
    return {
        "passed": result["exit_code"] == 0
        and out.exists()
        and int(data.get("characters", -1)) > 0
        and int(data.get("words", -1)) >= 4
        and int(data.get("unique_words", -1)) >= 3
        and isinstance(data.get("top_words"), list),
        "cli": result,
        "output": data,
    }


def _validate_password_policy(project_dir: Path) -> dict[str, Any]:
    script = (
        "from password_policy import validate_password, password_score, explain_password\n"
        "assert validate_password('StrongPass1!')['valid'] is True\n"
        "assert validate_password('weak')['valid'] is False\n"
        "assert password_score('StrongPass1!') > password_score('weak')\n"
        "assert explain_password('weak')\n"
    )
    result = base._run([sys.executable, "-c", script], env=base._test_env(project_dir), cwd=project_dir, timeout=60)
    return {"passed": result["exit_code"] == 0, "import_check": result}


def _validate_project(case: str, project: str, run_dir: Path, commands: list[dict[str, Any]]) -> dict[str, Any]:
    project_dir = run_dir / "project_output" / project
    attribution_path = run_dir / "artifacts" / "generation_attribution.json"
    provenance_path = run_dir / "artifacts" / "project_generation_provenance.json"
    report_path = project_dir / "provider_full_candidate_report.json"
    attribution = _read_json(attribution_path) if attribution_path.exists() else {}
    provenance = _read_json(provenance_path) if provenance_path.exists() else {}
    provider_report = _read_json(report_path) if report_path.exists() else {}
    if not project_dir.exists():
        return {
            "case": case,
            "project": project,
            "status": "failed",
            "project_dir": str(project_dir),
            "run_dir": str(run_dir),
            "generated_tests_passed": False,
            "runtime_validation": {"passed": False, "reason": "missing_project_dir"},
            "ordinary_mainline": False,
            "no_agent_scaffold": False,
            "attribution": attribution,
            "attribution_path": str(attribution_path),
            "provenance": provenance,
            "provenance_path": str(provenance_path),
            "provider_full_candidate_report": provider_report,
            "provider_full_candidate_report_path": str(report_path),
            "provider_ok": False,
            "passed": False,
        }
    tests = base._run([sys.executable, "-m", "unittest", "discover", "-v"], env=base._test_env(project_dir), cwd=project_dir, timeout=90)
    runtime = _validate_password_policy(project_dir) if project == "live_provider_password_policy_package" else _validate_text_stats(project_dir)
    command_text = "\n".join(str(row.get("cmd", "")) for row in commands)
    ordinary_mainline = all(token in command_text for token in ("new-run", "status", "advance"))
    no_agent_scaffold = not (project_dir / "run_agent.py").exists() and not (project_dir / "runtime").exists()
    validation = attribution.get("provider_candidate_validation", {}) if isinstance(attribution.get("provider_candidate_validation", {}), dict) else {}
    generated_files = [str(path) for path in attribution.get("provider_generated_files", [])]
    generated_exist = bool(generated_files) and all((run_dir / rel).exists() for rel in generated_files)
    invalid_case = case == "invalid_provider_candidate_fallback"
    provider_ok = (
        attribution.get("used_provider_agent") is True
        and attribution.get("live_provider_used") is True
        and attribution.get("provider_authorship") == "provider_candidate_authored"
        and attribution.get("generation_mode") == "live_provider_full_candidate"
        and int(attribution.get("provider_request_count", 0) or 0) > 0
        and int(attribution.get("provider_project_candidate_count", 0) or 0) > 0
        and attribution.get("used_agent_project") is False
        and attribution.get("used_agent_scaffold") is False
        and attribution.get("used_local_agent_runtime") is False
        and attribution.get("used_local_materializer") is True
    )
    if invalid_case:
        provider_ok = provider_ok and attribution.get("provider_candidate_accepted") is False and attribution.get("fallback_triggered") is True
    else:
        provider_ok = provider_ok and validation.get("manifest_valid") is True and validation.get("paths_safe") is True
        provider_ok = provider_ok and attribution.get("provider_candidate_accepted") is True and attribution.get("fallback_triggered") is False and generated_exist
        provider_ok = provider_ok and validation.get("generated_tests_passed") is True and validation.get("runtime_validation_passed") is True
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
        "provider_full_candidate_report": provider_report,
        "provider_full_candidate_report_path": str(report_path),
        "provider_ok": provider_ok,
        "passed": passed,
    }


def _run_case(path: Path) -> dict[str, Any]:
    fixture = _read_json(path)
    case = str(fixture["case"])
    project = str(fixture["project"])
    force_invalid = case == "invalid_provider_candidate_fallback"
    env = _env(force_invalid=force_invalid)
    commands: list[dict[str, Any]] = []
    run_id = f"live-full-{case}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
    goal = str(fixture["goal"]) + " Use ordinary CTCP new-run/status/advance and source_generation; do not use agent scaffold."
    new_run = base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "new-run", "--goal", goal, "--run-id", run_id], env=env, timeout=180)
    commands.append(new_run)
    run_dir = _run_dir_from_output(new_run)
    base._force_local_dispatch(run_dir)
    commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
    startup = "password_policy/__init__.py" if project == "live_provider_password_policy_package" else "text_stats.py"
    for _ in range(24):
        commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "advance", "--run-dir", str(run_dir), "--max-steps", "1"], env=env, timeout=360))
        if (run_dir / "artifacts" / "source_generation_report.json").exists() and (run_dir / "project_output" / project / startup).exists():
            break
    commands.append(base._run([sys.executable, str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)], env=env))
    validation = _validate_project(case, project, run_dir, commands)
    return {"commands": commands, **validation}


def _write_report(summary: dict[str, Any]) -> None:
    lines = ["# Live Provider Full Candidate Benchmark", ""]
    lines.append(f"- status: `{summary['status']}`")
    lines.append(f"- passed: `{summary['passed']}/{summary['total']}`")
    lines.append(f"- provider_request_count: `{summary['provider_request_count']}`")
    lines.append(f"- provider_project_candidate_count: `{summary['provider_project_candidate_count']}`")
    lines.append(f"- provider_candidate_accepted_count: `{summary['provider_candidate_accepted_count']}`")
    lines.append(f"- fallback_count: `{summary['fallback_count']}`")
    lines.append("")
    lines.append("## Live Provider Full Candidate Summary")
    lines.append("| Case | Project | Requests | Candidates | Accepted | Repaired | Fallback | Runtime |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for row in summary["cases"]:
        attr = row.get("attribution", {})
        lines.append(
            f"| {row['case']} | {row['project']} | `{attr.get('provider_request_count')}` | "
            f"`{attr.get('provider_project_candidate_count')}` | `{attr.get('provider_candidate_accepted')}` | "
            f"`{attr.get('provider_candidate_repaired')}` | `{attr.get('fallback_triggered')}` | "
            f"`{row.get('runtime_validation', {}).get('passed')}` |"
        )
    lines.append("")
    lines.append("## Attribution")
    for row in summary["cases"]:
        lines.append(f"- `{row['case']}` attribution: `{row.get('attribution_path', '')}`")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_full_candidate_review_pack(summary: dict[str, Any]) -> None:
    existing_phase_sections = ""
    if REVIEW_PACK.exists():
        existing = REVIEW_PACK.read_text(encoding="utf-8", errors="replace")
        if "## Phase 20 Acceptance Hardening Summary" in existing:
            existing_phase_sections = existing.split("## Phase 20 Acceptance Hardening Summary", 1)[1].rstrip()
            existing_phase_sections = existing_phase_sections.replace(
                "## Phase 21 Medium Project Generation Summary",
                "## Phase 21B Medium Candidate Recovery Summary",
            )
    if not existing_phase_sections:
        phase20_path = ROOT / "tests" / "live_provider_blind_matrix" / "generated" / "live_provider_blind_matrix_summary.json"
        phase21b_path = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"
        if phase20_path.exists() and phase21b_path.exists():
            phase20 = _read_json(phase20_path)
            phase21b = _read_json(phase21b_path)
            phase_lines = [
                f"- previous accepted/repaired/fallback counts: `0/3/2`",
                f"- new accepted/repaired/fallback counts: `{phase20.get('accepted_count')}/{phase20.get('repaired_count')}/{phase20.get('fallback_count')}`",
                f"- acceptance_rate: `{phase20.get('acceptance_rate')}`",
                f"- accepted_or_repaired_rate: `{phase20.get('accepted_or_repaired_rate')}`",
                f"- gate passed: `{phase20.get('phase20_gate_passed')}`",
                "- changed logic: provider prompt contract, self-check requirements, manifest normalization, and strict gate metrics.",
                "- fixture lowering: `no`",
                "",
                "## Phase 21B Medium Candidate Recovery Summary",
                "",
                f"- medium cases: `{phase21b.get('case_count')}`",
                f"- provider request count: `{phase21b.get('provider_request_count')}`",
                f"- provider plan valid count: `{phase21b.get('provider_plan_valid_count')}`",
                f"- provider manifest valid count: `{phase21b.get('provider_manifest_valid_count')}`",
                f"- provider batch count: `{phase21b.get('provider_batch_count')}`",
                f"- provider project candidate count: `{phase21b.get('provider_project_candidate_count')}`",
                f"- accepted count: `{phase21b.get('accepted_count')}`",
                f"- repaired count: `{phase21b.get('repaired_count')}`",
                f"- fallback count: `{phase21b.get('fallback_count')}`",
                f"- failed count: `{phase21b.get('failed_count')}`",
                "- ordinary mainline: `new-run/status/advance`",
                "- agent-project/scaffold substitution: `no`",
            ]
            existing_phase_sections = "\n".join(phase_lines)
    lines = [
        "# CTCP Live Provider Full Candidate Review Pack",
        "",
        "## Live Provider Full Candidate Summary",
        "| Case | Provider Called | Requests | Candidate Count | Accepted | Repaired | Fallback | Generated Files | Runtime Valid |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for row in summary.get("cases", []):
        attr = row.get("attribution", {})
        validation = attr.get("provider_candidate_validation", {}) if isinstance(attr.get("provider_candidate_validation", {}), dict) else {}
        lines.append(
            f"| {row.get('case')} | `{attr.get('live_provider_used')}` | `{attr.get('provider_request_count')}` | "
            f"`{attr.get('provider_project_candidate_count')}` | `{attr.get('provider_candidate_accepted')}` | "
            f"`{attr.get('provider_candidate_repaired')}` | `{attr.get('fallback_triggered')}` | "
            f"`{', '.join(attr.get('provider_generated_files', []))}` | `{validation.get('runtime_validation_passed')}` |"
        )
    lines.extend(
        [
            "",
            "## Deterministic Guardrails",
            "- Ordinary mainline remains `new-run/status/advance`.",
            "- Provider returns a structured file manifest and cannot write outside `project_output`.",
            "- Candidate paths, safety, syntax, generated tests, imports, and runtime behavior are validated.",
            "- Invalid candidates fall back to deterministic materializers with attribution evidence.",
            "",
            "## Benchmark Summary",
            f"- live provider full candidate benchmark: `{summary.get('passed')}/{summary.get('total')}`",
            f"- provider request count: `{summary.get('provider_request_count')}`",
            f"- provider project candidate count: `{summary.get('provider_project_candidate_count')}`",
            f"- accepted candidate count: `{summary.get('provider_candidate_accepted_count')}`",
            f"- fallback count: `{summary.get('fallback_count')}`",
            f"- report: `{REPORT}`",
            f"- summary: `{SUMMARY_PATH}`",
            "",
            "## Reproduction Commands",
            "- `.\\.venv\\Scripts\\python.exe tests\\live_provider_full_candidate_benchmark\\run_live_provider_full_candidate_benchmark.py`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_full_candidate_generation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_full_candidate_attribution -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_full_candidate_validation -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_full_candidate_fallback -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_full_candidate_safety -v`",
            "- `.\\.venv\\Scripts\\python.exe -m unittest tests.test_live_provider_full_candidate_review_pack -v`",
            "",
            "## Risks For Human Review",
            "- Full candidate mode is intentionally limited to two small non-server project types.",
            "- Provider-authored candidates remain accepted only after deterministic validation or repaired/fallback materialization.",
        ]
    )
    if existing_phase_sections:
        lines.extend(["", "## Phase 20 Acceptance Hardening Summary", existing_phase_sections])
    REVIEW_PACK.parent.mkdir(parents=True, exist_ok=True)
    REVIEW_PACK.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    GENERATED.mkdir(parents=True, exist_ok=True)
    projects = [_run_case(path) for path in FIXTURES]
    passed = sum(1 for row in projects if row["status"] == "passed")
    request_count = sum(int(row.get("attribution", {}).get("provider_request_count", 0) or 0) for row in projects)
    candidate_count = sum(int(row.get("attribution", {}).get("provider_project_candidate_count", 0) or 0) for row in projects)
    accepted_count = sum(1 for row in projects if row.get("attribution", {}).get("provider_candidate_accepted") is True)
    fallback_count = sum(1 for row in projects if row.get("attribution", {}).get("fallback_triggered") is True)
    summary = {
        "status": "passed" if passed == len(projects) and request_count > 0 and candidate_count >= len(projects) and accepted_count >= 2 and fallback_count >= 1 else "failed",
        "total": len(projects),
        "passed": passed,
        "failed": len(projects) - passed,
        "cases": projects,
        "provider_request_count": request_count,
        "provider_project_candidate_count": candidate_count,
        "provider_candidate_accepted_count": accepted_count,
        "fallback_count": fallback_count,
        "attribution_paths": [row.get("attribution_path", "") for row in projects],
        "project_output_paths": [row.get("project_dir", "") for row in projects],
        "report": str(REPORT),
        "summary": str(SUMMARY_PATH),
        "review_pack": str(REVIEW_PACK),
    }
    _write_json(SUMMARY_PATH, summary)
    _write_report(summary)
    write_full_candidate_review_pack(summary)
    public = {
        "status": summary["status"],
        "total": summary["total"],
        "passed": summary["passed"],
        "failed": summary["failed"],
        "provider_request_count": summary["provider_request_count"],
        "provider_project_candidate_count": summary["provider_project_candidate_count"],
        "provider_candidate_accepted_count": summary["provider_candidate_accepted_count"],
        "fallback_count": summary["fallback_count"],
        "cases": [{"case": row["case"], "project": row["project"], "status": row["status"]} for row in projects],
        "report": str(REPORT),
        "summary": str(SUMMARY_PATH),
        "review_pack": str(REVIEW_PACK),
    }
    print(json.dumps(public, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
