#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

SEARCH_ROOTS = (
    "docs",
    "scripts",
    "tools",
    "src",
    "workflow_registry",
    "simlab",
)

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "runs",
    "_runs",
    "_runs_repo_gate",
    "build",
    "build_lite",
    "build_verify",
    "dist",
    ".venv",
}

SKIP_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".zip",
    ".7z",
    ".gz",
    ".bz2",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".obj",
    ".o",
    ".a",
    ".lib",
    ".pdf",
}


def _to_rel_posix(path: Path, repo_root: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _format_snippet(lines: list[str], start: int, end: int, match_lines: set[int]) -> str:
    chunks: list[str] = []
    for idx in range(start, end + 1):
        marker = ">" if idx in match_lines else " "
        chunks.append(f"{idx:>6}{marker} {lines[idx - 1]}")
    return "\n".join(chunks)


def _read_text_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _build_result(
    *,
    repo_root: Path,
    rel_path: str,
    line_numbers: list[int],
    fallback_text: str,
) -> dict[str, Any]:
    abs_path = (repo_root / rel_path).resolve()
    start_line = min(line_numbers) if line_numbers else 1
    end_line = max(line_numbers) if line_numbers else start_line
    try:
        lines = _read_text_lines(abs_path)
        if lines:
            span_start = max(1, start_line - 1)
            span_end = min(len(lines), start_line + 1)
            snippet = _format_snippet(lines, span_start, span_end, set(line_numbers))
        else:
            snippet = fallback_text
    except Exception:
        snippet = fallback_text

    return {
        "path": rel_path,
        "start_line": int(start_line),
        "end_line": int(end_line),
        "snippet": snippet.strip(),
    }


def _search_with_rg(repo_root: Path, query: str) -> list[dict[str, Any]]:
    rg = shutil.which("rg")
    if not rg:
        return []

    roots = [r for r in SEARCH_ROOTS if (repo_root / r).exists()]
    if not roots:
        roots = ["."]
    cmd = [
        rg,
        "-n",
        "--no-heading",
        "--fixed-strings",
        "--color",
        "never",
        query,
        *roots,
    ]
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode not in (0, 1):
        return []

    grouped: dict[str, list[tuple[int, str]]] = {}
    for raw in proc.stdout.splitlines():
        line = raw.rstrip("\n")
        if not line:
            continue
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        rel = Path(parts[0]).as_posix()
        try:
            lineno = int(parts[1])
        except Exception:
            continue
        text = parts[2]
        grouped.setdefault(rel, []).append((lineno, text))

    results: list[dict[str, Any]] = []
    for rel in sorted(grouped.keys()):
        rows = sorted(grouped[rel], key=lambda x: x[0])
        line_numbers = [row[0] for row in rows[:5]]
        fallback_text = "\n".join(f"{ln}: {txt}" for ln, txt in rows[:3])
        results.append(
            _build_result(
                repo_root=repo_root,
                rel_path=rel,
                line_numbers=line_numbers,
                fallback_text=fallback_text,
            )
        )
    return results


def _iter_candidate_files(repo_root: Path) -> list[Path]:
    out: list[Path] = []
    for base in SEARCH_ROOTS:
        root = (repo_root / base).resolve()
        if not root.exists() or not root.is_dir():
            continue
        for current, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIR_NAMES)
            for name in sorted(files):
                p = Path(current) / name
                if p.suffix.lower() in SKIP_SUFFIXES:
                    continue
                out.append(p)
    return out


def _search_with_python(repo_root: Path, query: str) -> list[dict[str, Any]]:
    if not query:
        return []
    results: list[dict[str, Any]] = []
    for path in _iter_candidate_files(repo_root):
        try:
            if path.stat().st_size > 1024 * 1024:
                continue
            lines = _read_text_lines(path)
        except Exception:
            continue

        match_lines: list[int] = []
        for idx, text in enumerate(lines, start=1):
            if query in text:
                match_lines.append(idx)
        if not match_lines:
            continue

        rel = _to_rel_posix(path, repo_root)
        start_line = match_lines[0]
        span_start = max(1, start_line - 1)
        span_end = min(len(lines), start_line + 1)
        snippet = _format_snippet(lines, span_start, span_end, set(match_lines[:5]))
        results.append(
            {
                "path": rel,
                "start_line": int(start_line),
                "end_line": int(match_lines[min(len(match_lines), 5) - 1]),
                "snippet": snippet.strip(),
            }
        )
    results.sort(key=lambda x: (str(x["path"]), int(x["start_line"])))
    return results


def search(repo_root: str | Path, query: str, k: int = 8) -> list[dict[str, Any]]:
    root = Path(repo_root).resolve()
    text = str(query or "").strip()
    if not text or k <= 0:
        return []

    results = _search_with_rg(root, text)
    if not results:
        results = _search_with_python(root, text)

    results.sort(key=lambda x: (str(x["path"]), int(x["start_line"])))
    return results[: int(k)]


def main() -> int:
    ap = argparse.ArgumentParser(description="Local Librarian deterministic search")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--query", required=True)
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()

    rows = search(repo_root=args.repo_root, query=args.query, k=args.k)
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

