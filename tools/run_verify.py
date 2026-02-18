#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _format_cmd(cmd: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(cmd)
    return " ".join(shlex.quote(x) for x in cmd)


def _split_cmd(value: str) -> list[str]:
    if not value.strip():
        return []
    return shlex.split(value, posix=(os.name != "nt"))


def resolve_tool(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    if os.name == "nt":
        candidates = [
            Path(rf"C:\Program Files\CMake\bin\{name}.exe"),
            Path(rf"C:\Program Files (x86)\CMake\bin\{name}.exe"),
        ]
        for c in candidates:
            if c.exists():
                return c.as_posix()
    return name


@dataclass
class StepResult:
    name: str
    cmd: str
    cwd: str
    exit_code: int | None
    duration_sec: float
    log_file: str
    status: str


def build_configure_command(
    cmake_exe: str,
    src: Path,
    build: Path,
    config: str,
    generator: str,
    cmake_args: list[str],
) -> list[str]:
    cmd = [
        cmake_exe,
        "-S",
        str(src),
        "-B",
        str(build),
        f"-DCMAKE_BUILD_TYPE={config}",
    ]
    if generator:
        cmd.extend(["-G", generator])
    cmd.extend(cmake_args)
    return cmd


def build_ctest_command(ctest_exe: str, build: Path, config: str, ctest_args: list[str]) -> list[str]:
    cmd = [ctest_exe, "--test-dir", str(build), "--output-on-failure"]
    if config:
        cmd.extend(["-C", config])
    cmd.extend(ctest_args)
    return cmd


def collect_install_metrics(install_prefix: Path) -> dict[str, Any]:
    file_count = 0
    total_bytes = 0
    for p in install_prefix.rglob("*"):
        if p.is_file():
            file_count += 1
            total_bytes += p.stat().st_size
    return {"file_count": file_count, "total_bytes": total_bytes}


def parse_ctest_metrics(log_text: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    m = re.search(r"(\d+)% tests passed,\s+(\d+)\s+tests failed out of\s+(\d+)", log_text, re.IGNORECASE)
    if m:
        out["pass_rate_percent"] = int(m.group(1))
        out["failed"] = int(m.group(2))
        out["total"] = int(m.group(3))
        out["passed"] = int(m.group(3)) - int(m.group(2))
        return out
    m2 = re.search(r"Total Tests:\s*(\d+)", log_text, re.IGNORECASE)
    if m2:
        out["total"] = int(m2.group(1))
    return out


def resolve_smoke_command(
    install_prefix: Path,
    build_dir: Path,
    config: str,
    smoke_bin: str,
    explicit_cmd: str,
) -> tuple[list[str] | None, str]:
    if explicit_cmd.strip():
        return _split_cmd(explicit_cmd), "explicit"

    candidates: list[Path] = []
    names = [smoke_bin]
    if os.name == "nt":
        names.insert(0, f"{smoke_bin}.exe")

    for name in names:
        candidates.extend(
            [
                install_prefix / "bin" / name,
                install_prefix / name,
                build_dir / config / name,
                build_dir / name,
            ]
        )
        candidates.extend(list(install_prefix.rglob(name)))

    for c in candidates:
        if c.exists() and c.is_file():
            return [str(c), "--smoke"], c.as_posix()
    return None, "not_found"


def run_command(cmd: list[str], cwd: Path, log_path: Path, env: dict[str, str] | None = None) -> tuple[int, float]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            env=env,
        )
        rc = proc.returncode
        out = proc.stdout
        err = proc.stderr
    except FileNotFoundError as exc:
        rc = 127
        out = ""
        err = f"[run_verify][error] command not found: {exc}\n"
    dt_s = time.perf_counter() - t0
    text = (
        f"$ {_format_cmd(cmd)}\n"
        f"[cwd] {cwd.as_posix()}\n"
        f"[exit_code] {rc}\n"
        f"[duration_sec] {dt_s:.3f}\n\n"
        f"--- stdout ---\n{out}\n\n"
        f"--- stderr ---\n{err}\n"
    )
    log_path.write_text(text, encoding="utf-8")
    return rc, dt_s


def write_skip_log(log_path: Path, reason: str) -> None:
    log_path.write_text(f"[SKIPPED] {reason}\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run configure/build/ctest/install/smoke and emit proof artifacts.")
    ap.add_argument("--src", default=".")
    ap.add_argument("--build", default="build")
    ap.add_argument("--config", default="Release")
    ap.add_argument("--generator", default="")
    ap.add_argument("--install-prefix", default="dist")
    ap.add_argument("--artifacts-root", default="artifacts/verify")
    ap.add_argument("--cmake-arg", action="append", default=[])
    ap.add_argument("--ctest-arg", action="append", default=[])
    ap.add_argument("--smoke-cmd", default="")
    ap.add_argument("--smoke-prefix", default="")
    ap.add_argument("--smoke-bin", default="ctcp")
    ap.add_argument("--skip-install", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    args = ap.parse_args()

    src = Path(args.src).resolve()
    build = Path(args.build).resolve()
    install_prefix = Path(args.install_prefix).resolve()
    artifacts_root = Path(args.artifacts_root).resolve()
    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    proof_dir = artifacts_root / run_id
    proof_dir.mkdir(parents=True, exist_ok=True)

    steps: list[StepResult] = []
    failed = False
    step_specs: list[dict[str, Any]] = [
        {"name": "configure", "log": "01_configure.log"},
        {"name": "build", "log": "02_build.log"},
        {"name": "ctest", "log": "03_ctest.log"},
        {"name": "install", "log": "04_install.log"},
        {"name": "smoke", "log": "05_smoke.log"},
    ]

    smoke_resolved_from = ""
    smoke_cmd_list: list[str] | None = None
    smoke_target_path = ""
    cmake_exe = resolve_tool("cmake")
    ctest_exe = resolve_tool("ctest")

    configure_cmd = build_configure_command(
        cmake_exe=cmake_exe,
        src=src,
        build=build,
        config=args.config,
        generator=args.generator,
        cmake_args=args.cmake_arg,
    )
    build_cmd = [cmake_exe, "--build", str(build), "--config", args.config]
    ctest_cmd = build_ctest_command(ctest_exe=ctest_exe, build=build, config=args.config, ctest_args=args.ctest_arg)
    install_cmd = [
        cmake_exe,
        "--install",
        str(build),
        "--config",
        args.config,
        "--prefix",
        str(install_prefix),
    ]

    commands: dict[str, list[str] | None] = {
        "configure": configure_cmd,
        "build": build_cmd,
        "ctest": ctest_cmd,
        "install": None if args.skip_install else install_cmd,
        "smoke": ["__AUTO_SMOKE__"] if not args.skip_smoke else None,
    }

    t_all_0 = time.perf_counter()
    for spec in step_specs:
        name = spec["name"]
        log_name = spec["log"]
        log_path = proof_dir / log_name
        cmd = commands[name]

        if not failed and name == "smoke" and cmd is not None:
            smoke_cmd_list, smoke_resolved_from = resolve_smoke_command(
                install_prefix=install_prefix,
                build_dir=build,
                config=args.config,
                smoke_bin=args.smoke_bin,
                explicit_cmd=args.smoke_cmd,
            )
            if smoke_cmd_list is None:
                cmd = []
            else:
                prefix = _split_cmd(args.smoke_prefix)
                cmd = prefix + smoke_cmd_list
                commands[name] = cmd
                if smoke_cmd_list:
                    smoke_target_path = smoke_cmd_list[0]

        if failed:
            write_skip_log(log_path, "Skipped because a previous required step failed.")
            steps.append(
                StepResult(
                    name=name,
                    cmd="",
                    cwd=src.as_posix(),
                    exit_code=None,
                    duration_sec=0.0,
                    log_file=log_name,
                    status="skipped",
                )
            )
            continue

        if cmd is None:
            write_skip_log(log_path, f"Step '{name}' disabled by flag.")
            steps.append(
                StepResult(
                    name=name,
                    cmd="",
                    cwd=src.as_posix(),
                    exit_code=None,
                    duration_sec=0.0,
                    log_file=log_name,
                    status="skipped",
                )
            )
            failed = True
            continue

        if name == "smoke" and cmd == []:
            write_skip_log(log_path, "Smoke target not found in install/build outputs.")
            steps.append(
                StepResult(
                    name=name,
                    cmd="",
                    cwd=src.as_posix(),
                    exit_code=127,
                    duration_sec=0.0,
                    log_file=log_name,
                    status="fail",
                )
            )
            failed = True
            continue

        rc, dt_s = run_command(cmd=cmd, cwd=src, log_path=log_path)
        status = "pass" if rc == 0 else "fail"
        steps.append(
            StepResult(
                name=name,
                cmd=_format_cmd(cmd),
                cwd=src.as_posix(),
                exit_code=rc,
                duration_sec=dt_s,
                log_file=log_name,
                status=status,
            )
        )
        if rc != 0:
            failed = True

    total_duration = time.perf_counter() - t_all_0

    ctest_log = (proof_dir / "03_ctest.log").read_text(encoding="utf-8", errors="replace")
    ctest_metrics = parse_ctest_metrics(ctest_log)
    install_metrics = collect_install_metrics(install_prefix) if install_prefix.exists() else {"file_count": 0, "total_bytes": 0}
    smoke_size = 0
    if smoke_target_path and Path(smoke_target_path).exists():
        smoke_size = Path(smoke_target_path).stat().st_size

    platform_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "cmake": cmake_exe,
        "ctest": ctest_exe,
        "ninja": shutil.which("ninja") or "",
        "compiler": shutil.which("cl") or shutil.which("g++") or shutil.which("clang++") or "",
        "qmake": shutil.which("qmake") or "",
    }

    proof = {
        "schema_version": "adlc-proof-v1",
        "run_id": run_id,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "result": "FAIL" if failed else "PASS",
        "paths": {
            "source": src.as_posix(),
            "build": build.as_posix(),
            "install_prefix": install_prefix.as_posix(),
            "proof_dir": proof_dir.as_posix(),
        },
        "platform": platform_info,
        "inputs": {
            "config": args.config,
            "generator": args.generator,
            "cmake_args": args.cmake_arg,
            "ctest_args": args.ctest_arg,
            "smoke_cmd": args.smoke_cmd,
            "smoke_prefix": args.smoke_prefix,
            "smoke_bin": args.smoke_bin,
            "skip_install": args.skip_install,
            "skip_smoke": args.skip_smoke,
            "smoke_resolved_from": smoke_resolved_from,
        },
        "steps": [s.__dict__ for s in steps],
        "metrics": {
            "total_duration_sec": round(total_duration, 3),
            "ctest": ctest_metrics,
            "install": install_metrics,
            "smoke_binary_size": smoke_size,
        },
    }

    proof_path = proof_dir / "proof.json"
    proof_path.write_text(json.dumps(proof, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts_root.mkdir(parents=True, exist_ok=True)
    (artifacts_root / "latest_proof_path.txt").write_text(proof_dir.as_posix(), encoding="utf-8")
    print(f"[run_verify] proof_dir={proof_dir.as_posix()}")
    print(f"[run_verify] proof_json={proof_path.as_posix()}")
    print(f"[run_verify] result={proof['result']}")
    return 0 if proof["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
