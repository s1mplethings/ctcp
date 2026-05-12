from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.providers import api_source_chunking
from tools.providers.project_generation_source_helpers import _run_command_capture


class SourceGenerationPartialMaterializationTests(unittest.TestCase):
    def test_partial_materialization_does_not_overwrite_existing_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_partial_materialize_") as td:
            run_dir = Path(td)
            target = run_dir / "project_output" / "app" / "README.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("existing\n", encoding="utf-8")

            written = api_source_chunking._materialize_incremental_file_rows(
                run_dir=run_dir,
                rows=[{"path": "project_output/app/README.md", "content_lines": ["new"]}],
            )

            self.assertEqual(written, ["project_output/app/README.md"])
            self.assertEqual(target.read_text(encoding="utf-8"), "existing\n")

    def test_status_displays_source_generation_progress(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_status_progress_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "RUN.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-run-v1",
                        "run_id": "status-progress",
                        "goal": "Generate a concrete project",
                        "status": "running",
                        "verify_iterations": 0,
                        "max_iterations": 3,
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "artifacts" / "source_generation_state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-source-generation-state-v1",
                        "phase": "source_generation",
                        "total_batches": 4,
                        "completed_batches": [1, 2],
                        "pending_batches": [3, 4],
                        "generated_files": ["project_output/app/a.py", "project_output/app/b.py"],
                        "materialized_files": ["project_output/app/a.py"],
                        "status": "running",
                    }
                ),
                encoding="utf-8",
            )

            proc = subprocess.run(
                [str(ROOT / ".venv" / "Scripts" / "python.exe"), str(ROOT / "scripts" / "ctcp_orchestrate.py"), "status", "--run-dir", str(run_dir)],
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("source_generation_progress=completed_batches=2/4", proc.stdout)
            self.assertIn("generated_files=2", proc.stdout)
            self.assertIn("materialized_files=1", proc.stdout)

    def test_runtime_probe_timeout_returns_blocked_result(self) -> None:
        proc = _run_command_capture(
            [sys.executable, "-c", "import time; time.sleep(3)"],
            cwd=ROOT,
            timeout=1,
        )

        self.assertEqual(proc["rc"], 124)
        self.assertEqual(proc["status"], "blocked")
        self.assertEqual(proc["reason"], "runtime probe timed out")


if __name__ == "__main__":
    unittest.main()
