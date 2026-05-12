from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any


KNOWN_LIBRARY_PURPOSES: dict[str, str] = {
    "typer": "CLI command routing",
    "pydantic": "data model validation and serialization",
    "rich": "terminal tables and readable output",
    "pytest": "test execution",
    "fastapi": "HTTP API routing",
    "sqlalchemy": "database ORM",
}

MUST_USE_BY_LIBRARY: dict[str, list[str]] = {
    "typer": ["typer.Typer"],
    "pydantic": ["pydantic.BaseModel"],
    "rich": ["rich.console.Console", "rich.table.Table"],
}

FORBIDDEN_BY_LIBRARY: dict[str, list[str]] = {
    "typer": ["manual sys.argv parsing", "manual argparse command routing"],
    "pydantic": ["manual dict schema validation framework"],
    "rich": ["custom table padding logic"],
}

FORBIDDEN_PATTERN_MAP: dict[str, list[str]] = {
    "manual sys.argv parsing": ["sys.argv"],
    "manual argparse command routing": ["argparse.ArgumentParser", "argparse.SubParser"],
    "manual argument parsing": ["sys.argv", "argparse.ArgumentParser"],
    "custom table padding logic": [".ljust(", ".rjust(", ".center("],
    "manual dict schema validation framework": ["required_keys", "validate_dict", "schema_errors"],
}


def prepare_library_first_artifacts(
    *,
    run_dir: Path,
    inputs: dict[str, Any],
    provider_rows: list[dict[str, str]],
) -> dict[str, Any]:
    artifacts_dir = run_dir / "artifacts"
    library_plan = build_library_plan(inputs=inputs, provider_rows=provider_rows)
    file_manifest = build_file_manifest(inputs=inputs, provider_rows=provider_rows, library_plan=library_plan)
    file_tasks = build_file_tasks(file_manifest=file_manifest, library_plan=library_plan)
    library_plan_path = "artifacts/library_plan.json"
    file_manifest_path = "artifacts/file_manifest.json"
    file_task_paths: list[str] = []
    _write_json(run_dir / library_plan_path, library_plan)
    _write_json(run_dir / file_manifest_path, file_manifest)
    for task in file_tasks:
        safe_name = str(task["path"]).replace("\\", "/").replace("/", "__")
        rel = f"artifacts/file_tasks/{safe_name}.json"
        _write_json(run_dir / rel, task)
        file_task_paths.append(rel)
    return {
        "library_plan": library_plan,
        "library_plan_path": library_plan_path,
        "file_manifest": file_manifest,
        "file_manifest_path": file_manifest_path,
        "file_tasks": file_tasks,
        "file_task_paths": file_task_paths,
    }


