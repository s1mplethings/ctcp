#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import datetime as dt
import json
import math
import os
import re
import shutil
import stat
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import interaction_core as ic

ROOT = Path(__file__).resolve().parents[2]
RUNS_DIR = ROOT / "tests" / "fixtures" / "adlc_forge_full_bundle" / "runs"
DETAILED_REPORT = RUNS_DIR / "ISSUE_REPORT_DETAILED.md"
DIAG_REPORT = RUNS_DIR / "ISSUE_DIAGNOSIS.md"
SUMMARY_JSON = RUNS_DIR / "_suite_eval_summary.json"
SIMLAB_SUMMARY_JSON = RUNS_DIR / "_simlab_suite_summary.json"
SIMLAB_RUNS_DIR = RUNS_DIR / "simlab_runs"
SANDBOX = RUNS_DIR / "_gate_matrix_sandbox"
ENTRY_SUITE_GATE = Path("tools/checks/suite_gate.py")
ENTRY_LIVE_SUITE = Path("tests/fixtures/adlc_forge_full_bundle/suites/forge_full_suite.live.yaml")


@dataclass
class CmdResult:
    rc: int
    stdout: str
    stderr: str
    cmd: str


def run_cmd(cmd: list[str], cwd: Path, timeout: int = 240) -> CmdResult:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return CmdResult(rc=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, cmd=" ".join(cmd))


def detect_preflight(repo: Path) -> dict[str, Any]:
    def _ensure_cmake_in_path() -> None:
        if shutil.which("cmake") is not None:
            return
        candidates = [
            Path(r"C:\Program Files\CMake\bin"),
            Path(r"C:\Program Files (x86)\CMake\bin"),
        ]
        for c in candidates:
            cm = c / "cmake.exe"
            if cm.exists():
                os.environ["PATH"] = str(c) + os.pathsep + os.environ.get("PATH", "")
                return

    def _py_mod_exists(mod_name: str) -> bool:
        out = run_cmd(
            ["python", "-c", f"import importlib.util; print(1 if importlib.util.find_spec('{mod_name}') else 0)"],
            repo,
        )
        return out.rc == 0 and out.stdout.strip() == "1"

    _ensure_cmake_in_path()
    suite_gate_exists = (repo / ENTRY_SUITE_GATE).exists()
    live_suite_exists = (repo / ENTRY_LIVE_SUITE).exists()
    has_cmake = shutil.which("cmake") is not None
    has_cl = shutil.which("cl") is not None
    has_gpp = shutil.which("g++") is not None
    has_clangpp = shutil.which("clang++") is not None
    has_cpp_compiler = has_cl or has_gpp or has_clangpp
    has_qmake = shutil.which("qmake") is not None
    has_windeployqt = shutil.which("windeployqt") is not None
    has_qt_tooling = has_qmake or has_windeployqt
    has_pytest_qt = _py_mod_exists("pytestqt")
    has_display = bool(os.environ.get("DISPLAY"))
    has_gui_harness = any(
        (repo / p).exists()
        for p in [
            "tests/gui",
            "tests/qt",
            "tools/checks/gui_matrix_runner.py",
            "tools/checks/qt_gui_runner.py",
        ]
    )
    has_gui_automation = has_qt_tooling and has_pytest_qt and has_display and has_gui_harness
    has_build_toolchain = has_cmake and has_cpp_compiler and has_qt_tooling
    gui_missing: list[str] = []
    if not has_qt_tooling:
        gui_missing.append("Qt runtime tools not found (qmake/windeployqt)")
    if not has_pytest_qt:
        gui_missing.append("pytest-qt not installed")
    if not has_display:
        gui_missing.append("display not available (DISPLAY missing)")
    if not has_gui_harness:
        gui_missing.append("GUI harness not implemented (tests/gui or tools/checks gui runner missing)")
    if has_gui_automation:
        optional_gui_smoke = {
            "status": "ready",
            "reason": "GUI dependencies available; optional smoke can run separately.",
            "command": "python tools/checks/web_spider_visual_check.py",
        }
    else:
        optional_gui_smoke = {
            "status": "skip",
            "reason": "missing dependency: Qt/GUI automation | " + "; ".join(gui_missing),
            "command": "python tools/checks/web_spider_visual_check.py",
        }
    suite_entry_skip_reasons: list[str] = []
    if not suite_gate_exists:
        suite_entry_skip_reasons.append(f"missing entry: {ENTRY_SUITE_GATE.as_posix()}")
    if not live_suite_exists:
        suite_entry_skip_reasons.append(f"missing entry: {ENTRY_LIVE_SUITE.as_posix()}")

    return {
        "entry_suite_gate_exists": suite_gate_exists,
        "entry_live_suite_exists": live_suite_exists,
        "suite_entry_skip_reasons": suite_entry_skip_reasons,
        "has_cmake": has_cmake,
        "has_cl": has_cl,
        "has_gpp": has_gpp,
        "has_clangpp": has_clangpp,
        "has_cpp_compiler": has_cpp_compiler,
        "has_qmake": has_qmake,
        "has_windeployqt": has_windeployqt,
        "has_qt_tooling": has_qt_tooling,
        "has_pytest_qt": has_pytest_qt,
        "has_display": has_display,
        "has_gui_harness": has_gui_harness,
        "has_build_toolchain": has_build_toolchain,
        "has_gui_automation": has_gui_automation,
        "optional_gui_smoke": optional_gui_smoke,
    }


