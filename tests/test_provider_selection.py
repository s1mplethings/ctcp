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
                        "selected_workflow_id": "wf_orchestrator_only",
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
            self.assertEqual(role_providers.get("contract_guardian"), "local_exec")
            self.assertEqual(role_providers.get("librarian"), "local_exec")
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
                        "selected_workflow_id": "wf_orchestrator_only",
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
            self.assertEqual(role_providers.get("patchmaker"), "manual_outbox")
            self.assertEqual(role_providers.get("contract_guardian"), "local_exec")
            self.assertEqual(role_providers.get("librarian"), "local_exec")

    def test_local_exec_provider_is_preserved(self) -> None:
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
            role_providers = cfg.get("role_providers", {})
            self.assertEqual(role_providers.get("librarian"), "local_exec")
            self.assertEqual(role_providers.get("contract_guardian"), "local_exec")

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
            self.assertEqual(role_providers.get("librarian"), "local_exec")
            self.assertEqual(role_providers.get("patchmaker"), "manual_outbox")

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
                            "patchmaker": "api_agent",
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
                "owner": "PatchMaker",
                "path": "artifacts/diff.patch",
                "reason": "waiting for diff.patch",
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

    def test_force_provider_env_respects_hard_local_roles(self) -> None:
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
                    "CTCP_FORCE_PROVIDER": "api_agent",
                    "OPENAI_API_KEY": "",
                    "SDDAI_AGENT_CMD": "",
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                },
                clear=False,
            ):
                result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, ROOT)

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            self.assertEqual(result.get("provider"), "local_exec")
            self.assertIn("ignored CTCP_FORCE_PROVIDER=api_agent", str(result.get("note", "")))
            self.assertTrue((run_dir / "artifacts" / "context_pack.json").exists())

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
                        "role_providers": {"patchmaker": "api_agent"},
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
                "owner": "PatchMaker",
                "path": "artifacts/diff.patch",
                "reason": "waiting for diff.patch",
            }
            captured: dict[str, object] = {}

            def _fake_execute(*, repo_root: Path, run_dir: Path, request: dict[str, object], config: dict[str, object], guardrails_budgets: dict[str, str]) -> dict[str, object]:
                captured["request"] = request
                return {"status": "executed", "target_path": "artifacts/diff.patch"}

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
            self.assertTrue(any(str(e.get("role", "")) == "patchmaker" and str(e.get("kind", "")) == "dispatch_request" for e in entries))
            self.assertTrue(any(str(e.get("role", "")) == "patchmaker" and str(e.get("kind", "")) == "dispatch_result" for e in entries))
            self.assertTrue(any(str(e.get("role", "")) == "librarian" for e in entries))

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
                        "role_providers": {"patchmaker": "manual_outbox", "librarian": "manual_outbox"},
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
            self.assertEqual(cfg.get("role_providers", {}).get("librarian"), "local_exec")

            run_doc = {"goal": "manual outbox shared whiteboard"}
            gate = {
                "state": "blocked",
                "owner": "PatchMaker",
                "path": "artifacts/diff.patch",
                "reason": "waiting for diff.patch",
            }
            result = ctcp_dispatch.dispatch_once(run_dir, run_doc, gate, repo_root)
            self.assertEqual(result.get("status"), "outbox_created", msg=str(result))
            rel_path = str(result.get("path", "")).strip()
            self.assertTrue(rel_path.startswith("outbox/"), msg=str(result))
            prompt_path = run_dir / rel_path
            self.assertTrue(prompt_path.exists(), msg=str(prompt_path))
            prompt_text = prompt_path.read_text(encoding="utf-8", errors="replace")
            self.assertIn("Shared-Whiteboard:", prompt_text)
            self.assertIn("artifacts/support_whiteboard.json", prompt_text)
            self.assertIn("librarian_query", prompt_text)


if __name__ == "__main__":
    unittest.main()
