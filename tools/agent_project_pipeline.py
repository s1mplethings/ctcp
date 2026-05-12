from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.agent_manifest_consumer import generate_agent_scaffold, validate_manifest
from tools.agent_manifest_generator import generate_manifest_from_file, write_manifest


REPO_ROOT = Path(__file__).resolve().parents[1]
SENTINEL = ".ctcp_agent_project.json"


class AgentProjectPipelineError(ValueError):
    pass


def _write_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _is_dangerous_output_dir(path: Path) -> bool:
    resolved = path.resolve()
    roots = {Path(resolved.anchor).resolve(), Path.home().resolve(), REPO_ROOT.resolve()}
    if resolved in roots:
        return True
    if resolved == REPO_ROOT.parent.resolve():
        return True
    if len(resolved.parts) <= 1:
        return True
    return False


def _clear_directory_contents(path: Path) -> None:
    if _is_dangerous_output_dir(path):
        raise AgentProjectPipelineError(f"refusing to clear dangerous output directory: {path}")
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _prepare_output_dir(output_dir: Path, force: bool) -> Path:
    target = output_dir.expanduser().resolve()
    if _is_dangerous_output_dir(target):
        raise AgentProjectPipelineError(f"refusing dangerous output directory: {target}")
    if target.exists() and any(target.iterdir()):
        if not force:
            raise AgentProjectPipelineError(f"output directory is not empty; pass --force to replace it: {target}")
        _clear_directory_contents(target)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _run(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return path.resolve().as_posix()


def _report_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Agent Project Pipeline Report",
        "",
        f"- status: {report.get('status')}",
        f"- input_path: `{report.get('input_path', '')}`",
        f"- manifest_path: `{report.get('manifest_path', '')}`",
        f"- scaffold_dir: `{report.get('scaffold_dir', '')}`",
        f"- force: {str(report.get('force', False)).lower()}",
        "",
        "## Steps",
        "",
        "| Step | Status | Output |",
        "|---|---|---|",
    ]
    for step in report.get("steps", []):
        lines.append(f"| {step.get('name')} | {step.get('status')} | `{step.get('output', '')}` |")
    if report.get("status") == "failed":
        lines += ["", "## Failure", "", f"- failed_step: {report.get('failed_step')}", f"- error: {report.get('error')}"]
    return "\n".join(lines) + "\n"


def _write_reports(output_dir: Path, report: dict[str, Any]) -> None:
    _write_json(output_dir / "pipeline_report.json", report)
    _write_text(output_dir / "pipeline_report.md", _report_markdown(report))


def _failed_report(
    *,
    output_dir: Path,
    input_path: Path,
    manifest_path: Path,
    scaffold_dir: Path,
    force: bool,
    steps: list[dict[str, Any]],
    failed_step: str,
    error: str,
) -> dict[str, Any]:
    report = {
        "status": "failed",
        "input_path": input_path.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "scaffold_dir": scaffold_dir.as_posix(),
        "force": force,
        "steps": steps,
        "failed_step": failed_step,
        "error": error,
        "failed_assertions": [error],
        "warnings": [],
    }
    _write_reports(output_dir, report)
    return report


