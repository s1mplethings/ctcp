#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_cmd(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return p.returncode, p.stdout, p.stderr


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def collect_diff(root: Path) -> str:
    rc, out, err = run_cmd(["git", "diff"], root)
    _ = rc
    return out + err


def make_bundle(run_dir: Path) -> Path:
    bundle = run_dir / "failure_bundle.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in run_dir.rglob("*"):
            if p.is_file() and p != bundle:
                zf.write(p, p.relative_to(run_dir).as_posix())
    return bundle


def main() -> int:
    ap = argparse.ArgumentParser(description="Headless ADLC runner (doc->plan->patch->verify->bundle).")
    ap.add_argument("--goal", default="headless-lite")
    ap.add_argument("--verify-cmd", default="")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    run_id = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = ROOT / "meta" / "runs" / f"{run_id}-adlc-headless"
    artifacts_dir = run_dir / "artifacts"
    logs_dir = run_dir / "logs"
    trace_path = run_dir / "TRACE.md"
    write_text(
        trace_path,
        "\n".join(
            [
                f"# ADLC Run Trace — {run_id}",
                "",
                f"- Goal: {args.goal}",
                "- Pipeline: doc -> plan -> patch -> verify -> bundle",
                "",
                "## Steps",
            ]
        )
        + "\n",
    )

    def append_trace(lines: list[str]) -> None:
        with trace_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    # doc / plan
    cmd1 = ["python", "tools/ctcp_assistant.py", "init-task", args.goal]
    if args.force or (ROOT / "meta" / "tasks" / "CURRENT.md").exists():
        cmd1.append("--force")
    rc1, out1, err1 = run_cmd(cmd1, ROOT)
    write_text(logs_dir / "01_init_task.stdout.log", out1)
    write_text(logs_dir / "01_init_task.stderr.log", err1)
    append_trace(
        [
            "",
            "### 1) plan",
            f"- cmd: `{' '.join(cmd1)}`",
            f"- rc: `{rc1}`",
        ]
    )
    if rc1 != 0:
        write_text(run_dir / "diff.patch", collect_diff(ROOT))
        bundle = make_bundle(run_dir)
        append_trace(["", "## Result", f"- status: fail", f"- bundle: `{bundle.as_posix()}`"])
        return 1

    # analysis
    analysis_path = artifacts_dir / "analysis.md"
    write_text(
        analysis_path,
        "\n".join(
            [
                "# Analysis",
                "",
                f"- Goal: {args.goal}",
                "- Constraints: default headless, minimal patch, evidence required",
                "- Risk: verify may fail due to gate or environment drift",
            ]
        )
        + "\n",
    )
    append_trace(["", "### 2) analysis", f"- file: `{analysis_path.as_posix()}`", "- rc: `0`"])

    # find (resolver)
    find_path = artifacts_dir / "find_result.json"
    cmd_find = ["python", "scripts/resolve_workflow.py", "--goal", args.goal, "--out", str(find_path)]
    rc_find, out_find, err_find = run_cmd(cmd_find, ROOT)
    write_text(logs_dir / "02_find.stdout.log", out_find)
    write_text(logs_dir / "02_find.stderr.log", err_find)
    append_trace(["", "### 3) find", f"- cmd: `{' '.join(cmd_find)}`", f"- rc: `{rc_find}`"])
    if rc_find != 0:
        write_text(run_dir / "diff.patch", collect_diff(ROOT))
        bundle = make_bundle(run_dir)
        append_trace(["", "## Result", f"- status: fail", f"- bundle: `{bundle.as_posix()}`"])
        return 1

    find_doc = json.loads(find_path.read_text(encoding="utf-8"))

    # plan
    plan_path = artifacts_dir / "PLAN.md"
    write_text(
        plan_path,
        "\n".join(
            [
                "# PLAN",
                "",
                f"- Workflow: {find_doc.get('selected_workflow_id')}@{find_doc.get('selected_version')}",
                "- Steps: doc -> analysis -> find -> plan -> verify -> bundle",
                "- Gate: lite verify_repo + simlab lite",
                "- Allowed paths: docs/meta/scripts/simlab/workflow_registry",
            ]
        )
        + "\n",
    )
    append_trace(["", "### 4) plan", f"- file: `{plan_path.as_posix()}`", "- rc: `0`"])

    # patch (placeholder no-op for now)
    patch_note = artifacts_dir / "PATCH_PLAN.md"
    write_text(
        patch_note,
        "# Patch Stage\n\n- This minimal runner keeps patch stage as no-op placeholder for now.\n",
    )
    append_trace(
        [
            "",
            "### 5) patch",
            f"- file: `{patch_note.as_posix()}`",
            "- status: no-op placeholder",
        ]
    )

    # verify
    if args.verify_cmd.strip():
        verify_cmd = args.verify_cmd.split()
    else:
        verify_cmd = ["python", "simlab/run.py", "--suite", "lite"]
    rc2, out2, err2 = run_cmd(verify_cmd, ROOT)
    write_text(logs_dir / "03_verify.stdout.log", out2)
    write_text(logs_dir / "03_verify.stderr.log", err2)
    verify_report = artifacts_dir / "verify_report.md"
    write_text(
        verify_report,
        "\n".join(
            [
                "# Verify Report",
                "",
                f"- cmd: `{' '.join(verify_cmd)}`",
                f"- rc: `{rc2}`",
                "",
                "## stdout (tail)",
                "```",
                out2[-1000:],
                "```",
                "",
                "## stderr (tail)",
                "```",
                err2[-1000:],
                "```",
            ]
        )
        + "\n",
    )
    append_trace(
        [
            "",
            "### 6) verify",
            f"- cmd: `{' '.join(verify_cmd)}`",
            f"- rc: `{rc2}`",
            f"- report: `{verify_report.as_posix()}`",
        ]
    )
    if rc2 != 0:
        write_text(run_dir / "diff.patch", collect_diff(ROOT))
        bundle = make_bundle(run_dir)
        append_trace(["", "## Result", f"- status: fail", f"- bundle: `{bundle.as_posix()}`"])
        return 1

    append_trace(["", "## Result", "- status: pass"])
    write_text(
        run_dir / "RUN.json",
        json.dumps(
            {
                "run_id": run_id,
                "goal": args.goal,
                "result": "PASS",
                "trace": trace_path.as_posix(),
            },
            ensure_ascii=False,
            indent=2,
        ),
    )
    print(f"[adlc_run] run_dir={run_dir.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
