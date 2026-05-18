from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEW_PACK = ROOT / "meta" / "reports" / "REVIEW_PACK.md"


class LiveProviderMediumProjectReviewPackTests(unittest.TestCase):
    def test_review_pack_contains_phase20_and_phase21_sections(self) -> None:
        text = REVIEW_PACK.read_text(encoding="utf-8")
        self.assertIn("Phase 20 Acceptance Hardening Summary", text)
        self.assertIn("Phase 22 Medium Success Expansion Summary", text)
        self.assertIn("agent-project/scaffold substitution: `no`", text)


if __name__ == "__main__":
    unittest.main()
