#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Suite Gate — two-tier test suite dispatcher.

Usage:
  python tools/checks/suite_gate.py                          # default: regression (offline, stubs)
  python tools/checks/suite_gate.py --tier live              # live: requires OPENAI_API_KEY
  python tools/checks/suite_gate.py --tier regression        # explicit regression
  python tools/checks/suite_gate.py --tier auto              # auto-detect: live if key present, else regression
  python tools/checks/suite_gate.py --dry-run                # show what would run without executing
  python tools/checks/suite_gate.py --tier live --limit 3    # run only first 3 tasks (cost control)

Exit codes:
  0  = all tasks passed (or skipped gracefully)
  1  = some tasks failed
  2  = configuration / env gate error
  3  = suite skipped (no API key for live tier)

Design:
  - Regression suite: offline, --materialize-stubs, network=deny. Always safe.
  - Live suite: requires env_gate keys, network=allow. Only for manual/nightly.
  - Auto tier: picks live if required env vars present, else falls back to regression.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _find_repo_root() -> Path:
    cur = Path(__file__).resolve().parent
    for _ in range(10):
        if (cur / ".git").exists() or (cur / "AGENTS.md").exists():
            return cur
        cur = cur.parent
    return Path.cwd()


def _detect_python() -> str:
    """Return python command that works in current env."""
    import shutil
    for exe in ("python", "python3"):
        if shutil.which(exe):
            return exe
    if shutil.which("py"):
        return "py -3"
    return sys.executable


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────────────────
# Env gate
# ──────────────────────────────────────────────────────────────

def check_env_gate(gate: dict) -> tuple[bool, str]:
    """Check whether environment satisfies the gate requirements.

    Returns (ok, message).
    """
    required = gate.get("required_env", [])
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        skip_msg = gate.get("skip_message") or f"SKIP: missing env vars: {', '.join(missing)}"
        return False, skip_msg
    return True, "env gate passed"


def detect_tier(suites_dir: Path) -> str:
    """Auto-detect tier: try live gate, fall back to regression."""
    live_path = suites_dir / "forge_full_suite.live.yaml"
    if live_path.exists():
        live_cfg = _load_json(live_path)
        gate = live_cfg.get("suite", {}).get("env_gate", {})
        ok, _ = check_env_gate(gate)
        if ok:
            return "live"
    return "regression"


# ──────────────────────────────────────────────────────────────
# Suite resolution
# ──────────────────────────────────────────────────────────────

def resolve_suite(tier: str, suites_dir: Path) -> tuple[Path, dict, list[str]]:
    """Resolve which suite file + forge args to use.

    Returns (suite_path, suite_config, extra_forge_args).
    """
    if tier == "live":
        cfg_path = suites_dir / "forge_full_suite.live.yaml"
    elif tier == "regression":
        cfg_path = suites_dir / "forge_full_suite.regression.yaml"
    else:
        raise ValueError(f"unknown tier: {tier}")

    if not cfg_path.exists():
        raise FileNotFoundError(f"suite config not found: {cfg_path}")

    cfg = _load_json(cfg_path)
    suite = cfg.get("suite", {})
    base_ref = suite.get("base_suite", "forge_full_suite.yaml")
    base_path = suites_dir / base_ref

    if not base_path.exists():
        raise FileNotFoundError(f"base suite not found: {base_path}")

    forge_args: list[str] = []
    if tier == "regression" or suite.get("materialize_stubs"):
        forge_args.append("--materialize-stubs")

    return base_path, cfg, forge_args


# ──────────────────────────────────────────────────────────────
# Runner
# ──────────────────────────────────────────────────────────────

def run_forge_suite(
    runner_dir: Path,
    suite_path: Path,
    extra_args: list[str],
    limit: int = 0,
    env_extra: dict[str, str] | None = None,
) -> int:
    """Invoke `python -m forge suite <suite_path>` in the runner directory."""
    python_cmd = _detect_python()
    cmd = [python_cmd, "-m", "forge", "suite", str(suite_path.resolve())]
    if limit > 0:
        cmd += ["--limit", str(limit)]
    cmd += extra_args

    env = dict(os.environ)
    # Ensure PYTHONPATH includes src/
    src_dir = str((runner_dir / "src").resolve())
    prev = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_dir if not prev else f"{src_dir}{os.pathsep}{prev}"
    if env_extra:
        env.update(env_extra)

    print(f"[suite_gate] cwd={runner_dir}")
    print(f"[suite_gate] cmd={' '.join(cmd)}")
    print(f"[suite_gate] PYTHONPATH={env.get('PYTHONPATH', '')[:120]}...")
    print()

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(runner_dir),
            env=env,
            timeout=7200,  # 2h hard cap
        )
        return proc.returncode
    except subprocess.TimeoutExpired:
        print("[suite_gate] TIMEOUT after 7200s")
        return 1
    except Exception as e:
        print(f"[suite_gate] ERROR: {e}")
        return 2


