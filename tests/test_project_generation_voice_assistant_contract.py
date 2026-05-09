from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze


class VoiceAssistantContractTests(unittest.TestCase):
    def test_chinese_voice_assistant_goal_uses_goal_specific_slug_and_spec(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_voice_assistant_contract_") as td:
            goal = (
                "我想要做一个可以通过手机连接电脑操控的语音助理：电脑本地启动服务，"
                "手机在同一局域网打开网页，可以语音或文字输入命令，电脑只执行白名单命令；"
                "项目要包含README、启动脚本、核心源码、测试、示例数据和本地运行验证证据。"
            )
            doc = normalize_output_contract_freeze({}, goal=goal, run_dir=Path(td))

        self.assertEqual(doc.get("project_id"), "voice-assistant")
        self.assertEqual(doc.get("package_name"), "voice_assistant")
        self.assertEqual(doc.get("project_archetype"), "web_service")
        self.assertEqual(doc.get("delivery_shape"), "web_first")
        self.assertNotEqual(doc.get("project_id"), "readme")
        spec_text = json.dumps(doc.get("project_spec", {}), ensure_ascii=False).lower()
        for token in ("手机", "语音", "白名单", "local web"):
            self.assertIn(token, spec_text)

    def test_mixed_chinese_english_goal_does_not_freeze_to_web_readme(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_voice_assistant_mixed_goal_") as td:
            goal = (
                "请生成一个本地可运行的项目：手机通过同一局域网连接电脑，"
                "使用网页语音输入或按钮指令操控电脑上的安全白名单动作；"
                "需要本地 Web 服务、手机网页界面、命令白名单、执行日志、状态接口、README 和可运行测试。"
            )
            doc = normalize_output_contract_freeze({}, goal=goal, run_dir=Path(td))

        self.assertEqual(doc.get("project_id"), "voice-assistant")
        self.assertEqual(doc.get("project_root"), "project_output/voice-assistant")
        self.assertEqual(doc.get("package_name"), "voice_assistant")
        self.assertNotEqual(doc.get("project_id"), "web-readme")


if __name__ == "__main__":
    unittest.main()
