from __future__ import annotations

import importlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BENCH = Path(__file__).resolve().parent
FIXTURES = BENCH / "fixtures"
GENERATED = BENCH / "generated"
SEMANTIC_FIXTURES = BENCH / "semantic_fixtures"
SEMANTIC_GENERATED = BENCH / "semantic_generated"
HOLDOUT_FIXTURES = BENCH / "holdout_fixtures"
HOLDOUT_GENERATED = BENCH / "holdout_generated"
E2E_PIPELINE = BENCH / "e2e_pipeline"
REPORT = BENCH / "benchmark_report.md"

sys.path.insert(0, str(ROOT))

VALIDATORS = [
    importlib.import_module("tests.agent_factory_benchmark.validators.schema_validator"),
    importlib.import_module("tests.agent_factory_benchmark.validators.permission_validator"),
    importlib.import_module("tests.agent_factory_benchmark.validators.workflow_validator"),
    importlib.import_module("tests.agent_factory_benchmark.validators.tool_validator"),
]

SEMANTIC_VALIDATORS = [
    importlib.import_module("tests.agent_factory_benchmark.semantic_validators.relevance_validator"),
    importlib.import_module("tests.agent_factory_benchmark.semantic_validators.overgeneration_validator"),
    importlib.import_module("tests.agent_factory_benchmark.semantic_validators.permission_bypass_validator"),
    importlib.import_module("tests.agent_factory_benchmark.semantic_validators.ambiguity_validator"),
    importlib.import_module("tests.agent_factory_benchmark.semantic_validators.conflict_resolution_validator"),
]

HOLDOUT_VALIDATORS = [
    importlib.import_module("tests.agent_factory_benchmark.holdout_validators.domain_precision_validator"),
    importlib.import_module("tests.agent_factory_benchmark.holdout_validators.regulated_domain_safety_validator"),
    importlib.import_module("tests.agent_factory_benchmark.holdout_validators.minimality_validator"),
    importlib.import_module("tests.agent_factory_benchmark.holdout_validators.action_risk_validator"),
    importlib.import_module("tests.agent_factory_benchmark.holdout_validators.similarity_validator"),
]


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-1200:],
        "stderr_tail": proc.stderr[-1200:],
    }


def _read_text(path: Path, limit: int = 6000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    return text[:limit]


def _capability_text(paths: list[Path]) -> str:
    parts: list[str] = []
    for path in paths:
        if path.is_dir():
            for child in sorted(path.glob("*.json")):
                parts.append(_read_text(child, limit=20000))
        elif path.exists():
            parts.append(_read_text(path, limit=20000))
    return "\n".join(parts).lower().replace("-", "_").replace(" ", "_")


def discover_project() -> dict[str, Any]:
    deps = [name for name in ("package.json", "pyproject.toml", "Cargo.toml", "go.mod", "requirements.txt", "requirements-dev.txt", "CMakeLists.txt") if (ROOT / name).exists()]
    schema_files = sorted(str(path.relative_to(ROOT)).replace("\\", "/") for path in (ROOT / "contracts").glob("*") if path.is_file())
    entrypoints = [
        "scripts/ctcp_orchestrate.py new-run/status/advance",
        "scripts/resolve_workflow.py --goal --out",
        "tools.providers.project_generation_artifacts.normalize_output_contract_freeze",
        "tools.providers.project_generation_artifacts.normalize_source_generation",
        "tools.providers.project_generation_artifacts.normalize_workflow_generation",
        "tools.providers.project_generation_artifacts.normalize_project_manifest",
    ]
    test_commands = [
        ".venv\\Scripts\\python.exe -m unittest discover -s tests -p \"test_*.py\"",
        "powershell -ExecutionPolicy Bypass -File scripts\\verify_repo.ps1",
    ]
    return {
        "project_type": "Python CTCP goal-to-MVP project generator with CMake headless support",
        "runtime": "Python 3; optional CMake headless build; no package.json/pyproject project script file at repo root",
        "directory_sample": sorted(p.name for p in ROOT.iterdir())[:60],
        "dependency_files": deps,
        "readme_usage_summary": "README names scripts/ctcp_orchestrate.py as runtime orchestrator and scripts/verify_repo.ps1 or scripts/verify_repo.sh as acceptance entrypoints.",
        "entrypoints_found": entrypoints,
        "test_commands_found": test_commands,
        "existing_schema_files": schema_files,
        "previous_entrypoint": "scripts/resolve_workflow.py",
        "new_entrypoint": "scripts/generate_agent_manifest.py",
        "entrypoint_change_reason": "resolve_workflow outputs CTCP project workflow docs, not agent manifest",
        "agent_manifest_generation_entrypoint": "scripts/generate_agent_manifest.py --input <fixture.json> --output <output.json>",
        "can_run_project": True,
        "blocking_issues": [],
    }


def invoke_project(fixture: dict[str, Any], fixture_path: Path) -> dict[str, Any]:
    case_id = str(fixture["case_id"])
    output_path = GENERATED / f"output_{case_id}.json"
    manifest_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_agent_manifest.py"),
        "--input",
        str(fixture_path),
        "--output",
        str(output_path),
    ]
    command = _run(manifest_cmd)
    if output_path.exists():
        output = _json(output_path)
    else:
        output = {
            "manifest_version": "1.0",
            "system_name": "generation failed",
            "agents": [],
            "tools": [],
            "workflows": [],
            "memory": [],
            "permissions": {},
            "guardrails": [],
            "test_cases": [],
        }
    output["benchmark_metadata"] = {
        "schema_version": "external-agent-factory-benchmark-output-v2",
        "case_id": case_id,
        "fixture_path": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
        "generated_by": "scripts/generate_agent_manifest.py",
        "previous_entrypoint": "scripts/resolve_workflow.py",
        "new_entrypoint": "scripts/generate_agent_manifest.py",
        "reason": "resolve_workflow outputs CTCP project workflow docs, not agent manifest",
        "commands": [command],
        "runtime_status": "ran" if command["exit_code"] == 0 else "failed",
        "agent_manifest_generation_supported": command["exit_code"] == 0,
    }
    _write_json(output_path, output)
    return output


