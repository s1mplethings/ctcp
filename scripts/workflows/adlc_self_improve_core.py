#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

try:
    from tools import contract_guard, contrast_rules, local_librarian, run_state
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools import contract_guard, contrast_rules, local_librarian, run_state

PATCH_START_RE = re.compile(r"^diff --git .*$", re.M)


def _run(
    cmd: list[str] | str,
    *,
    cwd: Path,
    shell: bool = False,
) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=shell,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _extract_patch(text: str) -> str:
    match = PATCH_START_RE.search(text or "")
    if not match:
        return ""
    return text[match.start() :].strip() + "\n"


def _summarize_file(path: Path, max_lines: int = 10) -> str:
    if not path.exists():
        return f"- `{path.as_posix()}`: missing"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    picked = lines[:max_lines]
    summary = "\n".join(f"  {line}" for line in picked)
    return f"- `{path.as_posix()}`:\n{summary}"


def _write_analysis(repo_root: Path, out_path: Path, goal: str) -> None:
    readlist = [
        repo_root / "README.md",
        repo_root / "docs" / "03_quality_gates.md",
        repo_root / "docs" / "SELF_CHECK_SYSTEM.md",
        repo_root / "ai_context" / "00_AI_CONTRACT.md",
    ]
    lines = [
        "# Analysis",
        "",
        f"- Goal: {goal}",
        "- Flow: doc -> analysis -> find -> plan -> build -> verify -> contrast -> fix -> stop",
        "",
        "## Read Summary",
    ]
    for path in readlist:
        lines.append(_summarize_file(path))
    lines.append("")
    _write(out_path, "\n".join(lines))


def _write_context(
    *,
    out_path: Path,
    goal: str,
    references: list[dict[str, Any]],
) -> None:
    lines = [
        "# Context Evidence",
        "",
        f"- query: `{goal}`",
        "",
    ]
    if not references:
        lines += ["- No references found by Local Librarian.", ""]
    else:
        for idx, row in enumerate(references, start=1):
            path = str(row.get("path", ""))
            start_line = int(row.get("start_line", 0) or 0)
            end_line = int(row.get("end_line", 0) or 0)
            snippet = str(row.get("snippet", "")).strip()
            lines += [
                f"## Ref {idx}",
                f"- path: `{path}`",
                f"- lines: `{start_line}-{end_line}`",
                "```text",
                snippet,
                "```",
                "",
            ]
    _write(out_path, "\n".join(lines))


def _write_plan(
    *,
    out_path: Path,
    goal: str,
    current_round: int,
    references: list[dict[str, Any]],
) -> None:
    candidate_files: list[str] = []
    for row in references:
        path = str(row.get("path", "")).strip()
        if path and path not in candidate_files:
            candidate_files.append(path)
        if len(candidate_files) >= 3:
            break

    while len(candidate_files) < 3:
        fallback = [
            "scripts/workflows/adlc_self_improve_core.py",
            "tools/contrast_rules.py",
            "tools/contract_guard.py",
        ][len(candidate_files)]
        if fallback not in candidate_files:
            candidate_files.append(fallback)

    lines = [
        "# PLAN",
        "",
        f"- Goal: {goal}",
        f"- Round: {current_round}",
        "- Task limit: <= 5",
        "- File change limit: <= 3 files",
        "",
        "## Tasks",
        "1. Confirm failure class from latest verify logs.",
        "2. Use Local Librarian references to scope one minimal fix.",
        "3. Generate unified diff patch with evidence references.",
        "4. Run contract guard before/after patch apply.",
        "5. Run verify_repo and update fix brief if failed.",
        "",
        "## Candidate Files (max 3)",
    ]
    for path in candidate_files[:3]:
        lines.append(f"- `{path}`")

    lines += [
        "",
        "## Acceptance Commands",
        "- `python -m unittest discover -s tests -p \"test_*.py\"`",
        "- `powershell -ExecutionPolicy Bypass -File scripts/verify_repo.ps1` (Windows)",
        "- `bash scripts/verify_repo.sh` (Linux/macOS)",
        "",
    ]
    _write(out_path, "\n".join(lines))


