from __future__ import annotations

import json
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from llm_core.providers import api_provider
from tools import analysis_stage_progress

ROOT = Path(__file__).resolve().parents[1]


def _load_benchmark_module():
    path = ROOT / "tests" / "concrete_project_benchmark" / "run_concrete_project_benchmark.py"
    spec = importlib.util.spec_from_file_location("ctcp_concrete_benchmark_for_tests", path)
    if spec is None or spec.loader is None:
        raise ImportError(str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hooks(command: str, *, normalizer=None) -> api_provider.ApiProviderHooks:
    def build_evidence_pack(**kwargs):
        run_dir = Path(kwargs["run_dir"])
        evidence = run_dir / "evidence"
        evidence.mkdir(parents=True, exist_ok=True)
        out = {}
        for name in ("context", "constraints", "fix_brief", "externals"):
            path = evidence / f"{name}.md"
            path.write_text(name + "\n", encoding="utf-8")
            out[name] = path
        return out

    def record_failure_review(run_dir: Path, reason: str) -> Path:
        path = run_dir / "reviews" / "review_failure.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(reason + "\n", encoding="utf-8")
        return path

    def normalize_target_payload(**kwargs):
        if normalizer is not None:
            return normalizer(**kwargs)
        return "# Analysis\n\n" + str(kwargs.get("raw_text", "")).strip() + "\n", ""

    return api_provider.ApiProviderHooks(
        resolve_templates=lambda _repo_root, _request: ({"agent": command}, ""),
        build_evidence_pack=build_evidence_pack,
        render_prompt=lambda **_kwargs: "analysis prompt",
        record_failure_review=record_failure_review,
        needs_patch=lambda _request: False,
        normalize_patch_payload=lambda raw: (raw, ""),
        normalize_target_payload=normalize_target_payload,
    )


def _request() -> dict[str, str]:
    return {
        "role": "chair",
        "action": "plan_draft",
        "target_path": "artifacts/analysis.md",
        "goal": "build a concrete project",
    }


class AnalysisStageProgressTests(unittest.TestCase):
    def test_progress_artifact_written_before_provider_call_and_completed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            progress = analysis_stage_progress.progress_path(run_dir)
            script = root / "provider.py"
            script.write_text(
                "from pathlib import Path\n"
                f"assert Path({str(progress)!r}).exists()\n"
                "print('provider raw analysis')\n",
                encoding="utf-8",
            )

            result = api_provider.execute(
                repo_root=root,
                run_dir=run_dir,
                request=_request(),
                config={},
                guardrails_budgets={},
                hooks=_hooks(f'"{sys.executable}" "{script}"'),
            )

            self.assertEqual(result["status"], "executed")
            doc = analysis_stage_progress.load_progress(run_dir)
            self.assertEqual(doc["status"], "completed")
            self.assertEqual(doc["last_event"], "artifact_write_completed")
            self.assertTrue(doc["provider_call_started_at"])
            self.assertTrue(doc["provider_call_completed_at"])
            self.assertTrue(doc["parser_started_at"])
            self.assertTrue(doc["parser_completed_at"])
            self.assertTrue(doc["artifact_write_started_at"])
            self.assertTrue(doc["artifact_write_completed_at"])
            self.assertTrue((run_dir / "artifacts" / "analysis.md").exists())
            self.assertTrue(analysis_stage_progress.raw_path(run_dir).exists())

    def test_status_line_reads_analysis_progress(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            analysis_stage_progress.start_progress(run_dir=run_dir, request=_request(), last_event="unit_test")
            line = analysis_stage_progress.status_line(run_dir)
            self.assertIn("analysis_progress", line)
            self.assertIn("last_event=unit_test", line)

    def test_analysis_target_uses_single_provider_call_when_plan_template_is_reused(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            run_dir = root / "run"
            run_dir.mkdir()
            count_path = root / "count.txt"
            script = root / "provider.py"
            script.write_text(
                "from pathlib import Path\n"
                f"path = Path({str(count_path)!r})\n"
                "count = int(path.read_text() or '0') if path.exists() else 0\n"
                "path.write_text(str(count + 1))\n"
                "print('single provider raw analysis')\n",
                encoding="utf-8",
            )
            hooks = _hooks(f'"{sys.executable}" "{script}"')
            hooks = api_provider.ApiProviderHooks(
                resolve_templates=lambda _repo_root, _request: ({"plan": f'"{sys.executable}" "{script}"'}, ""),
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

            self.assertEqual(result["status"], "executed")
            self.assertEqual(count_path.read_text(encoding="utf-8"), "1")

    def test_benchmark_summary_includes_analysis_progress(self) -> None:
        bench = _load_benchmark_module()

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            analysis_stage_progress.start_progress(run_dir=run_dir, request=_request(), last_event="provider_call_started")
            summary: dict[str, object] = {}
            bench._merge_analysis_evidence(summary, run_dir, command_timed_out=True)

            self.assertTrue(summary["analysis_timeout"])
            self.assertEqual(summary["analysis_target"], "artifacts/analysis.md")
            self.assertIsInstance(summary["analysis_progress"], dict)
            json.dumps(summary)


if __name__ == "__main__":
    unittest.main()
