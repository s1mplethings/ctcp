#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generic case runner:
- Reads tests/cases/*.case.json
- Executes commands with placeholders
- Stores artifacts under runs/self_check_artifacts/cases/<case_id> (overridable via env SDDAI_SELF_CHECK_ARTIFACTS or --artifacts)
- Compares against golden outputs (tests/golden/<case_id>/) unless mode=schema
- Supports --record to refresh golden
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None

DEFAULT_ARTIFACT_ENV = "SDDAI_SELF_CHECK_ARTIFACTS"
CASE_GLOB = "*.case.json"


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for _ in range(8):
        if (cur / ".git").exists():
            return cur
        if (cur / "README.md").exists() and (cur / "specs").exists():
            return cur
        cur = cur.parent
    return start.resolve()


def load_cases(cases_dir: Path) -> Dict[str, Dict[str, Any]]:
    cases: Dict[str, Dict[str, Any]] = {}
    for p in sorted(cases_dir.glob(CASE_GLOB)):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            cid = data.get("id") or p.stem.replace(".case", "")
            data["id"] = cid
            data["_path"] = p
            cases[cid] = data
        except Exception as e:
            print(f"[WARN] skip case {p}: {e}")
    return cases


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_json(data: Any, ignore_keys: List[str], sort_lists: bool) -> Any:
    if isinstance(data, dict):
        return {k: normalize_json(v, ignore_keys, sort_lists) for k, v in sorted(data.items()) if k not in ignore_keys}
    if isinstance(data, list):
        items = [normalize_json(x, ignore_keys, sort_lists) for x in data]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True)) if sort_lists else items
    return data


def normalize_text(s: str, strip_whitespace: bool) -> str:
    return "\n".join(line.strip() for line in s.splitlines()) if strip_whitespace else s


def compare_output(kind: str, got: Path, golden: Path, normalize: Dict[str, Any]) -> Tuple[bool, str]:
    if kind == "json":
        g1 = json.loads(got.read_text(encoding="utf-8"))
        g2 = json.loads(golden.read_text(encoding="utf-8"))
        ignore_keys = normalize.get("ignore_keys", []) if normalize else []
        sort_lists = bool(normalize.get("sort_lists")) if normalize else False
        g1n = normalize_json(g1, ignore_keys, sort_lists)
        g2n = normalize_json(g2, ignore_keys, sort_lists)
        ok = g1n == g2n
        return ok, "" if ok else "json differs"
    if kind == "text":
        t1 = got.read_text(encoding="utf-8")
        t2 = golden.read_text(encoding="utf-8")
        strip_ws = bool(normalize.get("strip_whitespace")) if normalize else False
        t1n = normalize_text(t1, strip_ws)
        t2n = normalize_text(t2, strip_ws)
        ok = t1n == t2n
        return ok, "" if ok else "text differs"
    # binary
    ok = sha256_file(got) == sha256_file(golden)
    return ok, "" if ok else "binary hash differs"


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def run_one_case(case: Dict[str, Any], repo: Path, artifacts_root: Path, record: bool) -> Dict[str, Any]:
    cid = case["id"]
    case_artifacts = artifacts_root / "cases" / cid
    ensure_clean_dir(case_artifacts)

    input_rel = Path(case["input"])
    input_path = (repo / input_rel).resolve()
    if not input_path.exists():
        return {"id": cid, "pass": False, "error": f"input not found: {input_rel}"}

    fmt = {
        "input": str(input_path),
        "input_rel": input_rel.as_posix(),
        "artifacts": str(case_artifacts),
        "case_id": cid,
        "repo": str(repo),
    }
    cmd = case["cmd"].format(**fmt) if isinstance(case["cmd"], str) else " ".join(case["cmd"])

    try:
        proc = subprocess.run(cmd, cwd=str(repo), shell=True, capture_output=True, text=True, timeout=case.get("timeout", 300))
    except subprocess.TimeoutExpired:
        return {"id": cid, "pass": False, "stdout": "", "stderr": "[TIMEOUT]", "returncode": 124, "error": "timeout"}

    outputs = case.get("outputs", [])
    results = []
    errors = []

    if proc.returncode != 0:
        errors.append(f"cmd exit {proc.returncode}")

    # Collect outputs
    for out in outputs:
        opath = Path(out["path"])
        if not opath.is_absolute():
            opath = case_artifacts / opath
        if not opath.exists():
            errors.append(f"missing output: {opath}")
            results.append({"path": str(opath), "pass": False, "reason": "missing"})
            continue

        mode = (case.get("mode") or "golden").lower()
        otype = (out.get("type") or "text").lower()

        if mode == "schema":
            schema_path = out.get("schema") or case.get("schema")
            if not schema_path:
                errors.append("schema mode requires schema path")
                results.append({"path": str(opath), "pass": False, "reason": "no schema"})
                continue
            if jsonschema is None:
                errors.append("jsonschema not installed (pip install jsonschema)")
                results.append({"path": str(opath), "pass": False, "reason": "jsonschema missing"})
                continue
            sch = json.loads((repo / schema_path).read_text(encoding="utf-8"))
            doc = json.loads(opath.read_text(encoding="utf-8"))
            try:
                jsonschema.validate(doc, sch)  # type: ignore
                results.append({"path": str(opath), "pass": True, "reason": "schema ok"})
            except Exception as e:
                errors.append(f"schema fail: {e}")
                results.append({"path": str(opath), "pass": False, "reason": str(e)})
        else:
            golden_path = repo / "tests" / "golden" / cid / out["path"]
            if record:
                golden_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(opath, golden_path)
                results.append({"path": str(opath), "pass": True, "reason": "recorded"})
            else:
                if not golden_path.exists():
                    errors.append(f"golden missing: {golden_path}")
                    results.append({"path": str(opath), "pass": False, "reason": "golden missing"})
                    continue
                ok, reason = compare_output(otype, opath, golden_path, out.get("normalize") or {})
                if not ok:
                    errors.append(f"diff: {opath} vs {golden_path} ({reason})")
                results.append({"path": str(opath), "pass": ok, "reason": reason or "match"})

    case_report = {
        "id": cid,
        "pass": not errors,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "outputs": results,
        "errors": errors,
    }
    (case_artifacts / "case_report.json").write_text(json.dumps(case_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return case_report


def main() -> int:
    ap = argparse.ArgumentParser(description="Run file-based cases and compare with golden/schema.")
    ap.add_argument("--case", action="append", help="run only specified case id (can repeat or comma separated)")
    ap.add_argument("--record", action="store_true", help="record outputs as golden")
    ap.add_argument("--artifacts", default="", help="override artifacts root (default: env or runs/self_check_artifacts)")
    ap.add_argument("--timeout", type=int, default=300, help="per-case timeout seconds")
    args = ap.parse_args()

    repo = find_repo_root(Path("."))
    cases_dir = repo / "tests" / "cases"
    all_cases = load_cases(cases_dir)
    if not all_cases:
        print("[FAIL] no cases found")
        return 2

    chosen: List[str]
    if args.case:
        chosen = []
        for item in args.case:
            chosen.extend([c.strip() for c in item.split(",") if c.strip()])
    else:
        chosen = list(all_cases.keys())

    missing = [c for c in chosen if c not in all_cases]
    if missing:
        print(f"[FAIL] missing cases: {', '.join(missing)}")
        return 2

    artifacts_root = Path(args.artifacts) if args.artifacts else Path(os.environ.get(DEFAULT_ARTIFACT_ENV, repo / "runs" / "self_check_artifacts"))
    artifacts_root.mkdir(parents=True, exist_ok=True)

    failures = 0
    reports = []
    for cid in chosen:
        case = all_cases[cid]
        case.setdefault("timeout", args.timeout)
        print(f"[run] case {cid}")
        report = run_one_case(case, repo, artifacts_root, record=args.record)
        reports.append(report)
        if report.get("pass"):
            print(f"[PASS] {cid}")
        else:
            failures += 1
            print(f"[FAIL] {cid}: {'; '.join(report.get('errors', []))}")

    summary = {"pass": failures == 0, "cases": reports}
    (artifacts_root / "cases" / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
