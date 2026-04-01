#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "meta" / "code_health" / "rules.json"


@dataclass
class FileMetrics:
    path: str
    total_lines: int
    code_lines: int
    import_count: int
    function_count: int
    longest_function_lines: int
    entrypoint: bool
    mixed_responsibility: bool
    responsibility_categories: list[str]
    churn_30d: int
    churn_90d: int
    risk_score: int
    risk_level: str
    reasons: list[str]


def _run_git(args: list[str], repo: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=repo,
            text=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        )
        return out
    except Exception:
        return ""


def _git_tracked_files(repo: Path) -> list[str]:
    out = _run_git(["ls-files"], repo)
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _git_untracked_files(repo: Path) -> list[str]:
    out = _run_git(["ls-files", "--others", "--exclude-standard"], repo)
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def _git_changed_files(repo: Path, baseline_ref: str | None) -> list[str]:
    changed: set[str] = set()
    if baseline_ref:
        out = _run_git(["diff", "--name-only", "--diff-filter=ACMRTUXB", baseline_ref, "--"], repo)
        for line in out.splitlines():
            line = line.strip()
            if line:
                changed.add(line)
    else:
        for cmd in (
            ["diff", "--name-only"],
            ["diff", "--cached", "--name-only"],
            ["ls-files", "--others", "--exclude-standard"],
        ):
            out = _run_git(cmd, repo)
            for line in out.splitlines():
                line = line.strip()
                if line:
                    changed.add(line)
    out = _run_git(["ls-files", "--others", "--exclude-standard"], repo)
    for line in out.splitlines():
        line = line.strip()
        if line:
            changed.add(line)
    return sorted(changed)


def _git_file_content(repo: Path, ref: str, path: str) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", "show", f"{ref}:{path}"],
            cwd=repo,
            text=True,
            encoding="utf-8",
            stderr=subprocess.DEVNULL,
        )
        return out
    except Exception:
        return None


def _git_churn_counts(repo: Path, days: int) -> dict[str, int]:
    out = _run_git(["log", f"--since={days}.days", "--name-only", "--pretty=format:"], repo)
    counts: dict[str, int] = {}
    for line in out.splitlines():
        p = line.strip()
        if not p:
            continue
        counts[p] = counts.get(p, 0) + 1
    return counts


def _is_entrypoint(path: str, patterns: list[str]) -> bool:
    p = path.replace("\\", "/")
    name = Path(p).name
    if name.startswith("main.") or name in {"main.py", "main.cpp", "main.c", "app.py", "app.js", "index.js", "index.ts"}:
        return True
    for pat in patterns:
        if fnmatch.fnmatch(p, pat):
            return True
    return False


def _detect_comment_style(ext: str, filename: str) -> tuple[tuple[str, ...], tuple[str, str] | None]:
    ext = ext.lower()
    if filename == "CMakeLists.txt" or ext in {".py", ".sh", ".ps1", ".psm1", ".cmake", ".yaml", ".yml"}:
        return ("#",), None
    if ext in {".js", ".jsx", ".ts", ".tsx", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".java", ".cs", ".go", ".rs"}:
        return ("//",), ("/*", "*/")
    if ext in {".html", ".htm", ".xml"}:
        return tuple(), ("<!--", "-->")
    return ("#", "//"), ("/*", "*/")


def _count_code_lines(path: Path, text: str) -> int:
    lines = text.splitlines()
    ext = path.suffix
    line_comments, block_comment = _detect_comment_style(ext, path.name)
    in_block = False
    code_lines = 0
    for raw in lines:
        s = raw
        stripped = s.strip()
        if not stripped:
            continue
        if block_comment:
            bstart, bend = block_comment
            cursor = s
            cleaned = ""
            while cursor:
                if in_block:
                    end_i = cursor.find(bend)
                    if end_i < 0:
                        cursor = ""
                        break
                    cursor = cursor[end_i + len(bend) :]
                    in_block = False
                    continue
                start_i = cursor.find(bstart)
                if start_i < 0:
                    cleaned += cursor
                    cursor = ""
                    break
                cleaned += cursor[:start_i]
                cursor = cursor[start_i + len(bstart) :]
                in_block = True
            s = cleaned
        if in_block:
            continue
        stripped2 = s.strip()
        if not stripped2:
            continue
        commented = False
        for marker in line_comments:
            if stripped2.startswith(marker):
                commented = True
                break
        if commented:
            continue
        code_lines += 1
    return code_lines


