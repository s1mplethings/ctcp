from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze, normalize_source_generation

PRODUCTION_GUI_NARRATIVE_GOAL = (
    "做一个本地可运行的 VN 项目助手 MVP："
    "输入角色资料、章节大纲、场景列表，生成一个可视化整理工具。"
    "这个工具至少要能管理角色卡、管理章节和场景卡、绑定背景和立绘占位、"
    "展示剧情流程顺序、导出基础的 Ren'Py 风格脚本骨架或结构化 JSON，并提供一个最小可用界面。"
)


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _materialize_production_narrative_project(run_dir: Path, *, goal: str) -> Path:
    _write_json(
        run_dir / "artifacts" / "frontend_request.json",
        {
            "schema_version": "ctcp-frontend-request-v1",
            "goal": goal,
            "constraints": {"project_domain": "narrative_vn_editor", "story_knowledge_ops": "required"},
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
                {"path": "workflow_registry/wf_project_generation_manifest/recipe.yaml", "why": "workflow", "content": "fixed stage order"},
            ],
            "omitted": [],
        },
    )
    project_root = run_dir / "project_output" / str(contract.get("project_id", "vn-project"))
    _write_json(project_root / "meta" / "manifest.json", {"schema_version": "ctcp-pointcloud-manifest-v1"})
    report = normalize_source_generation(None, goal=goal, run_dir=run_dir)
    if str(report.get("status", "")) != "pass":
        raise AssertionError(json.dumps(report, ensure_ascii=False))
    return project_root


class ProjectGenerationVariantContentTests(unittest.TestCase):
    def test_narrative_sample_pipeline_same_goal_uses_run_variant_content(self) -> None:
        goal = PRODUCTION_GUI_NARRATIVE_GOAL
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_sample_variant_a_") as td_a:
            project_root_a = _materialize_production_narrative_project(Path(td_a), goal=goal)
            sample_a = json.loads((project_root_a / "sample_data" / "example_project.json").read_text(encoding="utf-8"))
            source_map_a = json.loads((project_root_a / "sample_data" / "source_map.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_sample_variant_b_") as td_b:
            project_root_b = _materialize_production_narrative_project(Path(td_b), goal=goal)
            sample_b = json.loads((project_root_b / "sample_data" / "example_project.json").read_text(encoding="utf-8"))
            source_map_b = json.loads((project_root_b / "sample_data" / "source_map.json").read_text(encoding="utf-8"))

        self.assertNotEqual(str(dict(sample_a.get("runtime_snippets", {})).get("opening_line", "")), str(dict(sample_b.get("runtime_snippets", {})).get("opening_line", "")))
        self.assertNotEqual(str(sample_a.get("project_name", "")), str(sample_b.get("project_name", "")))
        self.assertTrue(bool(dict(source_map_a.get("goal_adaptation", {})).get("applied", False)))
        self.assertTrue(bool(dict(source_map_b.get("goal_adaptation", {})).get("applied", False)))


if __name__ == "__main__":
    unittest.main()
