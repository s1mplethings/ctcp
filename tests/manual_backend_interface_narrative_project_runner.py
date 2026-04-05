from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ctcp_front_bridge as bridge


FIXED_NARRATIVE_PROMPT = (
    "我想要生成一个可以帮助创作者制作叙事项目的助手。"
    "它重点服务悬疑 / 解谜 / 猎奇风格。"
    "它需要能帮助用户梳理故事线、角色关系、章节结构、分支结局，"
    "还能生成角色立绘、表情、背景、CG 的提示词，"
    "最后输出成可以继续用于叙事制作的结构化内容。"
)


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _run_cmd(cmd: list[str], cwd: Path) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "cmd": " ".join(cmd),
        "rc": int(proc.returncode),
        "stdout_tail": "\n".join(str(proc.stdout or "").splitlines()[-20:]),
        "stderr_tail": "\n".join(str(proc.stderr or "").splitlines()[-20:]),
    }


def _collect_project_output(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    manifest_file: dict[str, Any],
    output_contract: dict[str, Any],
) -> dict[str, Any]:
    project_root = str(
        manifest_file.get("project_root")
        or manifest.get("project_root")
        or output_contract.get("project_root")
        or ""
    ).strip()
    project_dir = (run_dir / project_root).resolve() if project_root else Path("")
    startup_entry = str(
        manifest_file.get("startup_entrypoint")
        or manifest.get("startup_entrypoint")
        or ""
    ).strip()
    startup_readme = str(
        manifest_file.get("startup_readme")
        or manifest.get("startup_readme")
        or ""
    ).strip()
    startup_entry_path = (run_dir / startup_entry).resolve() if startup_entry else Path("")
    startup_smoke: dict[str, Any] = {}
    if startup_entry_path and startup_entry_path.exists():
        startup_smoke = _run_cmd([sys.executable, str(startup_entry_path), "--help"], cwd=startup_entry_path.parent)
    business_files_generated = (
        list(manifest_file.get("business_files_generated", []))
        if isinstance(manifest_file.get("business_files_generated"), list)
        else []
    )
    return {
        "project_root": project_root,
        "project_dir": project_dir,
        "startup_entrypoint": startup_entry,
        "startup_entry_path": startup_entry_path,
        "startup_readme": startup_readme,
        "startup_smoke": startup_smoke,
        "business_files_generated": business_files_generated,
    }


def _build_checks(
    *,
    find_result: dict[str, Any],
    output_contract: dict[str, Any],
    source_stage: dict[str, Any],
    docs_stage: dict[str, Any],
    workflow_stage: dict[str, Any],
    manifest: dict[str, Any],
    manifest_file: dict[str, Any],
    deliver_index: dict[str, Any],
    project_output: dict[str, Any],
    status_final: dict[str, Any],
    output_paths: list[str],
    run_dir: Path,
) -> dict[str, Any]:
    deliverables = list(deliver_index.get("deliverables", [])) if isinstance(deliver_index.get("deliverables"), list) else []
    business_files_generated = list(source_stage.get("business_files_generated", [])) if isinstance(source_stage.get("business_files_generated"), list) else []
    narrative_required_modules = [
        f"{project_output.get('project_root', '')}/src/narrative_copilot/story/outline.py",
        f"{project_output.get('project_root', '')}/src/narrative_copilot/story/chapter_planner.py",
        f"{project_output.get('project_root', '')}/src/narrative_copilot/cast/schema.py",
        f"{project_output.get('project_root', '')}/src/narrative_copilot/pipeline/prompt_pipeline.py",
        f"{project_output.get('project_root', '')}/src/narrative_copilot/exporters/deliver.py",
        f"{project_output.get('project_root', '')}/src/narrative_copilot/service.py",
        f"{project_output.get('project_root', '')}/tests/test_narrative_copilot_service.py",
    ]
    return {
        "selected_workflow_id": str(find_result.get("selected_workflow_id", "")).strip(),
        "has_output_contract_freeze": bool(output_contract),
        "has_source_generation_report": bool(source_stage),
        "has_docs_generation_report": bool(docs_stage),
        "has_workflow_generation_report": bool(workflow_stage),
        "has_project_manifest_file": bool(manifest_file),
        "has_deliverable_index": bool(deliver_index),
        "bridge_has_project_manifest": bool(isinstance(manifest, dict) and manifest.get("run_id")),
        "manifest_missing_files_empty": not bool(list(manifest_file.get("missing_files", []) if isinstance(manifest_file.get("missing_files"), list) else [])),
        "source_generation_business_codegen_used": bool(source_stage.get("business_codegen_used", False)),
        "source_generation_consumed_context_pack": bool(source_stage.get("consumed_context_pack", False)),
        "source_generation_execution_mode_is_benchmark": str(source_stage.get("execution_mode", "")).strip() == "benchmark_regression",
        "source_generation_delivery_shape_present": bool(str(source_stage.get("delivery_shape", "")).strip()),
        "source_generation_context_influence_present": bool(list(source_stage.get("context_influence_summary", []) if isinstance(source_stage.get("context_influence_summary"), list) else [])),
        "source_generation_business_files_generated_non_empty": bool(business_files_generated),
        "source_generation_business_files_missing_empty": not bool(list(source_stage.get("business_files_missing", []) if isinstance(source_stage.get("business_files_missing"), list) else [])),
        "project_root_exists": bool(project_output.get("project_root") and Path(project_output.get("project_dir", "")).exists()),
        "startup_entry_exists": bool(project_output.get("startup_entrypoint") and Path(project_output.get("startup_entry_path", "")).exists()),
        "startup_readme_exists": bool(project_output.get("startup_readme") and (run_dir / str(project_output.get("startup_readme", ""))).exists()),
        "startup_smoke_passed": bool(dict(project_output.get("startup_smoke", {})) and int(dict(project_output.get("startup_smoke", {})).get("rc", 1)) == 0),
        "narrative_business_modules_present": all((run_dir / rel).exists() for rel in narrative_required_modules if rel.strip()),
        "deliver_index_contains_business_modules": any(rel in deliverables for rel in business_files_generated),
        "deliver_index_not_scaffold_only": any("/src/narrative_copilot/" in rel for rel in deliverables),
        "manifest_execution_mode_is_benchmark": str(manifest_file.get("execution_mode", "")).strip() == "benchmark_regression",
        "manifest_delivery_shape_present": bool(str(manifest_file.get("delivery_shape", "")).strip()),
        "fell_back_to_ready_apply": str((status_final.get("gate", {}) or {}).get("state", "")).strip().lower() == "ready_apply",
        "has_manual_injected_story_tree_project": any(path.startswith("artifacts/story_tree_project/") for path in output_paths),
        "output_count": len(output_paths),
    }


