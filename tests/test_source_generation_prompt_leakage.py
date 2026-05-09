from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers import api_agent


class SourceGenerationPromptLeakageTests(unittest.TestCase):
    def test_web_service_prompt_excludes_narrative_gui_leakage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_prompt_leakage_") as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "output_contract_freeze.json").write_text(
                json.dumps(
                    {
                        "project_root": "project_output/voice-assistant",
                        "project_domain": "generic_software_project",
                        "project_archetype": "web_service",
                        "delivery_shape": "web_first",
                        "package_name": "voice_assistant",
                        "startup_entrypoint": "project_output/voice-assistant/scripts/run_project_web.py",
                        "startup_readme": "project_output/voice-assistant/README.md",
                        "source_files": [
                            "project_output/voice-assistant/pyproject.toml",
                            "project_output/voice-assistant/scripts/run_project_web.py",
                            "project_output/voice-assistant/src/voice_assistant/app.py",
                            "project_output/voice-assistant/src/voice_assistant/service.py",
                        ],
                        "business_files": [
                            "project_output/voice-assistant/scripts/run_project_web.py",
                            "project_output/voice-assistant/src/voice_assistant/app.py",
                            "project_output/voice-assistant/src/voice_assistant/service.py",
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            evidence: dict[str, Path] = {}
            for key in ("context", "constraints", "fix_brief", "externals"):
                path = run_dir / f"{key.upper()}.md"
                path.write_text(f"# {key}\n- sample\n", encoding="utf-8")
                evidence[key] = path

            prompt = api_agent._render_prompt(
                run_dir=run_dir,
                repo_root=repo_root,
                request={
                    "role": "chair",
                    "action": "source_generation",
                    "goal": "手机连接电脑操控的语音助理",
                    "target_path": "artifacts/source_generation_report.json",
                },
                evidence=evidence,
            )

        self.assertIn("project_output/voice-assistant/scripts/run_project_web.py", prompt)
        self.assertIn("from voice_assistant.service", prompt)
        self.assertIn("real `/` HTML page plus `/status`", prompt)
        self.assertIn("`--serve`", prompt)
        for leaked in (
            "story/scene/branch editor",
            "character/asset management",
            "run_project_gui.py",
            "tkinter",
            "from vn.service",
            "launcher compatibility table",
        ):
            self.assertNotIn(leaked, prompt)


if __name__ == "__main__":
    unittest.main()
