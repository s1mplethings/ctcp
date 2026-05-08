from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

MANDATORY_NEED_PATHS = (
    "AGENTS.md",
    "ai_context/00_AI_CONTRACT.md",
    "ai_context/CTCP_FAST_RULES.md",
)
OPTIONAL_MANDATORY_NEED_PATHS = (
    "docs/00_CORE.md",
    "PATCH_README.md",
)
DENY_PREFIXES = (
    ".git/",
    "runs/",
    "build/",
    "dist/",
    "node_modules/",
    "__pycache__/",
)
QUERY_STOPWORDS = {
    "about",
    "action",
    "agent",
    "api",
    "code",
    "context",
    "current",
    "file",
    "files",
    "for",
    "from",
    "generate",
    "generation",
    "goal",
    "local",
    "need",
    "needs",
    "project",
    "reason",
    "request",
    "source",
    "stage",
    "task",
    "that",
    "this",
    "with",
}
MAX_INFERRED_QUERIES = 8
MAX_INFERRED_FILES = 4
INFERRED_SNIPPET_CONTEXT_LINES = 12
ROLE_HINT_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("contract", ("agents.md", "contract", "quality_gates", "fast_rules", "patch_readme", "core")),
    ("planning", ("plan", "workflow", "execution_flow", "backlog", "current.md", "queue")),
    ("implementation", ("tools/", "scripts/", ".py", "provider", "source_generation")),
    ("validation", ("test", "verify", "gate", "check", "simlab", "quality")),
    ("delivery", ("readme", "package", "artifact", "report", "delivery")),
    ("product", ("north_star", "intent", "project_generation", "user", "ux")),
)


class LibrarianContractError(RuntimeError):
    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        stage: str,
        failed_path: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = str(error_code or "").strip() or "librarian_error"
        self.stage = str(stage or "").strip() or "build_context_pack"
        self.failed_path = str(failed_path or "").strip()
        self.details = dict(details or {})


def _raise_contract_error(
    error_code: str,
    message: str,
    *,
    stage: str,
    failed_path: str = "",
    details: dict[str, Any] | None = None,
) -> None:
    raise LibrarianContractError(
        error_code,
        message,
        stage=stage,
        failed_path=failed_path,
        details=details,
    )


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_failure_doc(
    run_dir: Path,
    *,
    stage: str,
    error_code: str,
    message: str,
    request_path: Path,
    target_path: Path,
    failed_path: str = "",
    details: dict[str, Any] | None = None,
) -> Path:
    failure_path = run_dir / "artifacts" / "context_pack.failure.json"
    _write_json(
        failure_path,
        {
            "schema_version": "ctcp-context-pack-failure-v1",
            "status": "failed",
            "stage": str(stage or "").strip() or "build_context_pack",
            "error_code": str(error_code or "").strip() or "librarian_error",
            "message": str(message or "").strip(),
            "request_path": request_path.relative_to(run_dir).as_posix(),
            "target_path": target_path.relative_to(run_dir).as_posix(),
            "failed_path": str(failed_path or "").strip(),
            "details": dict(details or {}),
        },
    )
    return failure_path


def _normalize_need_path(raw: str) -> tuple[str | None, str | None]:
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return None, "invalid_request"
    if text.startswith("/") or text.startswith("\\") or re.match(r"^[A-Za-z]:", text):
        return None, "denied"
    parts = [p for p in text.split("/") if p and p != "."]
    if not parts or any(p == ".." for p in parts):
        return None, "denied" if parts else "invalid_request"
    rel = "/".join(parts)
    return (rel, None) if rel else (None, "invalid_request")


def _is_denied_prefix(rel: str) -> bool:
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in DENY_PREFIXES)


def _normalize_ranges(raw: Any) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, list) or len(item) != 2:
            continue
        try:
            a = int(item[0])
            b = int(item[1])
        except Exception:
            continue
        if a <= 0 or b <= 0:
            continue
        out.append((min(a, b), max(a, b)))
    return out


