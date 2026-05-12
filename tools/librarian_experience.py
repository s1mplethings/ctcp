from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def build_librarian_experience_record(*, report: dict[str, Any]) -> dict[str, Any]:
    status = str(report.get("status", "")).strip() or "unknown"
    failed_checks = _failed_checks(report)
    lessons = _lessons(report, failed_checks=failed_checks)
    project_domain = str(report.get("project_domain", "")).strip() or "unknown"
    scaffold_family = str(report.get("scaffold_family", "")).strip() or "unknown"
    blocking_reason = str(report.get("blocking_reason", "")).strip()
    return {
        "schema_version": "ctcp-librarian-experience-record-v1",
        "source": {"artifact": "artifacts/source_generation_report.json", "stage": "source_generation"},
        "status": status,
        "project_domain": project_domain,
        "scaffold_family": scaffold_family,
        "library_plan_path": str(report.get("library_plan_path", "")).strip(),
        "file_manifest_path": str(report.get("file_manifest_path", "")).strip(),
        "model_budget_path": str(report.get("model_budget_path", "")).strip(),
        "provider_authored_source": _provider_authored_source(report),
        "blocking_reason": blocking_reason,
        "failed_checks": failed_checks,
        "lessons": lessons,
        "retrieval_text": _retrieval_text(
            status=status,
            project_domain=project_domain,
            scaffold_family=scaffold_family,
            blocking_reason=blocking_reason,
            failed_checks=failed_checks,
            lessons=lessons,
            report=report,
        ),
    }


def build_librarian_recipe_candidate(*, record: dict[str, Any]) -> dict[str, Any]:
    status = str(record.get("status", "")).strip()
    lessons = [str(item) for item in record.get("lessons", []) if str(item)]
    return {
        "schema_version": "ctcp-librarian-recipe-candidate-v1",
        "source_record": "artifacts/librarian_experience_record.json",
        "status": status,
        "project_domain": str(record.get("project_domain", "")),
        "recipe_type": "success_pattern" if status == "pass" else "failure_repair_pattern",
        "steps": lessons[:8],
        "search_tags": _search_tags(record),
    }


def write_librarian_experience_feedback(*, run_dir: Path, report: dict[str, Any]) -> dict[str, Any]:
    record = build_librarian_experience_record(report=report)
    recipe = build_librarian_recipe_candidate(record=record)
    record_rel = "artifacts/librarian_experience_record.json"
    recipe_rel = "artifacts/librarian_recipe_candidate.json"
    _write_json(run_dir / record_rel, record)
    _write_json(run_dir / recipe_rel, recipe)
    return {
        "record": record,
        "record_path": record_rel,
        "recipe": recipe,
        "recipe_path": recipe_rel,
    }


def _failed_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in (
        "generic_validation",
        "domain_validation",
        "readme_quality",
        "ux_validation",
        "product_validation",
        "capability_validation",
        "generation_quality",
        "library_usage_verification",
    ):
        value = report.get(key)
        if not isinstance(value, dict) or bool(value.get("passed", True)):
            continue
        reason = "; ".join(str(item) for item in value.get("reasons", []) if str(item))
        rows.append({"check_id": key, "reason": reason or str(value.get("details", ""))[:500]})
    return rows


def _lessons(report: dict[str, Any], *, failed_checks: list[dict[str, Any]]) -> list[str]:
    lessons: list[str] = []
    if report.get("library_plan_path"):
        lessons.append("Reuse the recorded library_plan before authoring provider files.")
    if report.get("file_manifest_path"):
        lessons.append("Keep provider generation bounded to file_manifest paths and single-file tasks.")
    if not _provider_authored_source(report):
        lessons.append("Production delivery must remain blocked until provider-authored source files exist.")
    if any(row.get("check_id") == "library_usage_verification" for row in failed_checks):
        lessons.append("Repair library usage before delivery; do not replace required libraries with hand-written framework code.")
    if any(row.get("check_id") == "generic_validation" for row in failed_checks):
        lessons.append("Feed concrete runtime and import failures back into the next source_generation repair.")
    if not failed_checks and str(report.get("status", "")) == "pass":
        lessons.append("Prefer this library-first artifact shape for similar successful projects.")
    return lessons or ["Record source_generation outcome for future similar runs."]


def _provider_authored_source(report: dict[str, Any]) -> bool:
    provenance = report.get("provenance") if isinstance(report.get("provenance"), dict) else {}
    materialization = provenance.get("materialization") if isinstance(provenance.get("materialization"), dict) else {}
    if "provider_source_files_applied" in materialization:
        return bool(materialization.get("provider_source_files_applied"))
    return bool(report.get("provider_source_files_applied", False))


def _retrieval_text(
    *,
    status: str,
    project_domain: str,
    scaffold_family: str,
    blocking_reason: str,
    failed_checks: list[dict[str, Any]],
    lessons: list[str],
    report: dict[str, Any],
) -> str:
    parts = [
        "source_generation experience",
        f"status {status}",
        f"project_domain {project_domain}",
        f"scaffold_family {scaffold_family}",
        f"library_plan {report.get('library_plan_path', '')}",
        f"file_manifest {report.get('file_manifest_path', '')}",
        blocking_reason,
        " ".join(str(row.get("check_id", "")) + " " + str(row.get("reason", "")) for row in failed_checks),
        " ".join(lessons),
    ]
    return "\n".join(part for part in parts if str(part).strip())


def _search_tags(record: dict[str, Any]) -> list[str]:
    tags = {"source_generation", str(record.get("status", "")), str(record.get("project_domain", "")), str(record.get("scaffold_family", ""))}
    if record.get("library_plan_path"):
        tags.add("library_first")
    if record.get("failed_checks"):
        tags.add("repair")
    return sorted(tag for tag in tags if tag)


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "build_librarian_experience_record",
    "build_librarian_recipe_candidate",
    "write_librarian_experience_feedback",
]
