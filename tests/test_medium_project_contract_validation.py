from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.providers.project_generation_medium_candidate import medium_project_contract


ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "tests" / "live_provider_medium_project_benchmark" / "generated" / "live_provider_medium_project_summary.json"


class MediumProjectContractValidationTests(unittest.TestCase):
    def test_contract_function_covers_routes_and_files(self) -> None:
        event = medium_project_contract("live_provider_event_booking_app")
        invoice = medium_project_contract("live_provider_invoice_manager_app")
        self.assertIn("POST /events/{id}/bookings", event["routes"])
        self.assertIn("event_store.py", event["required_files"])
        self.assertIn("POST /invoices/{id}/items", invoice["routes"])
        self.assertIn("invoice_store.py", invoice["required_files"])

    def test_benchmark_writes_contract_artifact_for_every_case(self) -> None:
        doc = json.loads(SUMMARY.read_text(encoding="utf-8"))
        for row in doc.get("cases", []):
            self.assertTrue(row.get("medium_project_contract_ok"))
            path = Path(row["medium_project_contract_path"])
            self.assertTrue(path.exists())
            contract = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(contract.get("case_name"), row.get("project"))


if __name__ == "__main__":
    unittest.main()
