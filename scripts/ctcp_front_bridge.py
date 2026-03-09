#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
ORCHESTRATE_PATH = SCRIPTS_DIR / "ctcp_orchestrate.py"
LAST_RUN_POINTER = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"
REPORT_LAST = ROOT / "meta" / "reports" / "LAST.md"

STATUS_LINE_RE = re.compile(r"^\[ctcp_orchestrate\]\s*([^=]+)=(.*)$")

try:
    from tools.run_paths import get_repo_runs_root
except ModuleNotFoundError:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.run_paths import get_repo_runs_root


class BridgeError(RuntimeError):
    pass


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
        "exit_code": int(proc.returncode),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        doc = json.loads(_read_text(path))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    _write_text(path, json.dumps(doc, ensure_ascii=False, indent=2) + "\n")


def _tail_lines(text: str, max_lines: int = 80) -> str:
    rows = text.splitlines()
    if len(rows) <= max_lines:
        return text
    return "\n".join(rows[-max_lines:])


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _ensure_within_run_dir(run_dir: Path, candidate: Path) -> None:
    if not _is_within(candidate, run_dir):
        raise BridgeError(f"path escapes run_dir: {candidate}")


def _resolve_latest_run_dir() -> Path:
    raw = _read_text(LAST_RUN_POINTER).strip()
    if not raw:
        raise BridgeError("missing LAST_RUN pointer; create a run first")
    run_dir = Path(raw).expanduser().resolve()
    if not run_dir.exists():
        raise BridgeError(f"LAST_RUN pointer does not exist: {run_dir}")
    return run_dir


def _resolve_run_dir(run_id: str = "") -> Path:
    rid = str(run_id or "").strip()
    if not rid:
        return _resolve_latest_run_dir()

    direct = Path(rid).expanduser()
    if direct.is_absolute() and direct.exists():
        return direct.resolve()

    if direct.exists() and direct.is_dir():
        return direct.resolve()

    run_dir = (get_repo_runs_root(ROOT) / rid).resolve()
    if run_dir.exists():
        return run_dir
    raise BridgeError(f"run_id not found: {rid}")


def _run_id_from_dir(run_dir: Path) -> str:
    return run_dir.resolve().name


