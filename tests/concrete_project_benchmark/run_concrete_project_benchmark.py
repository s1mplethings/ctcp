#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import analysis_stage_progress
from tools.providers.project_generation_contracts import write_generation_contract_artifacts

BENCH_DIR = ROOT / "tests" / "concrete_project_benchmark"
FIXTURE = BENCH_DIR / "fixtures" / "issue_tracker_api.json"
GENERATED_DIR = BENCH_DIR / "generated" / "issue_tracker_api"
PROJECT_COPY_DIR = GENERATED_DIR / "project"
PROJECT_PATH_POINTER = GENERATED_DIR / "project_path.txt"
REPORT_PATH = BENCH_DIR / "benchmark_report.md"
SUMMARY_PATH = GENERATED_DIR / "benchmark_summary.json"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
ORCHESTRATOR = ROOT / "scripts" / "ctcp_orchestrate.py"
BENCHMARK_MAX_WALL_CLOCK_SECONDS = int(os.environ.get("CTCP_CONCRETE_BENCHMARK_MAX_SECONDS", "540"))
ADVANCE_TIMEOUT_SECONDS = int(os.environ.get("CTCP_CONCRETE_BENCHMARK_ADVANCE_TIMEOUT", "180"))
SERVER_STARTUP_TIMEOUT_SECONDS = int(os.environ.get("CTCP_CONCRETE_BENCHMARK_SERVER_STARTUP_TIMEOUT", "8"))
SERVER_SHUTDOWN_TIMEOUT_SECONDS = int(os.environ.get("CTCP_CONCRETE_BENCHMARK_SERVER_SHUTDOWN_TIMEOUT", "5"))
HTTP_REQUEST_TIMEOUT_SECONDS = int(os.environ.get("CTCP_CONCRETE_BENCHMARK_HTTP_TIMEOUT", "5"))

AGENT_MODE_MARKERS = {
    "agent-manifest",
    "agent-scaffold",
    "agent-project",
}

EXCLUDED_SCAN_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "artifacts",
    "logs",
    "outbox",
    "reviews",
    "snapshot",
    "audit",
}


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_reset_generated_dir() -> None:
    target = GENERATED_DIR.resolve()
    allowed = (BENCH_DIR / "generated").resolve()
    try:
        target.relative_to(allowed)
    except ValueError as exc:
        raise RuntimeError(f"unsafe generated directory: {target}") from exc
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def _run(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None, timeout: int = 180) -> dict[str, Any]:
    start = time.time()
    try:
        proc = subprocess.run(
            [str(part) for part in cmd],
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "cwd": str(cwd),
            "exit_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_seconds": round(time.time() - start, 3),
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "cmd": " ".join(str(part) for part in cmd),
            "cwd": str(cwd),
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "duration_seconds": round(time.time() - start, 3),
            "timed_out": True,
        }


