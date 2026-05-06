from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.providers import local_exec


class LocalExecLibrarianEvidenceTests(unittest.TestCase):
    def test_librarian_local_exec_writes_prompt_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_local_exec_librarian_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)

            def _fake_run(*args: object, **kwargs: object) -> object:
                (run_dir / "artifacts" / "context_pack.json").write_text('{"schema_version":"ctcp-context-pack-v1"}\n', encoding="utf-8")
                return mock.Mock(returncode=0, stdout="", stderr="")

            request = {"role": "librarian", "action": "context_pack", "target_path": "artifacts/context_pack.json"}
            with mock.patch.object(local_exec.subprocess, "run", side_effect=_fake_run):
                result = local_exec.execute(repo_root=Path.cwd(), run_dir=run_dir, request=request)

            self.assertEqual(result.get("status"), "executed")
            self.assertEqual(result.get("prompt_path"), "outbox/AGENT_PROMPT_librarian_context_pack.md")
            prompt = run_dir / "outbox" / "AGENT_PROMPT_librarian_context_pack.md"
            self.assertTrue(prompt.exists())
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("Role: librarian", text)
            self.assertIn("Provider: local_exec", text)


if __name__ == "__main__":
    unittest.main()
