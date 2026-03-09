import json
import tempfile
import unittest
from pathlib import Path

from tools.telegram_cs_bot import Bot, Config


FIXTURE_PATH = Path("tests/fixtures/telegram_bot_dataset_v1/cases.jsonl")


class _FakeTg:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, *, chat_id, text, reply_to=None, markup=None):  # type: ignore[no-untyped-def]
        self.messages.append(str(text))
        return {"message_id": len(self.messages)}

    def send_doc(self, *, chat_id, path, caption="", reply_to=None):  # type: ignore[no-untyped-def]
        self.messages.append(f"[DOC] {caption}")
        return {"message_id": len(self.messages)}

    def edit(self, *, chat_id, msg_id, text):  # type: ignore[no-untyped-def]
        self.messages.append(str(text))

    def answer_cb(self, cb_id, text=""):  # type: ignore[no-untyped-def]
        self.messages.append(str(text))


def _load_cases() -> list[dict]:
    rows: list[dict] = []
    for line in FIXTURE_PATH.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        doc = json.loads(raw)
        if isinstance(doc, dict):
            rows.append(doc)
    return rows


def _new_config(base: Path) -> Config:
    return Config(
        token="fake",
        allowlist=None,
        repo_root=Path("d:/.c_projects/adc/ctcp").resolve(),
        state_db=base / "state.sqlite3",
        poll_seconds=1,
        tick_seconds=1,
        auto_advance=False,
        api_enabled=False,
        api_model="gpt-4.1-mini",
        api_timeout_sec=10,
        note_ack_path=False,
        progress_push_enabled=False,
    )


class TelegramBotDatasetV1Tests(unittest.TestCase):
    def test_dataset_v1_cases(self) -> None:
        cases = _load_cases()
        self.assertGreaterEqual(len(cases), 30)
        case_ids = [str(x.get("id", "")).strip() for x in cases]
        self.assertEqual(len(case_ids), len(set(case_ids)), msg="dataset case ids must be unique")
        for case in cases:
            with self.subTest(case=case.get("id")):
                with tempfile.TemporaryDirectory(prefix="ctcp_tg_dataset_v1_") as td:
                    base = Path(td)
                    cfg = _new_config(base)
                    bot = Bot(cfg)
                    fake = _FakeTg()
                    bot.tg = fake
                    try:
                        chat_id = 7001
                        session_lang = str(case.get("session_lang", "")).strip().lower()
                        if session_lang in {"zh", "en"}:
                            bot.db.set_lang(chat_id, session_lang)
                        if bool(case.get("prebind_run", False)):
                            run_dir = base / "run_demo"
                            run_dir.mkdir(parents=True, exist_ok=True)
                            (run_dir / "RUN.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")
                            bot.db.bind_run(chat_id, run_dir)
                            bot.db.set_lang(chat_id, session_lang or "zh")

                        text = str(case.get("text", "")).strip()
                        bot.process_update({"message": {"chat": {"id": chat_id}, "text": text}})
                        self.assertTrue(fake.messages, msg=f"no message for {case.get('id')}")
                        last_reply = fake.messages[-1]

                        expected = case.get("expect_reply_contains_any", [])
                        if isinstance(expected, list) and expected:
                            low = last_reply.lower()
                            self.assertTrue(
                                any(str(token).strip().lower() in low for token in expected if str(token).strip()),
                                msg=f"{case.get('id')} reply mismatch: {last_reply}",
                            )
                        expected_all = case.get("expect_reply_contains_all", [])
                        if isinstance(expected_all, list) and expected_all:
                            low = last_reply.lower()
                            for token in expected_all:
                                needle = str(token).strip().lower()
                                if not needle:
                                    continue
                                self.assertIn(needle, low, msg=f"{case.get('id')} missing token: {token}; reply={last_reply}")
                        expected_not = case.get("expect_reply_not_contains_any", [])
                        if isinstance(expected_not, list) and expected_not:
                            low = last_reply.lower()
                            for token in expected_not:
                                needle = str(token).strip().lower()
                                if not needle:
                                    continue
                                self.assertNotIn(needle, low, msg=f"{case.get('id')} should not contain: {token}; reply={last_reply}")

                        session = bot.db.get_session(chat_id)
                        run_bound = bool(str(session.get("run_dir", "")).strip())
                        self.assertEqual(run_bound, bool(case.get("expect_run_bound", False)), msg=f"{case.get('id')} run bind mismatch")
                    finally:
                        bot.close()
