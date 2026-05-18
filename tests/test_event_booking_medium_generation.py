from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"


class EventBookingMediumGenerationTests(unittest.TestCase):
    def test_event_booking_case_passed(self) -> None:
        doc = json.loads(SUMMARY.read_text(encoding="utf-8"))
        rows = {row.get("project"): row for row in doc.get("cases", [])}
        self.assertIn("live_provider_event_booking_app", rows)
        row = rows["live_provider_event_booking_app"]
        self.assertEqual(row.get("status"), "passed")
        self.assertIn(row.get("outcome"), {"accepted", "repaired", "fallback", "unsupported"})
        self.assertTrue(row.get("runtime_validation", {}).get("passed"))
        self.assertTrue(row.get("medium_project_contract_ok"))


if __name__ == "__main__":
    unittest.main()
