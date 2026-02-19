#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def validate_find_web(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, f"missing file: {path.as_posix()}"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"invalid json: {exc}"
    if not isinstance(doc, dict):
        return False, "top-level document must be object"
    if doc.get("schema_version") != "ctcp-find-web-v1":
        return False, "schema_version must be ctcp-find-web-v1"

    constraints = doc.get("constraints")
    if not isinstance(constraints, dict):
        return False, "constraints must be object"
    allow_domains = constraints.get("allow_domains")
    max_queries = constraints.get("max_queries")
    if not isinstance(allow_domains, list) or any(not isinstance(x, str) for x in allow_domains):
        return False, "constraints.allow_domains must be string array"
    if not isinstance(max_queries, int):
        return False, "constraints.max_queries must be integer"

    results = doc.get("results")
    if not isinstance(results, list):
        return False, "results must be array"
    required = {"url", "locator", "fetched_at", "excerpt", "why_relevant", "risk_flags"}
    for idx, row in enumerate(results):
        if not isinstance(row, dict):
            return False, f"results[{idx}] must be object"
        missing = sorted(required - set(row.keys()))
        if missing:
            return False, f"results[{idx}] missing fields: {', '.join(missing)}"
        if not isinstance(row.get("risk_flags"), list):
            return False, f"results[{idx}].risk_flags must be array"
    return True, "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate optional find_web artifact contract.")
    ap.add_argument("--mode", default="resolver_only", choices=["resolver_only", "resolver_plus_web"])
    ap.add_argument("--path", default="artifacts/find_web.json")
    args = ap.parse_args()

    target = Path(args.path).resolve()
    if args.mode == "resolver_only":
        print(f"[find_web_contract] skip in mode={args.mode}")
        return 0

    ok, msg = validate_find_web(target)
    if not ok:
        print(f"[find_web_contract] invalid: {msg}")
        return 1
    print(f"[find_web_contract] ok: {target.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
