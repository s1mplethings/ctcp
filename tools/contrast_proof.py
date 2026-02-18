#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _step_map(proof: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for s in proof.get("steps", []):
        if isinstance(s, dict) and s.get("name"):
            out[str(s["name"])] = s
    return out


def _fmt_delta(new_val: float, old_val: float) -> str:
    delta = new_val - old_val
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.3f}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare two proof.json files.")
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    old_path = Path(args.old).resolve()
    new_path = Path(args.new).resolve()
    out_path = Path(args.out).resolve()

    old = _load(old_path)
    new = _load(new_path)
    old_steps = _step_map(old)
    new_steps = _step_map(new)

    all_steps = ["configure", "build", "ctest", "install", "smoke"]
    lines = [
        "# Contrast Report",
        "",
        f"- Old proof: `{old_path.as_posix()}`",
        f"- New proof: `{new_path.as_posix()}`",
        "",
        "## Result",
        "",
        f"- Old: `{old.get('result', 'UNKNOWN')}`",
        f"- New: `{new.get('result', 'UNKNOWN')}`",
        "",
        "## Step Comparison",
        "",
        "| Step | Old exit | New exit | Status change |",
        "| --- | ---: | ---: | --- |",
    ]

    for step in all_steps:
        o = old_steps.get(step, {})
        n = new_steps.get(step, {})
        o_rc = o.get("exit_code")
        n_rc = n.get("exit_code")
        if o_rc == n_rc:
            change = "unchanged"
        else:
            change = "changed"
        lines.append(f"| {step} | {o_rc} | {n_rc} | {change} |")

    old_m = old.get("metrics", {})
    new_m = new.get("metrics", {})
    old_ct = old_m.get("ctest", {}) if isinstance(old_m.get("ctest", {}), dict) else {}
    new_ct = new_m.get("ctest", {}) if isinstance(new_m.get("ctest", {}), dict) else {}
    old_total = float(old_ct.get("total", 0) or 0)
    new_total = float(new_ct.get("total", 0) or 0)
    old_dur = float(old_m.get("total_duration_sec", 0) or 0)
    new_dur = float(new_m.get("total_duration_sec", 0) or 0)
    old_install_files = float((old_m.get("install", {}) or {}).get("file_count", 0) or 0)
    new_install_files = float((new_m.get("install", {}) or {}).get("file_count", 0) or 0)
    old_install_bytes = float((old_m.get("install", {}) or {}).get("total_bytes", 0) or 0)
    new_install_bytes = float((new_m.get("install", {}) or {}).get("total_bytes", 0) or 0)
    old_smoke = old_steps.get("smoke", {}).get("exit_code")
    new_smoke = new_steps.get("smoke", {}).get("exit_code")

    lines.extend(
        [
            "",
            "## Metrics Delta",
            "",
            f"- ctest total: old={int(old_total)} new={int(new_total)} delta={_fmt_delta(new_total, old_total)}",
            f"- total duration sec: old={old_dur:.3f} new={new_dur:.3f} delta={_fmt_delta(new_dur, old_dur)}",
            f"- install file count: old={int(old_install_files)} new={int(new_install_files)} delta={_fmt_delta(new_install_files, old_install_files)}",
            f"- install total bytes: old={int(old_install_bytes)} new={int(new_install_bytes)} delta={_fmt_delta(new_install_bytes, old_install_bytes)}",
            f"- smoke exit code: old={old_smoke} new={new_smoke}",
            "",
        ]
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[contrast_proof] wrote {out_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

