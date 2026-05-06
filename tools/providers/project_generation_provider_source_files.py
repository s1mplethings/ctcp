from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _candidate_provider_file_rows(src: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[Any] = []
    for key in ("files", "provider_source_files", "generated_files", "project_files"):
        value = src.get(key)
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            candidates.extend({"path": k, "content": v} for k, v in value.items())
    bundle = src.get("source_bundle")
    if isinstance(bundle, dict):
        value = bundle.get("files")
        if isinstance(value, list):
            candidates.extend(value)
        elif isinstance(value, dict):
            candidates.extend({"path": k, "content": v} for k, v in value.items())
    return [dict(row) for row in candidates if isinstance(row, dict)]


def _provider_source_file_rows(inputs: dict[str, Any]) -> list[dict[str, str]]:
    src = dict(inputs.get("src", {})) if isinstance(inputs.get("src", {}), dict) else {}
    project_root = str(inputs.get("project_root", "")).strip().replace("\\", "/").strip("/")
    if not project_root:
        return []
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for row in _candidate_provider_file_rows(src):
        rel = str(row.get("path", "")).strip().replace("\\", "/").lstrip("/")
        content = row.get("content")
        content_lines = row.get("content_lines")
        if not isinstance(content, str) and isinstance(content_lines, list):
            normalized_lines = [str(item) for item in content_lines]
            content = "\n".join(normalized_lines) + ("\n" if normalized_lines else "")
        if rel and rel not in seen and rel.startswith(project_root + "/") and isinstance(content, str) and content.strip():
            out.append({"path": rel, "content": content})
            seen.add(rel)
    return out


def _materialize_provider_source_files(*, run_dir: Path, inputs: dict[str, Any], rows: list[dict[str, str]]) -> list[str]:
    written: list[str] = []
    root = run_dir.resolve()
    for row in rows:
        rel = row["path"]
        target = (run_dir / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(row["content"], encoding="utf-8", errors="replace")
        written.append(rel)
    written.extend(_ensure_provider_package_init_files(run_dir=run_dir, inputs=inputs, already_written=set(written)))
    if written:
        _write_provider_source_map(run_dir=run_dir, inputs=inputs, rows=rows)
    return written


def _write_provider_source_map(*, run_dir: Path, inputs: dict[str, Any], rows: list[dict[str, str]]) -> None:
    src = dict(inputs.get("src", {})) if isinstance(inputs.get("src", {}), dict) else {}
    source_map = src.get("source_map") if isinstance(src.get("source_map"), dict) else {}
    path = run_dir / str(inputs["project_root"]) / "sample_data" / "source_map.json"
    existing = _read_json_dict(path)
    doc = dict(existing)
    doc.update(dict(source_map))
    doc["api_content_applied"] = True
    doc["api_content_source_ref"] = str(doc.get("api_content_source_ref", "")).strip() or "API:api_agent/source_generation"
    _ensure_provider_source_refs(doc, rows)
    doc["provider_authored_file_count"] = len(rows)
    doc["provider_authored_files"] = [row["path"] for row in rows]
    _write_json(path, doc)


def _read_json_dict(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _ensure_provider_source_refs(doc: dict[str, Any], rows: list[dict[str, str]]) -> None:
    source_ref = str(doc.get("api_content_source_ref", "")).strip() or "API:api_agent/source_generation"
    items = [dict(row) for row in doc.get("content_items", []) if isinstance(row, dict)]
    if not any(str(row.get("source", "")).strip().startswith("API:") for row in items):
        items.append({"item_id": "provider_authored_source_bundle", "source": source_ref})
    field_sources = dict(doc.get("field_sources", {})) if isinstance(doc.get("field_sources", {}), dict) else {}
    if not any(str(value).strip().startswith("API:") for value in field_sources.values()):
        for row in rows[:40]:
            field_sources[f"files.{row['path']}"] = source_ref
    doc["content_items"] = items
    doc["field_sources"] = field_sources


def _ensure_provider_package_init_files(*, run_dir: Path, inputs: dict[str, Any], already_written: set[str]) -> list[str]:
    root = run_dir.resolve()
    project_root = str(inputs.get("project_root", "")).strip().replace("\\", "/")
    lists = inputs.get("lists") if isinstance(inputs.get("lists"), dict) else {}
    expected = list(lists.get("source_files", [])) if isinstance(lists.get("source_files", []), list) else []
    added: list[str] = []
    for raw in expected:
        rel = str(raw or "").strip().replace("\\", "/")
        if not rel.endswith("/__init__.py") or rel in already_written:
            continue
        if project_root and not rel.startswith(project_root + "/"):
            continue
        target = (run_dir / rel).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            continue
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('"""Package marker for provider-authored source bundle."""\n', encoding="utf-8")
        added.append(rel)
    return added


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
