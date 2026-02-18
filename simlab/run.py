#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from simlab.assertions import ensure_excludes, ensure_includes, read_text
    from simlab.schema import validate_scenario
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from simlab.assertions import ensure_excludes, ensure_includes, read_text
    from simlab.schema import validate_scenario

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_DIR = ROOT / "simlab" / "scenarios"
DEFAULT_RUNS_ROOT = ROOT / "simlab" / "_runs"


@dataclass
class CmdResult:
    rc: int
    stdout: str
    stderr: str
    cmd: str


def run_cmd(cmd: str, cwd: Path) -> CmdResult:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    return CmdResult(rc=proc.returncode, stdout=proc.stdout, stderr=proc.stderr, cmd=cmd)


def _on_rm_error(func, path, exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
    except OSError:
        pass
    func(path)


def copy_repo(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst, onerror=_on_rm_error)

    def ignore(dir_path: str, names: list[str]) -> set[str]:
        rel = Path(dir_path).resolve().relative_to(src.resolve())
        ignored: set[str] = set()
        for name in names:
            child = (rel / name).as_posix()
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
            if child.startswith("tests/fixtures/adlc_forge_full_bundle/runs/"):
                ignored.add(name)
                continue
            if child.startswith("simlab/_runs/"):
                ignored.add(name)
                continue
        return ignored

    shutil.copytree(src, dst, ignore=ignore)


def git_baseline(repo: Path) -> None:
    run_cmd("git init", repo)
    run_cmd("git config user.email simlab@example.local", repo)
    run_cmd("git config user.name simlab-runner", repo)
    run_cmd("git add -A", repo)
    run_cmd("git commit -m baseline", repo)


def parse_doc(path: Path) -> dict[str, Any]:
    txt = path.read_text(encoding="utf-8")
    try:
        doc = json.loads(txt)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                f"failed to parse {path} as JSON; PyYAML not available for YAML parsing"
            ) from exc
        doc = yaml.safe_load(txt)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: top level must be object")
    validate_scenario(doc, path.as_posix())
    return doc


