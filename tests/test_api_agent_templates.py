#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers import api_agent


class ApiAgentTemplateTests(unittest.TestCase):
    def test_resolve_templates_plan_only_includes_agent_key(self) -> None:
        request = {
            "role": "chair",
            "action": "plan_draft",
            "target_path": "artifacts/PLAN_draft.md",
        }
        with mock.patch.dict(
            os.environ,
            {
                "SDDAI_PLAN_CMD": "echo plan",
                "SDDAI_AGENT_CMD": "",
                "SDDAI_PATCH_CMD": "",
                "OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
            },
            clear=False,
        ):
            templates, reason = api_agent._resolve_templates(ROOT, request)

        self.assertEqual(reason, "")
        self.assertIn("plan", templates)
        self.assertIn("agent", templates)
        self.assertEqual(templates["agent"], templates["plan"])

    def test_execute_plan_only_chair_writes_target_without_keyerror(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            plan_script = repo_root / "plan_stub.py"
            plan_script.write_text(
                "\n".join(
                    [
                        "print('# PLAN')",
                        "print('Status: DRAFT')",
                        "print('- step: chair')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            env = {
                "SDDAI_PLAN_CMD": f'"{sys.executable}" "{plan_script}"',
                "SDDAI_AGENT_CMD": "",
                "SDDAI_PATCH_CMD": "",
                "OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
            }
            cases = (
                ("plan_draft", "artifacts/PLAN_draft.md", "waiting for PLAN_draft.md"),
                ("plan_signed", "artifacts/PLAN.md", "waiting for PLAN.md"),
            )
            for action, target_path, reason in cases:
                request = {
                    "role": "chair",
                    "action": action,
                    "target_path": target_path,
                    "reason": reason,
                    "goal": "generate chair plan",
                }
                with mock.patch.dict(os.environ, env, clear=False):
                    result = api_agent.execute(
                        repo_root=repo_root,
                        run_dir=run_dir,
                        request=request,
                        config={"budgets": {"max_outbox_prompts": 8}},
                        guardrails_budgets={},
                    )

                self.assertEqual(result.get("status"), "executed", msg=str(result))
                target = run_dir / target_path
                self.assertTrue(target.exists(), msg=str(result))
                self.assertIn("Status: DRAFT", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
