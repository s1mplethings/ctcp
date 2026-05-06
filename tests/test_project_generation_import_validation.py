from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers.project_generation_import_validation import python_import_consistency_validation


class ProjectGenerationImportValidationTests(unittest.TestCase):
    def test_provider_interface_contract_ignores_scripts_and_tests(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_interface_scripts_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "vn"
            package = root / "src" / "vn"
            script = root / "scripts" / "run_project_gui.py"
            package.mkdir(parents=True, exist_ok=True)
            script.parent.mkdir(parents=True, exist_ok=True)
            script.write_text("def main():\n    return 0\n", encoding="utf-8")
            (package / "__init__.py").write_text("", encoding="utf-8")

            doc = python_import_consistency_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/vn/scripts/run_project_gui.py",
                generated_business_files=["project_output/vn/scripts/run_project_gui.py", "project_output/vn/src/vn/__init__.py"],
                interface_contract={"project_output/vn/scripts/run_project_gui.py": {"defines": [], "exports": []}},
            )

            self.assertTrue(bool(doc.get("passed", False)))
            self.assertEqual(doc.get("interface_contract_mismatches"), [])


if __name__ == "__main__":
    unittest.main()
