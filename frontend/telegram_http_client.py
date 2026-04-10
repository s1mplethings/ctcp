from __future__ import annotations

import json
import mimetypes
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def _parse_result(payload: str) -> Any:
    doc = json.loads(payload)
    if not isinstance(doc, dict) or not bool(doc.get("ok")):
        raise RuntimeError(f"telegram api error: {payload}")
    return doc.get("result")


def _http_error(exc: urllib.error.HTTPError) -> RuntimeError:
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    return RuntimeError(f"telegram api http {exc.code}: {body or str(exc)}")


def _curl_binary() -> str:
    path = shutil.which("curl.exe") or shutil.which("curl")
    if not path:
        raise RuntimeError("telegram api fallback unavailable: curl not found")
    return path


def _run_curl(args: list[str], *, original_error: Exception) -> Any:
    proc = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or str(original_error)).strip()
        raise RuntimeError(f"telegram api curl fallback failed: {detail}") from original_error
    return _parse_result(proc.stdout)


def telegram_post_form(base: str, method: str, params: dict[str, Any], *, timeout_sec: int) -> Any:
    url = f"{base}/{method}"
    data = urllib.parse.urlencode({k: str(v) for k, v in params.items()}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=max(1, timeout_sec)) as resp:
            return _parse_result(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from exc
    except Exception as exc:
        args = [_curl_binary(), "-sS", "--max-time", str(max(1, timeout_sec)), "-X", "POST", url]
        for key, value in params.items():
            args.extend(["--data-urlencode", f"{key}={value}"])
        return _run_curl(args, original_error=exc)


def telegram_post_multipart(base: str, method: str, params: dict[str, Any], file_field: str, file_path: Path, *, timeout_sec: int) -> Any:
    url = f"{base}/{method}"
    boundary = f"ctcp-{uuid.uuid4().hex}"
    body = bytearray()
    for key, value in params.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode("utf-8"))
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode("utf-8"))
    body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
    req = urllib.request.Request(url, data=bytes(body), method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req, timeout=max(1, timeout_sec)) as resp:
            return _parse_result(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        raise _http_error(exc) from exc
    except Exception as exc:
        args = [_curl_binary(), "-sS", "--max-time", str(max(1, timeout_sec)), "-X", "POST", url]
        for key, value in params.items():
            args.extend(["--form-string", f"{key}={value}"])
        args.extend(["-F", f"{file_field}=@{file_path};filename={file_path.name}"])
        return _run_curl(args, original_error=exc)
