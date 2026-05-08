from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ctcp_adapters.source_generation_prompt import render_source_generation_payload_requirements
from tools.providers.project_generation_validation import generic_validation
from tools.providers.project_generation_signature_validation import python_signature_consistency_validation


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class GeneratedProjectSignatureValidationTests(unittest.TestCase):
    def test_detects_constructor_missing_arg_and_unexpected_keyword(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_signature_validation_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "voice"
            _write(root / "scripts" / "run_project_web.py", "from voice.service import VoiceAssistantService\napp = VoiceAssistantService()\n")
            _write(root / "src" / "voice" / "__init__.py", "")
            _write(root / "src" / "voice" / "service.py", "class VoiceAssistantService:\n    def __init__(self, whitelist):\n        self.whitelist = whitelist\n")
            _write(root / "src" / "voice" / "models.py", "class CommandWhitelist:\n    def __init__(self, allowed):\n        self.allowed = allowed\n")
            _write(root / "tests" / "test_voice.py", "from voice.models import CommandWhitelist\n\nwhitelist = CommandWhitelist(commands=set())\n")

            report = python_signature_consistency_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/voice/scripts/run_project_web.py",
                generated_business_files=[
                    "project_output/voice/scripts/run_project_web.py",
                    "project_output/voice/src/voice/__init__.py",
                    "project_output/voice/src/voice/service.py",
                    "project_output/voice/src/voice/models.py",
                    "project_output/voice/tests/test_voice.py",
                ],
            )

            self.assertFalse(bool(report.get("passed", False)))
            mismatches = list(report.get("mismatches", []))
            self.assertEqual(len(mismatches), 2)
            by_callee = {row["callee"]: row for row in mismatches}
            self.assertEqual(by_callee["VoiceAssistantService"]["missing_required"], ["whitelist"])
            self.assertEqual(by_callee["CommandWhitelist"]["unexpected_keywords"], ["commands"])

    def test_generic_validation_includes_signature_consistency_blocker(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_generic_signature_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "voice"
            _write(root / "README.md", "# Voice\n\n## How To Run\npython scripts/run_project_web.py --help\n")
            _write(root / "scripts" / "run_project_web.py", "from voice.service import VoiceAssistantService\napp = VoiceAssistantService()\n")
            _write(root / "src" / "voice" / "__init__.py", "")
            _write(root / "src" / "voice" / "service.py", "class VoiceAssistantService:\n    def __init__(self, whitelist):\n        self.whitelist = whitelist\n")

            report = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/voice/scripts/run_project_web.py",
                startup_readme="project_output/voice/README.md",
                generated_business_files=[
                    "project_output/voice/scripts/run_project_web.py",
                    "project_output/voice/src/voice/__init__.py",
                    "project_output/voice/src/voice/service.py",
                ],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/voice/README.md"],
            )

            self.assertFalse(bool(report.get("passed", False)))
            signature_report = dict(report.get("python_signature_consistency", {}))
            self.assertFalse(bool(signature_report.get("passed", False)))
            self.assertEqual(signature_report["mismatches"][0]["callee"], "VoiceAssistantService")

    def test_retry_prompt_consumes_static_signature_mismatches(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_signature_prompt_") as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "output_contract_freeze.json").write_text(
                json.dumps({"project_root": "project_output/voice"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (artifacts / "source_generation_report.json").write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "generic_validation": {
                            "python_signature_consistency": {
                                "passed": False,
                                "mismatches": [
                                    {
                                        "caller_path": "project_output/voice/scripts/run_project_web.py",
                                        "line": 2,
                                        "callee": "VoiceAssistantService",
                                        "signature": "VoiceAssistantService(whitelist)",
                                        "missing_required": ["whitelist"],
                                        "unexpected_keywords": [],
                                        "too_many_positionals": False,
                                    },
                                    {
                                        "caller_path": "project_output/voice/tests/test_voice.py",
                                        "line": 3,
                                        "callee": "CommandWhitelist",
                                        "signature": "CommandWhitelist(allowed)",
                                        "missing_required": [],
                                        "unexpected_keywords": ["commands"],
                                        "too_many_positionals": False,
                                    },
                                ],
                            }
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            prompt = "\n".join(render_source_generation_payload_requirements(run_dir=run_dir))

            self.assertIn("signature_consistency", prompt)
            self.assertIn("VoiceAssistantService(whitelist)", prompt)
            self.assertIn("missing required: whitelist", prompt)
            self.assertIn("unexpected keywords: commands", prompt)


if __name__ == "__main__":
    unittest.main()
