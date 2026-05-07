from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ctcp_adapters.source_generation_prompt import render_source_generation_payload_requirements
from tools.providers.project_generation_validation import generic_validation


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class GeneratedProjectValidationSelfRepairTests(unittest.TestCase):
    def test_generic_validation_rejects_generated_tests_importing_src_package(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_generated_test_import_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "readme"
            _write(root / "README.md", "# Demo\n\n## How To Run\npython scripts/run_project_web.py --help\n")
            _write(root / "scripts" / "run_project_web.py", "from readme.service import VoiceAssistantService\nprint(VoiceAssistantService)\n")
            _write(root / "src" / "readme" / "__init__.py", "")
            _write(root / "src" / "readme" / "service.py", "class VoiceAssistantService:\n    pass\n")
            _write(root / "tests" / "test_readme_service.py", "from src.readme import service\n\nclass Smoke:\n    pass\n")

            report = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/readme/scripts/run_project_web.py",
                startup_readme="project_output/readme/README.md",
                generated_business_files=[
                    "project_output/readme/scripts/run_project_web.py",
                    "project_output/readme/src/readme/__init__.py",
                    "project_output/readme/src/readme/service.py",
                    "project_output/readme/tests/test_readme_service.py",
                ],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/readme/README.md"],
            )

            self.assertFalse(bool(report.get("passed", False)))
            generated_tests = dict(report.get("generated_tests", {}))
            self.assertFalse(bool(generated_tests.get("passed", False)))
            violations = list(generated_tests.get("import_style_violations", []))
            self.assertEqual(violations[0]["import"], "from src.readme import ...")

    def test_source_generation_retry_prompt_consumes_generated_test_failures(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_generated_test_prompt_") as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            artifacts.mkdir(parents=True, exist_ok=True)
            (artifacts / "output_contract_freeze.json").write_text(
                json.dumps(
                    {
                        "project_root": "project_output/readme",
                        "startup_entrypoint": "project_output/readme/scripts/run_project_web.py",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (artifacts / "source_generation_report.json").write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "generic_validation": {
                            "smoke_run": {
                                "startup_probe": {
                                    "stderr_tail": "TypeError: VoiceAssistantService.__init__() missing 1 required positional argument: 'whitelist'"
                                },
                                "export_probe": {"stderr_tail": ""},
                            },
                            "generated_tests": {
                                "passed": False,
                                "import_style_violations": [
                                    {
                                        "path": "tests/test_readme_service.py",
                                        "import": "from src.readme import ...",
                                        "reason": "generated tests must import the package name directly",
                                    }
                                ],
                                "stderr_tail": "ModuleNotFoundError: No module named 'src.readme'",
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            prompt = "\n".join(render_source_generation_payload_requirements(run_dir=run_dir))

            self.assertIn("VoiceAssistantService.__init__", prompt)
            self.assertIn("constructor or method signature mismatch", prompt)
            self.assertIn("generated_tests", prompt)
            self.assertIn("from src.readme import ...", prompt)
            self.assertIn("tests are importing `src.<package>`", prompt)


if __name__ == "__main__":
    unittest.main()
