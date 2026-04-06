from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from http_mvp_spec_workflow_plan_acceptance_json_heal.app import generate_payload, health_payload
from http_mvp_spec_workflow_plan_acceptance_json_heal.service import generate_project


class WebServiceTests(unittest.TestCase):
    def test_generate_project_exports_service_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="web_service_") as td:
            result = generate_project(goal="web smoke", project_name="Web Copilot", out_dir=Path(td))
            self.assertEqual(health_payload()["status"], "ok")
            payload = generate_payload("goal", "Web Copilot")
            self.assertTrue(payload["contract"])
            self.assertTrue(Path(result["service_contract_json"]).exists())
            json.loads(Path(result["sample_response_json"]).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
