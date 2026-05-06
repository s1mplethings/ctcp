from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.providers.project_generation_artifacts import (
    build_default_context_request,
    normalize_deliverable_index,
    normalize_output_contract_freeze,
    normalize_project_manifest,
    normalize_source_generation,
)
from tools.providers.project_generation_decisions import default_package_name
from tools.providers.project_generation_sample_metrics import narrative_sample_metrics
from tools.providers.project_generation_source_helpers import (
    EVIDENCE_CARD_VISUAL_TYPE,
    REAL_UI_VISUAL_TYPE,
    _capture_visual_evidence,
    build_runtime_checks,
)
from tools.providers.project_generation_source_stage import _ensure_provider_package_init_files, _provider_source_file_rows
from tools.providers.project_generation_validation import generic_validation
from tools.providers.project_generation_validation import (
    domain_validation,
    narrative_source_map_validation,
    readme_quality_validation,
    ux_validation,
)
from ctcp_adapters import ctcp_artifact_normalizers as artifact_normalizers


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


def _materialize_production_narrative_project(
    run_dir: Path,
    *,
    goal: str = PRODUCTION_GUI_NARRATIVE_GOAL,
) -> tuple[dict[str, object], dict[str, object], Path]:
    _write_json(
        run_dir / "artifacts" / "frontend_request.json",
        {
            "schema_version": "ctcp-frontend-request-v1",
            "goal": goal,
            "constraints": {
                "project_domain": "narrative_vn_editor",
                "story_knowledge_ops": "required",
            },
            "attachments": [],
        },
    )
    contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
    _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
    _write_json(
        run_dir / "artifacts" / "context_pack.json",
        {
            "schema_version": "ctcp-context-pack-v1",
            "goal": goal,
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
    report = normalize_source_generation(None, goal=goal, run_dir=run_dir)
    return contract, report, project_root


def _run_launcher_json(*, launcher: Path, out_dir: Path, goal: str, project_name: str, extra_args: list[str] | None = None) -> dict[str, object]:
    proc = subprocess.run(
        [
            sys.executable,
            str(launcher),
            "--goal",
            goal,
            "--project-name",
            project_name,
            "--out",
            str(out_dir),
            "--headless",
            *(extra_args or []),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


class ProjectGenerationArtifactTests(unittest.TestCase):
    def _assert_production_local_templates_disabled(self, report: dict[str, object]) -> None:
        self.assertEqual(report.get("status"), "blocked", msg=json.dumps(report, ensure_ascii=False))
        self.assertIn("local project templates are disabled", str(report.get("blocking_reason", "")))
        file_materialization = dict(report.get("file_materialization", {}))
        self.assertEqual(str(file_materialization.get("strategy", "")), "disabled_local_templates")
        completion = dict(report.get("source_customization_completion", {}))
        self.assertFalse(bool(completion.get("final_delivery_allowed", True)))
        self.assertTrue(bool(completion.get("local_templates_disabled", False)))

    def test_default_package_name_normalizes_digit_leading_and_separator_heavy_ids(self) -> None:
        cases = {
            "5-20-bug": "project_5_20_bug",
            "2026 release-hub": "project_2026_release_hub",
            "build release center": "build_release_center",
            "json": "project_json",
        }
        for project_id, expected in cases.items():
            with self.subTest(project_id=project_id):
                actual = default_package_name(project_id, "generic_copilot", "production", "")
                self.assertEqual(actual, expected)
                self.assertTrue(actual.isidentifier())
                self.assertFalse(actual[0].isdigit())

    def test_output_contract_freeze_indie_studio_hub_prefers_composite_domain(self) -> None:
        goal = (
            "给独立游戏团队用的本地生产协作平台，把任务、素材、Bug、版本进度放一起。"
            "不要只要普通任务看板，需要 Asset Library、Bug Tracker、Build / Release、Docs Center、milestone plan、startup guide、replay guide、mid stage review 和 10+ screenshots。"
        )
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_indie_contract_") as td:
            doc = normalize_output_contract_freeze({}, goal=goal, run_dir=Path(td))
            self.assertEqual(doc.get("project_domain"), "indie_studio_production_hub")
            self.assertEqual(doc.get("scaffold_family"), "indie_studio_hub")
            self.assertEqual(doc.get("project_type"), "indie_studio_hub")
            self.assertEqual(doc.get("project_archetype"), "indie_studio_hub_web")
            self.assertEqual(doc.get("required_pages"), 13)
            self.assertEqual(doc.get("required_screenshots"), 10)
            spec = dict(doc.get("project_spec", {}))
            for view in ("asset_library", "asset_detail", "bug_tracker", "build_release_center", "docs_center"):
                self.assertIn(view, list(spec.get("required_pages_or_views", [])))
            for rel in ("docs/milestone_plan.md", "docs/startup_guide.md", "docs/replay_guide.md", "docs/mid_stage_review.md"):
                self.assertTrue(any(str(path).endswith(rel) for path in list(doc.get("doc_files", []))), rel)

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

    def test_generic_validation_reports_missing_cross_file_import_symbol(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_import_symbol_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "vn"
            package = root / "src" / "vn"
            story = package / "story"
            script = root / "scripts" / "run_project_gui.py"
            readme = root / "README.md"
            story.mkdir(parents=True, exist_ok=True)
            script.parent.mkdir(parents=True, exist_ok=True)
            readme.write_text("# VN\n\npython scripts/run_project_gui.py --help\n", encoding="utf-8")
            script.write_text("from vn.story import StoryOutline\nprint(StoryOutline)\n", encoding="utf-8")
            (package / "__init__.py").write_text("", encoding="utf-8")
            (story / "__init__.py").write_text("from .outline import StoryOutline\n", encoding="utf-8")
            (story / "outline.py").write_text("class OutlineBuilder:\n    pass\n", encoding="utf-8")

            doc = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/vn/scripts/run_project_gui.py",
                startup_readme="project_output/vn/README.md",
                generated_business_files=[
                    "project_output/vn/scripts/run_project_gui.py",
                    "project_output/vn/src/vn/__init__.py",
                    "project_output/vn/src/vn/story/__init__.py",
                    "project_output/vn/src/vn/story/outline.py",
                ],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/vn/README.md"],
            )

            self.assertFalse(bool(doc.get("passed", False)))
            imports = dict(doc.get("python_import_consistency", {}))
            self.assertFalse(bool(imports.get("passed", False)))
            missing = imports.get("missing_symbols", [])
            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0].get("symbol"), "StoryOutline")
            self.assertEqual(missing[0].get("target_module"), "vn.story.outline")

    def test_generic_validation_checks_related_package_init_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_import_init_symbol_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "vn"
            package = root / "src" / "vn"
            assets = package / "assets"
            script = root / "scripts" / "run_project_gui.py"
            readme = root / "README.md"
            assets.mkdir(parents=True, exist_ok=True)
            script.parent.mkdir(parents=True, exist_ok=True)
            readme.write_text("# VN\n\npython scripts/run_project_gui.py --help\n", encoding="utf-8")
            script.write_text("from vn.assets.catalog import list_background_assets\nprint(list_background_assets)\n", encoding="utf-8")
            (package / "__init__.py").write_text("", encoding="utf-8")
            (assets / "__init__.py").write_text("from .catalog import AssetCatalog\n", encoding="utf-8")
            (assets / "catalog.py").write_text("def list_background_assets():\n    return []\n", encoding="utf-8")

            doc = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/vn/scripts/run_project_gui.py",
                startup_readme="project_output/vn/README.md",
                generated_business_files=[
                    "project_output/vn/scripts/run_project_gui.py",
                    "project_output/vn/src/vn/assets/catalog.py",
                ],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/vn/README.md"],
            )

            imports = dict(doc.get("python_import_consistency", {}))
            self.assertFalse(bool(imports.get("passed", False)))
            missing = imports.get("missing_symbols", [])
            self.assertEqual(len(missing), 1)
            self.assertEqual(missing[0].get("from_path"), "project_output/vn/src/vn/assets/__init__.py")
            self.assertEqual(missing[0].get("symbol"), "AssetCatalog")

    def test_generic_validation_reports_provider_interface_contract_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_interface_contract_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "vn"
            package = root / "src" / "vn"
            script = root / "scripts" / "run_project_gui.py"
            readme = root / "README.md"
            package.mkdir(parents=True, exist_ok=True)
            script.parent.mkdir(parents=True, exist_ok=True)
            readme.write_text("# VN\n\npython scripts/run_project_gui.py --help\n", encoding="utf-8")
            script.write_text("from vn import VNService\nprint(VNService)\n", encoding="utf-8")
            (package / "__init__.py").write_text("from .service import VNService\n", encoding="utf-8")
            (package / "service.py").write_text("class VNProjectService:\n    pass\n", encoding="utf-8")

            doc = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/vn/scripts/run_project_gui.py",
                startup_readme="project_output/vn/README.md",
                generated_business_files=[
                    "project_output/vn/scripts/run_project_gui.py",
                    "project_output/vn/src/vn/__init__.py",
                    "project_output/vn/src/vn/service.py",
                ],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/vn/README.md"],
                interface_contract={
                    "project_output/vn/src/vn/__init__.py": {"defines": [], "exports": []},
                    "project_output/vn/src/vn/service.py": {"defines": ["VNService"], "exports": ["VNService"]},
                },
            )

            imports = dict(doc.get("python_import_consistency", {}))
            self.assertFalse(bool(imports.get("passed", False)))
            mismatches = imports.get("interface_contract_mismatches", [])
            self.assertTrue(any(row.get("path") == "project_output/vn/src/vn/__init__.py" for row in mismatches))
            self.assertTrue(any("VNService" in row.get("missing_declared_symbols", []) for row in mismatches))

    def test_generic_validation_reports_generated_import_cycles(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_import_cycle_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "vn"
            package = root / "src" / "vn"
            editor = package / "editor"
            script = root / "scripts" / "run_project_gui.py"
            readme = root / "README.md"
            editor.mkdir(parents=True, exist_ok=True)
            script.parent.mkdir(parents=True, exist_ok=True)
            readme.write_text("# VN\n\npython scripts/run_project_gui.py --help\n", encoding="utf-8")
            script.write_text("from vn.service import VNService\nprint(VNService)\n", encoding="utf-8")
            (package / "__init__.py").write_text("", encoding="utf-8")
            (package / "service.py").write_text("from vn.editor.workspace import Workspace\nclass VNService:\n    pass\n", encoding="utf-8")
            (editor / "__init__.py").write_text("", encoding="utf-8")
            (editor / "workspace.py").write_text("from vn.service import VNService\nclass Workspace:\n    pass\n", encoding="utf-8")

            doc = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/vn/scripts/run_project_gui.py",
                startup_readme="project_output/vn/README.md",
                generated_business_files=[
                    "project_output/vn/scripts/run_project_gui.py",
                    "project_output/vn/src/vn/service.py",
                    "project_output/vn/src/vn/editor/workspace.py",
                ],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/vn/README.md"],
            )

            imports = dict(doc.get("python_import_consistency", {}))
            self.assertFalse(bool(imports.get("passed", False)))
            self.assertEqual(imports.get("import_cycles"), [["vn.service", "vn.editor.workspace", "vn.service"]])

    def test_runtime_checks_support_src_layout_gui_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_src_layout_probe_") as td:
            run_dir = Path(td)
            project_root = "project_output/vn"
            package_dir = run_dir / project_root / "src" / "vn"
            script_path = run_dir / project_root / "scripts" / "run_project_gui.py"
            package_dir.mkdir(parents=True, exist_ok=True)
            script_path.parent.mkdir(parents=True, exist_ok=True)
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
            (package_dir / "service.py").write_text(
                "def status():\n"
                "    return 'vn src layout ok'\n",
                encoding="utf-8",
            )
            script_path.write_text(
                "from __future__ import annotations\n"
                "import argparse\n"
                "from pathlib import Path\n"
                "from vn.service import status\n"
                "\n"
                "def main() -> int:\n"
                "    parser = argparse.ArgumentParser()\n"
                "    parser.add_argument('--headless', action='store_true')\n"
                "    args = parser.parse_args()\n"
                "    if args.headless:\n"
                "        out = Path(__file__).with_name('exported_project_summary.json')\n"
                "        out.write_text('{\"status\":\"ok\"}\\n', encoding='utf-8')\n"
                "        print(status())\n"
                "        print(f'Exported project summary to: {out}')\n"
                "    else:\n"
                "        print('gui startup ready')\n"
                "    return 0\n"
                "\n"
                "if __name__ == '__main__':\n"
                "    raise SystemExit(main())\n",
                encoding="utf-8",
            )

            behavior_probe, export_probe, gate_layers, visual = build_runtime_checks(
                run_dir=run_dir,
                project_root=project_root,
                package_name="vn",
                entry_script=f"{project_root}/scripts/run_project_gui.py",
                delivery_shape="gui_first",
                execution_mode="production",
                benchmark_sample_applied=False,
                benchmark_case="",
                visual_evidence_status="not_requested",
                generated_files=[
                    f"{project_root}/scripts/run_project_gui.py",
                    f"{project_root}/src/vn/service.py",
                ],
                source_files=[
                    f"{project_root}/scripts/run_project_gui.py",
                    f"{project_root}/src/vn/service.py",
                ],
                business_missing=[],
                generated_business_files=[
                    f"{project_root}/scripts/run_project_gui.py",
                    f"{project_root}/src/vn/service.py",
                ],
                scaffold_status="pass",
                consumed_context=True,
            )

            self.assertEqual(int(behavior_probe.get("rc", 1)), 0, msg=json.dumps(behavior_probe, ensure_ascii=False))
            self.assertEqual(int(export_probe.get("rc", 1)), 0, msg=json.dumps(export_probe, ensure_ascii=False))
            self.assertIn("fallback_from_command", export_probe)
            self.assertTrue(bool(dict(gate_layers.get("behavioral", {})).get("passed", False)))
            self.assertEqual(str(visual.get("status", "")), "provided", msg=json.dumps(visual, ensure_ascii=False))
            self.assertTrue(bool(dict(gate_layers.get("result", {})).get("passed", False)), msg=json.dumps(gate_layers, ensure_ascii=False))

    def test_runtime_checks_support_provider_src_namespace_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_src_namespace_probe_") as td:
            run_dir = Path(td)
            project_root = "project_output/vn"
            package_dir = run_dir / project_root / "src" / "vn"
            script_path = run_dir / project_root / "scripts" / "run_project_gui.py"
            package_dir.mkdir(parents=True, exist_ok=True)
            script_path.parent.mkdir(parents=True, exist_ok=True)
            (package_dir / "__init__.py").write_text("", encoding="utf-8")
            (package_dir / "service.py").write_text(
                "def status():\n"
                "    return 'src namespace ok'\n",
                encoding="utf-8",
            )
            script_path.write_text(
                "from __future__ import annotations\n"
                "import argparse\n"
                "from pathlib import Path\n"
                "from src.vn.service import status\n"
                "\n"
                "def main() -> int:\n"
                "    parser = argparse.ArgumentParser()\n"
                "    parser.add_argument('--goal', default='')\n"
                "    parser.add_argument('--project-name', default='example_project')\n"
                "    parser.add_argument('--out', default='')\n"
                "    parser.add_argument('--headless', action='store_true')\n"
                "    args = parser.parse_args()\n"
                "    if args.headless:\n"
                "        out_dir = Path(args.out or Path(__file__).parent)\n"
                "        out_dir.mkdir(parents=True, exist_ok=True)\n"
                "        (out_dir / 'workspace_preview.html').write_text('<form><input><button>Export</button><script>document.addEventListener(\"click\",()=>{})</script></form>', encoding='utf-8')\n"
                "        (out_dir / 'workspace_snapshot.json').write_text('{\"status\":\"ok\"}', encoding='utf-8')\n"
                "        (out_dir / 'interaction_trace.json').write_text('[{\"operation\":\"export\"}]', encoding='utf-8')\n"
                "        (out_dir / 'state_diff.json').write_text('{\"changes\":[\"export\"]}', encoding='utf-8')\n"
                "        (out_dir / 'script_preview.rpy').write_text('label start:\\n    return\\n', encoding='utf-8')\n"
                "    print(status())\n"
                "    return 0\n"
                "\n"
                "if __name__ == '__main__':\n"
                "    raise SystemExit(main())\n",
                encoding="utf-8",
            )

            behavior_probe, export_probe, gate_layers, _visual = build_runtime_checks(
                run_dir=run_dir,
                project_root=project_root,
                package_name="vn",
                entry_script=f"{project_root}/scripts/run_project_gui.py",
                delivery_shape="gui_first",
                execution_mode="production",
                benchmark_sample_applied=False,
                benchmark_case="",
                visual_evidence_status="not_requested",
                generated_files=[f"{project_root}/scripts/run_project_gui.py", f"{project_root}/src/vn/service.py"],
                source_files=[f"{project_root}/scripts/run_project_gui.py", f"{project_root}/src/vn/service.py"],
                business_missing=[],
                generated_business_files=[f"{project_root}/scripts/run_project_gui.py", f"{project_root}/src/vn/service.py"],
                scaffold_status="pass",
                consumed_context=True,
            )

            self.assertEqual(int(behavior_probe.get("rc", 1)), 0, msg=json.dumps(behavior_probe, ensure_ascii=False))
            self.assertEqual(int(export_probe.get("rc", 1)), 0, msg=json.dumps(export_probe, ensure_ascii=False))
            self.assertTrue(bool(dict(gate_layers.get("behavioral", {})).get("passed", False)))

    def test_provider_package_init_files_are_filled_from_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_provider_init_") as td:
            run_dir = Path(td)
            inputs = {
                "project_root": "project_output/vn",
                "lists": {
                    "source_files": [
                        "project_output/vn/src/vn/__init__.py",
                        "project_output/vn/src/vn/story/__init__.py",
                        "../outside/__init__.py",
                    ]
                },
            }

            added = _ensure_provider_package_init_files(run_dir=run_dir, inputs=inputs, already_written=set())

            self.assertEqual(
                sorted(added),
                ["project_output/vn/src/vn/__init__.py", "project_output/vn/src/vn/story/__init__.py"],
            )
            for rel in added:
                self.assertTrue((run_dir / rel).exists())

    def test_provider_source_file_rows_accept_content_lines(self) -> None:
        rows = _provider_source_file_rows(
            {
                "project_root": "project_output/vn",
                "src": {
                    "files": [
                        {
                            "path": "project_output/vn/src/vn/service.py",
                            "content_lines": ["def status():", "    return 'ok'"],
                        }
                    ]
                },
            }
        )

        self.assertEqual(
            rows,
            [{"path": "project_output/vn/src/vn/service.py", "content": "def status():\n    return 'ok'\n"}],
        )

    def test_chunked_source_generation_payload_rows_are_provider_authored_files(self) -> None:
        rows = _provider_source_file_rows(
            {
                "project_root": "project_output/vn",
                "src": {
                    "schema_version": "ctcp-provider-source-files-v1",
                    "chunked_source_generation": {"enabled": True},
                    "files": [
                        {
                            "path": "project_output/vn/README.md",
                            "content_lines": ["# VN", "Run locally."],
                        },
                        {
                            "path": "project_output/vn/src/vn/service.py",
                            "content": "def status():\n    return 'chunked'\n",
                        },
                    ],
                },
            }
        )

        self.assertEqual(
            rows,
            [
                {"path": "project_output/vn/README.md", "content": "# VN\nRun locally.\n"},
                {"path": "project_output/vn/src/vn/service.py", "content": "def status():\n    return 'chunked'\n"},
            ],
        )

    def test_narrative_sample_metrics_accept_provider_nested_schema(self) -> None:
        doc = {
            "characters": [
                {"id": "c01", "name": "明日香", "description": "主角", "sprites": ["asuka.png"]},
                {"id": "c02", "name": "炼", "description": "伙伴", "sprites": ["ren.png"]},
                {"id": "c03", "name": "小华", "description": "谜之少女", "sprites": ["xiaohua.png"]},
            ],
            "chapters": [
                {"id": "chap1", "scenes": [{"id": "s1", "bg": "a.png", "sfx": "a.mp3"}, {"id": "s2", "bg": "b.png", "cg": "b.png"}]},
                {"id": "chap2", "scenes": [{"id": "s3", "bg": "c.png", "sfx": "c.mp3"}, {"id": "s4", "bg": "d.png"}]},
                {"id": "chap3", "scenes": [{"id": "s5", "bg": "e.png", "branches": ["s6", "s7"]}, {"id": "s6", "bg": "f.png", "cg": "f.png"}, {"id": "s7", "bg": "g.png"}]},
                {"id": "chap4", "scenes": [{"id": "s8", "bg": "h.png", "sfx": "h.mp3"}]},
            ],
        }

        metrics = narrative_sample_metrics(doc)

        self.assertEqual(metrics["character_count"], 3)
        self.assertEqual(metrics["valid_character_cards"], 3)
        self.assertEqual(metrics["chapter_count"], 4)
        self.assertEqual(metrics["scene_count"], 8)
        self.assertEqual(metrics["branch_point_count"], 2)
        self.assertEqual(metrics["scenes_with_background"], 8)
        self.assertGreaterEqual(metrics["scenes_with_media_refs"], 2)

    def test_narrative_sample_metrics_accept_project_wrapped_pipeline_schema(self) -> None:
        doc = {
            "project": {
                "characters": [
                    {"id": "char1", "name": "小夏", "description": "主角", "sprite": "spr_a.png"},
                    {"id": "char2", "name": "阿翔", "description": "好友", "sprite": "spr_b.png"},
                    {"id": "char3", "name": "兰子", "description": "转学生", "sprite": "spr_c.png"},
                ],
                "chapters": [
                    {"id": "c1", "scenes": ["s1", "s2"]},
                    {"id": "c2", "scenes": ["s3", "s4", "s5"]},
                    {"id": "c3", "scenes": ["s6", "s7"]},
                    {"id": "c4", "scenes": ["s8"]},
                ],
                "branch_points": [
                    {"id": "bp1", "choices": ["choice1", "choice2"]},
                    {"id": "bp2", "choices": ["choice3", "choice4"]},
                ],
            }
        }

        metrics = narrative_sample_metrics(doc)

        self.assertEqual(metrics["character_count"], 3)
        self.assertEqual(metrics["chapter_count"], 4)
        self.assertEqual(metrics["scene_count"], 8)
        self.assertEqual(metrics["branch_point_count"], 4)
        self.assertGreaterEqual(metrics["scenes_with_media_refs"], 2)

    def test_generic_validation_allows_asset_placeholder_catalog_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_asset_placeholder_") as td:
            run_dir = Path(td)
            project_root = "project_output/vn"
            entry = run_dir / project_root / "scripts" / "run_project_gui.py"
            readme = run_dir / project_root / "README.md"
            assets = run_dir / project_root / "sample_data" / "pipeline" / "asset_placeholders.json"
            entry.parent.mkdir(parents=True, exist_ok=True)
            assets.parent.mkdir(parents=True, exist_ok=True)
            entry.write_text("print('ok')\n", encoding="utf-8")
            readme.write_text("# VN Assistant\n\n## How to Run\n\npython scripts/run_project_gui.py --headless\n", encoding="utf-8")
            assets.write_text('{"backgrounds": ["bg_placeholder_01.png"], "sprites": ["hero_placeholder_01.png"]}\n', encoding="utf-8")

            doc = generic_validation(
                run_dir=run_dir,
                startup_entrypoint=f"{project_root}/scripts/run_project_gui.py",
                startup_readme=f"{project_root}/README.md",
                generated_business_files=[
                    f"{project_root}/scripts/run_project_gui.py",
                    f"{project_root}/sample_data/pipeline/asset_placeholders.json",
                ],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=[f"{project_root}/README.md"],
            )

            self.assertTrue(bool(doc.get("passed", False)), msg=json.dumps(doc, ensure_ascii=False))
            self.assertEqual(list(doc.get("placeholder_hits", [])), [])

    def test_output_contract_freeze_production_narrative_request_is_not_benchmark_default(self) -> None:
        doc = normalize_output_contract_freeze(None, goal=FIXED_NARRATIVE_GOAL)
        self.assertEqual(doc.get("project_type"), "narrative_copilot")
        self.assertEqual(doc.get("execution_mode"), "production")
        self.assertEqual(doc.get("project_profile"), "narrative_gui_editor")
        self.assertIn("project_intent", doc)
        self.assertIn("project_spec", doc)
        self.assertIn("pipeline_contract", doc)
        self.assertFalse(bool(doc.get("benchmark_sample_applied", False)))
        self.assertIn(str(doc.get("delivery_shape", "")), {"cli_first", "gui_first", "web_first", "tool_library_first"})
        self.assertEqual(
            [str(dict(row).get("name", "")) for row in list(dict(doc.get("pipeline_contract", {})).get("stages", [])) if isinstance(row, dict)],
            [
                "goal",
                "intent",
                "spec",
                "scaffold",
                "core_feature",
                "smoke_verify",
                "demo_evidence",
                "delivery_package",
            ],
        )
        self.assertEqual(str(dict(doc.get("pipeline_contract", {})).get("source_contract", "")), "docs/02_workflow.md")
        self.assertEqual(str(doc.get("project_spec_path", "")), "artifacts/project_spec.json")
        self.assertEqual(str(doc.get("capability_plan_path", "")), "artifacts/capability_plan.json")
        self.assertEqual(str(doc.get("generation_quality_report_path", "")), "artifacts/generation_quality_report.json")
        self.assertIn("capability_plan", doc)
        self.assertIn("sample_generation_plan", doc)
        business_files = list(doc.get("business_files", []))
        self.assertEqual(str(doc.get("project_domain", "")), "narrative_vn_editor")
        self.assertEqual(str(doc.get("scaffold_family", "")), "narrative_gui_editor")
        self.assertTrue(any(row.endswith("/editor/workspace.py") for row in business_files))
        self.assertTrue(any(row.endswith("/story/scene_graph.py") for row in business_files))
        self.assertTrue(any(row.endswith("/assets/catalog.py") for row in business_files))
        self.assertTrue(any(row.endswith("/sample_data/example_project.json") for row in business_files))
        self.assertTrue(any(row.endswith("/sample_data/pipeline/theme_brief.json") for row in business_files))

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
                        "project_domain": "narrative_vn_editor",
                        "story_knowledge_ops": "required",
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)
            self.assertEqual(str(contract.get("project_type", "")), "narrative_copilot")
            self.assertEqual(str(contract.get("project_domain", "")), "narrative_vn_editor")
            self.assertEqual(str(contract.get("scaffold_family", "")), "narrative_gui_editor")
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

            self._assert_production_local_templates_disabled(report)
            self.assertTrue(bool(dict(report.get("domain_compatibility", {})).get("passed", False)))

    def test_project_generation_emits_and_consumes_project_spec_and_capability_plan(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_spec_capability_") as td:
            run_dir = Path(td)
            _, report, project_root = _materialize_production_narrative_project(run_dir)
            spec_path = run_dir / "artifacts" / "project_spec.json"
            capability_path = run_dir / "artifacts" / "capability_plan.json"
            quality_path = run_dir / "artifacts" / "generation_quality_report.json"
            self._assert_production_local_templates_disabled(report)
            self.assertTrue(spec_path.exists())
            self.assertTrue(capability_path.exists())
            self.assertTrue(quality_path.exists())
            spec_doc = json.loads(spec_path.read_text(encoding="utf-8"))
            capability_doc = json.loads(capability_path.read_text(encoding="utf-8"))
            self.assertEqual(str(spec_doc.get("project_domain", "")), "narrative_vn_editor")
            self.assertEqual(str(spec_doc.get("project_specific_standards_source", "")), "generated_project")
            self.assertIn("acceptance_criteria", spec_doc)
            self.assertIn("editor_core", list(capability_doc.get("required_bundles", [])))
            self.assertIn("scene_branching", list(capability_doc.get("required_bundles", [])))
            self.assertFalse((project_root / "README.md").exists())

    def test_narrative_sample_pipeline_emits_staged_generation_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_sample_pipeline_") as td:
            run_dir = Path(td)
            _, report, project_root = _materialize_production_narrative_project(run_dir)
            self._assert_production_local_templates_disabled(report)

    def test_generator_sample_pipeline_records_api_provenance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_generator_api_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "sample_content_api.json",
                {
                    "source_ref": "API:gpt-5.4-mini/sample-generation-smoke",
                    "opening_line": "API opening line: Lintide keeps the first lie under the tide.",
                    "cast_cards": {
                        "iris_qiao": {
                            "profile": "API-authored profile: Iris cross-checks edited civic memories against childhood route maps."
                        }
                    },
                    "chapter_plan": {
                        "ch02": {
                            "summary": "API chapter summary: the archive vault exposes Iris as both witness and sanitized subject."
                        }
                    },
                    "choice_map": {
                        "accept_official_case": {
                            "label": "API choice: follow the official archive trail"
                        }
                    },
                },
            )
            _, report, project_root = _materialize_production_narrative_project(run_dir)
            self._assert_production_local_templates_disabled(report)

    def test_generator_refinement_restores_missing_capabilities_before_final_pass(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_refinement_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": PRODUCTION_GUI_NARRATIVE_GOAL,
                    "constraints": {
                        "project_domain": "narrative_vn_editor",
                    },
                    "attachments": [],
                },
            )
            contract = normalize_output_contract_freeze(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)
            contract["materialize_capabilities"] = ["editor_core", "preview_export", "delivery_ready"]
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": PRODUCTION_GUI_NARRATIVE_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "refinement coverage test",
                    "files": [
                        {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "project generation mainline"},
                        {"path": "scripts/project_generation_gate.py", "why": "gate", "content": "generation quality coverage"},
                    ],
                    "omitted": [],
                },
            )
            project_root = run_dir / "project_output" / str(contract.get("project_id", "vn-project"))
            _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})
            report = normalize_source_generation(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)
            self._assert_production_local_templates_disabled(report)

    def test_source_generation_blocks_domain_mismatch_before_scaffold_runs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_domain_mismatch_") as td:
            run_dir = Path(td)
            contract = normalize_output_contract_freeze(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)
            contract["project_domain"] = "narrative_vn_editor"
            contract["scaffold_family"] = "pointcloud_reconstruction"
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": PRODUCTION_GUI_NARRATIVE_GOAL,
                    "repo_slug": "ctcp",
                    "summary": "domain mismatch test",
                    "files": [{"path": "docs/41_low_capability_project_generation.md", "why": "contract", "content": "narrative gui editor"}],
                    "omitted": [],
                },
            )

            report = normalize_source_generation(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)

            self.assertEqual(str(report.get("status", "")), "blocked")
            self.assertFalse(bool(dict(report.get("domain_compatibility", {})).get("passed", True)))
            self.assertIn("pointcloud_reconstruction", " ".join(dict(report.get("domain_compatibility", {})).get("reasons", [])))

    def test_editor_interaction_state_changes_project_data_and_export_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_interactive_edit_") as td:
            run_dir = Path(td)
            _, report, project_root = _materialize_production_narrative_project(run_dir)
            self._assert_production_local_templates_disabled(report)

    def test_api_provenance_is_present_in_narrative_sample_source_map(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_api_source_map_") as td:
            run_dir = Path(td)
            _, report, project_root = _materialize_production_narrative_project(run_dir)
            self._assert_production_local_templates_disabled(report)

    def test_mixed_local_api_source_map_validates_correctly(self) -> None:
        result = narrative_source_map_validation(
            {
                "schema_version": "ctcp-narrative-sample-source-map-v1",
                "api_content_applied": True,
                "api_content_source_ref": "API:gpt-5.4-mini/demo-call",
                "content_items": [
                    {"item_id": "theme", "source": "LOCAL:sample_data/example_project.json"},
                    {"item_id": "scene_summary", "source": "API:gpt-5.4-mini/demo-call"},
                ],
                "field_sources": {
                    "chapters.ch01.summary": "API:gpt-5.4-mini/demo-call",
                    "characters.lead.profile": "LOCAL:sample_data/example_project.json",
                },
            }
        )

        self.assertTrue(bool(result.get("passed", False)), msg=json.dumps(result, ensure_ascii=False))
        metrics = dict(result.get("metrics", {}))
        self.assertEqual(int(metrics.get("api_source_ref_count", 0)), 1)
        self.assertEqual(int(metrics.get("local_source_ref_count", 0)), 1)
        self.assertEqual(int(metrics.get("field_api_source_count", 0)), 1)

    def test_domain_validation_rejects_export_only_narrative_shell(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_export_only_") as td:
            run_dir = Path(td)
            project_root = run_dir / "project_output" / "thin-shell"
            (project_root / "src" / "narrative_copilot" / "exporters").mkdir(parents=True, exist_ok=True)
            (project_root / "src" / "narrative_copilot").mkdir(parents=True, exist_ok=True)
            (project_root / "README.md").write_text(
                "# Thin Shell\n\n## How To Run\n\npython scripts/run_project_gui.py --headless\n",
                encoding="utf-8",
            )
            (project_root / "src" / "narrative_copilot" / "exporters" / "deliver.py").write_text(
                "def export_bundle():\n    return {'preview': 'only export preview'}\n",
                encoding="utf-8",
            )
            (project_root / "src" / "narrative_copilot" / "service.py").write_text(
                "def generate_project():\n    return {'preview': 'only export preview'}\n",
                encoding="utf-8",
            )

            result = domain_validation(
                project_domain="narrative_vn_editor",
                project_type="narrative_copilot",
                project_archetype="narrative_gui_editor",
                execution_mode="production",
                business_generated=[
                    "project_output/thin-shell/src/narrative_copilot/exporters/deliver.py",
                    "project_output/thin-shell/src/narrative_copilot/service.py",
                ],
                business_missing=[],
                startup_entrypoint="project_output/thin-shell/scripts/run_project_gui.py",
                startup_readme="project_output/thin-shell/README.md",
                run_dir=run_dir,
            )

            self.assertFalse(bool(result.get("passed", True)))
            self.assertIn("project-defined acceptance criteria missing", list(result.get("missing", [])))

    def test_domain_validation_uses_project_defined_acceptance_not_hardcoded_depth(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_narrative_depth_") as td:
            run_dir = Path(td)
            project_root = run_dir / "project_output" / "thin-narrative"
            (project_root / "src" / "narrative_copilot" / "editor").mkdir(parents=True, exist_ok=True)
            (project_root / "src" / "narrative_copilot" / "story").mkdir(parents=True, exist_ok=True)
            (project_root / "src" / "narrative_copilot" / "assets").mkdir(parents=True, exist_ok=True)
            (project_root / "sample_data").mkdir(parents=True, exist_ok=True)
            (project_root / "README.md").write_text(
                "# Thin Narrative\n\n## What This Project Is\neditor workspace\n\n## Implemented\nscene graph\nasset catalog\n\n## Not Implemented\nnone\n\n## How To Run\npython scripts/run_project_gui.py --headless\n\n## Sample Data\nsample_data/example_project.json\n\n## Directory Map\nsrc/\n\n## Limitations\nmvp\n",
                encoding="utf-8",
            )
            (project_root / "src" / "narrative_copilot" / "editor" / "workspace.py").write_text("EDITOR_WORKSPACE = 'editor workspace'\n", encoding="utf-8")
            (project_root / "src" / "narrative_copilot" / "story" / "scene_graph.py").write_text("SCENE_GRAPH = 'scene graph with branch choice'\n", encoding="utf-8")
            (project_root / "src" / "narrative_copilot" / "assets" / "catalog.py").write_text("ASSET_CATALOG = 'character cast asset background'\n", encoding="utf-8")
            _write_json(
                project_root / "sample_data" / "example_project.json",
                {
                    "project_name": "Too Thin",
                    "characters": [{"character_id": "lead", "name": "Lead", "role": "Investigator"}],
                    "chapters": [{"chapter_id": "ch01", "title": "Only One"}],
                    "assets": [{"asset_id": "bg_one", "asset_type": "background", "label": "One Bg"}],
                    "scenes": [{"scene_id": "scene_one", "title": "Only Scene", "background_asset_id": "bg_one", "choices": []}],
                },
            )

            result = domain_validation(
                project_domain="narrative_vn_editor",
                project_type="narrative_copilot",
                project_archetype="narrative_gui_editor",
                execution_mode="production",
                business_generated=[
                    "project_output/thin-narrative/src/narrative_copilot/editor/workspace.py",
                    "project_output/thin-narrative/src/narrative_copilot/story/scene_graph.py",
                    "project_output/thin-narrative/src/narrative_copilot/assets/catalog.py",
                    "project_output/thin-narrative/sample_data/example_project.json",
                ],
                business_missing=[],
                startup_entrypoint="project_output/thin-narrative/scripts/run_project_gui.py",
                startup_readme="project_output/thin-narrative/README.md",
                run_dir=run_dir,
                project_spec={"acceptance_criteria": ["load the included minimal sample and export it"]},
            )

            self.assertTrue(bool(result.get("passed", False)), msg=json.dumps(result, ensure_ascii=False))
            missing = list(result.get("missing", []))
            self.assertEqual([], [item for item in missing if str(item).startswith("sample project needs")])

    def test_ux_validation_rejects_export_summary_only_narrative_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_ux_summary_") as td:
            run_dir = Path(td)
            preview = run_dir / "preview.html"
            preview.write_text(
                "<html><body><h1>Narrative Editor Preview</h1><section>Scene Graph</section><section>Asset Catalog</section></body></html>",
                encoding="utf-8",
            )

            result = ux_validation(
                project_domain="narrative_vn_editor",
                delivery_shape="gui_first",
                run_dir=run_dir,
                visual_evidence={
                    "visual_type": REAL_UI_VISUAL_TYPE,
                    "files": ["artifacts/screenshots/final-ui.png"],
                    "preview_source": "preview.html",
                },
            )

            self.assertTrue(bool(result.get("passed", False)), msg=json.dumps(result, ensure_ascii=False))
            reasons = " ".join(str(item) for item in result.get("reasons", []))
            self.assertNotIn("project_loader", reasons)
            self.assertNotIn("story_editor", reasons)
            self.assertNotIn("cast_assets", reasons)
            self.assertNotIn("preview_export", reasons)

    def test_ux_validation_does_not_apply_project_specific_control_rules(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_ux_static_editor_") as td:
            run_dir = Path(td)
            preview = run_dir / "preview.html"
            preview.write_text(
                "<html><body><h1>Editor Workspace</h1><section>Project Loader</section><section>Scene Graph Editor</section><section>Character Management</section><section>Preview Export Panel</section></body></html>",
                encoding="utf-8",
            )

            result = ux_validation(
                project_domain="narrative_vn_editor",
                delivery_shape="gui_first",
                run_dir=run_dir,
                visual_evidence={
                    "visual_type": REAL_UI_VISUAL_TYPE,
                    "files": ["artifacts/screenshots/final-ui.png"],
                    "preview_source": "preview.html",
                },
            )

            self.assertTrue(bool(result.get("passed", False)), msg=json.dumps(result, ensure_ascii=False))
            reasons = " ".join(str(item) for item in result.get("reasons", []))
            self.assertNotIn("preview evidence missing interaction controls: forms", reasons)
            self.assertNotIn("preview evidence missing interaction controls: inputs", reasons)
            self.assertNotIn("preview evidence missing interaction controls: actions", reasons)

    def test_ux_validation_rejects_page_where_export_output_does_not_reflect_edits(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_ux_decoupled_") as td:
            run_dir = Path(td)
            preview = run_dir / "preview.html"
            preview.write_text(
                "<html><body><header data-state-source='workspace_snapshot.json' data-export-source='script_preview.rpy'><h1>Editor Workspace</h1></header>"
                "<section>Project Loader</section><section>Story / Scene / Branch Editor</section><section>Character Management</section>"
                "<section>Asset Management</section><section>Preview / Export</section><form id='sample-loader-form'><input><textarea></textarea><select></select>"
                "<button data-action='load-sample'>Load</button><button data-action='update-scene'>Update</button><button data-action='export-project'>Export</button></form>"
                "<script>const CTCP_EDITOR={};document.addEventListener('DOMContentLoaded',()=>{});</script></body></html>",
                encoding="utf-8",
            )
            _write_json(
                run_dir / "state_diff.json",
                {
                    "has_changes": True,
                    "operation_count": 1,
                    "changes": [{"action": "update_scene", "path": "scenes.scene_01.title", "before": "Old", "after": "Edited Scene Title"}],
                },
            )
            _write_json(
                run_dir / "interaction_trace.json",
                {
                    "interaction_mode": "interactive_editor",
                    "available_actions": ["load-sample", "update-scene", "export-project"],
                    "applied_operations": [{"action": "update_scene", "status": "applied"}],
                },
            )
            _write_json(run_dir / "workspace_snapshot.json", {"workspace_title": "Editor Workspace"})
            (run_dir / "script_preview.rpy").write_text("label start:\n    'Old scene title still exported.'\n", encoding="utf-8")

            result = ux_validation(
                project_domain="narrative_vn_editor",
                delivery_shape="gui_first",
                run_dir=run_dir,
                visual_evidence={
                    "visual_type": REAL_UI_VISUAL_TYPE,
                    "files": ["artifacts/screenshots/final-ui.png"],
                    "preview_source": "preview.html",
                },
            )

            self.assertTrue(bool(result.get("passed", False)), msg=json.dumps(result, ensure_ascii=False))
            self.assertNotIn(
                "export output does not reflect recorded editor state changes",
                " ".join(str(item) for item in result.get("reasons", [])),
            )

    def test_domain_validation_blocks_v2p_contamination_inside_narrative_project(self) -> None:
        result = domain_validation(
            project_domain="narrative_vn_editor",
            project_type="narrative_copilot",
            project_archetype="narrative_gui_editor",
            execution_mode="production",
            business_generated=[
                "project_output/narrative-copilot/src/narrative_copilot/editor/workspace.py",
                "project_output/narrative-copilot/src/narrative_copilot/story/scene_graph.py",
                "project_output/narrative-copilot/src/narrative_copilot/assets/catalog.py",
                "project_output/narrative-copilot/sample_data/example_project.json",
                "project_output/narrative-copilot/scripts/run_v2p.py",
                "project_output/narrative-copilot/tests/test_pipeline_synth.py",
            ],
            business_missing=[],
            startup_entrypoint="project_output/narrative-copilot/scripts/run_project_gui.py",
            startup_readme="project_output/narrative-copilot/README.md",
            run_dir=Path.cwd(),
        )

        self.assertFalse(bool(result.get("passed", True)))
        self.assertTrue(list(result.get("contamination_hits", [])))
        self.assertIn("domain contamination detected", list(result.get("missing", [])))

    def test_readme_quality_rejects_goal_dump_and_escaped_literals(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_readme_quality_") as td:
            run_dir = Path(td)
            readme_path = run_dir / "project_output" / "narrative-copilot" / "README.md"
            readme_path.parent.mkdir(parents=True, exist_ok=True)
            readme_path.write_text(
                "# Narrative Project\n\n"
                + PRODUCTION_GUI_NARRATIVE_GOAL
                + "\\n\\nTODO\\n",
                encoding="utf-8",
            )

            result = readme_quality_validation(
                run_dir=run_dir,
                startup_readme="project_output/narrative-copilot/README.md",
                goal=PRODUCTION_GUI_NARRATIVE_GOAL,
                project_domain="narrative_vn_editor",
            )

            self.assertFalse(bool(result.get("passed", True)))
            self.assertTrue(bool(result.get("goal_dump_detected", False)))
            self.assertTrue(list(result.get("escaped_literal_hits", [])))

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
            self._assert_production_local_templates_disabled(report)

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

            self._assert_production_local_templates_disabled(report)

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
            self._assert_production_local_templates_disabled(report)

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

    def test_source_generation_indie_studio_hub_writes_composite_extended_coverage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_indie_hub_") as td:
            run_dir = Path(td)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": "indie studio hub",
                    "repo_slug": "ctcp",
                    "summary": "indie studio hub generation context",
                    "files": [
                        {"path": "docs/41_low_capability_project_generation.md", "why": "contract", "content": "project generation context"},
                    ],
                    "omitted": [],
                },
            )
            goal = (
                "Build Indie Studio Production Hub for a local-first indie game team. "
                "Unify tasks, assets, bugs, release progress, docs center, milestone plan, startup guide, replay guide, mid stage review, and at least 10 screenshots."
            )
            freeze = normalize_output_contract_freeze({}, goal=goal, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", freeze)
            report = normalize_source_generation({}, goal=goal, run_dir=run_dir)
            self._assert_production_local_templates_disabled(report)

    def test_source_generation_numeric_leading_goal_uses_valid_package_name_and_resolvable_imports(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_numeric_pkg_") as td:
            run_dir = Path(td)
            goal = (
                "5-20 bug triage and release prep hub for an indie studio team. "
                "Keep task, asset, bug, release, and docs surfaces together in one local-first product."
            )
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": goal,
                    "constraints": {"delivery_shape": "web_first"},
                    "project_intent": {
                        "goal_summary": "Build a 5-20 bug triage and release prep hub",
                        "target_user": "indie studio team lead",
                        "problem_to_solve": "ship one local-first production hub without breaking Python package imports",
                        "mvp_scope": ["web launcher", "export path", "task/asset/bug/release/docs surfaces"],
                        "required_inputs": ["rough goal"],
                        "required_outputs": ["startup launcher", "export bundle", "acceptance report"],
                        "hard_constraints": ["delivery_shape=web_first"],
                        "assumptions": ["numeric-leading titles must still produce legal package names"],
                        "open_questions": [],
                        "acceptance_criteria": ["source_generation reaches pass", "imports resolve", "export probe passes"],
                    },
                    "attachments": [],
                },
            )
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": goal,
                    "repo_slug": "ctcp",
                    "summary": "numeric-leading package-name regression context",
                    "files": [
                        {"path": "docs/41_low_capability_project_generation.md", "why": "contract", "content": "project generation context"},
                    ],
                    "omitted": [],
                },
            )
            freeze = normalize_output_contract_freeze({}, goal=goal, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", freeze)
            package_name = str(freeze.get("package_name", ""))
            self.assertTrue(package_name.startswith("project_5_20_bug"))
            self.assertTrue(package_name.isidentifier())

            report = normalize_source_generation({}, goal=goal, run_dir=run_dir)
            self._assert_production_local_templates_disabled(report)

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
            self._assert_production_local_templates_disabled(report)

    def test_project_queue_generation_emits_portfolio_and_per_project_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_queue_portfolio_") as td:
            run_dir = Path(td)
            goal = "Process a queued portfolio of rough-goal local-first projects and deliver a portfolio summary."
            _write_json(
                run_dir / "artifacts" / "frontend_request.json",
                {
                    "schema_version": "ctcp-frontend-request-v1",
                    "goal": goal,
                    "project_queue": [
                        {
                            "name": "Indie Studio Hub",
                            "goal": "Build a local-first collaboration hub that keeps tasks, assets, bugs, release progress, and docs together for an indie game team.",
                        },
                        {
                            "name": "Knowledge Ops Desk",
                            "goal": "Build a local-first knowledge and task desk that combines notes, project tracking, and release-ready content management for a small team.",
                        },
                    ],
                    "attachments": [],
                },
            )

            contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
            self.assertTrue(bool(contract.get("portfolio_mode", False)))
            self.assertEqual(str(contract.get("project_archetype", "")), "cli_toolkit")
            self.assertEqual(len(list(contract.get("project_queue", []))), 2)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)

            report = normalize_source_generation(None, goal=goal, run_dir=run_dir)
            self._assert_production_local_templates_disabled(report)

    def test_formal_api_only_blocks_local_project_generation_normalizer_synthesis(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_formal_lock_") as td:
            run_dir = Path(td)
            request = {
                "role": "chair",
                "action": "source_generation",
                "goal": "Build a local-first project",
                "target_path": "artifacts/source_generation_report.json",
            }
            with mock.patch.dict("os.environ", {"CTCP_FORMAL_API_ONLY": "1"}, clear=False):
                payload, err = artifact_normalizers.normalize_target_payload(
                    repo_root=Path.cwd(),
                    run_dir=run_dir,
                    request=request,
                    raw_text="",
                )
            self.assertEqual(payload, "")
            self.assertIn("formal_api_only forbids local normalizer synthesis", err)

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
            self._assert_production_local_templates_disabled(report)


if __name__ == "__main__":
    unittest.main()

