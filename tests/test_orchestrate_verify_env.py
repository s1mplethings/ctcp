#!/usr/bin/env python3
from __future__ import annotations

import os
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

import ctcp_orchestrate


class OrchestrateVerifyEnvTests(unittest.TestCase):
    def test_verify_env_sanitizes_provider_and_live_api_by_default(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "CTCP_FORCE_PROVIDER": "mock_agent",
                "CTCP_MOCK_AGENT_FAULT_MODE": "missing_field",
                "CTCP_MOCK_AGENT_FAULT_ROLE": "patchmaker_make_patch",
                "CTCP_LIVE_API": "1",
                "OPENAI_API_KEY": "dummy",
                "CTCP_OPENAI_API_KEY": "dummy2",
            },
            clear=False,
        ):
            env = ctcp_orchestrate.verify_run_env()

        self.assertEqual(env.get("CTCP_SKIP_LITE_REPLAY"), "1")
        self.assertEqual(env.get("CTCP_FORCE_PROVIDER"), "")
        self.assertEqual(env.get("CTCP_MOCK_AGENT_FAULT_MODE"), "")
        self.assertEqual(env.get("CTCP_MOCK_AGENT_FAULT_ROLE"), "")
        self.assertEqual(env.get("CTCP_LIVE_API"), "")
        self.assertEqual(env.get("OPENAI_API_KEY"), "")
        self.assertEqual(env.get("CTCP_OPENAI_API_KEY"), "")

    def test_verify_env_keeps_live_api_opt_in(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "CTCP_VERIFY_ALLOW_LIVE_API": "1",
                "CTCP_LIVE_API": "1",
                "OPENAI_API_KEY": "dummy",
            },
            clear=False,
        ):
            env = ctcp_orchestrate.verify_run_env()

        self.assertEqual(env.get("CTCP_SKIP_LITE_REPLAY"), "1")
        self.assertEqual(env.get("CTCP_FORCE_PROVIDER"), "")
        self.assertNotIn("CTCP_LIVE_API", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CTCP_OPENAI_API_KEY", env)


if __name__ == "__main__":
    unittest.main()
