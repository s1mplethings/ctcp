from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.providers.project_generation_business_templates import _launcher_script
from tools.providers.project_generation_artifacts import (
    build_default_context_request,
    normalize_output_contract_freeze,
    normalize_source_generation,
)
from tools.providers.project_generation_source_helpers import (
    EVIDENCE_CARD_VISUAL_TYPE,
    REAL_UI_VISUAL_TYPE,
    _capture_visual_evidence,
)
from tools.providers.project_generation_validation import generic_validation


FIXED_NARRATIVE_GOAL = (
    "我想要生成一个可以帮助创作者制作叙事项目的助手。"
    "它重点服务悬疑 / 解谜 / 猎奇风格，并能梳理故事线、角色关系、章节结构和提示词导出。"
)
GENERIC_GOAL = "请生成一个工具库型项目，用于整理任务规划和 JSON 导出。"
WEB_SERVICE_GOAL = "请生成一个本地 HTTP 服务 MVP，用于把模糊项目目标整理成结构化 spec、workflow plan 和 acceptance 摘要 JSON。"
DATA_PIPELINE_GOAL = "请生成一个数据处理 pipeline MVP，用于把原始项目目标转换成结构化 spec、sample output 和 acceptance 报告。"
ANNOTATION_WORKBENCH_GOAL = (
    "Build a local interactive Annotation Review Workbench that loads an image folder, lets users create/move/resize/delete "
    "bounding boxes with labels, track per-image review status and notes, autosave/restore state, and export YOLO annotations with a stats report."
)
PRODUCTION_GUI_NARRATIVE_GOAL = (
    "做一个本地可运行的 VN 项目助手 MVP："
    "输入角色资料、章节大纲、场景列表，生成一个可视化整理工具。"
    "这个工具至少要能管理角色卡、管理章节和场景卡、绑定背景和立绘占位、"
    "展示剧情流程顺序、导出基础的 Ren'Py 风格脚本骨架或结构化 JSON，并提供一个最小可用界面。"
)


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ProjectGenerationArtifactTests(unittest.TestCase):
    def test_narrative_launcher_script_is_python_parseable_for_gui_shape(self) -> None:
        script = _launcher_script(
            package_name="vn_mvp_ren_py_json",
            mode_label="Narrative project launcher.",
            startup_rel="scripts/run_project_gui.py",
        )
        ast.parse(script, filename="run_project_gui.py")
        self.assertIn("def main() -> int:", script)
        self.assertIn("if not args.headless and len(sys.argv) == 1:", script)

    def test_generic_validation_rejects_syntax_invalid_python_business_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_syntax_invalid_") as td:
            run_dir = Path(td)
            entry = run_dir / "project_output" / "broken-project" / "scripts" / "run_project_gui.py"
            readme = run_dir / "project_output" / "broken-project" / "README.md"
            entry.parent.mkdir(parents=True, exist_ok=True)
            readme.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text("from __future__ import annotations\n    import sys\n", encoding="utf-8")
            readme.write_text("# Broken Project\n\npython scripts/run_project_gui.py --help\n", encoding="utf-8")

            doc = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/broken-project/scripts/run_project_gui.py",
                startup_readme="project_output/broken-project/README.md",
                generated_business_files=["project_output/broken-project/scripts/run_project_gui.py"],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/broken-project/README.md"],
            )

            self.assertFalse(bool(doc.get("passed", False)))
            syntax = dict(doc.get("python_syntax", {}))
            self.assertFalse(bool(syntax.get("passed", False)))
            self.assertEqual(
                [row["path"] for row in syntax.get("syntax_errors", []) if isinstance(row, dict)],
                ["project_output/broken-project/scripts/run_project_gui.py"],
            )

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
        self.assertEqual(
            [str(dict(row).get("name", "")) for row in list(dict(doc.get("pipeline_contract", {})).get("stages", [])) if isinstance(row, dict)],
            [
                "project_intent",
                "spec",
                "scaffold",
                "core_feature_implementation",
                "smoke_run",
                "demo_evidence",
                "delivery_package",
            ],
        )
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

    def test_source_generation_production_narrative_gui_goal_generates_parseable_launcher(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_prod_gui_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": PRODUCTION_GUI_NARRATIVE_GOAL,
                    "constraints": {
                        "project_domain": "story_reasoning_game",
                        "story_knowledge_ops": "required",
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)
            self.assertEqual(str(contract.get("project_type", "")), "narrative_copilot")
            self.assertEqual(str(contract.get("delivery_shape", "")), "gui_first")
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": PRODUCTION_GUI_NARRATIVE_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "production narrative gui context",
                    "files": [
                        {"path": "docs/41_low_capability_project_generation.md", "why": "contract", "content": "production and benchmark split"},
                        {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "manifest fields and delivery bridge"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "generic_validation and runtime probes"},
                        {"path": "scripts/project_manifest_bridge.py", "why": "bridge", "content": "project_manifest fields"},
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "fixed stage order"},
                    ],
                    "omitted": [],
                },
            )
            project_root = run_dir / "project_output" / str(contract.get("project_id", "vn-project"))
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

            report = normalize_source_generation(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)

            self.assertEqual(report.get("status"), "pass", msg=json.dumps(report, ensure_ascii=False))
            self.assertTrue(bool(dict(report.get("generic_validation", {})).get("passed", False)))
            self.assertEqual(str(report.get("visual_evidence_status", "")), "provided")
            self.assertEqual(str(report.get("visual_type", "")), REAL_UI_VISUAL_TYPE)
            visual_files = [str(x) for x in list(report.get("visual_evidence_files", [])) if str(x).strip()]
            self.assertTrue(visual_files)
            screenshot_path = run_dir / visual_files[0]
            self.assertEqual(screenshot_path.name, "final-ui.png")
            self.assertTrue(screenshot_path.exists(), msg=str(screenshot_path))
            self.assertEqual(screenshot_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            capture = dict(report.get("visual_evidence_capture", {}))
            self.assertEqual(str(capture.get("visual_type", "")), REAL_UI_VISUAL_TYPE)
            self.assertTrue(str(capture.get("preview_source", "")).strip())
            syntax = dict(dict(report.get("generic_validation", {})).get("python_syntax", {}))
            self.assertTrue(bool(syntax.get("passed", False)))
            launcher = project_root / "scripts" / "run_project_gui.py"
            self.assertTrue(launcher.exists())
            ast.parse(launcher.read_text(encoding="utf-8"), filename=str(launcher))

            help_proc = subprocess.run(
                [sys.executable, str(launcher), "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            self.assertEqual(help_proc.returncode, 0, msg=help_proc.stderr or help_proc.stdout)

            with tempfile.TemporaryDirectory(prefix="ctcp_pg_prod_gui_export_") as export_td:
                export_proc = subprocess.run(
                    [
                        sys.executable,
                        str(launcher),
                        "--goal",
                        "vn smoke export",
                        "--project-name",
                        "VN Copilot",
                        "--out",
                        export_td,
                        "--headless",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                )
                self.assertEqual(export_proc.returncode, 0, msg=export_proc.stderr or export_proc.stdout)
                export_doc = json.loads(export_proc.stdout)
                for key in ("project_bundle_json", "asset_prompts_json", "project_outline_md"):
                    self.assertIn(key, export_doc)
                    self.assertTrue(Path(str(export_doc[key])).exists(), msg=key)

    def test_build_default_context_request_expands_project_generation_inputs(self) -> None:
        request = build_default_context_request(FIXED_NARRATIVE_GOAL)
        paths = {str(dict(item).get("path", "")) for item in list(request.get("needs", [])) if isinstance(item, dict)}
        self.assertIn("AGENTS.md", paths)
        self.assertIn("README.md", paths)
        self.assertIn("docs/01_north_star.md", paths)
        self.assertIn("workflow_registry/wf_project_generation_manifest/recipe.yaml", paths)
        self.assertIn("tools/providers/project_generation_artifacts.py", paths)
        self.assertIn("scripts/ctcp_dispatch.py", paths)
        self.assertIn("scripts/ctcp_front_bridge.py", paths)
        self.assertIn("scripts/project_generation_gate.py", paths)
        self.assertGreaterEqual(int(dict(request.get("budget", {})).get("max_files", 0) or 0), 14)

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

    def test_source_generation_generic_gui_goal_accepts_headless_export_probe(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_generic_gui_") as td:
            run_dir = Path(td)
            gui_goal = "Build a local GUI project workbench that exports a structured acceptance bundle."
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": gui_goal,
                    "constraints": {"delivery_shape": "gui_first"},
                    "project_intent": {
                        "goal_summary": "Generate a local GUI workbench MVP",
                        "target_user": "internal operator",
                        "problem_to_solve": "run a local GUI-first project shell that still supports headless export for verify",
                        "mvp_scope": ["local launcher", "headless export path", "acceptance bundle export"],
                        "required_inputs": ["goal text"],
                        "required_outputs": ["project bundle json", "workflow plan json", "acceptance report json"],
                        "hard_constraints": ["delivery_shape=gui_first"],
                        "assumptions": ["GUI-first projects still need a scripted export path"],
                        "open_questions": [],
                        "acceptance_criteria": ["headless export probe passes", "source_generation reaches pass"],
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=gui_goal, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": gui_goal,
                    "repo_slug": "ctcp",
                    "summary": "generic gui project generation context",
                    "files": [
                        {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "project manifest readable api"},
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "source_generation deliver"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "generic validation"},
                        {"path": "scripts/project_manifest_bridge.py", "why": "bridge", "content": "manifest fields"},
                    ],
                    "omitted": [],
                },
            )
            project_root = run_dir / "project_output" / str(contract.get("project_id", "project-copilot"))
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

            report = normalize_source_generation(None, goal=gui_goal, run_dir=run_dir)

            self.assertEqual(report.get("status"), "pass", msg=json.dumps(report, ensure_ascii=False))
            export_probe = dict(dict(report.get("behavioral_checks", {})).get("export_probe", {}))
            self.assertEqual(int(export_probe.get("rc", 1)), 0)
            self.assertIn("--headless", str(export_probe.get("command", "")))

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
            self.assertEqual(str(report.get("visual_evidence_status", "")), "provided")
            self.assertEqual(str(report.get("visual_type", "")), REAL_UI_VISUAL_TYPE)
            visual_files = [str(x) for x in list(report.get("visual_evidence_files", [])) if str(x).strip()]
            self.assertTrue(visual_files)
            screenshot_path = run_dir / visual_files[0]
            self.assertEqual(screenshot_path.name, "final-ui.png")
            self.assertTrue(screenshot_path.exists(), msg=str(screenshot_path))
            self.assertEqual(screenshot_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            capture = dict(report.get("visual_evidence_capture", {}))
            self.assertEqual(str(capture.get("visual_type", "")), REAL_UI_VISUAL_TYPE)
            self.assertTrue(str(capture.get("preview_source", "")).strip())
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

    def test_capture_visual_evidence_falls_back_to_evidence_card_when_real_page_capture_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_visual_fallback_") as td:
            run_dir = Path(td)
            export_dir = run_dir / "tmp_export"
            export_dir.mkdir(parents=True, exist_ok=True)
            (export_dir / "deliverables").mkdir(parents=True, exist_ok=True)
            (export_dir / "deliverables" / "project_bundle.json").write_text(
                json.dumps({"project_name": "Fallback Demo", "routes": ["/health", "/generate"]}, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            with mock.patch(
                "tools.providers.project_generation_source_helpers._capture_html_page_screenshot",
                return_value=(False, "browser unavailable"),
            ):
                result = _capture_visual_evidence(
                    run_dir=run_dir,
                    project_root="project_output/demo",
                    delivery_shape="web_first",
                    entry_script="project_output/demo/scripts/run_project_web.py",
                    behavior_probe={"rc": 0},
                    export_probe={"rc": 0},
                    export_dir=export_dir,
                )

            self.assertEqual(str(result.get("status", "")), "provided")
            self.assertEqual(str(result.get("visual_type", "")), EVIDENCE_CARD_VISUAL_TYPE)
            files = [str(x) for x in list(result.get("files", [])) if str(x).strip()]
            self.assertTrue(files)
            self.assertTrue((run_dir / files[0]).exists())

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

    def test_source_generation_annotation_workbench_fallback_is_blocked_by_product_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_annotation_workbench_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": ANNOTATION_WORKBENCH_GOAL,
                    "constraints": {"delivery_shape": "gui_first"},
                    "project_intent": {
                        "goal_summary": "Generate a local interactive annotation review workbench",
                        "target_user": "image annotation operator or reviewer",
                        "problem_to_solve": "load image folders, create and review bounding boxes, persist project state, and export standard annotations locally",
                        "mvp_scope": [
                            "select image folder and browse image list",
                            "draw/select/move/resize/delete bounding boxes",
                            "assign class labels to boxes",
                            "set image status and notes",
                            "undo redo save and autosave restore",
                            "export YOLO annotations and stats report",
                        ],
                        "required_inputs": ["local image folder with at least jpg png images"],
                        "required_outputs": ["saved project state", "YOLO annotation export", "stats report", "high-value UI evidence"],
                        "hard_constraints": ["local runnable project", "strong interactive UI", "delivery_shape=gui_first"],
                        "assumptions": ["single-user local workflow", "desktop-style interaction is acceptable"],
                        "open_questions": [],
                        "acceptance_criteria": [
                            "can load at least three images",
                            "can create move resize and delete boxes",
                            "can save and reopen state",
                            "can export YOLO plus stats report",
                        ],
                    },
                    "attachments": [],
                },
            )
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": ANNOTATION_WORKBENCH_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "annotation workbench generation context",
                    "files": [
                        {"path": "docs/backend_interface_contract.md", "why": "contract", "content": "project manifest readable api"},
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "source_generation deliver"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "generic validation and product capability validation"},
                        {"path": "scripts/project_manifest_bridge.py", "why": "bridge", "content": "manifest fields"},
                    ],
                    "omitted": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=ANNOTATION_WORKBENCH_GOAL, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            project_root = run_dir / "project_output" / str(contract.get("project_id", "annotation-workbench"))
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})

            report = normalize_source_generation(None, goal=ANNOTATION_WORKBENCH_GOAL, run_dir=run_dir)

            self.assertEqual(str(report.get("project_type", "")), "generic_copilot")
            self.assertEqual(str(report.get("project_archetype", "")), "generic_copilot")
            self.assertEqual(report.get("status"), "blocked", msg=json.dumps(report, ensure_ascii=False))
            product_validation = dict(report.get("product_validation", {}))
            self.assertTrue(bool(product_validation.get("required", False)))
            self.assertFalse(bool(product_validation.get("passed", True)))
            self.assertTrue(bool(product_validation.get("fallback_detected", False)))
            self.assertIn("high-interaction request degraded to generic_copilot/generic fallback", list(product_validation.get("reasons", [])))
            self.assertIn("bbox editing capability missing", list(product_validation.get("missing", [])))


if __name__ == "__main__":
    unittest.main()