# ──────────────────────────────────────────────────────────────
# Report
# ──────────────────────────────────────────────────────────────

def print_summary(runner_dir: Path, suite_id: str) -> None:
    """Print summary from the latest totals.json."""
    totals_dir = runner_dir / "runs" / "_suite" / suite_id
    # Try multiple names
    for name in ("totals.json", "totals.full_stubs.json", "totals.full_default.json"):
        p = totals_dir / name
        if p.exists():
            try:
                data = _load_json(p)
                total = data.get("tasks_total", 0)
                passed = data.get("tasks_passed", 0)
                avg = data.get("avg_score", 0)
                rate = data.get("pass_rate", 0)
                print(f"\n[suite_gate] {name}: {passed}/{total} passed, rate={rate:.1%}, avg_score={avg:.1f}")
            except Exception:
                pass


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Two-tier forge suite dispatcher (regression / live)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    ap.add_argument(
        "--tier", choices=["regression", "live", "auto"], default="regression",
        help="Which tier to run (default: regression)",
    )
    ap.add_argument("--limit", type=int, default=0, help="Max tasks to run (0=all)")
    ap.add_argument("--dry-run", action="store_true", help="Show config without executing")
    ap.add_argument("--bundle", type=str, default="", help="Override bundle root path")
    args = ap.parse_args()

    repo = _find_repo_root()
    bundle_root = Path(args.bundle) if args.bundle else repo / "tests" / "fixtures" / "adlc_forge_full_bundle"
    suites_dir = bundle_root / "suites"
    runner_dir = bundle_root / "capstone_runner_skeleton"

    if not suites_dir.exists():
        print(f"[suite_gate] ERROR: suites dir not found: {suites_dir}")
        return 2
    if not runner_dir.exists():
        print(f"[suite_gate] ERROR: runner dir not found: {runner_dir}")
        return 2

    # Resolve tier
    tier = args.tier
    if tier == "auto":
        tier = detect_tier(suites_dir)
        print(f"[suite_gate] auto-detected tier: {tier}")

    # Resolve suite
    try:
        suite_path, cfg, extra_args = resolve_suite(tier, suites_dir)
    except (FileNotFoundError, ValueError) as e:
        print(f"[suite_gate] ERROR: {e}")
        return 2

    suite_cfg = cfg.get("suite", {})
    suite_id = suite_cfg.get("id", "forge-full-v1")

    # Env gate check (for live tier)
    gate = suite_cfg.get("env_gate", {})
    if gate.get("required_env"):
        ok, msg = check_env_gate(gate)
        if not ok:
            print(f"[suite_gate] {msg}")
            return 3  # graceful skip

    # Cost guard display
    cost = suite_cfg.get("cost_guard", {})
    if cost:
        print(f"[suite_gate] cost_guard: max_tasks={cost.get('max_tasks')}, "
              f"max_api_calls={cost.get('max_total_api_calls')}, "
              f"max_cost=${cost.get('max_cost_usd')}")

    # Summary
    print(f"[suite_gate] tier={tier}")
    print(f"[suite_gate] suite_id={suite_id}")
    print(f"[suite_gate] base_suite={suite_path}")
    print(f"[suite_gate] forge_args={extra_args}")
    print(f"[suite_gate] limit={args.limit or 'all'}")
    if args.limit == 0 and tier == "live":
        limit_override = cost.get("max_tasks", 0)
        if limit_override:
            print(f"[suite_gate] applying cost_guard max_tasks={limit_override}")

    if args.dry_run:
        print("[suite_gate] DRY-RUN — exiting without execution")
        return 0

    # Apply limit
    limit = args.limit
    if limit == 0 and tier == "live" and cost.get("max_tasks"):
        limit = int(cost["max_tasks"])

    # Run
    rc = run_forge_suite(
        runner_dir=runner_dir,
        suite_path=suite_path,
        extra_args=extra_args,
        limit=limit,
    )

    # Post-run summary
    # The suite id in totals may be the base suite id, not the tier-specific one
    for sid in [suite_id, "forge-full-v1"]:
        print_summary(runner_dir, sid)

    print(f"\n[suite_gate] exit code: {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
