#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TASK_CURRENT = ROOT / "meta" / "tasks" / "CURRENT.md"
AI_CONTRACT = ROOT / "ai_context" / "00_AI_CONTRACT.md"
AIDOC_TPL_DIR = ROOT / "ai_context" / "templates" / "aidoc"

CODE_DIR_PREFIXES = (
    "src/",
    "include/",
    "web/",
    "scripts/",
    "tools/",
)

CODE_FILES = (
    "CMakeLists.txt",
    "web/package.json",
    "web/package-lock.json",
)

DOC_FIRST_DIR_PREFIXES = (
    "docs/",
    "specs/",
    "meta/tasks/",
    "meta/externals/",
    "ai_context/",
)

DOC_FIRST_FILES = (
    "README.md",
    "BUILD.md",
    "PATCH_README.md",
    "TREE.md",
    "AGENTS.md",
)

ALLOW_RE = re.compile(r"\[\s*[xX]\s*\]\s*Code changes allowed")

CURRENT_REQUIRED_PATTERNS = (
    ("Analysis/Find section", re.compile(r"(?im)^##+\s*Analysis\s*/\s*Find\b")),
    ("Integration Check section", re.compile(r"(?im)^##+\s*Integration Check\b")),
    ("Plan section", re.compile(r"(?im)^##+\s*Plan\b")),
    ("check/contrast/fix loop evidence", re.compile(r"(?i)(check\s*/\s*contrast\s*/\s*fix|implement\s*->\s*check.*fix|fix loop|复检|迭代)")),
    ("completion criteria evidence", re.compile(r"(?i)(connected\s*\+\s*accumulated\s*\+\s*consumed|完成标准)")),
    ("issue memory decision evidence", re.compile(r"(?i)(issue memory decision|issue memory|问题记忆决策)")),
    ("skill decision evidence", re.compile(r"(?i)(skillized\s*:\s*(yes|no)|skill decision)")),
)

CURRENT_REQUIRED_FIELDS = (
    "upstream:",
    "current_module:",
    "downstream:",
    "source_of_truth:",
    "fallback:",
    "acceptance_test:",
    "forbidden_bypass:",
    "user_visible_effect:",
)

CURRENT_TASK_TRUTH_FIELDS = (
    "task_purpose:",
    "allowed_behavior_change:",
    "forbidden_goal_shift:",
    "in_scope_modules:",
    "out_of_scope_modules:",
    "completion_evidence:",
)

REPORT_REQUIRED_PATTERNS = (
    ("Readlist section", re.compile(r"(?im)^###\s*Readlist\b")),
    ("Plan section", re.compile(r"(?im)^###\s*Plan\b")),
    ("Verify section", re.compile(r"(?im)^###\s*Verify\b")),
    ("Demo section", re.compile(r"(?im)^###\s*Demo\b")),
    ("first failure point evidence", re.compile(r"(?i)(first failure|首个失败点)")),
    ("minimal fix strategy evidence", re.compile(r"(?i)(minimal fix strategy|最小修复策略)")),
    ("triplet runtime wiring command evidence", re.compile(r'test_runtime_wiring_contract\.py')),
    ("triplet issue memory command evidence", re.compile(r'test_issue_memory_accumulation_contract\.py')),
    ("triplet skill consumption command evidence", re.compile(r'test_skill_consumption_contract\.py')),
)


def _run_git(args: list[str]) -> str | None:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return None


def _git_changed_files() -> list[str]:
    a = _run_git(["diff", "--name-only"]) or ""
    b = _run_git(["diff", "--cached", "--name-only"]) or ""
    c = _run_git(["ls-files", "--others", "--exclude-standard"]) or ""
    files = {x.strip() for x in (a + "\n" + b + "\n" + c).splitlines() if x.strip()}
    return sorted(files)


def _is_code_change(path: str) -> bool:
    if path in CODE_FILES:
        return True
    return any(path.startswith(p) for p in CODE_DIR_PREFIXES)


def _is_doc_first_change(path: str) -> bool:
    if path in DOC_FIRST_FILES:
        return True
    return any(path.startswith(p) for p in DOC_FIRST_DIR_PREFIXES)


def _missing_pattern_labels(text: str, required: tuple[tuple[str, re.Pattern], ...]) -> list[str]:
    missing: list[str] = []
    for label, pattern in required:
        if not pattern.search(text):
            missing.append(label)
    return missing