def validate_case(output: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    assertions: list[dict[str, str]] = []
    for module in VALIDATORS:
        assertions.extend(module.validate(output, fixture))
    failed = [row for row in assertions if row.get("status") == "fail"]
    unsupported = [row for row in assertions if row.get("status") == "unsupported"]
    if unsupported and not bool(output.get("agent_manifest_generation_supported", False)):
        status = "unsupported"
    elif failed:
        status = "fail"
    else:
        status = "pass"
    return {
        "status": status,
        "passed_assertions": [row for row in assertions if row.get("status") == "pass"],
        "failed_assertions": failed,
        "unsupported_features": unsupported,
        "assertions": assertions,
    }


def invoke_semantic_fixture(fixture: dict[str, Any], fixture_path: Path) -> dict[str, Any]:
    case_id = str(fixture["case_id"])
    output_path = SEMANTIC_GENERATED / f"output_{case_id}.json"
    manifest_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_agent_manifest.py"),
        "--input",
        str(fixture_path),
        "--output",
        str(output_path),
    ]
    command = _run(manifest_cmd)
    if output_path.exists():
        output = _json(output_path)
    else:
        output = {
            "manifest_version": "1.0",
            "system_name": "semantic generation failed",
            "agents": [],
            "tools": [],
            "workflows": [],
            "memory": [],
            "permissions": {},
            "guardrails": [],
            "test_cases": [],
        }
    output["benchmark_metadata"] = {
        "schema_version": "external-agent-factory-semantic-output-v1",
        "phase": "phase2_semantic",
        "case_id": case_id,
        "fixture_path": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
        "generated_by": "scripts/generate_agent_manifest.py",
        "commands": [command],
        "runtime_status": "ran" if command["exit_code"] == 0 else "failed",
        "agent_manifest_generation_supported": command["exit_code"] == 0,
    }
    _write_json(output_path, output)
    return output


def validate_semantic_case(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    assertions: list[dict[str, str]] = []
    for module in SEMANTIC_VALIDATORS:
        assertions.extend(module.validate(output, fixture, context))
    failed = [row for row in assertions if row.get("status") == "fail"]
    warnings = [row for row in assertions if row.get("status") == "warning"]
    unsupported = [row for row in assertions if row.get("status") == "unsupported"]
    status = "fail" if failed else "pass"
    return {
        "status": status,
        "passed_assertions": [row for row in assertions if row.get("status") == "pass"],
        "failed_assertions": failed,
        "warnings": warnings,
        "unsupported_features": unsupported,
        "assertions": assertions,
    }


def invoke_holdout_fixture(fixture: dict[str, Any], fixture_path: Path) -> dict[str, Any]:
    case_id = str(fixture["case_id"])
    output_path = HOLDOUT_GENERATED / f"output_{case_id}.json"
    manifest_cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_agent_manifest.py"),
        "--input",
        str(fixture_path),
        "--output",
        str(output_path),
    ]
    command = _run(manifest_cmd)
    if output_path.exists():
        output = _json(output_path)
    else:
        output = {
            "manifest_version": "1.0",
            "system_name": "holdout generation failed",
            "agents": [],
            "tools": [],
            "workflows": [],
            "memory": [],
            "permissions": {},
            "guardrails": [],
            "test_cases": [],
        }
    output["benchmark_metadata"] = {
        "schema_version": "external-agent-factory-holdout-output-v1",
        "phase": "phase2_5_holdout",
        "case_id": case_id,
        "fixture_path": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
        "generated_by": "scripts/generate_agent_manifest.py",
        "generator_frozen": True,
        "commands": [command],
        "runtime_status": "ran" if command["exit_code"] == 0 else "failed",
        "agent_manifest_generation_supported": command["exit_code"] == 0,
    }
    _write_json(output_path, output)
    return output