def _on_rm_error(func, path, exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    func(path)


def copy_repo_for_sandbox(dst: Path) -> Path:
    target = dst
    if target.exists():
        try:
            shutil.rmtree(target, onerror=_on_rm_error)
        except OSError as exc:
            ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
            target = dst.parent / f"{dst.name}_{ts}"
            print(
                f"[gate_matrix] warning: failed to clean sandbox {dst} ({exc}); "
                f"using {target} instead"
            )

    def ignore(dir_path: str, names: list[str]) -> set[str]:
        # Avoid expensive/fragile .resolve() here; nested artifact trees can
        # create very deep paths and trigger recursion on Windows.
        try:
            rel_posix = Path(os.path.relpath(dir_path, ROOT)).as_posix()
        except Exception:
            rel_posix = ""
        ignored: set[str] = set()

        for name in names:
            if rel_posix in (".", ""):
                child = name
            else:
                child = f"{rel_posix}/{name}"
            if name in {
                ".git",
                ".venv",
                "build",
                "build_lite",
                "build_verify",
                "build_gui",
                "dist",
                "__pycache__",
                ".pytest_cache",
            }:
                ignored.add(name)
                continue
            if (
                child.startswith("runs/")
                or child.startswith("meta/runs/")
                or child.startswith("simlab/_runs")
                or child.startswith("tests/fixtures/adlc_forge_full_bundle/runs/")
                or child.startswith("artifacts/verify/")
            ):
                ignored.add(name)
                continue
            if name == "__pycache__":
                ignored.add(name)
                continue
        return ignored

    shutil.copytree(ROOT, target, ignore=ignore)
    return target


def git_init_clean_repo(repo: Path) -> None:
    run_cmd(["git", "init"], repo)
    run_cmd(["git", "config", "user.email", "matrix@example.local"], repo)
    run_cmd(["git", "config", "user.name", "matrix-runner"], repo)
    run_cmd(["git", "add", "-A"], repo)
    c = run_cmd(["git", "commit", "-m", "baseline"], repo)
    if c.rc != 0:
        raise RuntimeError(f"git baseline commit failed:\n{c.stdout}\n{c.stderr}")


@contextlib.contextmanager
def preserve_files(repo: Path, rel_paths: list[str]):
    saved: dict[str, tuple[bool, bytes]] = {}
    for rel in rel_paths:
        p = repo / rel
        if p.exists():
            saved[rel] = (True, p.read_bytes())
        else:
            saved[rel] = (False, b"")
    try:
        yield
    finally:
        for rel, (exists, data) in saved.items():
            p = repo / rel
            if exists:
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(data)
            else:
                if p.exists():
                    if p.is_dir():
                        shutil.rmtree(p)
                    else:
                        p.unlink()


def set_code_allowed(repo: Path, allow: bool) -> None:
    current = repo / "meta/tasks/CURRENT.md"
    txt = current.read_text(encoding="utf-8")
    txt = re.sub(
        r"\[\s*[xX ]\s*\]\s*Code changes allowed",
        "[x] Code changes allowed" if allow else "[ ] Code changes allowed",
        txt,
    )
    current.write_text(txt, encoding="utf-8")


def run_verify_repo(repo: Path) -> CmdResult:
    return run_cmd(["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/verify_repo.ps1"], repo, timeout=480)


def run_verify(repo: Path) -> CmdResult:
    return run_cmd(["powershell", "-ExecutionPolicy", "Bypass", "-File", "scripts/verify_repo.ps1"], repo, timeout=480)


def run_sync_check(repo: Path) -> CmdResult:
    return run_cmd(["python", "scripts/sync_doc_links.py", "--check"], repo)


def run_sync_write(repo: Path) -> CmdResult:
    return run_cmd(["python", "scripts/sync_doc_links.py"], repo)


def run_assistant(repo: Path, args: list[str]) -> CmdResult:
    return run_cmd(["python", "scripts/ctcp_orchestrate.py"] + args, repo)


def run_simlab_suite(repo: Path) -> tuple[CmdResult, dict[str, Any] | None]:
    SIMLAB_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = run_cmd(
        [
            "python",
            "simlab/run.py",
            "--suite",
            "core",
            "--runs-root",
            str(SIMLAB_RUNS_DIR),
            "--json-out",
            str(SIMLAB_SUMMARY_JSON),
        ],
        repo,
        timeout=1200,
    )
    summary: dict[str, Any] | None = None
    if SIMLAB_SUMMARY_JSON.exists():
        try:
            summary = json.loads(SIMLAB_SUMMARY_JSON.read_text(encoding="utf-8"))
        except Exception:
            summary = None
    return out, summary


def record_case(cases: list[dict[str, Any]], cid: int, name: str, status: str, expectation: str, evidence: dict[str, Any]) -> None:
    cases.append(
        {
            "id": cid,
            "name": name,
            "status": status,
            "expectation": expectation,
            "evidence": evidence,
        }
    )


def contains(s: str, needle: str) -> bool:
    return needle.lower() in s.lower()


def run_matrix(repo: Path, preflight: dict[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    # 01
    with preserve_files(repo, ["meta/tasks/CURRENT.md", "src/main.cpp"]):
        set_code_allowed(repo, allow=False)
        p = repo / "src/main.cpp"
        p.write_text(p.read_text(encoding="utf-8") + "\n// matrix-case-01\n", encoding="utf-8")
        out = run_verify_repo(repo)
        diff = run_cmd(["git", "diff", "--", "meta/tasks/CURRENT.md", "src/main.cpp"], repo)
        ok = out.rc != 0 and contains(out.stdout + out.stderr, "Code changes allowed")
        record_case(cases, 1, "禁止代码门禁（未授权必须失败）", "pass" if ok else "fail",
                    "verify should fail with Code changes allowed hint",
                    {"rc": out.rc, "stdout_tail": out.stdout[-1200:], "stderr_tail": out.stderr[-1200:], "diff": diff.stdout[-1200:]})

    # 02
    with preserve_files(repo, ["meta/tasks/CURRENT.md", "src/main.cpp", "docs/00_overview.md"]):
        set_code_allowed(repo, allow=True)
        p = repo / "src/main.cpp"
        p.write_text(p.read_text(encoding="utf-8") + "\n// matrix-case-02\n", encoding="utf-8")
        doc = repo / "docs/00_overview.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\n<!-- matrix-case-02-doc-first -->\n", encoding="utf-8")
        out = run_verify_repo(repo)
        ok = out.rc == 0 and contains(out.stdout + out.stderr, "[workflow_checks] ok")
        record_case(cases, 2, "禁止代码门禁（授权后必须通过）", "pass" if ok else "fail",
                    "workflow gate should pass with authorization and doc/spec-first change",
                    {"rc": out.rc, "stdout_tail": out.stdout[-1200:], "stderr_tail": out.stderr[-1200:]})

    # 03
    with preserve_files(repo, ["meta/tasks/CURRENT.md", "docs/00_overview.md"]):
        set_code_allowed(repo, allow=False)
        doc = repo / "docs/00_overview.md"
        doc.write_text(doc.read_text(encoding="utf-8") + "\n<!-- matrix-case-03 -->\n", encoding="utf-8")
        out = run_verify_repo(repo)
        ok = out.rc == 0 and contains(out.stdout + out.stderr, "[workflow_checks] ok")
        record_case(cases, 3, "只改文档不需要授权（应通过）", "pass" if ok else "fail",
                    "doc-only change should not be blocked by workflow gate",
                    {"rc": out.rc, "stdout_tail": out.stdout[-1200:], "stderr_tail": out.stderr[-1200:]})

    # 04
    with preserve_files(repo, ["ai_context/00_AI_CONTRACT.md"]):
        target = repo / "ai_context/00_AI_CONTRACT.md"
        bak = repo / "ai_context/00_AI_CONTRACT.md.matrixbak"
        target.rename(bak)
        out = run_verify_repo(repo)
        bak.rename(target)
        ok = out.rc != 0 and contains(out.stdout + out.stderr, "ai_context/00_AI_CONTRACT.md")
        record_case(cases, 4, "缺失契约文件必须失败", "pass" if ok else "fail",
                    "verify should fail and mention missing AI contract",
                    {"rc": out.rc, "stdout_tail": out.stdout[-1200:], "stderr_tail": out.stderr[-1200:]})

    # 05
    with preserve_files(repo, ["README.md"]):
        rd = repo / "README.md"
        rd.write_text(rd.read_text(encoding="utf-8") + "\n- [Broken](docs/NOPE.md)\n", encoding="utf-8")
        out = run_verify_repo(repo)
        ok = out.rc != 0 and contains(out.stdout + out.stderr, "docs/NOPE.md") and contains(out.stdout + out.stderr, "README.md")
        record_case(cases, 5, "README 引用不存在文件必须失败", "pass" if ok else "fail",
                    "contract check should detect broken README link",
                    {"rc": out.rc, "stdout_tail": out.stdout[-1200:], "stderr_tail": out.stderr[-1200:]})

    # 06
    out = run_verify_repo(repo)
    ok = out.rc == 0 and contains(out.stdout + out.stderr, "readme links ok")
    record_case(cases, 6, "README 修复断链后必须通过", "pass" if ok else "fail",
                "contract check should pass after link fix",
                {"rc": out.rc, "stdout_tail": out.stdout[-1200:], "stderr_tail": out.stderr[-1200:]})

    # 07
    out = run_sync_check(repo)
    no_diff = run_cmd(["git", "diff", "--name-only"], repo)
    ok = out.rc == 0 and no_diff.stdout.strip() == ""
    record_case(cases, 7, "doc link check（无改动应通过）", "pass" if ok else "fail",
                "sync_doc_links --check should pass with no diff",
                {"rc": out.rc, "stdout_tail": out.stdout[-1200:], "stderr_tail": out.stderr[-1200:], "diff_names": no_diff.stdout.strip()})

    # 08
    with preserve_files(repo, ["README.md"]):
        readme = repo / "README.md"
        txt = readme.read_text(encoding="utf-8", errors="replace")
        tampered = txt.replace(
            "## Project Docs",
            "## Project Docs\n\n- [tampered-entry](docs/NOPE.md)",
            1,
        )
        readme.write_text(tampered, encoding="utf-8")
        out1 = run_sync_write(repo)
        diff = run_cmd(["git", "diff", "--", "README.md"], repo)
        out2 = run_sync_check(repo)
        wrote_update = contains(out1.stdout + out1.stderr, "updated:")
        ok = out1.rc == 0 and out2.rc == 0 and (wrote_update or diff.stdout.strip() != "")
        record_case(cases, 8, "doc link 同步可预测（产生固定 diff）", "pass" if ok else "fail",
                    "sync write should repair tampered README doc-index block, then --check should pass",
                    {"write_rc": out1.rc, "check_rc": out2.rc, "write_out": out1.stdout[-800:], "check_out": out2.stdout[-800:], "diff": diff.stdout[-1600:], "wrote_update": wrote_update})

    # 09
    out = run_assistant(repo, ["new-run", "--goal", "hitbox-fix"])
    current = (repo / "meta/tasks/CURRENT.md").read_text(encoding="utf-8", errors="replace")
    ok = out.rc == 0 and "## Acceptance" in current
    record_case(cases, 9, "orchestrator new-run 生成 CURRENT.md", "pass" if ok else "fail",
                "CURRENT.md should contain acceptance checklist",
                {"rc": out.rc, "stdout": out.stdout[-800:], "current_head": "\n".join(current.splitlines()[:20])})

    # 10
    out = run_assistant(repo, ["new-run", "--goal", "cytoscape-layout"])
    report = repo / "meta/reports/LAST.md"
    report_txt = report.read_text(encoding="utf-8", errors="replace") if report.exists() else ""
    ok = out.rc == 0 and report.exists() and "## Goal" in report_txt
    record_case(cases, 10, "orchestrator new-run 保证 LAST.md 存在", "pass" if ok else "fail",
                "new-run should create LAST.md when missing",
                {"rc": out.rc, "stdout": out.stdout[-800:], "file": report.as_posix(), "head": "\n".join(report_txt.splitlines()[:20])})

    # 11
    out = run_cmd(
        ["python", "scripts/resolve_workflow.py", "--goal", "headless-lite", "--out", "artifacts/_matrix_find.json"],
        repo,
    )
    find = repo / "artifacts/_matrix_find.json"
    find_txt = find.read_text(encoding="utf-8", errors="replace") if find.exists() else ""
    ok = out.rc == 0 and "\"selected_workflow_id\"" in find_txt
    record_case(cases, 11, "resolver 输出 find_result 选择信息", "pass" if ok else "fail",
                "resolve_workflow should produce selected_workflow_id",
                {"rc": out.rc, "stdout": out.stdout[-1600:], "stderr": out.stderr[-400:], "find_head": "\n".join(find_txt.splitlines()[:20])})

    # 12
    if not preflight["has_build_toolchain"]:
        t12_reasons: list[str] = []
        if not preflight["has_cmake"]:
            t12_reasons.append("cmake")
        if not preflight["has_cpp_compiler"]:
            t12_reasons.append("C++ compiler")
        if not preflight["has_qt_tooling"]:
            t12_reasons.append("Qt tooling (qmake/windeployqt)")
        reason = "missing dependency: " + ", ".join(t12_reasons) if t12_reasons else "missing dependency: build toolchain"
        record_case(cases, 12, "Windows build 脚本存在且可执行", "skip",
                    "requires build toolchain in environment", {"reason": reason})
    else:
        out = run_cmd(["cmd", "/c", "build_v6.cmd"], repo, timeout=1200)
        build_exists = (repo / "build").exists()
        ok = out.rc == 0 and build_exists
        record_case(cases, 12, "Windows build 脚本存在且可执行", "pass" if ok else "fail",
                    "build_v6.cmd should configure+build and create build dir",
                    {"rc": out.rc, "stdout_tail": out.stdout[-2000:], "stderr_tail": out.stderr[-1200:], "build_exists": build_exists})

    # 13
    _ = run_sync_write(repo)
    out = run_verify_repo(repo)
    text = out.stdout + "\n" + out.stderr
    token_groups = [
        ["[verify_repo] repo root"],
        ["[verify_repo] workflow gate", "[verify_repo] workflow checks"],
        ["[verify_repo] contract checks"],
        ["[verify_repo] doc index check", "[verify_repo] sync doc links"],
    ]
    pos: list[int] = []
    for group in token_groups:
        group_pos = [text.find(t) for t in group if text.find(t) >= 0]
        pos.append(min(group_pos) if group_pos else -1)
    ordered = all(p >= 0 for p in pos) and pos == sorted(pos)
    ok = out.rc == 0 and ordered
    record_case(cases, 13, "verify_repo 是唯一主 gate（覆盖 workflow+contract+doclinks）", "pass" if ok else "fail",
                "verify_repo output should contain expected sequence",
                {"rc": out.rc, "positions": pos, "stdout_tail": out.stdout[-2200:], "stderr_tail": out.stderr[-1200:]})

    # 14-20: headless core-interaction tests (no Qt/display dependency)
    core_graph = {
        "nodes": [
            {"id": "a", "x": 0.0, "y": 0.0, "r": 4.0},
            {"id": "b", "x": 100.0, "y": 0.0, "r": 4.0},
            {"id": "c", "x": 50.0, "y": 0.0, "r": 4.0},
        ],
        "edges": [{"id": "e_ab", "src": "a", "dst": "b"}],
    }
    core_params = {
        "node_radius_px": 8.0,
        "edge_radius_px": 5.0,
        "node_priority": True,
        "distance_metric": "pixel_to_world",
    }

    # 14: single click select
    hit = ic.hit_test(core_graph, {"x": 1.0, "y": 1.0}, 1.0, core_params)
    st = ic.selection_update(
        {},
        {"type": "click", "target": {"kind": hit["kind"], "id": hit["id"]}, "modifiers": {"ctrl": False}, "click_count": 1},
    )
    ok = hit["kind"] == "node" and st.get("selected_kind") == "node" and st.get("selected_id") == "a"
    record_case(
        cases,
        14,
        "单击选中节点（只测选中态）",
        "pass" if ok else "fail",
        "single click should select node target",
        {"hit": hit, "state": st},
    )

    # 15: double click drilldown
    trans = ic.drilldown_transition(
        {},
        {"type": "click", "target": {"kind": "node", "id": "c"}, "modifiers": {"ctrl": False}, "click_count": 2},
    )
    ok = trans.get("action") == "drilldown" and trans.get("target_id") == "c"
    record_case(
        cases,
        15,
        "二次点击钻取（只测 drilldown）",
        "pass" if ok else "fail",
        "double click on node should emit drilldown action",
        {"transition": trans},
    )

    # 16: ctrl+click open file action
    act = ic.ctrl_click_action(
        {"type": "click", "target": {"kind": "node", "id": "c"}, "modifiers": {"ctrl": True}, "click_count": 1},
        {"c": {"path": "src/main.cpp", "is_file": True}},
    )
    ok = act.get("action") == "open_file" and act.get("path") == "src/main.cpp"
    record_case(
        cases,
        16,
        "Ctrl+点击打开文件（只测 open-file 动作）",
        "pass" if ok else "fail",
        "ctrl+click file node should request open_file(path)",
        {"action": act},
    )

    # 17: wheel zoom formula
    zoom_params = {"zoom_k": 0.0018, "min_scale": 0.18, "max_scale": 5.0}
    new_scale = ic.zoom_update(1.0, 120.0, zoom_params)
    expected = max(zoom_params["min_scale"], min(zoom_params["max_scale"], 1.0 * math.exp(-120.0 * zoom_params["zoom_k"])))
    ok = abs(new_scale - expected) < 1e-12 and zoom_params["min_scale"] <= new_scale <= zoom_params["max_scale"]
    record_case(
        cases,
        17,
        "滚轮缩放（只测 zoom）",
        "pass" if ok else "fail",
        "zoom_update should follow exp wheel formula with clamp",
        {"new_scale": new_scale, "expected": expected, "params": zoom_params},
    )

    # 18: node priority over edge
    hit = ic.hit_test(core_graph, {"x": 50.0, "y": 1.0}, 1.0, core_params)
    ok = hit.get("kind") == "node" and hit.get("id") == "c"
    record_case(
        cases,
        18,
        "节点命中优先级（只测 node>edge）",
        "pass" if ok else "fail",
        "when node and edge both hit, node should win",
        {"hit": hit, "params": core_params},
    )

    edge_only_graph = {
        "nodes": [
            {"id": "a", "x": 0.0, "y": 0.0, "r": 4.0},
            {"id": "b", "x": 100.0, "y": 0.0, "r": 4.0},
        ],
        "edges": [{"id": "e_ab", "src": "a", "dst": "b"}],
    }

    # 19: edge hit radius threshold
    p19_params = {"node_radius_px": 0.0, "edge_radius_px": 5.0, "node_priority": True, "distance_metric": "pixel_to_world"}
    near = ic.hit_test(edge_only_graph, {"x": 50.0, "y": 4.0}, 1.0, p19_params)
    mid = ic.hit_test(edge_only_graph, {"x": 50.0, "y": 5.0}, 1.0, p19_params)
    far = ic.hit_test(edge_only_graph, {"x": 50.0, "y": 6.0}, 1.0, p19_params)
    ok = near.get("kind") == "edge" and mid.get("kind") == "edge" and far.get("kind") == "none"
    record_case(
        cases,
        19,
        "边命中半径（只测 edge hitbox）",
        "pass" if ok else "fail",
        "edge hit should be inside/at threshold and miss outside threshold",
        {"near": near, "mid": mid, "far": far, "params": p19_params},
    )

    # 20: scale-dependent hit rule consistency (pixel_to_world metric)
    p20_params = {"node_radius_px": 0.0, "edge_radius_px": 4.0, "node_priority": True, "distance_metric": "pixel_to_world"}
    at_scale_1 = ic.hit_test(edge_only_graph, {"x": 50.0, "y": 3.0}, 1.0, p20_params)
    at_scale_2 = ic.hit_test(edge_only_graph, {"x": 50.0, "y": 3.0}, 2.0, p20_params)
    ok = at_scale_1.get("kind") == "edge" and at_scale_2.get("kind") == "none"
    record_case(
        cases,
        20,
        "缩放后命中一致（只测 hitbox 随 scale）",
        "pass" if ok else "fail",
        "pixel_to_world rule: higher scale shrinks world-space hit radius",
        {"scale_1": at_scale_1, "scale_2": at_scale_2, "params": p20_params},
    )

    # 22-27: SimLab core suite (zero-dependency replay scenarios)
    simlab_cmd, simlab_summary = run_simlab_suite(repo)
    simlab_scenarios = []
    if simlab_summary and isinstance(simlab_summary.get("scenarios"), list):
        simlab_scenarios = simlab_summary["scenarios"]
    by_sid: dict[str, dict[str, Any]] = {
        str(s.get("id")): s
        for s in simlab_scenarios
        if isinstance(s, dict) and s.get("id")
    }
    simlab_map = [
        (22, "S01_init_task", "SimLab S01 init task"),
        (23, "S02_doc_first_gate", "SimLab S02 doc-first gate"),
        (24, "S03_doc_index_check", "SimLab S03 doc index check"),
        (25, "S04_assistant_force", "SimLab S04 orchestrator new-run"),
        (26, "S05_run_artifacts", "SimLab S05 run artifacts"),
        (27, "S06_failure_bundle", "SimLab S06 failure bundle"),
    ]
    for cid, sid, title in simlab_map:
        scen = by_sid.get(sid)
        if scen is None:
            status = "fail"
            evidence = {
                "reason": f"missing scenario result: {sid}",
                "simlab_cmd_rc": simlab_cmd.rc,
                "simlab_stdout_tail": simlab_cmd.stdout[-1200:],
                "simlab_stderr_tail": simlab_cmd.stderr[-1200:],
                "simlab_summary_path": SIMLAB_SUMMARY_JSON.as_posix(),
            }
        else:
            sstatus = str(scen.get("status", "fail"))
            status = "pass" if sstatus == "pass" else "fail"
            evidence = {
                "scenario_id": sid,
                "status": sstatus,
                "trace": scen.get("trace", ""),
                "bundle": scen.get("bundle", ""),
                "run_dir": simlab_summary.get("run_dir", "") if simlab_summary else "",
                "simlab_summary_path": SIMLAB_SUMMARY_JSON.as_posix(),
            }
        record_case(
            cases,
            cid,
            title,
            status,
            f"{sid} should pass in headless environment",
            evidence,
        )

    # 21
    with preserve_files(repo, ["_tmp_patch.py", "patch_debug.txt", "docs/matrix_tmp.bak", "dist/clean_repo_matrix.zip"]):
        (repo / "_tmp_patch.py").write_text("print('tmp')\n", encoding="utf-8")
        (repo / "patch_debug.txt").write_text("debug\n", encoding="utf-8")
        (repo / "docs/matrix_tmp.bak").write_text("bak\n", encoding="utf-8")
        out = run_cmd(["python", "tools/make_clean_zip.py", "--out", "dist/clean_repo_matrix.zip"], repo)
        zpath = repo / "dist/clean_repo_matrix.zip"
        names: list[str] = []
        contains_bad = False
        if zpath.exists():
            with zipfile.ZipFile(zpath, "r") as zf:
                names = zf.namelist()
            contains_bad = any(
                n.endswith("_tmp_patch.py") or n.endswith("patch_debug.txt") or n.endswith(".bak")
                for n in names
            )
        ok = out.rc == 0 and zpath.exists() and not contains_bad
        record_case(cases, 21, "clean zip 不包含临时文件", "pass" if ok else "fail",
                    "zip should exclude _tmp_patch.py/patch_debug.txt/*.bak",
                    {"rc": out.rc, "stdout": out.stdout[-800:], "stderr": out.stderr[-400:], "zip_exists": zpath.exists(), "contains_bad": contains_bad})

    return cases


def render_reports(cases: list[dict[str, Any]], preflight: dict[str, Any]) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    total = len(cases)
    passed = sum(1 for c in cases if c["status"] == "pass")
    failed = sum(1 for c in cases if c["status"] == "fail")
    skipped = sum(1 for c in cases if c["status"] == "skip")
    executed = passed + failed

    summary = {
        "suite": f"gate-matrix-{total}",
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "pass_rate": 0 if executed == 0 else round(passed / executed, 4),
        "preflight": preflight,
        "cases": cases,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# ISSUE REPORT (Detailed)",
        "",
        f"- Generated at: {summary['generated_at']}",
        f"- Total: {total}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        f"- Skipped: {skipped}",
        "",
        "## Preflight",
        "```json",
        json.dumps(preflight, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Case Results",
    ]
    for c in cases:
        lines.extend(
            [
                "",
                f"### T{c['id']:02d} {c['name']}",
                f"- Status: **{c['status']}**",
                f"- Expectation: {c['expectation']}",
                "- Evidence:",
                "```json",
                json.dumps(c["evidence"], ensure_ascii=False, indent=2),
                "```",
            ]
        )
    DETAILED_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    diag = [
        "# ISSUE DIAGNOSIS",
        "",
        f"- Generated at: {summary['generated_at']}",
        "",
        "## Key Findings",
        f"- Pass: {passed}",
        f"- Fail: {failed}",
        f"- Skip: {skipped}",
        "",
        "## Failed Cases",
    ]
    failed_cases = [c for c in cases if c["status"] == "fail"]
    if not failed_cases:
        diag.append("- None")
    else:
        for c in failed_cases:
            diag.append(f"- T{c['id']:02d} {c['name']}")
    diag.extend(["", "## Skipped Cases"])
    skipped_cases = [c for c in cases if c["status"] == "skip"]
    if not skipped_cases:
        diag.append("- None")
    else:
        for c in skipped_cases:
            reason = c["evidence"].get("reason", "")
            diag.append(f"- T{c['id']:02d} {c['name']} — {reason}")
    DIAG_REPORT.write_text("\n".join(diag) + "\n", encoding="utf-8")


def main() -> int:
    print(f"[gate_matrix] preparing sandbox: {SANDBOX}")
    sandbox = copy_repo_for_sandbox(SANDBOX)
    git_init_clean_repo(sandbox)
    preflight = detect_preflight(sandbox)
    print("[gate_matrix] running matrix cases...")
    cases = run_matrix(sandbox, preflight)
    render_reports(cases, preflight)
    print(f"[gate_matrix] wrote: {DETAILED_REPORT}")
    print(f"[gate_matrix] wrote: {DIAG_REPORT}")
    print(f"[gate_matrix] wrote: {SUMMARY_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
