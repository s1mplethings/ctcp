#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_verify


def test_build_configure_command_contains_expected_parts() -> None:
    src = Path("/tmp/src")
    build = Path("/tmp/build")
    cmd = run_verify.build_configure_command(
        cmake_exe="cmake",
        src=src,
        build=build,
        config="Release",
        generator="Ninja",
        cmake_args=["-DKEY=VALUE"],
    )
    assert cmd[:2] == ["cmake", "-S"]
    assert str(src) in cmd
    assert str(build) in cmd
    assert "-G" in cmd and "Ninja" in cmd
    assert "-DKEY=VALUE" in cmd


def test_resolve_smoke_command_prefers_install_bin() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        install = root / "dist"
        build = root / "build"
        install_bin = install / "bin"
        install_bin.mkdir(parents=True, exist_ok=True)
        exe = install_bin / ("ctcp.exe" if run_verify.os.name == "nt" else "ctcp")
        exe.write_text("fake", encoding="utf-8")
        cmd, source = run_verify.resolve_smoke_command(
            install_prefix=install,
            build_dir=build,
            config="Release",
            smoke_bin="ctcp",
            explicit_cmd="",
        )
        assert cmd is not None
        assert "--smoke" in cmd
        assert "not_found" != source


def test_collect_install_metrics_counts_files() -> None:
    with tempfile.TemporaryDirectory() as td:
        p = Path(td)
        (p / "a.txt").write_text("123", encoding="utf-8")
        (p / "sub").mkdir()
        (p / "sub" / "b.txt").write_text("xx", encoding="utf-8")
        m = run_verify.collect_install_metrics(p)
        assert m["file_count"] == 2
        assert m["total_bytes"] >= 5


def main() -> int:
    tests = [
        test_build_configure_command_contains_expected_parts,
        test_resolve_smoke_command_prefers_install_bin,
        test_collect_install_metrics_counts_files,
    ]
    for t in tests:
        t()
    print("[verify_tools_test] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