def _verify_command(repo_root: Path, override: str) -> list[str]:
    if override.strip():
        if os.name == "nt":
            return shlex.split(override, posix=False)
        return shlex.split(override)
    if os.name == "nt":
        return ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(repo_root / "scripts" / "verify_repo.ps1")]
    return ["bash", str(repo_root / "scripts" / "verify_repo.sh")]


def _query_for_label(label: str, goal: str) -> str:
    mapping = {
        "DOC_FAIL": "sync_doc_links.py",
        "CONTRACT_FAIL": "contract_checks.py",
        "SIMLAB_FAIL": "simlab",
        "PY_IMPORT_FAIL": "import",
    }
    return mapping.get(label, goal)


def _save_state(state_path_root: Path, state: dict[str, Any], **updates: Any) -> dict[str, Any]:
    for key, value in updates.items():
        if key == "artifacts" and isinstance(value, dict):
            artifacts = state.get("artifacts", {})
            if not isinstance(artifacts, dict):
                artifacts = {}
            artifacts.update(value)
            state["artifacts"] = artifacts
        elif key == "last_verify" and isinstance(value, dict):
            state["last_verify"] = value
        elif value is not None:
            state[key] = value
    return run_state.save_state(state_path_root, state)


def _generate_patch_via_cmd(
    *,
    repo_root: Path,
    run_dir: Path,
    patch_cmd_tpl: str,
    plan_path: Path,
    context_path: Path,
) -> str:
    prompt_path = run_dir / "outbox" / "PATCH_PROMPT.md"
    prompt = "\n".join(
        [
            "# Patch Request",
            "",
            "Generate a unified diff patch only.",
            "The output must start with `diff --git`.",
            "",
            f"PLAN: {plan_path.as_posix()}",
            f"CONTEXT: {context_path.as_posix()}",
        ]
    )
    _write(prompt_path, prompt)
    cmd = patch_cmd_tpl.format(
        PROMPT_PATH=str(prompt_path),
        PLAN_PATH=str(plan_path),
        CONTEXT_PATH=str(context_path),
        REPO_ROOT=str(repo_root),
    )
    rc, out, err = _run(cmd, cwd=repo_root, shell=True)
    _write(run_dir / "logs" / "patch_cmd.stdout.txt", out)
    _write(run_dir / "logs" / "patch_cmd.stderr.txt", err)
    if rc != 0:
        return ""
    return _extract_patch(out)


def _diff_text(repo_root: Path) -> str:
    _, out, err = _run(["git", "diff"], cwd=repo_root)
    return (out or "") + (err or "")


def _mechanical_patch(repo_root: Path, run_dir: Path, label: str) -> str:
    if label == "DOC_FAIL":
        rc, out, err = _run([sys.executable, str(repo_root / "scripts" / "sync_doc_links.py")], cwd=repo_root)
        _write(run_dir / "logs" / "mechanical_patch.stdout.txt", out)
        _write(run_dir / "logs" / "mechanical_patch.stderr.txt", err)
        if rc != 0:
            return ""
        return _diff_text(repo_root)
    return _diff_text(repo_root)


def _apply_patch_if_any(repo_root: Path, patch_path: Path, run_dir: Path) -> tuple[bool, str]:
    patch_text = patch_path.read_text(encoding="utf-8", errors="replace")
    if not patch_text.strip():
        return True, "empty patch; apply skipped"
    rc, out, err = _run(["git", "apply", str(patch_path)], cwd=repo_root)
    _write(run_dir / "logs" / "patch_apply.stdout.txt", out)
    _write(run_dir / "logs" / "patch_apply.stderr.txt", err)
    if rc != 0:
        return False, "git apply failed"
    return True, "ok"


