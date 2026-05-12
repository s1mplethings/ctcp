from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any


SEARCH_ROOTS = (
    "docs",
    "contracts",
    "specs",
    "ai_context",
    "meta/reports/archive",
    "issue_memory",
    "tools",
    "scripts",
    "tests",
    "workflow_registry",
    "library_docs",
    "recipes",
    "artifacts",
)
SKIP_DIRS = {".git", "__pycache__", "node_modules", "build", "build_lite", "dist", ".pytest_cache"}
TEXT_SUFFIXES = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml"}
STOPWORDS = {
    "and",
    "for",
    "from",
    "into",
    "local",
    "need",
    "project",
    "request",
    "source",
    "that",
    "the",
    "this",
    "with",
}


def build_hybrid_retrieval(
    *,
    repo_root: Path,
    query: str,
    task_type: str = "",
    project_domain: str = "",
    exclude_paths: set[str] | None = None,
    max_candidates: int = 80,
    max_selected: int = 12,
) -> dict[str, Any]:
    terms = _query_terms(query)
    excluded = {str(item).replace("\\", "/").lstrip("./") for item in (exclude_paths or set())}
    candidates = _candidate_rows(repo_root=repo_root, terms=terms, excluded=excluded, limit=max_candidates)
    keyword_hits = _score_keyword(candidates, terms)
    vector_hits = _score_token_vector(candidates, terms)
    merged = _merge_hits(keyword_hits, vector_hits, max_selected=max_selected)
    missing = _missing_context(merged, query=query)
    return {
        "schema_version": "ctcp-retrieval-trace-v1",
        "query": query,
        "task_type": task_type,
        "project_domain": project_domain,
        "query_terms": terms,
        "stages": [
            {
                "stage": "keyword_search",
                "candidate_count": len(keyword_hits),
                "top_paths": [row["path"] for row in keyword_hits[:8]],
            },
            {
                "stage": "token_vector_search",
                "candidate_count": len(vector_hits),
                "top_paths": [row["path"] for row in vector_hits[:8]],
            },
            {
                "stage": "merge_and_dedupe",
                "candidate_count": len(merged),
                "top_paths": [row["path"] for row in merged[:8]],
            },
        ],
        "selected": merged,
        "missing_context": missing,
    }


def selected_context_from_trace(trace: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in trace.get("selected", []):
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "source": str(row.get("path", "")),
                "reason": str(row.get("reason", "")) or "hybrid local retrieval match",
                "trust_level": _trust_level(str(row.get("path", ""))),
                "snippets": [str(row.get("snippet", ""))[:1000]],
                "metadata": {
                    "namespace": _namespace(str(row.get("path", ""))),
                    "score": row.get("score", 0),
                    "retrieval_modes": list(row.get("retrieval_modes", [])),
                    "start_line": row.get("start_line", 1),
                    "end_line": row.get("end_line", 1),
                },
            }
        )
    return out


def constraints_for_downstream(selected_context: list[dict[str, Any]]) -> list[str]:
    constraints = {
        "Librarian provides evidence and constraints only; it must not author generated project source.",
        "Do not treat local templates, examples, or reports as provider-authored business implementation.",
        "Prefer mature libraries and thin glue code when selected context documents library-first rules.",
    }
    for row in selected_context:
        text = " ".join(str(snippet) for snippet in row.get("snippets", [])).lower()
        if "do not" in text or "must not" in text or "forbidden" in text:
            constraints.add("Preserve MUST/MUST NOT rules from selected context in downstream prompts.")
        if "source_generation" in text:
            constraints.add("Use source_generation evidence to repair provider-authored files, not to bypass validation.")
        if "typer" in text or "pydantic" in text or "rich" in text:
            constraints.add("For CLI/data/rendering tasks, use selected libraries directly instead of hand-rolled replacements.")
    return sorted(constraints)


def _candidate_rows(*, repo_root: Path, terms: list[str], excluded: set[str], limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in _iter_text_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        if rel in excluded:
            continue
        text = _read_text(path)
        if not text:
            continue
        lowered = text.lower()
        path_l = rel.lower()
        if terms and not any(term.lower() in lowered or term.lower() in path_l for term in terms):
            continue
        line_no, snippet = _best_snippet(text, terms)
        rows.append({"path": rel, "content": text, "start_line": line_no, "end_line": line_no + max(0, snippet.count("\n")), "snippet": snippet})
        if len(rows) >= limit:
            break
    return rows


def _iter_text_files(repo_root: Path):
    for root_name in SEARCH_ROOTS:
        root = repo_root / root_name
        if not root.exists():
            continue
        if root.is_file():
            if root.suffix.lower() in TEXT_SUFFIXES:
                yield root
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in SKIP_DIRS or part.startswith(".agent_private") for part in path.parts):
                continue
            yield path


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def _query_terms(query: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_./-]{2,}", str(query or "")):
        token = raw.strip("._/-").lower()
        if not token or token in STOPWORDS or len(token) < 4:
            continue
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out[:16]


