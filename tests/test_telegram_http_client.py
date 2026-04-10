from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from frontend import telegram_http_client as client


class TelegramHttpClientTests(unittest.TestCase):
    def test_post_form_falls_back_to_curl_when_urllib_transport_fails(self) -> None:
        completed = mock.Mock(returncode=0, stdout=json.dumps({"ok": True, "result": {"message_id": 1}}), stderr="")
        with mock.patch.object(client.urllib.request, "urlopen", side_effect=TimeoutError("read timed out")), mock.patch.object(client.shutil, "which", return_value="curl.exe"), mock.patch.object(client.subprocess, "run", return_value=completed) as run:
            result = client.telegram_post_form("https://api.telegram.org/botTOKEN", "sendMessage", {"chat_id": 1, "text": "hello"}, timeout_sec=1)
        self.assertEqual(dict(result).get("message_id"), 1)
        self.assertIn("--data-urlencode", list(run.call_args.args[0]))

    def test_post_multipart_falls_back_to_curl_when_urllib_transport_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_tg_http_") as td:
            path = Path(td) / "final-ui.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n")
            completed = mock.Mock(returncode=0, stdout=json.dumps({"ok": True, "result": {"photo": []}}), stderr="")
            with mock.patch.object(client.urllib.request, "urlopen", side_effect=TimeoutError("read timed out")), mock.patch.object(client.shutil, "which", return_value="curl.exe"), mock.patch.object(client.subprocess, "run", return_value=completed) as run:
                result = client.telegram_post_multipart("https://api.telegram.org/botTOKEN", "sendPhoto", {"chat_id": 1}, "photo", path, timeout_sec=1)
        self.assertIn("photo", dict(result))
        self.assertTrue(any(str(item).startswith("photo=@") for item in list(run.call_args.args[0])))


if __name__ == "__main__":
    unittest.main()