def run_narrative_project_e2e() -> dict[str, Any]:
    out_root = ROOT / "artifacts" / "backend_interface_narrative"
    out_root.mkdir(parents=True, exist_ok=True)

    req_create = {
        "goal": FIXED_NARRATIVE_PROMPT,
        "constraints": {
            "project_generation_mode": "benchmark_regression",
            "benchmark_case": "narrative_fixed_project_generation_regression",
            "test_case": "narrative_fixed_project_generation_regression",
            "expect_project_generation_workflow": True,
        },
        "attachments": [],
    }
    create_resp = bridge.create_run(**req_create)
    run_id = str(create_resp.get("run_id", "")).strip()
    run_dir = Path(str(create_resp.get("run_dir", "")).strip())

    status_0 = bridge.get_run_status(run_id)

    timeline: list[dict[str, Any]] = []
    stagnation_count = 0
    last_gate_sig = ""
    for idx in range(24):
        adv = bridge.advance_run(run_id, max_steps=1)
        status = bridge.get_run_status(run_id)
        gate = status.get("gate", {}) if isinstance(status, dict) else {}
        gate_sig = (
            str(gate.get("state", "")).strip().lower(),
            str(gate.get("owner", "")).strip(),
            str(gate.get("reason", "")).strip(),
            str(status.get("run_status", "")).strip().lower(),
        )
        timeline.append(
            {
                "index": idx + 1,
                "advance_exit_code": int((adv.get("advance", {}) or {}).get("exit_code", 1) or 1),
                "run_status": str(status.get("run_status", "")).strip().lower(),
                "phase": str(status.get("phase", "")).strip(),
                "gate_state": str(gate.get("state", "")).strip().lower(),
                "gate_owner": str(gate.get("owner", "")).strip(),
                "gate_reason": str(gate.get("reason", "")).strip(),
                "verify_result": str(status.get("verify_result", "")).strip().upper(),
            }
        )

        if str(gate_sig) == last_gate_sig:
            stagnation_count += 1
        else:
            stagnation_count = 0
        last_gate_sig = str(gate_sig)

        run_status = str(status.get("run_status", "")).strip().lower()
        gate_state = str(gate.get("state", "")).strip().lower()
        if run_status in {"pass", "fail"}:
            break
        if gate_state == "ready_apply":
            # Project-generation request should not default to generic patch apply path.
            break
        if stagnation_count >= 3:
            break

    status_final = bridge.get_run_status(run_id)
    support_ctx = bridge.get_support_context(run_id)
    decisions = bridge.list_pending_decisions(run_id)
    outputs = bridge.list_output_artifacts(run_id)
    manifest = bridge.get_project_manifest(run_id)
    report = bridge.get_last_report(run_id)
    current_snapshot = bridge.get_current_state_snapshot(run_id)
    render_snapshot = bridge.get_render_state_snapshot(run_id)

    find_result = _load_json(run_dir / "artifacts" / "find_result.json")
    output_contract = _load_json(run_dir / "artifacts" / "output_contract_freeze.json")
    source_stage = _load_json(run_dir / "artifacts" / "source_generation_report.json")
    docs_stage = _load_json(run_dir / "artifacts" / "docs_generation_report.json")
    workflow_stage = _load_json(run_dir / "artifacts" / "workflow_generation_report.json")
    manifest_file = _load_json(run_dir / "artifacts" / "project_manifest.json")
    deliver_index = _load_json(run_dir / "artifacts" / "deliverable_index.json")
    project_output = _collect_project_output(
        run_dir=run_dir,
        manifest=manifest,
        manifest_file=manifest_file,
        output_contract=output_contract,
    )

    output_rows = list(outputs.get("artifacts", [])) if isinstance(outputs.get("artifacts"), list) else []
    output_paths = [str(dict(row).get("rel_path", "")).strip() for row in output_rows if isinstance(row, dict)]
    checks = _build_checks(
        find_result=find_result,
        output_contract=output_contract,
        source_stage=source_stage,
        docs_stage=docs_stage,
        workflow_stage=workflow_stage,
        manifest=manifest,
        manifest_file=manifest_file,
        deliver_index=deliver_index,
        project_output=project_output,
        status_final=status_final,
        output_paths=output_paths,
        run_dir=run_dir,
    )

    return {
        "task_name": "benchmark_narrative_project_generation_regression",
        "fixed_prompt": FIXED_NARRATIVE_PROMPT,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "step1_create_run": {"request": req_create, "response": create_resp},
        "step2_initial_status": status_0,
        "step3_advance_timeline": timeline,
        "step4_final_status": status_final,
        "step5_support_context": support_ctx,
        "step6_decisions": decisions,
        "step7_output_artifacts": outputs,
        "step8_project_manifest_api": manifest,
        "step9_last_report": report,
        "step10_snapshots": {"current": current_snapshot, "render": render_snapshot},
        "artifact_evidence": {
            "find_result": find_result,
            "output_contract_freeze": output_contract,
            "source_generation_report": source_stage,
            "docs_generation_report": docs_stage,
            "workflow_generation_report": workflow_stage,
            "project_manifest_file": manifest_file,
            "deliverable_index": deliver_index,
        },
        "project_output": {
            "project_root": str(project_output.get("project_root", "")),
            "project_dir": str(project_output.get("project_dir", "")),
            "startup_entrypoint": str(project_output.get("startup_entrypoint", "")),
            "startup_readme": str(project_output.get("startup_readme", "")),
            "startup_smoke": dict(project_output.get("startup_smoke", {})),
            "business_files_generated": list(project_output.get("business_files_generated", [])),
        },
        "checks": checks,
    }


