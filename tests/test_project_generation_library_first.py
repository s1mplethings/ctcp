from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze, normalize_source_generation
from tools.providers.project_generation_library_first import verify_library_usage_for_file
from tools.providers.project_generation_provider_payload import normalize_provider_source_payload
from tools.providers.project_generation_provider_source_files import _provider_source_file_rows


VN_CLI_GOAL = "Build a local runnable VN project assistant CLI for characters, story nodes, branch choices, and JSON export."


def _write_json(path: Path, doc: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class ProjectGenerationLibraryFirstTests(unittest.TestCase):
    def test_provider_payload_normalizer_accepts_common_shapes(self) -> None:
        fenced = """
        Provider result:
        ```json
        {
          "source_bundle": {
            "files": {
              "project_output/vn/README.md": "# VN\\n",
              "project_output/vn/src/vn/cli.py": "import typer\\n"
            }
          }
        }
        ```
        """

        doc = normalize_provider_source_payload(fenced)

        self.assertTrue(bool(doc.get("valid", False)))
        self.assertEqual(
            doc["provider_source_files"],
            [
                {"path": "project_output/vn/README.md", "content": "# VN\n"},
                {"path": "project_output/vn/src/vn/cli.py", "content": "import typer\n"},
            ],
        )

    def test_provider_source_rows_use_normalizer_shapes(self) -> None:
        rows = _provider_source_file_rows(
            {
                "project_root": "project_output/vn",
                "src": {
                    "provider_source_files": [
                        {"path": "project_output/vn/src/vn/models.py", "content_lines": ["from pydantic import BaseModel", "class Character(BaseModel):", "    name: str"]},
                    ]
                },
            }
        )

        self.assertEqual(
            rows,
            [{"path": "project_output/vn/src/vn/models.py", "content": "from pydantic import BaseModel\nclass Character(BaseModel):\n    name: str\n"}],
        )

    def test_library_usage_verifier_rejects_missing_required_import(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_library_usage_") as td:
            run_dir = Path(td)
            target = run_dir / "project_output" / "vn" / "src" / "vn" / "cli.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("def main():\n    return 'ok'\n", encoding="utf-8")

            result = verify_library_usage_for_file(
                run_dir=run_dir,
                file_task={
                    "path": "project_output/vn/src/vn/cli.py",
                    "primary_libraries": ["typer"],
                    "must_use": ["typer.Typer"],
                    "must_not_use": ["manual sys.argv parsing"],
                },
            )

            self.assertFalse(bool(result.get("passed", True)))
            required = [row for row in result["checks"] if row.get("check_id") == "required_imports"][0]
            self.assertEqual(required["missing"], ["typer"])

    def test_source_generation_records_library_first_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_library_first_source_") as td:
            run_dir = Path(td)
            contract = normalize_output_contract_freeze(None, goal=VN_CLI_GOAL, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": VN_CLI_GOAL,
                    "files": [{"path": "docs/41_low_capability_project_generation.md", "why": "contract", "content": "library-first provider source"}],
                    "omitted": [],
                },
            )
            provider_path = next(path for path in contract["source_files"] if str(path).endswith(".py"))
            report = normalize_source_generation(
                {
                    "schema_version": "ctcp-provider-source-files-v1",
                    "files": [
                        {
                            "path": provider_path,
                            "content_lines": [
                                "import typer",
                                "from pydantic import BaseModel",
                                "",
                                "app = typer.Typer()",
                                "",
                                "class Character(BaseModel):",
                                "    name: str",
                                "",
                                "@app.command()",
                                "def create_character(name: str) -> None:",
                                "    typer.echo(Character(name=name).model_dump_json())",
                            ],
                        }
                    ],
                    "source_map": {"api_content_source_ref": "API:test/library-first"},
                },
                goal=VN_CLI_GOAL,
                run_dir=run_dir,
            )

            self.assertEqual(report.get("library_plan_path"), "artifacts/library_plan.json")
            self.assertEqual(report.get("file_manifest_path"), "artifacts/file_manifest.json")
            self.assertTrue((run_dir / "artifacts" / "library_plan.json").exists())
            self.assertTrue((run_dir / "artifacts" / "file_manifest.json").exists())
            self.assertTrue((run_dir / "artifacts" / "model_budget.json").exists())
            self.assertTrue((run_dir / "artifacts" / "librarian_experience_record.json").exists())
            self.assertEqual(report.get("model_budget_path"), "artifacts/model_budget.json")
            self.assertEqual(report.get("librarian_experience_record_path"), "artifacts/librarian_experience_record.json")
            self.assertTrue((run_dir / "artifacts" / "library_usage_verification.json").exists())
            self.assertTrue(list(report.get("file_task_paths", [])))
            verification = dict(report.get("library_usage_verification", {}))
            self.assertTrue(bool(verification.get("passed", False)), json.dumps(verification, ensure_ascii=False))
            plan = json.loads((run_dir / "artifacts" / "library_plan.json").read_text(encoding="utf-8"))
            self.assertEqual([row["name"] for row in plan["selected_libraries"]], ["pydantic", "typer"])


if __name__ == "__main__":
    unittest.main()
