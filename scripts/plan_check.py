#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.checks.plan_contract import (
    behavior_page_has_required_sections,
    load_behavior_index,
    load_expected_results,
    load_plan_contract,
    load_reason_refs,
    parse_list,
)


def main() -> int:
    # BEHAVIOR_ID: B010
    ap = argparse.ArgumentParser(description="Validate PLAN/REASONS/EXPECTED_RESULTS contract")
    ap.add_argument("--repo", default=".", help="repo root")
    ap.add_argument("--executed-gates", default="", help="comma-separated executed gate names")
    ap.add_argument("--check-evidence", action="store_true", help="require EXPECTED_RESULTS evidence paths to exist")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    plan_path = repo / "artifacts" / "PLAN.md"
    reasons_path = repo / "artifacts" / "REASONS.md"
    expected_path = repo / "artifacts" / "EXPECTED_RESULTS.md"
    index_path = repo / "docs" / "behaviors" / "INDEX.md"
    behaviors_dir = repo / "docs" / "behaviors"

    errors: list[str] = []

    plan, plan_errors = load_plan_contract(plan_path)
    errors.extend(plan_errors)
    if plan is None:
        for e in errors:
            print(f"[plan_check][error] {e}")
        return 1

    index_map, index_errors = load_behavior_index(index_path)
    errors.extend(index_errors)

    expected_map, expected_errors = load_expected_results(expected_path)
    errors.extend(expected_errors)

    reason_refs, reason_errors = load_reason_refs(reasons_path)
    errors.extend(reason_errors)

    for bid in plan.behaviors:
        if bid not in index_map:
            errors.append(f"PLAN references unknown behavior: {bid}")
            continue
        page = behaviors_dir / index_map[bid]
        ok, page_errors = behavior_page_has_required_sections(page)
        if not ok:
            errors.extend(page_errors)

    known_result_ids = set(expected_map.keys())
    for rid in plan.results:
        if rid not in known_result_ids:
            errors.append(f"PLAN references unknown result: {rid}")

    valid_ref_ids = set(plan.behaviors) | set(plan.results)
    for lineno, refs in reason_refs:
        for ref in refs:
            if ref not in valid_ref_ids:
                errors.append(f"REASONS line {lineno}: reference not in PLAN Behaviors/Results: {ref}")

    if args.executed_gates.strip():
        executed = set(parse_list(args.executed_gates))
        missing = [gate for gate in plan.gates if gate not in executed]
        if missing:
            errors.append("PLAN-declared gates not executed: " + ", ".join(missing))

    if args.check_evidence:
        for rid in plan.results:
            row = expected_map.get(rid)
            if row is None:
                continue
            for rel in row.evidence:
                candidate = (repo / rel).resolve()
                if not candidate.exists():
                    errors.append(f"{rid} evidence path missing: {rel}")

    if errors:
        for e in errors:
            print(f"[plan_check][error] {e}")
        return 1

    print(
        "[plan_check] ok "
        f"(behaviors={len(plan.behaviors)} results={len(plan.results)} gates={len(plan.gates)} reasons={len(reason_refs)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

