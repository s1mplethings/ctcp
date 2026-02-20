#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


RULES: list[tuple[str, list[str], list[str]]] = [
    (
        "DOC_FAIL",
        ["sync_doc_links", "doc index check", "out of sync", "doc index"],
        [
            "Run `python scripts/sync_doc_links.py` to resync README doc index.",
            "Re-run `scripts/verify_repo.*` and confirm doc index gate is green.",
        ],
    ),
    (
        "CONTRACT_FAIL",
        ["contract checks", "contract_checks.py", "contract_guard", "workflow_checks"],
        [
            "Inspect contract gate output and keep edits inside allowed directories.",
            "Fix contract/doc link violations before the next verify run.",
        ],
    ),
    (
        "SIMLAB_FAIL",
        ["simlab", "suite_gate.py", "forge_full_suite", "lite scenario replay"],
        [
            "Open simlab logs and isolate the first failing scenario.",
            "Apply the smallest fix for that scenario and rerun lite replay.",
        ],
    ),
    (
        "PY_IMPORT_FAIL",
        ["modulenotfounderror", "importerror", "no module named"],
        [
            "Fix the failing Python import/module path.",
            "Run local unit tests before re-running `verify_repo`.",
        ],
    ),
]


def _pick_summary(text: str, *, max_lines: int = 8, max_chars: int = 700) -> str:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return "(empty)"
    picked = lines[-max_lines:]
    out = "\n".join(picked)
    if len(out) > max_chars:
        out = out[-max_chars:]
    return out


def classify_verify(rc: int, stdout: str, stderr: str) -> dict[str, Any]:
    merged = f"{stdout}\n{stderr}".lower()
    if int(rc) == 0:
        return {
            "label": "PASS",
            "next_actions": ["No action needed."],
            "matched_keywords": [],
        }

    for label, keys, actions in RULES:
        matched = [k for k in keys if k.lower() in merged]
        if matched:
            return {
                "label": label,
                "next_actions": actions,
                "matched_keywords": matched,
            }

    return {
        "label": "UNKNOWN",
        "next_actions": [
            "Inspect verify stdout/stderr logs for the first hard failure.",
            "Use Local Librarian evidence to plan a minimal, targeted fix.",
        ],
        "matched_keywords": [],
    }


def write_fix_brief(
    *,
    out_path: str | Path,
    rc: int,
    stdout: str,
    stderr: str,
    references: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = classify_verify(rc=rc, stdout=stdout, stderr=stderr)
    refs = references or []
    label = str(result["label"])
    actions = [str(x) for x in result.get("next_actions", [])]

    lines: list[str] = [
        "# Fix Brief",
        "",
        f"- label: `{label}`",
        f"- verify_rc: `{int(rc)}`",
    ]
    keys = [str(x) for x in result.get("matched_keywords", []) if str(x).strip()]
    if keys:
        lines.append(f"- matched_keywords: `{', '.join(keys)}`")

    lines += [
        "",
        "## Minimal Next Actions",
    ]
    for action in actions:
        lines.append(f"- {action}")

    lines += [
        "",
        "## Related File References",
    ]
    if refs:
        for row in refs:
            path = str(row.get("path", ""))
            start_line = int(row.get("start_line", 0) or 0)
            end_line = int(row.get("end_line", 0) or 0)
            if start_line > 0 and end_line > 0:
                lines.append(f"- `{path}:{start_line}-{end_line}`")
            else:
                lines.append(f"- `{path}`")
    else:
        lines.append("- (no librarian references)")

    lines += [
        "",
        "## Verify stdout summary",
        "```",
        _pick_summary(stdout),
        "```",
        "",
        "## Verify stderr summary",
        "```",
        _pick_summary(stderr),
        "```",
        "",
    ]

    target = Path(out_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Rule-based contrast classifier for verify output")
    ap.add_argument("--rc", type=int, required=True)
    ap.add_argument("--stdout", default="")
    ap.add_argument("--stderr", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    result = classify_verify(rc=args.rc, stdout=args.stdout, stderr=args.stderr)
    if args.out:
        write_fix_brief(
            out_path=args.out,
            rc=args.rc,
            stdout=args.stdout,
            stderr=args.stderr,
            references=[],
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

