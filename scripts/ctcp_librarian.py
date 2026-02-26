#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LAST_RUN_POINTER = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
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

try:
    from tools.run_paths import get_repo_slug
except ModuleNotFoundError:
    import sys

    sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_slug


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _resolve_run_dir(raw: str) -> Path:
    if raw.strip():
        run_dir = Path(raw).expanduser().resolve()
    else:
        if not LAST_RUN_POINTER.exists():
            raise SystemExit("[ctcp_librarian] missing LAST_RUN pointer; pass --run-dir")
        pointed = LAST_RUN_POINTER.read_text(encoding="utf-8").strip()
        if not pointed:
            raise SystemExit("[ctcp_librarian] LAST_RUN pointer is empty; pass --run-dir")
        run_dir = Path(pointed).expanduser().resolve()
    if _is_within(run_dir, ROOT):
        raise SystemExit(f"[ctcp_librarian] run_dir must be outside repo: {run_dir}")
    return run_dir


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalize_need_path(raw: str) -> tuple[str | None, str | None]:
    text = str(raw or "").strip().replace("\\", "/")
    if not text:
        return None, "invalid_request"
    if text.startswith("/") or text.startswith("\\"):
        return None, "denied"
    if re.match(r"^[A-Za-z]:", text):
        return None, "denied"

    parts = [p for p in text.split("/") if p and p != "."]
    if not parts:
        return None, "invalid_request"
    if any(p == ".." for p in parts):
        return None, "denied"

    rel = "/".join(parts)
    if not rel:
        return None, "invalid_request"
    return rel, None


def _is_denied_prefix(rel: str) -> bool:
    for prefix in DENY_PREFIXES:
        base = prefix.rstrip("/")
        if rel == base or rel.startswith(prefix):
            return True
    return False


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
        if a > b:
            a, b = b, a
        out.append((a, b))
    return out


