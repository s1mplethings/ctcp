#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_dispatch


class ProviderSelectionTests(unittest.TestCase):
    def test_recipe_defaults_are_applied_when_config_missing(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "find_result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-find-result-v1",
                        "selected_workflow_id": "wf_project_generation_manifest",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)
            self.assertIsNotNone(cfg, msg)
            role_providers = cfg.get("role_providers", {})
            self.assertEqual(role_providers.get("librarian"), "api_agent")
            self.assertEqual(role_providers.get("contract_guardian"), "api_agent")
            self.assertEqual(role_providers.get("patchmaker"), "api_agent")
            self.assertEqual(role_providers.get("fixer"), "api_agent")

    def test_dispatch_config_overrides_recipe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "find_result.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-find-result-v1",
                        "selected_workflow_id": "wf_project_generation_manifest",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            (artifacts / "dispatch_config.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {
                            "patchmaker": "manual_outbox",
                        },
                        "budgets": {"max_outbox_prompts": 5},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)
            self.assertIsNotNone(cfg, msg)
            role_providers = cfg.get("role_providers", {})
            self.assertEqual(role_providers.get("patchmaker"), "api_agent")
            self.assertEqual(role_providers.get("librarian"), "api_agent")
            self.assertEqual(role_providers.get("contract_guardian"), "api_agent")

    def test_non_librarian_local_exec_provider_falls_back_to_api(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "dispatch_config.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "api_agent",
                        "role_providers": {
                            "librarian": "local_exec",
                            "contract_guardian": "local_exec",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)
            self.assertIsNotNone(cfg, msg)
            provider, note = ctcp_dispatch._resolve_provider(cfg, "contract_guardian", "review_contract")
            self.assertEqual(provider, "api_agent")
            self.assertIn("hard-locked role=contract_guardian", note)

    def test_formal_api_only_non_librarian_local_exec_fails_fast(self) -> None:
        cfg = {
            "schema_version": "ctcp-dispatch-config-v1",
            "mode": "manual_outbox",
            "role_providers": {
                "contract_guardian": "local_exec",
            },
        }
        with mock.patch.dict(os.environ, {"CTCP_FORMAL_API_ONLY": "1"}, clear=False):
            provider, note = ctcp_dispatch._resolve_provider(cfg, "contract_guardian", "review_contract")
        self.assertEqual(provider, "api_agent")
        self.assertIn("hard-locked role=contract_guardian", note)

    def test_librarian_manual_outbox_override_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "dispatch_config.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {
                            "librarian": "manual_outbox",
                            "patchmaker": "manual_outbox",
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)
            self.assertIsNotNone(cfg, msg)
            role_providers = cfg.get("role_providers", {})
            self.assertEqual(role_providers.get("librarian"), "api_agent")
            self.assertEqual(role_providers.get("patchmaker"), "api_agent")

    def test_mock_agent_mode_allows_mock_librarian_context_pack_provider(self) -> None:
        cfg = {
            "schema_version": "ctcp-dispatch-config-v1",
            "mode": "mock_agent",
            "role_providers": {
                "librarian": "mock_agent",
            },
        }
        provider, note = ctcp_dispatch._resolve_provider(cfg, "librarian", "context_pack")
        self.assertEqual(provider, "api_agent")
        self.assertIn("hard-locked role=librarian", note)

    def test_api_agent_preview_disabled_without_env_or_cmd(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "dispatch_config.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {
                            "contract_guardian": "api_agent",
                        },
                        "budgets": {"max_outbox_prompts": 5},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            run_doc = {"goal": "provider selection"}
            gate = {
                "state": "blocked",
                "owner": "Contract Guardian",
                "path": "reviews/review_contract.md",
                "reason": "waiting for review_contract.md",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "",
                    "OPENAI_BASE_URL": "",
                    "CTCP_OPENAI_API_KEY": "",
                    "CTCP_LOCAL_NOTES_PATH": str(run_dir / "missing_notes.md"),
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "SDDAI_AGENT_CMD": "",
                },
                clear=False,
            ):
                preview = ctcp_dispatch.dispatch_preview(run_dir, run_doc, gate)

            self.assertEqual(preview.get("provider"), "api_agent")
            self.assertEqual(preview.get("status"), "disabled")
            self.assertIn("missing env", str(preview.get("reason", "")))

    def test_force_provider_env_respects_hard_locked_librarian_role(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "file_request.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-file-request-v1",
                        "goal": "force provider local librarian",
                        "needs": [{"path": "README.md", "mode": "snippets", "line_ranges": [[1, 20]]}],
                        "budget": {"max_files": 8, "max_total_bytes": 200000},
                        "reason": "cover local librarian hard boundary",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            run_doc = {"goal": "force provider"}
            gate = {
                "state": "blocked",
                "owner": "Local Librarian",
                "path": "artifacts/context_pack.json",
                "reason": "waiting for context_pack.json",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "CTCP_FORCE_PROVIDER": "ollama_agent",
                    "OPENAI_API_KEY": "",
                    "SDDAI_AGENT_CMD": "",
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                },
                clear=False,
            ):
                def _fake_execute(*, repo_root: Path, run_dir: Path, request: dict[str, object], config: dict[str, object], guardrails_budgets: dict[str, str]) -> dict[str, object]:
                    del repo_root, config, guardrails_budgets
                    (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
                    (run_dir / "artifacts" / "context_pack.json").write_text(
                        json.dumps({"schema_version": "ctcp-context-pack-v1", "files": [], "omitted": [], "summary": "ok"}, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    self.assertEqual(str(request.get("role", "")), "librarian")
                    return {
                        "status": "executed",
                        "target_path": "artifacts/context_pack.json",
                        "provider_mode": "remote",
                        "model_name": "api-test-model",
                        "request_id": "req-test-1",
                    }

                with mock.patch.object(ctcp_dispatch.api_agent, "execute", side_effect=_fake_execute) as api_execute, mock.patch.object(
                    ctcp_dispatch.ollama_agent, "execute"
                ) as ollama_execute:
                    result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, ROOT)

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            self.assertEqual(result.get("provider"), "api_agent")
            self.assertEqual(result.get("chosen_provider"), "api_agent")
            self.assertTrue(str(result.get("provider_mode", "")).strip())
            self.assertEqual(result.get("model_name"), "api-test-model")
            self.assertIn("ignored CTCP_FORCE_PROVIDER=ollama_agent", str(result.get("note", "")))
            api_execute.assert_called_once()
            ollama_execute.assert_not_called()
            self.assertTrue((run_dir / "artifacts" / "context_pack.json").exists())

    def test_librarian_api_failure_does_not_fallback_to_local(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            run_doc = {"goal": "api failure should stay failed"}
            gate = {
                "state": "blocked",
                "owner": "Local Librarian",
                "path": "artifacts/context_pack.json",
                "reason": "waiting for context_pack.json",
            }
            with mock.patch.object(
                ctcp_dispatch.api_agent,
                "execute",
                return_value={
                    "status": "exec_failed",
                    "reason": "OpenAI API request failed: timeout",
                    "provider_mode": "remote",
                    "model_name": "api-test-model",
                },
            ) as api_execute, mock.patch.object(ctcp_dispatch.ollama_agent, "execute") as ollama_execute, mock.patch.object(
                ctcp_dispatch.local_exec, "execute"
            ) as local_exec_execute:
                result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, ROOT)

            self.assertEqual(result.get("status"), "exec_failed", msg=str(result))
            self.assertEqual(result.get("provider"), "api_agent")
            self.assertTrue(str(result.get("provider_mode", "")).strip())
            self.assertEqual(result.get("model_name"), "api-test-model")
            self.assertIn("timeout", str(result.get("reason", "")))
            api_execute.assert_called_once()
            ollama_execute.assert_not_called()
            local_exec_execute.assert_not_called()

    def test_formal_api_only_dispatch_writes_provider_mismatch_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            _cfg = {
                "schema_version": "ctcp-dispatch-config-v1",
                "mode": "manual_outbox",
                "role_providers": {
                    "contract_guardian": "manual_outbox",
                },
            }
            (artifacts / "dispatch_config.json").write_text(json.dumps(_cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            gate = {
                "state": "blocked",
                "owner": "Contract Guardian",
                "path": "reviews/review_contract.md",
                "reason": "waiting for review_contract.md",
            }
            with mock.patch.dict(os.environ, {"CTCP_FORMAL_API_ONLY": "1"}, clear=False):
                result = ctcp_dispatch.dispatch_once(run_dir, {"goal": "formal provider lock"}, gate, ROOT)

            self.assertEqual(result.get("provider"), "api_agent", msg=str(result))
            self.assertIn(str(result.get("status", "")), {"executed", "exec_failed"}, msg=str(result))
            self.assertEqual(result.get("provider"), "api_agent")
            ledger_path = run_dir / "artifacts" / "provider_ledger.jsonl"
            self.assertTrue(ledger_path.exists())
            rows = [json.loads(line) for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertTrue(rows)
            self.assertIn(rows[-1]["verdict"], {"api_executed", "failed"})
            self.assertEqual(rows[-1]["provider_used"], "api_agent")

    def test_dispatch_once_writes_step_meta(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            repo_root = run_dir / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

            plan_script = repo_root / "plan_stub.py"
            plan_script.write_text("print('Status: DRAFT\\n- step: test')\n", encoding="utf-8")
            run_doc = {"goal": "step meta"}
            gate = {
                "state": "blocked",
                "owner": "Chair/Planner",
                "path": "artifacts/PLAN_draft.md",
                "reason": "waiting for PLAN_draft.md",
            }

            with mock.patch.dict(
                os.environ,
                {
                    "CTCP_FORCE_PROVIDER": "api_agent",
                    "SDDAI_PLAN_CMD": f'"{sys.executable}" "{plan_script}"',
                    "SDDAI_AGENT_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "OPENAI_API_KEY": "",
                },
                clear=False,
            ):
                result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, repo_root)

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            step_meta_path = run_dir / "step_meta.jsonl"
            self.assertTrue(step_meta_path.exists())
            rows = [json.loads(x) for x in step_meta_path.read_text(encoding="utf-8").splitlines() if x.strip()]
            self.assertTrue(rows, msg="step_meta.jsonl should not be empty")
            last = rows[-1]
            self.assertEqual(last.get("provider"), "api_agent")
            self.assertEqual(last.get("role"), "chair")
            self.assertEqual(last.get("action"), "plan_draft")

    def test_dispatch_once_does_not_recover_contract_review_with_local_exec_after_api_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            repo_root = run_dir / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "dispatch_config.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "api_agent",
                        "role_providers": {
                            "contract_guardian": "api_agent",
                        },
                        "budgets": {"max_outbox_prompts": 5},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            run_doc = {"goal": "contract review retry"}
            gate = {
                "state": "blocked",
                "owner": "Contract Guardian",
                "path": "reviews/review_contract.md",
                "reason": "waiting for review_contract.md",
            }
            provider_calls: list[str] = []

            def _fake_execute_provider(
                provider: str,
                *,
                repo_root: Path,
                run_dir: Path,
                request: dict[str, object],
                config: dict[str, object],
                guardrails_budgets: dict[str, str],
            ) -> dict[str, object]:
                del repo_root, config, guardrails_budgets, request
                provider_calls.append(str(provider))
                if str(provider) == "api_agent":
                    return {
                        "status": "exec_failed",
                        "reason": "OpenAI API request failed: Remote end closed connection without response",
                    }
                if str(provider) == "local_exec":
                    target = run_dir / "reviews" / "review_contract.md"
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(
                        "# Contract Review\n\nVerdict: APPROVE\n\nBlocking Reasons:\n- none\n\nRequired Fix/Artifacts:\n- none\n",
                        encoding="utf-8",
                    )
                    return {
                        "status": "executed",
                        "target_path": "reviews/review_contract.md",
                        "provider_mode": "local",
                    }
                return {"status": "exec_failed", "reason": f"unexpected provider: {provider}"}

            with mock.patch.object(ctcp_dispatch.provider_runtime, "execute_provider", side_effect=_fake_execute_provider):
                result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, repo_root)

            self.assertEqual(result.get("status"), "exec_failed", msg=str(result))
            self.assertEqual(result.get("provider"), "api_agent")
            self.assertEqual(result.get("chosen_provider"), "api_agent")
            self.assertNotIn("auto_recovery", result)
            self.assertEqual(provider_calls, ["api_agent"])
            self.assertFalse((run_dir / "reviews" / "review_contract.md").exists())

    def test_derive_request_routes_analysis_and_guardrails_through_plan_draft_family(self) -> None:
        run_doc = {"goal": "analysis routing"}
        analysis_gate = {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/analysis.md",
            "reason": "waiting for analysis.md",
        }
        guardrails_gate = {
            "state": "blocked",
            "owner": "Chair/Planner",
            "path": "artifacts/guardrails.md",
            "reason": "waiting for guardrails.md",
        }

        analysis_req = ctcp_dispatch.derive_request(analysis_gate, run_doc)
        guardrails_req = ctcp_dispatch.derive_request(guardrails_gate, run_doc)

        self.assertIsInstance(analysis_req, dict)
        self.assertEqual(str(analysis_req.get("role", "")), "chair")
        self.assertEqual(str(analysis_req.get("action", "")), "plan_draft")
        self.assertEqual(str(analysis_req.get("target_path", "")), "artifacts/analysis.md")

        self.assertIsInstance(guardrails_req, dict)
        self.assertEqual(str(guardrails_req.get("role", "")), "chair")
        self.assertEqual(str(guardrails_req.get("action", "")), "plan_draft")
        self.assertEqual(str(guardrails_req.get("target_path", "")), "artifacts/guardrails.md")

    def test_dispatch_once_injects_shared_whiteboard_context_for_api_provider(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            repo_root = base / "repo"
            (repo_root / "docs").mkdir(parents=True, exist_ok=True)
            (repo_root / "docs" / "sample.md").write_text("support production whiteboard\n", encoding="utf-8")
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "dispatch_config.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "api_agent",
                        "role_providers": {"chair": "api_agent"},
                        "budgets": {"max_outbox_prompts": 8},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            run_doc = {"goal": "support production whiteboard sync"}
            gate = {
                "state": "blocked",
                "owner": "Chair/Planner",
                "path": "artifacts/PLAN_draft.md",
                "reason": "waiting for PLAN_draft.md",
            }
            captured: dict[str, object] = {}

            def _fake_execute(*, repo_root: Path, run_dir: Path, request: dict[str, object], config: dict[str, object], guardrails_budgets: dict[str, str]) -> dict[str, object]:
                target_path = run_dir / "artifacts" / "PLAN_draft.md"
                target_path.write_text("Status: DRAFT\n- step: test\n", encoding="utf-8")
                captured["request"] = request
                return {"status": "executed", "target_path": "artifacts/PLAN_draft.md"}

            with mock.patch.object(ctcp_dispatch.api_agent, "execute", side_effect=_fake_execute):
                result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, repo_root)

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            request = captured.get("request")
            self.assertIsInstance(request, dict)
            whiteboard = dict(request.get("whiteboard", {}))  # type: ignore[arg-type]
            self.assertEqual(str(whiteboard.get("path", "")), "artifacts/support_whiteboard.json")
            self.assertTrue(str(whiteboard.get("query", "")).strip())
            self.assertIsInstance(whiteboard.get("snapshot"), dict)

            wb_path = run_dir / "artifacts" / "support_whiteboard.json"
            self.assertTrue(wb_path.exists(), msg="whiteboard file should exist after dispatch")
            wb_doc = json.loads(wb_path.read_text(encoding="utf-8"))
            entries = wb_doc.get("entries", [])
            self.assertTrue(any(str(e.get("role", "")) == "chair" and str(e.get("kind", "")) == "dispatch_request" for e in entries))
            self.assertTrue(any(str(e.get("role", "")) == "chair" and str(e.get("kind", "")) == "dispatch_result" for e in entries))
            self.assertTrue(
                any(
                    str(e.get("role", "")) == "local_search" and str(e.get("kind", "")) == "dispatch_lookup"
                    for e in entries
                )
            )

    def test_manual_outbox_prompt_contains_shared_whiteboard_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            run_dir = base / "run"
            repo_root = base / "repo"
            (repo_root / "docs").mkdir(parents=True, exist_ok=True)
            (repo_root / "docs" / "sample.md").write_text("manual outbox whiteboard context\n", encoding="utf-8")
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "dispatch_config.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-dispatch-config-v1",
                        "mode": "manual_outbox",
                        "role_providers": {"chair": "manual_outbox", "librarian": "manual_outbox"},
                        "budgets": {"max_outbox_prompts": 8},
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            cfg, msg = ctcp_dispatch.load_dispatch_config(run_dir)
            self.assertIsNotNone(cfg, msg)
            self.assertEqual(cfg.get("role_providers", {}).get("librarian"), "api_agent")

            run_doc = {"goal": "manual outbox shared whiteboard"}
            gate = {
                "state": "blocked",
                "owner": "Chair/Planner",
                "path": "artifacts/PLAN_draft.md",
                "reason": "waiting for PLAN_draft.md",
            }
            result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, repo_root)
            self.assertEqual(result.get("status"), "executed", msg=str(result))
            self.assertEqual(result.get("provider"), "api_agent", msg=str(result))
            rel_path = str(result.get("target_path", "")).strip()
            self.assertEqual(rel_path, "artifacts/PLAN_draft.md", msg=str(result))
            prompt_path = run_dir / rel_path
            self.assertTrue(prompt_path.exists(), msg=str(prompt_path))
            prompt_text = prompt_path.read_text(encoding="utf-8", errors="replace")
            self.assertIn("Status:", prompt_text)


if __name__ == "__main__":
    unittest.main()

