from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.providers.project_generation_artifacts import (
    build_default_context_request,
    normalize_output_contract_freeze,
    normalize_source_generation,
)


FIXED_NARRATIVE_GOAL = (
    "我想要生成一个可以帮助创作者制作叙事项目的助手。"
    "它重点服务悬疑 / 解谜 / 猎奇风格，并能梳理故事线、角色关系、章节结构和提示词导出。"
)
GENERIC_GOAL = "请生成一个工具库型项目，用于整理任务规划和 JSON 导出。"


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ProjectGenerationArtifactTests(unittest.TestCase):
    def test_output_contract_freeze_production_narrative_request_is_not_benchmark_default(self) -> None:
        doc = normalize_output_contract_freeze(None, goal=FIXED_NARRATIVE_GOAL)
        self.assertEqual(doc.get("project_type"), "narrative_copilot")
        self.assertEqual(doc.get("execution_mode"), "production")
        self.assertEqual(doc.get("project_profile"), "narrative_copilot")
        self.assertFalse(bool(doc.get("benchmark_sample_applied", False)))
        self.assertIn(str(doc.get("delivery_shape", "")), {"cli_first", "gui_first", "web_first", "tool_library_first"})
        business_files = list(doc.get("business_files", []))
        self.assertNotIn("project_output/narrative-copilot/src/narrative_copilot/story/chapter_planner.py", business_files)
        self.assertTrue(any("/story/stage_planner.py" in row for row in business_files))

    def test_output_contract_freeze_generic_goal_prefers_tool_shape(self) -> None:
        doc = normalize_output_contract_freeze(None, goal=GENERIC_GOAL)
        self.assertEqual(doc.get("project_type"), "generic_copilot")
        self.assertEqual(doc.get("execution_mode"), "production")
        self.assertEqual(doc.get("delivery_shape"), "tool_library_first")
        self.assertEqual(doc.get("startup_entrypoint"), f"{doc.get('project_root')}/src/{doc.get('package_name')}/service.py")

    def test_output_contract_freeze_benchmark_mode_keeps_fixed_narrative_sample(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_contract_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": FIXED_NARRATIVE_GOAL,
                    "constraints": {
                        "project_generation_mode": "benchmark_regression",
                        "benchmark_case": "narrative_fixed_project_generation_regression",
                    },
                    "attachments": [],
                },
            )
            doc = normalize_output_contract_freeze(None, goal=FIXED_NARRATIVE_GOAL, run_dir=run_dir)
        self.assertEqual(doc.get("execution_mode"), "benchmark_regression")
        self.assertTrue(bool(doc.get("benchmark_sample_applied", False)))
        self.assertEqual(doc.get("project_profile"), "narrative_copilot_benchmark")
        business_files = list(doc.get("business_files", []))
        self.assertIn("project_output/narrative-copilot/src/narrative_copilot/story/outline.py", business_files)
        self.assertIn("project_output/narrative-copilot/src/narrative_copilot/cast/schema.py", business_files)
        self.assertIn("project_output/narrative-copilot/src/narrative_copilot/pipeline/prompt_pipeline.py", business_files)
        self.assertIn("project_output/narrative-copilot/src/narrative_copilot/exporters/deliver.py", business_files)
        self.assertIn("project_output/narrative-copilot/src/narrative_copilot/service.py", business_files)
        self.assertIn("project_output/narrative-copilot/tests/test_narrative_copilot_service.py", business_files)

    def test_source_generation_consumes_context_pack_and_materializes_business_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_artifacts_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": FIXED_NARRATIVE_GOAL,
                    "constraints": {
                        "project_generation_mode": "benchmark_regression",
                        "benchmark_case": "narrative_fixed_project_generation_regression",
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=FIXED_NARRATIVE_GOAL, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": FIXED_NARRATIVE_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "narrative business context",
                    "files": [
                        {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "project generation manifest narrative"},
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "source_generation"},
                        {"path": "tools/providers/project_generation_artifacts.py", "why": "provider", "content": "narrative_copilot"},
                        {"path": "tools/providers/api_agent.py", "why": "provider", "content": "file_request"},
                        {"path": "scripts/ctcp_dispatch.py", "why": "dispatch", "content": "project_generation"},
                        {"path": "scripts/ctcp_front_bridge.py", "why": "bridge", "content": "get_project_manifest"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "business_codegen_used"},
                        {"path": "scripts/ctcp_librarian.py", "why": "librarian", "content": "context_pack"},
                    ],
                    "omitted": [],
                },
            )
            project_root = run_dir / "project_output" / "narrative-copilot"
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

            report = normalize_source_generation(None, goal=FIXED_NARRATIVE_GOAL, run_dir=run_dir)

            self.assertEqual(report.get("status"), "pass", msg=json.dumps(report, ensure_ascii=False))
            self.assertTrue(report.get("business_codegen_used"))
            self.assertTrue(report.get("consumed_context_pack"))
            self.assertTrue(list(report.get("consumed_context_files", [])))
            self.assertTrue(list(report.get("context_influence_summary", [])))
            self.assertTrue(list(report.get("business_files_generated", [])))
            self.assertEqual(list(report.get("business_files_missing", [])), [])
            self.assertEqual(report.get("execution_mode"), "benchmark_regression")
            self.assertTrue(bool(dict(report.get("gate_layers", {})).get("structural", {}).get("passed", False)))
            self.assertTrue(bool(dict(report.get("gate_layers", {})).get("behavioral", {}).get("passed", False)))
            self.assertTrue(bool(dict(report.get("gate_layers", {})).get("result", {}).get("passed", False)))
            self.assertEqual(int(dict(dict(report.get("behavioral_checks", {})).get("startup_probe", {})).get("rc", 1)), 0)
            self.assertEqual(int(dict(dict(report.get("behavioral_checks", {})).get("export_probe", {})).get("rc", 1)), 0)
            self.assertTrue((project_root / "src" / "narrative_copilot" / "story" / "outline.py").exists())
            self.assertTrue((project_root / "src" / "narrative_copilot" / "cast" / "schema.py").exists())
            self.assertTrue((project_root / "src" / "narrative_copilot" / "pipeline" / "prompt_pipeline.py").exists())
            self.assertTrue((project_root / "src" / "narrative_copilot" / "exporters" / "deliver.py").exists())
            self.assertTrue((project_root / "src" / "narrative_copilot" / "service.py").exists())
            self.assertTrue((project_root / "tests" / "test_narrative_copilot_service.py").exists())

            with tempfile.TemporaryDirectory(prefix="ctcp_pg_benchmark_export_") as export_td:
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(project_root / "scripts" / "run_narrative_copilot.py"),
                        "--goal",
                        "benchmark narrative export",
                        "--project-name",
                        "Benchmark Narrative Copilot",
                        "--out",
                        export_td,
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
                export_doc = json.loads(proc.stdout)
                for key in (
                    "story_bible_json",
                    "characters_json",
                    "outline_json",
                    "scene_cards_json",
                    "art_prompts_json",
                    "demo_script_md",
                ):
                    self.assertIn(key, export_doc)
                    self.assertTrue(Path(str(export_doc[key])).exists(), msg=key)

    def test_build_default_context_request_expands_project_generation_inputs(self) -> None:
        request = build_default_context_request(FIXED_NARRATIVE_GOAL)
        paths = {str(dict(item).get("path", "")) for item in list(request.get("needs", [])) if isinstance(item, dict)}
        self.assertIn("README.md", paths)
        self.assertIn("workflow_registry/wf_project_generation_manifest/recipe.yaml", paths)
        self.assertIn("tools/providers/project_generation_artifacts.py", paths)
        self.assertIn("scripts/ctcp_dispatch.py", paths)
        self.assertIn("scripts/ctcp_front_bridge.py", paths)
        self.assertIn("scripts/project_generation_gate.py", paths)
        self.assertGreaterEqual(int(dict(request.get("budget", {})).get("max_files", 0) or 0), 12)


if __name__ == "__main__":
    unittest.main()

