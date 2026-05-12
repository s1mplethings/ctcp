from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from llm_core.providers import api_provider
from tools import analysis_stage_progress
try:
    from tests.test_analysis_stage_progress import _hooks, _request
except ModuleNotFoundError:
    from test_analysis_stage_progress import _hooks, _request


class AnalysisStageResumeTests(unittest.TestCase):
    def test_raw_response_preserved_when_parser_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            script = root / "provider.py"
            script.write_text("print('raw provider payload')\n", encoding="utf-8")

            result = api_provider.execute(
                repo_root=root,
                run_dir=run_dir,
                request=_request(),
                config={},
                guardrails_budgets={},
                hooks=_hooks(
                    f'"{sys.executable}" "{script}"',
                    normalizer=lambda **_kwargs: ("", "parser exploded"),
                ),
            )

            self.assertEqual(result["status"], "exec_failed")
            self.assertEqual(result["reason"], "parser exploded")
            self.assertTrue(analysis_stage_progress.raw_path(run_dir).exists())
            self.assertIn("raw provider payload", analysis_stage_progress.raw_path(run_dir).read_text(encoding="utf-8"))
            doc = analysis_stage_progress.load_progress(run_dir)
            self.assertEqual(doc["status"], "failed")
            self.assertEqual(doc["last_event"], "parser_failed")

    def test_resume_uses_raw_response_before_recalling_provider(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            analysis_stage_progress.raw_path(run_dir).parent.mkdir(parents=True, exist_ok=True)
            analysis_stage_progress.raw_path(run_dir).write_text("stored raw response\n", encoding="utf-8")
            marker = root / "provider_called.txt"
            script = root / "provider.py"
            script.write_text(f"from pathlib import Path\nPath({str(marker)!r}).write_text('called')\n", encoding="utf-8")

            result = api_provider.execute(
                repo_root=root,
                run_dir=run_dir,
                request=_request(),
                config={},
                guardrails_budgets={},
                hooks=_hooks(f'"{sys.executable}" "{script}"'),
            )

            self.assertEqual(result["status"], "executed")
            self.assertTrue(result.get("resumed_from_analysis_raw"))
            self.assertFalse(marker.exists())
            self.assertTrue((run_dir / "artifacts" / "analysis.md").exists())
            self.assertIn("stored raw response", (run_dir / "artifacts" / "analysis.md").read_text(encoding="utf-8"))

    def test_artifact_write_failure_preserves_partial(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            script = root / "provider.py"
            script.write_text("print('raw provider payload')\n", encoding="utf-8")
            original_write_text = api_provider._write_text

            def fail_analysis_write(path: Path, text: str) -> None:
                if path.name == "analysis.md":
                    raise OSError("disk write failed")
                original_write_text(path, text)

            with mock.patch.object(api_provider, "_write_text", side_effect=fail_analysis_write):
                result = api_provider.execute(
                    repo_root=root,
                    run_dir=run_dir,
                    request=_request(),
                    config={},
                    guardrails_budgets={},
                    hooks=_hooks(f'"{sys.executable}" "{script}"'),
                )

            self.assertEqual(result["status"], "exec_failed")
            self.assertIn("analysis artifact write failed", result["reason"])
            self.assertTrue(analysis_stage_progress.partial_path(run_dir).exists())
            self.assertIn("raw provider payload", analysis_stage_progress.partial_path(run_dir).read_text(encoding="utf-8"))
            doc = analysis_stage_progress.load_progress(run_dir)
            self.assertEqual(doc["status"], "failed")
            self.assertEqual(doc["last_event"], "artifact_write_failed")


if __name__ == "__main__":
    unittest.main()
