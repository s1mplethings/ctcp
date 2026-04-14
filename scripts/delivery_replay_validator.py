from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Any

from tools.providers.project_generation_source_helpers import _render_visual_evidence_png


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_capture(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    import subprocess

    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "command": " ".join(cmd),
        "rc": int(proc.returncode),
        "stdout_tail": "\n".join(str(proc.stdout or "").splitlines()[-12:]),
        "stderr_tail": "\n".join(str(proc.stderr or "").splitlines()[-12:]),
    }


def _fail(*, package_path: Path, extracted_dir: Path, report_path: Path, entrypoint_detected: str = "", startup_command: str = "", first_failure_stage: str, short_reason: str, startup_pass: bool = False, minimal_flow_pass: bool = False, replay_screenshot_path: str = "") -> dict[str, Any]:
    report = {
        "package_path": str(package_path),
        "extracted_dir": str(extracted_dir),
        "entrypoint_detected": entrypoint_detected,
        "startup_command": startup_command,
        "startup_pass": bool(startup_pass),
        "minimal_flow_pass": bool(minimal_flow_pass),
        "replay_screenshot_path": str(replay_screenshot_path),
        "overall_pass": False,
        "first_failure_stage": first_failure_stage,
        "short_reason": short_reason,
    }
    _write_json(report_path, report)
    return report


def _candidate_project_roots(extracted_dir: Path) -> list[Path]:
    roots = [extracted_dir]
    roots.extend(sorted(path for path in extracted_dir.iterdir() if path.is_dir()))
    return roots


def detect_entrypoint(extracted_dir: Path) -> dict[str, Any]:
    script_candidates = (
        ("scripts/run_project_web.py", "web_first"),
        ("scripts/run_project_gui.py", "gui_first"),
        ("scripts/run_project_cli.py", "cli_first"),
    )
    for root in _candidate_project_roots(extracted_dir):
        for rel, shape in script_candidates:
            candidate = root / rel
            if candidate.exists():
                return {
                    "project_root": root,
                    "entrypoint_path": candidate,
                    "entrypoint_detected": rel,
                    "delivery_shape": shape,
                }
        service_paths = list((root / "src").glob("*/service.py")) if (root / "src").exists() else []
        if service_paths:
            service_path = service_paths[0]
            return {
                "project_root": root,
                "entrypoint_path": service_path,
                "entrypoint_detected": str(service_path.relative_to(root).as_posix()),
                "delivery_shape": "tool_library_first",
                "package_name": service_path.parent.name,
            }
        for rel in ("app.py", "main.py"):
            candidate = root / rel
            if candidate.exists():
                return {
                    "project_root": root,
                    "entrypoint_path": candidate,
                    "entrypoint_detected": rel,
                    "delivery_shape": "python_app",
                }
    return {}


def _startup_command(info: dict[str, Any]) -> list[str]:
    entrypoint_path = Path(str(info.get("entrypoint_path", "")))
    shape = str(info.get("delivery_shape", ""))
    if shape == "web_first":
        return [sys.executable, str(entrypoint_path), "--serve"]
    if shape in {"gui_first", "cli_first"}:
        return [sys.executable, str(entrypoint_path), "--help"]
    if shape == "tool_library_first":
        package_name = str(info.get("package_name", "")).strip()
        src_root = entrypoint_path.parents[1]
        return [
            sys.executable,
            "-c",
            (
                "import sys; "
                f"sys.path.insert(0, r'{src_root}'); "
                f"import {package_name}.service as service; "
                "print('ok' if hasattr(service, 'generate_project') else 'missing')"
            ),
        ]
    return [sys.executable, str(entrypoint_path)]


def _minimal_flow_command(info: dict[str, Any], export_dir: Path) -> list[str]:
    entrypoint_path = Path(str(info.get("entrypoint_path", "")))
    shape = str(info.get("delivery_shape", ""))
    if shape == "web_first":
        return [
            sys.executable,
            str(entrypoint_path),
            "--goal",
            "replay smoke export",
            "--project-name",
            "Replay Project",
            "--out",
            str(export_dir),
        ]
    if shape == "gui_first":
        return [
            sys.executable,
            str(entrypoint_path),
            "--goal",
            "replay smoke export",
            "--project-name",
            "Replay Project",
            "--out",
            str(export_dir),
            "--headless",
        ]
    if shape == "cli_first":
        return [
            sys.executable,
            str(entrypoint_path),
            "--goal",
            "replay smoke export",
            "--project-name",
            "Replay Project",
            "--out",
            str(export_dir),
        ]
    if shape == "tool_library_first":
        package_name = str(info.get("package_name", "")).strip()
        src_root = entrypoint_path.parents[1]
        return [
            sys.executable,
            "-c",
            (
                "import json, sys; "
                "from pathlib import Path; "
                f"sys.path.insert(0, r'{src_root}'); "
                f"from {package_name}.service import generate_project; "
                f"result = generate_project(goal='replay smoke export', project_name='Replay Project', out_dir=Path(r'{export_dir}')); "
                "print(json.dumps(result, ensure_ascii=False))"
            ),
        ]
    return [sys.executable, str(entrypoint_path)]


