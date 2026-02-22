#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLAN_REQUIRED_FIELDS = (
    "status",
    "scope-allow",
    "scope-deny",
    "gates",
    "budgets",
    "stop",
    "behaviors",
    "results",
)

PLAN_REQUIRED_GATES = ("lite", "plan_check", "patch_check", "behavior_catalog_check")
BEHAVIOR_ID_RE = re.compile(r"\bB\d{3}\b")
RESULT_ID_RE = re.compile(r"\bR\d{3}\b")
REASON_OR_RESULT_RE = re.compile(r"\b(?:B|R)\d{3}\b")
INDEX_ENTRY_RE = re.compile(
    r"^\s*-\s*(B\d{3})\b.*\b(B\d{3}-[a-z0-9][a-z0-9\-]*\.md)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class PlanContract:
    status: str
    scope_allow: tuple[str, ...]
    scope_deny: tuple[str, ...]
    gates: tuple[str, ...]
    budgets: dict[str, int]
    stop: dict[str, str]
    behaviors: tuple[str, ...]
    results: tuple[str, ...]


@dataclass(frozen=True)
class ExpectedResult:
    result_id: str
    acceptance: str
    evidence: tuple[str, ...]
    related_gates: tuple[str, ...]


def _parse_header_map(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip().lower()] = value.strip()
    return out


def parse_list(value: str) -> tuple[str, ...]:
    text = (value or "").strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()
    parts = [p.strip() for p in re.split(r"[,;|]", text) if p.strip()]
    dedup: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if part in seen:
            continue
        seen.add(part)
        dedup.append(part)
    return tuple(dedup)


def parse_map(value: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for chunk in re.split(r"[,;]", (value or "").strip()):
        token = chunk.strip()
        if not token:
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*[:=]\s*(.+)$", token)
        if not m:
            continue
        out[m.group(1).strip().lower()] = m.group(2).strip()
    return out


def _coerce_positive_int(value: Any) -> int | None:
    try:
        parsed = int(str(value).strip())
    except Exception:
        return None
    return parsed if parsed > 0 else None


def load_plan_contract(path: Path) -> tuple[PlanContract | None, list[str]]:
    if not path.exists():
        return None, [f"missing plan file: {path.as_posix()}"]
    raw = path.read_text(encoding="utf-8", errors="replace")
    kv = _parse_header_map(raw)
    errors: list[str] = []

    for key in PLAN_REQUIRED_FIELDS:
        if key not in kv:
            errors.append(f"PLAN missing required field: {key}")

    if errors:
        return None, errors

    status = kv.get("status", "").strip()
    if status != "SIGNED":
        errors.append("PLAN Status must be SIGNED")

    scope_allow = parse_list(kv.get("scope-allow", ""))
    scope_deny = parse_list(kv.get("scope-deny", ""))
    gates = parse_list(kv.get("gates", ""))
    behaviors = tuple(sorted({x for x in BEHAVIOR_ID_RE.findall(kv.get("behaviors", ""))}))
    results = tuple(sorted({x for x in RESULT_ID_RE.findall(kv.get("results", ""))}))

    budgets_raw = parse_map(kv.get("budgets", ""))
    budgets: dict[str, int] = {}
    for k in ("max_iterations", "max_files", "max_total_bytes"):
        v = _coerce_positive_int(budgets_raw.get(k))
        if v is None:
            errors.append(f"PLAN Budgets missing or invalid key: {k}")
        else:
            budgets[k] = v

    stop = parse_map(kv.get("stop", ""))
    if not stop:
        errors.append("PLAN Stop must include executable conditions")

    missing_required_gates = [g for g in PLAN_REQUIRED_GATES if g not in gates]
    if missing_required_gates:
        errors.append("PLAN Gates missing required items: " + ", ".join(missing_required_gates))

    if not scope_allow:
        errors.append("PLAN Scope-Allow must not be empty")
    if not behaviors:
        errors.append("PLAN Behaviors must include at least one B###")
    if not results:
        errors.append("PLAN Results must include at least one R###")

    if errors:
        return None, errors

    contract = PlanContract(
        status=status,
        scope_allow=scope_allow,
        scope_deny=scope_deny,
        gates=gates,
        budgets=budgets,
        stop=stop,
        behaviors=behaviors,
        results=results,
    )
    return contract, []


def load_behavior_index(index_path: Path) -> tuple[dict[str, str], list[str]]:
    if not index_path.exists():
        return {}, [f"missing behavior index: {index_path.as_posix()}"]
    entries: dict[str, str] = {}
    errors: list[str] = []
    for lineno, raw in enumerate(index_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        m = INDEX_ENTRY_RE.match(raw)
        if not m:
            continue
        bid = m.group(1).upper()
        page = m.group(2)
        if not page.startswith(f"{bid}-"):
            errors.append(f"INDEX line {lineno}: behavior/file mismatch ({bid} vs {page})")
            continue
        entries[bid] = page
    if not entries:
        errors.append("behavior INDEX has no parseable entries")
    return entries, errors


def behavior_page_has_required_sections(path: Path) -> tuple[bool, list[str]]:
    if not path.exists():
        return False, [f"missing behavior page: {path.as_posix()}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    missing: list[str] = []
    for marker in ("## Reason", "## Behavior", "## Result"):
        if marker not in text:
            missing.append(f"{path.as_posix()} missing section: {marker}")
    return (len(missing) == 0), missing


def load_expected_results(path: Path) -> tuple[dict[str, ExpectedResult], list[str]]:
    if not path.exists():
        return {}, [f"missing expected results: {path.as_posix()}"]
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    errors: list[str] = []
    rows: dict[str, dict[str, str]] = {}
    current = ""

    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        m_head = re.match(r"^(R\d{3})\s*:\s*(.+)$", line)
        if m_head:
            current = m_head.group(1)
            rows[current] = {"title": m_head.group(2).strip(), "acceptance": "", "evidence": "", "related-gates": ""}
            continue
        if not current:
            continue
        m_key = re.match(r"^(Acceptance|Evidence|Related-Gates)\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if m_key:
            key = m_key.group(1).strip().lower()
            val = m_key.group(2).strip()
            rows[current][key] = val
            continue
        if line.startswith("-"):
            # Permit note lines but keep parser strict for machine-readable keys above.
            continue
        errors.append(f"EXPECTED_RESULTS line {lineno}: unrecognized line outside machine fields")

    out: dict[str, ExpectedResult] = {}
    for rid, row in rows.items():
        acceptance = row.get("acceptance", "").strip()
        evidence = parse_list(row.get("evidence", ""))
        related = parse_list(row.get("related-gates", ""))
        if not acceptance:
            errors.append(f"{rid} missing Acceptance")
        if not evidence:
            errors.append(f"{rid} missing Evidence")
        if not related:
            errors.append(f"{rid} missing Related-Gates")
        out[rid] = ExpectedResult(
            result_id=rid,
            acceptance=acceptance,
            evidence=evidence,
            related_gates=related,
        )
    if not out:
        errors.append("EXPECTED_RESULTS has no parseable R### entries")
    return out, errors


def load_reason_refs(path: Path) -> tuple[list[tuple[int, tuple[str, ...]]], list[str]]:
    if not path.exists():
        return [], [f"missing reasons file: {path.as_posix()}"]
    refs: list[tuple[int, tuple[str, ...]]] = []
    errors: list[str] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if not line.startswith("-"):
            continue
        ids = tuple(sorted(set(REASON_OR_RESULT_RE.findall(line))))
        if not ids:
            errors.append(f"REASONS line {lineno}: missing B###/R### reference")
            continue
        refs.append((lineno, ids))
    if not refs:
        errors.append("REASONS has no parseable bullet entries")
    return refs, errors

