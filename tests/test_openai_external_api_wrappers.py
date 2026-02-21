#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
PLAN_SCRIPT = ROOT / "scripts" / "externals" / "openai_plan_api.py"
PATCH_SCRIPT = ROOT / "scripts" / "externals" / "openai_patch_api.py"


class _ResponsesHandler(BaseHTTPRequestHandler):
    response_doc: dict = {"output_text": "ok"}
    requests_seen: list[dict] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8", errors="replace")
        self.__class__.requests_seen.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": payload,
            }
        )

        body = json.dumps(self.__class__.response_doc, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


class OpenAiExternalApiWrappersTests(unittest.TestCase):
    def _start_server(self, response_doc: dict) -> tuple[ThreadingHTTPServer, threading.Thread, str]:
        _ResponsesHandler.response_doc = response_doc
        _ResponsesHandler.requests_seen = []
        server = ThreadingHTTPServer(("127.0.0.1", 0), _ResponsesHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}/v1"
        return server, thread, base_url

    def _run_script(self, cmd: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

    def test_plan_wrapper_calls_openai_responses_api(self) -> None:
        response = {"output_text": "# PLAN\n- item: ok"}
        server, thread, base_url = self._start_server(response)
        try:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                context = tmp / "CONTEXT.md"
                constraints = tmp / "CONSTRAINTS.md"
                fix_brief = tmp / "FIX_BRIEF.md"
                for path in (context, constraints, fix_brief):
                    path.write_text("seed\n", encoding="utf-8")

                env = dict(os.environ)
                env["OPENAI_API_KEY"] = "sk-test"
                env["OPENAI_BASE_URL"] = base_url
                env["SDDAI_OPENAI_PLAN_MODEL"] = "gpt-4.1-mini"
                proc = self._run_script(
                    [
                        sys.executable,
                        str(PLAN_SCRIPT),
                        str(context),
                        str(constraints),
                        str(fix_brief),
                        "goal-x",
                        "1",
                        str(tmp),
                    ],
                    env,
                )
                self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr}")
                self.assertIn("# PLAN", proc.stdout)
                self.assertTrue(_ResponsesHandler.requests_seen)
                seen = _ResponsesHandler.requests_seen[0]
                self.assertEqual(seen["path"], "/v1/responses")
                self.assertEqual(seen["headers"].get("User-Agent"), "OpenAI/Python")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_patch_wrapper_parses_structured_output(self) -> None:
        response = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "\n".join(
                                [
                                    "diff --git a/docs/target.txt b/docs/target.txt",
                                    "--- a/docs/target.txt",
                                    "+++ b/docs/target.txt",
                                    "@@ -1 +1 @@",
                                    "-hello",
                                    "+hello patched",
                                ]
                            ),
                        }
                    ],
                }
            ]
        }
        server, thread, base_url = self._start_server(response)
        try:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                plan = tmp / "PLAN.md"
                context = tmp / "CONTEXT.md"
                constraints = tmp / "CONSTRAINTS.md"
                fix_brief = tmp / "FIX_BRIEF.md"
                for path in (plan, context, constraints, fix_brief):
                    path.write_text("seed\n", encoding="utf-8")

                env = dict(os.environ)
                env["OPENAI_API_KEY"] = "sk-test"
                env["OPENAI_BASE_URL"] = base_url
                env["SDDAI_OPENAI_PATCH_MODEL"] = "gpt-4.1-mini"
                proc = self._run_script(
                    [
                        sys.executable,
                        str(PATCH_SCRIPT),
                        str(plan),
                        str(context),
                        str(constraints),
                        str(fix_brief),
                        "goal-x",
                        "1",
                        str(tmp),
                    ],
                    env,
                )
                self.assertEqual(proc.returncode, 0, msg=f"stderr={proc.stderr}")
                self.assertTrue(proc.stdout.startswith("diff --git"))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_missing_api_key_fails_fast(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            context = tmp / "CONTEXT.md"
            constraints = tmp / "CONSTRAINTS.md"
            fix_brief = tmp / "FIX_BRIEF.md"
            for path in (context, constraints, fix_brief):
                path.write_text("seed\n", encoding="utf-8")

            env = dict(os.environ)
            env.pop("OPENAI_API_KEY", None)
            proc = self._run_script(
                [
                    sys.executable,
                    str(PLAN_SCRIPT),
                    str(context),
                    str(constraints),
                    str(fix_brief),
                    "goal-x",
                    "1",
                    str(tmp),
                ],
                env,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("OPENAI_API_KEY", proc.stderr)


if __name__ == "__main__":
    unittest.main()
