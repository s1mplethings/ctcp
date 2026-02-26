#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOCAL_NOTES_PATH = ROOT / ".agent_private" / "NOTES.md"

try:
    from tools import contrast_rules, contract_guard, local_librarian
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools import contrast_rules, contract_guard, local_librarian


def _sanitize(value: str) -> str:
    text = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    text = re.sub(r"_+", "_", text).strip("_")
    return text or "item"


def _load_local_notes_defaults() -> dict[str, str]:
    path_text = str(os.environ.get("CTCP_LOCAL_NOTES_PATH", "")).strip()
    path = Path(path_text) if path_text else DEFAULT_LOCAL_NOTES_PATH
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}

    out: dict[str, str] = {}
    m_url = re.search(r"`(https?://[^`\s]+)`", text)
    if m_url:
        out["base_url"] = m_url.group(1).strip()
    m_key = re.search(r"`(sk-[^`\s]+)`", text)
    if m_key:
        out["api_key"] = m_key.group(1).strip()
    return out


def _slug(text: str) -> str:
    value = re.sub(r"[^a-z0-9_-]+", "-", (text or "").strip().lower())
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "goal"


def _read_text(path: Path, limit: int = 20000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) > limit:
        return text[:limit] + "\n\n[truncated]"
    return text


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _first_non_empty_line(text: str) -> str:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line:
            return line
    return ""


def _normalize_line_ranges(raw: Any) -> list[list[int]]:
    if not isinstance(raw, list):
        return []
    out: list[list[int]] = []
    for row in raw:
        if not isinstance(row, list) or len(row) != 2:
            continue
        try:
            a = int(row[0])
            b = int(row[1])
        except Exception:
            continue
        if a <= 0 or b <= 0:
            continue
        if a > b:
            a, b = b, a
        out.append([a, b])
    return out


def _extract_json_dict(text: str) -> dict[str, Any] | None:
    raw = (text or "").strip()
    if not raw:
        return None
    try:
        doc = json.loads(raw)
        if isinstance(doc, dict):
            return doc
    except Exception:
        pass

    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE):
        block = m.group(1).strip()
        if not block:
            continue
        try:
            doc = json.loads(block)
            if isinstance(doc, dict):
                return doc
        except Exception:
            continue

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        candidate = raw[start : end + 1]
        try:
            doc = json.loads(candidate)
            if isinstance(doc, dict):
                return doc
        except Exception:
            pass

    return None


def _to_json_text(doc: dict[str, Any]) -> str:
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


def _normalize_file_request(doc: dict[str, Any] | None, *, goal: str) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip() or "dispatch-goal"

    needs_out: list[dict[str, Any]] = []
    raw_needs = src.get("needs")
    if isinstance(raw_needs, list):
        for item in raw_needs:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).strip().replace("\\", "/")
            if not path:
                continue
            mode = str(item.get("mode", "snippets")).strip().lower()
            if mode not in {"full", "snippets"}:
                mode = "snippets"
            entry: dict[str, Any] = {"path": path, "mode": mode}
            if mode == "snippets":
                ranges = _normalize_line_ranges(item.get("line_ranges"))
                entry["line_ranges"] = ranges or [[1, 80]]
            needs_out.append(entry)
    if not needs_out:
        needs_out = [{"path": "README.md", "mode": "snippets", "line_ranges": [[1, 80]]}]

    budget_raw = src.get("budget")
    budget = budget_raw if isinstance(budget_raw, dict) else {}
    try:
        max_files = int(budget.get("max_files", 6))
    except Exception:
        max_files = 6
    try:
        max_total_bytes = int(budget.get("max_total_bytes", 48000))
    except Exception:
        max_total_bytes = 48000
    max_files = max(1, min(max_files, 50))
    max_total_bytes = max(512, min(max_total_bytes, 2_000_000))

    reason = str(src.get("reason", "")).strip() or "chair file request for downstream context pack"

    return {
        "schema_version": "ctcp-file-request-v1",
        "goal": goal_text,
        "needs": needs_out,
        "budget": {"max_files": max_files, "max_total_bytes": max_total_bytes},
        "reason": reason,
    }


