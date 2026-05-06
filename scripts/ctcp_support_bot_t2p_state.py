#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.ctcp_support_bot_constants import (
    SUPPORT_EXPORTS_REL_DIR,
    SUPPORT_INBOX_REL_PATH,
    SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH,
    SUPPORT_SCAFFOLD_SOURCE_MODE,
    SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH,
)
from scripts.ctcp_support_bot_io import append_event, now_iso, write_json
from scripts.ctcp_support_bot_provider_runtime import read_json_doc
from scripts.ctcp_support_bot_public_delivery_core import _delivery_project_slug, _existing_path
from scripts.ctcp_support_bot_public_delivery_transport import _materialize_support_scaffold_project
from scripts.ctcp_support_bot_reply_utils import sanitize_inline_text
from scripts.ctcp_support_bot_session_state import _state_zone, current_project_brief, latest_generation_state


def interactive_reply_advance_steps(*, created: bool) -> int:
    return 4 if created else 1


def first_turn_project_generation_payload(
    *,
    user_text: str,
    create_goal: str,
    conversation_mode: str,
    session_state: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    mode = str(conversation_mode or "").strip().upper()
    goal_summary = (
        sanitize_inline_text(str(create_goal or user_text), max_chars=280)
        or sanitize_inline_text(current_project_brief(session_state), max_chars=280)
        or "Build a runnable project MVP with clear feature structure."
    )
    constraint_brief = sanitize_inline_text(
        str(_state_zone(session_state, "project_constraints_memory").get("constraint_brief", "")),
        max_chars=220,
    )
    project_intent: dict[str, Any] = {
        "goal_summary": goal_summary,
        "target_user": "project owner",
        "problem_to_solve": "deliver a runnable local MVP with clear evidence and interaction flow",
        "assumptions": [
            "first-turn run should prioritize concrete runnable output over generic placeholder skeleton",
        ],
    }
    if constraint_brief:
        project_intent["hard_constraints"] = [constraint_brief]
    constraints: dict[str, Any] = {
        "support_first_turn_quality_boost": True,
        "first_turn_quality_boost": True,
        "build_profile": "high_quality_extended",
        "product_depth": "extended",
        "required_pages": 8,
        "required_screenshots": 8,
        "require_feature_matrix": True,
        "require_page_map": True,
        "require_data_model_summary": True,
        "require_search": True,
        "require_import_or_export": "both",
        "require_dashboard_or_project_overview": True,
        "support_conversation_mode": mode,
    }
    return constraints, project_intent, {}


def _record_generation_state(
    generation_state: dict[str, Any],
    *,
    state_code: str,
    note: str = "",
) -> None:
    generation_state["current_state"] = sanitize_inline_text(state_code, max_chars=32) or "T0_PLAN"
    history = generation_state.get("state_history", [])
    if not isinstance(history, list):
        history = []
    history.append(
        {
            "state": sanitize_inline_text(state_code, max_chars=32),
            "ts": now_iso(),
            "note": sanitize_inline_text(note, max_chars=220),
        }
    )
    generation_state["state_history"] = history[-24:]


def _locate_latest_scaffold_report(run_dir: Path, scaffold_run_dir: Path | None) -> Path | None:
    candidates: list[Path] = []
    if scaffold_run_dir is not None:
        for name in ("scaffold_report.json", "scaffold_pointcloud_report.json"):
            path = scaffold_run_dir / "artifacts" / name
            if path.exists() and path.is_file():
                candidates.append(path.resolve())
    root = run_dir / "artifacts" / "support_scaffold_runs"
    if root.exists():
        for name in ("scaffold_report.json", "scaffold_pointcloud_report.json"):
            for path in root.rglob(name):
                if path.is_file():
                    candidates.append(path.resolve())
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)[0]