def _rollback_patch(repo_root: Path, patch_path: Path, run_dir: Path) -> None:
    rc, out, err = _run(["git", "apply", "-R", str(patch_path)], cwd=repo_root)
    _write(run_dir / "logs" / "patch_rollback.stdout.txt", out)
    _write(run_dir / "logs" / "patch_rollback.stderr.txt", err)
    if rc != 0:
        _write(
            run_dir / "logs" / "patch_rollback.note.txt",
            "Rollback failed. Manual cleanup may be required.\n",
        )


def run_workflow(
    *,
    repo_root: Path,
    goal: str,
    max_rounds: int,
    run_id: str,
    patch_cmd_tpl: str,
    verify_cmd: str,
) -> int:
    run_dir = repo_root / "runs" / "adlc_self_improve_core" / run_id
    outbox_dir = run_dir / "outbox"
    reviews_dir = run_dir / "reviews"
    logs_dir = run_dir / "logs"
    for path in (outbox_dir, reviews_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    state = run_state.load_state(run_dir)
    state["run_id"] = run_id
    state = _save_state(
        run_dir,
        state,
        phase="doc",
        artifacts={"run_dir": str(run_dir.relative_to(repo_root).as_posix())},
    )

    analysis_path = outbox_dir / "analysis.md"
    _write_analysis(repo_root, analysis_path, goal)
    state = _save_state(
        run_dir,
        state,
        phase="analysis",
        artifacts={"analysis": str(analysis_path.relative_to(run_dir).as_posix())},
    )

    next_query = goal
    start_round = int(state.get("round", 1) or 1)
    for current_round in range(start_round, max_rounds + 1):
        state = _save_state(run_dir, state, phase="find", round=current_round)
        references = local_librarian.search(repo_root=repo_root, query=next_query, k=8)
        context_path = outbox_dir / "CONTEXT.md"
        _write_context(out_path=context_path, goal=next_query, references=references)
        state = _save_state(
            run_dir,
            state,
            artifacts={
                "context": str(context_path.relative_to(run_dir).as_posix()),
            },
        )

        state = _save_state(run_dir, state, phase="plan")
        plan_path = outbox_dir / "PLAN.md"
        _write_plan(
            out_path=plan_path,
            goal=goal,
            current_round=current_round,
            references=references,
        )
        state = _save_state(
            run_dir,
            state,
            artifacts={"plan": str(plan_path.relative_to(run_dir).as_posix())},
        )

        state = _save_state(run_dir, state, phase="build")
        pre_review = contract_guard.evaluate(
            repo_root,
            policy_path=repo_root / "contracts" / "allowed_changes.yaml",
            out_path=reviews_dir / "contract_review.json",
        )
        if not bool(pre_review.get("contract_guard", {}).get("pass", False)):
            _append_jsonl(
                run_dir / "events.jsonl",
                {"event": "CONTRACT_FAIL_PRE", "round": current_round},
            )
            _save_state(
                run_dir,
                state,
                phase="stop",
                artifacts={"contract_review": "reviews/contract_review.json"},
            )
            return 2

        label_hint = str(state.get("last_verify", {}).get("label", "UNKNOWN"))
        patch_text = ""
        if patch_cmd_tpl.strip():
            patch_text = _generate_patch_via_cmd(
                repo_root=repo_root,
                run_dir=run_dir,
                patch_cmd_tpl=patch_cmd_tpl,
                plan_path=plan_path,
                context_path=context_path,
            )
        if not patch_text:
            patch_text = _mechanical_patch(repo_root=repo_root, run_dir=run_dir, label=label_hint)
        patch_path = run_dir / "diff.patch"
        _write(patch_path, patch_text)
        state = _save_state(
            run_dir,
            state,
            artifacts={"patch": str(patch_path.relative_to(run_dir).as_posix())},
        )

        ok_apply, apply_reason = _apply_patch_if_any(repo_root, patch_path, run_dir)
        if not ok_apply:
            _append_jsonl(
                run_dir / "events.jsonl",
                {"event": "PATCH_APPLY_FAIL", "round": current_round, "reason": apply_reason},
            )
            _save_state(run_dir, state, phase="stop")
            return 3

        post_review = contract_guard.evaluate(
            repo_root,
            policy_path=repo_root / "contracts" / "allowed_changes.yaml",
            out_path=reviews_dir / "contract_review.json",
        )
        if not bool(post_review.get("contract_guard", {}).get("pass", False)):
            _rollback_patch(repo_root, patch_path, run_dir)
            _append_jsonl(
                run_dir / "events.jsonl",
                {"event": "CONTRACT_FAIL_POST", "round": current_round},
            )
            _save_state(
                run_dir,
                state,
                phase="stop",
                artifacts={"contract_review": "reviews/contract_review.json"},
            )
            return 4

        state = _save_state(run_dir, state, phase="verify")
        cmd = _verify_command(repo_root, verify_cmd)
        rc, stdout, stderr = _run(cmd, cwd=repo_root)
        verify_stdout_path = logs_dir / "verify_stdout.txt"
        verify_stderr_path = logs_dir / "verify_stderr.txt"
        _write(verify_stdout_path, stdout)
        _write(verify_stderr_path, stderr)
        state = _save_state(
            run_dir,
            state,
            last_verify={
                "rc": rc,
                "paths": {
                    "stdout": str(verify_stdout_path.relative_to(run_dir).as_posix()),
                    "stderr": str(verify_stderr_path.relative_to(run_dir).as_posix()),
                },
                "summary": (stdout + "\n" + stderr)[-1200:],
            },
            artifacts={
                "verify_stdout": str(verify_stdout_path.relative_to(run_dir).as_posix()),
                "verify_stderr": str(verify_stderr_path.relative_to(run_dir).as_posix()),
                "contract_review": "reviews/contract_review.json",
            },
        )
        if rc == 0:
            _save_state(run_dir, state, phase="done")
            print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "status": "done"}, ensure_ascii=False))
            return 0

        state = _save_state(run_dir, state, phase="contrast")
        contrast = contrast_rules.classify_verify(rc=rc, stdout=stdout, stderr=stderr)
        label = str(contrast.get("label", "UNKNOWN"))
        next_query = _query_for_label(label, goal)
        fix_refs = local_librarian.search(repo_root=repo_root, query=next_query, k=6)
        fix_brief_path = outbox_dir / "fix_brief.md"
        contrast_rules.write_fix_brief(
            out_path=fix_brief_path,
            rc=rc,
            stdout=stdout,
            stderr=stderr,
            references=fix_refs,
        )
        _save_state(
            run_dir,
            state,
            phase="fix",
            last_verify={
                "rc": rc,
                "paths": {
                    "stdout": str(verify_stdout_path.relative_to(run_dir).as_posix()),
                    "stderr": str(verify_stderr_path.relative_to(run_dir).as_posix()),
                },
                "summary": (stdout + "\n" + stderr)[-1200:],
                "label": label,
            },
            artifacts={"fix_brief": str(fix_brief_path.relative_to(run_dir).as_posix())},
        )

    _save_state(run_dir, state, phase="stop", round=max_rounds)
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "status": "stop"}, ensure_ascii=False))
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="ADLC self improve core workflow")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--goal", required=True)
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--patch-cmd", default="")
    ap.add_argument("--verify-cmd", default="")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve()
    run_id = args.run_id.strip() or run_state.create_run_id()
    patch_cmd_tpl = (args.patch_cmd or os.environ.get("SDDAI_PATCH_CMD", "")).strip()
    return run_workflow(
        repo_root=repo_root,
        goal=str(args.goal),
        max_rounds=max(1, int(args.max_rounds)),
        run_id=run_id,
        patch_cmd_tpl=patch_cmd_tpl,
        verify_cmd=str(args.verify_cmd),
    )


if __name__ == "__main__":
    raise SystemExit(main())

