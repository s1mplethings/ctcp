#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from tools.providers.project_generation_artifacts import (
    build_default_context_request,
    is_project_generation_goal,
    normalize_deliverable_index,
    normalize_docs_generation,
    normalize_output_contract_freeze,
    normalize_project_manifest,
    normalize_source_generation,
    normalize_workflow_generation,
)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    _write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _normalize_role(role: str) -> str:
    text = str(role or "").strip().lower()
    if text == "planner":
        return "chair"
    return text


def _parse_ranges(raw: Any) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    if not isinstance(raw, list):
        return rows
    for item in raw:
        if not isinstance(item, list) or len(item) != 2:
            continue
        try:
            a = int(item[0])
            b = int(item[1])
        except Exception:
            continue
        if a <= 0 or b <= 0:
            continue
        if a > b:
            a, b = b, a
        rows.append((a, b))
    return rows


def _render_snippets(text: str, ranges: list[tuple[int, int]]) -> str:
    if not ranges:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    for start, end in ranges:
        s = max(1, start)
        e = min(len(lines), end)
        if s > e:
            continue
        out.append(f"# lines {s}-{e}")
        for idx in range(s, e + 1):
            out.append(f"{idx:>6}: {lines[idx - 1]}")
    return "\n".join(out).strip()


def _mock_file_request(goal: str) -> dict[str, Any]:
    if is_project_generation_goal(goal):
        request = build_default_context_request(goal)
        return {
            "schema_version": "ctcp-file-request-v1",
            "goal": goal or "mock-goal",
            "needs": list(request.get("needs", [])),
            "budget": dict(request.get("budget", {})),
            "reason": str(request.get("reason", "")).strip() or "mock project-generation context request",
        }
    return {
        "schema_version": "ctcp-file-request-v1",
        "goal": goal or "mock-goal",
        "needs": [
            {
                "path": "README.md",
                "mode": "snippets",
                "line_ranges": [[1, 24]],
            }
        ],
        "budget": {"max_files": 3, "max_total_bytes": 12000},
        "reason": "mock chair request for deterministic offline flow",
    }


