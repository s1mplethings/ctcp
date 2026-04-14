from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from frontend.delivery_reply_actions import evaluate_delivery_completion, inject_ready_delivery_actions
from scripts import ctcp_support_bot as support_bot
from scripts.support_public_delivery import build_public_delivery_transport, finalize_public_delivery_manifest


def _png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return path


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_virtual_delivery_e2e(base_dir: Path) -> dict[str, Any]:
    root = Path(base_dir).resolve()
    support_run_dir = root / "support-session"
    bound_run_dir = root / "runs" / "bound-story"
    project_dir = root / "generated_projects" / "story_organizer"
    for rel in ("docs", "meta/tasks", "scripts", "tests", "artifacts/screenshots"):
        (project_dir / rel).mkdir(parents=True, exist_ok=True)
    support_run_dir.mkdir(parents=True, exist_ok=True)
    (bound_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
    (project_dir / "README.md").write_text("# story_organizer\n\nRun: python app.py\n", encoding="utf-8")
    (project_dir / "app.py").write_text("print('story organizer')\n", encoding="utf-8")
    (project_dir / "manifest.json").write_text("{}\n", encoding="utf-8")
    (project_dir / "docs" / "00_CORE.md").write_text("# core\n", encoding="utf-8")
    (project_dir / "meta" / "tasks" / "CURRENT.md").write_text("# current\n", encoding="utf-8")
    (project_dir / "scripts" / "verify_repo.ps1").write_text("Write-Host ok\n", encoding="utf-8")
    (project_dir / "tests" / "test_smoke.py").write_text("def test_smoke():\n    assert True\n", encoding="utf-8")
    (project_dir / "artifacts" / "test_plan.json").write_text("{}\n", encoding="utf-8")
    (project_dir / "artifacts" / "test_cases.json").write_text("{}\n", encoding="utf-8")
    (project_dir / "artifacts" / "test_summary.md").write_text("# summary\n", encoding="utf-8")
    (project_dir / "artifacts" / "demo_trace.md").write_text("# demo\n", encoding="utf-8")
    final_ui = _png(project_dir / "artifacts" / "screenshots" / "final-ui.png")
    _png(project_dir / "artifacts" / "screenshots" / "overview.png")

    _write_json(
        bound_run_dir / "artifacts" / "patch_apply.json",
        {"touched_files": ["generated_projects/story_organizer/README.md"]},
    )
    (bound_run_dir / "artifacts" / "PLAN.md").write_text(
        "Status: SIGNED\nScope-Allow: generated_projects/story_organizer/\n",
        encoding="utf-8",
    )

    state = support_bot.default_support_session_state("virtual-e2e")
    state["bound_run_id"] = "run-story"
    state["bound_run_dir"] = str(bound_run_dir)
    support_bot.write_json(support_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH, state)
    support_bot.write_json(
        support_run_dir / support_bot.DISPATCH_CONFIG_REL_PATH,
        {
            **support_bot.default_support_dispatch_config(),
            "public_delivery": {"mode": "e2e_virtual_delivery"},
        },
    )

    project_context = {
        "run_id": "run-story",
        "run_dir": str(bound_run_dir),
        "status": {
            "run_status": "completed",
            "verify_result": "PASS",
            "needs_user_decision": False,
            "decisions_needed_count": 0,
            "gate": {"state": "closed", "owner": "", "reason": ""},
        },
    }
    with mock.patch.object(support_bot, "ROOT", root):
        delivery_state = support_bot.collect_public_delivery_state(
            session_state=state,
            project_context=project_context,
            source="telegram",
            support_run_dir=support_run_dir,
        )
        actions = inject_ready_delivery_actions(
            actions=[],
            project_context=project_context,
            delivery_state=delivery_state,
            source_hint="telegram",
        )
        config, _ = support_bot.load_dispatch_config(support_run_dir)
        transport = build_public_delivery_transport(config=config, run_dir=support_run_dir, live_transport=object())
        plan = support_bot.emit_public_delivery(
            transport,
            chat_id=123,
            run_dir=support_run_dir,
            actions=actions,
            delivery_state=delivery_state,
        )
        plan = finalize_public_delivery_manifest(
            run_dir=support_run_dir,
            actions=actions,
            plan=plan,
        )
    manifest_path = support_run_dir / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    completion_gate = evaluate_delivery_completion(
        actions,
        manifest,
        manifest_path=str(manifest_path),
        require_existing_files=True,
    )
    result = {
        "support_run_dir": str(support_run_dir),
        "bound_run_dir": str(bound_run_dir),
        "project_dir": str(project_dir),
        "manifest_path": str(manifest_path),
        "actions": actions,
        "delivery_state": delivery_state,
        "plan": plan,
        "completion_gate": completion_gate,
        "selected_photo": str(completion_gate.get("selected_photo", "")),
        "selected_document": str(completion_gate.get("selected_document", "")),
        "sent_types": sorted({str(item.get("type", "")) for item in manifest.get("sent", []) if isinstance(item, dict)}),
    }
    if {"send_project_package", "send_project_screenshot"} - {
        str(item.get("type", "")) for item in actions if isinstance(item, dict)
    }:
        raise RuntimeError(f"virtual delivery actions incomplete: {actions}")
    if not completion_gate.get("passed", False):
        raise RuntimeError(json.dumps(result, ensure_ascii=False, indent=2))
    if Path(str(completion_gate.get("selected_photo", ""))).name != final_ui.name:
        raise RuntimeError(f"expected high-value screenshot first, got {completion_gate.get('selected_photo', '')}")
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Run CTCP virtual delivery E2E")
    ap.add_argument("--json-out", default="", help="Optional summary output path")
    args = ap.parse_args()
    if args.json_out:
        out_path = Path(args.json_out).resolve()
        run_root = out_path.parent / "_virtual_delivery_e2e_run"
        if run_root.exists():
            import shutil

            shutil.rmtree(run_root)
        run_root.mkdir(parents=True, exist_ok=True)
        result = run_virtual_delivery_e2e(run_root)
        _write_json(out_path, result)
        return 0
    with tempfile.TemporaryDirectory(prefix="ctcp_virtual_delivery_e2e_") as td:
        result = run_virtual_delivery_e2e(Path(td))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
