from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"


class LiveProviderMediumProjectAttributionTests(unittest.TestCase):
    def test_attribution_exists_for_every_medium_case(self) -> None:
        doc = json.loads(SUMMARY.read_text(encoding="utf-8"))
        for row in doc.get("cases", []):
            path = Path(row["attribution_path"])
            self.assertTrue(path.exists())
            attr = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(attr.get("generation_mode"), "live_provider_medium_candidate")
            self.assertTrue(attr.get("medium_case"))
            self.assertFalse(attr.get("used_agent_project"))
            self.assertFalse(attr.get("used_agent_scaffold"))
            self.assertFalse(attr.get("used_local_agent_runtime"))
            self.assertTrue(attr.get("used_provider_agent"))
            self.assertIn(attr.get("provider_candidate_outcome"), {"accepted", "repaired", "fallback", "unsupported"})
            self.assertIn("provider_authored_file_ratio", attr)
            self.assertEqual(attr.get("medium_project_contract_path"), "artifacts/medium_project_contract.json")
            contract_path = path.parent / "medium_project_contract.json"
            self.assertTrue(contract_path.exists())


if __name__ == "__main__":
    unittest.main()
