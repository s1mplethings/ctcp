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


if __name__ == "__main__":
    unittest.main()
