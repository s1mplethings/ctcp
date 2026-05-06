from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import scripts.ctcp_support_bot as support_bot


class SupportBotTelegramRestartTests(unittest.TestCase):
    def test_run_telegram_mode_clears_local_history_and_pending_updates_on_startup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_support_telegram_clear_history_") as td:
            runs_root = Path(td) / "runs"
            stale_run_dir = runs_root / "ctcp" / "support_sessions" / "123"
            (stale_run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            state = support_bot.default_support_session_state("123")
            state["bound_run_id"] = "stale-run"
            (stale_run_dir / support_bot.SUPPORT_SESSION_STATE_REL_PATH).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            class _FakeTelegram:
                def __init__(self, token: str, timeout_sec: int) -> None:
                    del token, timeout_sec
                    self.drop_pending_updates: bool | None = None

                def clear_webhook(self, drop_pending_updates: bool = False) -> None:
                    self.drop_pending_updates = bool(drop_pending_updates)

                def get_updates(self, offset: int) -> list[dict[str, object]]:
                    del offset
                    raise KeyboardInterrupt()

            fake_holder: dict[str, _FakeTelegram] = {}

            def _fake_tg_factory(token: str, timeout_sec: int) -> _FakeTelegram:
                fake_holder["tg"] = _FakeTelegram(token, timeout_sec)
                return fake_holder["tg"]

            with mock.patch.object(support_bot, "TelegramClient", side_effect=_fake_tg_factory), mock.patch.object(
                support_bot, "get_runs_root", return_value=runs_root
            ), mock.patch.object(
                support_bot, "get_repo_slug", return_value="ctcp"
            ):
                with self.assertRaises(KeyboardInterrupt):
                    support_bot.run_telegram_mode(token="fake", poll_seconds=1, allowlist_raw="123")

            self.assertFalse(stale_run_dir.exists())
            self.assertTrue(fake_holder["tg"].drop_pending_updates)


if __name__ == "__main__":
    unittest.main()
