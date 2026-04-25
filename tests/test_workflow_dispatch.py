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
        self.assertIn("wf_orchestrator_only", ids)
        self.assertIn("wf_project_generation_manifest", ids)
        fallback = str(doc.get("resolver_policy", {}).get("fallback_workflow_id", ""))
        self.assertEqual(fallback, "wf_orchestrator_only")

    def test_resolve_selects_orchestrator_workflow(self) -> None:
        result = resolve_workflow.resolve(goal="headless-lite", repo=ROOT)
        self.assertEqual(result.get("selected_workflow_id"), "wf_orchestrator_only")
        self.assertEqual(result.get("selected_path"), "workflow_registry/wf_minimal_patch_verify/recipe.yaml")

    def test_resolve_selects_project_generation_workflow_for_runnable_delivery_goal(self) -> None:
        result = resolve_workflow.resolve(
            goal="请直接开始，做一个本地可运行的单文件 HTML 页面并最终 zip 交付。",
            repo=ROOT,
        )
        self.assertEqual(result.get("selected_workflow_id"), "wf_project_generation_manifest")
        self.assertEqual(result.get("selected_path"), "workflow_registry/wf_project_generation_manifest/recipe.yaml")
        self.assertTrue(bool(dict(result.get("decision", {})).get("project_generation_goal", False)))

    def test_resolve_selects_project_generation_workflow_for_domain_lift_rerun_request(self) -> None:
        result = resolve_workflow.resolve(
            goal=(
                "绑定一个新任务：Indie Studio Hub Domain Lift。不要再只做 team_task_pm_web。"
                "用同类粗目标重跑生成测试，区分 internal_runtime_status 和 user_acceptance_status，"
                "并强化 Asset/Bug/Build-Release/Docs/10+ screenshots 的 coverage gate。"
            ),
            repo=ROOT,
        )
        self.assertEqual(result.get("selected_workflow_id"), "wf_project_generation_manifest")
        self.assertTrue(bool(dict(result.get("decision", {})).get("project_generation_goal", False)))


if __name__ == "__main__":
    unittest.main()