def _parse_status_output(stdout: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = STATUS_LINE_RE.match(line)
        if m:
            key = m.group(1).strip().lower().replace(" ", "_")
            out[key] = m.group(2).strip()
            continue
        if line.startswith("[ctcp_orchestrate] blocked:"):
            out["blocked"] = line.split(":", 1)[1].strip()
    return out


def _parse_outbox_prompt(path: Path) -> dict[str, str]:
    text = _read_text(path)
    out = {
        "role": "",
        "action": "",
        "target_path": "",
        "reason": "",
        "question_hint": "",
    }
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("Role:"):
            out["role"] = line.split(":", 1)[1].strip()
        elif line.startswith("Action:"):
            out["action"] = line.split(":", 1)[1].strip()
        elif line.startswith("Target-Path:"):
            out["target_path"] = line.split(":", 1)[1].strip()
        elif line.startswith("Reason:"):
            out["reason"] = line.split(":", 1)[1].strip()
        elif line.startswith("Question:"):
            out["question_hint"] = line.split(":", 1)[1].strip()
    return out


def _append_event(run_dir: Path, event: str, path: str = "", **extra: Any) -> None:
    row: dict[str, Any] = {
        "ts": _now_utc_iso(),
        "role": "frontend_bridge",
        "event": event,
        "path": path,
    }
    for key, value in extra.items():
        row[str(key)] = value
    events_path = run_dir / "events.jsonl"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _orchestrate_status(run_dir: Path) -> dict[str, Any]:
    cmd = [sys.executable, str(ORCHESTRATE_PATH), "status", "--run-dir", str(run_dir)]
    result = _run_cmd(cmd, ROOT)
    result["parsed"] = _parse_status_output(str(result.get("stdout", "")))
    return result


def ctcp_new_run(goal: str, constraints: dict[str, Any] | None = None, attachments: list[str] | None = None) -> dict[str, Any]:
    goal_text = str(goal or "").strip()
    if not goal_text:
        raise BridgeError("goal is required")

    cmd = [sys.executable, str(ORCHESTRATE_PATH), "new-run", "--goal", goal_text]
    created = _run_cmd(cmd, ROOT)
    if int(created.get("exit_code", 1)) != 0:
        raise BridgeError(f"ctcp_orchestrate new-run failed: {created.get('stderr', '').strip()}")

    run_dir = _resolve_latest_run_dir()
    run_id = _run_id_from_dir(run_dir)

    uploaded: list[dict[str, Any]] = []
    for item in attachments or []:
        uploaded.append(ctcp_upload_artifact(run_id, item))

    request_doc = {
        "schema_version": "ctcp-frontend-request-v1",
        "ts": _now_utc_iso(),
        "goal": goal_text,
        "constraints": constraints if isinstance(constraints, dict) else {},
        "attachments": uploaded,
    }
    _write_json(run_dir / "artifacts" / "frontend_request.json", request_doc)
    _append_event(run_dir, "FRONTEND_REQUEST_WRITTEN", "artifacts/frontend_request.json")

    status = ctcp_get_status(run_id)
    return {
        "run_id": run_id,
        "run_dir": str(run_dir),
        "created": created,
        "status": status,
    }


def ctcp_get_status(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    run_doc = _read_json(run_dir / "RUN.json")
    verify_doc = _read_json(run_dir / "artifacts" / "verify_report.json")
    status_cmd = _orchestrate_status(run_dir)
    parsed = status_cmd.get("parsed", {}) if isinstance(status_cmd.get("parsed"), dict) else {}
    decisions = ctcp_list_decisions_needed(_run_id_from_dir(run_dir))

    gate_state = str(parsed.get("next", "") or parsed.get("gate_state", "")).strip().lower()
    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "run_status": str(run_doc.get("status", "")).strip().lower(),
        "verify_result": str(verify_doc.get("result", "")).strip().upper(),
        "verify_gate": str(verify_doc.get("gate", "")).strip().lower(),
        "iterations": {
            "current": int(run_doc.get("verify_iterations", 0) or 0),
            "max": int(run_doc.get("max_iterations", 0) or 0),
            "source": str(run_doc.get("max_iterations_source", "")).strip(),
        },
        "gate": {
            "state": gate_state,
            "owner": str(parsed.get("owner", "")).strip(),
            "path": str(parsed.get("path", "")).strip(),
            "reason": str(parsed.get("reason", "") or parsed.get("blocked", "")).strip(),
        },
        "needs_user_decision": int(decisions.get("count", 0) or 0) > 0,
        "decisions_needed_count": int(decisions.get("count", 0) or 0),
        "latest_status_raw": {
            "exit_code": int(status_cmd.get("exit_code", 0) or 0),
            "stdout": str(status_cmd.get("stdout", "")),
            "stderr": str(status_cmd.get("stderr", "")),
        },
    }


def ctcp_advance(run_id: str, max_steps: int = 1) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    steps = max(1, min(int(max_steps or 1), 32))
    cmd = [
        sys.executable,
        str(ORCHESTRATE_PATH),
        "advance",
        "--run-dir",
        str(run_dir),
        "--max-steps",
        str(steps),
    ]
    result = _run_cmd(cmd, ROOT)
    status = ctcp_get_status(_run_id_from_dir(run_dir))
    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "max_steps": steps,
        "advance": result,
        "status": status,
    }


def ctcp_get_last_report(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    verify_report_path = run_dir / "artifacts" / "verify_report.json"
    report_text = _read_text(REPORT_LAST)
    trace_text = _read_text(run_dir / "TRACE.md")
    verify_doc = _read_json(verify_report_path)

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "repo_report_path": str(REPORT_LAST),
        "repo_report_exists": REPORT_LAST.exists(),
        "repo_report_tail": _tail_lines(report_text, max_lines=120),
        "trace_tail": _tail_lines(trace_text, max_lines=80),
        "verify_report_path": str(verify_report_path),
        "verify_report": verify_doc,
    }


def ctcp_list_decisions_needed(run_id: str = "") -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    outbox_dir = run_dir / "outbox"
    decisions: list[dict[str, Any]] = []

    for prompt in sorted(outbox_dir.glob("*.md")) if outbox_dir.exists() else []:
        parsed = _parse_outbox_prompt(prompt)
        target_rel = str(parsed.get("target_path", "")).strip()
        if not target_rel:
            continue
        target_abs = (run_dir / target_rel).resolve()
        _ensure_within_run_dir(run_dir, target_abs)
        if target_abs.exists():
            continue
        decision_id = f"outbox:{prompt.stem}"
        decisions.append(
            {
                "decision_id": decision_id,
                "kind": "outbox_prompt",
                "prompt_path": prompt.relative_to(run_dir).as_posix(),
                "role": str(parsed.get("role", "")).strip(),
                "action": str(parsed.get("action", "")).strip(),
                "target_path": target_rel,
                "reason": str(parsed.get("reason", "")).strip(),
                "question_hint": str(parsed.get("question_hint", "")).strip(),
            }
        )

    questions_path = run_dir / "QUESTIONS.md"
    if questions_path.exists():
        rows = [ln.strip() for ln in _read_text(questions_path).splitlines() if ln.strip()]
        for idx, row in enumerate(rows, start=1):
            if row.startswith("#"):
                continue
            if row.startswith("-"):
                row = row.lstrip("-").strip()
            if not row:
                continue
            decisions.append(
                {
                    "decision_id": f"questions:{idx}",
                    "kind": "questions_md",
                    "prompt_path": "QUESTIONS.md",
                    "role": "chair/planner",
                    "action": "question",
                    "target_path": "",
                    "reason": row,
                    "question_hint": row,
                }
            )

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "count": len(decisions),
        "decisions": decisions,
    }