def _verify_t2p_chain_artifacts(
    *,
    support_run_dir: Path,
    out_dir: Path,
    scaffold_run_dir: Path | None,
    source: str,
) -> tuple[list[dict[str, str]], str, str, str]:
    checked: list[dict[str, str]] = []
    first_failure_stage = "none"
    first_failure_reason = ""

    def record(path_label: str, ok: bool, *, stage_on_fail: str, na: bool = False, reason: str = "") -> None:
        nonlocal first_failure_stage, first_failure_reason
        status = "N/A" if na else ("PASS" if ok else "FAIL")
        row: dict[str, str] = {"path": path_label, "status": status}
        if reason:
            row["reason"] = sanitize_inline_text(reason, max_chars=220)
        checked.append(row)
        if (not na) and (not ok) and first_failure_stage == "none":
            first_failure_stage = stage_on_fail
            first_failure_reason = sanitize_inline_text(reason or f"missing {path_label}", max_chars=220)

    record(str(out_dir), out_dir.exists() and out_dir.is_dir(), stage_on_fail="scaffold failure", reason="output project directory")
    manifest_ok = (out_dir / "manifest.json").exists() or (out_dir / "meta" / "manifest.json").exists()
    record("manifest.json|meta/manifest.json", manifest_ok, stage_on_fail="artifact missing", reason="project manifest")
    if SUPPORT_SCAFFOLD_SOURCE_MODE == "live-reference":
        record("meta/reference_source.json", (out_dir / "meta" / "reference_source.json").exists(), stage_on_fail="artifact missing", reason="reference source metadata")
    else:
        record("meta/reference_source.json", ok=True, stage_on_fail="artifact missing", na=True)

    record(str(support_run_dir), support_run_dir.exists() and support_run_dir.is_dir(), stage_on_fail="orchestration failure")
    record("TRACE.md", (support_run_dir / "TRACE.md").exists(), stage_on_fail="artifact missing")
    record("events.jsonl", (support_run_dir / "events.jsonl").exists(), stage_on_fail="artifact missing")

    dialogue_enabled = str(source or "").strip().lower() in {"telegram", "stdin", "selftest"}
    inbox_path = support_run_dir / SUPPORT_INBOX_REL_PATH
    if dialogue_enabled:
        record(SUPPORT_INBOX_REL_PATH.as_posix(), inbox_path.exists(), stage_on_fail="artifact missing", reason="dialogue capture artifact")
    else:
        record(SUPPORT_INBOX_REL_PATH.as_posix(), ok=True, stage_on_fail="artifact missing", na=True)

    scaffold_report = _locate_latest_scaffold_report(support_run_dir, scaffold_run_dir)
    report_label = str(scaffold_report) if scaffold_report is not None else "artifacts/scaffold_report.json|artifacts/scaffold_pointcloud_report.json"
    record(report_label, scaffold_report is not None, stage_on_fail="artifact missing", reason="scaffold report artifact")

    core_exists = any(
        [
            (out_dir / "README.md").exists(),
            (out_dir / "src").exists(),
            (out_dir / "main.py").exists(),
            (out_dir / "main.ts").exists(),
            (out_dir / "index.js").exists(),
        ]
    )
    record("README.md|src/|main entry", core_exists, stage_on_fail="invalid output", reason="core generated file")
    pass_fail = "PASS" if first_failure_stage == "none" else "FAIL"
    concise_reason = "Ingress accepted and scaffold artifacts are complete." if pass_fail == "PASS" else first_failure_reason
    return checked, pass_fail, first_failure_stage, concise_reason