def _assert_pass(checks: dict[str, Any]) -> None:
    required = [
        "has_output_contract_freeze",
        "has_source_generation_report",
        "has_docs_generation_report",
        "has_workflow_generation_report",
        "has_project_manifest_file",
        "has_deliverable_index",
        "bridge_has_project_manifest",
        "manifest_missing_files_empty",
        "source_generation_business_codegen_used",
        "source_generation_consumed_context_pack",
        "source_generation_execution_mode_is_benchmark",
        "source_generation_delivery_shape_present",
        "source_generation_context_influence_present",
        "source_generation_business_files_generated_non_empty",
        "source_generation_business_files_missing_empty",
        "project_root_exists",
        "startup_entry_exists",
        "startup_readme_exists",
        "startup_smoke_passed",
        "narrative_business_modules_present",
        "deliver_index_contains_business_modules",
        "deliver_index_not_scaffold_only",
        "manifest_execution_mode_is_benchmark",
        "manifest_delivery_shape_present",
    ]
    failures = [name for name in required if not bool(checks.get(name, False))]
    if failures:
        raise SystemExit("manual narrative regression failed: " + ", ".join(failures))


if __name__ == "__main__":
    result = run_narrative_project_e2e()
    report_path = ROOT / "artifacts" / "backend_interface_narrative" / "narrative_backend_interface_e2e_report.json"
    _write_json(report_path, result)
    _assert_pass(dict(result.get("checks", {})))
    print(json.dumps({"report_path": str(report_path), "run_id": result.get("run_id", "")}, ensure_ascii=False))

