#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = (
    ROOT
    / "tests"
    / "fixtures"
    / "adlc_forge_full_bundle"
    / "suites"
    / "forge_full_suite.live.yaml"
)


def _parse_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def _load_doc(path: Path) -> dict[str, Any]:
    txt = path.read_text(encoding="utf-8")
    try:
        doc = json.loads(txt)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except Exception as exc:
            raise RuntimeError(
                f"failed to parse {path} as JSON; PyYAML not available for YAML parsing"
            ) from exc
        doc = yaml.safe_load(txt)
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: top-level object is required")
    return doc


def evaluate_suite_gate(doc: dict[str, Any], env: dict[str, str]) -> dict[str, Any]:
    suite = doc.get("suite")
    if not isinstance(suite, dict):
        raise ValueError("missing object key: suite")

    env_gate = suite.get("env_gate")
    if not isinstance(env_gate, dict):
        raise ValueError("missing object key: suite.env_gate")

    required_env = env_gate.get("required_env", [])
    if not isinstance(required_env, list):
        raise ValueError("suite.env_gate.required_env must be an array")
    required_env = [str(x) for x in required_env]

    allow_network_env = env_gate.get("allow_network_env", [])
    if isinstance(allow_network_env, str):
        allow_network_env = [allow_network_env]
    if not isinstance(allow_network_env, list):
        raise ValueError("suite.env_gate.allow_network_env must be an array or string")
    allow_network_env = [str(x) for x in allow_network_env]

    require_network = _parse_bool(env_gate.get("require_network", False))
    missing_env = [k for k in required_env if not env.get(k, "").strip()]
    network_allowed = True
    if require_network:
        network_allowed = any(_parse_bool(env.get(k)) for k in allow_network_env)

    reasons: list[str] = []
    if missing_env:
        reasons.append("missing required env: " + ", ".join(missing_env))
    if require_network and not network_allowed:
        reasons.append("network gate blocked: set one allow_network_env variable to true")

    ready = not reasons
    return {
        "checked_at": dt.datetime.now().isoformat(timespec="seconds"),
        "suite_file": str(DEFAULT_SUITE.as_posix()),
        "suite_id": str(suite.get("id", "")),
        "suite_title": str(suite.get("title", "")),
        "tier": str(suite.get("tier", "")),
        "required_env": required_env,
        "missing_env": missing_env,
        "require_network": require_network,
        "allow_network_env": allow_network_env,
        "network_allowed": network_allowed,
        "ready": ready,
        "status": "pass" if ready else "skip",
        "reasons": reasons,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate env gate for Forge live suite")
    ap.add_argument("--suite", default=str(DEFAULT_SUITE), help="suite YAML/JSON path")
    ap.add_argument("--json", action="store_true", help="print JSON result")
    args = ap.parse_args()

    suite_path = Path(args.suite)
    if not suite_path.is_absolute():
        suite_path = (ROOT / suite_path).resolve()
    if not suite_path.exists():
        print(f"[suite_gate] missing suite file: {suite_path}")
        return 2

    try:
        doc = _load_doc(suite_path)
        result = evaluate_suite_gate(doc, dict(os.environ))
    except Exception as exc:
        print(f"[suite_gate] error: {exc}")
        return 2

    result["suite_file"] = suite_path.as_posix()
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[suite_gate] suite: {result['suite_id']} ({result['tier']})")
        print(f"[suite_gate] status: {result['status']}")
        if result["reasons"]:
            for reason in result["reasons"]:
                print(f"[suite_gate] reason: {reason}")

    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
