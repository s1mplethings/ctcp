from __future__ import annotations

import json
import unittest

from tools.providers.project_generation_provenance_writer import concrete_fast_path_provenance, provenance_json
from tools.providers.project_generation_template_writer import prefixed_files, standard_support_files, static_asset_files


class ProjectGenerationTemplateWriterTests(unittest.TestCase):
    def test_prefixed_files_and_static_assets(self) -> None:
        files = prefixed_files("project_output/example", {"README.md": "# Example\n", **static_asset_files(index_html="html", app_js="js", styles_css="css")})
        self.assertEqual(files["project_output/example/README.md"], "# Example\n")
        self.assertEqual(files["project_output/example/static/app.js"], "js")

    def test_standard_support_files_uses_provenance_helper(self) -> None:
        provenance = concrete_fast_path_provenance(project_type="example_project", reason="unit test")
        support = standard_support_files(project_id="example_project", workflow_doc_rel="docs/workflow.md", provenance=provenance, core_notes="core", workflow_notes="workflow")
        self.assertIn("scripts/verify_repo.ps1", support)
        self.assertIn("docs/workflow.md", support)
        self.assertEqual(json.loads(support["provenance.json"])["project_type"], "example_project")
        self.assertEqual(json.loads(provenance_json(provenance))["provider_authorship"], "not_claimed")


if __name__ == "__main__":
    unittest.main()
