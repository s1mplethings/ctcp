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


class SourceGenerationResumeTests(unittest.TestCase):
    def test_resume_skips_completed_batches_and_continues_pending(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_source_resume_") as td:
            run_dir = Path(td)
            prompt_path = run_dir / "outbox" / "AGENT_PROMPT_chair_source_generation.md"
            target_path = run_dir / "artifacts" / "source_generation_report.json"
            manifest_doc = {
                "files": [
                    {"path": "project_output/app/a.py", "purpose": "a"},
                    {"path": "project_output/app/b.py", "purpose": "b"},
                    {"path": "project_output/app/c.py", "purpose": "c"},
                    {"path": "project_output/app/d.py", "purpose": "d"},
                ]
            }
            calls: list[str] = []

            def run_command(cmd: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
                prompt = str(kwargs.get("stdin_text", ""))
                requested = [line[2:].strip() for line in prompt.splitlines() if line.startswith("- project_output/")]
                calls.extend(requested)
                rows = [{"path": path, "content_lines": [f"# {Path(path).name}"]} for path in requested]
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=json.dumps({"files": rows}), stderr="")

            def first_run_env(name: str, default: int, **_kwargs: object) -> int:
                if name == "CTCP_SOURCE_GENERATION_FILE_BATCH_SIZE":
                    return 2
                if name == "CTCP_SOURCE_GENERATION_MAX_BATCHES_PER_RUN":
                    return 1
                return default

            rows, _docs, partial = api_source_chunking._collect_file_rows_from_batches(
                cmd="provider",
                repo_root=ROOT,
                run_dir=run_dir,
                logs_dir=run_dir / "logs",
                prompt_text="base prompt",
                api_call_env={},
                hooks=object(),
                request={"role": "chair", "action": "source_generation"},
                target_path=target_path,
                target_rel="artifacts/source_generation_report.json",
                prompt_path=prompt_path,
                manifest_doc=manifest_doc,
                retry_errors=[],
                fallback_target_result=lambda **_: {"status": "failed"},
                run_command=run_command,
                write_text=_write_text,
                agent_retry_policy=lambda _request: (1, 0.0),
                is_transient_transport_error=lambda *_args: False,
                safe_int_env=first_run_env,
            )
            self.assertEqual([row["path"] for row in rows], ["project_output/app/a.py", "project_output/app/b.py"])
            self.assertIsNotNone(partial)
            self.assertEqual(calls, ["project_output/app/a.py", "project_output/app/b.py"])

            calls.clear()

            def resume_env(name: str, default: int, **_kwargs: object) -> int:
                if name == "CTCP_SOURCE_GENERATION_FILE_BATCH_SIZE":
                    return 2
                if name == "CTCP_SOURCE_GENERATION_MAX_BATCHES_PER_RUN":
                    return 0
                return default

            rows, _docs, failure = api_source_chunking._collect_file_rows_from_batches(
                cmd="provider",
                repo_root=ROOT,
                run_dir=run_dir,
                logs_dir=run_dir / "logs",
                prompt_text="base prompt",
                api_call_env={},
                hooks=object(),
                request={"role": "chair", "action": "source_generation"},
                target_path=target_path,
                target_rel="artifacts/source_generation_report.json",
                prompt_path=prompt_path,
                manifest_doc=manifest_doc,
                retry_errors=[],
                fallback_target_result=lambda **_: {"status": "failed"},
                run_command=run_command,
                write_text=_write_text,
                agent_retry_policy=lambda _request: (1, 0.0),
                is_transient_transport_error=lambda *_args: False,
                safe_int_env=resume_env,
            )

            self.assertIsNone(failure)
            self.assertEqual(calls, ["project_output/app/c.py", "project_output/app/d.py"])
            self.assertEqual([row["path"] for row in rows], [
                "project_output/app/a.py",
                "project_output/app/b.py",
                "project_output/app/c.py",
                "project_output/app/d.py",
            ])
            state = json.loads((run_dir / "artifacts" / "source_generation_state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["completed_batches"], [1, 2])
            self.assertEqual(state["pending_batches"], [])
            self.assertEqual(state["status"], "completed")


if __name__ == "__main__":
    unittest.main()
