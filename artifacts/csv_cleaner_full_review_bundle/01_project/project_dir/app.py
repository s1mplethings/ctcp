from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / 'static'
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from csv_cleaner_web.service import CleaningOptions, clean_csv_text


def _json_bytes(doc: dict[str, object]) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


class CsvCleanerHandler(BaseHTTPRequestHandler):
    server_version = 'CsvCleanerHTTP/0.1'

    def _serve_file(self, relative_path: str, content_type: str) -> None:
        path = STATIC_DIR / relative_path
        if not path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == '/':
            self._serve_file('index.html', 'text/html; charset=utf-8')
            return
        if route == '/assets/app.css':
            self._serve_file('app.css', 'text/css; charset=utf-8')
            return
        if route == '/assets/app.js':
            self._serve_file('app.js', 'application/javascript; charset=utf-8')
            return
        if route == '/api/health':
            payload = _json_bytes({'status': 'ok', 'app': 'csv-cleaner-web-tool'})
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route != '/api/process':
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get('Content-Length', '0') or 0)
        payload = self.rfile.read(length)
        try:
            doc = json.loads(payload.decode('utf-8'))
        except Exception:
            self.send_error(HTTPStatus.BAD_REQUEST, 'invalid json')
            return
        csv_text = str(doc.get('csv_text', ''))
        keep_columns = [str(x) for x in doc.get('keep_columns', []) if str(x).strip()]
        result = clean_csv_text(
            csv_text,
            CleaningOptions(
                remove_empty_rows=bool(doc.get('remove_empty_rows', True)),
                remove_duplicates=bool(doc.get('remove_duplicates', True)),
                keep_columns=keep_columns or None,
            ),
        )
        body = _json_bytes(result.to_dict())
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = '127.0.0.1', port: int = 8008) -> None:
    server = ThreadingHTTPServer((host, port), CsvCleanerHandler)
    try:
        print(f'CSV Cleaner running at http://{host}:{port}', flush=True)
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == '__main__':
    run_server()
