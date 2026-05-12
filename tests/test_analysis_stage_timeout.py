from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from llm_core.providers import api_provider
from tools import analysis_stage_progress
try:
    from tests.test_analysis_stage_progress import _hooks, _request
except ModuleNotFoundError:
    from test_analysis_stage_progress import _hooks, _request


class AnalysisStageTimeoutTests(unittest.TestCase):
    def test_provider_timeout_returns_structured_failure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            script = root / "slow_provider.py"
            script.write_text("import time\nprint('partial raw before sleep')\ntime.sleep(5)\n", encoding="utf-8")
            old_timeout = os.environ.get("CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS")
            os.environ["CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS"] = "1"
            try:
                started = time.time()
                result = api_provider.execute(
                    repo_root=root,
                    run_dir=run_dir,
                    request=_request(),
                    config={},
                    guardrails_budgets={},
                    hooks=_hooks(f'"{sys.executable}" "{script}"'),
                )
            finally:
                if old_timeout is None:
                    os.environ.pop("CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS", None)
                else:
                    os.environ["CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS"] = old_timeout

            self.assertLess(time.time() - started, 4)
            self.assertEqual(result["status"], "exec_failed")
            self.assertEqual(result["reason"], "analysis_provider_timeout")
            self.assertEqual(result["rc"], 124)
            self.assertIn("analysis_progress", result)
            doc = analysis_stage_progress.load_progress(run_dir)
            self.assertEqual(doc["status"], "timeout")
            self.assertEqual(doc["last_event"], "provider_call_timeout")
            self.assertEqual(doc["error"], "analysis_provider_timeout")
            self.assertFalse((run_dir / "artifacts" / "analysis.md").exists())

    def test_advance_failure_shape_is_graceful_not_outer_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            script = root / "slow_provider.py"
            script.write_text("import time\ntime.sleep(5)\n", encoding="utf-8")
            old_timeout = os.environ.get("CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS")
            os.environ["CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS"] = "1"
            try:
                result = api_provider.execute(
                    repo_root=root,
                    run_dir=run_dir,
                    request=_request(),
                    config={},
                    guardrails_budgets={},
                    hooks=_hooks(f'"{sys.executable}" "{script}"'),
                )
            finally:
                if old_timeout is None:
                    os.environ.pop("CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS", None)
                else:
                    os.environ["CTCP_ANALYSIS_PROVIDER_TIMEOUT_SECONDS"] = old_timeout

            self.assertEqual(result["status"], "exec_failed")
            self.assertEqual(result["reason"], "analysis_provider_timeout")
            self.assertTrue((run_dir / "artifacts" / "analysis_progress.json").exists())


if __name__ == "__main__":
    unittest.main()
