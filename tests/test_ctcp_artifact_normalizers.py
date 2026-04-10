#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ctcp_adapters import ctcp_artifact_normalizers as normalizers


class CtcpArtifactNormalizersTests(unittest.TestCase):
    def test_normalize_target_payload_builds_file_request_json_from_non_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = Path(td) / "run"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            payload, err = normalizers.normalize_target_payload(
                repo_root=repo_root,
                run_dir=run_dir,
                request={
                    "role": "chair",
                    "action": "file_request",
                    "target_path": "artifacts/file_request.json",
                    "goal": "normalize me",
                },
                raw_text="# not json\n- but still normalize",
            )

            self.assertEqual(err, "")
            doc = json.loads(payload)
            self.assertEqual(doc.get("schema_version"), "ctcp-file-request-v1")
            self.assertIsInstance(doc.get("needs"), list)
            self.assertIsInstance(doc.get("budget"), dict)

    def test_render_prompt_keeps_whiteboard_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)

            evidence: dict[str, Path] = {}
            for key in ("context", "constraints", "fix_brief", "externals"):
                path = run_dir / "outbox" / f"{key}.md"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f"# {key}\n- sample\n", encoding="utf-8")
                evidence[key] = path

            prompt = normalizers._render_prompt(
                run_dir=run_dir,
                repo_root=repo_root,
                request={
                    "role": "patchmaker",
                    "action": "make_patch",
                    "goal": "whiteboard carry",
                    "reason": "waiting for diff.patch",
                    "target_path": "artifacts/diff.patch",
                    "whiteboard": {
                        "path": "artifacts/support_whiteboard.json",
                        "query": "whiteboard carry",
                        "hits": [
                            {
                                "path": "docs/10_team_mode.md",
                                "start_line": 42,
                                "snippet": "support and production collaboration lane",
                            }
                        ],
                        "snapshot": {
                            "entries": [
                                {
                                    "role": "support_lead",
                                    "kind": "dispatch_request",
                                    "text": "sync requirement to production lane",
                                }
                            ]
                        },
                    },
                },
                evidence=evidence,
            )

            self.assertIn("# WHITEBOARD", prompt)
            self.assertIn("artifacts/support_whiteboard.json", prompt)
            self.assertIn("librarian_query", prompt)
            self.assertIn("docs/10_team_mode.md", prompt)
            self.assertIn("[support_lead/dispatch_request]", prompt)

    def test_normalize_plan_md_keeps_explicit_goal_file_in_scope_allow(self) -> None:
        text = normalizers._normalize_plan_md(
            "",
            signed=True,
            goal="做一个双击 index.html 就能运行的单文件中文工具页面",
        )

        self.assertIn("Status: SIGNED", text)
        self.assertIn("Scope-Allow:", text)
        self.assertIn("index.html", text)


if __name__ == "__main__":
    unittest.main()
