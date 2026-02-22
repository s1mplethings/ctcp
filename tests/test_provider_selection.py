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
                        "selected_workflow_id": "adlc_self_improve_core",
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
                        "selected_workflow_id": "adlc_self_improve_core",
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


if __name__ == "__main__":
    unittest.main()
