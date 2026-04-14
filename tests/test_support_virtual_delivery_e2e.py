from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support_virtual_delivery_e2e_runner import run_virtual_delivery_e2e


class SupportVirtualDeliveryE2ETests(unittest.TestCase):
    def test_virtual_delivery_e2e_proves_photo_document_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_virtual_delivery_test_") as td:
            result = run_virtual_delivery_e2e(Path(td))
            completion_gate = dict(result.get("completion_gate", {}))
            self.assertTrue(bool(completion_gate.get("passed", False)))
            self.assertEqual(list(result.get("sent_types", [])), ["document", "photo"])
            self.assertEqual(Path(str(result.get("selected_photo", ""))).name, "final-ui.png")
            self.assertTrue(bool(completion_gate.get("cold_replay_passed", False)))
            self.assertTrue(Path(str(completion_gate.get("replay_screenshot_path", ""))).exists())



if __name__ == "__main__":
    unittest.main()
