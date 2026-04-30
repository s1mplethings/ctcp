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
        seed = path.name.encode("utf-8", errors="ignore")[:24]
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + seed)
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

    def test_telegram_delivery_prefers_real_ui_over_evidence_card(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_priority_") as td:
            root = Path(td)
            evidence_card = self._png(root / "artifacts" / "screenshots" / "evidence-card.png")
            final_ui = self._png(root / "artifacts" / "screenshots" / "final-ui.png")

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=root,
                actions=[{"type": "send_project_screenshot", "count": 1}],
                delivery_state={"screenshot_files": [str(evidence_card), str(final_ui)]},
            )

            self.assertEqual(Path(str(plan["deliveries"][0]["path"])).name, "final-ui.png")

    def test_telegram_delivery_excludes_delivery_replay_screenshots(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_replay_block_") as td:
            root = Path(td)
            replayed = self._png(root / "artifacts" / "delivery_replay" / "replay_artifacts" / "replayed_screenshot.png")
            final_ui = self._png(root / "artifacts" / "screenshots" / "final-ui.png")

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=root,
                actions=[{"type": "send_project_screenshot", "count": 2}],
                delivery_state={"screenshot_files": [str(replayed), str(final_ui)]},
            )

            deliveries = [row for row in plan.get("deliveries", []) if str(dict(row).get("type", "")).lower() == "photo"]
            names = [Path(str(dict(row).get("path", ""))).name for row in deliveries]
            self.assertEqual(names, ["final-ui.png"])

    def test_telegram_delivery_blocks_replay_artifact_when_it_is_the_only_candidate(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_replay_only_") as td:
            root = Path(td)
            replayed = self._png(root / "artifacts" / "delivery_replay" / "replay_artifacts" / "replayed_screenshot.png")

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=root,
                actions=[{"type": "send_project_screenshot", "count": 1}],
                delivery_state={"screenshot_files": [str(replayed)]},
            )

            deliveries = [row for row in plan.get("deliveries", []) if str(dict(row).get("type", "")).lower() == "photo"]
            self.assertEqual(deliveries, [])
            self.assertTrue(any("no screenshot artifact is available" in str(item) for item in plan.get("errors", [])))

    def test_telegram_delivery_dedupes_same_image_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_dedupe_") as td:
            root = Path(td)
            src = self._png(root / "project_output" / "demo" / "artifacts" / "screenshots" / "final-ui.png")
            copied = root / "artifacts" / "delivery_replay" / "extracted" / "artifacts" / "screenshots" / "final-ui.png"
            copied.parent.mkdir(parents=True, exist_ok=True)
            copied.write_bytes(src.read_bytes())

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=root,
                actions=[{"type": "send_project_screenshot", "count": 2}],
                delivery_state={"screenshot_files": [str(src), str(copied)]},
            )

            deliveries = [row for row in plan.get("deliveries", []) if str(dict(row).get("type", "")).lower() == "photo"]
            self.assertEqual(len(deliveries), 1)
            self.assertEqual(Path(str(deliveries[0]["path"])).name, "final-ui.png")

    def test_test_evidence_profile_prefers_test_screenshots_and_allows_up_to_five(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_test_evidence_") as td:
            root = Path(td)
            final_ui = self._png(root / "artifacts" / "screenshots" / "final-ui.png")
            page_02 = self._png(root / "artifacts" / "screenshots" / "02-project_list.png")
            test_smoke = self._png(root / "artifacts" / "test_screenshots" / "test-smoke-runtime.png")
            test_export = self._png(root / "artifacts" / "test_screenshots" / "test-export-validation.png")
            test_replay = self._png(root / "artifacts" / "test_screenshots" / "test-replay-acceptance.png")

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=root,
                actions=[{"type": "send_project_screenshot", "count": 5, "profile": "test_evidence"}],
                delivery_state={
                    "screenshot_files": [
                        str(page_02),
                        str(final_ui),
                        str(test_smoke),
                        str(test_export),
                        str(test_replay),
                    ]
                },
            )

            deliveries = [row for row in plan.get("deliveries", []) if str(dict(row).get("type", "")).lower() == "photo"]
            names = [Path(str(dict(row).get("path", ""))).name for row in deliveries]
            self.assertEqual(len(deliveries), 5)
            self.assertEqual(names[0], "test-export-validation.png")
            self.assertIn("test-smoke-runtime.png", names)
            self.assertIn("test-replay-acceptance.png", names)
            self.assertIn("final-ui.png", names)

    def test_default_screenshot_action_prefers_test_screenshots_when_available(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_screenshot_default_test_priority_") as td:
            root = Path(td)
            final_ui = self._png(root / "artifacts" / "screenshots" / "final-ui.png")
            test_smoke = self._png(root / "artifacts" / "test_screenshots" / "test-smoke-runtime.png")

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=root,
                actions=[{"type": "send_project_screenshot", "count": 1}],
                delivery_state={"screenshot_files": [str(final_ui), str(test_smoke)]},
            )

            deliveries = [row for row in plan.get("deliveries", []) if str(dict(row).get("type", "")).lower() == "photo"]
            self.assertEqual(len(deliveries), 1)
            self.assertEqual(Path(str(deliveries[0]["path"])).name, "test-smoke-runtime.png")


if __name__ == "__main__":
    unittest.main()
