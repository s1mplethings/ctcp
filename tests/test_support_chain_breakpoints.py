from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_orchestrate
import scripts.ctcp_support_bot as support_bot
from test_support_to_production_path import _write_json, _write_provider_doc


class SupportChainBreakpointTests(unittest.TestCase):
    def test_current_gate_reads_librarian_failure_doc_without_blocked_reason(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_context_pack_failure_gate_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
            _write_json(run_dir / "RUN.json", {"status": "running", "goal": "context pack failure"})
            (run_dir / "artifacts" / "guardrails.md").write_text("find_mode: resolver_only\nmax_files: 5\nmax_total_bytes: 20000\nmax_iterations: 2\n", encoding="utf-8")
            (run_dir / "artifacts" / "analysis.md").write_text("# analysis\n", encoding="utf-8")
            _write_json(run_dir / "artifacts" / "find_result.json", {"schema_version": "ctcp-find-result-v1", "selected_workflow_id": "wf_orchestrator_only", "selected_version": "1.0", "candidates": [{"workflow_id": "wf_orchestrator_only", "version": "1.0", "score": 1.0, "why": "test"}]})
            _write_json(run_dir / "artifacts" / "file_request.json", {"schema_version": "ctcp-file-request-v1", "goal": "context pack failure", "needs": [{"path": "README.md", "mode": "full"}], "budget": {"max_files": 5, "max_total_bytes": 20000}, "reason": "test"})
            _write_json(run_dir / "artifacts" / "context_pack.failure.json", {"schema_version": "ctcp-context-pack-failure-v1", "status": "failed", "stage": "validate_request", "error_code": "invalid_schema", "message": "[ctcp_librarian] file_request schema_version must be ctcp-file-request-v1", "request_path": "artifacts/file_request.json", "target_path": "artifacts/context_pack.json", "failed_path": "", "details": {}})

            gate = ctcp_orchestrate.current_gate(run_dir, {"status": "running", "goal": "context pack failure"})

            self.assertEqual(str(gate.get("path", "")), "artifacts/context_pack.json")
            self.assertIn("ctcp-file-request-v1", str(gate.get("reason", "")))

    def test_current_gate_reads_plan_draft_step_meta_without_blocked_reason(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_plan_step_meta_gate_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
            _write_json(run_dir / "RUN.json", {"status": "running", "goal": "plan draft failure"})
            (run_dir / "artifacts" / "guardrails.md").write_text("find_mode: resolver_only\nmax_files: 5\nmax_total_bytes: 20000\nmax_iterations: 2\n", encoding="utf-8")
            (run_dir / "artifacts" / "analysis.md").write_text("# analysis\n", encoding="utf-8")
            _write_json(run_dir / "artifacts" / "find_result.json", {"schema_version": "ctcp-find-result-v1", "selected_workflow_id": "wf_orchestrator_only", "selected_version": "1.0", "candidates": [{"workflow_id": "wf_orchestrator_only", "version": "1.0", "score": 1.0, "why": "test"}]})
            _write_json(run_dir / "artifacts" / "file_request.json", {"schema_version": "ctcp-file-request-v1", "goal": "plan draft failure", "needs": [{"path": "README.md", "mode": "full"}], "budget": {"max_files": 5, "max_total_bytes": 20000}, "reason": "test"})
            _write_json(run_dir / "artifacts" / "context_pack.json", {"schema_version": "ctcp-context-pack-v1", "goal": "plan draft failure", "repo_slug": "ctcp", "summary": "test context", "files": [], "omitted": []})
            (run_dir / "step_meta.jsonl").write_text(json.dumps({"status": "exec_failed", "error": "provider reported executed but target missing: artifacts/PLAN_draft.md", "outputs": ["artifacts/PLAN_draft.md"]}, ensure_ascii=False) + "\n", encoding="utf-8")

            gate = ctcp_orchestrate.current_gate(run_dir, {"status": "running", "goal": "plan draft failure"})

            self.assertEqual(str(gate.get("path", "")), "artifacts/PLAN_draft.md")
            self.assertIn("target missing", str(gate.get("reason", "")))

    def test_plan_gate_generates_plan_draft_once_context_pack_exists(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_plan_gate_success_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
            _write_json(run_dir / "RUN.json", {"status": "running", "goal": "plan gate contract", "verify_iterations": 0, "max_iterations": 8, "max_iterations_source": "test"})
            (run_dir / "artifacts" / "guardrails.md").write_text("find_mode: resolver_only\nmax_files: 5\nmax_total_bytes: 20000\nmax_iterations: 2\n", encoding="utf-8")
            (run_dir / "artifacts" / "analysis.md").write_text("# analysis\n", encoding="utf-8")
            _write_json(run_dir / "artifacts" / "find_result.json", {"schema_version": "ctcp-find-result-v1", "selected_workflow_id": "wf_orchestrator_only", "selected_version": "1.0", "candidates": [{"workflow_id": "wf_orchestrator_only", "version": "1.0", "score": 1.0, "why": "test"}]})
            _write_json(run_dir / "artifacts" / "file_request.json", {"schema_version": "ctcp-file-request-v1", "goal": "plan gate contract", "needs": [{"path": "README.md", "mode": "full"}], "budget": {"max_files": 5, "max_total_bytes": 20000}, "reason": "test"})
            _write_json(run_dir / "artifacts" / "context_pack.json", {"schema_version": "ctcp-context-pack-v1", "goal": "plan gate contract", "repo_slug": "ctcp", "summary": "test context", "files": [], "omitted": []})
            _write_json(run_dir / "artifacts" / "dispatch_config.json", {"schema_version": "ctcp-dispatch-config-v1", "mode": "manual_outbox", "role_providers": {"chair": "mock_agent"}, "providers": {"mock_agent": {}}, "budgets": {"max_outbox_prompts": 20}})

            rc = ctcp_orchestrate.cmd_advance(run_dir, max_steps=1)

            self.assertEqual(rc, 0)
            self.assertTrue((run_dir / "artifacts" / "PLAN_draft.md").exists())
            gate = ctcp_orchestrate.current_gate(run_dir, json.loads((run_dir / "RUN.json").read_text(encoding="utf-8")))
            self.assertEqual(str(gate.get("path", "")), "reviews/review_contract.md")
            self.assertNotIn("context_pack.json", str(gate.get("reason", "")))
            self.assertNotIn("PLAN_draft.md", str(gate.get("reason", "")))

    def test_plan_gate_failure_becomes_explicit_blocker_instead_of_fake_running(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_plan_gate_fail_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "reviews").mkdir(parents=True, exist_ok=True)
            _write_json(run_dir / "RUN.json", {"status": "running", "goal": "plan gate failure contract", "verify_iterations": 0, "max_iterations": 8, "max_iterations_source": "test"})
            (run_dir / "artifacts" / "guardrails.md").write_text("find_mode: resolver_only\nmax_files: 5\nmax_total_bytes: 20000\nmax_iterations: 2\n", encoding="utf-8")
            (run_dir / "artifacts" / "analysis.md").write_text("# analysis\n", encoding="utf-8")
            _write_json(run_dir / "artifacts" / "find_result.json", {"schema_version": "ctcp-find-result-v1", "selected_workflow_id": "wf_orchestrator_only", "selected_version": "1.0", "candidates": [{"workflow_id": "wf_orchestrator_only", "version": "1.0", "score": 1.0, "why": "test"}]})
            _write_json(run_dir / "artifacts" / "file_request.json", {"schema_version": "ctcp-file-request-v1", "goal": "plan gate failure contract", "needs": [{"path": "README.md", "mode": "full"}], "budget": {"max_files": 5, "max_total_bytes": 20000}, "reason": "test"})
            _write_json(run_dir / "artifacts" / "context_pack.json", {"schema_version": "ctcp-context-pack-v1", "goal": "plan gate failure contract", "repo_slug": "ctcp", "summary": "test context", "files": [], "omitted": []})
            _write_json(run_dir / "artifacts" / "dispatch_config.json", {"schema_version": "ctcp-dispatch-config-v1", "mode": "manual_outbox", "role_providers": {"chair": "mock_agent"}, "providers": {"mock_agent": {"fault_mode": "drop_output", "fault_role": "chair_plan_draft"}}, "budgets": {"max_outbox_prompts": 20}})

            rc = ctcp_orchestrate.cmd_advance(run_dir, max_steps=1)

            self.assertEqual(rc, 0)
            self.assertFalse((run_dir / "artifacts" / "PLAN_draft.md").exists())
            run_doc = json.loads((run_dir / "RUN.json").read_text(encoding="utf-8"))
            self.assertEqual(str(run_doc.get("status", "")), "blocked")
            gate = ctcp_orchestrate.current_gate(run_dir, run_doc)
            self.assertEqual(str(gate.get("path", "")), "artifacts/PLAN_draft.md")
            self.assertIn("target missing", str(gate.get("reason", "")))

    def test_level4_empty_status_reply_syncs_latest_backend_truth_and_drops_stale_blocker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_truth_sync_") as td:
            run_dir = Path(td)
            _write_provider_doc(run_dir, "")
            _write_json(
                run_dir / "artifacts" / "support_runtime_state.json",
                {
                    "schema_version": "ctcp-support-runtime-state-v1",
                    "run_id": "r-truth-sync",
                    "run_dir": str(run_dir),
                    "phase": "RECOVER",
                    "run_status": "blocked",
                    "blocking_reason": "waiting for PLAN_draft.md",
                    "needs_user_decision": False,
                    "pending_decisions": [],
                    "decisions": [],
                    "latest_result": {"verify_result": "", "verify_gate": "", "iterations": {"current": 0, "max": 8, "source": "test"}, "gate": {}, "status_raw": {}},
                    "error": {"has_error": False, "code": "", "message": ""},
                    "recovery": {"needed": True, "hint": "retry planner to generate PLAN_draft.md", "status": "retry_ready"},
                    "gate": {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN_draft.md", "reason": "waiting for PLAN_draft.md"},
                    "iterations": {"current": 0, "max": 8, "source": "test"},
                    "verify_result": "",
                    "verify_gate": "",
                    "decisions_needed_count": 0,
                    "open_decisions_count": 0,
                    "submitted_decisions_count": 0,
                    "core_hash": "old-hash",
                    "updated_at": "2026-03-30T00:00:00Z",
                    "snapshot_source": "canonical_snapshot",
                },
            )
            (run_dir / support_bot.SUPPORT_INBOX_REL_PATH).parent.mkdir(parents=True, exist_ok=True)
            (run_dir / support_bot.SUPPORT_INBOX_REL_PATH).write_text(json.dumps({"ts": support_bot.now_iso(), "source": "telegram", "text": "现在进度到哪了？"}, ensure_ascii=False) + "\n", encoding="utf-8")

            blocked_context = {
                "run_id": "r-truth-sync",
                "goal": "剧情结构项目",
                "status": {"run_status": "running", "verify_result": "", "needs_user_decision": False, "decisions_needed_count": 0, "gate": {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN_draft.md", "reason": "waiting for PLAN_draft.md"}},
                "runtime_state": {"phase": "RECOVER", "run_status": "running", "verify_result": "", "blocking_reason": "waiting for PLAN_draft.md", "needs_user_decision": False, "pending_decisions": [], "error": {"has_error": False}, "gate": {"state": "blocked", "owner": "Chair/Planner", "path": "artifacts/PLAN_draft.md", "reason": "waiting for PLAN_draft.md"}, "recovery": {"needed": True, "hint": "retry planner to generate PLAN_draft.md", "status": "retry_ready"}},
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {"path": "artifacts/support_whiteboard.json", "hits": [], "snapshot": {}},
            }
            recovered_context = {
                "run_id": "r-truth-sync",
                "goal": "剧情结构项目",
                "status": {"run_status": "running", "verify_result": "", "needs_user_decision": False, "decisions_needed_count": 0, "gate": {"state": "open", "owner": "PatchMaker", "path": "artifacts/PLAN.md", "reason": "working"}},
                "runtime_state": {"phase": "EXECUTE", "run_status": "running", "verify_result": "", "blocking_reason": "none", "needs_user_decision": False, "pending_decisions": [], "error": {"has_error": False}, "gate": {"state": "open", "owner": "PatchMaker", "path": "artifacts/PLAN.md", "reason": "working"}, "recovery": {"needed": False, "hint": "", "status": "none"}},
                "decisions": {"count": 0, "decisions": []},
                "whiteboard": {"path": "artifacts/support_whiteboard.json", "hits": [], "snapshot": {}},
            }

            blocked_doc = support_bot.build_final_reply_doc(run_dir=run_dir, provider="api_agent", provider_result={"status": "executed", "reason": "ok"}, provider_doc={"reply_text": "", "next_question": "", "actions": [], "debug_notes": ""}, project_context=blocked_context, conversation_mode="STATUS_QUERY", task_summary_hint="剧情结构项目", lang_hint="zh")
            recovered_doc = support_bot.build_final_reply_doc(run_dir=run_dir, provider="api_agent", provider_result={"status": "executed", "reason": "ok"}, provider_doc={"reply_text": "", "next_question": "", "actions": [], "debug_notes": ""}, project_context=recovered_context, conversation_mode="STATUS_QUERY", task_summary_hint="剧情结构项目", lang_hint="zh")

            blocked_reply = str(blocked_doc.get("reply_text", ""))
            recovered_reply = str(recovered_doc.get("reply_text", ""))
            self.assertIn("PLAN_draft.md", blocked_reply)
            self.assertIn("方案整理", blocked_reply)
            self.assertNotIn("PLAN_draft.md", recovered_reply)
            self.assertNotIn("资料检索卡住", recovered_reply)
            self.assertNotIn("收到，我继续推进", recovered_reply)
            self.assertNotEqual(blocked_reply, recovered_reply)


if __name__ == "__main__":
    unittest.main()