def _mock_context_pack(repo_root: Path, run_dir: Path) -> tuple[dict[str, Any] | None, str]:
    request_path = run_dir / "artifacts" / "file_request.json"
    if not request_path.exists():
        return None, "missing artifacts/file_request.json"
    try:
        request = json.loads(request_path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:
        return None, f"invalid file_request.json: {exc}"

    if str(request.get("schema_version", "")) != "ctcp-file-request-v1":
        return None, "file_request schema_version must be ctcp-file-request-v1"
    needs = request.get("needs", [])
    if not isinstance(needs, list):
        return None, "file_request.needs must be array"

    budget = request.get("budget", {})
    if not isinstance(budget, dict):
        budget = {}
    try:
        max_files = max(1, int(budget.get("max_files", 3)))
    except Exception:
        max_files = 3
    try:
        max_total_bytes = max(1, int(budget.get("max_total_bytes", 12000)))
    except Exception:
        max_total_bytes = 12000

    files: list[dict[str, str]] = []
    omitted: list[dict[str, str]] = []
    used_bytes = 0
    for row in needs:
        if not isinstance(row, dict):
            continue
        rel = str(row.get("path", "")).strip().replace("\\", "/")
        mode = str(row.get("mode", "")).strip().lower()
        if not rel:
            continue
        src = (repo_root / rel).resolve()
        if not _is_within(src, repo_root):
            omitted.append({"path": rel, "reason": "denied"})
            continue
        if not src.exists() or not src.is_file():
            omitted.append({"path": rel, "reason": "denied"})
            continue
        raw = src.read_text(encoding="utf-8", errors="replace")
        if mode == "full":
            content = raw
        elif mode == "snippets":
            content = _render_snippets(raw, _parse_ranges(row.get("line_ranges", [])))
            if not content:
                omitted.append({"path": rel, "reason": "irrelevant"})
                continue
        else:
            omitted.append({"path": rel, "reason": "irrelevant"})
            continue

        size = len(content.encode("utf-8"))
        if len(files) >= max_files or (used_bytes + size) > max_total_bytes:
            omitted.append({"path": rel, "reason": "too_large"})
            continue
        files.append(
            {
                "path": rel,
                "why": f"mock librarian capture mode={mode}",
                "content": content,
            }
        )
        used_bytes += size

    return (
        {
            "schema_version": "ctcp-context-pack-v1",
            "goal": str(request.get("goal", "")).strip(),
            "repo_slug": repo_root.name,
            "summary": (
                f"included={len(files)} omitted={len(omitted)} "
                f"used_bytes={used_bytes} budget_files={max_files} budget_bytes={max_total_bytes}"
            ),
            "files": files,
            "omitted": omitted,
        },
        "",
    )


def _mock_readme_content(*, package_name: str, goal: str) -> str:
    project_title = package_name.replace("_", " ").title()
    return "\n".join(
        [
            f"# {project_title}",
            "",
            "## Project Overview",
            "A compact local web service generated by the mock provider pipeline.",
            "",
            "## Implemented",
            "- Standard-library HTTP service surface.",
            "- `/` and `/status` response helpers.",
            "- Deterministic sample export.",
            "",
            "## Not Implemented",
            "- Production hosting.",
            "- Authentication.",
            "",
            "## How To Run",
            "Run `python scripts/run_project_web.py --serve` to smoke the web service.",
            f"Run `python scripts/run_project_web.py --goal \"{goal}\" --project-name mock_service --out sample_data` to export sample data.",
            "",
            "## Sample Data",
            "The exporter writes `sample_response.json` with status, project name, routes, and goal.",
            "",
            "## Directory Map",
            "- `src/`: service, app, models, and exporter modules.",
            "- `scripts/`: startup and smoke entrypoint.",
            "- `tests/`: generated unittest coverage.",
            "",
            "## Limitations",
            "This is a local MVP for pipeline validation.",
            "",
        ]
    )


def _mock_entrypoint_content(package_name: str) -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "import argparse",
            "import json",
            "import sys",
            "from pathlib import Path",
            "",
            "PROJECT_ROOT = Path(__file__).resolve().parents[1]",
            "SRC_ROOT = PROJECT_ROOT / 'src'",
            "if str(SRC_ROOT) not in sys.path:",
            "    sys.path.insert(0, str(SRC_ROOT))",
            "",
            f"from {package_name}.app import render_index, render_status",
            f"from {package_name}.exporter import export_sample",
            "",
            "",
            "def main(argv=None) -> int:",
            "    parser = argparse.ArgumentParser(description='Run the local mock web service.')",
            "    parser.add_argument('--serve', action='store_true')",
            "    parser.add_argument('--goal', default='mock service smoke')",
            "    parser.add_argument('--project-name', default='mock_service')",
            "    parser.add_argument('--out', default='sample_data')",
            "    parser.add_argument('--headless', action='store_true')",
            "    args = parser.parse_args(argv)",
            "    if args.serve:",
            "        print(json.dumps({'status': 'ok', 'routes': ['/', '/status'], 'index': render_index(), 'status_payload': render_status()}, ensure_ascii=False))",
            "        return 0",
            "    result = export_sample(goal=args.goal, project_name=args.project_name, out_dir=Path(args.out))",
            "    print(json.dumps(result, ensure_ascii=False, indent=2))",
            "    return 0",
            "",
            "",
            "if __name__ == '__main__':",
            "    raise SystemExit(main())",
            "",
        ]
    )


def _mock_model_content() -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from dataclasses import asdict, dataclass",
            "",
            "",
            "@dataclass",
            "class ServiceRequest:",
            "    goal: str",
            "    project_name: str",
            "",
            "",
            "@dataclass",
            "class ServiceResponse:",
            "    status: str",
            "    project_name: str",
            "    goal: str",
            "    routes: list[str]",
            "",
            "    def to_dict(self) -> dict[str, object]:",
            "        return asdict(self)",
            "",
        ]
    )


def _mock_service_content() -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "from .models import ServiceRequest, ServiceResponse",
            "from .service_contract import SERVICE_ROUTES, SERVICE_STATUS",
            "",
            "",
            "def generate_response(goal: str = 'mock service smoke', project_name: str = 'mock_service') -> dict[str, object]:",
            "    request = ServiceRequest(goal=goal, project_name=project_name)",
            "    response = ServiceResponse(status=SERVICE_STATUS, project_name=request.project_name, goal=request.goal, routes=list(SERVICE_ROUTES))",
            "    return response.to_dict()",
            "",
        ]
    )


def _mock_app_content() -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "import json",
            "",
            "from .service import generate_response",
            "",
            "",
            "def render_status() -> dict[str, object]:",
            "    return generate_response(goal='status probe', project_name='mock_service')",
            "",
            "",
            "def render_index() -> str:",
            "    payload = render_status()",
            "    return '<html><body><h1>Mock Service</h1><pre>' + json.dumps(payload, ensure_ascii=False) + '</pre></body></html>'",
            "",
        ]
    )


