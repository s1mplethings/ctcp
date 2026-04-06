from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.project_delivery_evidence_bridge import (
    build_delivery_evidence_manifest,
    write_delivery_evidence_manifest,
)


class DeliveryEvidenceBridgeTests(unittest.TestCase):
    def test_build_and_write_delivery_evidence_manifest(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_delivery_evidence_") as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "reports").mkdir(parents=True, exist_ok=True)
            (run_dir / "screenshots").mkdir(parents=True, exist_ok=True)
            (run_dir / "demo").mkdir(parents=True, exist_ok=True)
            (run_dir / "outputs").mkdir(parents=True, exist_ok=True)

            (run_dir / "reports" / "report.html").write_text("<html>ok</html>", encoding="utf-8")
            (run_dir / "screenshots" / "overview.png").write_bytes(b"\x89PNG\r\n")
            (run_dir / "demo" / "walkthrough.gif").write_bytes(b"GIF89a")
            (run_dir / "outputs" / "result.json").write_text('{"ok": true}\n', encoding="utf-8")
            (run_dir / "artifacts" / "frontend_request.json").write_text(
                '{"goal": "deliver a local MVP with visible evidence"}\n',
                encoding="utf-8",
            )

            project_manifest = {
                "project_root": str((run_dir / "project").resolve()),
                "manifest_source": "declared",
                "project_intent": {"goal_summary": "deliver a local MVP with visible evidence"},
                "generic_validation": {"passed": True},
                "domain_validation": {"kind": "web_service", "passed": True},
            }
            artifacts = [
                {"rel_path": "reports/report.html", "kind": "report", "mime_type": "text/html"},
                {"rel_path": "screenshots/overview.png", "kind": "image", "mime_type": "image/png"},
                {"rel_path": "demo/walkthrough.gif", "kind": "image", "mime_type": "image/gif"},
                {"rel_path": "outputs/result.json", "kind": "code", "mime_type": "application/json"},
            ]
            verify_report = {"result": "PASS"}

            manifest = build_delivery_evidence_manifest(
                run_id="demo-run",
                run_dir=run_dir,
                project_manifest=project_manifest,
                artifacts=artifacts,
                verify_report=verify_report,
            )
            self.assertEqual(str(manifest.get("status", "")), "ready")
            self.assertEqual(str(manifest.get("primary_report_path", "")), str((run_dir / "reports" / "report.html").resolve()))
            self.assertEqual(len(list(manifest.get("screenshots", []))), 1)
            self.assertEqual(len(list(manifest.get("demo_media", []))), 1)
            self.assertEqual(str(dict(manifest.get("verification_summary", {})).get("verify_result", "")), "PASS")

            rel_path = write_delivery_evidence_manifest(run_dir, manifest)
            target = run_dir / rel_path
            self.assertTrue(target.exists(), msg=str(target))


if __name__ == "__main__":
    unittest.main()
