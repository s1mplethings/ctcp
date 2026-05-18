from __future__ import annotations

import sys
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from live_provider_full_candidate_benchmark.validators.summary import ensure_full_candidate_review_pack


class LiveProviderFullCandidateReviewPackTests(unittest.TestCase):
    def test_review_pack_contains_full_candidate_summary(self) -> None:
        path = ensure_full_candidate_review_pack()
        text = path.read_text(encoding="utf-8")
        self.assertIn("Live Provider Full Candidate Summary", text)
        self.assertIn("provider project candidate count", text.lower())
        self.assertIn("deterministic", text.lower())


if __name__ == "__main__":
    unittest.main()