def _write_replay_screenshot(*, screenshot_path: Path, title: str, subtitle: str, detail_lines: list[str]) -> None:
    _render_visual_evidence_png(
        path=screenshot_path,
        title=title,
        subtitle=subtitle,
        detail_lines=detail_lines,
    )


def run_delivery_replay_check(*, package_path: Path | str, output_root: Path | str | None = None) -> dict[str, Any]:
    package = Path(package_path).resolve()
    base_root = Path(output_root).resolve() if output_root else Path(shutil.mkdtemp(prefix="ctcp_delivery_replay_")).resolve()
    extracted_dir = (base_root / "extracted").resolve()
    replay_artifacts_dir = (base_root / "replay_artifacts").resolve()
    report_path = (replay_artifacts_dir / "replay_report.json").resolve()
    screenshot_path = (replay_artifacts_dir / "replayed_screenshot.png").resolve()
    replay_artifacts_dir.mkdir(parents=True, exist_ok=True)

    if not package.exists():
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            first_failure_stage="package_missing",
            short_reason="package file does not exist",
        )
    if package.stat().st_size <= 0:
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            first_failure_stage="package_empty",
            short_reason="package file is empty",
        )

    if extracted_dir.exists():
        shutil.rmtree(extracted_dir)
    extracted_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(package) as zf:
            zf.extractall(extracted_dir)
    except Exception as exc:
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            first_failure_stage="extract_failed",
            short_reason=f"package extraction failed: {exc}",
        )

    info = detect_entrypoint(extracted_dir)
    if not info:
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            first_failure_stage="entrypoint_missing",
            short_reason="no supported entrypoint detected in extracted package",
        )

    startup_cmd = _startup_command(info)
    startup = _run_capture(startup_cmd, cwd=Path(info["project_root"]))
    if int(startup.get("rc", 1)) != 0:
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            entrypoint_detected=str(info.get("entrypoint_detected", "")),
            startup_command=str(startup.get("command", "")),
            first_failure_stage="startup_failed",
            short_reason=(str(startup.get("stderr_tail", "")).strip() or str(startup.get("stdout_tail", "")).strip() or "startup command failed"),
        )

    export_dir = (base_root / "replay_export").resolve()
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)
    flow_cmd = _minimal_flow_command(info, export_dir)
    flow = _run_capture(flow_cmd, cwd=Path(info["project_root"]))
    if int(flow.get("rc", 1)) != 0:
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            entrypoint_detected=str(info.get("entrypoint_detected", "")),
            startup_command=str(startup.get("command", "")),
            first_failure_stage="minimal_flow_failed",
            short_reason=(str(flow.get("stderr_tail", "")).strip() or str(flow.get("stdout_tail", "")).strip() or "minimal flow command failed"),
            startup_pass=True,
        )

    exported_files = [path for path in export_dir.rglob("*") if path.is_file()]
    if str(info.get("delivery_shape", "")) == "python_app":
        exported_files = [Path(str(info.get("entrypoint_path", "")))]
    if not exported_files:
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            entrypoint_detected=str(info.get("entrypoint_detected", "")),
            startup_command=str(startup.get("command", "")),
            first_failure_stage="minimal_flow_failed",
            short_reason="minimal flow completed without any exported files",
            startup_pass=True,
        )

    _write_replay_screenshot(
        screenshot_path=screenshot_path,
        title="CTCP REPLAY PASS",
        subtitle=str(Path(str(info.get("entrypoint_detected", ""))).name or "package replay"),
        detail_lines=[
            f"STARTUP PASS {Path(str(info.get('entrypoint_detected', ''))).name}",
            f"FLOW PASS {len(exported_files)} FILES",
            f"PACKAGE {package.name}",
        ] + [f"OUT {path.name}" for path in exported_files[:5]],
    )
    if not screenshot_path.exists() or screenshot_path.stat().st_size <= 0:
        return _fail(
            package_path=package,
            extracted_dir=extracted_dir,
            report_path=report_path,
            entrypoint_detected=str(info.get("entrypoint_detected", "")),
            startup_command=str(startup.get("command", "")),
            first_failure_stage="replay_screenshot_failed",
            short_reason="replay screenshot was not created",
            startup_pass=True,
            minimal_flow_pass=True,
        )

    report = {
        "package_path": str(package),
        "extracted_dir": str(extracted_dir),
        "entrypoint_detected": str(info.get("entrypoint_detected", "")),
        "startup_command": str(startup.get("command", "")),
        "startup_pass": True,
        "minimal_flow_pass": True,
        "replay_screenshot_path": str(screenshot_path),
        "overall_pass": True,
        "first_failure_stage": "",
        "short_reason": "",
    }
    _write_json(report_path, report)
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate a delivered CTCP package by replaying it in a clean directory")
    ap.add_argument("--package", required=True, help="Package zip path")
    ap.add_argument("--output-root", default="", help="Optional replay working/evidence directory")
    args = ap.parse_args()
    report = run_delivery_replay_check(package_path=args.package, output_root=args.output_root or None)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if bool(report.get("overall_pass", False)) else 1


if __name__ == "__main__":
    raise SystemExit(main())
