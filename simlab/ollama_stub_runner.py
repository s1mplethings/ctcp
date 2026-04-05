#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAST_RUN_POINTER = ROOT / "meta" / "run_pointers" / "LAST_RUN.txt"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import ctcp_librarian  # type: ignore  # noqa: E402


def _resolve_run_dir(raw: str) -> Path:
    if str(raw or "").strip():
        return Path(raw).expanduser().resolve()
    if not LAST_RUN_POINTER.exists():
        raise SystemExit("[ollama_stub_runner] missing LAST_RUN pointer; pass --run-dir")
    pointed = LAST_RUN_POINTER.read_text(encoding="utf-8").strip()
    if not pointed:
        raise SystemExit("[ollama_stub_runner] LAST_RUN pointer is empty; pass --run-dir")
    return Path(pointed).expanduser().resolve()


class _Handler(BaseHTTPRequestHandler):
    run_dir: Path = ROOT
    model_name = "simlab-librarian-stub"

    def _send_json(self, doc: dict[str, object], status: int = 200) -> None:
        body = json.dumps(doc, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "/api/tags":
            self._send_json({"models": [{"name": self.__class__.model_name}]})
            return
        self._send_json({"error": "not_found"}, status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/api/chat":
            self._send_json({"error": "not_found"}, status=404)
            return
        request_path = self.__class__.run_dir / "artifacts" / "file_request.json"
        if not request_path.exists():
            self._send_json({"error": f"missing file_request.json: {request_path}"}, status=500)
            return
        try:
            file_request = ctcp_librarian._read_json(request_path)
            context_pack = ctcp_librarian._build_context_pack(file_request)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)
            return
        self._send_json(
            {
                "model": self.__class__.model_name,
                "message": {
                    "role": "assistant",
                    "content": json.dumps(context_pack, ensure_ascii=False, indent=2),
                },
                "done": True,
            }
        )

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> int:
    ap = argparse.ArgumentParser(description="Run a shell command behind a local Ollama-compatible stub.")
    ap.add_argument("--run-dir", default="")
    ap.add_argument("--model", default="simlab-librarian-stub")
    ap.add_argument("--shell-command", required=True)
    args = ap.parse_args()

    run_dir = _resolve_run_dir(args.run_dir)
    _Handler.run_dir = run_dir
    _Handler.model_name = str(args.model or "simlab-librarian-stub").strip() or "simlab-librarian-stub"
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}/v1"
    env = dict(os.environ)
    env["LIBRARIAN_BASE_URL"] = base_url
    env["LIBRARIAN_MODEL"] = _Handler.model_name
    env["LIBRARIAN_API_KEY"] = "ollama"
    env["CTCP_OLLAMA_AUTO_START"] = "0"
    try:
        proc = subprocess.run(
            str(args.shell_command),
            cwd=str(ROOT),
            env=env,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        return int(proc.returncode)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