def validate_holdout_case(output: dict[str, Any], fixture: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    assertions: list[dict[str, str]] = []
    for module in HOLDOUT_VALIDATORS:
        assertions.extend(module.validate(output, fixture, context))
    failed = [row for row in assertions if row.get("status") == "fail"]
    warnings = [row for row in assertions if row.get("status") == "warning"]
    unsupported = [row for row in assertions if row.get("status") == "unsupported"]
    if failed:
        status = "fail"
    elif warnings:
        status = "warning"
    else:
        status = "pass"
    return {
        "status": status,
        "passed_assertions": [row for row in assertions if row.get("status") == "pass"],
        "failed_assertions": failed,
        "warnings": warnings,
        "unsupported_features": unsupported,
        "assertions": assertions,
    }


def run_phase1() -> list[dict[str, Any]]:
    GENERATED.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for fixture_path in sorted(FIXTURES.glob("input_*.json")):
        fixture = _json(fixture_path)
        output = invoke_project(fixture, fixture_path)
        validation = validate_case(output, fixture)
        case_id = str(fixture["case_id"])
        results.append(
            {
                "case_id": case_id,
                "status": validation["status"],
                "fixture_path": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
                "generated_output_path": str((GENERATED / f"output_{case_id}.json").relative_to(ROOT)).replace("\\", "/"),
                "validation": validation,
            }
        )
    return results


def run_phase2() -> list[dict[str, Any]]:
    SEMANTIC_GENERATED.mkdir(parents=True, exist_ok=True)
    fixtures: dict[str, tuple[Path, dict[str, Any]]] = {}
    outputs: dict[str, dict[str, Any]] = {}
    for fixture_path in sorted(SEMANTIC_FIXTURES.glob("input_*.json")):
        fixture = _json(fixture_path)
        case_id = str(fixture["case_id"])
        fixtures[case_id] = (fixture_path, fixture)
        outputs[case_id] = invoke_semantic_fixture(fixture, fixture_path)

    context = {"semantic_outputs": outputs}
    results: list[dict[str, Any]] = []
    for case_id in sorted(fixtures):
        fixture_path, fixture = fixtures[case_id]
        validation = validate_semantic_case(outputs[case_id], fixture, context)
        results.append(
            {
                "case_id": case_id,
                "status": validation["status"],
                "fixture_path": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
                "generated_output_path": str((SEMANTIC_GENERATED / f"output_{case_id}.json").relative_to(ROOT)).replace("\\", "/"),
                "validation": validation,
            }
        )
    return results


def run_holdout() -> list[dict[str, Any]]:
    HOLDOUT_GENERATED.mkdir(parents=True, exist_ok=True)
    fixtures: dict[str, tuple[Path, dict[str, Any]]] = {}
    outputs: dict[str, dict[str, Any]] = {}
    for fixture_path in sorted(HOLDOUT_FIXTURES.glob("input_*.json")):
        fixture = _json(fixture_path)
        case_id = str(fixture["case_id"])
        fixtures[case_id] = (fixture_path, fixture)
        outputs[case_id] = invoke_holdout_fixture(fixture, fixture_path)

    context = {"holdout_outputs": outputs}
    results: list[dict[str, Any]] = []
    for case_id in sorted(fixtures):
        fixture_path, fixture = fixtures[case_id]
        validation = validate_holdout_case(outputs[case_id], fixture, context)
        results.append(
            {
                "case_id": case_id,
                "status": validation["status"],
                "fixture_path": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
                "generated_output_path": str((HOLDOUT_GENERATED / f"output_{case_id}.json").relative_to(ROOT)).replace("\\", "/"),
                "validation": validation,
            }
        )
    return results


def _phase4_cases() -> list[dict[str, Any]]:
    return [
        {
            "case": "devops_incident",
            "input_path": FIXTURES / "input_devops_incident.json",
            "forbidden": [],
            "required_approvals": ["rollback"],
        },
        {
            "case": "permission_attack",
            "input_path": FIXTURES / "input_permission_attack.json",
            "forbidden": [],
            "required_approvals": ["rollback", "refund"],
        },
        {
            "case": "holdout_h1_personal_productivity",
            "input_path": HOLDOUT_FIXTURES / "input_h1_personal_productivity.json",
            "forbidden": ["rollback", "refund", "deployment", "github_issue", "incident_response"],
            "required_terms": ["task_intake", "daily_summary"],
            "required_approvals": [],
        },
        {
            "case": "holdout_h2_patient_intake",
            "input_path": HOLDOUT_FIXTURES / "input_h2_patient_intake.json",
            "forbidden": ["diagnosis_tool", "prescription_tool"],
            "required_terms": ["no_diagnosis", "no_prescription", "clinical_summary_draft", "clinician_escalation"],
            "required_approvals": [],
            "capability_paths": ["tools", "workflows", "guardrails"],
        },
        {
            "case": "holdout_h9_battery_charging",
            "input_path": HOLDOUT_FIXTURES / "input_h9_battery_charging_station.json",
            "forbidden": ["billing", "refund", "payment"],
            "required_terms": ["device_status", "maintenance_ticket"],
            "required_approvals": [],
        },
        {
            "case": "holdout_h10_product_launch",
            "input_path": HOLDOUT_FIXTURES / "input_h10_product_launch_coordination.json",
            "forbidden": ["rollback", "incident_response"],
            "required_terms": ["launch_coordination", "prd_extraction"],
            "required_approvals": ["launch publish"],
        },
    ]


def run_phase4_e2e_pipeline() -> list[dict[str, Any]]:
    E2E_PIPELINE.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for spec in _phase4_cases():
        case = str(spec["case"])
        case_output_dir = Path(tempfile.mkdtemp(prefix=f"ctcp_phase4_{case}_")) / "agent_project"
        input_path = Path(spec["input_path"])
        pipeline_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "ctcp_orchestrate.py"),
            "agent-project",
            "--input",
            str(input_path),
            "--output-dir",
            str(case_output_dir),
        ]
        pipeline_command = _run(pipeline_cmd)
        failed: list[str] = []
        if pipeline_command["exit_code"] != 0:
            failed.append("agent-project command failed")
        manifest_path = case_output_dir / "manifest.json"
        scaffold_dir = case_output_dir / "scaffold"
        report_path = case_output_dir / "pipeline_report.json"
        manifest_generated = manifest_path.exists()
        scaffold_generated = scaffold_dir.exists()
        pipeline_report_generated = report_path.exists()
        scaffold_tests_generated = (scaffold_dir / "tests").exists()
        dry_run_passed = False
        scaffold_tests_passed = False
        pipeline_report_status = ""
        if not manifest_generated:
            failed.append("manifest.json was not generated")
        if not scaffold_generated:
            failed.append("scaffold was not generated")
        for rel in (
            "scaffold/run_agent.py",
            "scaffold/tests/test_manifest_contract.py",
            "scaffold/tests/test_permissions.py",
            "scaffold/tests/test_workflows.py",
            "scaffold/tests/test_dry_run.py",
            "scaffold/tests/test_runtime.py",
            "scaffold/runtime/runtime_engine.py",
            "scaffold/runtime/runtime_tools.py",
            "scaffold/runtime/runtime_permissions.py",
            "scaffold/runtime/runtime_state.py",
            "scaffold/runtime/runtime_audit.py",
            "pipeline_report.json",
            "pipeline_report.md",
        ):
            if not (case_output_dir / rel).exists():
                failed.append(f"missing pipeline artifact: {rel}")
        if pipeline_report_generated:
            report = _json(report_path)
            pipeline_report_status = str(report.get("status", ""))
            if pipeline_report_status != "passed":
                failed.append(f"pipeline_report status was not passed: {pipeline_report_status}")
            dry_run_passed = any(step.get("name") == "dry_run" and step.get("status") == "passed" for step in report.get("steps", []))
            scaffold_tests_passed = any(step.get("name") == "scaffold_tests" and step.get("status") == "passed" for step in report.get("steps", []))
            if not dry_run_passed:
                failed.append("pipeline dry-run step did not pass")
            if not scaffold_tests_passed:
                failed.append("pipeline scaffold tests step did not pass")
        if manifest_generated and scaffold_generated:
            permissions = _json(scaffold_dir / "permissions" / "permissions.json") if (scaffold_dir / "permissions" / "permissions.json").exists() else {}
            approvals = set(permissions.get("approval_required_for", []))
            for required in spec.get("required_approvals", []):
                if required not in approvals:
                    failed.append(f"missing approval requirement: {required}")
            tools = [_json(path) for path in sorted((scaffold_dir / "tools").glob("*.json"))]
            for tool in tools:
                if tool.get("side_effect_level") == "high" and tool.get("requires_approval") is not True:
                    failed.append(f"high side effect tool lacks approval: {tool.get('tool_name')}")
            capability_paths = [scaffold_dir / path for path in spec.get("capability_paths", ["tools", "workflows"])]
            text = _capability_text(capability_paths)
            for forbidden in spec.get("forbidden", []):
                if forbidden in text:
                    failed.append(f"forbidden scaffold capability appeared: {forbidden}")
            for required in spec.get("required_terms", []):
                if required not in text:
                    failed.append(f"required scaffold capability missing: {required}")
        row = {
            "case": case,
            "input_path": str(input_path.relative_to(ROOT)).replace("\\", "/"),
            "manifest_path": manifest_path.as_posix(),
            "scaffold_output_dir": scaffold_dir.as_posix(),
            "scaffold_generated": scaffold_generated,
            "manifest_generated": manifest_generated,
            "scaffold_tests_generated": scaffold_tests_generated,
            "pipeline_report_generated": pipeline_report_generated,
            "pipeline_report_status": pipeline_report_status,
            "dry_run_passed": dry_run_passed,
            "scaffold_tests_passed": scaffold_tests_passed,
            "permission_checks_passed": not any("approval" in item or "high side effect" in item for item in failed),
            "domain_regression_checks_passed": not any("forbidden scaffold capability" in item or "required scaffold capability" in item for item in failed),
            "failed_assertions": failed,
            "commands": [pipeline_command],
        }
        row["status"] = "pass" if not failed else "fail"
        _write_json(E2E_PIPELINE / case / "result.json", row)
        results.append(row)
    _write_json(E2E_PIPELINE / "e2e_summary.json", {"schema_version": "external-agent-factory-e2e-summary-v1", "results": results})
    return results


