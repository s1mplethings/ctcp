#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate proof artifacts: no evidence => fail.")
    ap.add_argument("--proof-dir", required=True, help="Path to proof directory or proof.json")
    args = ap.parse_args()

    p = Path(args.proof_dir).resolve()
    proof_json = p if p.is_file() else p / "proof.json"
    proof_dir = proof_json.parent

    issues: list[str] = []
    if not proof_json.exists():
        issues.append(f"missing proof.json: {proof_json.as_posix()}")
    else:
        try:
            proof = json.loads(proof_json.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(f"invalid proof.json: {exc}")
            proof = {}

        if proof.get("result") != "PASS":
            issues.append(f"proof result is not PASS: {proof.get('result')}")

        required_steps = ["configure", "build", "ctest", "install", "smoke"]
        step_map = {}
        for s in proof.get("steps", []):
            if isinstance(s, dict) and s.get("name"):
                step_map[str(s["name"])] = s

        for step_name in required_steps:
            s = step_map.get(step_name)
            if s is None:
                issues.append(f"missing step: {step_name}")
                continue
            if s.get("exit_code") != 0:
                issues.append(f"step failed: {step_name} (exit_code={s.get('exit_code')})")
            log_name = s.get("log_file")
            if not isinstance(log_name, str) or not log_name.strip():
                issues.append(f"missing log file field for step: {step_name}")
                continue
            if not (proof_dir / log_name).exists():
                issues.append(f"missing log file for step {step_name}: {(proof_dir / log_name).as_posix()}")

    if issues:
        print("[adlc_gate] FAIL")
        for i in issues:
            print(f" - {i}")
        return 2

    print("[adlc_gate] PASS")
    print(f"[adlc_gate] proof={proof_json.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

