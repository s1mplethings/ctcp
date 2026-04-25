#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from tools.formal_api_lock import load_provider_ledger_summary

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_ZIP = ROOT / "plane_lite_team_pm_test_pack.zip"
SUMMARY_TEMPLATE = ROOT / "templates" / "benchmark_summary_template.json"

HQ_PROFILE_DIRECTIVE = (
    "本轮是 formal_hq_benchmark。请在 plane_lite_team_pm 基础上按 high-quality / extended build 标准执行，"
    "不要缩回基础 MVP。必须包含 Dashboard、项目列表、单项目总览、任务列表、看板、任务详情、活动流、"
    "设置/项目配置、多项目切换、search/filter/sort、import/export、feature matrix、page map、"
    "data model summary、至少 8 张最终截图，并保留完整 evidence bundle。"
)

ENDURANCE_GOAL = (
    "我想做一个给独立游戏团队用的本地生产协作平台。\n"
    "团队大概 5 到 20 人，主要有策划、程序、美术、测试、制作人。\n"
    "我不想只要普通任务看板，我希望它能把任务、素材、Bug、版本进度、发布准备这些东西放在一起。\n"
    "不要做成很重的企业系统，但最终要像一个真的可以长期使用的产品。"
)

PROFILE_TO_ENTRY = {
    "basic": "formal_basic_benchmark",
    "hq": "formal_hq_benchmark",
    "endurance": "formal_endurance_benchmark",
}

PROFILE_TO_GOLDEN_DIR = {
    "basic": "formal_basic_benchmark",
    "hq": "formal_hq_benchmark",
    "endurance": "endurance_indie_studio_hub",
}

PROFILE_TO_SUMMARY_BASENAME = {
    "basic": "formal_basic_benchmark_summary",
    "hq": "formal_hq_benchmark_summary",
    "endurance": "benchmark_endurance_summary",
}

