from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MATRIX_PATH = ROOT / "contracts" / "project_domain_matrix.json"


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").replace("\r", " ").replace("\n", " ").split()).strip().lower()


def _normalize_rel(path: str) -> str:
    return str(path or "").strip().replace("\\", "/").lower()


def _signal_contains(signal_text: str, token: str) -> bool:
    normalized_signal = _normalize_text(signal_text)
    normalized_token = _normalize_text(token)
    if not normalized_signal or not normalized_token:
        return False
    if any(ord(ch) > 127 for ch in normalized_token):
        return normalized_token in normalized_signal
    return f" {normalized_token} " in f" {normalized_signal} "


@lru_cache(maxsize=1)
def load_domain_matrix() -> dict[str, Any]:
    raw = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("project_domain_matrix.json must be an object")
    return raw


def domain_spec(domain_id: str) -> dict[str, Any]:
    matrix = load_domain_matrix()
    domains = dict(matrix.get("domains", {}))
    default_id = str(matrix.get("default_domain", "generic_software_project")).strip() or "generic_software_project"
    raw = domains.get(domain_id) or domains.get(default_id) or {}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "domain_id": domain_id if domain_id in domains else default_id,
        "scaffold_family": str(raw.get("scaffold_family", "")).strip(),
        "project_type": str(raw.get("project_type", "")).strip(),
        "default_archetype": str(raw.get("default_archetype", "")).strip(),
        "default_delivery_shape": str(raw.get("default_delivery_shape", "")).strip(),
        "keywords": [str(item).strip() for item in raw.get("keywords", []) if str(item).strip()],
        "allowed_families": [str(item).strip() for item in raw.get("allowed_families", []) if str(item).strip()],
        "incompatible_families": [str(item).strip() for item in raw.get("incompatible_families", []) if str(item).strip()],
        "contamination_markers": [str(item).strip() for item in raw.get("contamination_markers", []) if str(item).strip()],
        "readme_required_sections": [str(item).strip() for item in raw.get("readme_required_sections", []) if str(item).strip()],
        "ux_preview_keywords": [str(item).strip() for item in raw.get("ux_preview_keywords", []) if str(item).strip()],
    }


def _constraint_domain(constraints: dict[str, Any]) -> tuple[str, str]:
    for key in ("project_domain", "domain", "workflow_intent_domain"):
        value = str(constraints.get(key, "")).strip()
        if value:
            return value, f"constraints.{key}"
    return "", ""


def _signal_text(
    *,
    goal: str,
    project_intent: dict[str, Any] | None,
    project_spec: dict[str, Any] | None,
    context_files: list[dict[str, Any]] | None,
    constraints: dict[str, Any] | None,
) -> str:
    parts: list[str] = [str(goal or "")]
    for doc in (project_intent or {}, project_spec or {}, constraints or {}):
        if not isinstance(doc, dict):
            continue
        for value in doc.values():
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, list):
                parts.extend(str(item) for item in value)
    for item in context_files or []:
        if not isinstance(item, dict):
            continue
        parts.append(str(item.get("path", "")))
        parts.append(str(item.get("content", ""))[:2000])
    return _normalize_text(" ".join(parts))


def detect_project_domain(
    *,
    goal: str,
    project_intent: dict[str, Any] | None = None,
    project_spec: dict[str, Any] | None = None,
    context_files: list[dict[str, Any]] | None = None,
    constraints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    matrix = load_domain_matrix()
    domains = dict(matrix.get("domains", {}))
    default_id = str(matrix.get("default_domain", "generic_software_project")).strip() or "generic_software_project"
    constraints = dict(constraints or {})
    explicit_value, explicit_source = _constraint_domain(constraints)
    signal = _signal_text(
        goal=goal,
        project_intent=project_intent,
        project_spec=project_spec,
        context_files=context_files,
        constraints=constraints,
    )
    signal_text = f" {signal} "

    if explicit_value:
        lowered = _normalize_text(explicit_value)
        for domain_id, raw in domains.items():
            spec = domain_spec(domain_id)
            candidates = [domain_id, lowered] + spec["keywords"]
            if lowered == _normalize_text(domain_id) or lowered in {_normalize_text(item) for item in candidates}:
                return {
                    **spec,
                    "decision_source": explicit_source,
                    "matched_terms": [explicit_value],
                    "signal_excerpt": signal[:320],
                }

    best_domain = default_id
    best_terms: list[str] = []
    best_score = 0
    ordered_domains = [
        "v2p_pipeline",
        "pointcloud_pipeline",
        "reconstruction_pipeline",
        "narrative_vn_editor",
        "indie_studio_production_hub",
        "team_task_management",
        "admin_dashboard",
        "computer_vision_demo",
        "media_tool",
        "data_tool",
        default_id,
    ]
    for domain_id in ordered_domains:
        if domain_id not in domains:
            continue
        spec = domain_spec(domain_id)
        matched = []
        for keyword in spec["keywords"]:
            token = _normalize_text(keyword)
            if token and _signal_contains(signal, token):
                matched.append(keyword)
        score = len(set(matched))
        if score > best_score:
            best_domain = domain_id
            best_terms = sorted(set(matched))
            best_score = score
    spec = domain_spec(best_domain)
    return {
        **spec,
        "decision_source": "signal_keywords" if best_score > 0 else "default_domain",
        "matched_terms": best_terms,
        "signal_excerpt": signal[:320],
    }


def compatibility_report(*, project_domain: str, scaffold_family: str) -> dict[str, Any]:
    spec = domain_spec(project_domain)
    allowed = list(spec.get("allowed_families", []))
    incompatible = list(spec.get("incompatible_families", []))
    family = str(scaffold_family or "").strip()
    passed = family in allowed if allowed else True
    if family in incompatible:
        passed = False
    reasons: list[str] = []
    if family and allowed and family not in allowed:
        reasons.append(f"domain `{project_domain}` requires one of {allowed}, got `{family}`")
    if family and family in incompatible:
        reasons.append(f"domain `{project_domain}` is incompatible with scaffold family `{family}`")
    return {
        "passed": passed,
        "project_domain": str(spec.get("domain_id", project_domain)).strip(),
        "scaffold_family": family,
        "allowed_families": allowed,
        "incompatible_families": incompatible,
        "reasons": reasons,
    }


def contamination_hits(*, project_domain: str, rel_paths: list[str]) -> list[str]:
    spec = domain_spec(project_domain)
    markers = [marker.lower() for marker in spec.get("contamination_markers", [])]
    hits: list[str] = []
    seen: set[str] = set()
    for raw in rel_paths:
        rel = _normalize_rel(raw)
        if not rel:
            continue
        for marker in markers:
            if marker and marker in rel and rel not in seen:
                seen.add(rel)
                hits.append(raw.replace("\\", "/"))
                break
    return sorted(hits)


def readme_required_sections(project_domain: str) -> list[str]:
    return list(domain_spec(project_domain).get("readme_required_sections", []))


def preview_keywords(project_domain: str) -> list[str]:
    return list(domain_spec(project_domain).get("ux_preview_keywords", []))
