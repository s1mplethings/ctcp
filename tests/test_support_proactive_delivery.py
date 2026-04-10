import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import ctcp_support_bot as support_bot


class SupportProactiveDeliveryTests(unittest.TestCase):
    def test_controller_result_push_emits_public_delivery_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_controller_delivery_") as td:
            root = Path(td)
            support_run_dir = root / "support-session"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            project_dir = root / "generated_projects" / "story_organizer"
            project_dir.mkdir(parents=True, exist_ok=True)
            (project_dir / "README.md").write_text("# story_organizer\n", encoding="utf-8")
            screenshot = project_dir / "artifacts" / "screenshots" / "overview.png"
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            screenshot.write_bytes(b"\x89PNG\r\n\x1a\n")
            session_state = support_bot.default_support_session_state("123")
            session_state["outbound_queue"] = {
                "pending_ids": ["result:run-demo:1"],
                "jobs": [{
                    "id": "result:run-demo:1",
                    "kind": "result",
                    "run_id": "run-demo",
                    "status_hash": "hash-result",
                    "reason": "final_ready",
                    "message_hash": "hash-result",
                    "created_ts": support_bot.now_iso(),
                }],
            }
            project_context = {"run_id": "run-demo", "status": {"run_status": "pass", "verify_result": "PASS"}}

            class _FakeTelegram:
                def __init__(self) -> None:
                    self.sent_messages: list[tuple[int, str]] = []
                    self.sent_documents: list[tuple[int, Path, str]] = []
                    self.sent_photos: list[tuple[int, Path, str]] = []

                def send_message(self, chat_id: int, text: str) -> None:
                    self.sent_messages.append((chat_id, text))

                def send_document(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    self.sent_documents.append((chat_id, file_path, caption))

                def send_photo(self, chat_id: int, file_path: Path, caption: str = "") -> None:
                    self.sent_photos.append((chat_id, file_path, caption))

            with mock.patch.object(
                support_bot,
                "build_grounded_status_reply_doc",
                return_value={
                    "reply_text": "我现在直接把 zip 包和结果截图发到当前对话。",
                    "provider_status": "executed",
                    "actions": [{"type": "send_project_package"}, {"type": "send_project_screenshot"}],
                },
            ), mock.patch.object(
                support_bot,
                "collect_public_delivery_state",
                return_value={
                    "package_ready": True,
                    "package_delivery_allowed": True,
                    "screenshot_ready": True,
                    "package_source_dirs": [str(project_dir)],
                    "ctcp_package_source_dirs": [],
                    "placeholder_package_source_dirs": [],
                    "existing_package_files": [],
                    "screenshot_files": [str(screenshot)],
                    "project_name_hint": "story_organizer",
                },
            ):
                fake = _FakeTelegram()
                sent = support_bot._emit_controller_outbound_jobs(
                    tg=fake,  # type: ignore[arg-type]
                    chat_id=123,
                    run_dir=support_run_dir,
                    session_state=session_state,
                    project_context=project_context,
                    auto_advanced=False,
                    recovered_candidate=None,
                )

            self.assertEqual(sent, 1)
            self.assertEqual(len(fake.sent_messages), 1)
            self.assertEqual(len(fake.sent_documents), 1)
            self.assertEqual(len(fake.sent_photos), 1)
            manifest = json.loads((support_run_dir / support_bot.SUPPORT_PUBLIC_DELIVERY_REL_PATH).read_text(encoding="utf-8"))
            self.assertEqual(len(list(manifest.get("sent", []))), 2)

    def test_controller_result_push_requeues_when_delivery_manifest_has_no_sent_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_controller_delivery_fail_") as td:
            support_run_dir = Path(td) / "support-session"
            (support_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            session_state = support_bot.default_support_session_state("123")
            session_state["outbound_queue"] = {
                "pending_ids": ["result:run-demo:1"],
                "jobs": [{"id": "result:run-demo:1", "kind": "result", "run_id": "run-demo", "status_hash": "hash-result", "reason": "final_ready"}],
            }

            class _FakeTelegram:
                def __init__(self) -> None:
                    self.sent_messages: list[tuple[int, str]] = []
                def send_message(self, chat_id: int, text: str) -> None:
                    self.sent_messages.append((chat_id, text))

            with mock.patch.object(
                support_bot,
                "build_grounded_status_reply_doc",
                return_value={"reply_text": "我现在直接把 zip 包发到当前对话。", "provider_status": "executed", "actions": [{"type": "send_project_package"}]},
            ), mock.patch.object(
                support_bot,
                "collect_public_delivery_state",
                return_value={"package_ready": True, "package_delivery_allowed": True, "screenshot_ready": False, "package_source_dirs": [], "existing_package_files": []},
            ):
                sent = support_bot._emit_controller_outbound_jobs(
                    tg=_FakeTelegram(),  # type: ignore[arg-type]
                    chat_id=123,
                    run_dir=support_run_dir,
                    session_state=session_state,
                    project_context={"run_id": "run-demo", "status": {"run_status": "pass"}},
                    auto_advanced=False,
                    recovered_candidate=None,
                )

            self.assertEqual(sent, 0)
            queued = list(dict(session_state.get("outbound_queue", {})).get("jobs", []))
            self.assertTrue(queued)


if __name__ == "__main__":
    unittest.main()
