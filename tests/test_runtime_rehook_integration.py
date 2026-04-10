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


class RuntimeRehookIntegrationTests(unittest.TestCase):
    def test_orchestrate_advance_calls_llm_core_dispatch_execute(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_rehook_orchestrate_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
            _write_json(
                run_dir / "RUN.json",
                {
                    "status": "running",
                    "goal": "runtime rehook orchestrate",
                    "verify_iterations": 0,
                    "max_iterations": 8,
                    "max_iterations_source": "test",
                },
            )
            (run_dir / "artifacts" / "guardrails.md").write_text(
                "find_mode: resolver_only\nmax_files: 5\nmax_total_bytes: 20000\nmax_iterations: 2\n",
                encoding="utf-8",
            )
            (run_dir / "artifacts" / "analysis.md").write_text("# analysis\n", encoding="utf-8")
            _write_json(
                run_dir / "artifacts" / "find_result.json",
                {
                    "schema_version": "ctcp-find-result-v1",
                    "selected_workflow_id": "wf_orchestrator_only",
                    "selected_version": "1.0",
                    "candidates": [{"workflow_id": "wf_orchestrator_only", "version": "1.0", "score": 1.0, "why": "test"}],
                },
            )
            _write_json(
                run_dir / "artifacts" / "file_request.json",
                {
                    "schema_version": "ctcp-file-request-v1",
                    "goal": "runtime rehook orchestrate",
                    "needs": [{"path": "README.md", "mode": "full"}],
                    "budget": {"max_files": 5, "max_total_bytes": 20000},
                    "reason": "test",
                },
            )
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": "runtime rehook orchestrate",
                    "repo_slug": "ctcp",
                    "summary": "test context",
                    "files": [],
                    "omitted": [],
                },
            )

            observed: list[dict[str, object]] = []

            def _fake_dispatch_execute(**kwargs):  # type: ignore[no-untyped-def]
                observed.append(dict(kwargs))
                target = run_dir / "artifacts" / "PLAN_draft.md"
                target.write_text("Status: DRAFT\n- step: runtime rehook\n", encoding="utf-8")
                return {
                    "status": "executed",
                    "provider": "api_agent",
                    "chosen_provider": "api_agent",
                    "provider_mode": "remote",
                    "target_path": "artifacts/PLAN_draft.md",
                }

            with mock.patch.object(ctcp_orchestrate.ctcp_dispatch.core_router, "dispatch_execute", side_effect=_fake_dispatch_execute):
                rc = ctcp_orchestrate.cmd_advance(run_dir, max_steps=1)

            self.assertEqual(rc, 0)
            self.assertEqual(len(observed), 1)
            request = dict(observed[0].get("request", {}))
            self.assertEqual(str(request.get("role", "")), "chair")
            self.assertEqual(str(request.get("action", "")), "plan_draft")
            self.assertEqual(str(request.get("target_path", "")), "artifacts/PLAN_draft.md")
            self.assertTrue((run_dir / "artifacts" / "PLAN_draft.md").exists())
            gate = ctcp_orchestrate.current_gate(run_dir, json.loads((run_dir / "RUN.json").read_text(encoding="utf-8")))
            self.assertEqual(str(gate.get("path", "")), "reviews/review_contract.md")

    def test_support_bot_execute_provider_uses_runtime_facade(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_rehook_support_") as td:
            run_dir = Path(td)
            request = {"role": "support_lead", "action": "reply", "target_path": "artifacts/support_reply.provider.json"}
            config = {"mode": "api_agent"}
            captured: list[dict[str, object]] = []

            def _fake_execute(provider, *, repo_root, run_dir, request, config, guardrails_budgets):  # type: ignore[no-untyped-def]
                captured.append(
                    {
                        "provider": provider,
                        "repo_root": repo_root,
                        "run_dir": run_dir,
                        "request": dict(request),
                        "config": dict(config),
                        "guardrails_budgets": dict(guardrails_budgets),
                    }
                )
                return {"status": "executed", "target_path": str(request.get("target_path", ""))}

            with mock.patch.object(support_bot.provider_runtime, "execute_provider", side_effect=_fake_execute):
                result = support_bot.execute_provider(
                    provider="api_agent",
                    run_dir=run_dir,
                    request=request,
                    config=config,
                )

            self.assertEqual(str(result.get("status", "")), "executed")
            self.assertEqual(len(captured), 1)
            self.assertEqual(str(captured[0]["provider"]), "api_agent")
            self.assertEqual(Path(str(captured[0]["repo_root"])).resolve(), ROOT.resolve())
            self.assertEqual(Path(str(captured[0]["run_dir"])).resolve(), run_dir.resolve())
            self.assertEqual(str(dict(captured[0]["request"]).get("role", "")), "support_lead")

    def test_front_bridge_status_uses_latest_backend_blocker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_runtime_rehook_bridge_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "support_runtime_state.json",
                {
                    "schema_version": "ctcp-support-runtime-state-v1",
                    "run_id": "r-runtime-sync",
                    "run_dir": str(run_dir),
                    "phase": "RECOVER",
                    "run_status": "blocked",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "needs_user_decision": False,
                    "pending_decisions": [],
                    "decisions": [],
                    "latest_result": {"verify_result": "", "verify_gate": "", "iterations": {"current": 0, "max": 8, "source": "test"}, "gate": {}, "status_raw": {}},
                    "error": {"has_error": False, "code": "", "message": ""},
                    "recovery": {"needed": True, "hint": "old retry", "status": "retry_ready"},
                    "gate": {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN_draft.md", "reason": "waiting for PLAN_draft.md"},
                    "iterations": {"current": 0, "max": 8, "source": "test"},
                    "verify_result": "",
                    "verify_gate": "",
                    "decisions_needed_count": 0,
                    "open_decisions_count": 0,
                    "submitted_decisions_count": 0,
                    "core_hash": "stale",
                    "updated_at": "2026-04-09T00:00:00Z",
                    "snapshot_source": "canonical_snapshot",
                },
            )

            def _fake_run_cmd(cmd: list[str], cwd: Path) -> dict[str, object]:
                del cwd
                self.assertEqual(str(cmd[2]), "status")
                stdout = "\n".join(
                    [
                        f"[ctcp_orchestrate] run_dir={run_dir}",
                        "[ctcp_orchestrate] run_status=running",
                        "[ctcp_orchestrate] next=blocked",
                        "[ctcp_orchestrate] owner=Chair/Planner",
                        "[ctcp_orchestrate] path=artifacts/file_request.json",
                        "[ctcp_orchestrate] reason=waiting for file_request.json",
                    ]
                )
                return {"cmd": " ".join(cmd), "exit_code": 0, "stdout": stdout + "\n", "stderr": ""}

            with mock.patch.object(ctcp_front_bridge, "_resolve_run_dir", return_value=run_dir), mock.patch.object(
                ctcp_front_bridge, "_run_cmd", side_effect=_fake_run_cmd
            ):
                status = ctcp_front_bridge.ctcp_get_status("r-runtime-sync")

            self.assertEqual(str(status.get("blocking_reason", "")), "waiting for file_request.json")
            runtime_state = dict(status.get("runtime_state", {}))
            self.assertEqual(str(runtime_state.get("blocking_reason", "")), "waiting for file_request.json")
            self.assertEqual(str(dict(status.get("gate", {})).get("path", "")), "artifacts/file_request.json")


if __name__ == "__main__":
    unittest.main()
