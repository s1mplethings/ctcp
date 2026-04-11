import json
import tempfile
import unittest
from pathlib import Path

from frontend.delivery_reply_actions import delivery_plan_failed
from frontend.support_reply_policy import render_fallback_reply
from scripts import ctcp_support_bot as support_bot


class SupportDeliveryUserVisibleContractTests(unittest.TestCase):
    def _png(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"\x89PNG\r\n\x1a\n")
        return path

    def test_screenshot_delivery_prefers_final_product_image_over_overview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_delivery_priority_") as td:
            run_dir = Path(td) / "support-session"
            project_dir = Path(td) / "project"
            run_dir.mkdir(parents=True, exist_ok=True)
            project_dir.mkdir(parents=True, exist_ok=True)
            overview = self._png(project_dir / "artifacts" / "screenshots" / "overview.png")
            preview = self._png(project_dir / "artifacts" / "screenshots" / "preview.png")
            final_ui = self._png(project_dir / "artifacts" / "screenshots" / "final-ui.png")

            plan = support_bot.resolve_public_delivery_plan(
                run_dir=run_dir,
                actions=[{"type": "send_project_screenshot", "count": 1}],
                delivery_state={"screenshot_files": [str(overview), str(preview), str(final_ui)]},
            )

            deliveries = list(plan.get("deliveries", []))
            self.assertEqual(len(deliveries), 1)
            self.assertEqual(Path(str(deliveries[0].get("path", ""))).name, "final-ui.png")

    def test_humanized_delivery_reply_hides_internal_state_and_explains_how_to_start(self) -> None:
        reply = render_fallback_reply(
            intent="deliver_result",
            lang_hint="zh",
            project_context={
                "project_manifest": {
                    "startup_entrypoint": "generated_projects/story_organizer/main.py",
                    "startup_readme": "generated_projects/story_organizer/README.md",
                }
            },
        )["reply_text"]

        self.assertIn("成品截图", reply)
        self.assertIn("zip", reply.lower())
        self.assertIn("README", reply)
        self.assertIn("启动入口", reply)
        self.assertIn("说明执行", reply)
        for forbidden in ("stage", "artifact", ".json", "source_generation_report", "Produced artifacts", "Startup entry"):
            self.assertNotIn(forbidden.lower(), reply.lower())

    def test_english_delivery_reply_uses_user_facing_package_language(self) -> None:
        reply = render_fallback_reply(
            intent="deliver_result",
            lang_hint="en",
            project_context={
                "project_manifest": {
                    "startup_entrypoint": "generated_projects/story_organizer/main.py",
                    "startup_readme": "generated_projects/story_organizer/README.md",
                }
            },
        )["reply_text"]

        low = reply.lower()
        self.assertIn("final screenshot", low)
        self.assertIn("zip package", low)
        self.assertIn("startup entry", low)
        self.assertIn("README", reply)
        self.assertNotIn("Produced artifacts", reply)
        self.assertNotIn("Startup entry", reply)

    def test_delivery_action_without_matching_sent_file_is_failed(self) -> None:
        actions = [{"type": "send_project_package"}, {"type": "send_project_screenshot"}]
        self.assertTrue(delivery_plan_failed(actions, {"errors": [], "sent": [{"type": "document", "path": "project.zip"}]}))
        self.assertTrue(delivery_plan_failed(actions, {"errors": [], "sent": [{"type": "photo", "path": "final-ui.png"}]}))
        self.assertFalse(
            delivery_plan_failed(
                actions,
                {"errors": [], "sent": [{"type": "document", "path": "project.zip"}, {"type": "photo", "path": "final-ui.png"}]},
            )
        )

    def test_public_delivery_sends_photo_document_and_records_real_sent_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_delivery_real_") as td:
            root = Path(td)
            run_dir = root / "support-session"
            project_dir = root / "project"
            project_dir.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "README.md").write_text("# Demo\n\nRun: python app.py\n", encoding="utf-8")
            (project_dir / "app.py").write_text("print('demo')\n", encoding="utf-8")
            overview = self._png(project_dir / "artifacts" / "screenshots" / "overview.png")
            final_ui = self._png(project_dir / "artifacts" / "screenshots" / "final-ui.png")

            class FakeTelegram:
                def __init__(self) -> None:
                    self.documents: list[Path] = []
                    self.photos: list[Path] = []

                def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    self.documents.append(file_path)

                def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    self.photos.append(file_path)

            fake = FakeTelegram()
            plan = support_bot.emit_public_delivery(
                fake,  # type: ignore[arg-type]
                chat_id=123,
                run_dir=run_dir,
                actions=[{"type": "send_project_package"}, {"type": "send_project_screenshot", "count": 1}],
                delivery_state={
                    "package_delivery_allowed": True,
                    "package_source_dirs": [str(project_dir)],
                    "ctcp_package_source_dirs": [],
                    "placeholder_package_source_dirs": [],
                    "existing_package_files": [],
                    "screenshot_files": [str(overview), str(final_ui)],
                },
            )

            self.assertFalse(plan.get("errors"), msg=json.dumps(plan, ensure_ascii=False))
            self.assertEqual(len(fake.documents), 1)
            self.assertEqual(len(fake.photos), 1)
            self.assertEqual(fake.photos[0].name, "final-ui.png")
            self.assertTrue(fake.documents[0].exists())
            manifest = json.loads((run_dir / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual({item.get("type") for item in manifest.get("sent", [])}, {"document", "photo"})


if __name__ == "__main__":
    unittest.main()
