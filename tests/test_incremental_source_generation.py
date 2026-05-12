from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.providers import api_source_chunking


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _safe_int_env(name: str, default: int, **_kwargs: object) -> int:
    if name == "CTCP_SOURCE_GENERATION_FILE_BATCH_SIZE":
        return 2
    if name == "CTCP_SOURCE_GENERATION_MAX_BATCHES_PER_RUN":
        return 0
    return default


def _batch_command(calls: list[str]) -> Any:
    def run_command(cmd: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        prompt = str(kwargs.get("stdin_text", ""))
        requested = [line[2:].strip() for line in prompt.splitlines() if line.startswith("- project_output/")]
        calls.extend(requested)
        rows = [{"path": path, "content_lines": [f"# generated {Path(path).name}"]} for path in requested]
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=json.dumps({"files": rows}), stderr="")

    return run_command


class IncrementalSourceGenerationTests(unittest.TestCase):
    def test_batch_checkpoint_created_and_materialized_immediately(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_incremental_source_") as td:
            run_dir = Path(td)
            calls: list[str] = []
            rows, docs, failure = api_source_chunking._collect_file_rows_from_batches(
                cmd="provider",
                repo_root=ROOT,
                run_dir=run_dir,
                logs_dir=run_dir / "logs",
                prompt_text="base prompt",
                api_call_env={},
                hooks=object(),
                request={"role": "chair", "action": "source_generation"},
                target_path=run_dir / "artifacts" / "source_generation_report.json",
                target_rel="artifacts/source_generation_report.json",
                prompt_path=run_dir / "outbox" / "AGENT_PROMPT_chair_source_generation.md",
                manifest_doc={
                    "files": [
                        {"path": "project_output/app/README.md", "purpose": "docs"},
                        {"path": "project_output/app/src/server.py", "purpose": "server"},
                    ]
                },
                retry_errors=[],
                fallback_target_result=lambda **_: {"status": "failed"},
                run_command=_batch_command(calls),
                write_text=_write_text,
                agent_retry_policy=lambda _request: (1, 0.0),
                is_transient_transport_error=lambda *_args: False,
                safe_int_env=_safe_int_env,
            )

            self.assertIsNone(failure)
            self.assertEqual(len(rows), 2)
            self.assertEqual(len(docs), 2)
            checkpoint = run_dir / "artifacts" / "source_generation_batches" / "batch_001.json"
            self.assertTrue(checkpoint.exists())
            checkpoint_doc = json.loads(checkpoint.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint_doc["status"], "completed")
            self.assertTrue(checkpoint_doc["materialized"])
            self.assertTrue((run_dir / "project_output" / "app" / "README.md").exists())
            self.assertTrue((run_dir / "project_output" / "app" / "src" / "server.py").exists())
            partial = json.loads((run_dir / "artifacts" / "source_generation_partial_report.json").read_text(encoding="utf-8"))
            self.assertEqual(partial["completed_batch_count"], 1)
            self.assertTrue(partial["project_output_exists"])
            self.assertTrue((run_dir / "artifacts" / "generated_symbols.json").exists())
            self.assertTrue((run_dir / "artifacts" / "generated_routes.json").exists())
            self.assertTrue((run_dir / "artifacts" / "runtime_contract.json").exists())
            self.assertTrue((run_dir / "artifacts" / "reconciliation_report.json").exists())

    def test_adaptive_batching_default_is_greater_than_one(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_batch_plan_") as td:
            run_dir = Path(td)

            def safe_int_env(name: str, default: int, **_kwargs: object) -> int:
                self.assertEqual(name, "CTCP_SOURCE_GENERATION_FILE_BATCH_SIZE")
                self.assertGreater(default, 1)
                return default

            batch_size, batches = api_source_chunking._load_or_create_batch_plan(
                run_dir=run_dir,
                manifest_paths=[
                    "project_output/app/a.py",
                    "project_output/app/b.py",
                    "project_output/app/c.py",
                    "project_output/app/d.py",
                ],
                safe_int_env=safe_int_env,
            )
            self.assertEqual(batch_size, 3)
            self.assertEqual([len(batch) for batch in batches], [3, 1])

    def test_final_source_generation_report_still_writes_after_batches_complete(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_final_source_report_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "output_contract_freeze.json").write_text("{}", encoding="utf-8")
            calls: list[str] = []

            class Hooks:
                def record_failure_review(self, _run_dir: Path, reason: str) -> Path:
                    path = run_dir / "reviews" / "failure.md"
                    _write_text(path, reason)
                    return path

                def normalize_target_payload(self, **kwargs: object) -> tuple[str, str]:
                    return str(kwargs["raw_text"]), ""

            def run_command(cmd: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
                prompt = str(kwargs.get("stdin_text", ""))
                if "Manifest Only" in prompt:
                    return subprocess.CompletedProcess(
                        args=cmd,
                        returncode=0,
                        stdout=json.dumps(
                            {
                                "files": [
                                    {"path": "project_output/app/README.md", "purpose": "docs"},
                                    {"path": "project_output/app/src/server.py", "purpose": "server"},
                                ]
                            }
                        ),
                        stderr="",
                    )
                requested = [line[2:].strip() for line in prompt.splitlines() if line.startswith("- project_output/")]
                calls.extend(requested)
                rows = [{"path": path, "content_lines": [f"# {Path(path).name}"]} for path in requested]
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=json.dumps({"files": rows}), stderr="")

            result = api_source_chunking.run_chunked_source_generation_phase(
                template="provider",
                placeholders={},
                repo_root=ROOT,
                run_dir=run_dir,
                logs_dir=run_dir / "logs",
                prompt_text="base prompt",
                api_call_env={},
                hooks=Hooks(),
                request={"role": "chair", "action": "source_generation", "target_path": "artifacts/source_generation_report.json"},
                target_path=run_dir / "artifacts" / "source_generation_report.json",
                target_rel="artifacts/source_generation_report.json",
                prompt_path=run_dir / "outbox" / "AGENT_PROMPT_chair_source_generation.md",
                format_cmd_template=lambda template, _placeholders: (template, ""),
                failure_result=lambda **kwargs: {"status": "failed", "reason": kwargs.get("reason", "")},
                fallback_target_result=lambda **kwargs: {"status": "failed", "reason": kwargs.get("reason", "")},
                run_command=run_command,
                write_text=_write_text,
                agent_retry_policy=lambda _request: (1, 0.0),
                is_transient_transport_error=lambda *_args: False,
                safe_int_env=_safe_int_env,
            )

            self.assertEqual(result["status"], "executed")
            self.assertTrue((run_dir / "artifacts" / "source_generation_report.json").exists())
            report = json.loads((run_dir / "artifacts" / "source_generation_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["chunked_source_generation"]["materialized_file_count"], 2)
            self.assertEqual(calls, ["project_output/app/README.md", "project_output/app/src/server.py"])


if __name__ == "__main__":
    unittest.main()
