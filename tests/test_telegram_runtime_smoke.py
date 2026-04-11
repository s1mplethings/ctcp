from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_front_bridge
import ctcp_orchestrate
import scripts.ctcp_support_bot as support_bot


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _status_cmd_from_run(run_dir: Path) -> dict[str, object]:
    out = io.StringIO()
    with redirect_stdout(out):
        rc = ctcp_orchestrate.cmd_status(run_dir)
    return {
        "cmd": "python ctcp_orchestrate.py status",
        "exit_code": rc,
        "stdout": out.getvalue(),
        "stderr": "",
    }


class TelegramRuntimeSmokeTests(unittest.TestCase):
    def _setup_smoke_dirs(self, run_dir: Path, session_dir: Path) -> None:
        (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
        (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
        _write_json(
            run_dir / "RUN.json",
            {
                "status": "running",
                "goal": "剧情项目 smoke",
                "verify_iterations": 0,
                "max_iterations": 8,
                "max_iterations_source": "test",
            },
        )
        (run_dir / "artifacts" / "guardrails.md").write_text(
            "find_mode: resolver_only\nmax_files: 5\nmax_total_bytes: 20000\nmax_iterations: 2\n",
            encoding="utf-8",
        )
        _write_json(
            run_dir / "artifacts" / "find_result.json",
            {
                "schema_version": "ctcp-find-result-v1",
                "selected_workflow_id": "wf_orchestrator_only",
                "selected_version": "1.0",
                "candidates": [{"workflow_id": "wf_orchestrator_only", "version": "1.0", "score": 1.0, "why": "test"}],
            },
        )
        (session_dir / support_bot.SUPPORT_INBOX_REL_PATH).parent.mkdir(parents=True, exist_ok=True)
        (session_dir / support_bot.SUPPORT_INBOX_REL_PATH).write_text(
            json.dumps({"ts": support_bot.now_iso(), "source": "telegram", "text": "现在进度到哪了？"}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    def _fake_dispatch_execute(self, materialize_root: Path, **kwargs) -> dict[str, object]:  # type: ignore[no-untyped-def]
        request = dict(kwargs.get("request", {}))
        target_rel = str(request.get("target_path", ""))
        target = materialize_root / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target_rel.endswith("analysis.md"):
            target.write_text("# analysis\n", encoding="utf-8")
        elif target_rel.endswith("file_request.json"):
            _write_json(
                target,
                {
                    "schema_version": "ctcp-file-request-v1",
                    "goal": "剧情项目 smoke",
                    "needs": [{"path": "README.md", "mode": "full"}],
                    "budget": {"max_files": 5, "max_total_bytes": 20000},
                    "reason": "smoke",
                },
            )
        elif target_rel.endswith("context_pack.json"):
            _write_json(
                target,
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": "剧情项目 smoke",
                    "repo_slug": "ctcp",
                    "summary": "smoke context",
                    "files": [],
                    "omitted": [],
                },
            )
        elif target_rel.endswith("PLAN_draft.md"):
            target.write_text("Status: DRAFT\n- step: smoke\n", encoding="utf-8")
        else:
            raise AssertionError(f"unexpected smoke target: {target_rel}")
        return {
            "status": "executed",
            "provider": "api_agent",
            "chosen_provider": "api_agent",
            "provider_mode": "remote",
            "target_path": target_rel,
        }

    def _load_support_context(self, run_dir: Path) -> dict[str, object]:
        def _fake_run_cmd(cmd: list[str], cwd: Path) -> dict[str, object]:
            del cwd
            self.assertEqual(str(cmd[2]), "status")
            return _status_cmd_from_run(run_dir)

        with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
            ctcp_front_bridge, "_run_cmd", side_effect=_fake_run_cmd
        ):
            return ctcp_front_bridge.ctcp_get_support_context("r-smoke")

    def _build_status_reply(self, session_dir: Path, context: dict[str, object]) -> str:
        reply_doc = support_bot.build_final_reply_doc(
            run_dir=session_dir,
            provider="api_agent",
            provider_result={"status": "executed", "reason": "ok"},
            provider_doc={"reply_text": "", "next_question": "", "actions": [], "debug_notes": ""},
            project_context=context,
            conversation_mode="STATUS_QUERY",
            task_summary_hint="剧情项目 smoke",
            lang_hint="zh",
        )
        return str(reply_doc.get("reply_text", ""))

    def test_analysis_file_request_context_pack_plan_draft_progression_matches_user_visible_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_telegram_smoke_prod_") as prod_td, tempfile.TemporaryDirectory(
            prefix="ctcp_telegram_smoke_session_"
        ) as session_td:
            run_dir = Path(prod_td)
            session_dir = Path(session_td)
            self._setup_smoke_dirs(run_dir, session_dir)
            reply_markers = {
                "artifacts/file_request.json": ("需求清单", "需求整理", "file_request.json"),
                "artifacts/context_pack.json": ("context_pack.json", "资料检索"),
                "artifacts/PLAN_draft.md": ("PLAN_draft.md", "方案整理"),
            }
            observed_next_paths: list[str] = []
            observed_replies: list[str] = []

            with mock.patch.object(
                ctcp_orchestrate.ctcp_dispatch.core_router,
                "dispatch_execute",
                side_effect=lambda **kwargs: self._fake_dispatch_execute(materialize_root=run_dir, **kwargs),
            ):
                initial_gate = ctcp_orchestrate.current_gate(run_dir, json.loads((run_dir / "RUN.json").read_text(encoding="utf-8")))
                self.assertEqual(str(initial_gate.get("path", "")), "artifacts/analysis.md")
                for expected_next_path in ("artifacts/file_request.json", "artifacts/context_pack.json", "artifacts/PLAN_draft.md"):
                    self.assertEqual(ctcp_orchestrate.cmd_advance(run_dir, max_steps=1), 0)
                    context = self._load_support_context(run_dir)
                    gate = dict(context.get("status", {}).get("gate", {}))
                    observed_next_paths.append(str(gate.get("path", "")))
                    self.assertEqual(str(gate.get("path", "")), expected_next_path)
                    self.assertEqual(str(context.get("runtime_state", {}).get("blocking_reason", "")), f"waiting for {Path(expected_next_path).name}")
                    reply_text = self._build_status_reply(session_dir, context)
                    observed_replies.append(reply_text)
                    self.assertTrue(any(marker in reply_text for marker in reply_markers[expected_next_path]), msg=reply_text)

            self.assertEqual(observed_next_paths, ["artifacts/file_request.json", "artifacts/context_pack.json", "artifacts/PLAN_draft.md"])
            self.assertEqual(len(observed_replies), 3)


if __name__ == "__main__":
    unittest.main()
