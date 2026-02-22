#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.checks.plan_contract import behavior_page_has_required_sections, load_behavior_index

BEHAVIOR_MARKER_RE = re.compile(r"BEHAVIOR_ID\s*[:=]\s*[\"']?(B\d{3})[\"']?", flags=re.IGNORECASE)
SCAN_SUFFIXES = (".py", ".ps1", ".sh")
SCAN_ROOTS = ("scripts", "tools")
REQUIRED_MARKER_FILES = (
    "scripts/verify_repo.ps1",
    "scripts/verify_repo.sh",
    "scripts/adlc_run.py",
    "scripts/workflow_dispatch.py",
    "scripts/ctcp_orchestrate.py",
    "scripts/ctcp_dispatch.py",
    "scripts/apply_patch_first.py",
    "scripts/ctcp_librarian.py",
    "scripts/workflow_checks.py",
    "scripts/contract_checks.py",
    "tools/providers/manual_outbox.py",
    "tools/providers/local_exec.py",
    "tools/providers/api_agent.py",
)


def _scan_behavior_ids(repo: Path) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    by_file: dict[str, set[str]] = {}
    by_id: dict[str, set[str]] = {}
    for rel_root in SCAN_ROOTS:
        base = repo / rel_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            rel = path.relative_to(repo).as_posix()
            if "/__pycache__/" in rel:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            ids = set(BEHAVIOR_MARKER_RE.findall(text))
            if not ids:
                continue
            by_file[rel] = ids
            for bid in ids:
                by_id.setdefault(bid, set()).add(rel)
    return by_file, by_id


def main() -> int:
    # BEHAVIOR_ID: B012
    ap = argparse.ArgumentParser(description="Ensure code BEHAVIOR_ID markers are fully cataloged")
    ap.add_argument("--repo", default=".", help="repo root")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    index_path = repo / "docs" / "behaviors" / "INDEX.md"
    behaviors_dir = repo / "docs" / "behaviors"

    errors: list[str] = []
    by_file, by_id = _scan_behavior_ids(repo)
    code_ids = set(by_id.keys())

    for rel in REQUIRED_MARKER_FILES:
        ids = by_file.get(rel, set())
        if not ids:
            errors.append(f"required entry file missing BEHAVIOR_ID marker: {rel}")

    index_map, index_errors = load_behavior_index(index_path)
    errors.extend(index_errors)
    index_ids = set(index_map.keys())

    for bid in sorted(code_ids):
        if bid not in index_ids:
            errors.append(f"code marker not found in docs/behaviors/INDEX.md: {bid}")
            continue
        page = behaviors_dir / index_map[bid]
        ok, page_errors = behavior_page_has_required_sections(page)
        if not ok:
            errors.extend(page_errors)

    for bid in sorted(index_ids):
        if bid not in code_ids:
            errors.append(f"INDEX behavior has no code marker: {bid}")
        page = behaviors_dir / index_map[bid]
        ok, page_errors = behavior_page_has_required_sections(page)
        if not ok:
            errors.extend(page_errors)

    if errors:
        for e in errors:
            print(f"[behavior_catalog_check][error] {e}")
        return 1

    print(
        "[behavior_catalog_check] ok "
        f"(code_ids={len(code_ids)} index_ids={len(index_ids)} files={len(by_file)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

