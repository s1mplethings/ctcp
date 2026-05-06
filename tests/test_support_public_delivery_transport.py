from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.support_public_delivery import VirtualDeliveryTransport


class SupportPublicDeliveryTransportTests(unittest.TestCase):
    def test_virtual_delivery_uses_unique_path_when_target_exists(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_virtual_delivery_unique_") as td:
            run_dir = Path(td) / "run"
            source_dir = Path(td) / "src"
            source_dir.mkdir(parents=True, exist_ok=True)
            source = source_dir / "final_project_bundle.zip"
            source.write_bytes(b"zip1")
            target = run_dir / "artifacts" / "support_exports" / "virtual_delivery" / "sent" / "documents" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"existing")

            receipt = VirtualDeliveryTransport(run_dir=run_dir).send_document(0, source)
            delivered = Path(str(receipt.get("delivered_path", "")))
            self.assertEqual(delivered.name, "final_project_bundle-2.zip")
            self.assertEqual(delivered.read_bytes(), b"zip1")


if __name__ == "__main__":
    unittest.main()
