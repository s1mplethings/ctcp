from __future__ import annotations

import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.project_generation_gate import evaluate_project_generation_gate
from tools.providers.project_generation_artifacts import (
    normalize_deliverable_index,
    normalize_docs_generation,
    normalize_output_contract_freeze,
    normalize_project_manifest,
    normalize_source_generation,
    normalize_workflow_generation,
)

GOAL = "生成一个本地 HTTP 服务 MVP：接收模糊项目目标，返回结构化 spec、workflow plan、acceptance 摘要 JSON，并提供 health 检查。"
RUN_DIR = ROOT / "artifacts" / "backend_interface_non_narrative" / "manual_web_service_run"
REPORT_PATH = ROOT / "artifacts" / "backend_interface_non_narrative" / "non_narrative_backend_interface_e2e_report.json"


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def _run(cmd: list[str], *, cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "command": " ".join(cmd),
        "rc": int(proc.returncode),
        "stdout_tail": "\n".join(str(proc.stdout or "").splitlines()[-20:]),
        "stderr_tail": "\n".join(str(proc.stderr or "").splitlines()[-20:]),
    }


def _prepare_run_dir() -> None:
    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    (RUN_DIR / "artifacts").mkdir(parents=True, exist_ok=True)


def _prepare_inputs() -> None:
    _write_json(
        RUN_DIR / "artifacts" / "frontend_request.json",
        {
            "schema_version": "ctcp-frontend-request-v1",
            "goal": GOAL,
            "constraints": {"delivery_shape": "web_first"},
            "project_intent": {
                "goal_summary": "生成一个本地 HTTP 服务 MVP",
                "target_user": "内部项目发起人",
                "problem_to_solve": "把模糊项目目标转成结构化 spec/workflow/acceptance JSON 响应",
                "mvp_scope": ["提供 health 路径", "提供 generate 路径", "导出 spec、workflow、acceptance 结果"],
                "required_inputs": ["用户目标"],
                "required_outputs": ["service contract", "sample response", "acceptance report"],
                "hard_constraints": ["delivery_shape=web_first"],
                "assumptions": ["先做本地可运行的 JSON 服务 MVP"],
                "open_questions": [],
                "acceptance_criteria": ["health 路径可用", "generate 路径返回结构化 JSON", "README 可指导启动"],
            },
            "attachments": [],
        },
    )
    _write_json(
        RUN_DIR / "artifacts" / "context_pack.json",
        {
            "schema_version": "ctcp-context-pack-v1",
            "goal": GOAL,
            "repo_slug": "ctcp",
            "summary": "non-narrative web service project generation acceptance",
            "files": [
                {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "project manifest readable api"},
                {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "source_generation deliver"},
                {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "web_service validation"},
                {"path": "scripts/project_manifest_bridge.py", "why": "bridge", "content": "manifest fields"},
                {"path": "artifacts/frontend_uploads/brief.txt", "why": "input", "content": "local HTTP service, health route, generate route, acceptance json"},
            ],
            "omitted": [],
        },
    )


