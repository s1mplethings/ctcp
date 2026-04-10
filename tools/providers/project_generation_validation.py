from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from contracts.schemas.project_intent import ProjectIntent


def read_frontend_request(run_dir: Path | None) -> dict[str, Any]:
    if run_dir is None:
        return {}
    path = run_dir / "artifacts" / "frontend_request.json"
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def resolve_project_intent(goal: str, *, run_dir: Path | None, src: dict[str, Any]) -> dict[str, Any]:
    direct = src.get("project_intent")
    if isinstance(direct, dict):
        return ProjectIntent.from_payload(direct, user_goal=goal).to_payload()
    request = read_frontend_request(run_dir)
    from_request = request.get("project_intent")
    if isinstance(from_request, dict):
        return ProjectIntent.from_payload(from_request, user_goal=goal).to_payload()
    constraints = src.get("constraints") if isinstance(src.get("constraints"), dict) else request.get("constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    return ProjectIntent.minimal_from_goal(goal, constraints).to_payload()


def resolve_project_spec(goal: str, *, run_dir: Path | None, src: dict[str, Any], project_intent: dict[str, Any]) -> dict[str, Any]:
    direct = src.get("project_spec")
    if isinstance(direct, dict) and direct:
        return dict(direct)
    request = read_frontend_request(run_dir)
    from_request = request.get("project_spec")
    if isinstance(from_request, dict) and from_request:
        return dict(from_request)
    intent = ProjectIntent.from_payload(project_intent, user_goal=goal)
    constraints = src.get("constraints") if isinstance(src.get("constraints"), dict) else request.get("constraints", {})
    if not isinstance(constraints, dict):
        constraints = {}
    return {
        "schema_version": "ctcp-project-spec-v1",
        "goal_summary": intent.goal_summary,
        "target_user": intent.target_user,
        "problem_to_solve": intent.problem_to_solve,
        "mvp_scope": list(intent.mvp_scope),
        "required_inputs": list(intent.required_inputs),
        "required_outputs": list(intent.required_outputs),
        "hard_constraints": list(intent.hard_constraints),
        "assumptions": list(intent.assumptions),
        "open_questions": list(intent.open_questions),
        "acceptance_criteria": list(intent.acceptance_criteria),
        "constraint_snapshot": dict(constraints),
    }


def pipeline_contract(*, project_root: str, startup_entrypoint: str, startup_readme: str, business_files: list[str], acceptance_files: list[str]) -> dict[str, Any]:
    core_feature_files = sorted(set(business_files))
    return {
        "schema_version": "ctcp-project-generation-pipeline-v1",
        "stages": [
            {"name": "project_intent", "artifact": "project_intent", "status": "ready"},
            {"name": "spec", "artifact": "project_spec", "status": "ready"},
            {"name": "scaffold", "artifact": "project_root", "status": "planned", "project_root": project_root},
            {"name": "core_feature_implementation", "artifact": "core_feature_files", "status": "planned", "core_feature_files": core_feature_files},
            {"name": "smoke_run", "artifact": "startup_entrypoint", "status": "planned", "startup_entrypoint": startup_entrypoint},
            {"name": "delivery_package", "artifact": "acceptance_files", "status": "planned", "acceptance_files": list(acceptance_files), "startup_readme": startup_readme},
        ],
    }


def _looks_placeholder_content(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").lower()
    except Exception:
        return False
    compact = text.strip()
    if len(compact) <= 240 and any(marker in compact for marker in ("todo", "placeholder", "coming soon", "stub", "not implemented")):
        return True
    lines = [line.strip() for line in compact.splitlines() if line.strip()]
    return len(lines) <= 4 and any(line == "pass" for line in lines)


def _python_syntax_validation(*, run_dir: Path, generated_business_files: list[str], startup_entrypoint: str) -> dict[str, Any]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw in [startup_entrypoint] + list(generated_business_files):
        rel = str(raw or "").strip().replace("\\", "/")
        if not rel or rel in seen or not rel.endswith(".py"):
            continue
        seen.add(rel)
        candidates.append(rel)
    checked: list[str] = []
    syntax_errors: list[dict[str, Any]] = []
    for rel in candidates:
        path = (run_dir / rel).resolve()
        if not path.exists():
            continue
        checked.append(rel)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            ast.parse(source, filename=rel)
        except SyntaxError as exc:
            syntax_errors.append(
                {
                    "path": rel,
                    "message": str(exc.msg or "syntax error"),
                    "line": int(exc.lineno or 0),
                    "offset": int(exc.offset or 0),
                }
            )
    return {
        "checked_files": checked,
        "syntax_errors": syntax_errors,
        "passed": not syntax_errors,
    }


def generic_validation(
    *,
    run_dir: Path,
    startup_entrypoint: str,
    startup_readme: str,
    generated_business_files: list[str],
    behavior_probe: dict[str, Any],
    export_probe: dict[str, Any],
    acceptance_files: list[str],
) -> dict[str, Any]:
    entry = (run_dir / startup_entrypoint).resolve()
    readme = (run_dir / startup_readme).resolve()
    readme_text = readme.read_text(encoding="utf-8", errors="replace") if readme.exists() else ""
    entry_name = Path(startup_entrypoint).name.lower()
    placeholder_hits: list[str] = []
    for rel in generated_business_files:
        candidate = (run_dir / rel).resolve()
        if candidate.exists() and _looks_placeholder_content(candidate):
            placeholder_hits.append(rel)
    readme_lower = readme_text.lower()
    readme_has_start_signal = (
        "python" in readme_lower
        or "启动" in readme_text
        or "run " in readme_lower
        or entry_name in readme_lower
        or "quick start" in readme_lower
        or "usage" in readme_lower
    )
    readme_has_start = bool(readme.exists()) and (readme_has_start_signal or bool(readme_text.strip()))
    smoke_passed = int(dict(behavior_probe).get("rc", 1)) == 0 and int(dict(export_probe).get("rc", 1)) == 0
    python_syntax = _python_syntax_validation(
        run_dir=run_dir,
        generated_business_files=generated_business_files,
        startup_entrypoint=startup_entrypoint,
    )
    return {
        "passed": bool(entry.exists())
        and bool(readme.exists())
        and readme_has_start
        and bool(generated_business_files)
        and smoke_passed
        and not placeholder_hits
        and bool(python_syntax.get("passed", False)),
        "has_runnable_entrypoint": bool(entry.exists()),
        "readme_startup_ready": readme_has_start,
        "core_user_flow": [
            "start the generated project from README",
            "execute one smoke export or equivalent core path",
        ],
        "core_feature_files": list(generated_business_files),
        "placeholder_hits": placeholder_hits,
        "python_syntax": python_syntax,
        "delivery_package": list(acceptance_files),
        "smoke_run": {
            "startup_probe": dict(behavior_probe),
            "export_probe": dict(export_probe),
            "passed": smoke_passed,
        },
    }


def _normalized_paths(rows: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in rows:
        value = str(raw or "").strip().replace("\\", "/")
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _matching_suffix(rows: list[str], suffix: str) -> str:
    return next((row for row in rows if row.endswith(suffix)), "")


def _validate_required_suffixes(rows: list[str], suffixes: list[str], *, run_dir: Path) -> tuple[list[str], list[str]]:
    checks: list[str] = []
    missing: list[str] = []
    for suffix in suffixes:
        matched = _matching_suffix(rows, suffix)
        if not matched:
            missing.append(suffix)
            continue
        if not (run_dir / matched).resolve().exists():
            missing.append(matched)
            continue
        checks.append(f"generated {suffix}")
    return checks, missing


def _readme_has_tokens(*, run_dir: Path, startup_readme: str, tokens: tuple[str, ...]) -> bool:
    readme_path = (run_dir / startup_readme).resolve()
    if not readme_path.exists():
        return False
    text = readme_path.read_text(encoding="utf-8", errors="replace").lower()
    return any(token.lower() in text for token in tokens)


def domain_validation(
    *,
    project_type: str,
    project_archetype: str,
    business_generated: list[str],
    business_missing: list[str],
    startup_entrypoint: str,
    startup_readme: str,
    run_dir: Path,
) -> dict[str, Any]:
    rows = _normalized_paths(business_generated)
    if project_type != "narrative_copilot":
        if project_archetype == "cli_toolkit":
            checks, missing = _validate_required_suffixes(
                rows,
                ["/commands.py", "/exporter.py", "/service.py"],
                run_dir=run_dir,
            )
            if startup_entrypoint:
                entry = (run_dir / startup_entrypoint).resolve()
                if entry.exists():
                    checks.append("cli startup entrypoint present")
                else:
                    missing.append(startup_entrypoint)
            if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("python", "cli", "command", "命令")):
                checks.append("readme explains CLI startup")
            else:
                missing.append("README CLI startup guidance")
            test_file = next((row for row in rows if row.endswith("_service.py") and "/tests/" in row), "")
            if test_file:
                checks.append("service regression test generated")
            else:
                missing.append("tests/test_*_service.py")
            return {
                "kind": "cli_toolkit",
                "passed": not missing and not business_missing,
                "checks": checks or ["cli toolkit files generated"],
                "missing": sorted(set(list(business_missing) + missing)),
            }

        if project_archetype == "web_service":
            checks, missing = _validate_required_suffixes(
                rows,
                ["/service_contract.py", "/app.py", "/exporter.py", "/service.py"],
                run_dir=run_dir,
            )
            if startup_entrypoint:
                entry = (run_dir / startup_entrypoint).resolve()
                if entry.exists():
                    checks.append("web service startup entrypoint present")
                else:
                    missing.append(startup_entrypoint)
            if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("--serve", "http", "web", "service", "接口")):
                checks.append("readme explains web service usage")
            else:
                missing.append("README web/service startup guidance")
            return {
                "kind": "web_service",
                "passed": not missing and not business_missing,
                "checks": checks or ["web service files generated"],
                "missing": sorted(set(list(business_missing) + missing)),
            }

        if project_archetype == "data_pipeline":
            checks, missing = _validate_required_suffixes(
                rows,
                ["/transforms.py", "/pipeline.py", "/exporter.py", "/service.py"],
                run_dir=run_dir,
            )
            if _readme_has_tokens(run_dir=run_dir, startup_readme=startup_readme, tokens=("pipeline", "sample output", "数据", "导出")):
                checks.append("readme explains pipeline output path")
            else:
                missing.append("README pipeline output guidance")
            return {
                "kind": "data_pipeline",
                "passed": not missing and not business_missing,
                "checks": checks or ["data pipeline files generated"],
                "missing": sorted(set(list(business_missing) + missing)),
            }

        return {
            "kind": "generic",
            "passed": True,
            "checks": ["no domain-specific checks required"],
        }
    return {
        "kind": "narrative_copilot",
        "passed": bool(business_generated) and not business_missing,
        "checks": [
            "story outline generated",
            "cast schema generated",
            "prompt/export pipeline generated",
        ],
        "missing": list(business_missing),
    }
