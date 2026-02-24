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

import resolve_workflow


class WorkflowDispatchTests(unittest.TestCase):
    def test_registry_contains_orchestrator_workflow(self) -> None:
        index_path = ROOT / "workflow_registry" / "index.json"
        doc = json.loads(index_path.read_text(encoding="utf-8"))
        ids = {str(row.get("id", "")) for row in doc.get("workflows", [])}
        self.assertEqual(ids, {"wf_orchestrator_only"})
        fallback = str(doc.get("resolver_policy", {}).get("fallback_workflow_id", ""))
        self.assertEqual(fallback, "wf_orchestrator_only")

    def test_resolve_selects_orchestrator_workflow(self) -> None:
        result = resolve_workflow.resolve(goal="headless-lite", repo=ROOT)
        self.assertEqual(result.get("selected_workflow_id"), "wf_orchestrator_only")
        self.assertEqual(result.get("selected_path"), "workflow_registry/wf_minimal_patch_verify/recipe.yaml")


if __name__ == "__main__":
    unittest.main()