def run_non_narrative_project_e2e() -> dict[str, Any]:
    _prepare_run_dir()
    _prepare_inputs()

    output_contract = normalize_output_contract_freeze(None, goal=GOAL, run_dir=RUN_DIR)
    _write_json(RUN_DIR / "artifacts" / "output_contract_freeze.json", output_contract)

    project_root = RUN_DIR / str(output_contract.get("project_root", "project_output/project-copilot"))
    _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

    source_stage = normalize_source_generation(None, goal=GOAL, run_dir=RUN_DIR)
    _write_json(RUN_DIR / "artifacts" / "source_generation_report.json", source_stage)

    docs_stage = normalize_docs_generation(None, goal=GOAL, run_dir=RUN_DIR)
    _write_json(RUN_DIR / "artifacts" / "docs_generation_report.json", docs_stage)

    workflow_stage = normalize_workflow_generation(None, goal=GOAL, run_dir=RUN_DIR)
    _write_json(RUN_DIR / "artifacts" / "workflow_generation_report.json", workflow_stage)

    manifest = normalize_project_manifest(None, goal=GOAL, run_dir=RUN_DIR)
    _write_json(RUN_DIR / "artifacts" / "project_manifest.json", manifest)

    deliverable_index = normalize_deliverable_index(None, goal=GOAL, run_dir=RUN_DIR)
    _write_json(RUN_DIR / "artifacts" / "deliverable_index.json", deliverable_index)

    gate_report = evaluate_project_generation_gate(RUN_DIR / "artifacts")

    package_name = str(output_contract.get("package_name", "")).strip()
    startup_entrypoint = RUN_DIR / str(manifest.get("startup_entrypoint", "")).strip()
    project_dir = RUN_DIR / str(manifest.get("project_root", "")).strip()
    export_dir = RUN_DIR / "manual_export"
    if export_dir.exists():
        shutil.rmtree(export_dir)

    smoke_export = _run(
        [sys.executable, str(startup_entrypoint), "--goal", "manual acceptance smoke", "--project-name", "Manual Acceptance", "--out", str(export_dir)],
        cwd=startup_entrypoint.parent,
    )
    health_probe = _run([sys.executable, str(startup_entrypoint), "--serve"], cwd=startup_entrypoint.parent)

    if str(project_dir / "src") not in sys.path:
        sys.path.insert(0, str(project_dir / "src"))
    app = importlib.import_module(f"{package_name}.app")
    app_health = app.health_payload()
    app_generate = app.generate_payload("manual acceptance goal", "Manual Acceptance")

    exported_files = sorted(str(path.relative_to(export_dir)).replace("\\", "/") for path in export_dir.rglob("*") if path.is_file())
    generated_response = _load_json(export_dir / "deliverables" / "sample_response.json")
    service_contract = _load_json(export_dir / "deliverables" / "service_contract.json")
    acceptance_report = _load_json(export_dir / "deliverables" / "acceptance_report.json")

    generated_test = _run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(project_dir / "tests"), "-p", f"test_{package_name}_service.py", "-v"],
        cwd=project_dir,
    )

    checks = {
        "project_archetype_is_web_service": str(manifest.get("project_archetype", "")).strip() == "web_service",
        "source_stage_passed": str(source_stage.get("status", "")).strip() == "pass",
        "docs_stage_passed": str(docs_stage.get("status", "")).strip() == "pass",
        "workflow_stage_passed": str(workflow_stage.get("status", "")).strip() == "pass",
        "manifest_has_no_missing_files": not bool(list(manifest.get("missing_files", []))),
        "generic_validation_passed": bool(dict(manifest.get("generic_validation", {})).get("passed", False)),
        "domain_validation_passed": bool(dict(manifest.get("domain_validation", {})).get("passed", False)),
        "gate_ready_verify": str(gate_report.get("state", "")).strip() == "ready_verify",
        "startup_smoke_passed": int(smoke_export.get("rc", 1)) == 0,
        "health_probe_passed": int(health_probe.get("rc", 1)) == 0,
        "generated_web_modules_exist": all(
            (RUN_DIR / rel).exists()
            for rel in (
                f"{manifest.get('project_root', '')}/src/{package_name}/service_contract.py",
                f"{manifest.get('project_root', '')}/src/{package_name}/app.py",
                f"{manifest.get('project_root', '')}/src/{package_name}/exporter.py",
                f"{manifest.get('project_root', '')}/src/{package_name}/service.py",
            )
        ),
        "deliverables_exist": all(
            (export_dir / rel).exists()
            for rel in (
                "deliverables/mvp_spec.json",
                "deliverables/service_contract.json",
                "deliverables/sample_response.json",
                "deliverables/acceptance_report.json",
                "deliverables/delivery_summary.md",
            )
        ),
        "sample_response_has_contract": isinstance(generated_response.get("contract"), list) and bool(generated_response.get("contract")),
        "service_contract_has_routes": isinstance(service_contract.get("routes"), list) and len(service_contract.get("routes", [])) >= 2,
        "app_health_ok": dict(app_health).get("status") == "ok",
        "app_generate_payload_has_acceptance": isinstance(app_generate.get("acceptance"), list) and bool(app_generate.get("acceptance")),
        "generated_service_test_passed": int(generated_test.get("rc", 1)) == 0,
        "acceptance_report_passed": str(acceptance_report.get("status", "")).strip() == "pass",
    }

    return {
        "goal": GOAL,
        "run_dir": str(RUN_DIR),
        "project_root": str(manifest.get("project_root", "")),
        "project_archetype": str(manifest.get("project_archetype", "")),
        "output_contract_freeze": output_contract,
        "source_generation_report": source_stage,
        "docs_generation_report": docs_stage,
        "workflow_generation_report": workflow_stage,
        "project_manifest": manifest,
        "deliverable_index": deliverable_index,
        "gate_report": gate_report,
        "smoke_export": smoke_export,
        "health_probe": health_probe,
        "app_health": app_health,
        "app_generate": app_generate,
        "generated_test": generated_test,
        "exported_files": exported_files,
        "checks": checks,
    }


def _assert_pass(checks: dict[str, Any]) -> None:
    failures = [name for name, passed in checks.items() if not bool(passed)]
    if failures:
        raise SystemExit("manual non-narrative acceptance failed: " + ", ".join(failures))


if __name__ == "__main__":
    result = run_non_narrative_project_e2e()
    _write_json(REPORT_PATH, result)
    _assert_pass(dict(result.get("checks", {})))
    print(json.dumps({"report_path": str(REPORT_PATH), "project_archetype": result.get("project_archetype", "")}, ensure_ascii=False))
