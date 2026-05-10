from __future__ import annotations

import unittest

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze


VN_GOAL = (
    "做一个本地可运行的 VN 项目助手 MVP：输入角色资料、章节大纲、场景列表，"
    "生成一个可视化整理工具，绑定背景和立绘占位，并导出基础脚本骨架。"
)


class ProjectGenerationNarrativeContractTests(unittest.TestCase):
    def test_vn_board_asset_text_does_not_trigger_team_pm_guard(self) -> None:
        doc = normalize_output_contract_freeze(
            {
                "project_spec": {
                    "core_modules": ["story_engine", "asset_manager", "route_manager"],
                    "mvp_scope": ["branching_scene_script", "background_art", "character_sprites"],
                    "background_art": [
                        {
                            "id": "train_platform",
                            "description": "A rainy platform with an old timetable board near the tracks.",
                        }
                    ],
                }
            },
            goal=VN_GOAL,
        )
        self.assertEqual(doc.get("project_domain"), "narrative_vn_editor")
        self.assertEqual(doc.get("scaffold_family"), "narrative_gui_editor")
        self.assertEqual(doc.get("project_type"), "narrative_copilot")
        spec = dict(doc.get("project_spec", {}))
        self.assertEqual(spec.get("core_modules"), ["story_engine", "asset_manager", "route_manager"])

    def test_vn_contract_supplies_required_structural_lists(self) -> None:
        doc = normalize_output_contract_freeze({"project_spec": {}}, goal=VN_GOAL)
        spec = dict(doc.get("project_spec", {}))
        for key in (
            "core_modules",
            "required_outputs",
            "required_pages_or_views",
            "data_models",
            "key_interactions",
            "export_targets",
            "delivery_requirements",
            "explicit_non_goals",
        ):
            self.assertTrue(list(spec.get(key, [])), key)
        self.assertIn("scene_script.rpy", list(spec.get("required_outputs", [])))
        self.assertIsInstance(spec.get("sample_content_plan"), dict)


if __name__ == "__main__":
    unittest.main()
