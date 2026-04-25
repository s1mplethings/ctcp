#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ctcp_adapters.analysis_md_normalizer import normalize_analysis_md as _normalize_analysis_md
from llm_core.providers.api_provider import _read_text, _slug, _write_text
from tools import contrast_rules, contract_guard, local_librarian
from tools.providers.project_generation_artifacts import (
    build_default_context_request,
    is_project_generation_goal,
    normalize_deliverable_index,
    normalize_docs_generation,
    normalize_output_contract_freeze,
    normalize_patch_payload,
    normalize_project_manifest,
    normalize_source_generation,
    normalize_workflow_generation,
)
from tools.formal_api_lock import formal_api_only_enabled, requires_formal_api

_DEFAULT_PLAN_SCOPE_ALLOW = (
    "scripts/",
    "tools/",
    "tests/",
    "artifacts/",
    "meta/",
    "docs/",
)

_GOAL_SCOPE_FILE_RE = re.compile(r"(?<![:/A-Za-z0-9_.-])([A-Za-z0-9][A-Za-z0-9_./-]*\.[A-Za-z0-9]{1,16})(?![A-Za-z0-9_.-])")


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


def _render_snippets(text: str, ranges: list[list[int]]) -> str:
    if not ranges:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    for pair in ranges:
        if not isinstance(pair, list) or len(pair) != 2:
            continue
        try:
            start = int(pair[0])
            end = int(pair[1])
        except Exception:
            continue
        s = max(1, min(start, end))
        e = min(len(lines), max(start, end))
        if s > e:
            continue
        out.append(f"# lines {s}-{e}")
        for idx in range(s, e + 1):
            out.append(f"{idx:>6}: {lines[idx - 1]}")
    return "\n".join(out).strip()


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
    for match in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", raw, flags=re.IGNORECASE):
        block = match.group(1).strip()
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
    defaults = build_default_context_request(goal_text)
    default_budget = dict(defaults.get("budget", {}))

    needs_out: list[dict[str, Any]] = []
    seed_needs = src.get("needs")
    if not isinstance(seed_needs, list) or not seed_needs:
        seed_needs = list(defaults.get("needs", []))
    for item in seed_needs:
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
            entry["line_ranges"] = _normalize_line_ranges(item.get("line_ranges")) or [[1, 120]]
        needs_out.append(entry)

    budget_raw = src.get("budget")
    budget = budget_raw if isinstance(budget_raw, dict) else {}
    try:
        max_files = int(budget.get("max_files", default_budget.get("max_files", 6)))
    except Exception:
        max_files = int(default_budget.get("max_files", 6))
    try:
        max_total_bytes = int(budget.get("max_total_bytes", default_budget.get("max_total_bytes", 48000)))
    except Exception:
        max_total_bytes = int(default_budget.get("max_total_bytes", 48000))
    max_files = max(1, min(max_files, 50))
    max_total_bytes = max(512, min(max_total_bytes, 2_000_000))

    reason = (
        str(src.get("reason", "")).strip()
        or str(defaults.get("reason", "")).strip()
        or "chair file request for downstream context pack"
    )

    return {
        "schema_version": "ctcp-file-request-v1",
        "goal": goal_text,
        "needs": needs_out,
        "budget": {"max_files": max_files, "max_total_bytes": max_total_bytes},
        "reason": reason,
    }


