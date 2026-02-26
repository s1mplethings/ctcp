#!/usr/bin/env python3
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers import ollama_agent


class OllamaAgentTests(unittest.TestCase):
    def test_preview_returns_disabled_when_autostart_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.dict(
                os.environ,
                {"SDDAI_AGENT_CMD": "", "SDDAI_PLAN_CMD": "", "SDDAI_PATCH_CMD": ""},
                clear=False,
            ):
                with mock.patch.object(
                    ollama_agent,
                    "_ensure_ollama_ready",
                    return_value=(False, "bootstrap failed"),
                ) as ensure_ready:
                    with mock.patch.object(ollama_agent.api_agent, "preview") as api_preview:
                        out = ollama_agent.preview(run_dir=run_dir, request={}, config={})

            self.assertEqual(out.get("status"), "disabled", msg=str(out))
            self.assertIn("bootstrap failed", str(out.get("reason", "")))
            self.assertEqual(out.get("runtime"), "ollama")
            ensure_ready.assert_called_once()
            api_preview.assert_not_called()

    def test_preview_skips_bootstrap_when_custom_cmd_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.dict(
                os.environ,
                {"SDDAI_AGENT_CMD": "echo custom", "SDDAI_PLAN_CMD": "", "SDDAI_PATCH_CMD": ""},
                clear=False,
            ):
                with mock.patch.object(ollama_agent, "_ensure_ollama_ready") as ensure_ready:
                    with mock.patch.object(
                        ollama_agent.api_agent,
                        "preview",
                        return_value={"status": "can_exec"},
                    ) as api_preview:
                        out = ollama_agent.preview(run_dir=run_dir, request={}, config={})

            self.assertEqual(out.get("status"), "can_exec", msg=str(out))
            self.assertEqual(out.get("runtime"), "ollama")
            ensure_ready.assert_not_called()
            api_preview.assert_called_once()

    def test_execute_returns_exec_failed_when_autostart_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.dict(
                os.environ,
                {"SDDAI_AGENT_CMD": "", "SDDAI_PLAN_CMD": "", "SDDAI_PATCH_CMD": ""},
                clear=False,
            ):
                with mock.patch.object(
                    ollama_agent,
                    "_ensure_ollama_ready",
                    return_value=(False, "cannot reach ollama"),
                ) as ensure_ready:
                    with mock.patch.object(ollama_agent.api_agent, "execute") as api_execute:
                        out = ollama_agent.execute(
                            repo_root=ROOT,
                            run_dir=run_dir,
                            request={},
                            config={},
                            guardrails_budgets={},
                        )

            self.assertEqual(out.get("status"), "exec_failed", msg=str(out))
            self.assertIn("cannot reach ollama", str(out.get("reason", "")))
            self.assertEqual(out.get("runtime"), "ollama")
            ensure_ready.assert_called_once()
            api_execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
