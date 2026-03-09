import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.telegram_cs_bot import Bot, Config


FIXTURE_DIR = Path("tests/fixtures/telegram_human_dialogue_sim_v1")
FIXTURE_PATH = FIXTURE_DIR / "cases.jsonl"
FORBIDDEN_MARKERS = (
    "diff --git",
    "trace.md",
    "logs/",
    "outbox/",
    "artifacts/",
    "run_dir",
    "stack trace",
)


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


def _load_cases() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


class TelegramHumanDialogueSimV1Tests(unittest.TestCase):
    def test_fixture_schema_and_coverage(self) -> None:
        cases = _load_cases()
        self.assertGreaterEqual(len(cases), 20)
        case_ids = [str(x.get("id", "")).strip() for x in cases]
        self.assertEqual(len(case_ids), len(set(case_ids)), msg="dialogue case ids must be unique")

        en_count = 0
        zh_count = 0
        for case in cases:
            cid = str(case.get("id", "")).strip()
            self.assertTrue(cid, msg="missing case id")
            turns = case.get("turns", [])
            self.assertIsInstance(turns, list, msg=f"{cid} turns must be a list")
            self.assertGreaterEqual(len(turns), 2, msg=f"{cid} requires at least 2 turns")
            for turn in turns:
                self.assertIsInstance(turn, str, msg=f"{cid} turn must be str")
                self.assertTrue(turn.strip(), msg=f"{cid} empty turn text")
            lang = str(case.get("lang", "")).strip().lower()
            if lang == "en":
                en_count += 1
            if lang == "zh":
                zh_count += 1
        self.assertGreaterEqual(en_count, 3, msg="expected at least 3 english simulated dialogues")
        self.assertGreaterEqual(zh_count, 10, msg="expected at least 10 chinese simulated dialogues")

    def test_dialogue_replay_human_hygiene(self) -> None:
        cases = _load_cases()
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_human_dialogue_sim_") as td:
            base = Path(td)
            cfg = _new_config(base)
            bot = Bot(cfg)
            fake = _FakeTg()
            bot.tg = fake
            try:
                for idx, case in enumerate(cases):
                    cid = str(case.get("id", f"case-{idx+1}")).strip()
                    turns = case.get("turns", [])
                    lang = str(case.get("lang", "zh")).strip().lower()
                    if lang not in {"zh", "en"}:
                        lang = "zh"
                    chat_id = 88000 + idx
                    bot.db.set_lang(chat_id, lang)

                    last_reply = ""
                    max_q = int(((case.get("expect") or {}).get("max_questions_per_reply", 2)))
                    for turn in turns:
                        user_text = str(turn).strip()
                        bot.process_update({"message": {"chat": {"id": chat_id}, "text": user_text}})
                        self.assertTrue(fake.messages, msg=f"{cid} no bot message emitted")
                        last_reply = str(fake.messages[-1]).strip()
                        self.assertTrue(last_reply, msg=f"{cid} empty reply")
                        low = last_reply.lower()
                        for marker in FORBIDDEN_MARKERS:
                            self.assertNotIn(marker, low, msg=f"{cid} leaked internal marker: {marker}")
                        q_count = last_reply.count("?") + last_reply.count("？")
                        self.assertLessEqual(q_count, max_q, msg=f"{cid} too many questions in one reply")

                    expect = case.get("expect", {}) if isinstance(case.get("expect"), dict) else {}
                    must_include = expect.get("final_contains_any", [])
                    if isinstance(must_include, list) and must_include:
                        low = last_reply.lower()
                        self.assertTrue(
                            any(str(token).strip().lower() in low for token in must_include if str(token).strip()),
                            msg=f"{cid} final reply missing expected hints",
                        )
            finally:
                bot.close()
