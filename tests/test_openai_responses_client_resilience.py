#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
EXTERNALS_DIR = ROOT / "scripts" / "externals"
if str(EXTERNALS_DIR) not in sys.path:
    sys.path.insert(0, str(EXTERNALS_DIR))

import openai_responses_client as client


class _MockHttpResponse:
    def __init__(self, body: dict) -> None:
        self._payload = json.dumps(body, ensure_ascii=False).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_MockHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class OpenAiResponsesClientResilienceTests(unittest.TestCase):
    def test_retries_transient_transport_error(self) -> None:
        calls: list[str] = []

        def _urlopen(req, timeout=0):
            calls.append(str(req.full_url))
            if len(calls) == 1:
                raise urllib.error.URLError("unexpected eof")
            return _MockHttpResponse({"id": "resp_1", "output_text": "ok"})

        env = {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://example.test/v1",
            "SDDAI_OPENAI_ENDPOINT_MODE": "responses",
            "SDDAI_OPENAI_MAX_ATTEMPTS": "2",
            "SDDAI_OPENAI_RETRY_BASE_DELAY_SEC": "0",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch("openai_responses_client.urllib.request.urlopen", side_effect=_urlopen):
                text, err = client.call_openai_responses(prompt="hello", model="gpt-4.1-mini", timeout_sec=5)
        self.assertEqual(err, "")
        self.assertEqual(text, "ok")
        self.assertEqual(calls, ["https://example.test/v1/responses", "https://example.test/v1/responses"])

    def test_auto_falls_back_to_chat_completions(self) -> None:
        calls: list[str] = []

        def _urlopen(req, timeout=0):
            calls.append(str(req.full_url))
            if str(req.full_url).endswith("/responses"):
                raise urllib.error.HTTPError(
                    str(req.full_url),
                    404,
                    "not found",
                    hdrs=None,
                    fp=io.BytesIO(b'{"error":"missing endpoint"}'),
                )
            return _MockHttpResponse(
                {
                    "id": "chat_1",
                    "choices": [{"message": {"content": "chat-ok"}}],
                }
            )

        env = {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://example.test/v1",
            "SDDAI_OPENAI_ENDPOINT_MODE": "auto",
            "SDDAI_OPENAI_MAX_ATTEMPTS": "1",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch("openai_responses_client.urllib.request.urlopen", side_effect=_urlopen):
                text, err = client.call_openai_responses(prompt="hello", model="gpt-4.1-mini", timeout_sec=5)
        self.assertEqual(err, "")
        self.assertEqual(text, "chat-ok")
        self.assertEqual(calls, ["https://example.test/v1/responses", "https://example.test/v1/chat/completions"])

    def test_chat_mode_does_not_touch_responses_endpoint(self) -> None:
        calls: list[str] = []

        def _urlopen(req, timeout=0):
            calls.append(str(req.full_url))
            return _MockHttpResponse(
                {
                    "id": "chat_2",
                    "choices": [{"message": {"content": "chat-only"}}],
                }
            )

        env = {
            "OPENAI_API_KEY": "sk-test",
            "OPENAI_BASE_URL": "https://example.test/v1",
            "SDDAI_OPENAI_ENDPOINT_MODE": "chat",
            "SDDAI_OPENAI_MAX_ATTEMPTS": "1",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            with mock.patch("openai_responses_client.urllib.request.urlopen", side_effect=_urlopen):
                text, err = client.call_openai_responses(prompt="hello", model="gpt-4.1-mini", timeout_sec=5)
        self.assertEqual(err, "")
        self.assertEqual(text, "chat-only")
        self.assertEqual(calls, ["https://example.test/v1/chat/completions"])

    def test_loads_api_defaults_from_local_notes(self) -> None:
        calls: list[str] = []

        def _urlopen(req, timeout=0):
            calls.append(str(req.full_url))
            headers = {k.lower(): v for k, v in req.header_items()}
            self.assertEqual(headers.get("authorization"), "Bearer sk-notes")
            return _MockHttpResponse({"id": "resp_notes", "output_text": "notes-ok"})

        with tempfile.TemporaryDirectory() as td:
            notes = Path(td) / "NOTES.md"
            notes.write_text(
                "\n".join(
                    [
                        "Use this base URL:",
                        "- `https://notes.example/v1`",
                        "",
                        "Use this API key:",
                        "- `sk-notes`",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            env = {
                "OPENAI_API_KEY": "",
                "CTCP_OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
                "CTCP_LOCAL_NOTES_PATH": str(notes),
                "SDDAI_OPENAI_ENDPOINT_MODE": "responses",
                "SDDAI_OPENAI_MAX_ATTEMPTS": "1",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                with mock.patch("openai_responses_client.urllib.request.urlopen", side_effect=_urlopen):
                    text, err = client.call_openai_responses(prompt="hello", model="gpt-4.1-mini", timeout_sec=5)

        self.assertEqual(err, "")
        self.assertEqual(text, "notes-ok")
        self.assertEqual(calls, ["https://notes.example/v1/responses"])


if __name__ == "__main__":
    unittest.main()
