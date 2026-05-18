from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
for item in (ROOT, TESTS_DIR):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from provider_assisted_benchmark.validators.summary import ensure_provider_review_pack, load_or_run_summary


class ProviderAssistedAttributionTests(unittest.TestCase):
    def test_attribution_records_provider_participation(self) -> None:
        summary = load_or_run_summary()
        for row in summary["projects"]:
            attr = row["attribution"]
            self.assertTrue(attr["ordinary_mainline"])
            self.assertFalse(attr["used_agent_project"])
            self.assertFalse(attr["used_agent_scaffold"])
            self.assertFalse(attr["used_local_agent_runtime"])
            self.assertTrue(attr["used_local_materializer"])
            self.assertTrue(attr["used_provider_agent"])
            self.assertEqual(attr["provider_authorship"], "provider_assisted")
            self.assertEqual(attr["generation_mode"], "provider_assisted")
            self.assertTrue(attr["provider_assisted_sections"])
            self.assertTrue(attr["provider_generated_files"])
            self.assertFalse(attr["provider_validation"]["fallback_triggered"])

    def test_provider_evidence_files_exist(self) -> None:
        summary = load_or_run_summary()
        for row in summary["projects"]:
            provider_path = Path(row["provider_assisted_generation_path"])
            self.assertTrue(provider_path.exists())
            provider_doc = json.loads(provider_path.read_text(encoding="utf-8"))
            self.assertTrue(provider_doc["provider_generated_files"])

    def test_review_pack_contains_provider_participation_summary(self) -> None:
        review_pack = ensure_provider_review_pack()
        text = review_pack.read_text(encoding="utf-8")
        self.assertIn("Provider Participation Summary", text)
        self.assertIn("provider-assisted benchmark", text)
        self.assertIn("provider_assisted_csv_tool", text)


if __name__ == "__main__":
    unittest.main()