def run_t2p_state_machine(
    *,
    run_dir: Path,
    session_state: dict[str, Any],
    user_text: str,
    source: str,
    conversation_mode: str,
    delivery_state: dict[str, Any] | None,
) -> dict[str, Any]:
    generation_state = latest_generation_state(session_state)
    trigger_text = sanitize_inline_text(user_text, max_chars=280)
    generation_state["last_trigger_text"] = trigger_text
    generation_state["last_trigger_ts"] = now_iso()
    generation_state["last_mode"] = sanitize_inline_text(conversation_mode, max_chars=40)

    _record_generation_state(generation_state, state_code="T0_PLAN", note="bind sanity task + out_dir")
    project_name_hint = _delivery_project_slug(
        str((delivery_state or {}).get("project_name_hint", "")).strip() or current_project_brief(session_state)
    )
    out_dir = (run_dir / SUPPORT_EXPORTS_REL_DIR / f"{project_name_hint}_ctcp_project").resolve()
    input_message = trigger_text or "Generate a minimal runnable project scaffold."

    _record_generation_state(generation_state, state_code="T1_INPUT", note="capture one minimal input")
    mode = "telegram_ingress_sanity" if str(source or "").strip().lower() == "telegram" else "fallback_generation"
    command_or_entry = "telegram_message_ingress" if mode == "telegram_ingress_sanity" else "ctcp_orchestrate scaffold entry"
    generation_state["last_test_mode"] = mode
    generation_state["last_command_or_entry"] = sanitize_inline_text(command_or_entry, max_chars=120)
    generation_state["last_out_dir"] = str(out_dir)

    _record_generation_state(generation_state, state_code="T2_ROUTE", note=mode)
    _record_generation_state(generation_state, state_code="T3_EXECUTE", note="trigger scaffold generation")

    execute_error = ""
    scaffold_dir: Path | None = None
    try:
        exec_delivery_state = dict(delivery_state) if isinstance(delivery_state, dict) else {}
        exec_delivery_state["project_name_hint"] = project_name_hint
        scaffold_dir = _materialize_support_scaffold_project(run_dir=run_dir, delivery_state=exec_delivery_state)
    except Exception as exc:
        execute_error = sanitize_inline_text(str(exc), max_chars=220) or "state machine execute failed"

    materialization_doc = read_json_doc(run_dir / SUPPORT_SCAFFOLD_MATERIALIZATION_REL_PATH) or {}
    scaffold_run_dir_text = str(materialization_doc.get("run_dir", "")).strip()
    scaffold_run_dir = _existing_path(scaffold_run_dir_text) if scaffold_run_dir_text else None
    generation_state["last_run_dir"] = scaffold_run_dir_text or str(run_dir)

    _record_generation_state(generation_state, state_code="T4_VERIFY", note="verify required artifacts")
    checked_artifacts: list[dict[str, str]] = []
    pass_fail = "FAIL"
    failure_stage = "scaffold failure"
    concise_reason = execute_error or sanitize_inline_text(str(materialization_doc.get("error", "")), max_chars=220)
    target_out_dir = scaffold_dir if isinstance(scaffold_dir, Path) else out_dir
    if scaffold_dir is not None and scaffold_dir.exists():
        checked_artifacts, pass_fail, failure_stage, concise_reason = _verify_t2p_chain_artifacts(
            support_run_dir=run_dir,
            out_dir=target_out_dir,
            scaffold_run_dir=scaffold_run_dir,
            source=source,
        )
    elif not concise_reason:
        concise_reason = "scaffold output directory missing"

    _record_generation_state(generation_state, state_code="T5_REPORT", note=f"{pass_fail}:{failure_stage}")
    report = {
        "schema_version": "ctcp-support-t2p-state-machine-report-v1",
        "ts": now_iso(),
        "test_name": "Low-token Telegram-to-Project Sanity Test",
        "state_machine": "T0->T1->T2->T3->T4->T5",
        "mode": mode,
        "input_message": input_message,
        "command_or_entry": command_or_entry,
        "out_dir": str(target_out_dir),
        "run_dir": scaffold_run_dir_text or str(run_dir),
        "checked_artifacts": checked_artifacts,
        "pass_fail": pass_fail,
        "failure_stage": failure_stage if pass_fail == "FAIL" else "none",
        "concise_reason": concise_reason or ("Ingress accepted and scaffold artifacts are complete." if pass_fail == "PASS" else ""),
        "trigger": {
            "source": sanitize_inline_text(source, max_chars=20),
            "conversation_mode": sanitize_inline_text(conversation_mode, max_chars=40),
            "user_text": trigger_text,
        },
        "materialization": {
            "out_dir": sanitize_inline_text(str(materialization_doc.get("out_dir", "")), max_chars=320),
            "run_dir": sanitize_inline_text(scaffold_run_dir_text, max_chars=320),
            "reused_existing": bool(materialization_doc.get("reused_existing", False)),
            "exit_code": int(materialization_doc.get("exit_code", 0) or 0),
            "error": sanitize_inline_text(str(materialization_doc.get("error", "")), max_chars=220),
        },
        "state_history": list(generation_state.get("state_history", [])),
    }
    write_json(run_dir / SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH, report)
    append_event(
        run_dir,
        "SUPPORT_T2P_STATE_MACHINE_REPORTED",
        SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix(),
        pass_fail=pass_fail,
        failure_stage=str(report.get("failure_stage", "")),
    )

    generation_state["last_report_ts"] = now_iso()
    generation_state["last_report_path"] = SUPPORT_T2P_STATE_MACHINE_REPORT_REL_PATH.as_posix()
    generation_state["last_pass_fail"] = pass_fail
    generation_state["last_failure_stage"] = str(report.get("failure_stage", ""))
    generation_state["last_concise_reason"] = sanitize_inline_text(str(report.get("concise_reason", "")), max_chars=220)
    generation_state["last_generated_project_dir"] = str(target_out_dir if target_out_dir.exists() else "")
    return report


__all__ = [
    "interactive_reply_advance_steps",
    "first_turn_project_generation_payload",
    "_record_generation_state",
    "_locate_latest_scaffold_report",
    "_verify_t2p_chain_artifacts",
    "run_t2p_state_machine",
]
