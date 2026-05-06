#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]


RUNTIME_PREFIXES = (
    "build/",
    "build_lite/",
    "build_verify/",
    "dist/",
    "generated_projects/",
    "runs/",
    "simlab/_runs/",
    "meta/runs/",
)

SOURCE_PREFIXES = (
    "ctcp_adapters/",
    "frontend/",
    "llm_core/",
    "scripts/",
    "tests/",
    "tools/",
)

DOC_META_PREFIXES = (
    "ai/",
    "ai_context/",
    "artifacts/",
    "contracts/",
    "docs/",
    "simlab/scenarios/",
    "workflow_registry/",
)

ARCHIVE_PREFIXES = (
    "meta/reports/archive/",
    "meta/tasks/archive/",
)

TASK_REPORT_PATHS = {
    "meta/backlog/execution_queue.json",
    "meta/reports/LAST.md",
    "meta/tasks/ARCHIVE_INDEX.md",
    "meta/tasks/CURRENT.md",
}


@dataclass(frozen=True)
class StatusEntry:
    index_status: str
    worktree_status: str
    path: str
    original_path: str = ""

    @property
    def status_code(self) -> str:
        return f"{self.index_status}{self.worktree_status}"


def normalize_path(path: str) -> str:
    return str(path or "").strip().replace("\\", "/").strip("/")


def parse_status_line(line: str) -> StatusEntry | None:
    text = line.rstrip("\n")
    if not text:
        return None
    if len(text) < 4:
        return None

    status = text[:2]
    path_text = text[3:].strip()
    original_path = ""
    if " -> " in path_text:
        original_path, path_text = path_text.split(" -> ", 1)

    return StatusEntry(
        index_status=status[0],
        worktree_status=status[1],
        path=normalize_path(path_text),
        original_path=normalize_path(original_path),
    )


def classify_path(path: str) -> str:
    rel = normalize_path(path)
    name = Path(rel).name
    if rel in TASK_REPORT_PATHS:
        return "task_report_meta"
    if rel.startswith(ARCHIVE_PREFIXES):
        return "task_report_archive"
    if rel.startswith(RUNTIME_PREFIXES) or name.startswith("_tmp_") or name.endswith(".tmp"):
        return "runtime_or_generated_output"
    if rel.startswith(SOURCE_PREFIXES):
        return "source_or_test_change"
    if rel.startswith(DOC_META_PREFIXES) or rel in {"README.md", "PATCH_README.md", "TREE.md", "AGENTS.md"}:
        return "docs_contract_or_workflow_change"
    return "other"


def status_kind(entry: StatusEntry) -> str:
    if entry.index_status == "?" and entry.worktree_status == "?":
        return "untracked"
    if entry.index_status == "!" and entry.worktree_status == "!":
        return "ignored"
    if entry.index_status != " " and entry.worktree_status == " ":
        return "staged"
    if entry.index_status == " " and entry.worktree_status != " ":
        return "modified_unstaged"
    return "mixed_or_renamed"


def run_git_status(repo: Path) -> list[str]:
    proc = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git status failed")
    return proc.stdout.splitlines()


def build_report(lines: Iterable[str]) -> dict[str, object]:
    entries = [entry for line in lines if (entry := parse_status_line(line)) is not None]
    category_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    samples: dict[str, list[str]] = defaultdict(list)

    for entry in entries:
        category = classify_path(entry.path)
        kind = status_kind(entry)
        category_counts[category] += 1
        status_counts[kind] += 1
        if len(samples[category]) < 12:
            samples[category].append(entry.path)

    runtime_outputs = category_counts.get("runtime_or_generated_output", 0)
    return {
        "schema_version": "ctcp-worktree-cleanliness-report-v1",
        "total_dirty": len(entries),
        "category_counts": dict(sorted(category_counts.items())),
        "status_counts": dict(sorted(status_counts.items())),
        "samples": dict(sorted(samples.items())),
        "recommended_order": [
            "Remove or externalize runtime_or_generated_output files first.",
            "Review untracked source_or_test_change files and either add them to the intended patch or move them out.",
            "Group docs_contract_or_workflow_change files by queue item before commit or stash.",
            "Commit task_report_archive files with the task that produced them.",
            "Re-run canonical verify with CTCP_RUNS_ROOT outside the repo and CTCP_FORCE_PROVIDER cleared for local smoke gates.",
        ],
        "runtime_output_count": int(runtime_outputs),
    }


def print_text_report(report: dict[str, object]) -> None:
    print("[worktree_cleanliness_report] dirty files:", report["total_dirty"])
    print("[worktree_cleanliness_report] categories:")
    for category, count in dict(report.get("category_counts", {})).items():
        print(f"  - {category}: {count}")
    print("[worktree_cleanliness_report] status kinds:")
    for kind, count in dict(report.get("status_counts", {})).items():
        print(f"  - {kind}: {count}")
    print("[worktree_cleanliness_report] samples:")
    for category, paths in dict(report.get("samples", {})).items():
        print(f"  - {category}:")
        for path in list(paths):
            print(f"    - {path}")
    print("[worktree_cleanliness_report] recommended order:")
    for item in list(report.get("recommended_order", [])):
        print(f"  - {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify git dirty state into cleanup action buckets.")
    parser.add_argument("--repo", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument(
        "--fail-on-runtime-output",
        action="store_true",
        help="return non-zero when tracked or unignored runtime/generated outputs are dirty",
    )
    args = parser.parse_args(argv)

    try:
        lines = run_git_status(args.repo.resolve())
    except Exception as exc:
        print(f"[worktree_cleanliness_report][error] {exc}", file=sys.stderr)
        return 2

    report = build_report(lines)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_text_report(report)

    if args.fail_on_runtime_output and int(report.get("runtime_output_count", 0)) > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
