import json
import tempfile
import unittest
from pathlib import Path

from frontend.delivery_reply_actions import (
    delivery_plan_failed,
    evaluate_delivery_completion,
    inject_ready_delivery_actions,
)
from frontend.support_reply_policy import render_fallback_reply
from scripts import ctcp_support_bot as support_bot
from scripts.support_public_delivery import finalize_public_delivery_manifest


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
            self.assertEqual(fake.documents[0].name, "final_project_bundle.zip")
            self.assertTrue(fake.documents[0].exists())
            manifest = json.loads((run_dir / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual({item.get("type") for item in manifest.get("sent", [])}, {"document", "photo"})
            self.assertEqual(Path(str(dict(manifest.get("completion_gate", {})).get("selected_document", ""))).name, "final_project_bundle.zip")

    def test_synthesize_delivery_actions_upgrades_to_test_evidence_profile(self) -> None:
        actions = support_bot.synthesize_delivery_actions(
            actions=[],
            user_text="把测试截图发我，不要只发GUI图",
            delivery_state={
                "channel_can_send_files": True,
                "package_delivery_allowed": False,
                "screenshot_ready": True,
                "video_ready": False,
                "screenshot_files": [f"D:/tmp/s{i}.png" for i in range(1, 8)],
                "video_files": [],
            },
            conversation_mode="PROJECT_DETAIL",
        )
        screenshot_actions = [row for row in actions if str(dict(row).get("type", "")).lower() == "send_project_screenshot"]
        self.assertEqual(len(screenshot_actions), 1)
        action = dict(screenshot_actions[0])
        self.assertEqual(int(action.get("count", 0) or 0), 5)
        self.assertEqual(str(action.get("profile", "")), "test_evidence")

    def test_synthesize_delivery_actions_defaults_to_test_evidence_when_available(self) -> None:
        actions = support_bot.synthesize_delivery_actions(
            actions=[],
            user_text="发截图看看",
            delivery_state={
                "channel_can_send_files": True,
                "package_delivery_allowed": False,
                "screenshot_ready": True,
                "video_ready": False,
                "screenshot_files": [
                    "D:/tmp/final-ui.png",
                    "D:/tmp/test-smoke-runtime.png",
                ],
                "video_files": [],
            },
            conversation_mode="PROJECT_DETAIL",
        )
        screenshot_actions = [row for row in actions if str(dict(row).get("type", "")).lower() == "send_project_screenshot"]
        self.assertEqual(len(screenshot_actions), 1)
        action = dict(screenshot_actions[0])
        self.assertEqual(str(action.get("profile", "")), "test_evidence")

    def test_prepare_public_reply_for_telegram_redacts_internal_plan_draft_markers(self) -> None:
        reply = support_bot._prepare_public_reply_for_telegram(
            "当前卡点是：waiting for PLAN_draft.md。下一步我会继续处理：补齐 PLAN_draft.md 并继续推进方案整理。",
            delivery_preview={},
            lang_hint="zh",
        )
        self.assertNotIn("PLAN_draft.md", reply)
        self.assertIn("方案草案", reply)

    def test_prepare_public_reply_for_telegram_prefers_delivery_notice_when_files_will_be_sent(self) -> None:
        reply = support_bot._prepare_public_reply_for_telegram(
            "这轮请求已经进了后端，但目前还没有可直接发送的正式回复。",
            delivery_preview={
                "deliveries": [
                    {"type": "photo", "path": "D:/tmp/test-smoke-runtime.png"},
                    {"type": "document", "path": "D:/tmp/final_project_bundle.zip"},
                ]
            },
            lang_hint="zh",
        )
        self.assertNotIn("没有可直接发送的正式回复", reply)
        self.assertIn("测试截图", reply)
        self.assertIn("项目包", reply)

    def test_inject_ready_delivery_actions_defaults_to_three_test_screenshots_when_available(self) -> None:
        actions = inject_ready_delivery_actions(
            actions=[],
            project_context={"status": {"run_status": "pass", "verify_result": "PASS"}},
            delivery_state={
                "screenshot_ready": True,
                "screenshot_files": [
                    "D:/tmp/final-ui.png",
                    "D:/tmp/test-smoke-runtime.png",
                    "D:/tmp/test-export-validation.png",
                    "D:/tmp/test-replay-acceptance.png",
                ],
                "video_ready": False,
                "video_files": [],
                "package_delivery_allowed": False,
            },
            source_hint="telegram",
        )
        screenshot_actions = [row for row in actions if str(dict(row).get("type", "")).lower() == "send_project_screenshot"]
        self.assertEqual(len(screenshot_actions), 1)
        screenshot_action = dict(screenshot_actions[0])
        self.assertEqual(int(screenshot_action.get("count", 0) or 0), 3)
        self.assertEqual(str(screenshot_action.get("profile", "")), "test_evidence")

    def test_delivery_completion_accepts_test_evidence_first_photo_order(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_delivery_test_profile_gate_") as td:
            root = Path(td)
            replay = self._png(root / "artifacts" / "delivery_replay" / "replayed_screenshot.png")
            final_ui = self._png(root / "project_output" / "vn" / "artifacts" / "screenshots" / "final-ui.png")
            actions = [{"type": "send_project_screenshot", "count": 2, "profile": "test_evidence"}]
            plan = {
                "errors": [],
                "sent": [
                    {"type": "photo", "path": str(replay)},
                    {"type": "photo", "path": str(final_ui)},
                ],
            }
            completion = evaluate_delivery_completion(actions, plan)
            self.assertTrue(bool(completion.get("passed", False)), msg=str(completion.get("reasons", [])))
            self.assertFalse(any("highest-value screenshot" in str(item) for item in completion.get("reasons", [])))

    def test_outbound_send_failure_is_suppressed_after_retry_limit(self) -> None:
        session_state = support_bot.default_support_session_state("retry-limit")
        job = {
            "id": "error:run-demo:abc",
            "kind": "error",
            "run_id": "run-demo",
            "status_hash": "status-hash",
            "reason": "runtime_error",
            "message_hash": "message-hash",
        }
        limit = int(support_bot.SUPPORT_OUTBOUND_REQUEUE_MAX_RETRIES.get("error", 3) or 3)

        keep_retrying = True
        for _ in range(limit + 1):
            session_state["outbound_queue"] = {"pending_ids": [], "jobs": []}
            keep_retrying = support_bot._handle_outbound_send_failure_with_limit(
                session_state=session_state,
                job=job,
                kind="error",
                error_text="public delivery action produced no sent files",
            )
        self.assertFalse(keep_retrying)
        queue = dict(session_state.get("outbound_queue", {}))
        self.assertFalse(list(queue.get("jobs", [])))
        notice = dict(session_state.get("notification_state", {}))
        self.assertEqual(str(notice.get("last_sent_message_hash", "")), "message-hash")

    def test_finalize_public_delivery_manifest_exposes_internal_and_user_acceptance_status(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_delivery_statuses_") as td:
            run_dir = Path(td)
            artifacts = run_dir / "artifacts"
            project_root = run_dir / "project_output" / "indie-studio-production-hub"
            screenshots_dir = project_root / "artifacts" / "screenshots"
            docs_dir = project_root / "docs"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            docs_dir.mkdir(parents=True, exist_ok=True)
            self._png(screenshots_dir / "final-ui.png")
            for index in range(2, 11):
                self._png(screenshots_dir / f"{index:02d}-shot.png")
            for name in ("feature_matrix.md", "page_map.md", "data_model_summary.md", "milestone_plan.md", "startup_guide.md", "replay_guide.md", "mid_stage_review.md"):
                (docs_dir / name).write_text(f"# {name}\n", encoding="utf-8")
            bundle = artifacts / "final_project_bundle.zip"
            bundle.parent.mkdir(parents=True, exist_ok=True)
            bundle.write_bytes(b"PK\x03\x04")
            (artifacts / "project_manifest.json").write_text(
                json.dumps(
                    {
                        "project_domain": "indie_studio_production_hub",
                        "project_type": "indie_studio_hub",
                        "project_archetype": "indie_studio_hub_web",
                        "extended_coverage": {
                            "coverage": {
                                "screenshots": {"actual": 10, "passed": True},
                                "asset_library": {"passed": True},
                                "asset_detail": {"passed": True},
                                "bug_tracker": {"passed": True},
                                "build_release_center": {"passed": True},
                                "docs_center": {"passed": True},
                                "milestone_plan": {"passed": True},
                                "startup_guide": {"passed": True},
                                "replay_guide": {"passed": True},
                                "mid_stage_review": {"passed": True},
                            }
                        },
                        "product_validation": {"profile": "indie_studio_hub", "required": True, "passed": True, "checks": [], "missing": [], "reasons": []},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            plan = finalize_public_delivery_manifest(
                run_dir=run_dir,
                actions=[{"type": "send_project_package"}, {"type": "send_project_screenshot", "count": 1}],
                plan={"sent": [{"type": "document", "path": str(bundle)}, {"type": "photo", "path": str(screenshots_dir / "final-ui.png")}], "deliveries": []},
                replay_runner=lambda **_: {"overall_pass": True},
            )
            self.assertEqual(plan.get("internal_runtime_status"), "PASS")
            self.assertEqual(plan.get("user_acceptance_status"), "PASS")


if __name__ == "__main__":
    unittest.main()