def _mock_exporter_content() -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "import json",
            "from pathlib import Path",
            "",
            "from .service import generate_response",
            "",
            "",
            "def export_sample(goal: str, project_name: str, out_dir: Path) -> dict[str, object]:",
            "    out_dir.mkdir(parents=True, exist_ok=True)",
            "    payload = generate_response(goal=goal, project_name=project_name)",
            "    target = out_dir / 'sample_response.json'",
            "    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\\n', encoding='utf-8')",
            "    html = out_dir / 'index.html'",
            "    html.write_text('<html><body><h1>Mock Service Export</h1><p>/status ready</p></body></html>\\n', encoding='utf-8')",
            "    return {'passed': True, 'files': [str(target), str(html)], 'status': payload['status'], 'routes': payload['routes']}",
            "",
        ]
    )


def _mock_test_content(package_name: str) -> str:
    return "\n".join(
        [
            "from __future__ import annotations",
            "",
            "import unittest",
            "",
            f"from {package_name}.service import generate_response",
            "",
            "",
            "class GeneratedServiceTests(unittest.TestCase):",
            "    def test_generate_response_has_status_route(self) -> None:",
            "        payload = generate_response(goal='unit test', project_name='mock_service')",
            "        self.assertEqual(payload['status'], 'ok')",
            "        self.assertIn('/status', payload['routes'])",
            "",
            "",
            "if __name__ == '__main__':",
            "    unittest.main()",
            "",
        ]
    )


