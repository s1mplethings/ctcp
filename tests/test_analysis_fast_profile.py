from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm_core.providers import api_provider
from tools import analysis_fast_profile, analysis_stage_progress
try:
    from tests.test_analysis_stage_progress import _hooks, _request
except ModuleNotFoundError:
    from test_analysis_stage_progress import _hooks, _request


class AnalysisFastProfileTests(unittest.TestCase):
    def test_fast_profile_selected_via_env(self) -> None:
        with mock.patch.dict(os.environ, {"CTCP_ANALYSIS_PROFILE": "fast"}, clear=False):
            self.assertEqual(analysis_fast_profile.analysis_profile(), "fast")
            self.assertTrue(analysis_fast_profile.fast_analysis_enabled(_request()))

    def test_fast_profile_prompt_retains_requirements_and_excludes_unrelated_context(self) -> None:
        request = _request()
        request["goal"] = (
            "Generate a real runnable local HTTP API project for tracking issues. "
            "Required endpoints: POST /issues, GET /issues, GET /issues/{id}, "
            "PATCH /issues/{id}/status, POST /issues/{id}/close. Use SQLite persistence. "
            "Valid issue statuses: open, in_progress, closed."
        )
        prompt = analysis_fast_profile.render_fast_analysis_prompt(
            run_dir=Path("C:/tmp/run"),
            repo_root=Path("C:/tmp/repo"),
            request=request,
            evidence={},
        )
        self.assertIn("POST /issues", prompt)
        self.assertIn("SQLite", prompt)
        self.assertIn("open, in_progress, closed", prompt)
        self.assertIn("Do not generate an agent manifest", prompt)
        self.assertNotIn("agent factory", prompt.lower())
        self.assertLess(prompt.lower().count("agent manifest"), 2)

    def test_fast_output_contract_exists(self) -> None:
        contract = analysis_fast_profile.FAST_ANALYSIS_OUTPUT_CONTRACT
        for section in ("## Project Type", "## Required Files", "## Runtime", "## Data Model", "## Acceptance Checks"):
            self.assertIn(section, contract)

    def test_fast_profile_still_calls_provider_and_writes_analysis(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            called = root / "provider_called.txt"
            provider = root / "provider.py"
            provider.write_text(
                "from pathlib import Path\n"
                f"Path({str(called)!r}).write_text('called')\n"
                "print('# Analysis\\n\\n## Project Type\\nIssue tracker API')\n",
                encoding="utf-8",
            )
            env = {
                "CTCP_ANALYSIS_PROFILE": "fast",
                "SDDAI_AGENT_CMD": f'"{sys.executable}" "{provider}"',
            }
            with mock.patch.dict(os.environ, env, clear=False):
                hooks = _hooks("unused")
                hooks = api_provider.ApiProviderHooks(
                    resolve_templates=lambda _repo_root, _request: ({"plan": "unused plan command"}, ""),
                    build_evidence_pack=hooks.build_evidence_pack,
                    render_prompt=hooks.render_prompt,
                    record_failure_review=hooks.record_failure_review,
                    needs_patch=hooks.needs_patch,
                    normalize_patch_payload=hooks.normalize_patch_payload,
                    normalize_target_payload=hooks.normalize_target_payload,
                )
                result = api_provider.execute(
                    repo_root=root,
                    run_dir=run_dir,
                    request=_request(),
                    config={},
                    guardrails_budgets={},
                    hooks=hooks,
                )

            self.assertEqual(result["status"], "executed", msg=str(result))
            self.assertTrue(called.exists())
            self.assertTrue((run_dir / "artifacts" / "analysis.md").exists())
            progress = analysis_stage_progress.load_progress(run_dir)
            self.assertEqual(progress.get("analysis_profile"), "fast")


if __name__ == "__main__":
    unittest.main()
