from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def normalize_rel_path(path: str) -> str:
    return str(path or "").strip().replace("\\", "/").strip("/")


def path_matches(path: str, rule: str) -> bool:
    rel = normalize_rel_path(path)
    pattern = normalize_rel_path(rule)
    if not rel or not pattern:
        return False
    return rel == pattern or rel.startswith(pattern + "/")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        norm = normalize_rel_path(item)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        out.append(norm)
    return out


def _strip_inline_value(value: str) -> str:
    return str(value or "").strip().strip("`").strip()


def _parse_bool(value: str) -> bool:
    text = _strip_inline_value(value).lower()
    return text in {"true", "yes", "y", "1"}


def _run_git(repo_root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def git_changed_files(repo_root: Path) -> list[str]:
    outputs = [
        _run_git(repo_root, ["diff", "--name-only"]),
        _run_git(repo_root, ["diff", "--cached", "--name-only"]),
        _run_git(repo_root, ["ls-files", "--others", "--exclude-standard"]),
    ]
    files = {
        normalize_rel_path(line)
        for output in outputs
        for line in output.splitlines()
        if normalize_rel_path(line)
    }
    return sorted(files)


def load_freeze_contract(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    doc = json.loads(path.read_text(encoding="utf-8"))
    return doc if isinstance(doc, dict) else {}


def parse_task_card(path: Path) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "allowed_write_paths": [],
        "protected_paths": [],
        "frozen_kernels_touched": False,
        "explicit_elevation_required": False,
        "explicit_elevation_signal": "",
        "forbidden_bypass": [],
        "acceptance_checks": [],
    }
    if not path.exists():
        return fields

    list_map = {
        "allowed write paths": "allowed_write_paths",
        "protected paths": "protected_paths",
        "forbidden bypass": "forbidden_bypass",
        "acceptance checks": "acceptance_checks",
    }
    scalar_map = {
        "frozen kernels touched": "frozen_kernels_touched",
        "explicit elevation required": "explicit_elevation_required",
        "explicit elevation signal": "explicit_elevation_signal",
    }

    current_list = ""
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw.strip()
        if stripped.startswith("## "):
            current_list = ""
            continue
        if not stripped.startswith("- "):
            continue

        content = stripped[2:].strip()
        lowered = content.lower()
        matched = False

        for label, key in list_map.items():
            prefix = f"{label}:"
            if lowered.startswith(prefix):
                current_list = key
                inline_value = _strip_inline_value(content[len(prefix):])
                if inline_value:
                    fields[key].append(inline_value)
                matched = True
                break
        if matched:
            continue

        for label, key in scalar_map.items():
            prefix = f"{label}:"
            if lowered.startswith(prefix):
                current_list = ""
                raw_value = content[len(prefix):]
                if key in {"frozen_kernels_touched", "explicit_elevation_required"}:
                    fields[key] = _parse_bool(raw_value)
                else:
                    fields[key] = _strip_inline_value(raw_value)
                matched = True
                break
        if matched:
            continue

        if current_list:
            item = _strip_inline_value(content)
            if item:
                fields[current_list].append(item)

    fields["allowed_write_paths"] = _dedupe(list(fields["allowed_write_paths"]))
    fields["protected_paths"] = _dedupe(list(fields["protected_paths"]))
    fields["forbidden_bypass"] = _dedupe(list(fields["forbidden_bypass"]))
    fields["acceptance_checks"] = _dedupe(list(fields["acceptance_checks"]))
    fields["explicit_elevation_signal"] = _strip_inline_value(str(fields["explicit_elevation_signal"]))
    return fields


def _matching_files(changed_files: list[str], rules: list[str]) -> list[str]:
    return [path for path in changed_files if any(path_matches(path, rule) for rule in rules)]


def _scope_changed_files(
    changed_files: list[str],
    *,
    allowed_roots: list[str],
    protected_rules: list[str],
    frozen_rules: list[str],
    lane_rules: list[str],
) -> tuple[list[str], list[str]]:
    scope_rules = _dedupe([*allowed_roots, *protected_rules, *frozen_rules, *lane_rules])
    if not scope_rules:
        return sorted(changed_files), []
    scoped = [path for path in changed_files if any(path_matches(path, rule) for rule in scope_rules)]
    ignored = [path for path in changed_files if path not in scoped]
    return sorted(scoped), sorted(ignored)


def evaluate_module_protection(
    repo_root: Path,
    *,
    changed_files: list[str] | None = None,
    contract_path: Path | None = None,
    task_card_path: Path | None = None,
) -> dict[str, Any]:
    root = repo_root.resolve()
    contract_file = contract_path or (root / "contracts" / "module_freeze.json")
    task_file = task_card_path or (root / "meta" / "tasks" / "CURRENT.md")

    contract = load_freeze_contract(contract_file)
    task = parse_task_card(task_file)
    all_changed = sorted(changed_files if changed_files is not None else git_changed_files(root))

    frozen_rules = _dedupe([str(x) for x in contract.get("frozen_kernels", []) if str(x).strip()])
    lane_rules = _dedupe([str(x) for x in contract.get("lane_owned", []) if str(x).strip()])
    default_rules = _dedupe([str(x) for x in contract.get("task_writable_defaults", []) if str(x).strip()])
    allowed_roots = list(task.get("allowed_write_paths", [])) or default_rules
    protected_rules = list(task.get("protected_paths", []))
    changed, ignored = _scope_changed_files(
        all_changed,
        allowed_roots=allowed_roots,
        protected_rules=protected_rules,
        frozen_rules=frozen_rules,
        lane_rules=lane_rules,
    )

    frozen_files = _matching_files(changed, frozen_rules)
    lane_files = [path for path in _matching_files(changed, lane_rules) if path not in frozen_files]
    task_files = [path for path in changed if path not in frozen_files and path not in lane_files]
    protected_files = _matching_files(changed, protected_rules)

    ownership = "task-owned"
    if frozen_files:
        ownership = "frozen-kernel"
    elif lane_files:
        ownership = "lane-owned"

    not_allowed = [path for path in changed if allowed_roots and not any(path_matches(path, rule) for rule in allowed_roots)]

    violations: list[str] = []
    if not list(task.get("allowed_write_paths", [])):
        violations.append("CURRENT.md missing Allowed Write Paths entries")
    if not list(task.get("protected_paths", [])):
        violations.append("CURRENT.md missing Protected Paths entries")
    if not list(task.get("forbidden_bypass", [])):
        violations.append("CURRENT.md missing Forbidden Bypass entries")
    if not list(task.get("acceptance_checks", [])):
        violations.append("CURRENT.md missing Acceptance Checks entries")
    for path in not_allowed:
        violations.append(f"path outside CURRENT.md Allowed Write Paths: {path}")

    if frozen_files:
        if not bool(task.get("frozen_kernels_touched", False)):
            violations.append("frozen-kernel change detected but CURRENT.md does not set Frozen Kernels Touched: true")
        if not bool(task.get("explicit_elevation_required", False)):
            violations.append("frozen-kernel change detected but CURRENT.md does not set Explicit Elevation Required: true")
        signal = str(task.get("explicit_elevation_signal", "")).strip().lower()
        if signal in {"", "none"}:
            violations.append("frozen-kernel change detected but CURRENT.md has no Explicit Elevation Signal")

    if protected_files and not bool(task.get("frozen_kernels_touched", False)):
        violations.append("protected path touched without Frozen Kernels Touched acknowledgement")

    return {
        "schema_version": "ctcp-module-protection-eval-v1",
        "contract_path": str(contract_file.resolve()),
        "task_card_path": str(task_file.resolve()),
        "all_changed_files": all_changed,
        "changed_files": changed,
        "ignored_changed_files": ignored,
        "ownership": ownership,
        "task_owned_files": task_files,
        "lane_owned_files": lane_files,
        "frozen_kernel_files": frozen_files,
        "protected_touched_files": protected_files,
        "allowed_write_paths": allowed_roots,
        "task_card": task,
        "requires_lane_regression": ownership in {"lane-owned", "frozen-kernel"},
        "requires_frozen_regression": ownership == "frozen-kernel",
        "lane_regression_tests": [str(x) for x in contract.get("lane_regression_tests", []) if str(x).strip()],
        "frozen_kernel_regression_tests": [
            str(x) for x in contract.get("frozen_kernel_regression_tests", []) if str(x).strip()
        ],
        "violations": violations,
    }