class ScenarioRunner:
    def __init__(self, doc: dict[str, Any], run_root: Path):
        self.doc = doc
        self.id = str(doc["id"])
        self.name = str(doc["name"])
        self.suite = str(doc.get("suite", "core"))
        self.scenario_dir = run_root / self.id
        self.sandbox = self.scenario_dir / "sandbox"
        self.logs_dir = self.scenario_dir / "logs"
        self.artifacts_dir = self.scenario_dir / "artifacts"
        self.trace_path = self.scenario_dir / "TRACE.md"
        self.bundle_path = self.scenario_dir / "failure_bundle.zip"
        self.diff_path = self.scenario_dir / "diff.patch"
        self.trace_lines: list[str] = []
        self.snapshots: set[str] = set()
        self.failed = False
        self.failure_reason = ""
        self.step_records: list[dict[str, Any]] = []

    def setup(self) -> None:
        self.scenario_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        copy_repo(ROOT, self.sandbox)
        git_baseline(self.sandbox)
        self.trace_lines = [
            f"# SimLab Trace — {self.id}",
            "",
            f"- Name: {self.name}",
            f"- Started: {dt.datetime.now().isoformat(timespec='seconds')}",
            f"- Sandbox: `{self.sandbox.as_posix()}`",
            "",
            "## Steps",
        ]

    def write_trace(self) -> None:
        self.trace_path.write_text("\n".join(self.trace_lines) + "\n", encoding="utf-8")

    def _bundle(self, reason: str) -> None:
        if self.bundle_path.exists():
            return
        self.failure_reason = reason
        self.trace_lines.append("")
        self.trace_lines.append(f"## Failure")
        self.trace_lines.append(f"- Reason: {reason}")
        self.write_trace()

        diff = run_cmd("git diff", self.sandbox)
        self.diff_path.write_text(diff.stdout + diff.stderr, encoding="utf-8")

        for rel in sorted(self.snapshots):
            src = self.sandbox / rel
            if not src.exists() or src.is_dir():
                continue
            dst = self.artifacts_dir / "snapshots" / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

        with zipfile.ZipFile(self.bundle_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in [self.trace_path, self.diff_path]:
                if p.exists():
                    zf.write(p, p.relative_to(self.scenario_dir).as_posix())
            for p in self.logs_dir.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(self.scenario_dir).as_posix())
            for p in self.artifacts_dir.rglob("*"):
                if p.is_file():
                    zf.write(p, p.relative_to(self.scenario_dir).as_posix())

    def _step_run(self, payload: dict[str, Any], idx: int) -> None:
        cmd = str(payload["cmd"])
        cwd_rel = str(payload.get("cwd", "."))
        cwd = self.sandbox / cwd_rel
        expected = payload.get("expect_exit", 0)
        includes = [str(x) for x in payload.get("expect_output_includes", [])]
        bundle_on_nonzero = bool(payload.get("bundle_on_nonzero", False))

        res = run_cmd(cmd, cwd)
        log_prefix = self.logs_dir / f"step_{idx:02d}"
        (log_prefix.with_suffix(".stdout.txt")).write_text(res.stdout, encoding="utf-8")
        (log_prefix.with_suffix(".stderr.txt")).write_text(res.stderr, encoding="utf-8")
        combo = res.stdout + "\n" + res.stderr

        if expected == "nonzero":
            rc_ok = res.rc != 0
        else:
            rc_ok = res.rc == int(expected)
        inc_ok, inc_msg = ensure_includes(combo, includes)

        if bundle_on_nonzero and res.rc != 0:
            self._bundle(f"bundle_on_nonzero: command exited {res.rc}")

        self.step_records.append(
            {
                "type": "run",
                "cmd": cmd,
                "cwd": cwd_rel,
                "rc": res.rc,
                "expect_exit": expected,
                "stdout_tail": res.stdout[-1200:],
                "stderr_tail": res.stderr[-1200:],
            }
        )
        self.trace_lines.extend(
            [
                "",
                f"### Step {idx} run",
                f"- cmd: `{cmd}`",
                f"- cwd: `{cwd_rel}`",
                f"- rc: `{res.rc}`",
                f"- expect_exit: `{expected}`",
            ]
        )
        if not rc_ok:
            raise RuntimeError(f"step {idx}: expect_exit mismatch, rc={res.rc}, expect={expected}")
        if not inc_ok:
            raise RuntimeError(f"step {idx}: output assertion failed: {inc_msg}")

    def _step_write(self, payload: dict[str, Any], idx: int) -> None:
        rel = str(payload["path"])
        mode = str(payload.get("mode", "overwrite"))
        content = str(payload.get("content", ""))
        path = self.sandbox / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append":
            with path.open("a", encoding="utf-8") as f:
                f.write(content)
        else:
            path.write_text(content, encoding="utf-8")
        self.snapshots.add(rel)
        self.step_records.append({"type": "write", "path": rel, "mode": mode, "bytes": len(content.encode("utf-8"))})
        self.trace_lines.extend(["", f"### Step {idx} write", f"- path: `{rel}`", f"- mode: `{mode}`"])

    def _step_expect_path(self, payload: dict[str, Any], idx: int) -> None:
        rel = str(payload["path"])
        want_exists = bool(payload.get("exists", True))
        p = self.sandbox / rel
        got = p.exists()
        self.snapshots.add(rel)
        self.step_records.append({"type": "expect_path", "path": rel, "exists": got, "expect": want_exists})
        self.trace_lines.extend(["", f"### Step {idx} expect_path", f"- path: `{rel}`", f"- exists: `{got}`"])
        if got != want_exists:
            raise RuntimeError(f"step {idx}: path existence mismatch for {rel}: got={got}, expect={want_exists}")

    def _step_expect_text(self, payload: dict[str, Any], idx: int) -> None:
        rel = str(payload["path"])
        includes = [str(x) for x in payload.get("includes", [])]
        excludes = [str(x) for x in payload.get("excludes", [])]
        p = self.sandbox / rel
        if not p.exists():
            raise RuntimeError(f"step {idx}: file not found for expect_text: {rel}")
        txt = read_text(p)
        inc_ok, inc_msg = ensure_includes(txt, includes)
        exc_ok, exc_msg = ensure_excludes(txt, excludes)
        self.snapshots.add(rel)
        self.step_records.append(
            {"type": "expect_text", "path": rel, "includes": includes, "excludes": excludes, "size": len(txt)}
        )
        self.trace_lines.extend(["", f"### Step {idx} expect_text", f"- path: `{rel}`", f"- size: `{len(txt)}`"])
        if not inc_ok:
            raise RuntimeError(f"step {idx}: include assertion failed: {inc_msg}")
        if not exc_ok:
            raise RuntimeError(f"step {idx}: exclude assertion failed: {exc_msg}")

    def _step_expect_bundle(self, payload: dict[str, Any], idx: int) -> None:
        want = bool(payload.get("exists", True))
        got = self.bundle_path.exists()
        self.step_records.append({"type": "expect_bundle", "exists": got, "expect": want, "path": self.bundle_path.as_posix()})
        self.trace_lines.extend(["", f"### Step {idx} expect_bundle", f"- path: `{self.bundle_path.as_posix()}`", f"- exists: `{got}`"])
        if got != want:
            raise RuntimeError(f"step {idx}: failure bundle existence mismatch: got={got}, expect={want}")

    def run(self) -> dict[str, Any]:
        self.setup()
        try:
            for idx, step in enumerate(self.doc["steps"], start=1):
                if "run" in step:
                    self._step_run(step["run"], idx)
                elif "write" in step:
                    self._step_write(step["write"], idx)
                elif "expect_path" in step:
                    self._step_expect_path(step["expect_path"], idx)
                elif "expect_text" in step:
                    self._step_expect_text(step["expect_text"], idx)
                elif "expect_bundle" in step:
                    self._step_expect_bundle(step["expect_bundle"], idx)
                else:
                    raise RuntimeError(f"step {idx}: unsupported type")
        except Exception as exc:
            self.failed = True
            self._bundle(str(exc))
            self.trace_lines.append("")
            self.trace_lines.append("## Result")
            self.trace_lines.append("- status: fail")
            self.trace_lines.append(f"- error: {exc}")
            self.write_trace()
            return {
                "id": self.id,
                "name": self.name,
                "suite": self.suite,
                "status": "fail",
                "error": str(exc),
                "trace": self.trace_path.as_posix(),
                "bundle": self.bundle_path.as_posix() if self.bundle_path.exists() else "",
                "steps": self.step_records,
            }

        self.trace_lines.append("")
        self.trace_lines.append("## Result")
        self.trace_lines.append("- status: pass")
        self.write_trace()
        return {
            "id": self.id,
            "name": self.name,
            "suite": self.suite,
            "status": "pass",
            "trace": self.trace_path.as_posix(),
            "bundle": self.bundle_path.as_posix() if self.bundle_path.exists() else "",
            "steps": self.step_records,
        }


def load_scenarios(suite: str) -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    for p in sorted(SCENARIOS_DIR.glob("*.yaml")):
        doc = parse_doc(p)
        if suite != "all" and str(doc.get("suite", "core")) != suite:
            continue
        docs.append(doc)
    return docs


def main() -> int:
    ap = argparse.ArgumentParser(description="SimLab scene replay runner")
    ap.add_argument("--suite", default="all", choices=["all", "lite", "core", "integration"])
    ap.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    ap.add_argument("--json-out", default="")
    args = ap.parse_args()

    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    runs_root = Path(args.runs_root).resolve()
    runs_root.mkdir(parents=True, exist_ok=True)
    run_root = runs_root / run_id
    run_root.mkdir(parents=True, exist_ok=True)

    scenarios = load_scenarios(args.suite)
    results: list[dict[str, Any]] = []
    for doc in scenarios:
        runner = ScenarioRunner(doc, run_root)
        res = runner.run()
        results.append(res)

    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    summary = {
        "run_id": run_id,
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "suite": args.suite,
        "runs_root": runs_root.as_posix(),
        "run_dir": run_root.as_posix(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "scenarios": results,
    }
    summary_path = run_root / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run_dir": run_root.as_posix(), "passed": passed, "failed": failed}, ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