def main() -> int:
    # BEHAVIOR_ID: B034
    missing: list[str] = []
    if not AI_CONTRACT.exists():
        missing.append("ai_context/00_AI_CONTRACT.md")
    if not AIDOC_TPL_DIR.exists():
        missing.append("ai_context/templates/aidoc/")
    if not TASK_CURRENT.exists():
        missing.append("meta/tasks/CURRENT.md")
    if missing:
        print("[workflow_checks][error] missing required workflow files:")
        for m in missing:
            print(f"  - {m}")
        return 1

    changed = _git_changed_files()

    # If git is not available / not a git repo, we can't detect code changes reliably.
    # In that case we only enforce presence of CURRENT.md and contract files above.
    if not changed:
        print("[workflow_checks] ok (no git diff detected)")
        return 0

    if "meta/tasks/CURRENT.md" not in changed:
        print("[workflow_checks][error] changes detected but meta/tasks/CURRENT.md was not updated.")
        return 1

    if "meta/reports/LAST.md" not in changed:
        print("[workflow_checks][error] changes detected but meta/reports/LAST.md was not updated.")
        return 1

    current_text = TASK_CURRENT.read_text(encoding="utf-8", errors="replace")
    report_path = ROOT / "meta" / "reports" / "LAST.md"
    report_text = report_path.read_text(encoding="utf-8", errors="replace") if report_path.exists() else ""

    missing_current_patterns = _missing_pattern_labels(current_text, CURRENT_REQUIRED_PATTERNS)
    if missing_current_patterns:
        print("[workflow_checks][error] CURRENT.md missing mandatory 10-step evidence sections:")
        for label in missing_current_patterns:
            print(f"  - {label}")
        return 1

    lowered_current = current_text.lower()
    missing_current_fields = [field for field in CURRENT_REQUIRED_FIELDS if field not in lowered_current]
    if missing_current_fields:
        print("[workflow_checks][error] CURRENT.md missing mandatory Integration Check fields:")
        for field in missing_current_fields:
            print(f"  - {field}")
        return 1

    missing_task_truth_fields = [field for field in CURRENT_TASK_TRUTH_FIELDS if field not in lowered_current]
    if missing_task_truth_fields:
        print("[workflow_checks][error] CURRENT.md missing mandatory task truth fields:")
        for field in missing_task_truth_fields:
            print(f"  - {field}")
        return 1

    missing_report_patterns = _missing_pattern_labels(report_text, REPORT_REQUIRED_PATTERNS)
    if missing_report_patterns:
        print("[workflow_checks][error] LAST.md missing mandatory workflow evidence:")
        for label in missing_report_patterns:
            print(f"  - {label}")
        return 1

    code_changes = [p for p in changed if _is_code_change(p)]
    if not code_changes:
        print("[workflow_checks] ok (workflow evidence + docs/meta changes)")
        return 0

    text = TASK_CURRENT.read_text(encoding="utf-8", errors="replace")
    if not ALLOW_RE.search(text):
        print("[workflow_checks][error] code changes detected but CURRENT.md does not allow code edits.")
        print("Add and tick the checkbox in meta/tasks/CURRENT.md:")
        print("  - [x] Code changes allowed")
        print("Code changes:")
        for p in code_changes:
            print(f"  - {p}")
        return 1

    if "meta/reports/LAST.md" not in changed:
        print("[workflow_checks][error] code changes detected but meta/reports/LAST.md was not updated.")
        print("Please update meta/reports/LAST.md in the same patch when touching code directories.")
        print("Code changes:")
        for p in code_changes:
            print(f"  - {p}")
        return 1

    doc_first_changes = [p for p in changed if _is_doc_first_change(p)]
    if not doc_first_changes:
        print("[workflow_checks][error] code changes detected but no docs/spec-first update was found.")
        print("Add at least one docs/spec/meta task change in the same patch (report-only updates do not count).")
        print("Accepted doc/spec-first roots:")
        for root in (*DOC_FIRST_DIR_PREFIXES, *DOC_FIRST_FILES):
            print(f"  - {root}")
        print("Code changes:")
        for p in code_changes:
            print(f"  - {p}")
        return 1

    print("[workflow_checks] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
