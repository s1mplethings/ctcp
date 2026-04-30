from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scripts.ctcp_support_bot as support_bot


def _write_provider_doc(run_dir: Path, reply_text: str, next_question: str = "") -> None:
    target = run_dir / support_bot.SUPPORT_REPLY_PROVIDER_REL_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "reply_text": reply_text,
                "next_question": next_question,
                "actions": [],
                "debug_notes": "",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class ProjectTurnMainlineContractTests(unittest.TestCase):
    def test_project_turn_uses_bridge_mainline_and_never_calls_support_fast_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_bridge_only_") as td:
            base_dir = Path(td)
            session_runs_root = base_dir / "support_runs_root"
            production_run = base_dir / "ctcp_runs" / "r-mainline"
            provider_reply = "项目已经绑定到正式 CTCP 主链，我继续按 bridge 状态推进。"

            def _fake_execute(*, provider, run_dir, request, config):  # type: ignore[no-untyped-def]
                del config
                self.assertEqual(provider, "api_agent")
                _write_provider_doc(run_dir, provider_reply)
                return {
                    "status": "executed",
                    "reason": "ok",
                    "target_path": str(request.get("target_path", "")),
                }

            sync_calls: list[dict[str, object]] = []

            def _fake_sync_support_turn(**kwargs: object) -> dict[str, object]:
                sync_calls.append(dict(kwargs))
                return {
                    "run_id": "r-mainline",
                    "run_dir": str(production_run),
                    "goal": "做一个走正式 CTCP 主链的项目",
                    "status": {
                        "run_status": "running",
                        "verify_result": "",
                        "needs_user_decision": False,
                        "decisions_needed_count": 0,
                        "gate": {"state": "open", "owner": "chair", "reason": "mainline active"},
                    },
                    "runtime_state": {"phase": "EXECUTE"},
                    "whiteboard": {"path": "artifacts/support_whiteboard.json", "snapshot": {"entry_count": 1, "entries": []}},
                    "current_snapshot": {"task_id": "r-mainline", "authoritative_stage": "EXECUTING"},
                    "render_snapshot": {"task_id": "r-mainline", "visible_state": "EXECUTING"},
                    "decisions": {"count": 0, "decisions": []},
                    "output_artifacts": {"count": 0, "artifacts": []},
                    "project_manifest": {},
                    "delivery_evidence": {},
                    "frontend_request": {"goal": "做一个走正式 CTCP 主链的项目"},
                    "created": {"run_id": "r-mainline", "run_dir": str(production_run)},
                    "recorded_turn": {"run_id": "r-mainline", "written_path": "artifacts/support_frontend_turns.jsonl"},
                    "advance": {"run_id": "r-mainline", "status": "advanced"},
                }

            config = {"mode": "manual_outbox", "role_providers": {"support_lead": "api_agent"}}
            with mock.patch.object(support_bot, "get_runs_root", return_value=session_runs_root), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ), mock.patch.object(
                support_bot, "load_dispatch_config", return_value=(config, "ok")
            ), mock.patch.object(
                support_bot, "execute_provider", side_effect=_fake_execute
            ), mock.patch.object(
                support_bot, "render_frontend_output", None
            ), mock.patch.object(
                support_bot, "run_t2p_state_machine", side_effect=AssertionError("support fast path must stay disabled")
            ), mock.patch.object(
                support_bot.ctcp_front_bridge, "ctcp_sync_support_project_turn", side_effect=_fake_sync_support_turn
            ) as sync_spy:
                doc, support_session_dir = support_bot.process_message(
                    chat_id="bridge-only-demo",
                    user_text="帮我做一个项目，但这次必须走正式 CTCP 主链。",
                    source="stdin",
                )

        self.assertEqual(len(sync_calls), 1)
        self.assertEqual(str(sync_calls[0].get("create_goal", "")), "帮我做一个项目，但这次必须走正式 CTCP 主链。")
        constraints = sync_calls[0].get("constraints", {})
        self.assertTrue(isinstance(constraints, dict))
        self.assertTrue(bool(dict(constraints).get("support_first_turn_quality_boost", False)))
        self.assertEqual(int(sync_calls[0].get("advance_steps", 0) or 0), 4)
        self.assertEqual(str(doc.get("reply_text", "")), provider_reply)
        sync_spy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
