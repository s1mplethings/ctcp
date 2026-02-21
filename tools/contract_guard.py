#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def _normalize_prefix(value: str) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    return text if text.endswith("/") else text + "/"


def _parse_scalar(value: str) -> Any:
    text = value.strip().strip("'").strip('"')
    if text.lower() in {"true", "false"}:
        return text.lower() == "true"
    try:
        return int(text)
    except Exception:
        return text


def load_policy(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}

    doc: dict[str, Any] = {}
    current_list_key = ""
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- "):
            if not current_list_key:
                continue
            doc.setdefault(current_list_key, [])
            doc[current_list_key].append(stripped[2:].strip().strip("'").strip('"'))
            continue

        current_list_key = ""
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            doc[key] = []
            current_list_key = key
        else:
            doc[key] = _parse_scalar(value)
    return doc


def _run_git(repo_root: Path, args: list[str]) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, text


def _is_git_noise_line(raw: str) -> bool:
    text = str(raw or "").strip()
    if not text:
        return True
    lower = text.lower()
    return lower.startswith("warning: ") or lower.startswith("hint: ")


def _collect_diff(repo_root: Path) -> tuple[list[str], dict[str, Any], list[str]]:
    touched: set[str] = set()
    stats = {
        "files": {},
        "total_files": 0,
        "added_lines": 0,
        "deleted_lines": 0,
        "total_lines": 0,
    }
    errors: list[str] = []

    for args in (["diff", "--name-only"], ["diff", "--cached", "--name-only"]):
        rc, out = _run_git(repo_root, args)
        if rc != 0:
            errors.append(f"git {' '.join(args)} failed")
            continue
        for row in out.splitlines():
            if _is_git_noise_line(row):
                continue
            rel = row.strip().replace("\\", "/")
            if rel:
                touched.add(rel)

    def parse_numstat(output: str) -> None:
        for row in output.splitlines():
            if _is_git_noise_line(row):
                continue
            parts = row.split("\t")
            if len(parts) < 3:
                continue
            added_raw, deleted_raw, path_raw = parts[0], parts[1], parts[2]
            rel = path_raw.strip().replace("\\", "/")
            if not rel:
                continue
            try:
                added = int(added_raw)
            except Exception:
                added = 0
            try:
                deleted = int(deleted_raw)
            except Exception:
                deleted = 0
            touched.add(rel)
            file_stats = stats["files"].setdefault(rel, {"added": 0, "deleted": 0})
            file_stats["added"] += added
            file_stats["deleted"] += deleted
            stats["added_lines"] += added
            stats["deleted_lines"] += deleted

    for args in (["diff", "--numstat"], ["diff", "--cached", "--numstat"]):
        rc, out = _run_git(repo_root, args)
        if rc != 0:
            errors.append(f"git {' '.join(args)} failed")
            continue
        parse_numstat(out)

    stats["total_files"] = len(touched)
    stats["total_lines"] = int(stats["added_lines"]) + int(stats["deleted_lines"])
    return sorted(touched), stats, errors


def _path_matches_prefix(path: str, prefixes: list[str]) -> bool:
    rel = path.strip().replace("\\", "/")
    for pref in prefixes:
        norm = _normalize_prefix(pref)
        if not norm:
            continue
        raw = norm[:-1]
        if rel == raw or rel.startswith(norm):
            return True
    return False


def evaluate(
    repo_root: str | Path,
    *,
    policy_path: str | Path | None = None,
    out_path: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    policy_file = Path(policy_path) if policy_path else (root / "contracts" / "allowed_changes.yaml")
    policy = load_policy(policy_file)

    allowed_paths = [str(x) for x in policy.get("allowed_paths", []) if str(x).strip()]
    blocked_paths = [str(x) for x in policy.get("blocked_paths", []) if str(x).strip()]
    max_files = int(policy.get("max_files", 10))
    max_added = int(policy.get("max_added_lines", 800))
    max_deleted = int(policy.get("max_deleted_lines", 800))
    max_total = int(policy.get("max_total_lines", 800))

    touched_files, stats, git_errors = _collect_diff(root)
    reasons: list[str] = []
    reasons.extend(git_errors)

    for rel in touched_files:
        if blocked_paths and _path_matches_prefix(rel, blocked_paths):
            reasons.append(f"blocked path touched: {rel}")
        if allowed_paths and not _path_matches_prefix(rel, allowed_paths):
            reasons.append(f"path outside allowlist: {rel}")

    if stats["total_files"] > max_files:
        reasons.append(f"changed file count {stats['total_files']} exceeds max_files={max_files}")
    if stats["added_lines"] > max_added:
        reasons.append(f"added lines {stats['added_lines']} exceeds max_added_lines={max_added}")
    if stats["deleted_lines"] > max_deleted:
        reasons.append(f"deleted lines {stats['deleted_lines']} exceeds max_deleted_lines={max_deleted}")
    if stats["total_lines"] > max_total:
        reasons.append(f"total changed lines {stats['total_lines']} exceeds max_total_lines={max_total}")

    passed = len(reasons) == 0
    review = {
        "contract_guard": {
            "pass": passed,
            "policy_path": str(policy_file.resolve()),
            "reasons": reasons,
            "touched_files": touched_files,
            "stats": stats,
            "limits": {
                "max_files": max_files,
                "max_added_lines": max_added,
                "max_deleted_lines": max_deleted,
                "max_total_lines": max_total,
                "allowed_paths": allowed_paths,
                "blocked_paths": blocked_paths,
            },
        }
    }

    target = Path(out_path) if out_path else (root / "reviews" / "contract_review.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return review


def main() -> int:
    ap = argparse.ArgumentParser(description="Contract guard for local diff scope and size")
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--policy", default="")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    doc = evaluate(
        args.repo_root,
        policy_path=args.policy or None,
        out_path=args.out or None,
    )
    guard = doc.get("contract_guard", {})
    if bool(guard.get("pass", False)):
        print("[contract_guard] PASS")
        return 0
    print("[contract_guard] FAIL")
    for reason in guard.get("reasons", []):
        print(f"- {reason}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
