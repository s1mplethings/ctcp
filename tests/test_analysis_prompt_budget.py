from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ctcp_adapters import ctcp_artifact_normalizers as normalizers
from llm_core.providers import api_provider
from tools import analysis_fast_profile, analysis_stage_progress
try:
    from tests.test_analysis_stage_progress import _hooks, _request
except ModuleNotFoundError:
    from test_analysis_stage_progress import _hooks, _request

ROOT = Path(__file__).resolve().parents[1]


def _load_benchmark_module():
    path = ROOT / "tests" / "concrete_project_benchmark" / "run_concrete_project_benchmark.py"
    spec = importlib.util.spec_from_file_location("ctcp_concrete_benchmark_for_budget_tests", path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AnalysisPromptBudgetTests(unittest.TestCase):
    def test_fast_profile_prompt_is_smaller_than_default_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            run_dir.mkdir()
            repo_root.mkdir()
            evidence = {}
            for name in ("context", "constraints", "fix_brief", "externals"):
                path = run_dir / "outbox" / f"{name}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text((name + "\n") * 1500, encoding="utf-8")
                evidence[name] = path
            request = _request()
            request["goal"] = "Generate a concrete issue tracker API. Required endpoints: POST /issues. Use SQLite."

            default_prompt = normalizers._render_prompt(run_dir=run_dir, repo_root=repo_root, request=request, evidence=evidence)
            fast_prompt = analysis_fast_profile.render_fast_analysis_prompt(
                run_dir=run_dir,
                repo_root=repo_root,
                request=request,
                evidence=evidence,
            )

            self.assertLess(len(fast_prompt), len(default_prompt) // 3)
            self.assertIn("POST /issues", fast_prompt)
            self.assertIn("SQLite", fast_prompt)

    def test_analysis_progress_records_prompt_budget_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            provider = root / "provider.py"
            provider.write_text("print('# Analysis\\n\\n## Project Type\\nIssue tracker API')\n", encoding="utf-8")
            env = {
                "CTCP_ANALYSIS_PROFILE": "fast",
                "CTCP_ANALYSIS_MAX_OUTPUT_TOKENS": "777",
                "SDDAI_AGENT_CMD": f'"{sys.executable}" "{provider}"',
            }
            with mock.patch.dict(os.environ, env, clear=False):
                result = api_provider.execute(
                    repo_root=root,
                    run_dir=run_dir,
                    request=_request(),
                    config={},
                    guardrails_budgets={},
                    hooks=_hooks("unused"),
                )

            self.assertEqual(result["status"], "executed", msg=str(result))
            progress = analysis_stage_progress.load_progress(run_dir)
            self.assertEqual(progress.get("analysis_profile"), "fast")
            self.assertGreater(int(progress.get("prompt_char_count", 0)), 0)
            self.assertGreater(int(progress.get("prompt_estimated_tokens", 0)), 0)
            self.assertIn("## Runtime", str(progress.get("output_contract", "")))
            self.assertEqual(progress.get("max_output_tokens"), 777)

    def test_benchmark_env_sets_fast_profile(self) -> None:
        benchmark = _load_benchmark_module()
        env = benchmark._ordinary_env()
        self.assertEqual(env.get("CTCP_ANALYSIS_PROFILE"), "fast")

    def test_timeout_failure_reports_prompt_budget_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            analysis_stage_progress.start_progress(
                run_dir=run_dir,
                request=_request(),
                prompt_budget={
                    "prompt_char_count": 123,
                    "prompt_estimated_tokens": 31,
                    "output_contract": "contract",
                    "max_output_tokens": 777,
                    "analysis_profile": "fast",
                },
            )
            analysis_stage_progress.mark_timeout(run_dir, error="analysis_provider_timeout")
            benchmark = _load_benchmark_module()
            summary: dict[str, object] = {}
            benchmark._merge_analysis_evidence(summary, run_dir, command_timed_out=False)
            self.assertEqual(summary["analysis_profile"], "fast")
            self.assertEqual(summary["analysis_prompt_char_count"], 123)
            self.assertEqual(summary["analysis_prompt_estimated_tokens"], 31)
            self.assertEqual(summary["analysis_max_output_tokens"], 777)


if __name__ == "__main__":
    unittest.main()
