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
WEB_SERVICE_GOAL = "请生成一个本地 HTTP 服务 MVP，用于把模糊项目目标整理成结构化 spec、workflow plan 和 acceptance 摘要 JSON。"
DATA_PIPELINE_GOAL = "请生成一个数据处理 pipeline MVP，用于把原始项目目标转换成结构化 spec、sample output 和 acceptance 报告。"


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ProjectGenerationArtifactTests(unittest.TestCase):
    def test_output_contract_freeze_production_narrative_request_is_not_benchmark_default(self) -> None:
        doc = normalize_output_contract_freeze(None, goal=FIXED_NARRATIVE_GOAL)
        self.assertEqual(doc.get("project_type"), "narrative_copilot")
        self.assertEqual(doc.get("execution_mode"), "production")
        self.assertEqual(doc.get("project_profile"), "narrative_copilot")
        self.assertIn("project_intent", doc)
        self.assertIn("project_spec", doc)
        self.assertIn("pipeline_contract", doc)
        self.assertFalse(bool(doc.get("benchmark_sample_applied", False)))
        self.assertIn(str(doc.get("delivery_shape", "")), {"cli_first", "gui_first", "web_first", "tool_library_first"})
        business_files = list(doc.get("business_files", []))
        self.assertNotIn("project_output/narrative-copilot/src/narrative_copilot/story/chapter_planner.py", business_files)
        self.assertTrue(any("/story/stage_planner.py" in row for row in business_files))

    def test_output_contract_freeze_generic_goal_prefers_tool_shape(self) -> None:
        doc = normalize_output_contract_freeze(None, goal=GENERIC_GOAL)
        self.assertEqual(doc.get("project_type"), "generic_copilot")
        self.assertEqual(doc.get("project_archetype"), "cli_toolkit")
        self.assertEqual(doc.get("execution_mode"), "production")
        self.assertEqual(doc.get("delivery_shape"), "tool_library_first")
        self.assertEqual(doc.get("startup_entrypoint"), f"{doc.get('project_root')}/src/{doc.get('package_name')}/service.py")

    def test_output_contract_freeze_web_service_goal_prefers_web_shape(self) -> None:
        doc = normalize_output_contract_freeze(None, goal=WEB_SERVICE_GOAL)
        self.assertEqual(doc.get("project_type"), "generic_copilot")
        self.assertEqual(doc.get("project_archetype"), "web_service")
        self.assertEqual(doc.get("delivery_shape"), "web_first")

    def test_output_contract_freeze_data_pipeline_goal_prefers_data_pipeline_archetype(self) -> None:
        doc = normalize_output_contract_freeze(None, goal=DATA_PIPELINE_GOAL)
        self.assertEqual(doc.get("project_type"), "generic_copilot")
        self.assertEqual(doc.get("project_archetype"), "data_pipeline")

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
            self.assertTrue(bool(dict(report.get("generic_validation", {})).get("passed", False)))
            self.assertTrue(bool(dict(report.get("domain_validation", {})).get("passed", False)))
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

    def test_source_generation_generic_goal_exports_spec_and_workflow_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_generic_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": GENERIC_GOAL,
                    "constraints": {"delivery_shape": "tool_library_first"},
                    "project_intent": {
                        "goal_summary": "生成一个任务规划和 JSON 导出的工具库 MVP",
                        "target_user": "内部项目操作者",
                        "problem_to_solve": "把模糊任务整理目标转成一个可运行的结构化导出工具",
                        "mvp_scope": ["接收目标", "产出结构化 spec", "导出 workflow 与 acceptance artifacts"],
                        "required_inputs": ["用户目标"],
                        "required_outputs": ["spec json", "workflow json", "acceptance json"],
                        "hard_constraints": ["delivery_shape=tool_library_first"],
                        "assumptions": ["先交付最小可运行工具库"],
                        "open_questions": [],
                        "acceptance_criteria": ["工具库可以生成 spec/workflow/acceptance 三类结果"],
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=GENERIC_GOAL, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": GENERIC_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "generic project generation context",
                    "files": [
                        {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "project manifest readable api"},
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "source_generation deliver"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "generic validation"},
                        {"path": "scripts/project_manifest_bridge.py", "why": "bridge", "content": "manifest fields"},
                        {"path": "artifacts/frontend_uploads/brief.txt", "why": "input", "content": "任务规划 JSON 导出工具库，强调 spec 和 workflow 输出"},
                    ],
                    "omitted": [],
                },
            )
            project_root = run_dir / "project_output" / str(contract.get("project_id", "project-copilot"))
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

            report = normalize_source_generation(None, goal=GENERIC_GOAL, run_dir=run_dir)
            self.assertEqual(report.get("status"), "pass", msg=json.dumps(report, ensure_ascii=False))
            self.assertTrue(bool(dict(report.get("generic_validation", {})).get("passed", False)))
            self.assertEqual(str(report.get("project_archetype", "")), "cli_toolkit")
            self.assertEqual(str(dict(report.get("domain_validation", {})).get("kind", "")), "cli_toolkit")
            package_name = str(contract.get("package_name", "project_copilot"))
            self.assertTrue((project_root / "src" / package_name / "seed.py").exists())
            self.assertTrue((project_root / "src" / package_name / "spec_builder.py").exists())
            self.assertTrue((project_root / "src" / package_name / "commands.py").exists())
            self.assertTrue((project_root / "src" / package_name / "exporter.py").exists())

            with tempfile.TemporaryDirectory(prefix="ctcp_pg_generic_export_") as export_td:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import json, sys; "
                            f"sys.path.insert(0, r'{project_root / 'src'}'); "
                            f"from {package_name}.service import generate_project; "
                            f"result = generate_project(goal='smoke export', project_name='Project Copilot', out_dir=__import__('pathlib').Path(r'{export_td}')); "
                            "print(json.dumps(result, ensure_ascii=False))"
                        ),
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
                export_doc = json.loads(proc.stdout)
                for key in ("mvp_spec_json", "cli_command_plan_json", "operator_checklist_md", "acceptance_report_json"):
                    self.assertIn(key, export_doc)
                    self.assertTrue(Path(str(export_doc[key])).exists(), msg=key)

    def test_source_generation_web_service_goal_exports_service_contract_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_web_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": WEB_SERVICE_GOAL,
                    "constraints": {"delivery_shape": "web_first"},
                    "project_intent": {
                        "goal_summary": "生成一个本地 HTTP 服务 MVP",
                        "target_user": "内部项目操作者",
                        "problem_to_solve": "把模糊项目目标转换成结构化 spec/workflow/acceptance JSON 响应",
                        "mvp_scope": ["接收 goal", "返回结构化 JSON", "提供 health 与 generate 两条服务路径"],
                        "required_inputs": ["用户目标"],
                        "required_outputs": ["service contract", "sample response", "acceptance report"],
                        "hard_constraints": ["delivery_shape=web_first"],
                        "assumptions": ["先做本地可运行服务 MVP"],
                        "open_questions": [],
                        "acceptance_criteria": ["可返回 health payload", "可导出 service contract 与 sample response"],
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=WEB_SERVICE_GOAL, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": WEB_SERVICE_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "web service generation context",
                    "files": [
                        {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "project manifest readable api"},
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "source_generation deliver"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "web_service validation"},
                        {"path": "scripts/project_manifest_bridge.py", "why": "bridge", "content": "manifest fields"},
                        {"path": "artifacts/frontend_uploads/brief.txt", "why": "input", "content": "本地 HTTP service, health route, generate route, sample response"},
                    ],
                    "omitted": [],
                },
            )
            project_root = run_dir / "project_output" / str(contract.get("project_id", "project-copilot"))
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

            report = normalize_source_generation(None, goal=WEB_SERVICE_GOAL, run_dir=run_dir)
            self.assertEqual(report.get("status"), "pass", msg=json.dumps(report, ensure_ascii=False))
            self.assertEqual(str(report.get("project_archetype", "")), "web_service")
            self.assertEqual(str(dict(report.get("domain_validation", {})).get("kind", "")), "web_service")
            package_name = str(contract.get("package_name", "project_copilot"))
            self.assertTrue((project_root / "src" / package_name / "service_contract.py").exists())
            self.assertTrue((project_root / "src" / package_name / "app.py").exists())

            serve = subprocess.run(
                [sys.executable, str(project_root / "scripts" / "run_project_web.py"), "--serve"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(serve.returncode, 0, msg=serve.stderr or serve.stdout)
            serve_doc = json.loads(serve.stdout)
            self.assertEqual(serve_doc.get("status"), "ok")

            with tempfile.TemporaryDirectory(prefix="ctcp_pg_web_export_") as export_td:
                proc = subprocess.run(
                    [sys.executable, str(project_root / "scripts" / "run_project_web.py"), "--goal", "web smoke export", "--project-name", "Web Copilot", "--out", export_td],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
                export_doc = json.loads(proc.stdout)
                for key in ("mvp_spec_json", "service_contract_json", "sample_response_json", "acceptance_report_json", "delivery_summary_md"):
                    self.assertIn(key, export_doc)
                    self.assertTrue(Path(str(export_doc[key])).exists(), msg=key)

    def test_source_generation_data_pipeline_goal_exports_pipeline_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_pipeline_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": DATA_PIPELINE_GOAL,
                    "constraints": {"delivery_shape": "cli_first"},
                    "project_intent": {
                        "goal_summary": "生成一个数据处理 pipeline MVP",
                        "target_user": "内部项目操作者",
                        "problem_to_solve": "把原始目标输入整理成 sample output 与 acceptance 结果",
                        "mvp_scope": ["接收输入目标", "输出 sample input/output", "导出 acceptance report"],
                        "required_inputs": ["用户目标"],
                        "required_outputs": ["pipeline plan", "sample input", "sample output", "acceptance report"],
                        "hard_constraints": ["delivery_shape=cli_first"],
                        "assumptions": ["先做本地 smoke run pipeline"],
                        "open_questions": [],
                        "acceptance_criteria": ["可导出 sample output", "pipeline 结果可读", "README 可指导运行"],
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=DATA_PIPELINE_GOAL, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": DATA_PIPELINE_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "data pipeline generation context",
                    "files": [
                        {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "project manifest readable api"},
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "source_generation deliver"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "data_pipeline validation"},
                        {"path": "scripts/project_manifest_bridge.py", "why": "bridge", "content": "manifest fields"},
                        {"path": "artifacts/frontend_uploads/brief.txt", "why": "input", "content": "数据 pipeline, transform, sample output, acceptance report"},
                    ],
                    "omitted": [],
                },
            )
            project_root = run_dir / "project_output" / str(contract.get("project_id", "project-copilot"))
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

            report = normalize_source_generation(None, goal=DATA_PIPELINE_GOAL, run_dir=run_dir)
            self.assertEqual(report.get("status"), "pass", msg=json.dumps(report, ensure_ascii=False))
            self.assertEqual(str(report.get("project_archetype", "")), "data_pipeline")
            self.assertEqual(str(dict(report.get("domain_validation", {})).get("kind", "")), "data_pipeline")
            package_name = str(contract.get("package_name", "project_copilot"))
            self.assertTrue((project_root / "src" / package_name / "transforms.py").exists())
            self.assertTrue((project_root / "src" / package_name / "pipeline.py").exists())

            with tempfile.TemporaryDirectory(prefix="ctcp_pg_pipeline_export_") as export_td:
                proc = subprocess.run(
                    [sys.executable, str(project_root / "scripts" / "run_project_cli.py"), "--goal", "pipeline smoke export", "--project-name", "Pipeline Copilot", "--out", export_td],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
                export_doc = json.loads(proc.stdout)
                for key in ("mvp_spec_json", "pipeline_plan_json", "sample_input_json", "sample_output_json", "acceptance_report_json"):
                    self.assertIn(key, export_doc)
                    self.assertTrue(Path(str(export_doc[key])).exists(), msg=key)


if __name__ == "__main__":
    unittest.main()

