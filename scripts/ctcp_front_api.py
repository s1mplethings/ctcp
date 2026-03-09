#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from typing import Any

from ctcp_front_bridge import (
    BridgeError,
    ctcp_advance,
    ctcp_get_last_report,
    ctcp_get_status,
    ctcp_list_decisions_needed,
    ctcp_new_run,
    ctcp_submit_decision,
    ctcp_upload_artifact,
)


def _parse_json(text: str, *, fallback: Any) -> Any:
    raw = str(text or "").strip()
    if not raw:
        return fallback
    doc = json.loads(raw)
    return doc


def _print_json(doc: dict[str, Any]) -> None:
    print(json.dumps(doc, ensure_ascii=False, indent=2))


def _ok(result: Any) -> int:
    _print_json({"ok": True, "result": result})
    return 0


def _fail(msg: str, *, code: int = 1) -> int:
    _print_json({"ok": False, "error": msg})
    return code


def _cmd_new_run(args: argparse.Namespace) -> int:
    constraints = _parse_json(args.constraints_json, fallback={})
    if not isinstance(constraints, dict):
        return _fail("constraints_json must be a JSON object")
    result = ctcp_new_run(
        goal=str(args.goal),
        constraints=constraints,
        attachments=list(args.attachment or []),
    )
    return _ok(result)


def _cmd_get_status(args: argparse.Namespace) -> int:
    return _ok(ctcp_get_status(str(args.run_id or "")))


def _cmd_advance(args: argparse.Namespace) -> int:
    return _ok(ctcp_advance(str(args.run_id or ""), max_steps=int(args.max_steps or 1)))


def _cmd_get_last_report(args: argparse.Namespace) -> int:
    return _ok(ctcp_get_last_report(str(args.run_id or "")))


def _cmd_list_decisions(args: argparse.Namespace) -> int:
    return _ok(ctcp_list_decisions_needed(str(args.run_id or "")))


def _cmd_submit_decision(args: argparse.Namespace) -> int:
    if str(args.decision_json or "").strip():
        decision = _parse_json(args.decision_json, fallback={})
        if not isinstance(decision, dict):
            return _fail("decision_json must be a JSON object")
    else:
        content: Any = str(args.content or "")
        if str(args.content_json or "").strip():
            content = _parse_json(args.content_json, fallback={})
        decision = {
            "decision_id": str(args.decision_id or "").strip(),
            "prompt_path": str(args.prompt_path or "").strip(),
            "target_path": str(args.target_path or "").strip(),
            "content": content,
        }
    return _ok(ctcp_submit_decision(str(args.run_id or ""), decision))


def _cmd_upload_artifact(args: argparse.Namespace) -> int:
    payload: dict[str, Any] = {"source_path": str(args.file)}
    if str(args.dest_rel or "").strip():
        payload["dest_rel"] = str(args.dest_rel).strip()
    return _ok(ctcp_upload_artifact(str(args.run_id or ""), payload))


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Frontend-safe CTCP bridge API")
    sub = ap.add_subparsers(dest="cmd")

    p_new = sub.add_parser("ctcp_new_run", help="Create a new CTCP run via orchestrator")
    p_new.add_argument("--goal", required=True)
    p_new.add_argument("--constraints-json", default="{}")
    p_new.add_argument("--attachment", action="append", default=[])

    p_status = sub.add_parser("ctcp_get_status", help="Read CTCP run status")
    p_status.add_argument("--run-id", default="")

    p_advance = sub.add_parser("ctcp_advance", help="Advance CTCP run state")
    p_advance.add_argument("--run-id", default="")
    p_advance.add_argument("--max-steps", type=int, default=1)

    p_report = sub.add_parser("ctcp_get_last_report", help="Read CTCP report + verify summary")
    p_report.add_argument("--run-id", default="")

    p_decisions = sub.add_parser("ctcp_list_decisions_needed", help="List pending decisions for a run")
    p_decisions.add_argument("--run-id", default="")

    p_submit = sub.add_parser("ctcp_submit_decision", help="Submit a pending decision artifact")
    p_submit.add_argument("--run-id", default="")
    p_submit.add_argument("--decision-json", default="")
    p_submit.add_argument("--decision-id", default="")
    p_submit.add_argument("--prompt-path", default="")
    p_submit.add_argument("--target-path", default="")
    p_submit.add_argument("--content", default="")
    p_submit.add_argument("--content-json", default="")

    p_upload = sub.add_parser("ctcp_upload_artifact", help="Upload file to run_dir artifacts")
    p_upload.add_argument("--run-id", default="")
    p_upload.add_argument("--file", required=True)
    p_upload.add_argument("--dest-rel", default="")

    return ap


def main() -> int:
    ap = build_parser()
    args = ap.parse_args()
    cmd = str(args.cmd or "").strip()

    try:
        if cmd == "ctcp_new_run":
            return _cmd_new_run(args)
        if cmd == "ctcp_get_status":
            return _cmd_get_status(args)
        if cmd == "ctcp_advance":
            return _cmd_advance(args)
        if cmd == "ctcp_get_last_report":
            return _cmd_get_last_report(args)
        if cmd == "ctcp_list_decisions_needed":
            return _cmd_list_decisions(args)
        if cmd == "ctcp_submit_decision":
            return _cmd_submit_decision(args)
        if cmd == "ctcp_upload_artifact":
            return _cmd_upload_artifact(args)
        ap.print_help()
        return 1
    except BridgeError as exc:
        return _fail(str(exc))
    except json.JSONDecodeError as exc:
        return _fail(f"invalid json input: {exc}")
    except Exception as exc:
        return _fail(f"unexpected error: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