def _counts(results: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "pass_count": sum(1 for row in results if row["status"] == "pass"),
        "fail_count": sum(1 for row in results if row["status"] == "fail"),
        "unsupported_count": sum(1 for row in results if row["status"] == "unsupported"),
        "warning_count": max(
            sum(1 for row in results if row["status"] == "warning"),
            sum(len(row.get("validation", {}).get("warnings", [])) for row in results),
        ),
    }


def _report_header(discovery: dict[str, Any], phase1: dict[str, int], phase2: dict[str, int], holdout: dict[str, int]) -> list[str]:
    return [
        "# Agent Factory Benchmark Report",
        "",
        "## Project Discovery",
        f"- project type: {discovery['project_type']}",
        f"- runtime: {discovery['runtime']}",
        f"- entrypoints: {', '.join(discovery['entrypoints_found'])}",
        f"- previous_entrypoint: {discovery['previous_entrypoint']}",
        f"- new_entrypoint: {discovery['new_entrypoint']}",
        f"- reason: {discovery['entrypoint_change_reason']}",
        f"- agent manifest generation entrypoint: {discovery['agent_manifest_generation_entrypoint']}",
        f"- test command: {'; '.join(discovery['test_commands_found'])}",
        f"- runtime status: {'can run' if discovery['can_run_project'] else 'runtime blocked'}",
        f"- dependency files: {', '.join(discovery['dependency_files']) or 'none'}",
        f"- schema files: {', '.join(discovery['existing_schema_files']) or 'none'}",
        "",
        "```json",
        json.dumps(
            {
                "project_type": discovery["project_type"],
                "runtime": discovery["runtime"],
                "entrypoints_found": discovery["entrypoints_found"],
                "previous_entrypoint": discovery["previous_entrypoint"],
                "new_entrypoint": discovery["new_entrypoint"],
                "reason": discovery["entrypoint_change_reason"],
                "agent_manifest_generation_entrypoint": discovery["agent_manifest_generation_entrypoint"],
                "test_commands_found": discovery["test_commands_found"],
                "existing_schema_files": discovery["existing_schema_files"],
                "can_run_project": discovery["can_run_project"],
                "blocking_issues": discovery["blocking_issues"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
        "## Benchmark Summary",
        f"- phase1_pass_count: {phase1['pass_count']}",
        f"- phase1_fail_count: {phase1['fail_count']}",
        f"- phase1_unsupported_count: {phase1['unsupported_count']}",
        f"- phase2_pass_count: {phase2['pass_count']}",
        f"- phase2_fail_count: {phase2['fail_count']}",
        f"- phase2_warning_count: {phase2['warning_count']}",
        f"- phase2_unsupported_count: {phase2['unsupported_count']}",
        f"- holdout_pass_count: {holdout['pass_count']}",
        f"- holdout_fail_count: {holdout['fail_count']}",
        f"- holdout_warning_count: {holdout['warning_count']}",
        f"- holdout_unsupported_count: {holdout['unsupported_count']}",
        "",
        "### Phase 1 Structural Benchmark",
        "",
        "| Case | Status | Key Failures |",
        "|---|---|---|",
    ]


def _append_phase1_results(lines: list[str], phase1_results: list[dict[str, Any]]) -> None:
    for row in phase1_results:
        failures = row["validation"]["failed_assertions"][:3]
        unsupported_items = row["validation"]["unsupported_features"][:3]
        key = "; ".join(item["assertion"] for item in failures or unsupported_items) or "none"
        lines.append(f"| {row['case_id']} | {row['status']} | {key} |")
    lines += ["", "## Detailed Results"]
    for row in phase1_results:
        validation = row["validation"]
        lines += [
            "",
            f"### {row['case_id']}",
            f"- input fixture path: `{row['fixture_path']}`",
            f"- generated output path: `{row['generated_output_path']}`",
            "- validators run: schema_validator, permission_validator, workflow_validator, tool_validator",
            f"- passed assertions: {len(validation['passed_assertions'])}",
            f"- failed assertions: {len(validation['failed_assertions'])}",
            f"- unsupported features: {len(validation['unsupported_features'])}",
        ]
        if validation["failed_assertions"]:
            lines.append("- failed assertions:")
            for item in validation["failed_assertions"][:12]:
                lines.append(f"  - {item['validator']}: {item['assertion']} - {item['message']}")
        if validation["unsupported_features"]:
            lines.append("- unsupported features:")
            for item in validation["unsupported_features"][:12]:
                lines.append(f"  - {item['validator']}: {item['assertion']} - {item['message']}")


def _append_phase2_summary(lines: list[str], phase2_results: list[dict[str, Any]], phase2: dict[str, int]) -> None:
    lines += [
        "",
        "# Phase 2 Semantic Stress Benchmark",
        "",
        f"- phase2_total_cases: {len(phase2_results)}",
        f"- phase2_pass_count: {phase2['pass_count']}",
        f"- phase2_fail_count: {phase2['fail_count']}",
        f"- phase2_warning_count: {phase2['warning_count']}",
        f"- phase2_unsupported_count: {phase2['unsupported_count']}",
        "",
        "| Case | Structural Pass | Security Pass | Semantic Pass | Status | Key Failures | Warnings |",
        "|---|---:|---:|---:|---|---|---|",
    ]
    for row in phase2_results:
        validation = row["validation"]
        failed = validation["failed_assertions"]
        warnings = validation.get("warnings", [])
        failed_validators = {item["validator"] for item in failed}
        structural_pass = "yes"
        security_pass = "no" if "semantic_permission_bypass" in failed_validators else "yes"
        semantic_pass = "no" if failed else "yes"
        key = "; ".join(item["assertion"] for item in failed[:3]) or "none"
        warning_text = "; ".join(item["assertion"] for item in warnings[:3]) or "none"
        lines.append(f"| {row['case_id']} | {structural_pass} | {security_pass} | {semantic_pass} | {row['status']} | {key} | {warning_text} |")


def _append_phase2_details(lines: list[str], phase2_results: list[dict[str, Any]]) -> None:
    lines += ["", "## Phase 2 Detailed Results"]
    for row in phase2_results:
        validation = row["validation"]
        lines += [
            "",
            f"### {row['case_id']}",
            f"- input fixture path: `{row['fixture_path']}`",
            f"- generated output path: `{row['generated_output_path']}`",
            "- validators run: relevance_validator, overgeneration_validator, permission_bypass_validator, ambiguity_validator, conflict_resolution_validator",
            f"- passed assertions: {len(validation['passed_assertions'])}",
            f"- failed assertions: {len(validation['failed_assertions'])}",
            f"- warnings: {len(validation.get('warnings', []))}",
            f"- unsupported features: {len(validation['unsupported_features'])}",
        ]
        if validation["failed_assertions"]:
            lines.append("- semantic failures:")
            for item in validation["failed_assertions"][:12]:
                lines.append(f"  - {item['validator']}: {item['assertion']} - {item['message']}")
        if validation.get("warnings"):
            lines.append("- overgeneration warnings:")
            for item in validation["warnings"][:12]:
                lines.append(f"  - {item['validator']}: {item['assertion']} - {item['message']}")


def _append_holdout_summary(lines: list[str], holdout_results: list[dict[str, Any]], holdout: dict[str, int]) -> None:
    lines += [
        "",
        "# Phase 2.5 Holdout Generalization Audit",
        "",
        f"- holdout_total_cases: {len(holdout_results)}",
        f"- holdout_pass_count: {holdout['pass_count']}",
        f"- holdout_fail_count: {holdout['fail_count']}",
        f"- holdout_warning_count: {holdout['warning_count']}",
        f"- holdout_unsupported_count: {holdout['unsupported_count']}",
        "- generator_frozen: true",
        "",
        "| Case | Status | Failed Assertions | Warnings |",
        "|---|---|---|---|",
    ]
    for row in holdout_results:
        validation = row["validation"]
        failures = "; ".join(item["assertion"] for item in validation["failed_assertions"][:3]) or "none"
        warnings = "; ".join(item["assertion"] for item in validation.get("warnings", [])[:3]) or "none"
        lines.append(f"| {row['case_id']} | {row['status']} | {failures} | {warnings} |")


def _append_holdout_details(lines: list[str], holdout_results: list[dict[str, Any]]) -> None:
    lines += ["", "## Phase 2.5 Detailed Results"]
    for row in holdout_results:
        validation = row["validation"]
        lines += [
            "",
            f"### {row['case_id']}",
            f"- input fixture path: `{row['fixture_path']}`",
            f"- generated output path: `{row['generated_output_path']}`",
            "- validators run: domain_precision_validator, regulated_domain_safety_validator, minimality_validator, action_risk_validator, similarity_validator",
            f"- passed assertions: {len(validation['passed_assertions'])}",
            f"- failed assertions: {len(validation['failed_assertions'])}",
            f"- warnings: {len(validation.get('warnings', []))}",
            f"- unsupported features: {len(validation['unsupported_features'])}",
        ]
        if validation["failed_assertions"]:
            lines.append("- failed assertions:")
            for item in validation["failed_assertions"][:12]:
                lines.append(f"  - {item['validator']}: {item['assertion']} - {item['message']}")
        if validation.get("warnings"):
            lines.append("- overgeneration / similarity warnings:")
            for item in validation["warnings"][:12]:
                lines.append(f"  - {item['validator']}: {item['assertion']} - {item['message']}")


def _append_phase4_e2e_pipeline(lines: list[str], phase4_results: list[dict[str, Any]], phase4: dict[str, int]) -> None:
    lines += [
        "",
        "# Phase 4 End-to-End Agent Project Pipeline",
        "",
        f"- phase4_total_cases: {len(phase4_results)}",
        f"- phase4_pass_count: {phase4['pass_count']}",
        f"- phase4_fail_count: {phase4['fail_count']}",
        f"- phase4_unsupported_count: {phase4['unsupported_count']}",
        "",
        "| Case | Status | Manifest | Scaffold | Dry Run | Scaffold Tests | Permission Checks | Domain Checks | Failed Assertions |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in phase4_results:
        failures = "; ".join(row["failed_assertions"][:4]) or "none"
        lines.append(
            f"| {row['case']} | {row['status']} | {row['manifest_generated']} | {row['scaffold_generated']} | "
            f"{row['dry_run_passed']} | {row['scaffold_tests_passed']} | {row['permission_checks_passed']} | "
            f"{row['domain_regression_checks_passed']} | {failures} |"
        )
    lines += ["", "## Phase 4 Detailed Results"]
    for row in phase4_results:
        lines += [
            "",
            f"### {row['case']}",
            f"- input path: `{row['input_path']}`",
            f"- manifest path: `{row['manifest_path']}`",
            f"- scaffold output dir: `{row['scaffold_output_dir']}`",
            f"- pipeline report generated: {row['pipeline_report_generated']}",
            f"- pipeline report status: {row['pipeline_report_status']}",
            f"- manifest generated: {row['manifest_generated']}",
            f"- scaffold generated: {row['scaffold_generated']}",
            f"- scaffold tests generated: {row['scaffold_tests_generated']}",
            f"- dry-run passed: {row['dry_run_passed']}",
            f"- generated scaffold tests passed: {row['scaffold_tests_passed']}",
            f"- permission checks passed: {row['permission_checks_passed']}",
            f"- domain regression checks passed: {row['domain_regression_checks_passed']}",
            f"- failed assertions: {len(row['failed_assertions'])}",
        ]
        if row["failed_assertions"]:
            for item in row["failed_assertions"]:
                lines.append(f"  - {item}")


def _append_findings(lines: list[str], phase2_results: list[dict[str, Any]], holdout_results: list[dict[str, Any]]) -> None:
    all_failures = [item for row in phase2_results for item in row["validation"]["failed_assertions"]]
    all_warnings = [item for row in phase2_results for item in row["validation"].get("warnings", [])]
    holdout_failures = [item for row in holdout_results for item in row["validation"]["failed_assertions"]]
    holdout_warnings = [item for row in holdout_results for item in row["validation"].get("warnings", [])]
    lines += [
        "",
        "## Critical Bugs",
        "- Phase 1 failures would indicate structural or basic security regressions.",
        "- Phase 2 semantic failures indicate domain mismatch, overgeneration, permission bypass, ambiguity, or conflict-resolution weakness.",
        "- Phase 2.5 holdout failures indicate frozen-generator generalization gaps and are not repaired in this audit.",
        f"- Current semantic failure count: {len(all_failures)}.",
        f"- Current holdout failure count: {len(holdout_failures)}.",
        "",
        "## Design Weaknesses",
        "- The manifest generator remains deterministic and signal-based; phase 2 now checks whether those signals produce domain-specific manifests.",
        "- Holdout results measure blind generalization without generator changes.",
        "- Semantic validators are intentionally explicit and should grow with new benchmark scenarios.",
        "- This entrypoint is separate from CTCP project-generation and should not be treated as full agent runtime execution.",
        "",
        "## Semantic Failures",
    ]
    if all_failures:
        for item in all_failures[:30]:
            lines.append(f"- {item['validator']}: {item['assertion']} - {item['message']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Overgeneration Warnings",
    ]
    if all_warnings:
        for item in all_warnings[:30]:
            lines.append(f"- {item['validator']}: {item['assertion']} - {item['message']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Holdout Domain Confusion And Overgeneration Findings",
    ]
    if holdout_failures or holdout_warnings:
        for item in (holdout_failures + holdout_warnings)[:40]:
            lines.append(f"- {item['validator']}: {item['assertion']} - {item['message']}")
    else:
        lines.append("- none")
    lines += [
        "",
        "## Suggested Fixes",
        "- Recommended generator improvements: add phrase-level negation handling for domain detection.",
        "- Recommended generator improvements: add richer clause/message/risk taxonomies for legal and customer-communication domains.",
        "- Recommended generator improvements from holdout: add regulated-domain packs for medical, finance, recruiting, privacy, education, moderation, marketplace review, and launch coordination.",
        "- Recommended generator improvements: add learned examples only after deterministic benchmark regressions are stable.",
        "",
        "## Reproduction Commands",
    ]


def write_report(discovery: dict[str, Any], phase1_results: list[dict[str, Any]], phase2_results: list[dict[str, Any]], holdout_results: list[dict[str, Any]], phase4_results: list[dict[str, Any]], commands: list[str]) -> None:
    phase1 = _counts(phase1_results)
    phase2 = _counts(phase2_results)
    holdout = _counts(holdout_results)
    phase4 = _counts(phase4_results)
    lines = _report_header(discovery, phase1, phase2, holdout)
    _append_phase1_results(lines, phase1_results)
    _append_phase2_summary(lines, phase2_results, phase2)
    _append_phase2_details(lines, phase2_results)
    _append_holdout_summary(lines, holdout_results, holdout)
    _append_holdout_details(lines, holdout_results)
    _append_phase4_e2e_pipeline(lines, phase4_results, phase4)
    _append_findings(lines, phase2_results, holdout_results)
    for command in commands:
        lines.append(f"- `{command}`")
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    discovery = discover_project()
    phase1_results = run_phase1()
    phase2_results = run_phase2()
    holdout_results = run_holdout()
    phase4_results = run_phase4_e2e_pipeline()
    phase1 = _counts(phase1_results)
    phase2 = _counts(phase2_results)
    holdout = _counts(holdout_results)
    phase4 = _counts(phase4_results)
    summary = {
        "schema_version": "external-agent-factory-benchmark-summary-v3",
        "project_discovery": discovery,
        "phase1": {
            "results": phase1_results,
            **phase1,
        },
        "phase2": {
            "results": phase2_results,
            **phase2,
        },
        "holdout": {
            "results": holdout_results,
            **holdout,
        },
        "phase4_e2e_pipeline": {
            "results": phase4_results,
            **phase4,
        },
        "pass_count": phase1["pass_count"],
        "fail_count": phase1["fail_count"],
        "unsupported_count": phase1["unsupported_count"],
        "phase2_pass_count": phase2["pass_count"],
        "phase2_fail_count": phase2["fail_count"],
        "phase2_warning_count": phase2["warning_count"],
        "phase2_unsupported_count": phase2["unsupported_count"],
        "holdout_pass_count": holdout["pass_count"],
        "holdout_fail_count": holdout["fail_count"],
        "holdout_warning_count": holdout["warning_count"],
        "holdout_unsupported_count": holdout["unsupported_count"],
        "phase4_pass_count": phase4["pass_count"],
        "phase4_fail_count": phase4["fail_count"],
        "phase4_unsupported_count": phase4["unsupported_count"],
    }
    _write_json(GENERATED / "benchmark_summary.json", summary)
    _write_json(SEMANTIC_GENERATED / "semantic_summary.json", {"schema_version": "external-agent-factory-semantic-summary-v1", **summary["phase2"]})
    _write_json(HOLDOUT_GENERATED / "holdout_summary.json", {"schema_version": "external-agent-factory-holdout-summary-v1", **summary["holdout"]})
    _write_json(E2E_PIPELINE / "e2e_summary.json", {"schema_version": "external-agent-factory-e2e-summary-v1", **summary["phase4_e2e_pipeline"]})
    commands = [
        f"{sys.executable} tests\\agent_factory_benchmark\\run_benchmark.py",
        f"{sys.executable} scripts\\generate_agent_manifest.py --input tests\\agent_factory_benchmark\\fixtures\\input_devops_incident.json --output tests\\agent_factory_benchmark\\generated\\output_devops_incident.json",
        f"{sys.executable} scripts\\ctcp_orchestrate.py agent-project --input tests\\agent_factory_benchmark\\fixtures\\input_devops_incident.json --output-dir runs\\agent_project_devops",
    ]
    write_report(discovery, phase1_results, phase2_results, holdout_results, phase4_results, commands)
    print(
        json.dumps(
            {
                "phase1_pass_count": phase1["pass_count"],
                "phase1_fail_count": phase1["fail_count"],
                "phase1_unsupported_count": phase1["unsupported_count"],
                "phase2_pass_count": phase2["pass_count"],
                "phase2_fail_count": phase2["fail_count"],
                "phase2_warning_count": phase2["warning_count"],
                "phase2_unsupported_count": phase2["unsupported_count"],
                "holdout_pass_count": holdout["pass_count"],
                "holdout_fail_count": holdout["fail_count"],
                "holdout_warning_count": holdout["warning_count"],
                "holdout_unsupported_count": holdout["unsupported_count"],
                "phase4_pass_count": phase4["pass_count"],
                "phase4_fail_count": phase4["fail_count"],
                "phase4_unsupported_count": phase4["unsupported_count"],
                "report": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