PROFILE_GOLDEN_FILES: dict[str, tuple[tuple[str, str], ...]] = {
    "basic": (
        ("transcript", "formal_transcript.md"),
        ("api_calls.jsonl", "api_calls.jsonl"),
        ("artifacts/provider_ledger.jsonl", "provider_ledger.jsonl"),
        ("artifacts/provider_ledger_summary.json", "provider_ledger_summary.json"),
        ("artifacts/project_spec.json", "project_spec.json"),
        ("artifacts/output_contract_freeze.json", "output_contract_freeze.json"),
        ("artifacts/verify_report.json", "verify_report.json"),
        ("artifacts/support_public_delivery.json", "support_public_delivery.json"),
        ("artifacts/final_project_bundle.zip", "final_project_bundle.zip"),
        ("artifacts/intermediate_evidence_bundle.zip", "intermediate_evidence_bundle.zip"),
    ),
    "hq": (
        ("transcript", "formal_transcript.md"),
        ("api_calls.jsonl", "api_calls.jsonl"),
        ("artifacts/provider_ledger.jsonl", "provider_ledger.jsonl"),
        ("artifacts/provider_ledger_summary.json", "provider_ledger_summary.json"),
        ("artifacts/project_spec.json", "project_spec.json"),
        ("artifacts/output_contract_freeze.json", "output_contract_freeze.json"),
        ("artifacts/verify_report.json", "verify_report.json"),
        ("artifacts/support_public_delivery.json", "support_public_delivery.json"),
        ("artifacts/final_project_bundle.zip", "final_project_bundle.zip"),
        ("artifacts/intermediate_evidence_bundle.zip", "intermediate_evidence_bundle.zip"),
    ),
    "endurance": (
        ("transcript", "formal_transcript.md"),
        ("api_calls.jsonl", "api_calls.jsonl"),
        ("artifacts/provider_ledger.jsonl", "provider_ledger.jsonl"),
        ("artifacts/provider_ledger_summary.json", "provider_ledger_summary.json"),
        ("artifacts/project_spec.json", "project_spec.json"),
        ("artifacts/output_contract_freeze.json", "output_contract_freeze.json"),
        ("artifacts/source_generation_report.json", "source_generation_report.json"),
        ("artifacts/project_manifest.json", "project_manifest.json"),
        ("artifacts/deliverable_index.json", "deliverable_index.json"),
        ("artifacts/support_public_delivery.json", "support_public_delivery.json"),
        ("artifacts/verify_report.json", "verify_report.json"),
        ("artifacts/final_project_bundle.zip", "final_project_bundle.zip"),
        ("artifacts/intermediate_evidence_bundle.zip", "intermediate_evidence_bundle.zip"),
        ("screenshots", "screenshots"),
    ),
}


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _mask_secret(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    if len(value) <= 10:
        return value[:2] + "..." + value[-2:]
    return value[:7] + "..." + value[-4:]


def _provider_summary() -> dict[str, str]:
    return {
        "provider": os.environ.get("CTCP_FORCE_PROVIDER", "api_agent") or "api_agent",
        "model": os.environ.get("CTCP_API_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-4.1-mini",
        "base_url": os.environ.get("CTCP_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.gptsapi.net/v1",
        "key_mask": _mask_secret(os.environ.get("OPENAI_API_KEY") or os.environ.get("CTCP_API_KEY") or ""),
        "project": os.environ.get("OPENAI_PROJECT") or os.environ.get("CTCP_OPENAI_PROJECT") or "",
        "organization": os.environ.get("OPENAI_ORG_ID") or os.environ.get("OPENAI_ORGANIZATION") or "",
        "confirmed_non_mock": str(os.environ.get("CTCP_FORCE_PROVIDER", "api_agent") != "mock_agent").lower(),
    }


def _profile_entry(profile: str) -> str:
    return PROFILE_TO_ENTRY[profile]


def _summary_basename(profile: str) -> str:
    return PROFILE_TO_SUMMARY_BASENAME[profile]


def _golden_dir_name(profile: str) -> str:
    return PROFILE_TO_GOLDEN_DIR[profile]


def _load_benchmark(zip_path: Path, extract_to: Path | None = None) -> dict[str, Any]:
    if not zip_path.exists():
        raise FileNotFoundError(f"benchmark zip not found: {zip_path}")
    files: dict[str, str] = {}
    with zipfile.ZipFile(zip_path) as zf:
        if extract_to is not None:
            extract_to.mkdir(parents=True, exist_ok=True)
            zf.extractall(extract_to)
        for name in zf.namelist():
            if name.endswith("/"):
                continue
            if name.lower().endswith((".md", ".json", ".txt")):
                files[name] = zf.read(name).decode("utf-8", errors="replace")
    case_name = next((name for name in files if name.endswith("benchmark_case.json")), "")
    case = json.loads(files[case_name]) if case_name else {}
    return {"zip_path": str(zip_path), "case": case, "files": files}


def _benchmark_source_label(profile: str, benchmark_zip: Path | None) -> str:
    if profile == "endurance":
        return "embedded_endurance_rough_goal"
    return str(benchmark_zip or DEFAULT_BENCHMARK_ZIP)


def _turns_for_profile(profile: str, benchmark: dict[str, Any] | None) -> list[str]:
    if profile == "endurance":
        return [ENDURANCE_GOAL]
    case = (benchmark or {}).get("case", {})
    turns = list(case.get("scripted_turns", [])) if isinstance(case, dict) else []
    if not turns:
        raise RuntimeError("benchmark_case.json has no scripted_turns")
    if profile == "hq":
        return [HQ_PROFILE_DIRECTIVE, *turns]
    return turns


def _run_command(
    args: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
) -> dict[str, Any]:
    proc = subprocess.run(
        args,
        cwd=str(cwd),
        input=stdin_text,
        text=True,
        capture_output=True,
        env=env,
    )
    return {
        "cmd": " ".join(args),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _latest_run_dir(runs_root: Path) -> Path:
    ctcp_root = runs_root / "ctcp"
    candidates = [
        path
        for path in ctcp_root.iterdir()
        if path.is_dir() and path.name != "support_sessions" and (path / "RUN.json").exists()
    ]
    if not candidates:
        raise RuntimeError(f"no CTCP run_dir found under {ctcp_root}")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _support_session_dir(run_dir: Path, chat_id: str | None = None) -> Path | None:
    root = run_dir.parent / "support_sessions"
    if not root.exists():
        return None
    if chat_id:
        direct = root / chat_id
        if direct.exists():
            return direct
    run_id = run_dir.name
    for state_path in root.glob("*/artifacts/support_session_state.json"):
        state = _read_json(state_path)
        bound_run_id = str(state.get("bound_run_id", "")).strip()
        bound_run_dir = str(state.get("bound_run_dir", "")).strip().lower()
        if bound_run_id == run_id or bound_run_dir == str(run_dir).lower():
            return state_path.parents[1]
    return None


def _run_profile(profile: str, benchmark_zip: Path | None, runs_root: Path | None, chat_id: str | None) -> tuple[Path, Path | None]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if runs_root is None:
        runs_root = Path(tempfile.gettempdir()) / f"ctcp_formal_{profile}_benchmark_{stamp}" / "runs"
    runs_root.mkdir(parents=True, exist_ok=True)
    benchmark: dict[str, Any] | None = None
    if profile in {"basic", "hq"}:
        benchmark = _load_benchmark((benchmark_zip or DEFAULT_BENCHMARK_ZIP), runs_root.parent / "benchmark_input")
    turns = _turns_for_profile(profile, benchmark)
    chat_id = chat_id or f"formal_{profile}_benchmark_{stamp}"
    env = os.environ.copy()
    env["CTCP_FORCE_PROVIDER"] = "api_agent"
    env["CTCP_FORMAL_API_ONLY"] = "1"
    env["CTCP_RUNS_ROOT"] = str(runs_root)
    if env.get("CTCP_FORCE_PROVIDER") == "mock_agent":
        raise RuntimeError("mock_agent is forbidden for formal benchmark runs")

    transcript_rows: list[str] = [f"# {_profile_entry(profile)} transcript\n"]
    command_rows: list[dict[str, Any]] = []
    for idx, turn in enumerate(turns, start=1):
        result = _run_command(
            [sys.executable, "scripts/ctcp_support_bot.py", "--stdin", "--chat-id", chat_id, "--provider", "api_agent"],
            env=env,
            stdin_text=turn,
        )
        command_rows.append({"turn": idx, "command": result["cmd"], "returncode": result["returncode"]})
        transcript_rows.append(f"\n## Turn {idx}\n\n### User\n{turn}\n\n### System\n{result['stdout'].strip()}\n")
        if result["returncode"] != 0:
            raise RuntimeError(f"support bot failed on turn {idx}: {result['stderr']}")

    run_dir = _latest_run_dir(runs_root)
    transcript_path = run_dir / f"{_profile_entry(profile)}_transcript.md"
    transcript_path.write_text("\n".join(transcript_rows), encoding="utf-8")
    _write_json(run_dir / f"{_profile_entry(profile)}_commands.json", {"commands": command_rows})

    step_budget = "120" if profile == "endurance" else "80"
    for _ in range(6):
        status_result = _run_command(
            [sys.executable, "scripts/ctcp_orchestrate.py", "status", "--run-dir", str(run_dir)],
            env=env,
        )
        command_rows.append({"command": status_result["cmd"], "returncode": status_result["returncode"]})
        if status_result["returncode"] != 0:
            break
        if _run_status(run_dir) in {"pass", "fail"}:
            break
        advance_result = _run_command(
            [sys.executable, "scripts/ctcp_orchestrate.py", "advance", "--run-dir", str(run_dir), "--max-steps", step_budget],
            env=env,
        )
        command_rows.append({"command": advance_result["cmd"], "returncode": advance_result["returncode"]})
        if advance_result["returncode"] != 0 or _run_status(run_dir) in {"pass", "fail"}:
            break
    final_status = _run_command(
        [sys.executable, "scripts/ctcp_orchestrate.py", "status", "--run-dir", str(run_dir)],
        env=env,
    )
    command_rows.append({"command": final_status["cmd"], "returncode": final_status["returncode"]})
    _write_json(run_dir / f"{_profile_entry(profile)}_commands.json", {"commands": command_rows})
    return run_dir, _support_session_dir(run_dir, chat_id)


def _api_summary(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "api_calls.jsonl"
    rows: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                try:
                    item = json.loads(line)
                    if isinstance(item, dict):
                        rows.append(item)
                except Exception:
                    pass
    ok = [row for row in rows if str(row.get("status", "")).upper() == "OK"]
    err = [row for row in rows if str(row.get("status", "")).upper() == "ERR"]
    return {
        "api_calls_path": str(path) if path.exists() else "",
        "total": len(rows),
        "ok": len(ok),
        "err": len(err),
        "request_ids": [str(row.get("request_id", "")) for row in ok if row.get("request_id")],
        "true_remote_api_used": bool(ok),
    }


def _acceptance_summary(run_dir: Path) -> dict[str, Any]:
    acceptance_root = run_dir / "artifacts" / "acceptance"
    triplet_dirs = []
    missing = []
    fallback_passed = []
    if acceptance_root.exists():
        for child in acceptance_root.glob("**"):
            if not child.is_dir() or child == acceptance_root:
                continue
            files = {name for name in ("request.json", "result.json", "acceptance.json") if (child / name).exists()}
            if files:
                rel = child.relative_to(acceptance_root).as_posix()
                if files == {"request.json", "result.json", "acceptance.json"}:
                    triplet_dirs.append(rel)
                    result = _read_json(child / "result.json")
                    acceptance = _read_json(child / "acceptance.json")
                    if result.get("fallback_used") is True and acceptance.get("passed") is True:
                        fallback_passed.append(rel)
                else:
                    missing.append({"step": rel, "present": sorted(files)})
    ledger = acceptance_root / "ledger.jsonl"
    ledger_lines = 0
    if ledger.exists():
        ledger_lines = len([line for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()])
    return {
        "triplet_dir_count": len(triplet_dirs),
        "ledger_path": str(ledger) if ledger.exists() else "",
        "ledger_lines": ledger_lines,
        "missing_triplets": missing,
        "fallback_accepted_as_passed": fallback_passed,
        "complete": bool(triplet_dirs) and not missing,
    }


def _provider_ledger_summary(run_dir: Path) -> dict[str, Any]:
    return load_provider_ledger_summary(run_dir)


def _bundle_summary(run_dir: Path) -> dict[str, Any]:
    final_zip = run_dir / "artifacts" / "final_project_bundle.zip"
    evidence_zip = run_dir / "artifacts" / "intermediate_evidence_bundle.zip"
    return {
        "final_project_bundle": str(final_zip),
        "final_project_bundle_exists": final_zip.exists(),
        "intermediate_evidence_bundle": str(evidence_zip),
        "intermediate_evidence_bundle_exists": evidence_zip.exists(),
    }


def _verify_summary(run_dir: Path) -> dict[str, Any]:
    verify_path = run_dir / "artifacts" / "verify_report.json"
    verify = _read_json(verify_path)
    return {
        "path": str(verify_path),
        "result": verify.get("result", ""),
        "first_failure_point": verify.get("first_failure_point", ""),
    }


def _replay_summary(delivery: dict[str, Any]) -> dict[str, Any]:
    replay = delivery.get("replay_report", {}) if isinstance(delivery.get("replay_report"), dict) else {}
    completion = delivery.get("completion_gate", {}) if isinstance(delivery.get("completion_gate"), dict) else {}
    return {
        "overall_pass": bool(replay.get("overall_pass", False)),
        "startup_pass": bool(replay.get("startup_pass", False)),
        "minimal_flow_pass": bool(replay.get("minimal_flow_pass", False)),
        "report_path": replay.get("report_path", "") or completion.get("replay_report_path", ""),
        "replay_screenshot_path": replay.get("replay_screenshot_path", "") or completion.get("replay_screenshot_path", ""),
        "first_failure_stage": replay.get("first_failure_stage", ""),
    }


def _delivery_summary(run_dir: Path) -> dict[str, Any]:
    delivery_path = run_dir / "artifacts" / "support_public_delivery.json"
    delivery = _read_json(delivery_path)
    gate = delivery.get("completion_gate", {}) if isinstance(delivery.get("completion_gate"), dict) else {}
    overall = delivery.get("overall_completion", {}) if isinstance(delivery.get("overall_completion"), dict) else {}
    return {
        "support_public_delivery_path": str(delivery_path),
        "completion_gate_passed": bool(gate.get("passed", False)),
        "cold_replay_passed": bool(gate.get("cold_replay_passed", False)),
        "overall_completion_passed": bool(overall.get("passed", False)),
        "internal_runtime_status": str(delivery.get("internal_runtime_status", "")).strip(),
        "user_acceptance_status": str(delivery.get("user_acceptance_status", "")).strip(),
        "product_completion_passed": bool((delivery.get("product_completion", {}) if isinstance(delivery.get("product_completion"), dict) else {}).get("passed", False)),
        "user_acceptance_passed": bool((delivery.get("user_acceptance", {}) if isinstance(delivery.get("user_acceptance"), dict) else {}).get("passed", False)),
        "delivery_completion_passed": bool((delivery.get("delivery_completion", {}) if isinstance(delivery.get("delivery_completion"), dict) else {}).get("passed", False)),
        "replay_summary": _replay_summary(delivery),
    }


def _extended_summary(run_dir: Path) -> dict[str, Any]:
    ledger_path = run_dir / "artifacts" / "extended_coverage_ledger.json"
    ledger = _read_json(ledger_path)
    coverage = ledger.get("coverage", {}) if isinstance(ledger.get("coverage"), dict) else {}
    screenshot_files = ledger.get("screenshot_files", []) if isinstance(ledger.get("screenshot_files"), list) else []
    documentation_files = ledger.get("documentation_files", []) if isinstance(ledger.get("documentation_files"), list) else []
    return {
        "ledger_path": str(ledger_path),
        "ledger_exists": bool(ledger),
        "ledger_passed": bool(ledger.get("passed", False)),
        "implemented_pages": ledger.get("implemented_pages", []),
        "implemented_capabilities": ledger.get("implemented_capabilities", []),
        "documentation_files": documentation_files,
        "screenshot_files": screenshot_files,
        "screenshot_count": len(screenshot_files),
        "coverage": coverage,
    }


def _source_generation_summary(run_dir: Path) -> dict[str, Any]:
    report_path = run_dir / "artifacts" / "source_generation_report.json"
    report = _read_json(report_path)
    generic_validation = report.get("generic_validation", {}) if isinstance(report.get("generic_validation"), dict) else {}
    python_syntax = generic_validation.get("python_syntax", {}) if isinstance(generic_validation.get("python_syntax"), dict) else {}
    return {
        "path": str(report_path),
        "status": report.get("status", ""),
        "package_name": report.get("package_name", ""),
        "generic_validation_passed": bool(generic_validation.get("passed", False)),
        "python_syntax_passed": bool(python_syntax.get("passed", False)),
    }


def _run_status(run_dir: Path) -> str:
    run = _read_json(run_dir / "RUN.json")
    status = str(run.get("status", "")).strip()
    if status:
        return status
    trace = run_dir / "TRACE.md"
    if trace.exists() and "run_pass" in trace.read_text(encoding="utf-8", errors="replace"):
        return "pass"
    return ""


def _spec_freeze_summary(run_dir: Path) -> dict[str, Any]:
    spec = _read_json(run_dir / "artifacts" / "project_spec.json")
    freeze = _read_json(run_dir / "artifacts" / "output_contract_freeze.json")
    return {
        "project_domain": freeze.get("project_domain") or spec.get("project_domain"),
        "project_type": freeze.get("project_type") or spec.get("project_type"),
        "project_archetype": freeze.get("project_archetype") or spec.get("project_archetype"),
        "build_profile": freeze.get("build_profile") or spec.get("build_profile"),
        "product_depth": freeze.get("product_depth") or spec.get("product_depth"),
        "required_pages": freeze.get("required_pages") or spec.get("required_pages"),
        "required_screenshots": freeze.get("required_screenshots") or spec.get("required_screenshots"),
        "package_name": freeze.get("package_name") or spec.get("package_name") or "",
    }


def _evaluate(profile: str, summary: dict[str, Any]) -> tuple[str, str]:
    spec = summary["spec_freeze"]
    api = summary["api_usage_summary"]
    acceptance = summary["acceptance_summary"]
    verify = summary["verify_summary"]
    delivery = summary["delivery_summary"]
    bundles = summary["bundle_summary"]
    checks: list[tuple[str, bool]] = [
        ("true API used", bool(api.get("true_remote_api_used"))),
        ("provider ledger critical steps are API", bool(summary.get("provider_ledger_summary", {}).get("all_critical_steps_api", False))),
        ("workflow is wf_project_generation_manifest", summary.get("workflow_id") == "wf_project_generation_manifest"),
        ("acceptance triplets complete", bool(acceptance.get("complete"))),
        ("no fallback accepted", not acceptance.get("fallback_accepted_as_passed")),
        ("verify PASS", verify.get("result") == "PASS"),
        ("delivery completion PASS", bool(delivery.get("completion_gate_passed"))),
        ("cold replay PASS", bool(delivery.get("cold_replay_passed"))),
        ("final bundle exists", bool(bundles.get("final_project_bundle_exists"))),
        ("evidence bundle exists", bool(bundles.get("intermediate_evidence_bundle_exists"))),
        ("run_status pass", summary.get("run_status") == "pass"),
    ]
    if profile in {"basic", "hq"}:
        checks.extend(
            [
                ("domain is team_task_management", spec.get("project_domain") == "team_task_management"),
                ("type is team_task_pm", spec.get("project_type") == "team_task_pm"),
                ("archetype is team_task_pm_web", spec.get("project_archetype") == "team_task_pm_web"),
            ]
        )
    if profile == "hq":
        extended = summary["extended_coverage_summary"]
        coverage = extended.get("coverage", {})
        checks.extend(
            [
                ("build_profile high_quality_extended", spec.get("build_profile") == "high_quality_extended"),
                ("required_pages 8", int(spec.get("required_pages", 0) or 0) >= 8),
                ("required_screenshots 8", int(spec.get("required_screenshots", 0) or 0) >= 8),
                ("feature matrix present", bool(coverage.get("feature_matrix", {}).get("passed"))),
                ("page map present", bool(coverage.get("page_map", {}).get("passed"))),
                ("data model summary present", bool(coverage.get("data_model_summary", {}).get("passed"))),
                ("dashboard/overview present", bool(coverage.get("dashboard_or_project_overview", {}).get("passed"))),
                ("search present", bool(coverage.get("search", {}).get("passed"))),
                ("import/export present", bool(coverage.get("import_export", {}).get("passed"))),
                ("extended ledger passed", bool(extended.get("ledger_passed"))),
                ("screenshot count >= 8", int(extended.get("screenshot_count", 0) or 0) >= 8),
            ]
        )
    if profile == "endurance":
        extended = summary["extended_coverage_summary"]
        coverage = extended.get("coverage", {})
        source_generation = summary["source_generation_summary"]
        checks.extend(
            [
                ("domain is indie_studio_production_hub", spec.get("project_domain") == "indie_studio_production_hub"),
                ("type is indie_studio_hub", spec.get("project_type") == "indie_studio_hub"),
                ("archetype is indie_studio_hub_web", spec.get("project_archetype") == "indie_studio_hub_web"),
                ("package_name present", bool(spec.get("package_name"))),
                ("source generation PASS", source_generation.get("status") == "pass"),
                ("generic validation PASS", bool(source_generation.get("generic_validation_passed"))),
                ("python syntax PASS", bool(source_generation.get("python_syntax_passed"))),
                ("internal_runtime_status PASS", delivery.get("internal_runtime_status") == "PASS"),
                ("user_acceptance_status PASS", delivery.get("user_acceptance_status") == "PASS"),
                ("extended ledger passed", bool(extended.get("ledger_passed"))),
                ("page count >= 12", int(coverage.get("pages", {}).get("actual", 0) or 0) >= 12),
                ("screenshot count >= 10", int(extended.get("screenshot_count", 0) or 0) >= 10),
                ("feature matrix present", bool(coverage.get("feature_matrix", {}).get("passed"))),
                ("page map present", bool(coverage.get("page_map", {}).get("passed"))),
                ("data model summary present", bool(coverage.get("data_model_summary", {}).get("passed"))),
                ("milestone plan present", bool(coverage.get("milestone_plan", {}).get("passed"))),
                ("startup guide present", bool(coverage.get("startup_guide", {}).get("passed"))),
                ("replay guide present", bool(coverage.get("replay_guide", {}).get("passed"))),
                ("mid stage review present", bool(coverage.get("mid_stage_review", {}).get("passed"))),
                ("asset library covered", bool(coverage.get("asset_library", {}).get("passed"))),
                ("asset detail covered", bool(coverage.get("asset_detail", {}).get("passed"))),
                ("bug tracker covered", bool(coverage.get("bug_tracker", {}).get("passed"))),
                ("build release center covered", bool(coverage.get("build_release_center", {}).get("passed"))),
                ("docs center covered", bool(coverage.get("docs_center", {}).get("passed"))),
            ]
        )
    failed = [name for name, ok in checks if not ok]
    if not failed:
        return "PASS", ""
    return "FAIL", failed[0]


def build_summary(profile: str, run_dir: Path, benchmark_zip: Path | None = DEFAULT_BENCHMARK_ZIP, chat_id: str | None = None) -> dict[str, Any]:
    if profile in {"basic", "hq"}:
        _load_benchmark((benchmark_zip or DEFAULT_BENCHMARK_ZIP), None)
    find_result = _read_json(run_dir / "artifacts" / "find_result.json")
    spec_freeze = _spec_freeze_summary(run_dir)
    delivery_summary = _delivery_summary(run_dir)
    support_session_dir = _support_session_dir(run_dir, chat_id)
    summary: dict[str, Any] = {
        "schema_version": "ctcp-formal-benchmark-summary-v2",
        "benchmark_entry": _profile_entry(profile),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "benchmark_source": _benchmark_source_label(profile, benchmark_zip),
        "provider_summary": _provider_summary(),
        "run_dir": str(run_dir),
        "support_session_dir": str(support_session_dir) if support_session_dir else "",
        "workflow_id": find_result.get("selected_workflow_id") or find_result.get("workflow_id") or "",
        "project_generation_goal": bool((find_result.get("decision", {}) if isinstance(find_result.get("decision"), dict) else {}).get("project_generation_goal", False)),
        "project_domain": spec_freeze.get("project_domain", ""),
        "project_type": spec_freeze.get("project_type", ""),
        "project_archetype": spec_freeze.get("project_archetype", ""),
        "package_name": spec_freeze.get("package_name", ""),
        "spec_freeze": spec_freeze,
        "api_usage_summary": _api_summary(run_dir),
        "provider_ledger_summary": _provider_ledger_summary(run_dir),
        "source_generation_summary": _source_generation_summary(run_dir),
        "acceptance_summary": _acceptance_summary(run_dir),
        "verify_summary": _verify_summary(run_dir),
        "delivery_summary": delivery_summary,
        "replay_summary": delivery_summary["replay_summary"],
        "bundle_summary": _bundle_summary(run_dir),
        "extended_coverage_summary": _extended_summary(run_dir),
        "internal_runtime_status": delivery_summary.get("internal_runtime_status", ""),
        "user_acceptance_status": delivery_summary.get("user_acceptance_status", ""),
        "run_status": _run_status(run_dir),
        "repo_level_verify_note": "Benchmark PASS is reported separately from repo-level canonical verify; dirty worktree/module protection failures are separate repo gates.",
    }
    verdict, first_failure = _evaluate(profile, summary)
    summary["verdict"] = verdict
    summary["first_failure_point"] = first_failure
    return summary


def _find_transcript(run_dir: Path, profile: str) -> Path | None:
    candidates = [
        run_dir / f"{_profile_entry(profile)}_transcript.md",
        run_dir / "hq_repair_transcript.md",
    ]
    candidates.extend(sorted(run_dir.glob("*transcript*.md")))
    return next((path for path in candidates if path.exists()), None)


def _write_reconstructed_transcript(dest: Path, run_dir: Path, profile: str) -> None:
    if profile == "endurance":
        turns = [ENDURANCE_GOAL]
        source_note = "embedded_endurance_rough_goal"
    else:
        benchmark = _load_benchmark(DEFAULT_BENCHMARK_ZIP, None)
        turns = _turns_for_profile(profile, benchmark)
        source_note = "benchmark_scripted_turns_and_run_metadata"
    run = _read_json(run_dir / "RUN.json")
    lines = [
        f"# {_profile_entry(profile)} transcript",
        "",
        f"Source: reconstructed from {source_note} because this historical PASS run did not contain a dedicated transcript file.",
        "",
        f"- run_dir: `{run_dir}`",
        f"- run_goal: {run.get('goal', '')}",
        "",
    ]
    for idx, turn in enumerate(turns, start=1):
        lines.append(f"## Turn {idx}")
        lines.append("")
        lines.append("### User")
        lines.append(turn)
        lines.append("")
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _copy_screenshots(run_dir: Path, dest_dir: Path) -> list[str]:
    screenshot_root = run_dir / "project_output"
    matches = list(screenshot_root.glob("*/artifacts/screenshots/*.png"))
    copied: list[str] = []
    dest_dir.mkdir(parents=True, exist_ok=True)
    for src in sorted(matches):
        dst = dest_dir / src.name
        shutil.copy2(src, dst)
        copied.append(str(dst))
    return copied


def _write_markdown_summary(summary: dict[str, Any], dest: Path) -> None:
    provider = summary.get("provider_summary", {})
    api = summary.get("api_usage_summary", {})
    acceptance = summary.get("acceptance_summary", {})
    verify = summary.get("verify_summary", {})
    delivery = summary.get("delivery_summary", {})
    replay = summary.get("replay_summary", {})
    bundles = summary.get("bundle_summary", {})
    extended = summary.get("extended_coverage_summary", {})
    spec = summary.get("spec_freeze", {})
    lines = [
        f"# {summary.get('benchmark_entry', '')} summary",
        "",
        "## Provider",
        f"- provider: `{provider.get('provider', '')}`",
        f"- model: `{provider.get('model', '')}`",
        f"- base_url: `{provider.get('base_url', '')}`",
        f"- key_mask: `{provider.get('key_mask', '')}`",
        "",
        "## Run",
        f"- run_dir: `{summary.get('run_dir', '')}`",
        f"- support_session_dir: `{summary.get('support_session_dir', '')}`",
        f"- workflow_id: `{summary.get('workflow_id', '')}`",
        "",
        "## Freeze",
        f"- project_domain: `{spec.get('project_domain', '')}`",
        f"- project_type: `{spec.get('project_type', '')}`",
        f"- project_archetype: `{spec.get('project_archetype', '')}`",
        f"- package_name: `{spec.get('package_name', '')}`",
        "",
        "## Runtime",
        f"- api_calls_ok: `{api.get('ok', 0)}` / `{api.get('total', 0)}`",
        f"- api_coverage: `{dict(summary.get('provider_ledger_summary', {})).get('critical_api_step_count', 0)}` / `{dict(summary.get('provider_ledger_summary', {})).get('critical_step_count', 0)}`",
        f"- all_critical_steps_api: `{dict(summary.get('provider_ledger_summary', {})).get('all_critical_steps_api', False)}`",
        f"- acceptance_triplets_complete: `{acceptance.get('complete', False)}`",
        f"- verify: `{verify.get('result', '')}`",
        f"- delivery_completion_passed: `{delivery.get('completion_gate_passed', False)}`",
        f"- cold_replay_passed: `{delivery.get('cold_replay_passed', False)}`",
        f"- replay_overall_pass: `{replay.get('overall_pass', False)}`",
        f"- screenshot_count: `{extended.get('screenshot_count', 0)}`",
        "",
        "## Bundles",
        f"- final_bundle: `{bundles.get('final_project_bundle', '')}`",
        f"- evidence_bundle: `{bundles.get('intermediate_evidence_bundle', '')}`",
        "",
        "## Verdict",
        f"- internal_runtime_status: `{summary.get('internal_runtime_status', '')}`",
        f"- user_acceptance_status: `{summary.get('user_acceptance_status', '')}`",
        f"- final_verdict: `{summary.get('verdict', '')}`",
        f"- first_failure_point: `{summary.get('first_failure_point', '')}`",
        "",
    ]
    _write_text(dest, "\n".join(lines))


def archive_golden(profile: str, run_dir: Path, summary_json_path: Path, summary_md_path: Path | None, dest_root: Path) -> Path:
    dest = dest_root / _golden_dir_name(profile)
    dest.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema_version": "ctcp-benchmark-golden-v2",
        "profile": profile,
        "benchmark_entry": _profile_entry(profile),
        "source_run_dir": str(run_dir),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": {},
    }
    for src_rel, dest_name in PROFILE_GOLDEN_FILES[profile]:
        if src_rel == "transcript":
            transcript = _find_transcript(run_dir, profile)
            if transcript and transcript.exists():
                shutil.copy2(transcript, dest / dest_name)
                manifest["files"][dest_name] = {"present": True, "source": str(transcript)}
            else:
                _write_reconstructed_transcript(dest / dest_name, run_dir, profile)
                manifest["files"][dest_name] = {"present": True, "source": "reconstructed"}
            continue
        if src_rel == "screenshots":
            copied = _copy_screenshots(run_dir, dest / dest_name)
            manifest["files"][dest_name] = {"present": bool(copied), "source": "run screenshots", "copied": copied}
            continue
        src = run_dir / src_rel
        if not src.exists():
            manifest["files"][dest_name] = {"present": False, "source": str(src)}
            continue
        shutil.copy2(src, dest / dest_name)
        manifest["files"][dest_name] = {"present": True, "source": str(src)}
    summary_json_name = f"{_summary_basename(profile)}.json"
    summary_md_name = f"{_summary_basename(profile)}.md"
    shutil.copy2(summary_json_path, dest / summary_json_name)
    manifest["files"][summary_json_name] = {"present": True, "source": str(summary_json_path)}
    if summary_md_path and summary_md_path.exists():
        shutil.copy2(summary_md_path, dest / summary_md_name)
        manifest["files"][summary_md_name] = {"present": True, "source": str(summary_md_path)}
    _write_json(dest / "golden_manifest.json", manifest)
    return dest


def _default_summary_paths(profile: str, run_dir: Path, summary_out: Path | None) -> tuple[Path, Path]:
    if summary_out is not None:
        summary_json = summary_out
    else:
        summary_json = run_dir / f"{_summary_basename(profile)}.json"
    summary_md = summary_json.with_suffix(".md")
    return summary_json, summary_md


def _stdout_payload(summary: dict[str, Any], summary_json: Path, summary_md: Path, golden_dir: Path | None) -> dict[str, Any]:
    bundles = summary.get("bundle_summary", {})
    delivery = summary.get("delivery_summary", {})
    replay = summary.get("replay_summary", {})
    return {
        "summary_json": str(summary_json),
        "summary_md": str(summary_md),
        "golden_archive_dir": str(golden_dir) if golden_dir else "",
        "run_dir": summary.get("run_dir", ""),
        "support_session_dir": summary.get("support_session_dir", ""),
        "workflow_id": summary.get("workflow_id", ""),
        "project_domain": summary.get("project_domain", ""),
        "project_type": summary.get("project_type", ""),
        "project_archetype": summary.get("project_archetype", ""),
        "package_name": summary.get("package_name", ""),
        "final_verdict": summary.get("verdict", ""),
        "internal_runtime_status": summary.get("internal_runtime_status", ""),
        "user_acceptance_status": summary.get("user_acceptance_status", ""),
        "verify_result": summary.get("verify_summary", {}).get("result", ""),
        "delivery_completion_passed": delivery.get("completion_gate_passed", False),
        "cold_replay_passed": delivery.get("cold_replay_passed", False),
        "replay_overall_pass": replay.get("overall_pass", False),
        "final_bundle_path": bundles.get("final_project_bundle", ""),
        "evidence_bundle_path": bundles.get("intermediate_evidence_bundle", ""),
        "first_failure_point": summary.get("first_failure_point", ""),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run or summarize CTCP formal benchmarks.")
    parser.add_argument("--profile", choices=("basic", "hq", "endurance"), required=True)
    parser.add_argument("--mode", choices=("run", "summarize", "archive-golden"), default="run")
    parser.add_argument("--benchmark-zip", type=Path, default=DEFAULT_BENCHMARK_ZIP)
    parser.add_argument("--runs-root", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--chat-id")
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--golden-root", type=Path, default=ROOT / "artifacts" / "benchmark_goldens")
    args = parser.parse_args(argv)

    profile = args.profile
    run_dir = args.run_dir
    support_session_dir: Path | None = None
    if args.mode == "run":
        run_dir, support_session_dir = _run_profile(profile, args.benchmark_zip, args.runs_root, args.chat_id)
    if run_dir is None:
        raise SystemExit("--run-dir is required for summarize/archive-golden mode")
    run_dir = run_dir.resolve()
    summary = build_summary(profile, run_dir, args.benchmark_zip.resolve() if args.benchmark_zip else None, args.chat_id)
    if support_session_dir is not None:
        summary["support_session_dir"] = str(support_session_dir)
    summary_json, summary_md = _default_summary_paths(profile, run_dir, args.summary_out)
    _write_json(summary_json, summary)
    _write_markdown_summary(summary, summary_md)
    golden_dir: Path | None = None
    if args.mode == "archive-golden":
        golden_dir = archive_golden(profile, run_dir, summary_json, summary_md, args.golden_root)
        summary["golden_archive_dir"] = str(golden_dir)
        _write_json(summary_json, summary)
        _write_markdown_summary(summary, summary_md)
    print(json.dumps(_stdout_payload(summary, summary_json, summary_md, golden_dir), ensure_ascii=False))
    return 0 if summary["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
