#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

try:
    from tools import contract_guard, contrast_rules, local_librarian, run_state
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from tools import contract_guard, contrast_rules, local_librarian, run_state

PATCH_START_RE = re.compile(r"^diff --git .*$", re.M)
NESTED_DIFF_ADDED_LINE_RE = re.compile(r"^\+diff --git .*$", re.M)
PATCH_META_PREFIXES = (
    "diff --git ",
    "index ",
    "new file mode ",
    "deleted file mode ",
    "old mode ",
    "new mode ",
    "similarity index ",
    "rename from ",
    "rename to ",
    "copy from ",
    "copy to ",
    "--- ",
    "+++ ",
    "@@",
    "Binary files ",
    "GIT binary patch",
    "literal ",
    "delta ",
    "\\ No newline at end of file",
)


def _parse_bool(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _run(
    cmd: list[str] | str,
    *,
    cwd: Path,
    shell: bool = False,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=shell,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _trace(run_dir: Path, message: str) -> None:
    trace_path = run_dir / "TRACE.md"
    stamp = datetime.now().isoformat(timespec="seconds")
    with trace_path.open("a", encoding="utf-8") as fh:
        fh.write(f"- [{stamp}] {message}\n")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _is_patch_line(line: str) -> bool:
    if not line:
        return False
    if line.startswith(PATCH_META_PREFIXES):
        return True
    first = line[0]
    return first in {"+", "-", " "}


def _sanitize_patch_block(lines: list[str]) -> list[str]:
    block = list(lines)
    while block and not _is_patch_line(block[-1]):
        block.pop()
    if not block:
        return []
    if not block[0].startswith("diff --git "):
        return []
    has_old = any(row.startswith("--- ") for row in block)
    has_new = any(row.startswith("+++ ") for row in block)
    if not (has_old and has_new):
        return []
    return block


def _has_nested_diff_added_lines(patch_text: str) -> bool:
    return bool(NESTED_DIFF_ADDED_LINE_RE.search(patch_text or ""))


def _extract_patch(text: str) -> str:
    lines = (text or "").splitlines()
    start = -1
    for idx, row in enumerate(lines):
        if row.startswith("diff --git "):
            start = idx
            break
    if start < 0:
        return ""

    blocks: list[list[str]] = []
    current: list[str] = []
    for row in lines[start:]:
        if row.startswith("diff --git "):
            if current:
                cleaned = _sanitize_patch_block(current)
                if cleaned:
                    blocks.append(cleaned)
            current = [row]
            continue
        current.append(row)
    if current:
        cleaned = _sanitize_patch_block(current)
        if cleaned:
            blocks.append(cleaned)

    if not blocks:
        return ""
    merged: list[str] = []
    for block in blocks:
        if merged:
            merged.append("")
        merged.extend(block)
    return "\n".join(merged).strip() + "\n"


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


def _write_constraints(out_path: Path, repo_root: Path) -> None:
    policy_path = repo_root / "contracts" / "allowed_changes.yaml"
    policy = contract_guard.load_policy(policy_path)
    allowed_paths = [str(x) for x in policy.get("allowed_paths", []) if str(x).strip()]
    blocked_paths = [str(x) for x in policy.get("blocked_paths", []) if str(x).strip()]
    max_files = int(policy.get("max_files", 10))
    max_added = int(policy.get("max_added_lines", 800))
    max_deleted = int(policy.get("max_deleted_lines", 800))
    max_total = int(policy.get("max_total_lines", 800))

    lines = [
        "# Constraints",
        "",
        f"- policy: `{policy_path.as_posix()}`",
        f"- max_files: `{max_files}`",
        f"- max_added_lines: `{max_added}`",
        f"- max_deleted_lines: `{max_deleted}`",
        f"- max_total_lines: `{max_total}`",
        "",
        "## Allowed Paths",
    ]
    if allowed_paths:
        for row in allowed_paths:
            lines.append(f"- `{row}`")
    else:
        lines.append("- (none specified)")

    lines += [
        "",
        "## Blocked Paths",
    ]
    if blocked_paths:
        for row in blocked_paths:
            lines.append(f"- `{row}`")
    else:
        lines.append("- (none specified)")
    lines.append("")
    _write(out_path, "\n".join(lines))


def _ensure_fix_brief_seed(path: Path, goal: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8", errors="replace").strip():
        return
    lines = [
        "# Fix Brief",
        "",
        "- label: `BOOTSTRAP`",
        "- verify_rc: `N/A`",
        "",
        "## Minimal Next Actions",
        "- Use CONTEXT + CONSTRAINTS to generate a minimal external PLAN.",
        "- Use external PATCH command to emit unified diff starting with `diff --git`.",
        "",
        "## Related File References",
        f"- goal: `{goal}`",
        "",
    ]
    _write(path, "\n".join(lines))


def _sync_fix_brief_alias(upper_path: Path, lower_path: Path) -> None:
    if not upper_path.exists():
        return
    _write(lower_path, upper_path.read_text(encoding="utf-8", errors="replace"))


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
        return [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo_root / "scripts" / "verify_repo.ps1"),
        ]
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


def _fail(
    *,
    run_dir: Path,
    state: dict[str, Any],
    phase: str,
    round_number: int,
    reason: str,
    code: int,
    event: str,
    artifacts: dict[str, Any] | None = None,
) -> int:
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    _write(logs_dir / "error.txt", reason.rstrip() + "\n")
    _trace(run_dir, f"[error] {reason}")
    _append_jsonl(run_dir / "events.jsonl", {"event": event, "round": round_number, "reason": reason})
    _save_state(
        run_dir,
        state,
        phase=phase,
        round=round_number,
        last_error=reason,
        artifacts=artifacts or {},
    )
    print(f"[adlc_self_improve_core][error] {reason}")
    return code


def _format_cmd(template: str, **kwargs: str) -> tuple[str, str]:
    try:
        return template.format(**kwargs), ""
    except Exception as exc:
        return "", f"command template formatting failed: {exc}"


def _generate_plan_via_cmd(
    *,
    repo_root: Path,
    run_dir: Path,
    plan_cmd_tpl: str,
    plan_path: Path,
    context_path: Path,
    constraints_path: Path,
    fix_brief_path: Path,
    goal: str,
    current_round: int,
) -> tuple[bool, str]:
    cmd, err = _format_cmd(
        plan_cmd_tpl,
        PLAN_PATH=str(plan_path),
        CONTEXT_PATH=str(context_path),
        CONSTRAINTS_PATH=str(constraints_path),
        FIX_BRIEF_PATH=str(fix_brief_path),
        GOAL=goal,
        ROUND=str(current_round),
        REPO_ROOT=str(repo_root),
    )
    if err:
        _write(run_dir / "logs" / "plan_cmd.stdout.txt", "")
        _write(run_dir / "logs" / "plan_cmd.stderr.txt", err + "\n")
        return False, err

    rc, out, stderr = _run(cmd, cwd=repo_root, shell=True)
    _write(run_dir / "logs" / "plan_cmd.stdout.txt", out)
    _write(run_dir / "logs" / "plan_cmd.stderr.txt", stderr)
    if rc != 0:
        return False, f"plan-cmd failed (exit={rc})"

    plan_text = out.strip()
    if not plan_text:
        return False, "plan-cmd produced empty stdout"
    _write(plan_path, plan_text + "\n")
    return True, "ok"


def _generate_patch_via_cmd(
    *,
    repo_root: Path,
    run_dir: Path,
    patch_cmd_tpl: str,
    plan_path: Path,
    context_path: Path,
    constraints_path: Path,
    fix_brief_path: Path,
    goal: str,
    current_round: int,
) -> tuple[str, str]:
    prompt_path = run_dir / "outbox" / "PATCH_PROMPT.md"
    prompt = "\n".join(
        [
            """SYSTEM CONTRACT (EN)

You are a patch-first coding agent. Follow these rules strictly:

Scope: Only make changes that are necessary to fulfill the user’s request. Do not refactor, rename, reformat, or change unrelated logic.

Minimality: Prefer the smallest verified change. Avoid touching files not required by the fix.

Output: Produce exactly ONE unified diff patch that is git apply compatible. No explanations, no extra text.

Verification: If the repository has an existing verification command (tests / lint / verify_repo / CI script), run or specify it in your plan. Do not add new dependencies.

If uncertain: Stop after producing a short PLAN in JSON (see below) and do NOT output a patch.

PLAN JSON schema (only when uncertain):
{
"goal": "...",
"assumptions": ["..."],
"files_to_change": ["..."],
"steps": ["..."],
"verification": ["..."]
}

Additional constraints:

Never modify more than the minimum number of files needed.

Never change formatting outside the prompt/contract text area.

Never change any behavior except prompt/contract enforcement.

END SYSTEM CONTRACT""",
            "",
            "# Patch Request",
            "",
            "Generate a unified diff patch only.",
            "The output must start with `diff --git`.",
            "",
            f"PLAN: {plan_path.as_posix()}",
            f"CONTEXT: {context_path.as_posix()}",
            f"CONSTRAINTS: {constraints_path.as_posix()}",
            f"FIX_BRIEF: {fix_brief_path.as_posix()}",
        ]
    )
    _write(prompt_path, prompt)
    cmd, err = _format_cmd(
        patch_cmd_tpl,
        PROMPT_PATH=str(prompt_path),
        PLAN_PATH=str(plan_path),
        CONTEXT_PATH=str(context_path),
        CONSTRAINTS_PATH=str(constraints_path),
        FIX_BRIEF_PATH=str(fix_brief_path),
        GOAL=goal,
        ROUND=str(current_round),
        REPO_ROOT=str(repo_root),
    )
    if err:
        _write(run_dir / "logs" / "patch_cmd.stdout.txt", "")
        _write(run_dir / "logs" / "patch_cmd.stderr.txt", err + "\n")
        return "", err
    rc, out, err = _run(cmd, cwd=repo_root, shell=True)
    _write(run_dir / "logs" / "patch_cmd.stdout.txt", out)
    _write(run_dir / "logs" / "patch_cmd.stderr.txt", err)
    if rc != 0:
        return "", f"patch-cmd failed (exit={rc})"
    patch = _extract_patch(out)
    if not patch:
        return "", "patch-cmd output did not contain unified diff starting with `diff --git`"
    if _has_nested_diff_added_lines(patch):
        return "", "patch-cmd output contained nested diff markers inside added lines"
    return patch, "ok"


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
    plan_cmd_tpl: str,
    patch_cmd_tpl: str,
    verify_cmd: str,
    require_external_plan: bool,
    require_external_patch: bool,
    no_mechanical_fallback: bool,
    allow_local: bool,
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
        last_error="",
        artifacts={"run_dir": str(run_dir.relative_to(repo_root).as_posix())},
    )
    _trace(run_dir, f"start run_id={run_id} goal={goal}")

    effective_require_plan = bool(require_external_plan) and not bool(allow_local)
    effective_require_patch = bool(require_external_patch) and not bool(allow_local)
    effective_no_mechanical_fallback = bool(no_mechanical_fallback) or effective_require_patch
    _trace(
        run_dir,
        "mode "
        + json.dumps(
            {
                "require_external_plan": effective_require_plan,
                "require_external_patch": effective_require_patch,
                "no_mechanical_fallback": effective_no_mechanical_fallback,
                "allow_local": bool(allow_local),
            },
            ensure_ascii=False,
        ),
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
    fix_brief_upper = outbox_dir / "FIX_BRIEF.md"
    fix_brief_lower = outbox_dir / "fix_brief.md"
    _ensure_fix_brief_seed(fix_brief_upper, goal)
    _sync_fix_brief_alias(fix_brief_upper, fix_brief_lower)

    start_round = int(state.get("round", 1) or 1)
    for current_round in range(start_round, max_rounds + 1):
        _trace(run_dir, f"round={current_round} phase=find query={next_query}")
        state = _save_state(run_dir, state, phase="find", round=current_round)
        references = local_librarian.search(repo_root=repo_root, query=next_query, k=8)
        context_path = outbox_dir / "CONTEXT.md"
        _write_context(out_path=context_path, goal=next_query, references=references)
        constraints_path = outbox_dir / "CONSTRAINTS.md"
        _write_constraints(constraints_path, repo_root)
        _ensure_fix_brief_seed(fix_brief_upper, goal)
        _sync_fix_brief_alias(fix_brief_upper, fix_brief_lower)
        state = _save_state(
            run_dir,
            state,
            artifacts={
                "context": str(context_path.relative_to(run_dir).as_posix()),
                "constraints": str(constraints_path.relative_to(run_dir).as_posix()),
                "fix_brief": str(fix_brief_upper.relative_to(run_dir).as_posix()),
            },
        )

        state = _save_state(run_dir, state, phase="plan")
        plan_path = outbox_dir / "PLAN.md"
        _trace(run_dir, f"round={current_round} phase=plan")
        if plan_cmd_tpl.strip():
            ok_plan, plan_reason = _generate_plan_via_cmd(
                repo_root=repo_root,
                run_dir=run_dir,
                plan_cmd_tpl=plan_cmd_tpl,
                plan_path=plan_path,
                context_path=context_path,
                constraints_path=constraints_path,
                fix_brief_path=fix_brief_upper,
                goal=goal,
                current_round=current_round,
            )
            if not ok_plan:
                if effective_require_plan:
                    return _fail(
                        run_dir=run_dir,
                        state=state,
                        phase="stop",
                        round_number=current_round,
                        reason=f"external plan required; {plan_reason}",
                        code=5,
                        event="PLAN_CMD_FAIL",
                    )
                _trace(
                    run_dir,
                    f"plan-cmd failed but local fallback allowed: {plan_reason}",
                )
                _write_plan(
                    out_path=plan_path,
                    goal=goal,
                    current_round=current_round,
                    references=references,
                )
        elif effective_require_plan:
            return _fail(
                run_dir=run_dir,
                state=state,
                phase="stop",
                round_number=current_round,
                reason="SDDAI_PLAN_CMD/--plan-cmd required when require-external-plan=true",
                code=5,
                event="PLAN_CMD_REQUIRED",
            )
        else:
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
        _trace(run_dir, f"round={current_round} phase=build")
        pre_review = contract_guard.evaluate(
            repo_root,
            policy_path=repo_root / "contracts" / "allowed_changes.yaml",
            out_path=reviews_dir / "contract_review.json",
        )
        if not bool(pre_review.get("contract_guard", {}).get("pass", False)):
            return _fail(
                run_dir=run_dir,
                state=state,
                phase="stop",
                round_number=current_round,
                reason="contract guard failed before apply",
                code=2,
                event="CONTRACT_FAIL_PRE",
                artifacts={"contract_review": "reviews/contract_review.json"},
            )

        label_hint = str(state.get("last_verify", {}).get("label", "UNKNOWN"))
        patch_text = ""
        patch_reason = ""
        if patch_cmd_tpl.strip():
            patch_text, patch_reason = _generate_patch_via_cmd(
                repo_root=repo_root,
                run_dir=run_dir,
                patch_cmd_tpl=patch_cmd_tpl,
                plan_path=plan_path,
                context_path=context_path,
                constraints_path=constraints_path,
                fix_brief_path=fix_brief_upper,
                goal=goal,
                current_round=current_round,
            )
            if not patch_text and effective_no_mechanical_fallback:
                return _fail(
                    run_dir=run_dir,
                    state=state,
                    phase="stop",
                    round_number=current_round,
                    reason=f"external patch required; {patch_reason}",
                    code=6,
                    event="PATCH_CMD_FAIL",
                )
        elif effective_require_patch:
            return _fail(
                run_dir=run_dir,
                state=state,
                phase="stop",
                round_number=current_round,
                reason="SDDAI_PATCH_CMD/--patch-cmd required when require-external-patch=true",
                code=6,
                event="PATCH_CMD_REQUIRED",
            )

        if not patch_text:
            if effective_no_mechanical_fallback:
                return _fail(
                    run_dir=run_dir,
                    state=state,
                    phase="stop",
                    round_number=current_round,
                    reason="local mechanical fallback disabled and no external patch available",
                    code=6,
                    event="PATCH_FALLBACK_DISABLED",
                )
            _trace(run_dir, f"using local mechanical patch fallback label={label_hint}")
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
            _rollback_patch(repo_root, patch_path, run_dir)
            return _fail(
                run_dir=run_dir,
                state=state,
                phase="stop",
                round_number=current_round,
                reason=f"patch apply failed: {apply_reason}",
                code=3,
                event="PATCH_APPLY_FAIL",
            )

        post_review = contract_guard.evaluate(
            repo_root,
            policy_path=repo_root / "contracts" / "allowed_changes.yaml",
            out_path=reviews_dir / "contract_review.json",
        )
        if not bool(post_review.get("contract_guard", {}).get("pass", False)):
            _rollback_patch(repo_root, patch_path, run_dir)
            return _fail(
                run_dir=run_dir,
                state=state,
                phase="stop",
                round_number=current_round,
                reason="contract guard failed after apply",
                code=4,
                event="CONTRACT_FAIL_POST",
                artifacts={"contract_review": "reviews/contract_review.json"},
            )

        state = _save_state(run_dir, state, phase="verify")
        _trace(run_dir, f"round={current_round} phase=verify")
        cmd = _verify_command(repo_root, verify_cmd)
        verify_env = dict(os.environ)
        verify_env.pop("SDDAI_PLAN_CMD", None)
        verify_env.pop("SDDAI_PATCH_CMD", None)
        rc, stdout, stderr = _run(cmd, cwd=repo_root, env=verify_env)
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
            _save_state(run_dir, state, phase="done", last_error="")
            _trace(run_dir, f"round={current_round} phase=done")
            print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "status": "done"}, ensure_ascii=False))
            return 0

        state = _save_state(run_dir, state, phase="contrast")
        contrast = contrast_rules.classify_verify(rc=rc, stdout=stdout, stderr=stderr)
        label = str(contrast.get("label", "UNKNOWN"))
        next_query = _query_for_label(label, goal)
        fix_refs = local_librarian.search(repo_root=repo_root, query=next_query, k=6)
        fix_brief_path = fix_brief_upper
        contrast_rules.write_fix_brief(
            out_path=fix_brief_path,
            rc=rc,
            stdout=stdout,
            stderr=stderr,
            references=fix_refs,
        )
        _sync_fix_brief_alias(fix_brief_upper, fix_brief_lower)
        _trace(run_dir, f"round={current_round} phase=fix label={label}")
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

    _save_state(
        run_dir,
        state,
        phase="stop",
        round=max_rounds,
        last_error="max_rounds reached without verify pass",
    )
    _trace(run_dir, "phase=stop reason=max_rounds")
    print(json.dumps({"run_id": run_id, "run_dir": str(run_dir), "status": "stop"}, ensure_ascii=False))
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="ADLC self improve core workflow")
    ap.add_argument("--repo", default=".")
    ap.add_argument("--goal", required=True)
    ap.add_argument("--max-rounds", type=int, default=2)
    ap.add_argument("--run-id", default="")
    ap.add_argument("--plan-cmd", default="")
    ap.add_argument("--patch-cmd", default="")
    ap.add_argument("--verify-cmd", default="")
    ap.add_argument("--require-external-plan", default="true")
    ap.add_argument("--require-external-patch", default="true")
    ap.add_argument("--allow-local", action="store_true")
    ap.add_argument("--no-mechanical-fallback", action="store_true")
    args = ap.parse_args()

    repo_root = Path(args.repo).resolve()
    run_id = args.run_id.strip() or run_state.create_run_id()
    plan_cmd_tpl = (args.plan_cmd or os.environ.get("SDDAI_PLAN_CMD", "")).strip()
    patch_cmd_tpl = (args.patch_cmd or os.environ.get("SDDAI_PATCH_CMD", "")).strip()
    require_external_plan = _parse_bool(args.require_external_plan, default=True)
    require_external_patch = _parse_bool(args.require_external_patch, default=True)
    return run_workflow(
        repo_root=repo_root,
        goal=str(args.goal),
        max_rounds=max(1, int(args.max_rounds)),
        run_id=run_id,
        plan_cmd_tpl=plan_cmd_tpl,
        patch_cmd_tpl=patch_cmd_tpl,
        verify_cmd=str(args.verify_cmd),
        require_external_plan=require_external_plan,
        require_external_patch=require_external_patch,
        no_mechanical_fallback=bool(args.no_mechanical_fallback),
        allow_local=bool(args.allow_local),
    )


if __name__ == "__main__":
    raise SystemExit(main())