def run_agent_project_pipeline(input_path: Path, output_dir: Path, *, force: bool = False) -> dict[str, Any]:
    source_input = input_path.expanduser().resolve()
    if not source_input.exists() or not source_input.is_file():
        raise AgentProjectPipelineError(f"input file not found: {source_input}")
    target = _prepare_output_dir(output_dir, force=force)
    manifest_path = target / "manifest.json"
    scaffold_dir = target / "scaffold"
    steps: list[dict[str, Any]] = []
    _write_text(target / "input.json", source_input.read_text(encoding="utf-8"))
    _write_json(target / SENTINEL, {"schema_version": "ctcp-agent-project-pipeline-v1", "force": force})

    try:
        manifest = generate_manifest_from_file(source_input)
        write_manifest(manifest_path, manifest)
        steps.append({"name": "manifest_generation", "status": "passed", "output": "manifest.json"})
    except Exception as exc:
        steps.append({"name": "manifest_generation", "status": "failed", "output": "manifest.json"})
        return _failed_report(
            output_dir=target,
            input_path=source_input,
            manifest_path=manifest_path,
            scaffold_dir=scaffold_dir,
            force=force,
            steps=steps,
            failed_step="manifest_generation",
            error=str(exc),
        )

    try:
        validate_manifest(manifest)
        steps.append({"name": "manifest_validation", "status": "passed"})
    except Exception as exc:
        steps.append({"name": "manifest_validation", "status": "failed"})
        return _failed_report(
            output_dir=target,
            input_path=source_input,
            manifest_path=manifest_path,
            scaffold_dir=scaffold_dir,
            force=force,
            steps=steps,
            failed_step="manifest_validation",
            error=str(exc),
        )

    try:
        generate_agent_scaffold(manifest_path, scaffold_dir)
        steps.append({"name": "scaffold_generation", "status": "passed", "output": "scaffold/"})
    except Exception as exc:
        steps.append({"name": "scaffold_generation", "status": "failed", "output": "scaffold/"})
        return _failed_report(
            output_dir=target,
            input_path=source_input,
            manifest_path=manifest_path,
            scaffold_dir=scaffold_dir,
            force=force,
            steps=steps,
            failed_step="scaffold_generation",
            error=str(exc),
        )

    dry_run = _run([sys.executable, str(scaffold_dir / "run_agent.py"), "--dry-run", "--input", str(scaffold_dir / "sample_input.json")], target)
    if dry_run["exit_code"] != 0:
        steps.append({"name": "dry_run", "status": "failed", "output": dry_run["stdout"][-800:]})
        return _failed_report(
            output_dir=target,
            input_path=source_input,
            manifest_path=manifest_path,
            scaffold_dir=scaffold_dir,
            force=force,
            steps=steps,
            failed_step="dry_run",
            error=dry_run["stderr"] or dry_run["stdout"],
        )
    try:
        json.loads(dry_run["stdout"])
    except json.JSONDecodeError as exc:
        steps.append({"name": "dry_run", "status": "failed", "output": "non-json stdout"})
        return _failed_report(
            output_dir=target,
            input_path=source_input,
            manifest_path=manifest_path,
            scaffold_dir=scaffold_dir,
            force=force,
            steps=steps,
            failed_step="dry_run",
            error=f"dry-run output was not JSON: {exc}",
        )
    steps.append({"name": "dry_run", "status": "passed"})

    scaffold_tests = _run([sys.executable, "-m", "unittest", "discover", str(scaffold_dir / "tests"), "-v"], scaffold_dir)
    if scaffold_tests["exit_code"] != 0:
        steps.append({"name": "scaffold_tests", "status": "failed", "output": scaffold_tests["stdout"][-800:]})
        return _failed_report(
            output_dir=target,
            input_path=source_input,
            manifest_path=manifest_path,
            scaffold_dir=scaffold_dir,
            force=force,
            steps=steps,
            failed_step="scaffold_tests",
            error=scaffold_tests["stderr"] or scaffold_tests["stdout"],
        )
    steps.append({"name": "scaffold_tests", "status": "passed"})

    report = {
        "status": "passed",
        "input_path": source_input.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "scaffold_dir": scaffold_dir.as_posix(),
        "force": force,
        "steps": steps,
        "failed_assertions": [],
        "warnings": [],
    }
    _write_reports(target, report)
    return report


def register_agent_project_subcommand(subparsers: Any) -> None:
    parser = subparsers.add_parser("agent-project", help="Generate an end-to-end dry-run agent project from a requirement input")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory after safety checks")


def run_agent_project_command(args: Any) -> int:
    try:
        report = run_agent_project_pipeline(Path(args.input), Path(args.output_dir), force=bool(args.force))
    except Exception as exc:
        print(f"[ctcp_orchestrate][agent-project][error] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("status") == "passed" else 2


__all__ = [
    "AgentProjectPipelineError",
    "register_agent_project_subcommand",
    "run_agent_project_command",
    "run_agent_project_pipeline",
]
