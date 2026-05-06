from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from test_project_generation_artifacts import (
    PRODUCTION_GUI_NARRATIVE_GOAL,
    _materialize_production_narrative_project,
    _write_json,
)
from tools.providers.project_generation_artifacts import normalize_project_manifest
from tools.providers.project_generation_artifacts import normalize_deliverable_index
from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_artifacts import normalize_source_generation
from tools.providers.project_generation_provenance import attach_source_generation_provenance


class ProjectGenerationProvenanceTests(unittest.TestCase):
    def test_production_source_generation_blocks_before_local_template_materialization_test(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_provenance_") as td:
            run_dir = Path(td)
            _, report, project_root = _materialize_production_narrative_project(run_dir)

            provider_execution = dict(report.get("provider_execution", {}))
            file_materialization = dict(report.get("file_materialization", {}))
            file_provenance = [dict(row) for row in report.get("file_provenance", []) if isinstance(row, dict)]
            self.assertEqual(str(report.get("status", "")), "blocked")
            self.assertEqual(str(provider_execution.get("provider_identity_source", "")), "artifacts/provider_ledger.jsonl")
            self.assertFalse(bool(provider_execution.get("known_at_source_stage", True)))
            self.assertEqual(str(file_materialization.get("strategy", "")), "disabled_local_templates")
            self.assertEqual(file_provenance, [])
            self.assertFalse((project_root / "src").exists())
            completion = dict(report.get("source_customization_completion", {}))
            self.assertFalse(bool(completion.get("passed", True)))
            self.assertFalse(bool(completion.get("final_delivery_allowed", True)))
            self.assertTrue(bool(completion.get("local_templates_disabled", False)))

            _write_json(run_dir / "artifacts" / "source_generation_report.json", report)
            manifest = normalize_project_manifest(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)
            self.assertEqual(str(dict(manifest.get("file_materialization", {})).get("strategy", "")), "disabled_local_templates")
            self.assertEqual([row for row in manifest.get("file_provenance", []) if isinstance(row, dict)], [])
            self.assertEqual(
                str(dict(manifest.get("provider_execution", {})).get("provider_identity_source", "")),
                "artifacts/provider_ledger.jsonl",
            )
            self.assertFalse(bool(dict(manifest.get("source_customization_completion", {})).get("final_delivery_allowed", True)))
            _write_json(run_dir / "artifacts" / "project_manifest.json", manifest)
            deliverable_index = normalize_deliverable_index(None, goal=PRODUCTION_GUI_NARRATIVE_GOAL, run_dir=run_dir)
            self.assertFalse(bool(deliverable_index.get("final_delivery_allowed", True)))
            self.assertEqual(str(deliverable_index.get("final_package_path", "")), "")
            self.assertTrue(str(deliverable_index.get("delivery_blocked_reason", "")).strip())

    def test_api_content_provenance_allows_final_delivery_test(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_provenance_api_") as td:
            run_dir = Path(td)
            project_root = "project_output/api-demo"
            source_map = {
                "api_content_applied": True,
                "api_content_source_ref": "API:gpt-5.4-mini/demo",
            }
            _write_json(run_dir / project_root / "sample_data" / "source_map.json", source_map)
            report: dict[str, object] = {}
            attach_source_generation_provenance(
                report,
                run_dir,
                {
                    "project_root": project_root,
                    "lists": {"execution_mode": "production"},
                },
                [f"{project_root}/src/app.py"],
                ["source_files"],
            )
            completion = dict(report.get("source_customization_completion", {}))
            self.assertTrue(bool(completion.get("passed", False)))
            self.assertTrue(bool(completion.get("final_delivery_allowed", False)))
            file_provenance = [dict(row) for row in report.get("file_provenance", []) if isinstance(row, dict)]
            self.assertEqual(str(file_provenance[0].get("provider_authorship", "")), "mixed_api_content")

    def test_provider_source_bundle_is_written_without_local_template_fallback_test(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_provider_source_") as td:
            run_dir = Path(td)
            goal = PRODUCTION_GUI_NARRATIVE_GOAL
            contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": goal,
                    "repo_slug": "ctcp",
                    "summary": "provider source bundle context",
                    "files": [{"path": "docs/41_low_capability_project_generation.md", "why": "contract", "content": "provider source files"}],
                    "omitted": [],
                },
            )
            business_files = [str(item) for item in contract.get("business_files", []) if str(item)]
            provider_path = business_files[0]
            report = normalize_source_generation(
                {
                    "schema_version": "ctcp-provider-source-files-v1",
                    "files": [{"path": provider_path, "content": "print('api authored source')\n"}],
                    "source_map": {"api_content_source_ref": "API:test/provider-source"},
                },
                goal=goal,
                run_dir=run_dir,
            )

            self.assertTrue((run_dir / provider_path).exists())
            self.assertNotIn("local project templates are disabled", str(report.get("blocking_reason", "")))
            materialization = dict(report.get("file_materialization", {}))
            self.assertEqual(str(materialization.get("strategy", "")), "provider_authored_source")
            self.assertTrue(bool(materialization.get("api_content_applied", False)))
            self.assertTrue(bool(materialization.get("provider_source_files_applied", False)))
            completion = dict(report.get("source_customization_completion", {}))
            self.assertTrue(bool(completion.get("provider_authored_source_present", False)))
            self.assertFalse(bool(completion.get("local_templates_disabled", True)))

    def test_provider_source_map_preserves_api_content_and_adds_refs_test(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_pg_provider_source_map_") as td:
            run_dir = Path(td)
            goal = PRODUCTION_GUI_NARRATIVE_GOAL
            contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
            _write_json(run_dir / "artifacts" / "output_contract_freeze.json", contract)
            _write_json(
                run_dir / "artifacts" / "context_pack.json",
                {
                    "schema_version": "ctcp-context-pack-v1",
                    "goal": goal,
                    "files": [{"path": "docs/41_low_capability_project_generation.md", "why": "contract", "content": "provider source"}],
                    "omitted": [],
                },
            )
            source_map_path = f"{contract['project_root']}/sample_data/source_map.json"
            startup_path = str(contract["startup_entrypoint"])
            readme_path = str(contract["startup_readme"])
            service_path = f"{contract['project_root']}/src/vn/service.py"
            normalize_source_generation(
                {
                    "schema_version": "ctcp-provider-source-files-v1",
                    "files": [
                        {"path": startup_path, "content": "import argparse\n\nif __name__ == '__main__':\n    argparse.ArgumentParser().parse_args()\n"},
                        {"path": readme_path, "content": "# Project Overview\n\n## Implemented\n\n## Not Implemented\n\n## How To Run\npython scripts/run_project_gui.py --help\n\n## Sample Data\n\n## Directory Map\n\n## Limitations\n"},
                        {"path": service_path, "content": "def smoke():\n    return 'ok'\n"},
                        {
                            "path": source_map_path,
                            "content": '{"content_items":[{"item_id":"api_scene","source":"API:test/source_generation"}],"field_sources":{"scenes.s1.summary":"API:test/source_generation"}}',
                        },
                    ],
                    "source_map": {"api_content_source_ref": "API:test/source_generation"},
                },
                goal=goal,
                run_dir=run_dir,
            )

            final_map = json.loads((run_dir / source_map_path).read_text(encoding="utf-8"))
            self.assertEqual(final_map["content_items"][0]["item_id"], "api_scene")
            self.assertEqual(final_map["field_sources"]["scenes.s1.summary"], "API:test/source_generation")
            self.assertTrue(bool(final_map.get("api_content_applied", False)))
            self.assertIn(service_path, final_map.get("provider_authored_files", []))


if __name__ == "__main__":
    unittest.main()
