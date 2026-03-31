from __future__ import annotations

import hashlib
import json
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


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _tiny_png_bytes() -> bytes:
    return bytes(
        [
            0x89,
            0x50,
            0x4E,
            0x47,
            0x0D,
            0x0A,
            0x1A,
            0x0A,
            0x00,
            0x00,
            0x00,
            0x0D,
            0x49,
            0x48,
            0x44,
            0x52,
            0x00,
            0x00,
            0x00,
            0x01,
            0x00,
            0x00,
            0x00,
            0x01,
            0x08,
            0x06,
            0x00,
            0x00,
            0x00,
            0x1F,
            0x15,
            0xC4,
            0x89,
            0x00,
            0x00,
            0x00,
            0x0A,
            0x49,
            0x44,
            0x41,
            0x54,
            0x78,
            0x9C,
            0x63,
            0x00,
            0x01,
            0x00,
            0x00,
            0x05,
            0x00,
            0x01,
            0x0D,
            0x0A,
            0x2D,
            0xB4,
            0x00,
            0x00,
            0x00,
            0x00,
            0x49,
            0x45,
            0x4E,
            0x44,
            0xAE,
            0x42,
            0x60,
            0x82,
        ]
    )


def _status_shape_ok(doc: dict[str, Any]) -> dict[str, bool]:
    required = [
        "run_status",
        "verify_result",
        "gate",
        "needs_user_decision",
        "decisions_needed_count",
        "latest_status_raw",
    ]
    return {key: key in doc for key in required}


