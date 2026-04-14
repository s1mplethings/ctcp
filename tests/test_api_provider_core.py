#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.providers import api_provider


class ApiProviderCoreTests(unittest.TestCase):
    def test_resolve_templates_uses_defaults_when_api_env_ready(self) -> None:
        request = {
            "role": "chair",
            "action": "plan_draft",
            "target_path": "artifacts/PLAN_draft.md",
        }

        templates, reason = api_provider.resolve_templates(
            ROOT,
            request,
            needs_plan=lambda _: True,
            needs_patch=lambda _: False,
            agent_tpl="",
            plan_tpl="",
            patch_tpl="",
            is_api_env_ready=lambda: (True, ""),
            default_plan_cmd=lambda _: "plan-cmd",
            default_patch_cmd=lambda _: "patch-cmd",
            default_agent_cmd=lambda _: "agent-cmd",
        )

        self.assertEqual(reason, "")
        self.assertEqual(templates.get("plan"), "plan-cmd")
        self.assertEqual(templates.get("agent"), "plan-cmd")

    def test_execute_runs_agent_with_injected_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "repo"
            run_dir = root / "run"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub.py"
            agent_script.write_text("print('core-normalized')\n", encoding="utf-8")

            evidence = {}
            for name in ("context", "constraints", "fix_brief", "externals"):
                path = run_dir / "outbox" / f"{name}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {name}\n", encoding="utf-8")
                evidence[name] = path

            def _record_failure(run_path: Path, reason: str) -> Path:
                review = run_path / "reviews" / "review_api_agent.md"
                review.parent.mkdir(parents=True, exist_ok=True)
                review.write_text(reason, encoding="utf-8")
                return review

            hooks = api_provider.ApiProviderHooks(
                resolve_templates=lambda _repo_root, _request: ({ "agent": f'"{sys.executable}" "{agent_script}"' }, ""),
                build_evidence_pack=lambda **_: evidence,
                render_prompt=lambda **_: "prompt-text",
                record_failure_review=_record_failure,
                needs_patch=lambda _request: False,
                normalize_patch_payload=lambda text: (text, ""),
                normalize_target_payload=lambda **_: ("core-normalized\n", ""),
            )

            result = api_provider.execute(
                repo_root=repo_root,
                run_dir=run_dir,
                request={
                    "role": "chair",
                    "action": "plan_draft",
                    "target_path": "artifacts/analysis.md",
                    "goal": "test goal",
                    "reason": "test reason",
                },
                config={"budgets": {"max_outbox_prompts": 8}},
                guardrails_budgets={},
                hooks=hooks,
            )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            self.assertEqual((run_dir / "artifacts" / "analysis.md").read_text(encoding="utf-8"), "core-normalized\n")
            self.assertTrue((run_dir / "outbox" / "AGENT_PROMPT_chair_plan_draft.md").exists())
            self.assertTrue((run_dir / "logs" / "agent.stdout").exists())

    def test_execute_falls_back_to_normalized_target_when_agent_command_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo_root = root / "repo"
            run_dir = root / "run"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_fail.py"
            agent_script.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")

            evidence = {}
            for name in ("context", "constraints", "fix_brief", "externals"):
                path = run_dir / "outbox" / f"{name}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {name}\n", encoding="utf-8")
                evidence[name] = path

            def _record_failure(run_path: Path, reason: str) -> Path:
                review = run_path / "reviews" / "review_api_agent.md"
                review.parent.mkdir(parents=True, exist_ok=True)
                review.write_text(reason, encoding="utf-8")
                return review

            hooks = api_provider.ApiProviderHooks(
                resolve_templates=lambda _repo_root, _request: ({"agent": f'"{sys.executable}" "{agent_script}"'}, ""),
                build_evidence_pack=lambda **_: evidence,
                render_prompt=lambda **_: "prompt-text",
                record_failure_review=_record_failure,
                needs_patch=lambda _request: False,
                normalize_patch_payload=lambda text: (text, ""),
                normalize_target_payload=lambda **_: ("# Analysis\n\n## Core Goal\n- fallback-goal\n", ""),
            )

            result = api_provider.execute(
                repo_root=repo_root,
                run_dir=run_dir,
                request={
                    "role": "chair",
                    "action": "plan_draft",
                    "target_path": "artifacts/analysis.md",
                    "goal": "fallback goal",
                    "reason": "test reason",
                },
                config={"budgets": {"max_outbox_prompts": 8}},
                guardrails_budgets={},
                hooks=hooks,
            )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            self.assertTrue(bool(result.get("fallback_used", False)))
            self.assertIn("agent command failed", str(result.get("fallback_reason", "")))
            self.assertIn("fallback-goal", (run_dir / "artifacts" / "analysis.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
