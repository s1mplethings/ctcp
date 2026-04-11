from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from frontend.delivery_reply_actions import prioritize_screenshot_files
from scripts import ctcp_support_bot as support_bot
from scripts.project_delivery_evidence_bridge import build_delivery_evidence_manifest


class ScreenshotPrioritySelectionTests(unittest.TestCase):
    def _png(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        return path

    def test_overview_and_final_ui_prefers_final_ui(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_priority_") as td:
            root = Path(td)
            overview = self._png(root / "artifacts" / "screenshots" / "overview.png")
            debug = self._png(root / "artifacts" / "screenshots" / "debug.png")
            result = self._png(root / "artifacts" / "screenshots" / "result.png")
            final_ui = self._png(root / "artifacts" / "screenshots" / "final-ui.png")

            ordered = prioritize_screenshot_files([str(overview), str(debug), str(result), str(final_ui)])
            self.assertEqual(Path(str(ordered[0])).name, "final-ui.png")

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=root,
                actions=[{"type": "send_project_screenshot", "count": 1}],
                delivery_state={"screenshot_files": [str(overview), str(debug), str(result), str(final_ui)]},
            )
            self.assertEqual(Path(str(plan["deliveries"][0]["path"])).name, "final-ui.png")

    def test_debug_and_result_prefers_result(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_priority_") as td:
            root = Path(td)
            debug = self._png(root / "artifacts" / "screenshots" / "debug.png")
            result = self._png(root / "artifacts" / "screenshots" / "result.png")

            ordered = prioritize_screenshot_files([str(debug), str(result)])
            self.assertEqual(Path(str(ordered[0])).name, "result.png")

    def test_delivery_evidence_bridge_prefers_product_screenshot(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_delivery_bridge_priority_") as td:
            run_dir = Path(td)
            self._png(run_dir / "screenshots" / "overview.png")
            self._png(run_dir / "screenshots" / "final-ui.png")
            manifest = build_delivery_evidence_manifest(
                run_id="run-priority",
                run_dir=run_dir,
                project_manifest={
                    "project_root": "project_output/demo",
                    "project_intent": {"goal_summary": "demo"},
                    "generic_validation": {"passed": True},
                    "domain_validation": {"kind": "gui", "passed": True},
                },
                artifacts=[
                    {"rel_path": "screenshots/overview.png", "kind": "image", "mime_type": "image/png"},
                    {"rel_path": "screenshots/final-ui.png", "kind": "image", "mime_type": "image/png"},
                ],
                verify_report={"result": "PASS"},
            )

            screenshots = list(manifest.get("screenshots", []))
            self.assertEqual(Path(str(dict(screenshots[0]).get("path", ""))).name, "final-ui.png")


if __name__ == "__main__":
    unittest.main()
