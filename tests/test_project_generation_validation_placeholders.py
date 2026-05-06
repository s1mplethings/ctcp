from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers.project_generation_validation import generic_validation


class ProjectGenerationValidationPlaceholderTests(unittest.TestCase):
    def test_asset_placeholder_data_filename_is_not_placeholder_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_asset_placeholder_name_") as td:
            run_dir = Path(td)
            root = run_dir / "project_output" / "vn"
            script = root / "scripts" / "run_project_gui.py"
            catalog = root / "src" / "vn" / "assets" / "catalog.py"
            readme = root / "README.md"
            catalog.parent.mkdir(parents=True, exist_ok=True)
            script.parent.mkdir(parents=True, exist_ok=True)
            readme.write_text("# VN\n\npython scripts/run_project_gui.py --help\n", encoding="utf-8")
            script.write_text("print('ok')\n", encoding="utf-8")
            catalog.write_text("def get_asset_list():\n    return './sample_data/pipeline/asset_placeholders.json'\n", encoding="utf-8")

            doc = generic_validation(
                run_dir=run_dir,
                startup_entrypoint="project_output/vn/scripts/run_project_gui.py",
                startup_readme="project_output/vn/README.md",
                generated_business_files=["project_output/vn/scripts/run_project_gui.py", "project_output/vn/src/vn/assets/catalog.py"],
                behavior_probe={"rc": 0},
                export_probe={"rc": 0},
                acceptance_files=["project_output/vn/README.md"],
            )

            self.assertEqual(doc.get("placeholder_hits"), [])


if __name__ == "__main__":
    unittest.main()
