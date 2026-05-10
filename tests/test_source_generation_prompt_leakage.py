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

    def test_source_generation_retry_prompt_consumes_live_api_export_signature_visual_blockers(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_prompt_live_api_retry_") as td:
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
                            "passed": False,
                            "smoke_run": {
                                "startup_probe": {"rc": 0, "status": "pass", "stdout_tail": "Server started on http://localhost:8000"},
                                "export_probe": {
                                    "rc": 1,
                                    "status": "blocked",
                                    "stdout_tail": "API Agent Standard Library Web Service\noptions:\n  --serve\n  --goal GOAL\n  --project-name PROJECT_NAME\n  --out OUT\n  --headless",
                                },
                            },
                            "python_signature_consistency": {
                                "passed": False,
                                "mismatches": [
                                    {
                                        "caller_path": "project_output/voice-assistant/tests/test_voice_assistant_service.py",
                                        "line": 21,
                                        "callee": "export_project_assets",
                                        "signature": "export_project_assets(service_inst, out_dir)",
                                        "provided_positionals": 1,
                                        "missing_required": ["out_dir"],
                                    }
                                ],
                                "interface_signature_mismatches": [
                                    {
                                        "path": "project_output/voice-assistant/src/voice_assistant/exporter.py",
                                        "symbol": "export_project_assets",
                                        "declared_signature": "export_project_assets(service_inst:APIService, out_dir:str)",
                                        "actual_signature": "export_project_assets(service_inst, out_dir)",
                                    }
                                ],
                            },
                        },
                        "gate_layers": {
                            "behavioral": {"passed": False, "reason": "startup and export probes must pass"},
                            "result": {"passed": False, "reason": "visual evidence required for gui/web delivery"},
                        },
                        "ux_validation": {
                            "passed": False,
                            "reasons": [
                                "visual evidence files missing",
                                "GUI/web projects require real export page evidence instead of fallback evidence cards",
                                "GUI/web projects require a preview source page",
                            ],
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            prompt = self._render_web_prompt(run_dir=run_dir, repo_root=repo_root, goal="API web service")

        self.assertIn("export_probe: rc=1 status=blocked", prompt)
        self.assertIn("export command must exit 0", prompt)
        self.assertIn("export_project_assets(service_inst, out_dir)", prompt)
        self.assertIn("missing required: out_dir", prompt)
        self.assertIn("signature_matrix", prompt)
        self.assertIn("declares `export_project_assets`", prompt)
        self.assertIn("visual evidence files missing", prompt)
        self.assertIn("preview source page", prompt)
        self.assertIn("single replacement batch", prompt)

    def test_source_generation_retry_prompt_consumes_vn_interaction_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_prompt_vn_retry_") as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "output_contract_freeze.json").write_text(
                json.dumps(
                    {
                        "project_root": "project_output/vn",
                        "project_domain": "narrative_vn_editor",
                        "project_archetype": "narrative_gui_editor",
                        "delivery_shape": "gui_first",
                        "package_name": "vn",
                        "startup_entrypoint": "project_output/vn/scripts/run_project_gui.py",
                        "source_files": ["project_output/vn/scripts/run_project_gui.py", "project_output/vn/src/vn/service.py"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            (run_dir / "artifacts" / "source_generation_report.json").write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "generic_validation": {
                            "python_import_consistency": {
                                "missing_symbols": [
                                    {
                                        "from_path": "project_output/vn/scripts/run_project_gui.py",
                                        "target_path": "project_output/vn/src/vn/__init__.py",
                                        "symbol": "service",
                                    }
                                ]
                            },
                            "python_signature_consistency": {
                                "mismatches": [
                                    {
                                        "caller_path": "project_output/vn/src/vn/pipeline/prompt_pipeline.py",
                                        "line": 9,
                                        "callee": "StoryOutline",
                                        "signature": "StoryOutline(title, theme, chapters)",
                                        "missing_required": ["theme"],
                                        "unexpected_keywords": ["synopsis"],
                                    }
                                ]
                            },
                            "generated_tests": {
                                "passed": False,
                                "stderr_tail": "TypeError: StoryOutline.__init__() got an unexpected keyword argument 'synopsis'",
                            },
                        },
                        "ux_validation": {
                            "passed": False,
                            "reasons": ["visual evidence files missing", "GUI/web projects require a preview source page"],
                            "interaction_acceptance": {
                                "passed": False,
                                "reasons": [
                                    "preview evidence missing interaction controls: forms",
                                    "preview evidence missing interaction controls: inputs",
                                    "preview evidence missing interaction controls: actions",
                                    "preview evidence missing interaction controls: hooks",
                                    "preview evidence missing interaction trace",
                                    "preview evidence missing workspace snapshot",
                                    "preview evidence missing export script",
                                ],
                            },
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            prompt = self._render_web_prompt(run_dir=run_dir, repo_root=repo_root, goal="VN retry")

        self.assertIn("import_consistency", prompt)
        self.assertIn("StoryOutline(title, theme, chapters)", prompt)
        self.assertIn("unexpected keywords: synopsis", prompt)
        self.assertIn("StoryOutline.__init__() got an unexpected keyword argument", prompt)
        self.assertIn("ux_interaction", prompt)
        self.assertIn("preview evidence missing interaction controls: forms", prompt)
        self.assertIn("preview evidence missing workspace snapshot", prompt)
        self.assertIn("preview evidence missing export script", prompt)


if __name__ == "__main__":
    unittest.main()
