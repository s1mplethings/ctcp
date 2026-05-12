from __future__ import annotations

import json
import unittest
import sys
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.providers import api_source_chunking


class ApiSourceChunkingTests(unittest.TestCase):
    def test_batch_prompt_carries_interface_contract(self) -> None:
        interfaces = {
            "project_output/vn/src/vn/editor/__init__.py": {"defines": [], "imports": ["EditorActions"], "exports": ["EditorActions"]},
            "project_output/vn/src/vn/editor/actions.py": {"defines": ["EditorActions"], "imports": [], "exports": ["EditorActions"]},
        }

        prompt = api_source_chunking._batch_prompt(
            "base prompt",
            ["project_output/vn/src/vn/editor/actions.py"],
            1,
            1,
            interfaces,
        )

        self.assertIn("global Python interface contract", prompt)
        self.assertIn("Model Budget", prompt)
        self.assertIn("tier_1_cheap", prompt)
        self.assertIn("EditorActions", prompt)
        self.assertIn("project_output/vn/src/vn/editor/actions.py", prompt)

    def test_file_content_batches_default_to_adaptive_grouping(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_chunk_single_file_") as td:
            run_dir = Path(td)
            logs_dir = run_dir / "logs"
            prompt_path = run_dir / "artifacts" / "source_generation.prompt.md"
            target_path = run_dir / "artifacts" / "source_generation_report.json"
            calls: list[str] = []

            def write_text(path: Path, text: str) -> None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            def run_command(_cmd: str, **kwargs: object) -> subprocess.CompletedProcess[str]:
                prompt = str(kwargs.get("stdin_text", ""))
                requested = [line[2:].strip() for line in prompt.splitlines() if line.startswith("- project_output/")]
                calls.append(",".join(requested))
                rows = [{"path": path, "content_lines": ["print('ok')"]} for path in requested]
                return subprocess.CompletedProcess(args=_cmd, returncode=0, stdout=json.dumps({"files": rows}), stderr="")

            def safe_int_env(name: str, default: int, **_kwargs: object) -> int:
                if name == "CTCP_SOURCE_GENERATION_FILE_BATCH_SIZE":
                    self.assertEqual(default, 3)
                elif name == "CTCP_SOURCE_GENERATION_MAX_BATCHES_PER_RUN":
                    self.assertEqual(default, 0)
                return default

            rows, docs, failure = api_source_chunking._collect_file_rows_from_batches(
                cmd="provider",
                repo_root=ROOT,
                run_dir=run_dir,
                logs_dir=logs_dir,
                prompt_text="base prompt",
                api_call_env={},
                hooks=object(),
                request={"role": "chair", "action": "source_generation"},
                target_path=target_path,
                target_rel="artifacts/source_generation_report.json",
                prompt_path=prompt_path,
                manifest_doc={
                    "files": [
                        {"path": "project_output/vn/a.py", "purpose": "a"},
                        {"path": "project_output/vn/b.py", "purpose": "b"},
                    ]
                },
                retry_errors=[],
                fallback_target_result=lambda **_: {"status": "failed"},
                run_command=run_command,
                write_text=write_text,
                agent_retry_policy=lambda _request: (1, 0.0),
                is_transient_transport_error=lambda *_args: False,
                safe_int_env=safe_int_env,
            )

            self.assertIsNone(failure)
            self.assertEqual(calls, ["project_output/vn/a.py,project_output/vn/b.py"])
            self.assertEqual([row["path"] for row in rows], ["project_output/vn/a.py", "project_output/vn/b.py"])
            choices = docs[0].get("model_budget_choices", [])
            self.assertEqual([row["tier"] for row in choices], ["tier_2_medium", "tier_1_cheap"])


if __name__ == "__main__":
    unittest.main()