def _fallback_context_pack_from_file_request(*, run_dir: Path, repo_root: Path, goal: str, repo_slug: str) -> dict[str, Any]:
    request_path = run_dir / "artifacts" / "file_request.json"
    if not request_path.exists():
        return {
            "schema_version": "ctcp-context-pack-v1",
            "goal": goal,
            "repo_slug": repo_slug,
            "summary": "included=0 omitted=0",
            "files": [],
            "omitted": [],
        }
    try:
        request = json.loads(request_path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        request = {}
    if not isinstance(request, dict):
        request = {}

    needs = request.get("needs", [])
    if not isinstance(needs, list):
        needs = []
    budget = request.get("budget", {})
    if not isinstance(budget, dict):
        budget = {}
    try:
        max_files = max(1, int(budget.get("max_files", 6) or 6))
    except Exception:
        max_files = 6
    try:
        max_total_bytes = max(1024, int(budget.get("max_total_bytes", 48000) or 48000))
    except Exception:
        max_total_bytes = 48000

    files_out: list[dict[str, str]] = []
    omitted_out: list[dict[str, str]] = []
    used_bytes = 0
    for item in needs:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip().replace("\\", "/")
        if not path:
            continue
        src = (repo_root / path).resolve()
        try:
            src.relative_to(repo_root.resolve())
        except ValueError:
            omitted_out.append({"path": path, "reason": "denied"})
            continue
        if not src.exists() or not src.is_file():
            omitted_out.append({"path": path, "reason": "missing"})
            continue
        mode = str(item.get("mode", "snippets")).strip().lower()
        raw = src.read_text(encoding="utf-8", errors="replace")
        if mode == "full":
            content = raw
        else:
            content = _render_snippets(raw, _normalize_line_ranges(item.get("line_ranges")))
            if not content:
                omitted_out.append({"path": path, "reason": "irrelevant"})
                continue
        size = len(content.encode("utf-8", errors="replace"))
        if len(files_out) >= max_files or (used_bytes + size) > max_total_bytes:
            omitted_out.append({"path": path, "reason": "too_large"})
            continue
        used_bytes += size
        files_out.append(
            {
                "path": path,
                "why": str(item.get("why", "")).strip() or f"fallback materialized from file_request mode={mode or 'snippets'}",
                "content": content,
            }
        )

    return {
        "schema_version": "ctcp-context-pack-v1",
        "goal": str(request.get("goal", "")).strip() or goal,
        "repo_slug": repo_slug,
        "summary": f"included={len(files_out)} omitted={len(omitted_out)} used_bytes={used_bytes}",
        "files": files_out,
        "omitted": omitted_out,
    }


def _normalize_context_pack(doc: dict[str, Any] | None, *, goal: str, repo_root: Path, run_dir: Path) -> dict[str, Any]:
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
    if not files_out:
        fallback = _fallback_context_pack_from_file_request(
            run_dir=run_dir,
            repo_root=repo_root,
            goal=goal_text,
            repo_slug=repo_slug,
        )
        fallback_files = fallback.get("files", [])
        if isinstance(fallback_files, list) and fallback_files:
            return fallback

    summary = str(src.get("summary", "")).strip() or f"included={len(files_out)} omitted={len(omitted_out)}"
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
        out_results.append(
            {
                "url": url,
                "locator": locator,
                "fetched_at": str(row.get("fetched_at", "")).strip(),
                "excerpt": str(row.get("excerpt", "")),
                "why_relevant": str(row.get("why_relevant", "")),
                "risk_flags": row.get("risk_flags") if isinstance(row.get("risk_flags"), list) else [],
            }
        )
    return {
        "schema_version": "ctcp-find-web-v1",
        "constraints": constraints,
        "results": out_results,
    }


def _normalize_guardrails_md(raw_text: str) -> str:
    kv: dict[str, str] = {}
    for line in (raw_text or "").splitlines():
        match = re.match(r"^\s*([A-Za-z0-9_\-]+)\s*:\s*(.+?)\s*$", line)
        if not match:
            continue
        kv[match.group(1).strip().lower()] = match.group(2).strip()

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
        lines.append(f"max_queries: {_to_int('max_queries', default=2, minimum=1, maximum=20)}")
        lines.append(f"max_pages: {_to_int('max_pages', default=2, minimum=1, maximum=50)}")
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
    elif reasons:
        for row in reasons:
            lines.append(f"- {row}")
    else:
        lines.append("- requires follow-up fixes")
    lines += ["", "Required Fix/Artifacts:"]
    lines.append("- none" if verdict == "APPROVE" else "- provide corrected artifact and rerun review")
    lines.append("")
    return "\n".join(lines)


def _parse_plan_scope_allow(raw_text: str) -> list[str]:
    items: list[str] = []
    for raw in str(raw_text or "").splitlines():
        line = raw.strip()
        if not line.lower().startswith("scope-allow:"):
            continue
        payload = line.split(":", 1)[1]
        for chunk in payload.split(","):
            candidate = _normalize_scope_allow_entry(chunk)
            if candidate and candidate not in items:
                items.append(candidate)
    return items


def _normalize_scope_allow_entry(raw: str) -> str:
    text = str(raw or "").strip().replace("\\", "/")
    text = text.strip("`'\"")
    if not text or "://" in text or text.startswith("/") or text.startswith("../"):
        return ""
    if re.match(r"^[A-Za-z]:", text):
        return ""
    while text.startswith("./"):
        text = text[2:]
    if not text or text.startswith("."):
        return ""
    return text


def _goal_scope_allow_hints(goal: str) -> list[str]:
    out: list[str] = []
    for match in _GOAL_SCOPE_FILE_RE.finditer(str(goal or "")):
        candidate = _normalize_scope_allow_entry(match.group(1))
        if candidate and candidate not in out:
            out.append(candidate)
    return out


def _normalize_plan_md(raw_text: str, *, signed: bool, goal: str) -> str:
    status = "SIGNED" if signed else "DRAFT"
    scope_allow: list[str] = []
    for candidate in [*_DEFAULT_PLAN_SCOPE_ALLOW, *_parse_plan_scope_allow(raw_text), *_goal_scope_allow_hints(goal)]:
        if candidate and candidate not in scope_allow:
            scope_allow.append(candidate)
    project_generation_lines: list[str] = []
    if is_project_generation_goal(goal):
        project_generation_lines = [
            "Project-Generation: true",
            "Deliverables: runnable_app,README,startup_steps,verify_report,final_screenshot,final_package",
            "Verification: artifacts/verify_report.json must prove the generated project starts and passes acceptance checks",
            "Delivery: README with startup steps, final screenshot, and final project package are required before completion",
        ]
    return "\n".join(
        [
            f"Status: {status}",
            f"Scope-Allow: {','.join(scope_allow)}",
            "Scope-Deny: .git/,build/,build_lite/,dist/,runs/",
            "Gates: lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,lite_replay,python_unit_tests",
            "Budgets: max_iterations=3,max_files=20,max_total_bytes=200000",
            "Stop: scope_violation=true,repeated_failure=2,missing_plan_fields=true",
            "Behaviors: B001,B002,B003,B004,B005,B006,B007,B008,B009,B010,B011,B012,B013,B014,B015,B016,B017,B018,B019,B020,B021,B022,B023,B024,B025,B026,B027,B028,B029,B030,B031,B032,B033,B034,B035",
            "Results: R001,R002,R003,R004,R005",
            f"Goal: {goal or 'dispatch-goal'}",
            *project_generation_lines,
            "",
        ]
    )


def _normalize_json_artifact(*, repo_root: Path, run_dir: Path, request: dict[str, Any], raw_text: str) -> tuple[str, str]:
    role = str(request.get("role", "")).strip().lower()
    action = str(request.get("action", "")).strip().lower()
    goal = str(request.get("goal", "")).strip()
    doc = _extract_json_dict(raw_text)

    if formal_api_only_enabled() and requires_formal_api(role, action) and action in {
        "output_contract_freeze",
        "source_generation",
        "docs_generation",
        "workflow_generation",
        "artifact_manifest_build",
        "deliver",
    }:
        if doc is None:
            return "", f"formal_api_only forbids local normalizer synthesis for role={role} action={action}: agent output is not valid JSON object"
        return _to_json_text(doc), ""

    if role == "chair" and action == "file_request":
        return _to_json_text(_normalize_file_request(doc, goal=goal)), ""
    if role == "chair":
        chair_builders: dict[str, Any] = {
            "output_contract_freeze": lambda: normalize_output_contract_freeze(doc, goal=goal, run_dir=run_dir),
            "source_generation": lambda: normalize_source_generation(doc, goal=goal, run_dir=run_dir),
            "docs_generation": lambda: normalize_docs_generation(doc, goal=goal, run_dir=run_dir),
            "workflow_generation": lambda: normalize_workflow_generation(doc, goal=goal, run_dir=run_dir),
            "artifact_manifest_build": lambda: normalize_project_manifest(doc, goal=goal, run_dir=run_dir),
            "deliver": lambda: normalize_deliverable_index(doc, goal=goal, run_dir=run_dir),
        }
        if action in chair_builders:
            return _to_json_text(chair_builders[action]()), ""
    if role == "librarian" and action == "context_pack":
        return _to_json_text(_normalize_context_pack(doc, goal=goal, repo_root=repo_root, run_dir=run_dir)), ""
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
    policy_path = repo_root / "policy" / "allowed_changes.yaml"
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


def _render_whiteboard_md(request: dict[str, Any]) -> str:
    wb = request.get("whiteboard")
    lines = ["# WHITEBOARD", ""]
    if not isinstance(wb, dict):
        lines += ["- none", ""]
        return "\n".join(lines)

    path = str(wb.get("path", "")).strip()
    query = str(wb.get("query", "")).strip()
    lookup_error = str(wb.get("lookup_error", "")).strip()
    hits = wb.get("hits")
    snapshot = wb.get("snapshot")

    if path:
        lines.append(f"- path: `{path}`")
    if query:
        lines.append(f"- librarian_query: `{query}`")
    if lookup_error:
        lines.append(f"- librarian_error: `{lookup_error}`")
    lines.append("")

    if isinstance(hits, list) and hits:
        lines.append("## Librarian Hits")
        for idx, item in enumerate(hits[:4], start=1):
            if not isinstance(item, dict):
                continue
            hp = str(item.get("path", "")).strip()
            if not hp:
                continue
            try:
                start = int(item.get("start_line", 1) or 1)
            except Exception:
                start = 1
            snippet = re.sub(r"\s+", " ", str(item.get("snippet", "")).strip())
            if len(snippet) > 180:
                snippet = snippet[:177].rstrip() + "..."
            lines.append(f"- {idx}. `{hp}:{start}` {snippet}")
        lines.append("")

    if isinstance(snapshot, dict):
        entries = snapshot.get("entries")
        if isinstance(entries, list) and entries:
            lines.append("## Snapshot Tail")
            for item in entries[-4:]:
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role", "")).strip() or "unknown"
                kind = str(item.get("kind", "")).strip() or "note"
                text = re.sub(r"\s+", " ", str(item.get("text", "")).strip())
                if len(text) > 180:
                    text = text[:177].rstrip() + "..."
                lines.append(f"- [{role}/{kind}] {text}")
            lines.append("")

    if len(lines) <= 2:
        lines += ["- none", ""]
    return "\n".join(lines)


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
    _write_fix_brief(repo_root=repo_root, run_dir=run_dir, goal=goal, reason=reason, out_path=fix_brief_path)
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
    if role.lower() == "patchmaker":
        lines += [
            "## Patch Format Requirements",
            "",
            "For creating new files:",
            "- Use hunk header: @@ -0,0 +1,N @@ where N is the number of lines in the new file",
            "- Example for a 57-line file: @@ -0,0 +1,57 @@",
            "- WRONG: @@ -0,57 +1,57 @@ (this is invalid)",
            "",
            "For modifying existing files:",
            "- Use standard hunk header: @@ -start,count +start,count @@",
            "- Example: @@ -10,5 +10,7 @@ (removes 5 lines starting at 10, adds 7 lines starting at 10)",
            "",
        ]

    for key in ("context", "constraints", "fix_brief", "externals"):
        path = evidence[key]
        lines += [f"## {path.name}", _read_text(path, limit=18000), ""]
    lines += [_render_whiteboard_md(request), ""]
    return "\n".join(lines)


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


def normalize_target_payload(*, repo_root: Path, run_dir: Path, request: dict[str, Any], raw_text: str) -> tuple[str, str]:
    target_rel = str(request.get("target_path", "")).strip()
    if target_rel.lower().endswith(".json"):
        return _normalize_json_artifact(
            repo_root=repo_root,
            run_dir=run_dir,
            request=request,
            raw_text=raw_text,
        )
    if target_rel.lower().endswith("guardrails.md"):
        return _normalize_guardrails_md(raw_text), ""
    if target_rel.lower().endswith("analysis.md"):
        return _normalize_analysis_md(raw_text, goal=str(request.get("goal", "")).strip()), ""
    if target_rel.lower().endswith("artifacts/plan.md"):
        return _normalize_plan_md(raw_text, signed=True, goal=str(request.get("goal", "")).strip()), ""
    if target_rel.lower().endswith("artifacts/plan_draft.md"):
        return _normalize_plan_md(raw_text, signed=False, goal=str(request.get("goal", "")).strip()), ""
    if target_rel.lower().endswith("reviews/review_contract.md"):
        return _normalize_review_md(raw_text, title="Contract Review"), ""
    if target_rel.lower().endswith("reviews/review_cost.md"):
        return _normalize_review_md(raw_text, title="Cost Review"), ""
    return raw_text + "\n", ""


__all__ = [
    "_build_evidence_pack",
    "_extract_json_dict",
    "_fallback_context_pack_from_file_request",
    "_load_externals_doc",
    "_max_outbox_prompts",
    "_needs_patch",
    "_needs_plan",
    "_normalize_context_pack",
    "_normalize_file_request",
    "_normalize_find_web",
    "_normalize_guardrails_md",
    "_normalize_json_artifact",
    "_normalize_line_ranges",
    "_normalize_plan_md",
    "_normalize_review_md",
    "_record_failure_review",
    "_render_constraints_md",
    "_render_context_md",
    "_render_externals_md",
    "_render_fix_brief_seed",
    "_render_prompt",
    "_render_snippets",
    "_render_whiteboard_md",
    "_to_json_text",
    "_write_fix_brief",
    "normalize_patch_payload",
    "normalize_target_payload",
]