def _normalize_context_pack(doc: dict[str, Any] | None, *, goal: str, repo_root: Path) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    goal_text = str(src.get("goal", "")).strip() or goal.strip()
    repo_slug = str(src.get("repo_slug", "")).strip() or repo_root.name

    files_out: list[dict[str, str]] = []
    raw_files = src.get("files")
    if isinstance(raw_files, list):
        for item in raw_files:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).strip().replace("\\", "/")
            if not path:
                continue
            why = str(item.get("why", "")).strip() or "included by api_agent"
            content = str(item.get("content", ""))
            files_out.append({"path": path, "why": why, "content": content})

    omitted_out: list[dict[str, str]] = []
    raw_omitted = src.get("omitted")
    if isinstance(raw_omitted, list):
        for item in raw_omitted:
            if not isinstance(item, dict):
                continue
            path = str(item.get("path", "")).strip().replace("\\", "/")
            if not path:
                continue
            reason = str(item.get("reason", "")).strip() or "unspecified"
            omitted_out.append({"path": path, "reason": reason})

    summary = str(src.get("summary", "")).strip()
    if not summary:
        summary = f"included={len(files_out)} omitted={len(omitted_out)}"

    return {
        "schema_version": "ctcp-context-pack-v1",
        "goal": goal_text,
        "repo_slug": repo_slug,
        "summary": summary,
        "files": files_out,
        "omitted": omitted_out,
    }


def _normalize_find_web(doc: dict[str, Any] | None) -> dict[str, Any]:
    src = doc if isinstance(doc, dict) else {}
    constraints = src.get("constraints")
    if not isinstance(constraints, dict):
        constraints = {}
    results = src.get("results")
    if not isinstance(results, list):
        results = []
    out_results: list[dict[str, Any]] = []
    for row in results:
        if not isinstance(row, dict):
            continue
        url = str(row.get("url", "")).strip()
        if not url:
            continue
        locator = row.get("locator")
        if not isinstance(locator, dict):
            locator = {"type": "unknown", "value": ""}
        item = {
            "url": url,
            "locator": locator,
            "fetched_at": str(row.get("fetched_at", "")).strip(),
            "excerpt": str(row.get("excerpt", "")),
            "why_relevant": str(row.get("why_relevant", "")),
            "risk_flags": row.get("risk_flags") if isinstance(row.get("risk_flags"), list) else [],
        }
        out_results.append(item)
    return {
        "schema_version": "ctcp-find-web-v1",
        "constraints": constraints,
        "results": out_results,
    }


def _normalize_guardrails_md(raw_text: str) -> str:
    kv: dict[str, str] = {}
    for line in (raw_text or "").splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*$", line)
        if not m:
            continue
        kv[m.group(1).strip().lower()] = m.group(2).strip()

    mode = str(kv.get("find_mode", "")).strip().lower()
    if mode not in {"resolver_only", "resolver_plus_web"}:
        mode = "resolver_only"

    def _to_int(name: str, default: int, minimum: int, maximum: int) -> int:
        raw = str(kv.get(name, "")).strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except Exception:
            return default
        if value < minimum:
            return minimum
        if value > maximum:
            return maximum
        return value

    max_files = _to_int("max_files", default=20, minimum=1, maximum=500)
    max_total_bytes = _to_int("max_total_bytes", default=200000, minimum=2048, maximum=20_000_000)
    max_iterations = _to_int("max_iterations", default=3, minimum=1, maximum=20)

    lines = [
        f"find_mode: {mode}",
        f"max_files: {max_files}",
        f"max_total_bytes: {max_total_bytes}",
        f"max_iterations: {max_iterations}",
    ]
    if mode == "resolver_plus_web":
        allow_domains = str(kv.get("allow_domains", "")).strip()
        if allow_domains:
            lines.append(f"allow_domains: {allow_domains}")
        max_queries = _to_int("max_queries", default=2, minimum=1, maximum=20)
        max_pages = _to_int("max_pages", default=2, minimum=1, maximum=50)
        lines.append(f"max_queries: {max_queries}")
        lines.append(f"max_pages: {max_pages}")
    return "\n".join(lines) + "\n"


def _normalize_review_md(raw_text: str, *, title: str) -> str:
    text = raw_text or ""
    upper = text.upper()
    verdict = "APPROVE"
    if "VERDICT: BLOCK" in upper or re.search(r"\bBLOCK\b", upper):
        verdict = "BLOCK"
    elif "VERDICT: APPROVE" in upper or re.search(r"\bAPPROVE\b", upper):
        verdict = "APPROVE"

    reasons: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        item = stripped.lstrip("-").strip()
        if not item:
            continue
        reasons.append(item)
        if len(reasons) >= 3:
            break

    lines = [
        f"# {title}",
        "",
        f"Verdict: {verdict}",
        "",
        "Blocking Reasons:",
    ]
    if verdict == "APPROVE":
        lines.append("- none")
    else:
        if reasons:
            for row in reasons:
                lines.append(f"- {row}")
        else:
            lines.append("- requires follow-up fixes")
    lines += [
        "",
        "Required Fix/Artifacts:",
    ]
    if verdict == "APPROVE":
        lines.append("- none")
    else:
        lines.append("- provide corrected artifact and rerun review")
    lines.append("")
    return "\n".join(lines)


