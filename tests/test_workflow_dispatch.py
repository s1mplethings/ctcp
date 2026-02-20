#!/usr/bin/env python3
from __future__ import annotations

import json
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import workflow_dispatch


class WorkflowDispatchTests(unittest.TestCase):
    def test_registry_contains_self_improve_workflow(self) -> None:
        index_path = ROOT / "workflow_registry" / "index.json"
        doc = json.loads(index_path.read_text(encoding="utf-8"))
        ids = {str(row.get("id", "")) for row in doc.get("workflows", [])}
        self.assertIn("adlc_self_improve_core", ids)

    def test_dispatch_command_points_to_self_improve_entry(self) -> None:
        cmd = workflow_dispatch._dispatch_command(
            workflow_id="adlc_self_improve_core",
            repo_root=ROOT,
            goal="Self improve core loop",
            max_rounds=2,
            patch_cmd="",
            verify_cmd="",
        )
        text = " ".join(cmd)
        self.assertIn("adlc_self_improve_core.py", text)
        self.assertIn("--max-rounds", cmd)


if __name__ == "__main__":
    unittest.main()