def _stable_status_fingerprint(doc: dict[str, Any]) -> str:
    subset = {
        "run_status": doc.get("run_status", ""),
        "verify_result": doc.get("verify_result", ""),
        "verify_gate": doc.get("verify_gate", ""),
        "phase": doc.get("phase", ""),
        "needs_user_decision": doc.get("needs_user_decision", False),
        "decisions_needed_count": doc.get("decisions_needed_count", 0),
        "gate": doc.get("gate", {}),
        "blocking_reason": doc.get("blocking_reason", ""),
    }
    raw = json.dumps(subset, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8", errors="replace")).hexdigest()


def run_backend_interface_e2e() -> dict[str, Any]:
    out_root = ROOT / "artifacts" / "backend_interface_e2e"
    out_root.mkdir(parents=True, exist_ok=True)
    input_dir = out_root / "inputs"
    input_dir.mkdir(parents=True, exist_ok=True)

    brief = input_dir / "brief.txt"
    brief.write_text(
        "做一个极简单页网站，标题为 CTCP Demo，页面展示一句介绍文字，并展示上传的 logo。"
        "输出 HTML/CSS/README。若支持图片产物，请额外生成一张预览图或线框图。\n",
        encoding="utf-8",
    )
    logo = input_dir / "logo.png"
    logo.write_bytes(_tiny_png_bytes())

    goal = (
        "生成一个带图片输入和文件输出的单页项目。"
        "输入: brief.txt 和 logo.png。"
        "输出: index.html, styles.css, README.md，若支持图片输出则再给 preview/wireframe 图片。"
    )

    steps: dict[str, Any] = {}

    # Step 1: create_run
    req_create = {
        "goal": goal,
        "constraints": {
            "task_name": "backend_interface_e2e",
            "expected_outputs": ["index.html", "styles.css", "README.md"],
        },
        "attachments": [str(brief), str(logo)],
    }
    create_resp = bridge.create_run(
        goal=req_create["goal"],
        constraints=req_create["constraints"],
        attachments=req_create["attachments"],
    )
    run_id = str(create_resp.get("run_id", ""))
    run_dir = Path(str(create_resp.get("run_dir", "")))
    steps["step1_create_run"] = {
        "request": req_create,
        "response": create_resp,
        "success": bool(run_id and run_dir.exists()),
    }

    # Step 2: upload_input_artifact
    up_text = bridge.upload_input_artifact(run_id, str(brief))
    up_logo = bridge.upload_input_artifact(run_id, str(logo))
    text_dest = Path(str(up_text.get("dest_path", "")))
    logo_dest = Path(str(up_logo.get("dest_path", "")))
    steps["step2_upload_input_artifact"] = {
        "brief_upload": up_text,
        "logo_upload": up_logo,
        "brief_in_workspace": str(text_dest).startswith(str(run_dir)),
        "logo_in_workspace": str(logo_dest).startswith(str(run_dir)),
        "brief_exists": text_dest.exists(),
        "logo_exists": logo_dest.exists(),
    }

    # Step 3: create_run attachment association check
    frontend_request = {}
    frontend_request_path = run_dir / "artifacts" / "frontend_request.json"
    if frontend_request_path.exists():
        frontend_request = json.loads(frontend_request_path.read_text(encoding="utf-8"))
    request_attachments = list(frontend_request.get("attachments", [])) if isinstance(frontend_request, dict) else []
    steps["step3_attachment_association"] = {
        "frontend_request_path": str(frontend_request_path),
        "frontend_request_exists": frontend_request_path.exists(),
        "frontend_request_attachments_count": len(request_attachments),
        "frontend_request": frontend_request,
    }

    # Step 4: get_run_status
    status_1 = bridge.get_run_status(run_id)
    steps["step4_get_run_status"] = {
        "response": status_1,
        "shape_check": _status_shape_ok(status_1),
        "fingerprint": _stable_status_fingerprint(status_1),
    }

    # Step 5: get_support_context
    support_ctx = bridge.get_support_context(run_id)
    steps["step5_get_support_context"] = {
        "response": support_ctx,
        "has_status": isinstance(support_ctx.get("status"), dict),
        "has_decisions": isinstance(support_ctx.get("decisions"), dict),
        "has_goal": bool(str(support_ctx.get("goal", "")).strip()),
        "has_frontend_request": isinstance(support_ctx.get("frontend_request"), dict),
        "has_whiteboard": isinstance(support_ctx.get("whiteboard"), dict),
    }

    # Step 6: record_support_turn
    turn_text = "请继续执行当前任务，并在需要选择时明确提出问题。"
    turn_resp = bridge.record_support_turn(
        run_id,
        text=turn_text,
        source="support_bot",
        chat_id="backend-interface-e2e",
        conversation_mode="STATUS_QUERY",
    )
    steps["step6_record_support_turn"] = {
        "request": {
            "run_id": run_id,
            "text": turn_text,
            "source": "support_bot",
            "chat_id": "backend-interface-e2e",
            "conversation_mode": "STATUS_QUERY",
        },
        "response": turn_resp,
    }

    # Step 7: advance_run + status stability checks
    advances: list[dict[str, Any]] = []
    for idx in range(3):
        adv = bridge.advance_run(run_id, max_steps=1)
        s_a = bridge.get_run_status(run_id)
        s_b = bridge.get_run_status(run_id)
        advances.append(
            {
                "index": idx + 1,
                "advance": adv,
                "status_after_1": s_a,
                "status_after_2": s_b,
                "stable_fingerprint_1": _stable_status_fingerprint(s_a),
                "stable_fingerprint_2": _stable_status_fingerprint(s_b),
                "stable_same_poll": _stable_status_fingerprint(s_a) == _stable_status_fingerprint(s_b),
            }
        )
    steps["step7_advance_run"] = {"advances": advances}

    # Step 8: list_pending_decisions
    decisions_before = bridge.list_pending_decisions(run_id)
    fabricated = None
    if int(decisions_before.get("count", 0) or 0) <= 0:
        # only for proving decision path when not naturally triggered
        outbox = run_dir / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        fabricated = outbox / "manual_backend_interface_e2e.md"
        fabricated.write_text(
            "\n".join(
                [
                    "Role: chair/planner",
                    "Action: decide",
                    "Target-Path: artifacts/answers/manual_backend_interface_e2e.md",
                    "Reason: choose deliver order",
                    "Question: 先看截图还是先要压缩包？",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        decisions_before = bridge.list_pending_decisions(run_id)
    steps["step8_list_pending_decisions"] = {
        "response": decisions_before,
        "fabricated_prompt_path": str(fabricated) if fabricated else "",
    }

    # Step 9: submit_decision
    submit = {}
    submit_before_status = bridge.get_run_status(run_id)
    decision_rows = list(decisions_before.get("decisions", [])) if isinstance(decisions_before.get("decisions"), list) else []
    if decision_rows:
        chosen = dict(decision_rows[0])
        submit = bridge.submit_decision(
            run_id,
            {
                "decision_id": str(chosen.get("decision_id", "")),
                "content": "先给压缩包，再补截图预览。",
            },
        )
    submit_after_status = bridge.get_run_status(run_id)
    steps["step9_submit_decision"] = {
        "status_before": submit_before_status,
        "submit_response": submit,
        "status_after": submit_after_status,
        "submitted_not_consumed": bool(submit)
        and str(submit.get("decision_status", "")).strip().lower() == "submitted"
        and (not bool(submit.get("backend_acknowledged", False))),
    }

    # Step 10: get_current_state_snapshot / get_render_state_snapshot
    current_iface = hasattr(bridge, "get_current_state_snapshot")
    render_iface = hasattr(bridge, "get_render_state_snapshot")
    current_resp: dict[str, Any] = {}
    render_resp: dict[str, Any] = {}
    current_err = ""
    render_err = ""
    if current_iface:
        try:
            current_resp = getattr(bridge, "get_current_state_snapshot")(run_id)
        except Exception as exc:  # pragma: no cover - runtime evidence only
            current_err = str(exc)
    if render_iface:
        try:
            render_resp = getattr(bridge, "get_render_state_snapshot")(run_id)
        except Exception as exc:  # pragma: no cover - runtime evidence only
            render_err = str(exc)
    steps["step10_state_snapshots"] = {
        "get_current_state_snapshot_exists": current_iface,
        "get_render_state_snapshot_exists": render_iface,
        "get_current_state_snapshot_response": current_resp,
        "get_render_state_snapshot_response": render_resp,
        "get_current_state_snapshot_error": current_err,
        "get_render_state_snapshot_error": render_err,
    }

    # Step 11: get_last_report
    report = bridge.get_last_report(run_id)
    steps["step11_get_last_report"] = {"response": report}

    # Step 12/13/14: output artifact APIs
    list_iface = hasattr(bridge, "list_output_artifacts")
    meta_iface = hasattr(bridge, "get_output_artifact_meta")
    read_iface = hasattr(bridge, "read_output_artifact")
    list_resp: dict[str, Any] = {}
    list_err = ""
    output_rows: list[dict[str, Any]] = []
    if list_iface:
        try:
            list_resp = getattr(bridge, "list_output_artifacts")(run_id)
            if isinstance(list_resp.get("artifacts"), list):
                output_rows = [dict(item) for item in list_resp.get("artifacts", []) if isinstance(item, dict)]
        except Exception as exc:  # pragma: no cover
            list_err = str(exc)
    if (not list_iface) or bool(list_err):
        # fallback evidence only when formal listing is missing/unavailable
        fallback_rows: list[dict[str, Any]] = []
        for p in run_dir.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(run_dir).as_posix()
            if rel.endswith("/"):
                continue
            fallback_rows.append({"rel_path": rel, "size_bytes": int(p.stat().st_size)})
        output_rows = fallback_rows

    targeted = [
        row
        for row in output_rows
        if str(row.get("rel_path", "")).endswith("index.html")
        or str(row.get("rel_path", "")).endswith("styles.css")
        or str(row.get("rel_path", "")).endswith("README.md")
    ]
    image_rows = [
        row
        for row in output_rows
        if str(row.get("rel_path", "")).lower().endswith(".png")
        or str(row.get("rel_path", "")).lower().endswith(".jpg")
        or str(row.get("rel_path", "")).lower().endswith(".jpeg")
        or str(row.get("rel_path", "")).lower().endswith(".webp")
    ]

    meta_checks: list[dict[str, Any]] = []
    read_checks: list[dict[str, Any]] = []
    sample_rows = []
    if targeted:
        sample_rows.append(targeted[0])
    if image_rows:
        sample_rows.append(image_rows[0])
    if not sample_rows and output_rows:
        sample_rows.extend(output_rows[:2])
    for row in sample_rows:
        rel = str(row.get("rel_path", ""))
        one_meta: dict[str, Any] = {"rel_path": rel, "interface_exists": meta_iface}
        one_read: dict[str, Any] = {"rel_path": rel, "interface_exists": read_iface}
        if meta_iface:
            try:
                one_meta["response"] = getattr(bridge, "get_output_artifact_meta")(run_id, rel)
            except Exception as exc:  # pragma: no cover
                one_meta["error"] = str(exc)
        if read_iface:
            try:
                one_read["response"] = getattr(bridge, "read_output_artifact")(run_id, rel)
            except Exception as exc:  # pragma: no cover
                one_read["error"] = str(exc)
        if not read_iface:
            p = run_dir / rel
            if p.exists():
                if p.suffix.lower() in {".html", ".css", ".md", ".txt", ".json"}:
                    one_read["fallback_preview"] = p.read_text(encoding="utf-8", errors="replace")[:400]
                else:
                    one_read["fallback_bytes"] = int(p.stat().st_size)
        meta_checks.append(one_meta)
        read_checks.append(one_read)

    steps["step12_list_output_artifacts"] = {
        "interface_exists": list_iface,
        "interface_response": list_resp,
        "interface_error": list_err,
        "fallback_used": not list_iface or bool(list_err),
        "fallback_count": len(output_rows),
        "target_output_files_found": [row.get("rel_path", "") for row in targeted],
        "image_outputs_found": [row.get("rel_path", "") for row in image_rows],
    }
    steps["step13_get_output_artifact_meta"] = {
        "interface_exists": meta_iface,
        "checks": meta_checks,
    }
    steps["step14_read_output_artifact"] = {
        "interface_exists": read_iface,
        "checks": read_checks,
    }

    return {
        "task_name": "生成一个带图片输入和文件输出的单页项目",
        "inputs": {"brief_path": str(brief), "logo_path": str(logo)},
        "run_id": run_id,
        "run_dir": str(run_dir),
        "steps": steps,
    }


if __name__ == "__main__":
    report = run_backend_interface_e2e()
    out = ROOT / "artifacts" / "backend_interface_e2e" / "backend_interface_e2e_report.json"
    _write_json(out, report)
    print(json.dumps({"report_path": str(out), "run_id": report.get("run_id", "")}, ensure_ascii=False))