def _path_content_for_mock_source(*, rel: str, project_root: str, package_name: str, goal: str) -> str:
    rel = rel.replace("\\", "/")
    static_rows = {
        "/docs/00_CORE.md": "# Core\n\nRuntime truth: local mock web service with status and export probes.\n",
        "/docs/web_workflow.md": "# Web Workflow\n\nStart with `--serve`, then run the export command for sample output.\n",
        "/meta/reports/LAST.md": "# Report\n\nMock provider source bundle generated for pipeline smoke.\n",
        "/meta/tasks/CURRENT.md": "# Task\n\nRun the generated local web service smoke.\n",
        "/scripts/verify_repo.ps1": "python scripts/run_project_web.py --serve\n",
        "/__init__.py": "from .service import generate_response\n\n__all__ = ['generate_response']\n",
        "/seed.py": "DEFAULT_GOAL = 'mock service smoke'\nDEFAULT_PROJECT_NAME = 'mock_service'\n",
        "/spec_builder.py": "def build_spec() -> dict[str, object]:\n    return {'routes': ['/', '/status'], 'transport': 'stdlib-http'}\n",
        "/service_contract.py": "SERVICE_ROUTES = ['/', '/status']\nSERVICE_STATUS = 'ok'\n",
    }
    if rel.endswith("/README.md"):
        return _mock_readme_content(package_name=package_name, goal=goal)
    if rel.endswith("/meta/manifest.json"):
        return json.dumps(
            {"schema_version": "ctcp-generated-project-manifest-v1", "project_root": project_root, "package_name": package_name, "routes": ["/", "/status"]},
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    if rel.endswith("/pyproject.toml"):
        return "\n".join(["[project]", f'name = "{package_name.replace("_", "-")}"', 'version = "0.1.0"', 'description = "Mock provider authored CTCP web service"', 'requires-python = ">=3.10"', ""])
    if rel.endswith("/scripts/run_project_web.py"):
        return _mock_entrypoint_content(package_name)
    if rel.endswith("/models.py"):
        return _mock_model_content()
    if rel.endswith("/service.py"):
        return _mock_service_content()
    if rel.endswith("/app.py"):
        return _mock_app_content()
    if rel.endswith("/exporter.py"):
        return _mock_exporter_content()
    if "/tests/test_" in rel and rel.endswith(".py"):
        return _mock_test_content(package_name)
    for suffix, content in static_rows.items():
        if rel.endswith(suffix):
            return content
    return f"# Generated mock provider file for {rel}\n"


def _mock_source_generation_payload(goal: str, run_dir: Path) -> dict[str, Any]:
    contract = normalize_output_contract_freeze({}, goal=goal, run_dir=run_dir)
    project_root = str(contract.get("project_root", "")).strip().replace("\\", "/")
    package_name = str(contract.get("package_name", "mock_project")).strip() or "mock_project"
    files: list[dict[str, str]] = []
    candidate_paths: list[str] = []
    for key in ("target_files", "source_files", "doc_files", "workflow_files", "acceptance_files"):
        value = contract.get(key)
        if isinstance(value, list):
            candidate_paths.extend(str(item).strip().replace("\\", "/") for item in value if str(item).strip())
    seen: set[str] = set()
    for rel in candidate_paths:
        if not project_root or not rel.startswith(project_root + "/") or rel in seen:
            continue
        seen.add(rel)
        files.append(
            {
                "path": rel,
                "content": _path_content_for_mock_source(rel=rel, project_root=project_root, package_name=package_name, goal=goal),
            }
        )
    return {
        "schema_version": "ctcp-provider-source-files-v1",
        "files": files,
        "source_map": {"api_content_applied": True, "api_content_source_ref": "API:mock_agent/source_generation"},
    }


def _mock_guardrails() -> str:
    return "\n".join(
        [
            "find_mode: resolver_only",
            "max_files: 20",
            "max_total_bytes: 200000",
            "max_iterations: 3",
            "",
        ]
    )


def _mock_analysis(goal: str) -> str:
    return "\n".join(
        [
            "# Analysis",
            "",
            f"- Goal: {goal or 'mock-goal'}",
            "- Strategy: deterministic offline pipeline run",
            "",
        ]
    )


def _mock_plan_draft(goal: str) -> str:
    project_generation_lines: list[str] = []
    if is_project_generation_goal(goal):
        project_generation_lines = [
            "Project-Generation: true",
            "Deliverables: runnable_app,README,startup_steps,verify_report,final_screenshot,final_package",
            "Verification: artifacts/verify_report.json must prove the generated project starts and passes acceptance checks",
            "Delivery: README with startup steps, final screenshot, and final project package are required before completion",
        ]
    return "\n".join(
        [
            "Status: DRAFT",
            "Scope-Allow: scripts/,tools/,tests/,artifacts/,meta/",
            "Scope-Deny: .git/,build/,build_lite/,dist/,runs/",
            "Gates: lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,lite_replay,python_unit_tests",
            "Budgets: max_iterations=3,max_files=20,max_total_bytes=200000",
            "Stop: scope_violation=true,repeated_failure=2,missing_plan_fields=true",
            "Behaviors: B001,B002,B003,B004,B005,B006,B007,B008,B009,B010,B011,B012,B013,B014,B015,B016,B017,B018,B019,B020,B021,B022,B023,B024,B025,B026,B027,B028,B029,B030,B031,B032,B033,B034,B035",
            "Results: R001,R002,R003,R004,R005",
            f"Goal: {goal or 'mock-goal'}",
            *project_generation_lines,
            "",
        ]
    )


def _mock_plan_signed(goal: str) -> str:
    project_generation_lines: list[str] = []
    if is_project_generation_goal(goal):
        project_generation_lines = [
            "Project-Generation: true",
            "Deliverables: runnable_app,README,startup_steps,verify_report,final_screenshot,final_package",
            "Verification: artifacts/verify_report.json must prove the generated project starts and passes acceptance checks",
            "Delivery: README with startup steps, final screenshot, and final project package are required before completion",
        ]
    return "\n".join(
        [
            "Status: SIGNED",
            "Scope-Allow: scripts/,tools/,tests/,artifacts/,meta/",
            "Scope-Deny: .git/,build/,build_lite/,dist/,runs/",
            "Gates: lite,workflow_gate,plan_check,patch_check,behavior_catalog_check,contract_checks,doc_index_check,lite_replay,python_unit_tests",
            "Budgets: max_iterations=3,max_files=20,max_total_bytes=200000",
            "Stop: scope_violation=true,repeated_failure=2,missing_plan_fields=true",
            "Behaviors: B001,B002,B003,B004,B005,B006,B007,B008,B009,B010,B011,B012,B013,B014,B015,B016,B017,B018,B019,B020,B021,B022,B023,B024,B025,B026,B027,B028,B029,B030,B031,B032,B033,B034,B035",
            "Results: R001,R002,R003,R004,R005",
            f"Goal: {goal or 'mock-goal'}",
            *project_generation_lines,
            "",
        ]
    )


def _mock_review(title: str) -> str:
    return "\n".join(
        [
            f"# {title}",
            "",
            "Verdict: APPROVE",
            "",
            "Blocking Reasons:",
            "- none",
            "",
            "Required Fix/Artifacts:",
            "- none",
            "",
        ]
    )


def _mock_find_web() -> dict[str, Any]:
    return {
        "schema_version": "ctcp-find-web-v1",
        "constraints": {
            "allow_domains": ["example.com"],
            "max_queries": 1,
            "max_pages": 1,
        },
        "results": [
            {
                "url": "https://example.com/mock",
                "locator": {"type": "heading", "value": "Mock Source"},
                "fetched_at": "2026-01-01T00:00:00Z",
                "excerpt": "mock source",
                "why_relevant": "offline deterministic placeholder",
                "risk_flags": [],
            }
        ],
    }


def _mock_patch(run_dir: Path) -> str:
    run_token = re.sub(r"[^A-Za-z0-9_.-]+", "-", run_dir.name).strip("-")
    if not run_token:
        run_token = "run"
    rel = f"docs/mock_agent_probe_{run_token}.txt"
    return "\n".join(
        [
            f"diff --git a/{rel} b/{rel}",
            "new file mode 100644",
            "index 0000000..88f4248",
            "--- /dev/null",
            f"+++ b/{rel}",
            "@@ -0,0 +1 @@",
            f"+mock agent deterministic patch {run_token}",
            "",
        ]
    )


def _default_target(role: str, action: str) -> str:
    if role == "chair" and action == "file_request":
        return "artifacts/file_request.json"
    if role == "chair" and action == "plan_signed":
        return "artifacts/PLAN.md"
    if role == "chair":
        return "artifacts/PLAN_draft.md"
    if role == "librarian":
        return "artifacts/context_pack.json"
    if role == "contract_guardian":
        return "reviews/review_contract.md"
    if role == "cost_controller":
        return "reviews/review_cost.md"
    if role in {"patchmaker", "fixer"}:
        return "artifacts/diff.patch"
    if role == "researcher":
        return "artifacts/find_web.json"
    return "artifacts/mock_output.txt"


def _fault_config(config: dict[str, Any]) -> tuple[str, str]:
    providers = config.get("providers", {}) if isinstance(config, dict) else {}
    if not isinstance(providers, dict):
        providers = {}
    mock_cfg = providers.get("mock_agent", {})
    if not isinstance(mock_cfg, dict):
        mock_cfg = {}

    mode = str(mock_cfg.get("fault_mode", "")).strip().lower()
    role = str(mock_cfg.get("fault_role", "")).strip().lower()
    env_mode = str(os.environ.get("CTCP_MOCK_AGENT_FAULT_MODE", "")).strip().lower()
    env_role = str(os.environ.get("CTCP_MOCK_AGENT_FAULT_ROLE", "")).strip().lower()
    if env_mode:
        mode = env_mode
    if env_role:
        role = env_role
    return mode, role


def _fault_applies(*, mode: str, role_selector: str, role: str, action: str, target_rel: str) -> bool:
    if not mode:
        return False
    if not role_selector:
        return True
    tokens = {
        role.lower(),
        action.lower(),
        f"{role.lower()}_{action.lower()}",
        target_rel.lower(),
        Path(target_rel).name.lower(),
    }
    selectors = {x.strip() for x in role_selector.replace("|", ",").split(",") if x.strip()}
    return any(x in tokens for x in selectors)


def _degraded_payload(payload_type: str, role: str, action: str, goal: str) -> tuple[str, dict[str, Any] | str]:
    if payload_type == "json":
        if role == "chair" and action == "file_request":
            return "json", {"schema_version": "ctcp-file-request-v1", "goal": goal or "mock-goal"}
        if role == "librarian":
            return "json", {"schema_version": "ctcp-context-pack-v1", "goal": goal or "mock-goal"}
        return "json", {"schema_version": "mock-v1"}
    if payload_type == "text":
        if role in {"contract_guardian", "cost_controller"}:
            return "text", "# Review\n\nRequired Fix/Artifacts:\n- missing verdict\n"
        if role == "chair" and action == "plan_signed":
            return "text", "Status: DRAFT\n"
        if role == "chair":
            return "text", "# Draft\n"
        if role in {"patchmaker", "fixer"}:
            return "text", "diff --git\n"
    return payload_type, ""


def preview(*, run_dir: Path, request: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    _ = (run_dir, request, config)
    return {"status": "can_exec"}


def execute(
    *,
    repo_root: Path,
    run_dir: Path,
    request: dict[str, Any],
    config: dict[str, Any],
    guardrails_budgets: dict[str, str],
) -> dict[str, Any]:
    _ = guardrails_budgets
    role = _normalize_role(str(request.get("role", "")))
    action = str(request.get("action", "")).strip().lower()
    goal = str(request.get("goal", "")).strip()
    target_rel = str(request.get("target_path", "")).strip() or _default_target(role, action)
    target = (run_dir / target_rel).resolve()
    if not _is_within(target, run_dir):
        return {"status": "exec_failed", "reason": f"target_path escapes run_dir: {target_rel}"}

    try:
        payload_type = "text"
        payload: dict[str, Any] | str

        if role == "chair" and action == "file_request":
            payload_type = "json"
            payload = _mock_file_request(goal)
        elif role == "chair" and action == "plan_signed":
            payload = _mock_plan_signed(goal)
        elif role == "chair" and action == "plan_draft":
            lower = target_rel.lower()
            if lower.endswith("guardrails.md"):
                payload = _mock_guardrails()
            elif lower.endswith("analysis.md"):
                payload = _mock_analysis(goal)
            else:
                payload = _mock_plan_draft(goal)
        elif role == "chair" and action == "output_contract_freeze":
            payload_type = "json"
            payload = normalize_output_contract_freeze({}, goal=goal, run_dir=run_dir)
        elif role == "chair" and action == "source_generation":
            payload_type = "json"
            payload = normalize_source_generation(_mock_source_generation_payload(goal, run_dir), goal=goal, run_dir=run_dir)
        elif role == "chair" and action == "docs_generation":
            payload_type = "json"
            payload = normalize_docs_generation({}, goal=goal, run_dir=run_dir)
        elif role == "chair" and action == "workflow_generation":
            payload_type = "json"
            payload = normalize_workflow_generation({}, goal=goal, run_dir=run_dir)
        elif role == "chair" and action == "artifact_manifest_build":
            payload_type = "json"
            payload = normalize_project_manifest({}, goal=goal, run_dir=run_dir)
        elif role == "chair" and action == "deliver":
            payload_type = "json"
            payload = normalize_deliverable_index({}, goal=goal, run_dir=run_dir)
        elif role == "librarian" and action == "context_pack":
            payload_type = "json"
            doc, reason = _mock_context_pack(repo_root, run_dir)
            if doc is None:
                return {"status": "exec_failed", "reason": reason, "target_path": target_rel}
            payload = doc
        elif role == "contract_guardian" and action == "review_contract":
            payload = _mock_review("Contract Review")
        elif role == "cost_controller" and action == "review_cost":
            payload = _mock_review("Cost Review")
        elif role in {"patchmaker", "fixer"} and action in {"make_patch", "fix_patch"}:
            payload = _mock_patch(run_dir)
        elif role == "researcher" and action == "find_web":
            payload_type = "json"
            payload = _mock_find_web()
        else:
            return {"status": "exec_failed", "reason": f"unsupported mock request: role={role} action={action}"}

        fault_mode, fault_role = _fault_config(config)
        if _fault_applies(
            mode=fault_mode,
            role_selector=fault_role,
            role=role,
            action=action,
            target_rel=target_rel,
        ):
            if fault_mode == "raise_exception":
                raise RuntimeError(f"mock fault injected: mode={fault_mode}")
            if fault_mode == "drop_output":
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                    "note": "output intentionally dropped",
                }
            if fault_mode == "corrupt_json":
                _write_text(target, '{"broken_json":')
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                }
            if fault_mode == "missing_field":
                payload_type, payload = _degraded_payload(payload_type, role, action, goal)
            elif fault_mode == "empty_file":
                _write_text(target, "")
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                }
            elif fault_mode == "invalid_patch":
                _write_text(target, "mock-invalid-patch\n")
                return {
                    "status": "executed",
                    "target_path": target_rel,
                    "fault_mode": fault_mode,
                    "fault_role": fault_role,
                }

        if payload_type == "json":
            if not isinstance(payload, dict):
                return {"status": "exec_failed", "reason": "mock payload type mismatch for json", "target_path": target_rel}
            _write_json(target, payload)
        else:
            if not isinstance(payload, str):
                return {"status": "exec_failed", "reason": "mock payload type mismatch for text", "target_path": target_rel}
            text = payload if payload.endswith("\n") else payload + "\n"
            _write_text(target, text)

        return {
            "status": "executed",
            "target_path": target_rel,
        }
    except Exception as exc:
        return {
            "status": "exec_failed",
            "reason": f"mock_agent exception: {exc}",
            "target_path": target_rel,
        }