def ctcp_submit_decision(run_id: str, decision: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise BridgeError("decision must be an object")

    run_dir = _resolve_run_dir(run_id)
    pending = ctcp_list_decisions_needed(_run_id_from_dir(run_dir)).get("decisions", [])
    if not isinstance(pending, list):
        pending = []

    decision_id = str(decision.get("decision_id", "")).strip()
    prompt_path = str(decision.get("prompt_path", "")).strip()
    target_path = str(decision.get("target_path", "")).strip()
    content = decision.get("content", "")

    selected: dict[str, Any] | None = None
    for row in pending:
        if not isinstance(row, dict):
            continue
        if decision_id and str(row.get("decision_id", "")).strip() == decision_id:
            selected = row
            break
        if prompt_path and str(row.get("prompt_path", "")).strip() == prompt_path:
            selected = row
            break
        if target_path and str(row.get("target_path", "")).strip() == target_path:
            selected = row
            break

    if selected is None:
        raise BridgeError("decision target not found in pending decision list")

    final_target = str(selected.get("target_path", "")).strip()
    if not final_target:
        raise BridgeError("selected decision has no writable target_path")

    target_abs = (run_dir / final_target).resolve()
    _ensure_within_run_dir(run_dir, target_abs)

    if isinstance(content, (dict, list)):
        payload = json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    else:
        payload = str(content or "")
        if final_target.lower().endswith(".json"):
            try:
                doc = json.loads(payload)
            except Exception as exc:
                raise BridgeError(f"decision content must be valid JSON for {final_target}: {exc}") from exc
            payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        elif not payload.endswith("\n"):
            payload += "\n"

    _write_text(target_abs, payload)
    _append_event(
        run_dir,
        "FRONT_DECISION_SUBMITTED",
        final_target,
        decision_id=str(selected.get("decision_id", "")),
        prompt_path=str(selected.get("prompt_path", "")),
    )

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "decision_id": str(selected.get("decision_id", "")),
        "target_path": final_target,
        "written": True,
        "remaining_decisions": int(ctcp_list_decisions_needed(_run_id_from_dir(run_dir)).get("count", 0)),
    }


def ctcp_upload_artifact(run_id: str, file: str | dict[str, Any]) -> dict[str, Any]:
    run_dir = _resolve_run_dir(run_id)
    if isinstance(file, dict):
        src_text = str(file.get("source_path", "")).strip()
        dest_rel = str(file.get("dest_rel", "")).strip()
    else:
        src_text = str(file or "").strip()
        dest_rel = ""

    if not src_text:
        raise BridgeError("file path is required")
    src = Path(src_text).expanduser().resolve()
    if not src.exists() or not src.is_file():
        raise BridgeError(f"upload file not found: {src}")

    if dest_rel:
        dest = (run_dir / dest_rel).resolve()
    else:
        dest = (run_dir / "artifacts" / "frontend_uploads" / src.name).resolve()
        dest_rel = dest.relative_to(run_dir).as_posix()
    _ensure_within_run_dir(run_dir, dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    _append_event(run_dir, "FRONT_ARTIFACT_UPLOADED", dest_rel, source=str(src))

    return {
        "run_id": _run_id_from_dir(run_dir),
        "run_dir": str(run_dir),
        "source_path": str(src),
        "dest_path": str(dest),
        "dest_rel": dest_rel,
        "size_bytes": int(dest.stat().st_size),
        "uploaded_at": _now_utc_iso(),
    }


__all__ = [
    "BridgeError",
    "ctcp_new_run",
    "ctcp_get_status",
    "ctcp_advance",
    "ctcp_get_last_report",
    "ctcp_list_decisions_needed",
    "ctcp_submit_decision",
    "ctcp_upload_artifact",
]