def verify_and_write_library_usage(
    *,
    run_dir: Path,
    file_tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    verification = verify_library_usage(run_dir=run_dir, file_tasks=file_tasks)
    rel = "artifacts/library_usage_verification.json"
    _write_json(run_dir / rel, verification)
    verification["path"] = rel
    return verification


def build_library_plan(*, inputs: dict[str, Any], provider_rows: list[dict[str, str]]) -> dict[str, Any]:
    src = inputs.get("src") if isinstance(inputs.get("src"), dict) else {}
    declared = src.get("library_plan") if isinstance(src.get("library_plan"), dict) else src.get("project_library_plan")
    if isinstance(declared, dict):
        plan = dict(declared)
        plan.setdefault("schema_version", "ctcp-library-plan-v1")
        plan.setdefault("policy", "library_first")
        plan.setdefault("selected_libraries", [])
        plan.setdefault("feature_library_map", [])
        plan.setdefault("custom_code_allowed", ["thin glue code", "project-specific defaults"])
        plan.setdefault("custom_code_forbidden", _custom_code_forbidden(plan))
        return plan
    imported = _imported_top_level_libraries(provider_rows)
    selected = [
        {
            "name": name,
            "purpose": KNOWN_LIBRARY_PURPOSES[name],
            "why": "detected in provider-authored source and verified as library-first glue",
            "risk": "low",
        }
        for name in sorted(imported & set(KNOWN_LIBRARY_PURPOSES))
    ]
    feature_map = []
    for row in selected:
        name = row["name"]
        feature_map.append(
            {
                "feature": row["purpose"],
                "primary_library": name,
                "fallback_library": "standard library",
                "custom_implementation_allowed": False,
            }
        )
    return {
        "schema_version": "ctcp-library-plan-v1",
        "policy": "library_first",
        "selected_libraries": selected,
        "feature_library_map": feature_map,
        "custom_code_allowed": ["domain naming", "thin service functions", "CLI/UI wiring", "project defaults"],
        "custom_code_forbidden": _custom_code_forbidden({"selected_libraries": selected}),
    }


def build_file_manifest(
    *,
    inputs: dict[str, Any],
    provider_rows: list[dict[str, str]],
    library_plan: dict[str, Any],
) -> dict[str, Any]:
    provider_paths = {str(row.get("path", "")).replace("\\", "/") for row in provider_rows}
    paths: list[str] = []
    seen: set[str] = set()
    lists = inputs.get("lists") if isinstance(inputs.get("lists"), dict) else {}
    for key in ("source_files", "target_files", "business_files"):
        value = lists.get(key)
        rows = value if isinstance(value, list) else []
        for item in rows:
            rel = str(item or "").strip().replace("\\", "/")
            if rel and rel not in seen:
                seen.add(rel)
                paths.append(rel)
    for row in provider_rows:
        rel = str(row.get("path", "")).strip().replace("\\", "/")
        if rel and rel not in seen:
            seen.add(rel)
            paths.append(rel)
    files = []
    selected_names = _selected_library_names(library_plan)
    for path in paths:
        if path in provider_paths:
            content = next((row["content"] for row in provider_rows if row.get("path") == path), "")
            primary_libraries = sorted(_imports_from_content(content) & selected_names)
            generation_mode = "provider_file"
            file_type = "library_glue_file" if primary_libraries else "project_source_file"
        elif path.endswith("/__init__.py"):
            primary_libraries = []
            generation_mode = "local_template"
            file_type = "deterministic_file"
        else:
            primary_libraries = []
            generation_mode = "expected_provider_file"
            file_type = "missing_provider_source_file"
        files.append(
            {
                "path": path,
                "file_type": file_type,
                "generation_mode": generation_mode,
                "primary_libraries": primary_libraries,
                "depends_on": [],
            }
        )
    return {"schema_version": "ctcp-file-manifest-v1", "files": files}


def build_file_tasks(*, file_manifest: dict[str, Any], library_plan: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for row in file_manifest.get("files", []):
        if not isinstance(row, dict) or str(row.get("generation_mode")) != "provider_file":
            continue
        primary = [str(item) for item in row.get("primary_libraries", []) if str(item)]
        must_use = [item for name in primary for item in MUST_USE_BY_LIBRARY.get(name, [])]
        must_not_use = [item for name in primary for item in FORBIDDEN_BY_LIBRARY.get(name, [])]
        tasks.append(
            {
                "schema_version": "ctcp-file-task-v1",
                "path": str(row["path"]),
                "implementation_mode": "library_glue" if primary else "project_specific_source",
                "primary_libraries": primary,
                "must_use": must_use,
                "must_not_use": must_not_use,
                "custom_logic_budget": {"max_functions": 12, "max_lines": 240},
                "required_behavior": [],
                "acceptance": [],
                "output_contract": {"format": "json", "required_keys": ["path", "content"]},
            }
        )
    return tasks


def verify_library_usage(*, run_dir: Path, file_tasks: list[dict[str, Any]]) -> dict[str, Any]:
    file_results: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    for task in file_tasks:
        result = verify_library_usage_for_file(run_dir=run_dir, file_task=task)
        file_results.append(result)
        checks.extend(result["checks"])
    return {
        "schema_version": "ctcp-library-usage-verification-v1",
        "passed": all(bool(result.get("passed", False)) for result in file_results) if file_results else True,
        "checks": checks,
        "file_results": file_results,
    }


def verify_library_usage_for_file(*, run_dir: Path, file_task: dict[str, Any]) -> dict[str, Any]:
    path = str(file_task.get("path", "")).strip().replace("\\", "/")
    target = (run_dir / path).resolve()
    checks: list[dict[str, Any]] = []
    content = ""
    if target.exists() and target.is_file():
        content = target.read_text(encoding="utf-8", errors="replace")
        checks.append({"check_id": "file_exists", "path": path, "passed": True})
    else:
        checks.append({"check_id": "file_exists", "path": path, "passed": False, "reason": "file missing"})
        return {"path": path, "passed": False, "checks": checks}
    checks.append(_check_python_syntax(path=path, content=content))
    checks.append(_check_required_imports(path=path, content=content, file_task=file_task))
    checks.append(_check_forbidden_patterns(path=path, content=content, file_task=file_task))
    checks.append(_check_no_placeholder(path=path, content=content))
    checks.extend(_check_runtime_commands(run_dir=run_dir, path=path, file_task=file_task))
    return {"path": path, "passed": all(bool(check.get("passed", False)) for check in checks), "checks": checks}


def _check_python_syntax(*, path: str, content: str) -> dict[str, Any]:
    if not path.endswith(".py"):
        return {"check_id": "python_syntax", "path": path, "passed": True, "status": "skipped"}
    try:
        ast.parse(content)
    except SyntaxError as exc:
        return {"check_id": "python_syntax", "path": path, "passed": False, "reason": str(exc)}
    return {"check_id": "python_syntax", "path": path, "passed": True}


def _check_required_imports(*, path: str, content: str, file_task: dict[str, Any]) -> dict[str, Any]:
    required = {str(item).split(".", 1)[0] for item in file_task.get("primary_libraries", []) if str(item)}
    required.update(str(item).split(".", 1)[0] for item in file_task.get("must_use", []) if str(item))
    required = {item for item in required if item}
    if not required or not path.endswith(".py"):
        return {"check_id": "required_imports", "path": path, "passed": True, "status": "skipped"}
    imported = _imports_from_content(content)
    missing = sorted(required - imported)
    return {
        "check_id": "required_imports",
        "path": path,
        "passed": not missing,
        "required": sorted(required),
        "imported": sorted(imported),
        "missing": missing,
    }


def _check_forbidden_patterns(*, path: str, content: str, file_task: dict[str, Any]) -> dict[str, Any]:
    matches: list[dict[str, str]] = []
    for label in file_task.get("must_not_use", []):
        label_text = str(label)
        patterns = FORBIDDEN_PATTERN_MAP.get(label_text, [label_text])
        for pattern in patterns:
            if pattern and pattern in content:
                matches.append({"rule": label_text, "pattern": pattern})
    return {"check_id": "forbidden_patterns", "path": path, "passed": not matches, "matches": matches}


def _check_no_placeholder(*, path: str, content: str) -> dict[str, Any]:
    hits: list[str] = []
    lowered = content.lower()
    for token in ("todo", "placeholder", "notimplementederror"):
        if token in lowered:
            hits.append(token)
    try:
        tree = ast.parse(content) if path.endswith(".py") else None
    except SyntaxError:
        tree = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Pass):
                hits.append(f"pass:{node.lineno}")
    return {"check_id": "no_placeholder", "path": path, "passed": not hits, "hits": hits}


def _check_runtime_commands(*, run_dir: Path, path: str, file_task: dict[str, Any]) -> list[dict[str, Any]]:
    commands = file_task.get("required_runtime_checks")
    if not isinstance(commands, list) or not commands:
        return [{"check_id": "runtime_commands", "path": path, "passed": True, "status": "skipped"}]
    out: list[dict[str, Any]] = []
    for index, command in enumerate(commands, start=1):
        if not isinstance(command, list) or not all(isinstance(item, str) for item in command):
            out.append({"check_id": "runtime_command", "path": path, "passed": False, "reason": "runtime command must be a list of strings", "index": index})
            continue
        proc = subprocess.run(command, cwd=run_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        out.append(
            {
                "check_id": "runtime_command",
                "path": path,
                "passed": proc.returncode == 0,
                "index": index,
                "command": command,
                "rc": proc.returncode,
                "stdout_tail": proc.stdout[-1000:],
                "stderr_tail": proc.stderr[-1000:],
            }
        )
    return out


def _imported_top_level_libraries(provider_rows: list[dict[str, str]]) -> set[str]:
    imported: set[str] = set()
    for row in provider_rows:
        if str(row.get("path", "")).endswith(".py"):
            imported.update(_imports_from_content(str(row.get("content", ""))))
    return imported


def _imports_from_content(content: str) -> set[str]:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root:
                    imported.add(root)
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".", 1)[0]
            if root:
                imported.add(root)
    return imported


def _selected_library_names(library_plan: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for row in library_plan.get("selected_libraries", []):
        if isinstance(row, dict) and str(row.get("name", "")).strip():
            out.add(str(row["name"]).strip())
    return out


def _custom_code_forbidden(plan: dict[str, Any]) -> list[str]:
    selected = _selected_library_names(plan)
    out: list[str] = []
    for name in selected:
        out.extend(FORBIDDEN_BY_LIBRARY.get(name, []))
    return sorted(set(out))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


__all__ = [
    "build_file_manifest",
    "build_file_tasks",
    "build_library_plan",
    "prepare_library_first_artifacts",
    "verify_and_write_library_usage",
    "verify_library_usage",
    "verify_library_usage_for_file",
]
