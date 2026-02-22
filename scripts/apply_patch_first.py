#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.patch_first import PatchPolicy, apply_patch_safely


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_policy(path: Path) -> PatchPolicy:
    raw = json.loads(_read_text(path))
    if not isinstance(raw, dict):
        raise ValueError("policy json must be an object")
    return PatchPolicy.from_mapping(raw)


def _print_result(doc: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    # BEHAVIOR_ID: B032
    ap = argparse.ArgumentParser(description="Patch-first safe apply helper")
    ap.add_argument("--repo", default=".", help="repository root")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--patch", default="", help="path to unified diff patch file")
    src.add_argument("--stdin", action="store_true", help="read patch text from stdin")
    ap.add_argument("--policy-json", default="", help="optional patch policy JSON path")
    args = ap.parse_args()

    repo_root = Path(args.repo).expanduser().resolve()
    if not repo_root.exists():
        _print_result({"ok": False, "stage": "env", "code": "PATCH_ENV_INVALID", "message": f"repo does not exist: {repo_root}"})
        return 2

    try:
        if args.stdin:
            patch_text = sys.stdin.read()
        else:
            patch_path = Path(str(args.patch)).expanduser().resolve()
            if not patch_path.exists():
                _print_result(
                    {
                        "ok": False,
                        "stage": "env",
                        "code": "PATCH_ENV_INVALID",
                        "message": f"patch file does not exist: {patch_path}",
                    }
                )
                return 2
            patch_text = _read_text(patch_path)
    except Exception as exc:
        _print_result({"ok": False, "stage": "env", "code": "PATCH_ENV_INVALID", "message": str(exc)})
        return 2

    policy: PatchPolicy | None = None
    if str(args.policy_json).strip():
        policy_path = Path(str(args.policy_json)).expanduser().resolve()
        if not policy_path.exists():
            _print_result(
                {
                    "ok": False,
                    "stage": "env",
                    "code": "PATCH_ENV_INVALID",
                    "message": f"policy json does not exist: {policy_path}",
                }
            )
            return 2
        try:
            policy = _load_policy(policy_path)
        except Exception as exc:
            _print_result({"ok": False, "stage": "policy", "code": "PATCH_POLICY_INVALID", "message": str(exc)})
            return 2

    result = apply_patch_safely(repo_root=repo_root, diff_text=patch_text, policy=policy)
    _print_result(result.to_dict())

    if result.ok:
        return 0
    if result.code in {"PATCH_ENV_INVALID", "PATCH_POLICY_INVALID"}:
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
