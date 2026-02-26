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
            self.assertEqual(role_providers.get("contract_guardian"), "ollama_agent")
            self.assertEqual(role_providers.get("librarian"), "ollama_agent")
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
            self.assertEqual(role_providers.get("contract_guardian"), "ollama_agent")
            self.assertEqual(role_providers.get("librarian"), "ollama_agent")

    def test_legacy_local_exec_alias_maps_to_ollama_agent(self) -> None:
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
            self.assertEqual(role_providers.get("librarian"), "ollama_agent")
            self.assertEqual(role_providers.get("contract_guardian"), "ollama_agent")

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

    def test_force_provider_env_overrides_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
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
                preview = ctcp_dispatch.dispatch_preview(run_dir, run_doc, gate)

            self.assertEqual(preview.get("provider"), "api_agent")

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


if __name__ == "__main__":
    unittest.main()
