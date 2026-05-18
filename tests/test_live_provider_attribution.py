from __future__ import annotations

import unittest
from pathlib import Path
import sys

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_benchmark.validators.summary import ensure_live_review_pack, load_or_run_summary


class LiveProviderAttributionTests(unittest.TestCase):
    def test_attribution_marks_live_provider_participation(self) -> None:
        summary = load_or_run_summary()
        for row in summary["projects"]:
            attr = row["attribution"]
            self.assertTrue(attr["ordinary_mainline"])
            self.assertFalse(attr["used_agent_project"])
            self.assertFalse(attr["used_agent_scaffold"])
            self.assertFalse(attr["used_local_agent_runtime"])
            self.assertTrue(attr["used_local_materializer"])
            self.assertTrue(attr["used_provider_agent"])
            self.assertTrue(attr["live_provider_used"])
            self.assertEqual(attr["provider_authorship"], "provider_assisted")

    def test_review_pack_has_live_provider_section(self) -> None:
        review_pack = ensure_live_review_pack()
        text = review_pack.read_text(encoding="utf-8")
        self.assertIn("## Live Provider Participation", text)
        self.assertIn("provider request count", text.lower())


if __name__ == "__main__":
    unittest.main()
