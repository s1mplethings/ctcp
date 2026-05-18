from __future__ import annotations

import unittest

from tools.providers.project_generation_medium_candidate import medium_file_batches, normalize_medium_batch


class LiveProviderMediumCandidateBatchingTests(unittest.TestCase):
    def test_batch_paths_restricted_to_manifest_subset(self) -> None:
        project = "live_provider_knowledge_base_app"
        batch = medium_file_batches(project)[0]
        files, errors = normalize_medium_batch(
            project,
            {
                "files": [
                    {"path": "README.md", "content": "# KB"},
                    {"path": "app.py", "content": "print('ok')"},
                    {"path": "kb_store.py", "content": "class KnowledgeBaseStore: pass"},
                    {"path": "../bad.py", "content": "bad"},
                ]
            },
            batch,
        )
        self.assertIn("README.md", files)
        self.assertTrue(any("disallowed_path" in item for item in errors))

    def test_missing_batch_file_is_reported(self) -> None:
        project = "live_provider_inventory_manager_app"
        files, errors = normalize_medium_batch(
            project,
            {"files": [{"path": "README.md", "content": "# Inventory"}]},
            medium_file_batches(project)[0],
        )
        self.assertIn("README.md", files)
        self.assertTrue(any("missing_batch_file:app.py" == item for item in errors))


if __name__ == "__main__":
    unittest.main()