def _score_keyword(candidates: list[dict[str, Any]], terms: list[str]) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for row in candidates:
        haystack = f"{row['path']}\n{row['content']}".lower()
        score = sum(haystack.count(term.lower()) for term in terms)
        if score <= 0:
            continue
        scored.append(_hit(row, score=float(score), mode="keyword", reason="keyword term match"))
    return sorted(scored, key=lambda item: (-float(item["score"]), str(item["path"])))


def _score_token_vector(candidates: list[dict[str, Any]], terms: list[str]) -> list[dict[str, Any]]:
    query_vec = _term_vector(" ".join(terms))
    scored: list[dict[str, Any]] = []
    for row in candidates:
        doc_vec = _term_vector(f"{row['path']} {row['snippet']} {row['content'][:4000]}")
        score = _cosine(query_vec, doc_vec)
        if score <= 0:
            continue
        scored.append(_hit(row, score=round(score, 6), mode="token_vector", reason="token-vector similarity"))
    return sorted(scored, key=lambda item: (-float(item["score"]), str(item["path"])))


def _merge_hits(keyword_hits: list[dict[str, Any]], vector_hits: list[dict[str, Any]], *, max_selected: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for source in (keyword_hits, vector_hits):
        for row in source:
            path = str(row["path"])
            existing = merged.get(path)
            if existing is None:
                merged[path] = dict(row)
                continue
            existing["score"] = round(float(existing.get("score", 0)) + float(row.get("score", 0)), 6)
            modes = set(existing.get("retrieval_modes", []))
            modes.update(row.get("retrieval_modes", []))
            existing["retrieval_modes"] = sorted(modes)
            if len(str(row.get("snippet", ""))) > len(str(existing.get("snippet", ""))):
                existing["snippet"] = row["snippet"]
    return sorted(merged.values(), key=lambda item: (-float(item.get("score", 0)), str(item.get("path", ""))))[:max_selected]


def _hit(row: dict[str, Any], *, score: float, mode: str, reason: str) -> dict[str, Any]:
    return {
        "path": row["path"],
        "score": score,
        "retrieval_modes": [mode],
        "reason": reason,
        "start_line": row.get("start_line", 1),
        "end_line": row.get("end_line", 1),
        "snippet": row.get("snippet", ""),
    }


def _best_snippet(text: str, terms: list[str]) -> tuple[int, str]:
    lines = text.splitlines()
    best_index = 0
    best_score = -1
    for index, line in enumerate(lines):
        lowered = line.lower()
        score = sum(1 for term in terms if term in lowered)
        if score > best_score:
            best_score = score
            best_index = index
    start = max(0, best_index - 3)
    end = min(len(lines), best_index + 4)
    return start + 1, "\n".join(lines[start:end])


def _term_vector(text: str) -> dict[str, float]:
    vec: dict[str, float] = {}
    for token in _query_terms(text):
        vec[token] = vec.get(token, 0.0) + 1.0
    return vec


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(value * b.get(key, 0.0) for key, value in a.items())
    if dot <= 0:
        return 0.0
    norm_a = math.sqrt(sum(value * value for value in a.values()))
    norm_b = math.sqrt(sum(value * value for value in b.values()))
    if norm_a <= 0 or norm_b <= 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _missing_context(selected: list[dict[str, Any]], *, query: str) -> list[dict[str, str]]:
    lower_paths = " ".join(str(row.get("path", "")).lower() for row in selected)
    missing: list[dict[str, str]] = []
    query_l = query.lower()
    if any(token in query_l for token in ("typer", "pydantic", "rich", "library")) and "library_docs" not in lower_paths:
        missing.append({"kind": "library_docs", "reason": "no matching local library_docs files found"})
    if any(token in query_l for token in ("failure", "blocked", "repair", "source_generation")) and "meta/reports/archive" not in lower_paths:
        missing.append({"kind": "failure_memory", "reason": "no matching archived reports selected"})
    return missing


def _namespace(path: str) -> str:
    if path.startswith("docs/") or path.startswith("contracts/") or path.startswith("AGENTS.md"):
        return "ctcp_core_docs"
    if path.startswith("meta/reports/archive/") or path.startswith("issue_memory/"):
        return "ctcp_runtime_memory"
    if path.startswith("artifacts/librarian_experience_record"):
        return "ctcp_runtime_memory"
    if path.startswith("library_docs/"):
        return "library_docs"
    if path.startswith("recipes/") or path.startswith("workflow_registry/"):
        return "recipes"
    return "repo_context"


def _trust_level(path: str) -> str:
    if path.startswith(("docs/", "contracts/", "AGENTS.md", "ai_context/")):
        return "high"
    if path.startswith(("library_docs/", "recipes/")):
        return "medium"
    if path.startswith(("meta/reports/archive/", "issue_memory/")):
        return "medium"
    if path.startswith("artifacts/librarian_experience_record"):
        return "medium"
    return "low"


__all__ = ["build_hybrid_retrieval", "constraints_for_downstream", "selected_context_from_trace"]
