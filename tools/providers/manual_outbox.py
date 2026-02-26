#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

TEMPLATE_DIR = Path("agents") / "prompts"
DEFAULT_MAX_OUTBOX_PROMPTS = 20

TEMPLATE_BY_ROLE_ACTION = {
    ("chair", "plan_draft"): "chair_plan_draft.md",
    ("chair", "file_request"): "chair_file_request.md",
    ("chair", "plan_signed"): "chair_plan_draft.md",
    ("contract_guardian", "review_contract"): "contract_guardian_review.md",
    ("cost_controller", "review_cost"): "cost_controller_review.md",
    ("patchmaker", "make_patch"): "patchmaker_patch.md",
    ("fixer", "fix_patch"): "fixer_patch.md",
    ("researcher", "find_web"): "researcher_find_web.md",
    ("librarian", "context_pack"): "librarian_context_pack.md",
}


def _sanitize(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "item"


def _read_template(repo_root: Path, template_name: str) -> str:
    p = repo_root / TEMPLATE_DIR / template_name
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace").strip()
    return (
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

Never make stylistic-only formatting changes.

Only change repository behavior when required by the goal and within approved scope; avoid unrelated behavior changes.

END SYSTEM CONTRACT

## Task
"""
        "- Follow the artifact contract and write the requested artifact only.\n"
        "- Do not edit repo files.\n"
    )


def _outbox_files(outbox_dir: Path) -> list[Path]:
    if not outbox_dir.exists():
        return []
    return sorted(p for p in outbox_dir.glob("*.md") if p.is_file())


def _header_value(text: str, key: str) -> str:
    prefix = f"{key.strip()}:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return ""


def _find_existing_prompt(outbox_dir: Path, role: str, action: str, target_path: str) -> Path | None:
    for p in _outbox_files(outbox_dir):
        txt = p.read_text(encoding="utf-8", errors="replace")
        if _header_value(txt, "Role") != role:
            continue
        if _header_value(txt, "Action") != action:
            continue
        if _header_value(txt, "Target-Path") != target_path:
            continue
        return p
    return None


def _max_outbox_prompts(config: dict[str, Any]) -> int:
    budgets = config.get("budgets", {})
    if not isinstance(budgets, dict):
        return DEFAULT_MAX_OUTBOX_PROMPTS
    try:
        value = int(budgets.get("max_outbox_prompts", DEFAULT_MAX_OUTBOX_PROMPTS))
    except Exception:
        return DEFAULT_MAX_OUTBOX_PROMPTS
    return max(1, value)


def _next_prompt_path(outbox_dir: Path, role: str, action: str) -> tuple[Path, str]:
    max_idx = 0
    for p in _outbox_files(outbox_dir):
        m = re.match(r"^(\d+)_", p.name)
        if m:
            max_idx = max(max_idx, int(m.group(1)))
    idx = max_idx + 1
    name = f"{idx:03d}_{_sanitize(role)}_{_sanitize(action)}.md"
    rel = Path("outbox") / name
    return outbox_dir / name, rel.as_posix()


def _render_prompt(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> str:
    role = str(request["role"])
    action = str(request["action"])
    target_path = str(request["target_path"])
    missing_paths = [str(x) for x in request.get("missing_paths", [])]
    goal = str(request.get("goal", ""))
    reason = str(request.get("reason", ""))
    template_name = TEMPLATE_BY_ROLE_ACTION.get((role, action), "chair_plan_draft.md")
    template_body = _read_template(repo_root, template_name)
    max_outbox_prompts = _max_outbox_prompts(config)
    patch_only_rule = ""
    if target_path.endswith("diff.patch"):
        patch_only_rule = (
            "5. If target is artifacts/diff.patch, output unified diff only "
            "(first non-empty line: diff --git)."
        )

    missing_lines = "\n".join(f"- {p}" for p in missing_paths) if missing_paths else "- (none)"
    budget_lines = "\n".join(
        [
            f"- max_outbox_prompts: {max_outbox_prompts}",
            f"- max_files: {guardrails_budgets.get('max_files', '') or 'n/a'}",
            f"- max_total_bytes: {guardrails_budgets.get('max_total_bytes', '') or 'n/a'}",
            f"- max_iterations: {guardrails_budgets.get('max_iterations', '') or 'n/a'}",
        ]
    )
    run_target = (run_dir / target_path).resolve()
    return (
        "# OUTBOX PROMPT\n\n"
        f"Run-Dir: {run_dir.resolve()}\n"
        f"Repo-Root: {repo_root.resolve()}\n"
        f"Goal: {goal}\n"
        f"Role: {role}\n"
        f"Action: {action}\n"
        "Provider: manual_outbox\n"
        f"Target-Path: {target_path}\n"
        f"write to: {target_path}\n"
        f"Write-Abs: {run_target}\n"
        f"Reason: {reason}\n\n"
        "Missing-Artifact-Paths:\n"
        f"{missing_lines}\n\n"
        "Budgets:\n"
        f"{budget_lines}\n\n"
        "Hard Rules:\n"
        f"1. You may only write to `{run_target}`.\n"
        "2. Do not modify any file under repo root.\n"
        "3. Do not call network/API tools; manual offline execution only.\n"
        "4. Follow docs/30_artifact_contracts.md output requirements exactly.\n"
        f"{patch_only_rule}\n\n"
        "---\n\n"
        f"{template_body}\n"
    )


def preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    outbox_dir = run_dir / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)
    role = str(request["role"])
    action = str(request["action"])
    target_path = str(request["target_path"])

    existing = _find_existing_prompt(outbox_dir, role, action, target_path)
    if existing is not None:
        return {"status": "outbox_exists", "path": (Path("outbox") / existing.name).as_posix()}

    count = len(_outbox_files(outbox_dir))
    max_prompts = _max_outbox_prompts(config)
    if count >= max_prompts:
        return {
            "status": "budget_exceeded",
            "reason": f"outbox budget exceeded ({count}/{max_prompts})",
            "count": count,
            "max": max_prompts,
        }
    return {"status": "can_create"}


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Any]:
    # BEHAVIOR_ID: B028
    outbox_dir = run_dir / "outbox"
    outbox_dir.mkdir(parents=True, exist_ok=True)

    pre = preview(run_dir=run_dir, request=request, config=config)
    if pre["status"] != "can_create":
        return pre

    prompt_path, rel_path = _next_prompt_path(outbox_dir, str(request["role"]), str(request["action"]))
    prompt_text = _render_prompt(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    prompt_path.write_text(prompt_text, encoding="utf-8")
    return {"status": "outbox_created", "path": rel_path}
