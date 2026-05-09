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
    def _render_web_prompt(self, *, run_dir: Path, repo_root: Path, goal: str = "手机连接电脑操控的语音助理") -> str:
        evidence: dict[str, Path] = {}
        for key in ("context", "constraints", "fix_brief", "externals"):
            path = run_dir / f"{key.upper()}.md"
            path.write_text(f"# {key}\n- sample\n", encoding="utf-8")
            evidence[key] = path
        return api_agent._render_prompt(
            run_dir=run_dir,
            repo_root=repo_root,
            request={
                "role": "chair",
                "action": "source_generation",
                "goal": goal,
                "target_path": "artifacts/source_generation_report.json",
            },
            evidence=evidence,
        )

    def _write_web_contract(self, run_dir: Path) -> None:
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

    def test_web_service_prompt_excludes_narrative_gui_leakage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_prompt_leakage_") as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)
            self._write_web_contract(run_dir)
            prompt = self._render_web_prompt(run_dir=run_dir, repo_root=repo_root)

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

    def test_source_generation_retry_prompt_consumes_generic_validation_failures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_prompt_retry_feedback_") as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)
            self._write_web_contract(run_dir)
            (run_dir / "artifacts" / "source_generation_report.json").write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "generic_validation": {
                            "smoke_run": {
                                "startup_probe": {
                                    "stderr_tail": "ImportError: cannot import name 'execute_command' from 'voice_assistant.service'"
                                }
                            },
                            "python_import_consistency": {
                                "interface_contract_mismatches": [
                                    {
                                        "path": "project_output/voice-assistant/src/voice_assistant/app.py",
                                        "reason": "provider interface contract does not match generated Python file",
                                        "missing_declared_symbols": ["request_handler", "status_handler"],
                                        "undeclared_actual_symbols": ["SimpleRequestHandler"],
                                    }
                                ]
                            },
                            "python_signature_consistency": {
                                "mismatches": [
                                    {
                                        "caller_path": "project_output/voice-assistant/tests/test_voice_assistant_service.py",
                                        "line": 10,
                                        "callee": "VoiceAssistantService",
                                        "signature": "VoiceAssistantService(whitelist, log_dir)",
                                        "missing_required": ["log_dir"],
                                    }
                                ],
                                "abstract_stub_violations": [
                                    {
                                        "path": "project_output/voice-assistant/src/voice_assistant/service_contract.py",
                                        "line": 3,
                                        "symbol": "validate_command",
                                    }
                                ],
                            },
                            "generated_tests": {
                                "passed": False,
                                "import_style_violations": [
                                    {
                                        "path": "tests/test_voice_assistant_service.py",
                                        "import": "from src.voice_assistant.service import VoiceAssistantService",
                                        "reason": "generated tests must import the package name directly",
                                    }
                                ],
                                "stderr_tail": "FAILED (errors=1)",
                            },
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            prompt = self._render_web_prompt(run_dir=run_dir, repo_root=repo_root)

        self.assertIn("Previous source_generation failed; fix these exact issues", prompt)
        self.assertIn("retry_gate: generic_validation already blocked this project", prompt)
        self.assertIn("execute_command", prompt)
        self.assertIn("interface_contract", prompt)
        self.assertIn("request_handler", prompt)
        self.assertIn("signature_consistency", prompt)
        self.assertIn("VoiceAssistantService(whitelist, log_dir)", prompt)
        self.assertIn("abstract_stub", prompt)
        self.assertIn("validate_command", prompt)
        self.assertIn("generated_tests", prompt)
        self.assertIn("from src.voice_assistant.service import VoiceAssistantService", prompt)


if __name__ == "__main__":
    unittest.main()