def _clamp_ranges(ranges: list[tuple[int, int]], line_count: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for start, end in ranges:
        if line_count <= 0:
            continue
        s = max(1, min(start, line_count))
        e = max(1, min(end, line_count))
        out.append((min(s, e), max(s, e)))
    return out


def _utf8_bytes(text: str) -> int:
    return len(text.encode("utf-8", errors="replace"))


def _utf8_prefix(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    return text.encode("utf-8", errors="replace")[:max_bytes].decode("utf-8", errors="ignore")


def _resolve_mandatory_paths(repo_root: Path) -> list[str]:
    mandatory_paths: list[str] = []
    for rel in MANDATORY_NEED_PATHS:
        candidate = (repo_root / rel).resolve()
        if not _is_within(candidate, repo_root) or not candidate.exists() or not candidate.is_file():
            _raise_contract_error(
                "mandatory_missing",
                f"[ctcp_librarian] missing mandatory contract file: {rel}",
                stage="resolve_mandatory_paths",
                failed_path=rel,
            )
        mandatory_paths.append(rel)
    for rel in OPTIONAL_MANDATORY_NEED_PATHS:
        candidate = (repo_root / rel).resolve()
        if _is_within(candidate, repo_root) and candidate.exists() and candidate.is_file():
            mandatory_paths.append(rel)
    return mandatory_paths


def _prepend_mandatory_needs(needs: list[Any], mandatory_paths: list[str]) -> tuple[list[dict[str, Any]], set[str]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in mandatory_paths:
        key = rel.replace("\\", "/").lstrip("./")
        if key in seen:
            continue
        merged.append({"path": rel, "mode": "full"})
        seen.add(key)
    for need in needs:
        if not isinstance(need, dict):
            continue
        rel = str(need.get("path", "")).strip().replace("\\", "/").lstrip("./")
        if not rel or rel in seen:
            continue
        merged.append(need)
        seen.add(rel)
    return merged, {p.replace("\\", "/").lstrip("./") for p in mandatory_paths}


def _request_text_for_inference(file_request: dict[str, Any]) -> str:
    chunks: list[str] = [
        str(file_request.get("goal", "")),
        str(file_request.get("reason", "")),
    ]
    for need in file_request.get("needs", []):
        if not isinstance(need, dict):
            continue
        chunks.append(str(need.get("path", "")))
        chunks.append(str(need.get("why", "")))
    return "\n".join(chunks)


def _split_query_terms(text: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_./-]{2,}", text):
        cleaned = raw.strip("._/-").replace("\\", "/")
        if not cleaned:
            continue
        candidates = [cleaned]
        if "/" in cleaned:
            stem = Path(cleaned).stem
            if stem:
                candidates.append(stem)
        for item in candidates:
            token = item.strip("._/-")
            if not token:
                continue
            lowered = token.lower()
            if lowered in QUERY_STOPWORDS or len(lowered) < 4:
                continue
            if "." in lowered and not lowered.endswith((".py", ".md", ".json", ".yaml", ".yml", ".txt")):
                continue
            if lowered in seen:
                continue
            seen.add(lowered)
            terms.append(token)
            if len(terms) >= MAX_INFERRED_QUERIES:
                return terms
    return terms


def _known_need_paths(needs: list[dict[str, Any]], mandatory_paths: list[str]) -> set[str]:
    out = {p.replace("\\", "/").lstrip("./") for p in mandatory_paths}
    for need in needs:
        raw = str(need.get("path", ""))
        rel, rel_err = _normalize_need_path(raw)
        if rel and not rel_err:
            out.add(rel)
    return out


def _infer_context_needs(
    *,
    file_request: dict[str, Any],
    repo_root: Path,
    existing_paths: set[str],
    max_files: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if max_files <= 0:
        return [], {"strategy": "request_keyword_repo_search", "queries": [], "candidates": [], "selected": []}
    queries = _split_query_terms(_request_text_for_inference(file_request))
    selected: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    selected_paths: set[str] = set()
    try:
        from tools import local_librarian
    except Exception as exc:
        return [], {
            "strategy": "request_keyword_repo_search",
            "queries": queries,
            "candidates": [],
            "selected": [],
            "error": f"search_unavailable:{exc}",
        }

    for query in queries:
        try:
            rows = local_librarian.search(repo_root=repo_root, query=query, k=4)
        except Exception as exc:
            candidates.append({"query": query, "path": "", "reason": f"search_failed:{exc}"})
            continue
        for row in rows:
            rel = str(row.get("path", "")).strip().replace("\\", "/").lstrip("./")
            if not rel:
                continue
            if rel in existing_paths or rel in selected_paths:
                candidates.append({"query": query, "path": rel, "reason": "duplicate"})
                continue
            if _is_denied_prefix(rel):
                candidates.append({"query": query, "path": rel, "reason": "denied"})
                continue
            start = max(1, int(row.get("start_line", 1)) - INFERRED_SNIPPET_CONTEXT_LINES)
            end = max(start, int(row.get("end_line", start)) + INFERRED_SNIPPET_CONTEXT_LINES)
            need = {
                "path": rel,
                "mode": "snippets",
                "line_ranges": [[start, end]],
                "why": f"inferred_context: query={query}",
            }
            selected.append(need)
            selected_paths.add(rel)
            candidates.append({"query": query, "path": rel, "reason": "selected", "line_ranges": [[start, end]]})
            if len(selected) >= max_files:
                return selected, {
                    "strategy": "request_keyword_repo_search",
                    "queries": queries,
                    "candidates": candidates,
                    "selected": [str(item.get("path", "")) for item in selected],
                }
    return selected, {
        "strategy": "request_keyword_repo_search",
        "queries": queries,
        "candidates": candidates,
        "selected": [str(item.get("path", "")) for item in selected],
    }


def _increase_budget_error(mandatory_paths: list[str], mandatory_total_bytes: int) -> str:
    return (
        "[ctcp_librarian] budget too small for mandatory contract files; "
        f"requires max_files>={len(mandatory_paths)} and max_total_bytes>={mandatory_total_bytes}. "
        "Please increase budget.max_files and budget.max_total_bytes."
    )


def _mandatory_budget_error(mandatory_paths: list[str], mandatory_total_bytes: int) -> None:
    _raise_contract_error(
        "budget_too_small",
        _increase_budget_error(mandatory_paths, mandatory_total_bytes),
        stage="build_context_pack",
        details={
            "required_files": len(mandatory_paths),
            "required_total_bytes": mandatory_total_bytes,
        },
    )


def _read_candidate_text(candidate: Path, *, rel: str, is_mandatory: bool) -> str | None:
    try:
        return candidate.read_text(encoding="utf-8", errors="replace")
    except Exception:
        if is_mandatory:
            _raise_contract_error(
                "mandatory_read_failed",
                f"[ctcp_librarian] failed to read mandatory contract file: {rel}",
                stage="build_context_pack",
                failed_path=rel,
            )
        return None


def _append_need_content(
    *,
    files: list[dict[str, Any]],
    omitted: list[dict[str, str]],
    need: dict[str, Any],
    repo_root: Path,
    mandatory_need_keys: set[str],
    mandatory_paths: list[str],
    mandatory_total_bytes: int,
    request_reason: str,
    used_files: int,
    used_bytes: int,
    max_files: int,
    max_total_bytes: int,
    budget_stopped: bool,
) -> tuple[int, int, bool]:
    raw_rel = str(need.get("path", ""))
    rel, rel_err = _normalize_need_path(raw_rel)
    if rel is None:
        omitted.append({"path": str(raw_rel or ""), "reason": rel_err or "invalid_request"})
        return used_files, used_bytes, budget_stopped

    is_mandatory = rel in mandatory_need_keys
    if budget_stopped and not is_mandatory:
        omitted.append({"path": rel, "reason": "budget_exceeded"})
        return used_files, used_bytes, budget_stopped
    if _is_denied_prefix(rel):
        if is_mandatory:
            _raise_contract_error(
                "mandatory_denied",
                f"[ctcp_librarian] mandatory contract path denied by prefix rule: {rel}",
                stage="build_context_pack",
                failed_path=rel,
            )
        omitted.append({"path": rel, "reason": "denied"})
        return used_files, used_bytes, budget_stopped

    candidate = (repo_root / rel).resolve()
    if not _is_within(candidate, repo_root):
        if is_mandatory:
            _raise_contract_error(
                "mandatory_outside_repo",
                f"[ctcp_librarian] mandatory contract path is outside repo: {rel}",
                stage="build_context_pack",
                failed_path=rel,
            )
        omitted.append({"path": rel, "reason": "denied"})
        return used_files, used_bytes, budget_stopped
    if not candidate.exists() or not candidate.is_file():
        if is_mandatory:
            _raise_contract_error(
                "mandatory_missing",
                f"[ctcp_librarian] mandatory contract file missing: {rel}",
                stage="build_context_pack",
                failed_path=rel,
            )
        omitted.append({"path": rel, "reason": "not_found"})
        return used_files, used_bytes, budget_stopped

    raw = _read_candidate_text(candidate, rel=rel, is_mandatory=is_mandatory)
    if raw is None:
        omitted.append({"path": rel, "reason": "denied"})
        return used_files, used_bytes, budget_stopped
    if used_files >= max_files:
        if is_mandatory:
            _mandatory_budget_error(mandatory_paths, mandatory_total_bytes)
        omitted.append({"path": rel, "reason": "budget_exceeded"})
        return used_files, used_bytes, True

    mode = str(need.get("mode", "")).strip().lower()
    remaining_bytes = max_total_bytes - used_bytes
    explicit_why = str(need.get("why", "")).strip()
    why = "mandatory_contract" if is_mandatory else (explicit_why or f"requested:{request_reason}")
    if mode == "full":
        full_bytes = _utf8_bytes(raw)
        if is_mandatory and full_bytes > remaining_bytes:
            _mandatory_budget_error(mandatory_paths, mandatory_total_bytes)
        if full_bytes <= remaining_bytes:
            files.append(_context_file_row(path=rel, why=why, content=raw))
            return used_files + 1, used_bytes + full_bytes, budget_stopped
        if remaining_bytes <= 0:
            omitted.append({"path": rel, "reason": "budget_exceeded"})
            return used_files, used_bytes, True
        truncated = _utf8_prefix(raw, remaining_bytes)
        if not truncated:
            omitted.append({"path": rel, "reason": "budget_exceeded"})
            return used_files, used_bytes, True
        row = _context_file_row(path=rel, why=why, content=truncated)
        row["truncated"] = True
        files.append(row)
        return used_files + 1, used_bytes + _utf8_bytes(truncated), True
    if mode == "snippets":
        ranges = _clamp_ranges(_normalize_ranges(need.get("line_ranges", [])), len(raw.splitlines()))
        if not ranges:
            omitted.append({"path": rel, "reason": "invalid_request"})
            return used_files, used_bytes, budget_stopped
        lines = raw.splitlines()
        snippet = ""
        exceeded = False
        for start, end in ranges:
            block = "\n".join(lines[start - 1 : end])
            candidate_snippet = block if not snippet else (snippet + "\n" + block)
            if _utf8_bytes(candidate_snippet) > remaining_bytes:
                exceeded = True
                break
            snippet = candidate_snippet
        if not snippet:
            omitted.append({"path": rel, "reason": "budget_exceeded" if exceeded else "invalid_request"})
            return used_files, used_bytes, (True if exceeded else budget_stopped)
        files.append(_context_file_row(path=rel, why=why, content=snippet))
        return used_files + 1, used_bytes + _utf8_bytes(snippet), (True if exceeded else budget_stopped)
    if is_mandatory:
        _raise_contract_error(
            "mandatory_invalid_mode",
            f"[ctcp_librarian] mandatory contract file requires mode=full: {rel}",
            stage="build_context_pack",
            failed_path=rel,
        )
    omitted.append({"path": rel, "reason": "invalid_request"})
    return used_files, used_bytes, budget_stopped


def _role_hint_for_context(*, path: str, why: str, content: str) -> str:
    haystack = f"{path}\n{why}\n{content[:1200]}".lower()
    for role, tokens in ROLE_HINT_RULES:
        if any(token in haystack for token in tokens):
            return role
    return "reference"


def _context_file_row(*, path: str, why: str, content: str) -> dict[str, Any]:
    role_hint = _role_hint_for_context(path=path, why=why, content=content)
    must_follow_rules: list[str] = []
    avoid_patterns: list[str] = []
    lowered = content.lower()
    if role_hint == "contract" or any(token in lowered for token in ("must", "must not", "non-negotiable", "forbidden")):
        must_follow_rules.append("Treat this file as local authority or constraint evidence for downstream planning.")
    if any(token in lowered for token in ("template", "fallback", "placeholder", "stub", "todo")):
        avoid_patterns.append("Do not convert local examples or placeholders into deterministic generated-project templates.")
    if role_hint == "validation":
        must_follow_rules.append("Use this as verification/gate context rather than product content.")
    return {
        "path": path,
        "why": why,
        "content": content,
        "role_hint": role_hint,
        "relevance_summary": f"{role_hint} context selected because {why}",
        "compression_hint": "Use metadata and snippets first; read full content only when the downstream stage needs exact wording.",
        "must_follow_rules": must_follow_rules,
        "avoid_patterns": avoid_patterns,
    }


def _knowledge_summary(files: list[dict[str, Any]], *, selected_count: int, omitted_count: int) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    priority_paths: list[str] = []
    for row in files:
        role = str(row.get("role_hint", "")).strip() or "reference"
        role_counts[role] = role_counts.get(role, 0) + 1
        if role in {"contract", "planning", "implementation", "validation"} and len(priority_paths) < 12:
            priority_paths.append(str(row.get("path", "")))
    return {
        "purpose": "local knowledge compression for downstream planner/source-generation API calls",
        "boundary": "evidence_only_not_task_assignment",
        "api_usage_guidance": "Prefer role_hint, relevance_summary, must_follow_rules, and avoid_patterns before sending full file content to an API agent.",
        "selected_file_count": selected_count,
        "omitted_file_count": omitted_count,
        "role_counts": role_counts,
        "priority_paths": priority_paths,
    }


def build_context_pack(
    file_request: dict[str, Any],
    *,
    repo_root: Path,
    get_repo_slug_fn: Callable[[Path], str],
) -> dict[str, Any]:
    if file_request.get("schema_version") != "ctcp-file-request-v1":
        _raise_contract_error(
            "invalid_schema",
            "[ctcp_librarian] file_request schema_version must be ctcp-file-request-v1",
            stage="validate_request",
        )
    needs = file_request.get("needs", [])
    if not isinstance(needs, list):
        _raise_contract_error("invalid_needs", "[ctcp_librarian] file_request.needs must be array", stage="validate_request")
    budget = file_request.get("budget", {})
    if not isinstance(budget, dict):
        _raise_contract_error("invalid_budget", "[ctcp_librarian] file_request.budget must be object", stage="validate_request")
    try:
        max_files = int(budget.get("max_files", 0))
        max_total_bytes = int(budget.get("max_total_bytes", 0))
    except Exception:
        _raise_contract_error(
            "invalid_budget_values",
            "[ctcp_librarian] budget.max_files and budget.max_total_bytes must be > 0",
            stage="validate_request",
        )
    if max_files <= 0 or max_total_bytes <= 0:
        _raise_contract_error(
            "invalid_budget_values",
            "[ctcp_librarian] budget.max_files and budget.max_total_bytes must be > 0",
            stage="validate_request",
        )

    mandatory_paths = _resolve_mandatory_paths(repo_root)
    needs, mandatory_need_keys = _prepend_mandatory_needs(needs, mandatory_paths)
    explicit_need_count = max(0, len(needs) - len(mandatory_paths))
    mandatory_total_bytes = 0
    for rel in mandatory_paths:
        candidate = (repo_root / rel).resolve()
        raw = _read_candidate_text(candidate, rel=rel, is_mandatory=True)
        mandatory_total_bytes += _utf8_bytes(raw or "")
    if max_files < len(mandatory_paths) or max_total_bytes < mandatory_total_bytes:
        _mandatory_budget_error(mandatory_paths, mandatory_total_bytes)

    goal = str(file_request.get("goal", ""))
    request_reason = str(file_request.get("reason", "")).strip() or "request"
    inferred_needs, selection_strategy = _infer_context_needs(
        file_request=file_request,
        repo_root=repo_root,
        existing_paths=_known_need_paths(needs, mandatory_paths),
        max_files=max(0, min(MAX_INFERRED_FILES, max_files - len(needs))),
    )
    needs = [*needs, *inferred_needs]
    files: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []
    used_files = 0
    used_bytes = 0
    budget_stopped = False
    for need in needs:
        if not isinstance(need, dict):
            continue
        used_files, used_bytes, budget_stopped = _append_need_content(
            files=files,
            omitted=omitted,
            need=need,
            repo_root=repo_root,
            mandatory_need_keys=mandatory_need_keys,
            mandatory_paths=mandatory_paths,
            mandatory_total_bytes=mandatory_total_bytes,
            request_reason=request_reason,
            used_files=used_files,
            used_bytes=used_bytes,
            max_files=max_files,
            max_total_bytes=max_total_bytes,
            budget_stopped=budget_stopped,
        )

    reason_counts: dict[str, int] = {}
    for row in omitted:
        reason = str(row.get("reason", "")).strip() or "unknown"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    reason_summary = ",".join(f"{k}:{reason_counts[k]}" for k in sorted(reason_counts))
    return {
        "schema_version": "ctcp-context-pack-v1",
        "goal": goal,
        "repo_slug": get_repo_slug_fn(repo_root),
        "summary": (
            f"included={len(files)} omitted={len(omitted)} "
            f"used_files={used_files}/{max_files} used_bytes={used_bytes}/{max_total_bytes}; "
            f"inferred_selected={len(selection_strategy.get('selected', []))}; "
            f"omitted_by_reason={reason_summary or 'none'}"
        ),
        "selection_strategy": {
            **selection_strategy,
            "mandatory_file_count": len(mandatory_paths),
            "explicit_need_count": explicit_need_count,
            "budget_max_files": max_files,
            "budget_max_total_bytes": max_total_bytes,
        },
        "knowledge_summary": _knowledge_summary(files, selected_count=len(files), omitted_count=len(omitted)),
        "files": files,
        "omitted": omitted,
    }
