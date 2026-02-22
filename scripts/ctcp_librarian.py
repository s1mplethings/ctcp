#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LAST_RUN_POINTER = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"

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


def _render_snippets(text: str, line_ranges: list[tuple[int, int]]) -> str:
    lines = text.splitlines()
    if not line_ranges:
        return ""
    chunks: list[str] = []
    for start, end in line_ranges:
        s = max(1, start)
        e = min(len(lines), end)
        if s > e:
            continue
        chunks.append(f"# lines {s}-{e}")
        for idx in range(s, e + 1):
            chunks.append(f"{idx:>6}: {lines[idx - 1]}")
    return "\n".join(chunks).strip()


def _safe_relpath(path: Path) -> str:
    rel = path.resolve().relative_to(ROOT.resolve()).as_posix()
    return rel


def _build_context_pack(file_request: dict[str, Any]) -> dict[str, Any]:
    if file_request.get("schema_version") != "ctcp-file-request-v1":
        raise SystemExit("[ctcp_librarian] file_request schema_version must be ctcp-file-request-v1")

    needs = file_request.get("needs", [])
    if not isinstance(needs, list):
        raise SystemExit("[ctcp_librarian] file_request.needs must be array")

    budget = file_request.get("budget", {})
    if not isinstance(budget, dict):
        raise SystemExit("[ctcp_librarian] file_request.budget must be object")
    max_files = int(budget.get("max_files", 0))
    max_total_bytes = int(budget.get("max_total_bytes", 0))
    if max_files <= 0 or max_total_bytes <= 0:
        raise SystemExit("[ctcp_librarian] budget.max_files and budget.max_total_bytes must be > 0")

    goal = str(file_request.get("goal", ""))
    reason = str(file_request.get("reason", "")).strip() or "requested by chair"

    files: list[dict[str, str]] = []
    omitted: list[dict[str, str]] = []
    used_bytes = 0

    for need in needs:
        if not isinstance(need, dict):
            continue
        rel = str(need.get("path", "")).strip()
        mode = str(need.get("mode", "")).strip().lower()
        if not rel:
            continue

        candidate = (ROOT / rel).resolve()
        if not _is_within(candidate, ROOT):
            omitted.append({"path": rel, "reason": "denied"})
            continue
        if not candidate.exists() or not candidate.is_file():
            omitted.append({"path": rel, "reason": "denied"})
            continue

        try:
            raw = candidate.read_text(encoding="utf-8", errors="replace")
        except Exception:
            omitted.append({"path": rel, "reason": "denied"})
            continue

        if mode == "full":
            content = raw
        elif mode == "snippets":
            ranges = _normalize_ranges(need.get("line_ranges", []))
            content = _render_snippets(raw, ranges)
            if not content:
                omitted.append({"path": rel, "reason": "irrelevant"})
                continue
        else:
            omitted.append({"path": rel, "reason": "irrelevant"})
            continue

        content_bytes = len(content.encode("utf-8"))
        if len(files) >= max_files or (used_bytes + content_bytes) > max_total_bytes:
            omitted.append({"path": rel, "reason": "too_large"})
            continue

        files.append(
            {
                "path": _safe_relpath(candidate),
                "why": f"{reason}; mode={mode}",
                "content": content,
            }
        )
        used_bytes += content_bytes

    summary = (
        f"included={len(files)} omitted={len(omitted)} "
        f"used_bytes={used_bytes} budget_files={max_files} budget_bytes={max_total_bytes}"
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
    print(
        "[ctcp_librarian] "
        + re.sub(
            r"\s+",
            " ",
            str(context_pack.get("summary", "")).strip(),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