def _python_metrics(text: str) -> tuple[int, int, int]:
    import_count = 0
    function_count = 0
    longest = 0
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0, 0, 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_count += 1
            end_lineno = getattr(node, "end_lineno", None)
            start_lineno = getattr(node, "lineno", None)
            if end_lineno and start_lineno and end_lineno >= start_lineno:
                longest = max(longest, end_lineno - start_lineno + 1)
    return import_count, function_count, longest


def _regex_count(patterns: list[re.Pattern[str]], lines: list[str]) -> int:
    count = 0
    for line in lines:
        for pat in patterns:
            if pat.search(line):
                count += 1
                break
    return count


def _brace_function_lengths(lines: list[str], signatures: list[re.Pattern[str]]) -> list[int]:
    lengths: list[int] = []
    n = len(lines)
    i = 0
    while i < n:
        line = lines[i]
        if any(pat.search(line) for pat in signatures):
            start = i
            j = i
            seen_open = False
            depth = 0
            while j < n:
                chunk = lines[j]
                opens = chunk.count("{")
                closes = chunk.count("}")
                if opens > 0:
                    seen_open = True
                if seen_open:
                    depth += opens
                    depth -= closes
                    if depth <= 0 and seen_open:
                        lengths.append(j - start + 1)
                        i = j
                        break
                j += 1
        i += 1
    return lengths


def _script_function_lengths(lines: list[str], signatures: list[re.Pattern[str]]) -> list[int]:
    starts: list[int] = []
    for idx, line in enumerate(lines):
        if any(pat.search(line) for pat in signatures):
            starts.append(idx)
    if not starts:
        return []
    lengths: list[int] = []
    n = len(lines)
    for start in starts:
        depth = 0
        opened = False
        end = start
        for j in range(start, n):
            seg = lines[j]
            opens = seg.count("{")
            closes = seg.count("}")
            if opens > 0:
                opened = True
            if opened:
                depth += opens
                depth -= closes
                if depth <= 0:
                    end = j
                    break
        if end >= start:
            lengths.append(end - start + 1)
    return lengths


def _scope_paths_from_current(repo: Path) -> list[str]:
    current = repo / "meta" / "tasks" / "CURRENT.md"
    if not current.exists():
        return []
    text = current.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    raw: list[str] = []
    in_allowed = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        if lower.startswith("- allowed_behavior_change:"):
            in_allowed = True
            raw.extend(re.findall(r"`([^`]+)`", line))
            continue
        if in_allowed and re.match(r"^- [a-z0-9_]+:", stripped, flags=re.IGNORECASE):
            break
        if in_allowed:
            raw.extend(re.findall(r"`([^`]+)`", line))

    scopes: list[str] = []
    for item in raw:
        p = item.strip().replace("\\", "/")
        if not p:
            continue
        if p.startswith("meta/reports/archive/") or p.startswith("meta/tasks/archive/"):
            continue
        if "/" in p or p.endswith(".py") or p.endswith(".md") or p.endswith(".json") or p.endswith(".yml"):
            scopes.append(p)
    # keep stable order, dedupe
    seen: set[str] = set()
    out: list[str] = []
    for p in scopes:
        if p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _path_in_scope(path: str, scopes: list[str]) -> bool:
    p = path.replace("\\", "/")
    for scope in scopes:
        s = scope.replace("\\", "/")
        if not s:
            continue
        if "*" in s or "?" in s:
            if fnmatch.fnmatch(p, s):
                return True
            continue
        if s.endswith("/"):
            if p.startswith(s):
                return True
            continue
        if p == s:
            return True
        if p.startswith(s + "/"):
            return True
    return False