def _clamp_ranges(ranges: list[tuple[int, int]], line_count: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for start, end in ranges:
        s = max(1, min(start, line_count if line_count > 0 else 1))
        e = max(1, min(end, line_count if line_count > 0 else 1))
        if s > e:
            s, e = e, s
        if line_count <= 0:
            continue
        out.append((s, e))
    return out


def _utf8_bytes(text: str) -> int:
    return len(text.encode("utf-8", errors="replace"))


def _utf8_prefix(text: str, max_bytes: int) -> str:
    if max_bytes <= 0:
        return ""
    raw = text.encode("utf-8", errors="replace")
    return raw[:max_bytes].decode("utf-8", errors="ignore")


def _resolve_mandatory_paths() -> list[str]:
    mandatory_paths: list[str] = []
    for rel in MANDATORY_NEED_PATHS:
        candidate = (ROOT / rel).resolve()
        if not _is_within(candidate, ROOT) or not candidate.exists() or not candidate.is_file():
            raise SystemExit(f"[ctcp_librarian] missing mandatory contract file: {rel}")
        mandatory_paths.append(rel)
    for rel in OPTIONAL_MANDATORY_NEED_PATHS:
        candidate = (ROOT / rel).resolve()
        if _is_within(candidate, ROOT) and candidate.exists() and candidate.is_file():
            mandatory_paths.append(rel)
    return mandatory_paths


def _prepend_mandatory_needs(
    needs: list[Any],
    mandatory_paths: list[str],
) -> tuple[list[dict[str, Any]], set[str]]:
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


def _increase_budget_error(mandatory_paths: list[str], mandatory_total_bytes: int) -> str:
    return (
        "[ctcp_librarian] budget too small for mandatory contract files; "
        f"requires max_files>={len(mandatory_paths)} and max_total_bytes>={mandatory_total_bytes}. "
        "Please increase budget.max_files and budget.max_total_bytes."
    )


def _build_context_pack(file_request: dict[str, Any]) -> dict[str, Any]:
    if file_request.get("schema_version") != "ctcp-file-request-v1":
        raise SystemExit("[ctcp_librarian] file_request schema_version must be ctcp-file-request-v1")

    needs = file_request.get("needs", [])
    if not isinstance(needs, list):
        raise SystemExit("[ctcp_librarian] file_request.needs must be array")

    budget = file_request.get("budget", {})
    if not isinstance(budget, dict):
        raise SystemExit("[ctcp_librarian] file_request.budget must be object")

    try:
        max_files = int(budget.get("max_files", 0))
        max_total_bytes = int(budget.get("max_total_bytes", 0))
    except Exception:
        raise SystemExit("[ctcp_librarian] budget.max_files and budget.max_total_bytes must be > 0")
    if max_files <= 0 or max_total_bytes <= 0:
        raise SystemExit("[ctcp_librarian] budget.max_files and budget.max_total_bytes must be > 0")

    mandatory_paths = _resolve_mandatory_paths()
    needs, mandatory_need_keys = _prepend_mandatory_needs(needs, mandatory_paths)

    mandatory_total_bytes = 0
    for rel in mandatory_paths:
        candidate = (ROOT / rel).resolve()
        try:
            mandatory_total_bytes += _utf8_bytes(candidate.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            raise SystemExit(f"[ctcp_librarian] failed to read mandatory contract file: {rel}")

    if max_files < len(mandatory_paths) or max_total_bytes < mandatory_total_bytes:
        raise SystemExit(_increase_budget_error(mandatory_paths, mandatory_total_bytes))

    goal = str(file_request.get("goal", ""))
    request_reason = str(file_request.get("reason", "")).strip() or "request"

    files: list[dict[str, Any]] = []
    omitted: list[dict[str, str]] = []
    used_files = 0
    used_bytes = 0
    budget_stopped = False

    for need in needs:
        if not isinstance(need, dict):
            continue

        raw_rel = str(need.get("path", ""))
        rel, rel_err = _normalize_need_path(raw_rel)
        if rel is None:
            reason = rel_err or "invalid_request"
            omitted.append({"path": str(raw_rel or ""), "reason": reason})
            continue

        is_mandatory = rel in mandatory_need_keys

        if budget_stopped and not is_mandatory:
            omitted.append({"path": rel, "reason": "budget_exceeded"})
            continue

        if _is_denied_prefix(rel):
            if is_mandatory:
                raise SystemExit(f"[ctcp_librarian] mandatory contract path denied by prefix rule: {rel}")
            omitted.append({"path": rel, "reason": "denied"})
            continue

        candidate = (ROOT / rel).resolve()
        if not _is_within(candidate, ROOT):
            if is_mandatory:
                raise SystemExit(f"[ctcp_librarian] mandatory contract path is outside repo: {rel}")
            omitted.append({"path": rel, "reason": "denied"})
            continue
        if not candidate.exists() or not candidate.is_file():
            if is_mandatory:
                raise SystemExit(f"[ctcp_librarian] mandatory contract file missing: {rel}")
            omitted.append({"path": rel, "reason": "not_found"})
            continue

        try:
            raw = candidate.read_text(encoding="utf-8", errors="replace")
        except Exception:
            if is_mandatory:
                raise SystemExit(f"[ctcp_librarian] failed to read mandatory contract file: {rel}")
            omitted.append({"path": rel, "reason": "denied"})
            continue

        if used_files >= max_files:
            if is_mandatory:
                raise SystemExit(_increase_budget_error(mandatory_paths, mandatory_total_bytes))
            omitted.append({"path": rel, "reason": "budget_exceeded"})
            budget_stopped = True
            continue

        mode = str(need.get("mode", "")).strip().lower()
        remaining_bytes = max_total_bytes - used_bytes
        why = "mandatory_contract" if is_mandatory else f"requested:{request_reason}"

        if mode == "full":
            full_bytes = _utf8_bytes(raw)
            if is_mandatory and full_bytes > remaining_bytes:
                raise SystemExit(_increase_budget_error(mandatory_paths, mandatory_total_bytes))

            if full_bytes <= remaining_bytes:
                files.append({"path": rel, "why": why, "content": raw})
                used_files += 1
                used_bytes += full_bytes
                continue

            if remaining_bytes <= 0:
                omitted.append({"path": rel, "reason": "budget_exceeded"})
                budget_stopped = True
                continue

            truncated = _utf8_prefix(raw, remaining_bytes)
            if not truncated:
                omitted.append({"path": rel, "reason": "budget_exceeded"})
                budget_stopped = True
                continue

            files.append({"path": rel, "why": why, "content": truncated, "truncated": True})
            used_files += 1
            used_bytes += _utf8_bytes(truncated)
            budget_stopped = True
            continue

        if mode == "snippets":
            ranges = _normalize_ranges(need.get("line_ranges", []))
            if not ranges:
                omitted.append({"path": rel, "reason": "invalid_request"})
                continue

            lines = raw.splitlines()
            clamped = _clamp_ranges(ranges, len(lines))
            if not clamped:
                omitted.append({"path": rel, "reason": "invalid_request"})
                continue

            snippet = ""
            exceeded = False
            for start, end in clamped:
                block = "\n".join(lines[start - 1 : end])
                candidate_snippet = block if not snippet else (snippet + "\n" + block)
                if _utf8_bytes(candidate_snippet) > remaining_bytes:
                    exceeded = True
                    break
                snippet = candidate_snippet

            if not snippet:
                omitted.append({"path": rel, "reason": "budget_exceeded" if exceeded else "invalid_request"})
                if exceeded:
                    budget_stopped = True
                continue

            files.append({"path": rel, "why": why, "content": snippet})
            used_files += 1
            used_bytes += _utf8_bytes(snippet)
            if exceeded:
                budget_stopped = True
            continue

        if is_mandatory:
            raise SystemExit(f"[ctcp_librarian] mandatory contract file requires mode=full: {rel}")
        omitted.append({"path": rel, "reason": "invalid_request"})

    reason_counts: dict[str, int] = {}
    for row in omitted:
        reason = str(row.get("reason", "")).strip() or "unknown"
        reason_counts[reason] = reason_counts.get(reason, 0) + 1
    reason_summary = ",".join(f"{k}:{reason_counts[k]}" for k in sorted(reason_counts))

    summary = (
        f"included={len(files)} omitted={len(omitted)} "
        f"used_files={used_files}/{max_files} used_bytes={used_bytes}/{max_total_bytes}; "
        f"omitted_by_reason={reason_summary or 'none'}"
    )

    return {
        "schema_version": "ctcp-context-pack-v1",
        "goal": goal,
        "repo_slug": get_repo_slug(ROOT),
        "summary": summary,
        "files": files,
        "omitted": omitted,
    }


def main() -> int:
    # BEHAVIOR_ID: B033
    ap = argparse.ArgumentParser(description="CTCP local librarian (read-only context pack supplier)")
    ap.add_argument("--run-dir", default="")
    args = ap.parse_args()

    run_dir = _resolve_run_dir(args.run_dir)
    request_path = run_dir / "artifacts" / "file_request.json"
    if not request_path.exists():
        print(f"[ctcp_librarian] missing file_request: {request_path}")
        return 1

    file_request = _read_json(request_path)
    context_pack = _build_context_pack(file_request)
    out_path = run_dir / "artifacts" / "context_pack.json"
    _write_json(out_path, context_pack)
    print(f"[ctcp_librarian] wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