def _project_env(project: Path, extra: dict[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    src = project / "src"
    existing = env.get("PYTHONPATH", "")
    parts = [str(src)] if src.exists() else []
    if existing:
        parts.append(existing)
    if parts:
        env["PYTHONPATH"] = os.pathsep.join(parts)
    env["PYTHONIOENCODING"] = "utf-8"
    if extra:
        env.update(extra)
    return env


def _tail(text: str, limit: int = 1000) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[-limit:]


def _step_status(*, timed_out: bool = False, passed: bool = False, failed: bool = False) -> str:
    if timed_out:
        return "timeout"
    if passed:
        return "passed"
    if failed:
        return "failed"
    return "completed"


def _record_step(
    summary: dict[str, Any],
    step: str,
    start: float,
    *,
    status: str = "completed",
    details: dict[str, Any] | None = None,
) -> None:
    row: dict[str, Any] = {
        "step": step,
        "duration_seconds": round(time.time() - start, 3),
        "status": status,
    }
    if details:
        row.update(details)
    summary.setdefault("step_timings", []).append(row)
    if status == "timeout" and not summary.get("timeout_step"):
        summary["timeout_step"] = step


def _remaining_seconds(started_at: float) -> int:
    return max(int(BENCHMARK_MAX_WALL_CLOCK_SECONDS - (time.time() - started_at)), 0)


def _command_status(result: dict[str, Any]) -> str:
    return _step_status(timed_out=bool(result.get("timed_out")), passed=int(result.get("exit_code", 1)) == 0, failed=int(result.get("exit_code", 1)) != 0)


def _scout_entrypoints() -> dict[str, Any]:
    help_result = _run([str(PYTHON), str(ORCHESTRATOR), "--help"], timeout=30)
    stdout = str(help_result.get("stdout", ""))
    ordinary = []
    excluded = []
    for name in ("new-run", "status", "advance", "scaffold", "scaffold-pointcloud"):
        if name in stdout:
            ordinary.append(name)
    for name in sorted(AGENT_MODE_MARKERS):
        if name in stdout:
            excluded.append(name)
    usable = all(name in ordinary for name in ("new-run", "advance", "status"))
    return {
        "help_command": help_result,
        "ordinary_entrypoints_found": ordinary,
        "agent_mode_entrypoints_excluded": excluded,
        "selected_entrypoint": "scripts/ctcp_orchestrate.py new-run + advance" if usable else "",
        "can_run_ordinary_project_generation": usable,
    }


def _goal_from_fixture() -> str:
    fixture = _read_json(FIXTURE)
    endpoints = ", ".join(str(item) for item in fixture["project_requirements"]["api"]["required_endpoints"])
    statuses = ", ".join(str(item) for item in fixture["project_requirements"]["issue_model"]["valid_statuses"])
    return (
        f"{fixture['goal']} Required endpoints: {endpoints}. "
        f"Use SQLite persistence. Valid issue statuses: {statuses}. "
        "Generate the concrete project files, tests, README, runnable local HTTP server, and delivery package."
    )


def _ordinary_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["CTCP_RUNS_ROOT"] = str((Path(tempfile.gettempdir()) / "ctcp_concrete_project_benchmark_runs").resolve())
    env["CTCP_ANALYSIS_PROFILE"] = "fast"
    env.pop("CTCP_FORCE_PROVIDER", None)
    env.pop("CTCP_ALLOW_LOCAL_MAINLINE_PROVIDER", None)
    return env


def _parse_run_dir(result: dict[str, Any]) -> Path | None:
    text = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    match = re.search(r"run_dir=([^\r\n]+)", text)
    if match:
        return Path(match.group(1).strip()).resolve()
    pointer = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
    if pointer.exists():
        raw = pointer.read_text(encoding="utf-8", errors="replace").strip()
        if raw:
            return Path(raw).resolve()
    return None


def _analysis_evidence(run_dir: Path | None, *, command_timed_out: bool = False) -> dict[str, Any]:
    if run_dir is None:
        return {}
    progress = analysis_stage_progress.load_progress(run_dir)
    raw_exists = analysis_stage_progress.raw_path(run_dir).exists()
    partial_exists = analysis_stage_progress.partial_path(run_dir).exists()
    target = analysis_stage_progress.ANALYSIS_TARGET_PATH
    status = str(progress.get("status", "")).strip().lower()
    return {
        "analysis_progress": progress,
        "analysis_timeout": command_timed_out or status == "timeout",
        "analysis_target": target,
        "analysis_prompt_path": str(progress.get("prompt_path", "")),
        "analysis_provider_model": str(progress.get("provider_model", "")),
        "analysis_provider": str(progress.get("provider", "")),
        "analysis_provider_timeout_seconds": progress.get("provider_timeout_seconds", ""),
        "analysis_profile": str(progress.get("analysis_profile", "")),
        "analysis_prompt_char_count": progress.get("prompt_char_count", 0),
        "analysis_prompt_estimated_tokens": progress.get("prompt_estimated_tokens", 0),
        "analysis_output_contract": str(progress.get("output_contract", "")),
        "analysis_max_output_tokens": progress.get("max_output_tokens", 0),
        "analysis_last_event": str(progress.get("last_event", "")),
        "analysis_error": progress.get("error"),
        "analysis_raw_exists": raw_exists,
        "analysis_raw_path": analysis_stage_progress.ANALYSIS_RAW_PATH if raw_exists else "",
        "analysis_partial_exists": partial_exists,
        "analysis_partial_path": analysis_stage_progress.ANALYSIS_PARTIAL_PATH if partial_exists else "",
        "analysis_resume_possible": raw_exists and not analysis_stage_progress.target_path(run_dir).exists(),
    }


def _merge_analysis_evidence(summary: dict[str, Any], run_dir: Path | None, *, command_timed_out: bool = False) -> None:
    evidence = _analysis_evidence(run_dir, command_timed_out=command_timed_out)
    if evidence:
        summary.update(evidence)


def _invoke_ordinary_generation(summary: dict[str, Any], benchmark_started_at: float) -> dict[str, Any]:
    run_id = f"concrete-issue-tracker-{int(time.time())}"
    goal = _goal_from_fixture()
    env = _ordinary_env()
    step_start = time.time()
    new_run = _run(
        [str(PYTHON), str(ORCHESTRATOR), "new-run", "--goal", goal, "--run-id", run_id],
        env=env,
        timeout=min(60, max(_remaining_seconds(benchmark_started_at), 1)),
    )
    _record_step(summary, "new_run", step_start, status=_command_status(new_run), details={"exit_code": new_run.get("exit_code")})
    commands = [new_run]
    run_dir = _parse_run_dir(new_run)
    if new_run["exit_code"] != 0 or run_dir is None:
        return {"run_dir": str(run_dir or ""), "commands": commands, "blocked": True, "block_reason": "new-run failed"}
    step_start = time.time()
    status_before = _run([str(PYTHON), str(ORCHESTRATOR), "status", "--run-dir", str(run_dir)], env=env, timeout=60)
    _record_step(summary, "status_before_generation", step_start, status=_command_status(status_before), details={"exit_code": status_before.get("exit_code")})
    commands.append(status_before)
    recovery: dict[str, Any] = {
        "intentional_source_generation_interrupt": False,
        "resume_attempted": False,
        "partial_project_output_seen": False,
        "completed_batch_count_after_interrupt": 0,
        "completed_batch_count_after_resume": 0,
    }
    last_status_text = str(status_before.get("stdout", "")).lower()
    source_generation_started_at = 0.0
    source_generation_status = "completed"
    for advance_index in range(16):
        if _remaining_seconds(benchmark_started_at) <= 5:
            summary["timeout_step"] = summary.get("timeout_step") or "source_generation"
            source_generation_status = "timeout"
            return {
                "run_dir": str(run_dir),
                "commands": commands,
                "blocked": True,
                "block_reason": "benchmark wall-clock guard reached during generation",
                "source_generation_recovery": recovery,
            }
        advance_env = env
        step_name = "advance_1" if advance_index == 0 else f"advance_{advance_index + 1}"
        if "source_generation" in last_status_text and not recovery["intentional_source_generation_interrupt"]:
            advance_env = dict(env)
            advance_env["CTCP_SOURCE_GENERATION_MAX_BATCHES_PER_RUN"] = "1"
            recovery["intentional_source_generation_interrupt"] = True
            step_name = "interrupted_advance"
            source_generation_started_at = source_generation_started_at or time.time()
        elif recovery["intentional_source_generation_interrupt"]:
            recovery["resume_attempted"] = True
            step_name = "resume_advance"
            source_generation_started_at = source_generation_started_at or time.time()
        step_start = time.time()
        advance = _run(
            [str(PYTHON), str(ORCHESTRATOR), "advance", "--run-dir", str(run_dir), "--max-steps", "1"],
            env=advance_env,
            timeout=min(ADVANCE_TIMEOUT_SECONDS, max(_remaining_seconds(benchmark_started_at), 1)),
        )
        _record_step(summary, step_name, step_start, status=_command_status(advance), details={"exit_code": advance.get("exit_code")})
        if "CTCP_SOURCE_GENERATION_MAX_BATCHES_PER_RUN" in advance_env:
            advance["intentional_source_generation_interrupt"] = True
        if advance.get("timed_out"):
            summary["timeout_step"] = summary.get("timeout_step") or ("source_generation" if source_generation_started_at else step_name)
            _merge_analysis_evidence(summary, run_dir, command_timed_out=True)
            source_generation_status = "timeout"
            commands.append(advance)
            break
        step_start = time.time()
        status_after = _run([str(PYTHON), str(ORCHESTRATOR), "status", "--run-dir", str(run_dir)], env=env, timeout=60)
        _record_step(summary, "status_after_advance", step_start, status=_command_status(status_after), details={"exit_code": status_after.get("exit_code")})
        _merge_analysis_evidence(summary, run_dir)
        commands.extend([advance, status_after])
        if (summary.get("analysis_timeout") or summary.get("analysis_error")) and not (run_dir / "artifacts" / "analysis.md").exists():
            break
        state_path = run_dir / "artifacts" / "source_generation_state.json"
        if state_path.exists():
            try:
                state = _read_json(state_path)
            except Exception:
                state = {}
            completed = len(state.get("completed_batches", [])) if isinstance(state.get("completed_batches", []), list) else 0
            if recovery["intentional_source_generation_interrupt"] and not recovery["completed_batch_count_after_interrupt"]:
                recovery["completed_batch_count_after_interrupt"] = completed
            recovery["completed_batch_count_after_resume"] = completed
        recovery["partial_project_output_seen"] = recovery["partial_project_output_seen"] or (run_dir / "project_output").exists()
        if _project_candidate_exists(run_dir) and (run_dir / "artifacts" / "source_generation_report.json").exists():
            source_generation_status = "passed"
            break
        status_text = str(status_after.get("stdout", "")).lower()
        last_status_text = status_text
        if "run_status=pass" in status_text or "run_status=fail" in status_text:
            break
    if source_generation_started_at:
        _record_step(
            summary,
            "source_generation",
            source_generation_started_at,
            status=source_generation_status,
            details={
                "completed_batches": recovery["completed_batch_count_after_resume"],
                "partial_project_output_seen": recovery["partial_project_output_seen"],
            },
        )
    return {"run_dir": str(run_dir), "commands": commands, "blocked": False, "block_reason": "", "source_generation_recovery": recovery}


def _is_agent_artifact_dir(path: Path) -> bool:
    manifest = path / "manifest.json"
    if manifest.exists():
        try:
            doc = _read_json(manifest)
        except Exception:
            doc = {}
        agent_manifest_fields = {"manifest_version", "agents", "tools", "workflows", "memory", "permissions", "guardrails", "test_cases"}
        if agent_manifest_fields.issubset(set(doc.keys())):
            return True
    scaffold_markers = {"agents", "tools", "workflows", "guardrails"}
    if all((path / marker).exists() for marker in scaffold_markers) and (path / "run_agent.py").exists():
        return True
    return False


def _project_score(path: Path) -> int:
    if _is_agent_artifact_dir(path):
        return -100
    score = 0
    if (path / "README.md").exists():
        score += 5
    if (path / "tests").exists() or list(path.glob("test_*.py")):
        score += 4
    py_files = [p for p in path.rglob("*.py") if "__pycache__" not in p.parts and "tests" not in p.parts]
    if py_files:
        score += 4
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace")[:2000].lower() for p in py_files[:20])
    for token in ("sqlite", "http", "issue", "/issues", "post", "patch"):
        if token in text:
            score += 1
    return score


def _candidate_roots_from_artifacts(run_dir: Path) -> list[Path]:
    out: list[Path] = []
    for rel in ("artifacts/project_manifest.json", "artifacts/source_generation_report.json", "artifacts/output_contract_freeze.json"):
        path = run_dir / rel
        if not path.exists():
            continue
        try:
            doc = _read_json(path)
        except Exception:
            continue
        for key in ("project_root", "output_project_root"):
            raw = str(doc.get(key, "")).strip()
            if raw:
                out.append((run_dir / raw).resolve())
        spec = doc.get("project_spec")
        if isinstance(spec, dict):
            raw = str(spec.get("project_root", "")).strip()
            if raw:
                out.append((run_dir / raw).resolve())
    return out


def _project_candidate_exists(run_dir: Path) -> bool:
    for path in _candidate_roots_from_artifacts(run_dir):
        if path.exists() and path.is_dir() and _project_score(path) > 0:
            return True
    project_output = run_dir / "project_output"
    if project_output.exists():
        for path in project_output.rglob("*"):
            if path.is_dir() and _project_score(path) > 0:
                return True
    return False


def _discover_generated_project(run_dir_text: str) -> dict[str, Any]:
    if not run_dir_text:
        return {"project_found": False, "project_root": "", "candidates": []}
    run_dir = Path(run_dir_text).resolve()
    candidates: list[Path] = []
    for path in _candidate_roots_from_artifacts(run_dir):
        if path.exists() and path.is_dir():
            candidates.append(path)
    for path in run_dir.rglob("*"):
        if not path.is_dir():
            continue
        if any(part in EXCLUDED_SCAN_DIRS for part in path.relative_to(run_dir).parts):
            continue
        if (path / "README.md").exists() or (path / "tests").exists():
            candidates.append(path)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path.resolve())
    scored = [{"path": str(path), "score": _project_score(path)} for path in unique]
    scored.sort(key=lambda row: int(row["score"]), reverse=True)
    if not scored or int(scored[0]["score"]) <= 0:
        return {"project_found": False, "project_root": "", "candidates": scored[:10]}
    source = Path(str(scored[0]["path"]))
    PROJECT_PATH_POINTER.write_text(str(source) + "\n", encoding="utf-8")
    return {
        "project_found": True,
        "project_root": str(source),
        "project_path_pointer": str(PROJECT_PATH_POINTER),
        "candidates": scored[:10],
    }


def _has_readme(project: Path) -> dict[str, Any]:
    return {"passed": (project / "README.md").exists(), "path": str(project / "README.md")}


def _source_files(project: Path) -> list[str]:
    files = []
    for path in project.rglob("*.py"):
        rel_parts = path.relative_to(project).parts
        if "__pycache__" in rel_parts or rel_parts[0] == "tests" or path.name.startswith("test_"):
            continue
        files.append(path.relative_to(project).as_posix())
    return files


def _test_files(project: Path) -> list[str]:
    return [
        path.relative_to(project).as_posix()
        for path in project.rglob("test*.py")
        if "__pycache__" not in path.parts
    ]


def _run_generated_project_tests(project: Path) -> dict[str, Any]:
    tests = _test_files(project)
    if not tests:
        return {"passed": False, "commands": [], "reason": "no generated test files found"}
    commands = []
    if (project / "tests").exists():
        cmd = [str(PYTHON), "-m", "unittest", "discover", "-s", "tests", "-v"]
        result = _run(cmd, cwd=project, env=_project_env(project), timeout=180)
        commands.append(result)
        if result["exit_code"] == 0:
            return {"passed": True, "commands": commands, "reason": "unittest passed"}
    pytest_check = _run([str(PYTHON), "-c", "import pytest"], cwd=project, env=_project_env(project), timeout=20)
    if pytest_check["exit_code"] == 0:
        result = _run([str(PYTHON), "-m", "pytest", "-q"], cwd=project, env=_project_env(project), timeout=180)
        commands.append(result)
        if result["exit_code"] == 0:
            return {"passed": True, "commands": commands, "reason": "pytest passed"}
    return {"passed": False, "commands": commands, "reason": "generated tests failed"}


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(method: str, url: str, payload: dict[str, Any] | None = None, timeout: int = HTTP_REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            parsed: Any
            try:
                parsed = json.loads(raw) if raw.strip() else None
            except Exception:
                parsed = raw
            return {"ok": 200 <= response.status < 300, "status": response.status, "body": parsed}
    except urllib.error.HTTPError as exc:
        try:
            raw = exc.read().decode("utf-8", errors="replace")
        except Exception as read_exc:
            raw = f"{exc}; body read failed: {read_exc}"
        return {"ok": False, "status": exc.code, "body": raw}
    except Exception as exc:
        return {"ok": False, "status": 0, "body": str(exc)}


def _run_dir_for_project(project: Path, run_dir_text: str = "") -> Path | None:
    if run_dir_text:
        candidate = Path(run_dir_text).resolve()
        if candidate.exists():
            return candidate
    for parent in [project.resolve(), *project.resolve().parents]:
        if (parent / "artifacts").exists() and (parent / "RUN.json").exists():
            return parent
    return None


def _record_convergence_timings(summary: dict[str, Any], reconciliation: dict[str, Any]) -> None:
    for row in reconciliation.get("pass_timings", []):
        if not isinstance(row, dict):
            continue
        pass_id = row.get("pass", 0)
        for key, step in (
            ("extraction_seconds", "convergence_extraction"),
            ("validation_seconds", "convergence_validation"),
            ("repair_seconds", "convergence_repair"),
        ):
            summary.setdefault("step_timings", []).append(
                {
                    "step": step,
                    "duration_seconds": float(row.get(key, 0.0) or 0.0),
                    "status": "passed",
                    "pass": pass_id,
                    "drift_count": row.get("drift_count", 0),
                    "graph_hash": row.get("graph_hash", ""),
                    "changed_files": row.get("changed_files", []),
                }
            )


def _ensure_contract_artifacts(project: Path, run_dir: Path | None, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    if run_dir is None:
        return {}
    try:
        rel_root = project.resolve().relative_to(run_dir.resolve()).as_posix()
    except Exception:
        rel_root = ""
    try:
        reconciliation = write_generation_contract_artifacts(run_dir, project_root=rel_root, repair=True)
        if summary is not None:
            _record_convergence_timings(summary, reconciliation)
    except Exception:
        pass
    return {
        "graph": _read_json(run_dir / "artifacts" / "contract_graph.json") if (run_dir / "artifacts" / "contract_graph.json").exists() else {},
        "symbols": _read_json(run_dir / "artifacts" / "generated_symbols.json") if (run_dir / "artifacts" / "generated_symbols.json").exists() else {},
        "routes": _read_json(run_dir / "artifacts" / "generated_routes.json") if (run_dir / "artifacts" / "generated_routes.json").exists() else {},
        "runtime": _read_json(run_dir / "artifacts" / "runtime_contract.json") if (run_dir / "artifacts" / "runtime_contract.json").exists() else {},
        "reconciliation": _read_json(run_dir / "artifacts" / "reconciliation_report.json") if (run_dir / "artifacts" / "reconciliation_report.json").exists() else {},
    }


def _route_key(method: str, path: str) -> str:
    return f"{str(method).upper()} {str(path).strip()}"


def _registry_route_keys(routes_doc: dict[str, Any]) -> set[str]:
    routes = routes_doc.get("routes") if isinstance(routes_doc.get("routes"), list) else []
    return {
        _route_key(str(row.get("method", "")), str(row.get("path", "")))
        for row in routes
        if isinstance(row, dict) and str(row.get("method", "")).strip() and str(row.get("path", "")).strip()
    }


def _required_fixture_route_keys() -> set[str]:
    fixture = _read_json(FIXTURE)
    endpoints = fixture.get("project_requirements", {}).get("api", {}).get("required_endpoints", [])
    return {str(item).strip() for item in endpoints if str(item).strip()}


def _route_url(base_url: str, route_path: str, issue_id: str = "") -> str:
    path = route_path
    if "{id}" in path:
        path = path.replace("{id}", issue_id)
    return base_url + path


def _liveness_path(routes_doc: dict[str, Any]) -> str:
    route_keys = _registry_route_keys(routes_doc)
    get_paths = [
        key.split(" ", 1)[1]
        for key in sorted(route_keys)
        if key.startswith("GET ") and "{" not in key
    ]
    if "/status" in get_paths:
        return "/status"
    for path in get_paths:
        if path != "/":
            return path
    return get_paths[0] if get_paths else ""


def _server_candidates(project: Path, runtime_contract: dict[str, Any], port: int) -> tuple[list[list[str]], int, str]:
    candidates: list[list[str]] = []
    supported_args = set(str(item) for item in runtime_contract.get("supported_cli_args", []) if str(item))
    contract_port = int(runtime_contract.get("default_port", 0) or 0)
    selected_port = port if "--port" in supported_args else (contract_port or port)
    host = str(runtime_contract.get("default_host", "127.0.0.1") or "127.0.0.1")
    entrypoint = str(runtime_contract.get("entrypoint", "")).strip().replace("\\", "/")
    if entrypoint:
        entry_path = (project / entrypoint).resolve()
        if entry_path.exists():
            args = [str(PYTHON), str(entry_path)]
            if "--serve" in supported_args:
                args.append("--serve")
            if "--host" in supported_args:
                args.extend(["--host", host])
            if "--port" in supported_args:
                args.extend(["--port", str(selected_port)])
            candidates.append(args)
    direct = [
        project / "scripts" / "run_project_cli.py",
        project / "scripts" / "run_project_web.py",
        project / "run_project_cli.py",
        project / "run_project_web.py",
        project / "app.py",
        project / "main.py",
        project / "server.py",
    ]
    for path in direct:
        if path.exists():
            args = [str(PYTHON), str(path)]
            if path.name in {"run_project_cli.py", "run_project_web.py"}:
                args.extend(["--serve"])
            candidates.append(args)
    for path in project.glob("src/*/app.py"):
        candidates.append([str(PYTHON), str(path)])
    for path in project.glob("src/*/main.py"):
        candidates.append([str(PYTHON), str(path)])
    unique: list[list[str]] = []
    seen: set[str] = set()
    for cmd in candidates:
        key = "\0".join(cmd)
        if key not in seen:
            seen.add(key)
            unique.append(cmd)
    return unique, selected_port, host


def _wait_for_registered_endpoint(host: str, port: int, path: str, seconds: int = SERVER_STARTUP_TIMEOUT_SECONDS) -> bool:
    if not path:
        return False
    deadline = time.time() + seconds
    url = f"http://{host}:{port}{path}"
    while time.time() < deadline:
        probe = _http_json("GET", url, timeout=min(2, HTTP_REQUEST_TIMEOUT_SECONDS))
        if probe["status"] not in {0, 404, 405}:
            return True
        time.sleep(0.4)
    return False


def _extract_issue_id(body: Any) -> str:
    if isinstance(body, dict):
        for key in ("id", "issue_id"):
            if key in body:
                return str(body[key])
        issue = body.get("issue")
        if isinstance(issue, dict):
            return _extract_issue_id(issue)
    if isinstance(body, list) and body:
        return _extract_issue_id(body[0])
    return ""


def _probe_http_api(
    project: Path,
    run_dir_text: str = "",
    summary: dict[str, Any] | None = None,
    contracts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    run_dir = _run_dir_for_project(project, run_dir_text)
    contracts = contracts if isinstance(contracts, dict) else _ensure_contract_artifacts(project, run_dir, summary)
    routes_doc = contracts.get("routes", {}) if isinstance(contracts.get("routes", {}), dict) else {}
    runtime_contract = contracts.get("runtime", {}) if isinstance(contracts.get("runtime", {}), dict) else {}
    route_keys = _registry_route_keys(routes_doc)
    required_route_keys = _required_fixture_route_keys()
    missing_required = sorted(required_route_keys - route_keys)
    if missing_required:
        return {
            "passed": False,
            "server_started": False,
            "candidates": [],
            "endpoint_results": {},
            "route_registry": sorted(route_keys),
            "missing_required_routes": missing_required,
            "reason": "required fixture routes are absent from generated_routes.json",
        }
    requested_port = _free_port()
    candidates, port, host = _server_candidates(project, runtime_contract, requested_port)
    env = _project_env(project, {"PORT": str(port), "HOST": host})
    if not candidates:
        return {"passed": False, "server_started": False, "candidates": [], "endpoint_results": {}, "reason": "no server command candidate found"}

    attempts: list[dict[str, Any]] = []
    live_path = _liveness_path(routes_doc)
    base_url = f"http://{host}:{port}"
    for cmd in candidates:
        proc = subprocess.Popen(
            cmd,
            cwd=str(project),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            startup_start = time.time()
            started = _wait_for_registered_endpoint(host, port, live_path, seconds=SERVER_STARTUP_TIMEOUT_SECONDS)
            if summary is not None:
                _record_step(
                    summary,
                    "runtime_startup",
                    startup_start,
                    status="passed" if started else "failed",
                    details={"cmd": " ".join(cmd), "timeout_seconds": SERVER_STARTUP_TIMEOUT_SECONDS},
                )
            if not started and proc.poll() is not None:
                out, err = proc.communicate(timeout=3)
                attempts.append({"cmd": " ".join(cmd), "started": False, "exit_code": proc.returncode, "stdout": _tail(out), "stderr": _tail(err)})
                continue
            if not started:
                attempts.append(
                    {
                        "cmd": " ".join(cmd),
                        "started": False,
                        "exit_code": "still_running_after_startup_timeout",
                        "stdout": "",
                        "stderr": "",
                        "startup_timeout_seconds": SERVER_STARTUP_TIMEOUT_SECONDS,
                    }
                )
                continue
            if started:
                probe_start = time.time()
                results: dict[str, Any] = {}
                create_key = _route_key("POST", "/issues")
                create = _http_json("POST", _route_url(base_url, "/issues"), {"title": "First issue", "description": "Created by concrete benchmark"}, timeout=HTTP_REQUEST_TIMEOUT_SECONDS)
                issue_id = _extract_issue_id(create["body"])
                results[create_key] = create
                for key in sorted(required_route_keys):
                    if key == create_key:
                        continue
                    method, route_path = key.split(" ", 1)
                    if "{id}" in route_path and not issue_id:
                        results[key] = {"ok": False, "status": 0, "body": "POST /issues did not return an issue id"}
                        continue
                    payload = {"status": "in_progress"} if method == "PATCH" and route_path.endswith("/status") else None
                    results[key] = _http_json(method, _route_url(base_url, route_path, issue_id), payload, timeout=HTTP_REQUEST_TIMEOUT_SECONDS)
                passed = all(bool(row.get("ok", False)) for row in results.values())
                if summary is not None:
                    _record_step(
                        summary,
                        "HTTP probe",
                        probe_start,
                        status="passed" if passed else "failed",
                        details={"request_timeout_seconds": HTTP_REQUEST_TIMEOUT_SECONDS, "endpoint_count": len(results)},
                    )
                return {
                    "passed": passed,
                    "server_started": True,
                    "server_command": " ".join(cmd),
                    "port": port,
                    "runtime_contract": runtime_contract,
                    "route_registry": sorted(route_keys),
                    "endpoint_results": results,
                    "reason": "all endpoint probes passed" if passed else "one or more endpoint probes failed",
                }
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=SERVER_SHUTDOWN_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=SERVER_SHUTDOWN_TIMEOUT_SECONDS)
            try:
                proc.communicate(timeout=1)
            except Exception:
                pass
    return {
        "passed": False,
        "server_started": False,
        "candidates": attempts,
        "endpoint_results": {},
        "runtime_contract": runtime_contract,
        "route_registry": sorted(route_keys),
        "reason": "no candidate stayed up with a registered route endpoint",
    }


def _sqlite_verification(project: Path) -> dict[str, Any]:
    code_hits = []
    for path in project.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".py", ".toml", ".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if "sqlite" in text or ".db" in text or ".sqlite" in text:
            code_hits.append(path.relative_to(project).as_posix())
    db_files = [
        path.relative_to(project).as_posix()
        for path in project.rglob("*")
        if path.is_file() and path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}
    ]
    return {
        "passed": bool(code_hits or db_files),
        "sqlite_usage_detected": bool(code_hits),
        "database_file_created": bool(db_files),
        "code_hits": sorted(set(code_hits)),
        "database_files": sorted(set(db_files)),
    }


def _runtime_blocked(summary: dict[str, Any]) -> bool:
    joined = "\n".join(
        f"{cmd.get('stdout', '')}\n{cmd.get('stderr', '')}"
        for cmd in summary.get("generation", {}).get("commands", [])
    ).lower()
    run_dir_text = str(summary.get("generation", {}).get("run_dir", ""))
    outbox_exists = bool(run_dir_text and list((Path(run_dir_text) / "outbox").glob("*.md")))
    provider_markers = (
        "openai_api_key",
        "missing env: openai_api_key",
        "provider",
        "api_agent",
        "outbox prompt",
        "waiting for analysis.md",
    )
    return outbox_exists or any(marker in joined for marker in provider_markers)


def _validate_project(project_copy: str, run_dir_text: str = "", summary: dict[str, Any] | None = None) -> dict[str, Any]:
    project = Path(project_copy)
    run_dir = _run_dir_for_project(project, run_dir_text)
    contracts = _ensure_contract_artifacts(project, run_dir, summary)
    checks: dict[str, Any] = {}
    checks["not_agent_artifact"] = {"passed": not _is_agent_artifact_dir(project)}
    checks["readme"] = _has_readme(project)
    checks["source"] = {"passed": bool(_source_files(project)), "files": _source_files(project)}
    checks["tests"] = {"passed": bool(_test_files(project)), "files": _test_files(project)}
    step_start = time.time()
    checks["project_tests"] = _run_generated_project_tests(project)
    if summary is not None:
        _record_step(summary, "generated_project_tests", step_start, status="passed" if checks["project_tests"].get("passed") else "failed", details={"reason": checks["project_tests"].get("reason", "")})
    step_start = time.time()
    checks["http_api"] = _probe_http_api(project, run_dir_text, summary, contracts)
    if summary is not None and not any(row.get("step") == "HTTP probe" for row in summary.get("step_timings", [])):
        _record_step(summary, "HTTP probe", step_start, status="passed" if checks["http_api"].get("passed") else "failed", details={"reason": checks["http_api"].get("reason", "")})
    step_start = time.time()
    checks["sqlite"] = _sqlite_verification(project)
    if summary is not None:
        _record_step(summary, "SQLite validation", step_start, status="passed" if checks["sqlite"].get("passed") else "failed")
    checks["shared_contracts"] = {
        "passed": bool(contracts.get("graph")) and bool(contracts.get("symbols")) and bool(contracts.get("routes")) and bool(contracts.get("runtime")),
        "graph_path": str((run_dir / "artifacts" / "contract_graph.json") if run_dir else ""),
        "graph_hash": str(dict(contracts.get("graph", {})).get("graph_hash", "")),
        "symbols_path": str((run_dir / "artifacts" / "generated_symbols.json") if run_dir else ""),
        "routes_path": str((run_dir / "artifacts" / "generated_routes.json") if run_dir else ""),
        "runtime_contract_path": str((run_dir / "artifacts" / "runtime_contract.json") if run_dir else ""),
        "reconciliation_path": str((run_dir / "artifacts" / "reconciliation_report.json") if run_dir else ""),
        "reconciliation_status": str(dict(contracts.get("reconciliation", {})).get("status", "")),
        "converged": bool(dict(contracts.get("reconciliation", {})).get("converged", False)),
        "typed_issue_count": len(dict(contracts.get("reconciliation", {})).get("typed_issues", [])),
        "provider_call_count": int(dict(contracts.get("reconciliation", {})).get("provider_call_count", 0) or 0),
        "stopped_reason": str(dict(contracts.get("reconciliation", {})).get("stopped_reason", "")),
        "max_passes": dict(contracts.get("reconciliation", {})).get("max_passes", ""),
        "max_wall_clock_seconds": dict(contracts.get("reconciliation", {})).get("max_wall_clock_seconds", ""),
        "cache_hits": dict(dict(contracts.get("reconciliation", {})).get("cache", {})).get("cache_hits", ""),
        "cache_misses": dict(dict(contracts.get("reconciliation", {})).get("cache", {})).get("cache_misses", ""),
    }
    passed = all(bool(item.get("passed", False)) for item in checks.values())
    return {"passed": passed, "checks": checks}


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# Concrete Project Generation Benchmark Report",
        "",
        "## Summary",
        f"- concrete benchmark status: `{summary['status']}`",
        f"- fixture: `{_rel(FIXTURE)}`",
        f"- generated project path: `{summary.get('generated_project_path', '') or '(none)'}`",
        f"- run_dir: `{summary.get('generation', {}).get('run_dir', '') or '(none)'}`",
        f"- elapsed_seconds: `{summary.get('elapsed_seconds', 0)}`",
        f"- timeout_step: `{summary.get('timeout_step', '') or '(none)'}`",
        "",
        "## Entrypoint Discovery",
        f"- selected ordinary entrypoint: `{summary['entrypoint_discovery'].get('selected_entrypoint', '') or '(none)'}`",
        f"- ordinary entrypoints found: `{', '.join(summary['entrypoint_discovery'].get('ordinary_entrypoints_found', []))}`",
        f"- excluded agent modes found: `{', '.join(summary['entrypoint_discovery'].get('agent_mode_entrypoints_excluded', []))}`",
        "",
        "## Commands Executed",
    ]
    for command in summary.get("generation", {}).get("commands", []):
        lines.extend(
            [
                f"- command: `{command.get('cmd', '')}`",
                f"  - exit_code: `{command.get('exit_code')}`",
                f"  - stdout_tail: `{_tail(str(command.get('stdout', '')), 300)}`",
                f"  - stderr_tail: `{_tail(str(command.get('stderr', '')), 300)}`",
            ]
        )
    if not summary.get("generation", {}).get("commands"):
        lines.append("- (none)")
    lines.extend(["", "## Step Timings"])
    for row in summary.get("step_timings", []):
        lines.append(
            f"- {row.get('step', '')}: `{row.get('status', '')}` duration=`{row.get('duration_seconds', 0)}`"
        )
        if row.get("drift_count", "") != "":
            lines.append(f"  - drift_count: `{row.get('drift_count')}`")
        if row.get("changed_files"):
            lines.append(f"  - changed_files: `{', '.join(row.get('changed_files', []))}`")
        if row.get("graph_hash"):
            lines.append(f"  - graph_hash: `{row.get('graph_hash')}`")
    if not summary.get("step_timings"):
        lines.append("- (none)")
    analysis = summary.get("analysis_progress", {}) if isinstance(summary.get("analysis_progress", {}), dict) else {}
    lines.extend(
        [
            "",
            "## Analysis Progress",
            f"- target: `{summary.get('analysis_target', 'artifacts/analysis.md')}`",
            f"- status: `{analysis.get('status', '') or '(none)'}`",
            f"- last_event: `{summary.get('analysis_last_event', '') or analysis.get('last_event', '') or '(none)'}`",
            f"- timeout: `{summary.get('analysis_timeout', False)}`",
            f"- error: `{summary.get('analysis_error', '') or analysis.get('error', '') or '(none)'}`",
            f"- prompt_path: `{summary.get('analysis_prompt_path', '') or analysis.get('prompt_path', '') or '(none)'}`",
            f"- provider: `{summary.get('analysis_provider', '') or analysis.get('provider', '') or '(none)'}`",
            f"- provider_model: `{summary.get('analysis_provider_model', '') or analysis.get('provider_model', '') or '(none)'}`",
            f"- provider_timeout_seconds: `{summary.get('analysis_provider_timeout_seconds', '') or analysis.get('provider_timeout_seconds', '') or '(none)'}`",
            f"- analysis_profile: `{summary.get('analysis_profile', '') or analysis.get('analysis_profile', '') or '(none)'}`",
            f"- prompt_char_count: `{summary.get('analysis_prompt_char_count', '') or analysis.get('prompt_char_count', '') or 0}`",
            f"- prompt_estimated_tokens: `{summary.get('analysis_prompt_estimated_tokens', '') or analysis.get('prompt_estimated_tokens', '') or 0}`",
            f"- max_output_tokens: `{summary.get('analysis_max_output_tokens', '') or analysis.get('max_output_tokens', '') or 0}`",
            f"- output_contract: `{_tail(summary.get('analysis_output_contract', '') or analysis.get('output_contract', ''), 500) or '(none)'}`",
            f"- raw_exists: `{summary.get('analysis_raw_exists', False)}` path=`{summary.get('analysis_raw_path', '') or '(none)'}`",
            f"- partial_exists: `{summary.get('analysis_partial_exists', False)}` path=`{summary.get('analysis_partial_path', '') or '(none)'}`",
            f"- resume_possible: `{summary.get('analysis_resume_possible', False)}`",
        ]
    )
    recovery = summary.get("generation", {}).get("source_generation_recovery", {})
    lines.extend(
        [
            "",
            "## Source Generation Recovery",
            f"- intentional interrupt: `{recovery.get('intentional_source_generation_interrupt', False)}`",
            f"- resume attempted: `{recovery.get('resume_attempted', False)}`",
            f"- partial project_output seen: `{recovery.get('partial_project_output_seen', False)}`",
            f"- completed batches after interrupt: `{recovery.get('completed_batch_count_after_interrupt', 0)}`",
            f"- completed batches after resume: `{recovery.get('completed_batch_count_after_resume', 0)}`",
        ]
    )
    lines.extend(["", "## Generated Project Discovery"])
    discovery = summary.get("project_discovery", {})
    lines.append(f"- project_found: `{discovery.get('project_found', False)}`")
    lines.append(f"- source_project_root: `{discovery.get('project_root', '')}`")
    lines.append(f"- project_path_pointer: `{discovery.get('project_path_pointer', '')}`")
    lines.append("- candidates:")
    for row in discovery.get("candidates", [])[:10]:
        lines.append(f"  - `{row.get('path', '')}` score=`{row.get('score', '')}`")
    if not discovery.get("candidates"):
        lines.append("  - (none)")
    lines.extend(["", "## Validation Results"])
    validation = summary.get("validation", {})
    for name, result in validation.get("checks", {}).items():
        lines.append(f"- {name}: `{'passed' if result.get('passed') else 'failed'}`")
        if name == "http_api":
            lines.append(f"  - route registry: `{', '.join(result.get('route_registry', []))}`")
            runtime_contract = result.get("runtime_contract", {}) if isinstance(result.get("runtime_contract", {}), dict) else {}
            lines.append(f"  - runtime entrypoint: `{runtime_contract.get('entrypoint', '')}`")
            lines.append(f"  - runtime supported CLI args: `{', '.join(runtime_contract.get('supported_cli_args', []))}`")
            for endpoint, endpoint_result in result.get("endpoint_results", {}).items():
                lines.append(f"  - {endpoint}: `{'passed' if endpoint_result.get('ok') else 'failed'}` status=`{endpoint_result.get('status')}`")
            for missing in result.get("missing_required_routes", []):
                lines.append(f"  - missing_required_route: `{missing}`")
            if result.get("candidates"):
                lines.append("  - server_start_attempts:")
                for attempt in result.get("candidates", [])[:3]:
                    lines.append(f"    - cmd: `{attempt.get('cmd', '')}`")
                    lines.append(f"      exit_code: `{attempt.get('exit_code', '')}`")
                    lines.append(f"      stderr_tail: `{_tail(str(attempt.get('stderr', '')), 300)}`")
        if name == "sqlite":
            lines.append(f"  - sqlite3 usage detected: `{result.get('sqlite_usage_detected')}`")
            lines.append(f"  - database file created: `{result.get('database_file_created')}`")
        if name == "shared_contracts":
            lines.append(f"  - contract_graph: `{result.get('graph_path', '')}`")
            lines.append(f"  - graph_hash: `{result.get('graph_hash', '')}`")
            lines.append(f"  - generated_symbols: `{result.get('symbols_path', '')}`")
            lines.append(f"  - generated_routes: `{result.get('routes_path', '')}`")
            lines.append(f"  - runtime_contract: `{result.get('runtime_contract_path', '')}`")
            lines.append(f"  - reconciliation_report: `{result.get('reconciliation_path', '')}`")
            lines.append(f"  - reconciliation_status: `{result.get('reconciliation_status', '')}`")
            lines.append(f"  - converged: `{result.get('converged', False)}`")
            lines.append(f"  - typed_issue_count: `{result.get('typed_issue_count', 0)}`")
            lines.append(f"  - provider_call_count: `{result.get('provider_call_count', 0)}`")
            lines.append(f"  - stopped_reason: `{result.get('stopped_reason', '')}`")
            lines.append(f"  - max_passes: `{result.get('max_passes', '')}`")
            lines.append(f"  - max_wall_clock_seconds: `{result.get('max_wall_clock_seconds', '')}`")
            lines.append(f"  - cache_hits: `{result.get('cache_hits', '')}`")
            lines.append(f"  - cache_misses: `{result.get('cache_misses', '')}`")
        if name == "project_tests":
            lines.append(f"  - reason: `{result.get('reason', '')}`")
            for command in result.get("commands", [])[:2]:
                lines.append(f"  - test_command: `{command.get('cmd', '')}`")
                lines.append(f"    - exit_code: `{command.get('exit_code', '')}`")
                lines.append(f"    - stderr_tail: `{_tail(str(command.get('stderr', '')), 300)}`")
    lines.extend(["", "## Failed Assertions"])
    for item in summary.get("failed_assertions", []):
        lines.append(f"- {item}")
    if not summary.get("failed_assertions"):
        lines.append("- (none)")
    lines.extend(["", "## Unsupported Reasons"])
    for item in summary.get("unsupported_reasons", []):
        lines.append(f"- {item}")
    if not summary.get("unsupported_reasons"):
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## Reproduction",
            f"- `{PYTHON} {_rel(Path('tests/concrete_project_benchmark/run_concrete_project_benchmark.py'))}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    benchmark_started_at = time.time()
    _safe_reset_generated_dir()
    summary: dict[str, Any] = {
        "benchmark": "concrete_project_generation_issue_tracker_api",
        "status": "unsupported",
        "max_wall_clock_seconds": BENCHMARK_MAX_WALL_CLOCK_SECONDS,
        "timeout_step": "",
        "step_timings": [],
        "entrypoint_discovery": {},
        "generation": {},
        "project_discovery": {},
        "validation": {},
        "failed_assertions": [],
        "unsupported_reasons": [],
    }
    step_start = time.time()
    discovery = _scout_entrypoints()
    _record_step(summary, "discovery", step_start, status="passed" if discovery.get("can_run_ordinary_project_generation") else "failed")
    summary["entrypoint_discovery"] = discovery
    if not discovery["can_run_ordinary_project_generation"]:
        summary["unsupported_reasons"].append("ordinary new-run/status/advance entrypoint set not found")
        step_start = time.time()
        _write_json(SUMMARY_PATH, summary)
        REPORT_PATH.write_text(_markdown(summary), encoding="utf-8")
        _record_step(summary, "report_write", step_start, status="passed")
        _write_json(SUMMARY_PATH, summary)
        print(json.dumps({"status": summary["status"], "report": _rel(REPORT_PATH)}, indent=2))
        return 0

    generation = _invoke_ordinary_generation(summary, benchmark_started_at)
    summary["generation"] = generation
    step_start = time.time()
    project_discovery = _discover_generated_project(str(generation.get("run_dir", "")))
    _record_step(summary, "generated_project_discovery", step_start, status="passed" if project_discovery.get("project_found") else "failed")
    summary["project_discovery"] = project_discovery

    if not project_discovery.get("project_found"):
        if summary.get("analysis_timeout") or summary.get("analysis_error"):
            summary["status"] = "failed"
            reason = summary.get("analysis_error") or summary.get("analysis_last_event") or "analysis stage failed"
            summary["failed_assertions"].append(f"analysis stage failed before source_generation: {reason}")
        elif summary.get("timeout_step"):
            summary["status"] = "failed"
            summary["failed_assertions"].append(f"benchmark timed out during {summary['timeout_step']}")
        elif _runtime_blocked(summary):
            summary["status"] = "unsupported"
            summary["unsupported_reasons"].append("ordinary project generation runtime blocked before a concrete project was produced")
        elif not summary.get("failed_assertions"):
            summary["status"] = "failed"
            summary["failed_assertions"].append("ordinary project generation did not produce a discoverable concrete project")
    else:
        generated_project = str(project_discovery.get("project_root", ""))
        summary["generated_project_path"] = generated_project
        validation = _validate_project(generated_project, str(generation.get("run_dir", "")), summary)
        summary["validation"] = validation
        if validation.get("passed"):
            summary["status"] = "passed"
        else:
            summary["status"] = "failed"
            for name, result in validation.get("checks", {}).items():
                if not result.get("passed", False):
                    summary["failed_assertions"].append(f"{name} check failed")

    summary["elapsed_seconds"] = round(time.time() - benchmark_started_at, 3)
    step_start = time.time()
    _write_json(SUMMARY_PATH, summary)
    REPORT_PATH.write_text(_markdown(summary), encoding="utf-8")
    _record_step(summary, "report_write", step_start, status="passed")
    summary["elapsed_seconds"] = round(time.time() - benchmark_started_at, 3)
    _write_json(SUMMARY_PATH, summary)
    REPORT_PATH.write_text(_markdown(summary), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary["status"],
                "generated_project_path": summary.get("generated_project_path", ""),
                "report": _rel(REPORT_PATH),
                "summary": _rel(SUMMARY_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if summary["status"] in {"passed", "failed", "unsupported"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