def _generic_metrics(path: Path, text: str) -> tuple[int, int, int]:
    ext = path.suffix.lower()
    lines = text.splitlines()

    if ext in {".js", ".jsx", ".ts", ".tsx"}:
        import_patterns = [
            re.compile(r"^\s*import\s+"),
            re.compile(r"^\s*const\s+.+?=\s*require\("),
        ]
        signatures = [
            re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+[A-Za-z_]\w*\s*\([^;]*\)\s*\{"),
            re.compile(r"^\s*(?:const|let|var)\s+[A-Za-z_]\w*\s*=\s*(?:async\s*)?\([^;]*\)\s*=>\s*\{"),
            re.compile(r"^\s*(?:export\s+)?(?:async\s+)?[A-Za-z_]\w*\s*\([^;]*\)\s*\{"),
        ]
    elif ext in {".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx", ".java", ".cs", ".go", ".rs"}:
        import_patterns = [
            re.compile(r"^\s*#\s*include\s+[<\"]"),
            re.compile(r"^\s*using\s+[A-Za-z_]"),
            re.compile(r"^\s*import\s+[A-Za-z_\.]"),
        ]
        signatures = [
            re.compile(r"^\s*(?:template\s*<[^>]+>\s*)?(?:[\w:<>\[\],~*&]+\s+)+[A-Za-z_]\w*\s*\([^;]*\)\s*(?:const\s*)?\{"),
        ]
    elif ext in {".ps1", ".psm1"}:
        import_patterns = [re.compile(r"^\s*(?:Import-Module|using\s+module)\b", re.IGNORECASE)]
        signatures = [re.compile(r"^\s*function\s+[A-Za-z_][\w-]*\b", re.IGNORECASE)]
    elif ext in {".sh"}:
        import_patterns = [re.compile(r"^\s*(?:source|\.)\s+")]
        signatures = [re.compile(r"^\s*(?:function\s+)?[A-Za-z_][A-Za-z0-9_]*\s*\(\)\s*\{")]
    else:
        import_patterns = [re.compile(r"^\s*import\s+"), re.compile(r"^\s*#\s*include\s+")]
        signatures = [re.compile(r"^\s*function\s+[A-Za-z_]\w*\s*\(")]

    import_count = _regex_count(import_patterns, lines)
    if ext in {".ps1", ".psm1", ".sh"}:
        lengths = _script_function_lengths(lines, signatures)
    else:
        lengths = _brace_function_lengths(lines, signatures)
    function_count = len(lengths)
    longest = max(lengths) if lengths else 0
    return import_count, function_count, longest


def _responsibility_mix(text: str) -> list[str]:
    lowered = text.lower()
    buckets: dict[str, tuple[str, ...]] = {
        "orchestration": ("orchestr", "dispatch", "pipeline", "state_machine", "workflow", "runner"),
        "io_network": ("http", "api", "request", "response", "telegram", "socket", "client"),
        "presentation": ("render", "reply", "view", "template", "html", "ui"),
        "persistence": ("store", "cache", "sqlite", "save", "load", "write", "read"),
        "domain_policy": ("policy", "rule", "decision", "validate", "normalize", "scor"),
    }
    categories: list[str] = []
    for name, words in buckets.items():
        hit = 0
        for word in words:
            hit += len(re.findall(rf"\b{re.escape(word)}\w*\b", lowered))
        if hit >= 3:
            categories.append(name)
    return categories


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _compute_risk(
    total_lines: int,
    longest_func: int,
    import_count: int,
    function_count: int,
    entrypoint: bool,
    mixed: bool,
    category_count: int,
    churn_90d: int,
    rules: dict[str, Any],
) -> tuple[int, list[str]]:
    t = rules["thresholds"]
    score = 0
    reasons: list[str] = []

    file_warn = int(t["file_lines_warn"])
    file_critical = int(t["file_lines_critical"])
    func_warn = int(t["function_lines_warn"])
    func_critical = int(t["function_lines_critical"])
    entry_warn = int(t["entry_file_lines_warn"])
    import_warn = int(t["imports_warn"])
    churn_hot = int(t["churn_90d_hot"])

    if total_lines > file_warn:
        score += min(35, (total_lines - file_warn) // 25 + 8)
        reasons.append(f"file_lines>{file_warn}")
    if total_lines > file_critical:
        score += 20
        reasons.append(f"file_lines>{file_critical}")

    if longest_func > func_warn:
        score += min(20, (longest_func - func_warn) // 10 + 6)
        reasons.append(f"longest_function>{func_warn}")
    if longest_func > func_critical:
        score += 12
        reasons.append(f"longest_function>{func_critical}")

    if entrypoint and total_lines > entry_warn:
        score += 18 + max(0, (total_lines - entry_warn) // 30)
        reasons.append(f"entrypoint_overweight>{entry_warn}")

    if mixed:
        score += 16 + max(0, category_count - 3) * 2
        reasons.append("mixed_responsibility")

    if import_count > import_warn:
        score += min(10, (import_count - import_warn) // 5 + 2)
        reasons.append(f"imports>{import_warn}")

    if function_count == 0 and total_lines > file_warn:
        score += 5
        reasons.append("large_file_low_function_visibility")

    if churn_90d >= churn_hot:
        score += min(15, churn_90d - churn_hot + 1)
        reasons.append(f"high_churn_90d>={churn_hot}")

    return score, reasons


def _file_metrics(path: Path, repo: Path, rules: dict[str, Any], churn_30: dict[str, int], churn_90: dict[str, int]) -> FileMetrics:
    rel = path.relative_to(repo).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    total_lines = len(text.splitlines())
    code_lines = _count_code_lines(path, text)

    if path.suffix.lower() == ".py":
        import_count, function_count, longest_func = _python_metrics(text)
    else:
        import_count, function_count, longest_func = _generic_metrics(path, text)

    entry = _is_entrypoint(rel, rules.get("entrypoint_patterns", []))
    categories = _responsibility_mix(text)
    mixed = len(categories) >= 3 and function_count >= 8 and code_lines >= 180

    score, reasons = _compute_risk(
        total_lines=total_lines,
        longest_func=longest_func,
        import_count=import_count,
        function_count=function_count,
        entrypoint=entry,
        mixed=mixed,
        category_count=len(categories),
        churn_90d=churn_90.get(rel, 0),
        rules=rules,
    )

    return FileMetrics(
        path=rel,
        total_lines=total_lines,
        code_lines=code_lines,
        import_count=import_count,
        function_count=function_count,
        longest_function_lines=longest_func,
        entrypoint=entry,
        mixed_responsibility=mixed,
        responsibility_categories=categories,
        churn_30d=churn_30.get(rel, 0),
        churn_90d=churn_90.get(rel, 0),
        risk_score=score,
        risk_level=_risk_level(score),
        reasons=reasons,
    )


def _load_rules(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw


def _should_scan(path: str, rules: dict[str, Any]) -> bool:
    p = path.replace("\\", "/")
    ext = Path(p).suffix.lower()
    includes = set(rules.get("include_extensions", []))
    include_files = set(rules.get("include_files", []))
    excluded = rules.get("exclude_prefixes", [])
    excluded_globs = rules.get("exclude_globs", [])

    for prefix in excluded:
        if p.startswith(prefix):
            return False
    for pat in excluded_globs:
        if fnmatch.fnmatch(p, pat):
            return False
    if Path(p).name in include_files:
        return True
    return ext in includes


def _violations(
    metrics: list[FileMetrics],
    rules: dict[str, Any],
    repo: Path,
    changed_only: bool,
    baseline_ref: str | None,
    scope_current_task: bool,
) -> list[str]:
    t = rules["thresholds"]
    errors: list[str] = []
    by_path = {m.path: m for m in metrics}
    targets = sorted(by_path.keys())
    if changed_only:
        targets = _git_changed_files(repo, baseline_ref)
        targets = [p for p in targets if p in by_path]
    if scope_current_task:
        scopes = _scope_paths_from_current(repo)
        if scopes:
            targets = [p for p in targets if _path_in_scope(p, scopes)]

    for path in targets:
        m = by_path[path]
        baseline_text = _git_file_content(repo, baseline_ref or "HEAD", path) if changed_only else None
        baseline_lines = len(baseline_text.splitlines()) if baseline_text is not None else None
        baseline_longest = 0
        if baseline_text is not None:
            p = repo / path
            if p.suffix.lower() == ".py":
                _, _, baseline_longest = _python_metrics(baseline_text)
            else:
                _, _, baseline_longest = _generic_metrics(p, baseline_text)

        if m.total_lines > int(t["file_lines_critical"]):
            if baseline_lines is None:
                errors.append(
                    f"{path}: new/unknown baseline file is {m.total_lines} lines (> {t['file_lines_critical']})"
                )
            elif m.total_lines > baseline_lines:
                errors.append(
                    f"{path}: oversized file grew {baseline_lines}->{m.total_lines} (> {t['file_lines_critical']})"
                )

        if m.entrypoint and m.total_lines > int(t["entry_file_lines_warn"]):
            if baseline_lines is None:
                errors.append(
                    f"{path}: new/unknown baseline entrypoint is {m.total_lines} lines (> {t['entry_file_lines_warn']})"
                )
            elif m.total_lines > baseline_lines:
                errors.append(
                    f"{path}: entrypoint file grew {baseline_lines}->{m.total_lines} (> {t['entry_file_lines_warn']})"
                )

        if m.longest_function_lines > int(t["function_lines_critical"]):
            if baseline_text is None:
                errors.append(
                    f"{path}: new/unknown baseline longest function {m.longest_function_lines} lines (> {t['function_lines_critical']})"
                )
            elif m.longest_function_lines > baseline_longest:
                errors.append(
                    f"{path}: longest function grew {baseline_longest}->{m.longest_function_lines} (> {t['function_lines_critical']})"
                )

    return errors


def _to_json(metrics: list[FileMetrics], rules: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": {
            "total_files": len(metrics),
            "critical": sum(1 for m in metrics if m.risk_level == "critical"),
            "high": sum(1 for m in metrics if m.risk_level == "high"),
            "medium": sum(1 for m in metrics if m.risk_level == "medium"),
            "low": sum(1 for m in metrics if m.risk_level == "low"),
            "thresholds": rules["thresholds"],
        },
        "files": [
            {
                "path": m.path,
                "total_lines": m.total_lines,
                "code_lines": m.code_lines,
                "import_count": m.import_count,
                "function_count": m.function_count,
                "longest_function_lines": m.longest_function_lines,
                "entrypoint": m.entrypoint,
                "mixed_responsibility": m.mixed_responsibility,
                "responsibility_categories": m.responsibility_categories,
                "churn_30d": m.churn_30d,
                "churn_90d": m.churn_90d,
                "risk_score": m.risk_score,
                "risk_level": m.risk_level,
                "reasons": m.reasons,
            }
            for m in metrics
        ],
    }


def _to_markdown(metrics: list[FileMetrics], limit: int) -> str:
    head = [
        "# Code Health Report",
        "",
        "| Risk | Score | File | Total | Code | Imports | Functions | MaxFn | Churn90d | Flags |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    rows = []
    for m in metrics[:limit]:
        flags = []
        if m.entrypoint:
            flags.append("entry")
        if m.mixed_responsibility:
            flags.append("mixed")
        rows.append(
            f"| {m.risk_level} | {m.risk_score} | `{m.path}` | {m.total_lines} | {m.code_lines} | {m.import_count} | {m.function_count} | {m.longest_function_lines} | {m.churn_90d} | {','.join(flags)} |"
        )
    return "\n".join(head + rows + [""])


def _print_table(metrics: list[FileMetrics], limit: int) -> None:
    print("risk score  total  code  imp  fn  max_fn  churn90  file")
    print("---- -----  -----  ----  ---  --  ------  -------  ----")
    for m in metrics[:limit]:
        print(
            f"{m.risk_level[:4]:<4} {m.risk_score:>5}  {m.total_lines:>5}  {m.code_lines:>4}  "
            f"{m.import_count:>3}  {m.function_count:>2}  {m.longest_function_lines:>6}  "
            f"{m.churn_90d:>7}  {m.path}"
        )


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Repository code health scanner and growth guard")
    ap.add_argument("--repo", default=str(ROOT), help="repository root")
    ap.add_argument("--rules", default=str(DEFAULT_RULES), help="rules json path")
    ap.add_argument("--top", type=int, default=30, help="top risk rows to print")
    ap.add_argument("--output-json", default="", help="write full report json")
    ap.add_argument("--output-md", default="", help="write markdown summary")
    ap.add_argument("--enforce", action="store_true", help="fail on growth-guard violations")
    ap.add_argument("--changed-only", action="store_true", help="enforce rules only for changed files")
    ap.add_argument("--baseline-ref", default="HEAD", help="git ref used to compute changed files and growth")
    ap.add_argument(
        "--scope-current-task",
        action="store_true",
        help="when enforcing, restrict target files to paths declared in meta/tasks/CURRENT.md",
    )
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    repo = Path(args.repo).resolve()
    rules_path = Path(args.rules).resolve()
    if not rules_path.exists():
        print(f"[code_health][error] rules file not found: {rules_path}")
        return 2

    rules = _load_rules(rules_path)
    tracked = _git_tracked_files(repo)
    untracked = _git_untracked_files(repo)
    all_candidates = sorted(set(tracked + untracked))
    paths = [p for p in all_candidates if _should_scan(p, rules)]

    churn_30 = _git_churn_counts(repo, 30)
    churn_90 = _git_churn_counts(repo, 90)

    metrics: list[FileMetrics] = []
    for rel in paths:
        file_path = repo / rel
        if not file_path.exists() or not file_path.is_file():
            continue
        # Skip likely binary files
        if os.path.getsize(file_path) > 5_000_000:
            continue
        metrics.append(_file_metrics(file_path, repo, rules, churn_30, churn_90))

    metrics.sort(key=lambda x: (x.risk_score, x.total_lines, x.churn_90d), reverse=True)

    _print_table(metrics, max(1, args.top))

    report_json = _to_json(metrics, rules)
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report_json, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[code_health] json written: {out}")

    if args.output_md:
        out_md = Path(args.output_md)
        out_md.parent.mkdir(parents=True, exist_ok=True)
        out_md.write_text(_to_markdown(metrics, limit=max(args.top, 50)), encoding="utf-8")
        print(f"[code_health] markdown written: {out_md}")

    if args.enforce:
        baseline_ref = args.baseline_ref if args.baseline_ref else None
        violations = _violations(
            metrics=metrics,
            rules=rules,
            repo=repo,
            changed_only=args.changed_only,
            baseline_ref=baseline_ref,
            scope_current_task=bool(args.scope_current_task),
        )
        if violations:
            print("[code_health][error] growth-guard violations:")
            for v in violations:
                print(f"  - {v}")
            return 1
        print("[code_health] growth-guard check passed")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