def _normalize_plan_md(raw_text: str, *, signed: bool, goal: str) -> str:
    _ = raw_text
    status = "SIGNED" if signed else "DRAFT"
    return "\n".join(
        [
            f"Status: {status}",
            "Scope-Allow: scripts/,tools/,tests/,artifacts/,meta/,docs/",
            "Scope-Deny: .git/,build/,build_lite/,dist/,runs/",
            "Gates: lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,lite_replay,python_unit_tests",
            "Budgets: max_iterations=3,max_files=20,max_total_bytes=200000",
            "Stop: scope_violation=true,repeated_failure=2,missing_plan_fields=true",
            "Behaviors: B001,B002,B003,B004,B005,B006,B007,B008,B009,B010,B011,B012,B013,B014,B015,B016,B017,B018,B019,B020,B021,B022,B023,B024,B025,B026,B027,B028,B029,B030,B031,B032,B033,B034,B035",
            "Results: R001,R002,R003,R004,R005",
            f"Goal: {goal or 'dispatch-goal'}",
            "",
        ]
    )


def _normalize_json_artifact(*, repo_root: Path, request: dict[str, Any], raw_text: str) -> tuple[str, str]:
    role = str(request.get("role", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    goal = str(request.get("goal", "")).strip()
    doc = _extract_json_dict(raw_text)

    if role == "chair" and action == "file_request":
        return _to_json_text(_normalize_file_request(doc, goal=goal)), ""
    if role == "librarian" and action == "context_pack":
        return _to_json_text(_normalize_context_pack(doc, goal=goal, repo_root=repo_root)), ""
    if role == "researcher" and action == "find_web":
        return _to_json_text(_normalize_find_web(doc)), ""

    if doc is None:
        return "", "agent output is not valid JSON object"
    return _to_json_text(doc), ""


def _record_failure_review(run_dir: Path, reason: str) -> Path:
    review = run_dir / "reviews" / "review_api_agent.md"
    lines = [
        "# API Agent Review",
        "",
        "Verdict: BLOCK",
        f"Reason: {reason}",
        "Required Fix/Artifacts: check logs/plan_agent.* and logs/patch_agent.*",
        "",
    ]
    _write_text(review, "\n".join(lines))
    return review


def _load_externals_doc(repo_root: Path, run_dir: Path, goal: str) -> tuple[Path | None, dict[str, Any] | None]:
    candidates: list[Path] = [run_dir / "artifacts" / "externals_pack.json"]
    externals_root = repo_root / "meta" / "externals"
    candidates.append(externals_root / _slug(goal) / "externals_pack.json")
    if externals_root.exists():
        for row in sorted(externals_root.glob("*/externals_pack.json")):
            if row not in candidates:
                candidates.append(row)

    for path in candidates:
        if not path.exists():
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        if isinstance(doc, dict):
            return path, doc
    return None, None


def _render_context_md(*, goal: str, reason: str, references: list[dict[str, Any]]) -> str:
    query = goal.strip() or reason.strip() or "dispatch"
    lines = [
        "# CONTEXT",
        "",
        f"- query: `{query}`",
        f"- top_k: `{len(references)}`",
        "",
    ]
    if not references:
        lines += ["- none", ""]
        return "\n".join(lines)

    for idx, row in enumerate(references, start=1):
        path = str(row.get("path", "")).strip()
        start = int(row.get("start_line", 0) or 0)
        end = int(row.get("end_line", 0) or 0)
        snippet = str(row.get("snippet", "")).strip()
        line_ref = f"{path}:{start}-{end}" if start > 0 and end >= start else path
        lines += [
            f"## Ref {idx}",
            f"- source: `{line_ref}`",
            "```text",
            snippet,
            "```",
            "",
        ]
    return "\n".join(lines)


def _render_constraints_md(
    *,
    repo_root: Path,
    guardrails_budgets: dict[str, str],
    max_outbox_prompts: int,
) -> str:
    policy_path = repo_root / "contracts" / "allowed_changes.yaml"
    policy = contract_guard.load_policy(policy_path)
    allowed_paths = [str(x) for x in policy.get("allowed_paths", []) if str(x).strip()]
    blocked_paths = [str(x) for x in policy.get("blocked_paths", []) if str(x).strip()]
    lines = [
        "# CONSTRAINTS",
        "",
        f"- policy: `{policy_path.as_posix()}`",
        f"- max_outbox_prompts: `{max_outbox_prompts}`",
        f"- max_files: `{guardrails_budgets.get('max_files', '') or policy.get('max_files', 'n/a')}`",
        f"- max_total_bytes: `{guardrails_budgets.get('max_total_bytes', '') or 'n/a'}`",
        f"- max_iterations: `{guardrails_budgets.get('max_iterations', '') or 'n/a'}`",
        f"- max_added_lines: `{policy.get('max_added_lines', 'n/a')}`",
        f"- max_deleted_lines: `{policy.get('max_deleted_lines', 'n/a')}`",
        f"- max_total_lines: `{policy.get('max_total_lines', 'n/a')}`",
        "",
        "## Allowed Paths",
    ]
    if allowed_paths:
        for row in allowed_paths:
            lines.append(f"- `{row}`")
    else:
        lines.append("- (none)")

    lines += ["", "## Blocked Paths"]
    if blocked_paths:
        for row in blocked_paths:
            lines.append(f"- `{row}`")
    else:
        lines.append("- (none)")
    lines.append("")
    return "\n".join(lines)


def _render_externals_md(*, repo_root: Path, run_dir: Path, goal: str) -> str:
    path, doc = _load_externals_doc(repo_root, run_dir, goal)
    lines = ["# EXTERNALS", ""]
    if path is None or not isinstance(doc, dict):
        lines += ["- none", ""]
        return "\n".join(lines)

    lines.append(f"- source: `{path.as_posix()}`")
    constraints = doc.get("constraints", {})
    if isinstance(constraints, dict):
        max_sources = constraints.get("max_sources", "")
        if str(max_sources).strip():
            lines.append(f"- constraints.max_sources: `{max_sources}`")

    sources = doc.get("sources", [])
    if not isinstance(sources, list) or not sources:
        lines += ["- sources: none", ""]
        return "\n".join(lines)

    lines += ["", "## Sources"]
    for idx, row in enumerate(sources[:8], start=1):
        if not isinstance(row, dict):
            continue
        title = str(row.get("title", "")).strip() or "(untitled)"
        url = str(row.get("url", "")).strip() or "(missing-url)"
        why = str(row.get("why_relevant", "")).strip()
        lines.append(f"- {idx}. {title} | {url}")
        if why:
            lines.append(f"  why: {why}")
    lines.append("")
    return "\n".join(lines)


def _render_fix_brief_seed(goal: str, reason: str) -> str:
    return "\n".join(
        [
            "# Fix Brief",
            "",
            "- label: `BOOTSTRAP`",
            "- verify_rc: `N/A`",
            "",
            "## Minimal Next Actions",
            "- Use CONTEXT + CONSTRAINTS + EXTERNALS to produce a minimal PLAN.",
            "- Emit unified diff only for patch targets.",
            "",
            "## Related File References",
            f"- goal: `{goal}`",
            f"- reason: `{reason}`",
            "",
        ]
    )


def _write_fix_brief(*, repo_root: Path, run_dir: Path, goal: str, reason: str, out_path: Path) -> None:
    report_path = run_dir / "artifacts" / "verify_report.json"
    if not report_path.exists():
        _write_text(out_path, _render_fix_brief_seed(goal, reason))
        return

    try:
        report = json.loads(report_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        _write_text(out_path, _render_fix_brief_seed(goal, reason))
        return

    commands = report.get("commands", [])
    rc = 1
    stdout = ""
    stderr = ""
    if isinstance(commands, list) and commands:
        cmd0 = commands[0] if isinstance(commands[0], dict) else {}
        try:
            rc = int(cmd0.get("exit_code", 1))
        except Exception:
            rc = 1
        stdout_log = run_dir / str(cmd0.get("stdout_log", ""))
        stderr_log = run_dir / str(cmd0.get("stderr_log", ""))
        stdout = _read_text(stdout_log, limit=12000)
        stderr = _read_text(stderr_log, limit=12000)

    refs = local_librarian.search(repo_root=repo_root, query=goal.strip() or reason.strip(), k=6)
    contrast_rules.write_fix_brief(
        out_path=out_path,
        rc=rc,
        stdout=stdout,
        stderr=stderr,
        references=refs,
    )


def _max_outbox_prompts(config: dict[str, Any]) -> int:
    budgets = config.get("budgets", {}) if isinstance(config, dict) else {}
    if not isinstance(budgets, dict):
        return 20
    try:
        value = int(budgets.get("max_outbox_prompts", 20))
    except Exception:
        value = 20
    return max(1, value)


def _build_evidence_pack(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Path]:
    outbox = run_dir / "outbox"
    outbox.mkdir(parents=True, exist_ok=True)

    goal = str(request.get("goal", "")).strip()
    reason = str(request.get("reason", "")).strip()
    refs = local_librarian.search(repo_root=repo_root, query=goal or reason or "dispatch", k=8)

    context_path = outbox / "CONTEXT.md"
    constraints_path = outbox / "CONSTRAINTS.md"
    fix_brief_path = outbox / "FIX_BRIEF.md"
    externals_path = outbox / "EXTERNALS.md"

    _write_text(context_path, _render_context_md(goal=goal, reason=reason, references=refs))
    _write_text(
        constraints_path,
        _render_constraints_md(
            repo_root=repo_root,
            guardrails_budgets=guardrails_budgets,
            max_outbox_prompts=_max_outbox_prompts(config),
        ),
    )
    _write_fix_brief(
        repo_root=repo_root,
        run_dir=run_dir,
        goal=goal,
        reason=reason,
        out_path=fix_brief_path,
    )
    _write_text(externals_path, _render_externals_md(repo_root=repo_root, run_dir=run_dir, goal=goal))
    return {
        "context": context_path,
        "constraints": constraints_path,
        "fix_brief": fix_brief_path,
        "externals": externals_path,
    }


def _render_prompt(
    *,
    run_dir: Path,
    repo_root: Path,
    request: dict[str, Any],
    evidence: dict[str, Path],
) -> str:
    role = str(request.get("role", ""))
    action = str(request.get("action", ""))
    goal = str(request.get("goal", ""))
    reason = str(request.get("reason", ""))
    target_path = str(request.get("target_path", ""))
    missing_paths = [str(x) for x in request.get("missing_paths", []) if str(x).strip()]
    missing_text = "\n".join(f"- {row}" for row in missing_paths) if missing_paths else "- (none)"

    lines = [
        "# API AGENT PROMPT",
        "",
        f"Run-Dir: {run_dir.resolve()}",
        f"Repo-Root: {repo_root.resolve()}",
        f"Goal: {goal}",
        f"Role: {role}",
        f"Action: {action}",
        "Provider: api_agent",
        f"Target-Path: {target_path}",
        f"Reason: {reason}",
        "",
        "Missing-Artifact-Paths:",
        missing_text,
        "",
        "Hard Rules:",
        "1. Only write run_dir artifacts requested by this role.",
        "2. Never modify repository files directly.",
        "3. For patch targets output unified diff only (first non-empty line: diff --git).",
        "4. Keep changes minimal and policy compliant.",
        "",
    ]

    for key in ("context", "constraints", "fix_brief", "externals"):
        p = evidence[key]
        lines += [f"## {p.name}", _read_text(p, limit=18000), ""]
    return "\n".join(lines)


def _default_plan_cmd(repo_root: Path) -> str:
    script = repo_root / "scripts" / "externals" / "openai_plan_api.py"
    return (
        f'"{sys.executable}" "{script}" '
        '"{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}" '
        '"{GOAL}" "{ROUND}" "{REPO_ROOT}"'
    )


def _default_patch_cmd(repo_root: Path) -> str:
    script = repo_root / "scripts" / "externals" / "openai_patch_api.py"
    return (
        f'"{sys.executable}" "{script}" '
        '"{PLAN_PATH}" "{CONTEXT_PATH}" "{CONSTRAINTS_PATH}" "{FIX_BRIEF_PATH}" '
        '"{GOAL}" "{ROUND}" "{REPO_ROOT}"'
    )


def _default_agent_cmd(repo_root: Path) -> str:
    script = repo_root / "scripts" / "externals" / "openai_agent_api.py"
    return f'"{sys.executable}" "{script}"'


def _format_cmd_template(template: str, values: dict[str, str]) -> tuple[str, str]:
    text = (template or "").strip()
    if not text:
        return "", "empty command template"
    if "{" not in text:
        return text, ""
    try:
        return text.format(**values), ""
    except Exception as exc:
        return "", f"command template formatting failed: {exc}"


def _run_command(
    cmd: str,
    *,
    cwd: Path,
    stdin_text: str,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if extra_env:
        for key, value in extra_env.items():
            env[str(key)] = str(value)
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        shell=True,
        env=env,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _is_api_env_ready() -> tuple[bool, str]:
    defaults = _load_local_notes_defaults()
    key = (
        str(os.environ.get("OPENAI_API_KEY", "")).strip()
        or str(os.environ.get("CTCP_OPENAI_API_KEY", "")).strip()
        or str(defaults.get("api_key", "")).strip()
    )
    if key:
        return True, ""
    return False, "missing env: OPENAI_API_KEY"


def _needs_patch(request: dict[str, Any]) -> bool:
    role = str(request.get("role", "")).strip().lower()
    target_path = str(request.get("target_path", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    if target_path.endswith("diff.patch"):
        return True
    if role in {"patchmaker", "fixer"}:
        return True
    return action in {"make_patch", "fix_patch"}


def _needs_plan(request: dict[str, Any]) -> bool:
    role = str(request.get("role", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    target_path = str(request.get("target_path", "")).strip().lower()
    if role in {"patchmaker", "fixer"}:
        return True
    if action in {"plan_draft", "plan_signed", "make_patch", "fix_patch"}:
        return True
    return target_path.endswith("plan.md")


def _resolve_templates(repo_root: Path, request: dict[str, Any]) -> tuple[dict[str, str], str]:
    needs_plan = _needs_plan(request)
    needs_patch = _needs_patch(request)

    agent_tpl = str(os.environ.get("SDDAI_AGENT_CMD", "")).strip()
    plan_tpl = str(os.environ.get("SDDAI_PLAN_CMD", "")).strip()
    patch_tpl = str(os.environ.get("SDDAI_PATCH_CMD", "")).strip()

    templates: dict[str, str] = {}
    if needs_plan:
        templates["plan"] = plan_tpl or agent_tpl
    if needs_patch:
        templates["patch"] = patch_tpl or agent_tpl

    missing_cmd = (needs_plan and not templates.get("plan")) or (needs_patch and not templates.get("patch"))
    if missing_cmd:
        ready, reason = _is_api_env_ready()
        if not ready:
            return {}, reason
        if needs_plan and not templates.get("plan"):
            templates["plan"] = _default_plan_cmd(repo_root)
        if needs_patch and not templates.get("patch"):
            templates["patch"] = _default_patch_cmd(repo_root)

    if not needs_plan and not needs_patch:
        if agent_tpl:
            templates["agent"] = agent_tpl
            return templates, ""
        ready, reason = _is_api_env_ready()
        if not ready:
            return {}, reason
        templates["agent"] = _default_agent_cmd(repo_root)

    if needs_plan and not needs_patch and "plan" in templates and "agent" not in templates:
        templates["agent"] = templates["plan"]

    return templates, ""


def preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    _ = (run_dir, config)
    templates, reason = _resolve_templates(ROOT, request)
    if not templates:
        return {"status": "disabled", "reason": reason}
    if _needs_patch(request):
        return {"status": "can_exec", "writes": ["outbox/PLAN.md", "outbox/diff.patch"]}
    return {"status": "can_exec"}


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Any]:
    # BEHAVIOR_ID: B031
    logs_dir = run_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    templates, reason = _resolve_templates(repo_root, request)
    if not templates:
        review = _record_failure_review(run_dir, reason)
        return {
            "status": "disabled",
            "reason": reason,
            "review": review.relative_to(run_dir).as_posix(),
        }

    evidence = _build_evidence_pack(
        repo_root=repo_root,
        run_dir=run_dir,
        request=request,
        config=config,
        guardrails_budgets=guardrails_budgets,
    )
    prompt_text = _render_prompt(run_dir=run_dir, repo_root=repo_root, request=request, evidence=evidence)

    role = str(request.get("role", ""))
    action = str(request.get("action", ""))
    prompt_path = run_dir / "outbox" / f"AGENT_PROMPT_{_sanitize(role)}_{_sanitize(action)}.md"
    _write_text(prompt_path, prompt_text)

    plan_out = run_dir / "outbox" / "PLAN.md"
    patch_out = run_dir / "outbox" / "diff.patch"
    target_rel = str(request.get("target_path", "")).strip()
    target_path = (run_dir / target_rel).resolve() if target_rel else run_dir / "artifacts" / "diff.patch"

    placeholders = {
        "PROMPT_PATH": str(prompt_path),
        "PLAN_PATH": str(plan_out),
        "PATCH_PATH": str(patch_out),
        "TARGET_PATH": str(target_path),
        "CONTEXT_PATH": str(evidence["context"]),
        "CONSTRAINTS_PATH": str(evidence["constraints"]),
        "FIX_BRIEF_PATH": str(evidence["fix_brief"]),
        "EXTERNALS_PATH": str(evidence["externals"]),
        "GOAL": str(request.get("goal", "")),
        "REASON": str(request.get("reason", "")),
        "ROLE": role,
        "ACTION": action,
        "RUN_DIR": str(run_dir),
        "REPO_ROOT": str(repo_root),
        "ROUND": "1",
    }
    api_calls_path = run_dir / "api_calls.jsonl"
    api_call_env = {
        "CTCP_API_CALLS_PATH": str(api_calls_path),
        "CTCP_API_ROLE": role,
        "CTCP_API_ACTION": action,
    }

    if "plan" in templates:
        cmd, fmt_err = _format_cmd_template(templates["plan"], placeholders)
        if fmt_err:
            review = _record_failure_review(run_dir, fmt_err)
            return {
                "status": "exec_failed",
                "reason": fmt_err,
                "review": review.relative_to(run_dir).as_posix(),
            }
        proc = _run_command(cmd, cwd=repo_root, stdin_text=prompt_text, extra_env=api_call_env)
        plan_stdout = logs_dir / "plan_agent.stdout"
        plan_stderr = logs_dir / "plan_agent.stderr"
        _write_text(plan_stdout, proc.stdout)
        _write_text(plan_stderr, proc.stderr)
        if proc.returncode != 0:
            reason = f"plan agent command failed rc={proc.returncode}"
            review = _record_failure_review(run_dir, reason)
            return {
                "status": "exec_failed",
                "reason": reason,
                "cmd": cmd,
                "rc": proc.returncode,
                "stdout_log": plan_stdout.relative_to(run_dir).as_posix(),
                "stderr_log": plan_stderr.relative_to(run_dir).as_posix(),
                "review": review.relative_to(run_dir).as_posix(),
            }
        plan_text = (proc.stdout or "").strip()
        if not plan_text:
            reason = "plan agent output is empty"
            review = _record_failure_review(run_dir, reason)
            return {
                "status": "exec_failed",
                "reason": reason,
                "cmd": cmd,
                "stdout_log": plan_stdout.relative_to(run_dir).as_posix(),
                "stderr_log": plan_stderr.relative_to(run_dir).as_posix(),
                "review": review.relative_to(run_dir).as_posix(),
            }
        _write_text(plan_out, plan_text + "\n")
        placeholders["PLAN_PATH"] = str(plan_out)

    if "patch" in templates:
        cmd, fmt_err = _format_cmd_template(templates["patch"], placeholders)
        if fmt_err:
            review = _record_failure_review(run_dir, fmt_err)
            return {
                "status": "exec_failed",
                "reason": fmt_err,
                "review": review.relative_to(run_dir).as_posix(),
            }
        proc = _run_command(cmd, cwd=repo_root, stdin_text=prompt_text, extra_env=api_call_env)
        patch_stdout = logs_dir / "patch_agent.stdout"
        patch_stderr = logs_dir / "patch_agent.stderr"
        _write_text(patch_stdout, proc.stdout)
        _write_text(patch_stderr, proc.stderr)
        if proc.returncode != 0:
            reason = f"patch agent command failed rc={proc.returncode}"
            review = _record_failure_review(run_dir, reason)
            return {
                "status": "exec_failed",
                "reason": reason,
                "cmd": cmd,
                "rc": proc.returncode,
                "stdout_log": patch_stdout.relative_to(run_dir).as_posix(),
                "stderr_log": patch_stderr.relative_to(run_dir).as_posix(),
                "review": review.relative_to(run_dir).as_posix(),
            }
        patch_text = (proc.stdout or "").strip()
        first = _first_non_empty_line(patch_text)
        if first != "" and not first.startswith("diff --git"):
            reason = "patch output must start with diff --git"
            review = _record_failure_review(run_dir, reason)
            return {
                "status": "exec_failed",
                "reason": reason,
                "cmd": cmd,
                "stdout_log": patch_stdout.relative_to(run_dir).as_posix(),
                "stderr_log": patch_stderr.relative_to(run_dir).as_posix(),
                "review": review.relative_to(run_dir).as_posix(),
            }
        if not patch_text:
            reason = "patch output is empty"
            review = _record_failure_review(run_dir, reason)
            return {
                "status": "exec_failed",
                "reason": reason,
                "cmd": cmd,
                "stdout_log": patch_stdout.relative_to(run_dir).as_posix(),
                "stderr_log": patch_stderr.relative_to(run_dir).as_posix(),
                "review": review.relative_to(run_dir).as_posix(),
            }
        patch_payload = patch_text + "\n"
        _write_text(patch_out, patch_payload)
        _write_text(target_path, patch_payload)
        return {
            "status": "executed",
            "target_path": target_rel or "artifacts/diff.patch",
            "plan_path": plan_out.relative_to(run_dir).as_posix(),
            "patch_path": patch_out.relative_to(run_dir).as_posix(),
            "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
            "stdout_log": patch_stdout.relative_to(run_dir).as_posix(),
            "stderr_log": patch_stderr.relative_to(run_dir).as_posix(),
        }

    agent_tpl = templates.get("agent") or templates.get("plan")
    if not agent_tpl:
        available_keys = ", ".join(sorted(templates.keys())) or "(none)"
        reason = (
            "missing agent template "
            f"(role={role}, action={action}, plan={_needs_plan(request)}, patch={_needs_patch(request)}, keys={available_keys})"
        )
        review = _record_failure_review(run_dir, reason)
        return {
            "status": "exec_failed",
            "reason": reason,
            "review": review.relative_to(run_dir).as_posix(),
        }

    cmd, fmt_err = _format_cmd_template(agent_tpl, placeholders)
    if fmt_err:
        review = _record_failure_review(run_dir, fmt_err)
        return {
            "status": "exec_failed",
            "reason": fmt_err,
            "review": review.relative_to(run_dir).as_posix(),
        }

    proc = _run_command(cmd, cwd=repo_root, stdin_text=prompt_text, extra_env=api_call_env)
    agent_stdout = logs_dir / "agent.stdout"
    agent_stderr = logs_dir / "agent.stderr"
    _write_text(agent_stdout, proc.stdout)
    _write_text(agent_stderr, proc.stderr)
    if proc.returncode != 0:
        reason = f"agent command failed rc={proc.returncode}"
        review = _record_failure_review(run_dir, reason)
        return {
            "status": "exec_failed",
            "reason": reason,
            "cmd": cmd,
            "rc": proc.returncode,
            "stdout_log": agent_stdout.relative_to(run_dir).as_posix(),
            "stderr_log": agent_stderr.relative_to(run_dir).as_posix(),
            "review": review.relative_to(run_dir).as_posix(),
        }

    target_payload_raw = (proc.stdout or "").rstrip()
    if target_rel.lower().endswith(".json"):
        target_payload, norm_err = _normalize_json_artifact(
            repo_root=repo_root,
            request=request,
            raw_text=target_payload_raw,
        )
        if norm_err:
            review = _record_failure_review(run_dir, norm_err)
            return {
                "status": "exec_failed",
                "reason": norm_err,
                "cmd": cmd,
                "stdout_log": agent_stdout.relative_to(run_dir).as_posix(),
                "stderr_log": agent_stderr.relative_to(run_dir).as_posix(),
                "review": review.relative_to(run_dir).as_posix(),
            }
    else:
        if target_rel.lower().endswith("guardrails.md"):
            target_payload = _normalize_guardrails_md(target_payload_raw)
        elif target_rel.lower().endswith("artifacts/plan.md"):
            target_payload = _normalize_plan_md(
                target_payload_raw,
                signed=True,
                goal=str(request.get("goal", "")).strip(),
            )
        elif target_rel.lower().endswith("artifacts/plan_draft.md"):
            target_payload = _normalize_plan_md(
                target_payload_raw,
                signed=False,
                goal=str(request.get("goal", "")).strip(),
            )
        elif target_rel.lower().endswith("reviews/review_contract.md"):
            target_payload = _normalize_review_md(target_payload_raw, title="Contract Review")
        elif target_rel.lower().endswith("reviews/review_cost.md"):
            target_payload = _normalize_review_md(target_payload_raw, title="Cost Review")
        else:
            target_payload = target_payload_raw + "\n"
    _write_text(target_path, target_payload)
    return {
        "status": "executed",
        "target_path": target_rel,
        "prompt_path": prompt_path.relative_to(run_dir).as_posix(),
        "stdout_log": agent_stdout.relative_to(run_dir).as_posix(),
        "stderr_log": agent_stderr.relative_to(run_dir).as_posix(),
    }
