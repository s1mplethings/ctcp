from __future__ import annotations

import json
import re
from typing import Any


MEDIUM_CANDIDATE_PROJECTS: dict[str, dict[str, Any]] = {
    "live_provider_inventory_manager_app": {
        "keywords": (
            "live_provider_inventory_manager_app",
            "inventory manager app",
            "inventory manager",
            "low-stock",
            "stock movement",
        ),
        "required": ("live_provider_medium_candidate",),
        "startup": "app.py",
        "doc": "docs/inventory_manager_workflow.md",
        "business": [
            "README.md",
            "app.py",
            "inventory_store.py",
            "static/index.html",
            "static/app.js",
            "static/styles.css",
            "tests/test_inventory.py",
            "provenance.json",
        ],
        "description": "Live Provider Inventory Manager App",
        "task": (
            "Build a Python stdlib-only local full-stack inventory manager. Include SQLite persistence, "
            "app.py with --host and --port, inventory_store.py, static frontend files, and unittest tests. "
            "Endpoints: POST /products, GET /products, GET /products/{id}, PATCH /products/{id}, "
            "DELETE /products/{id}, POST /products/{id}/adjust, GET /low-stock, GET /movements."
        ),
    },
    "live_provider_knowledge_base_app": {
        "keywords": (
            "live_provider_knowledge_base_app",
            "knowledge base app",
            "knowledge base",
            "articles",
            "tags endpoint",
        ),
        "required": ("live_provider_medium_candidate",),
        "startup": "app.py",
        "doc": "docs/knowledge_base_workflow.md",
        "business": [
            "README.md",
            "app.py",
            "kb_store.py",
            "static/index.html",
            "static/app.js",
            "static/styles.css",
            "tests/test_knowledge_base.py",
            "provenance.json",
        ],
        "description": "Live Provider Knowledge Base App",
        "task": (
            "Build a Python stdlib-only local knowledge base app. Include persistence, app.py with --host "
            "and --port, kb_store.py, static frontend files, and unittest tests. Endpoints: POST /articles, "
            "GET /articles, GET /articles/{id}, PATCH /articles/{id}, DELETE /articles/{id}, "
            "GET /search?q=, GET /tags."
        ),
    },
    "live_provider_event_booking_app": {
        "keywords": (
            "live_provider_event_booking_app",
            "event booking app",
            "event booking",
            "availability endpoint",
        ),
        "required": ("live_provider_medium_candidate",),
        "startup": "app.py",
        "doc": "docs/event_booking_workflow.md",
        "business": [
            "README.md",
            "app.py",
            "event_store.py",
            "static/index.html",
            "static/app.js",
            "static/styles.css",
            "tests/test_event_booking.py",
            "provenance.json",
        ],
        "description": "Live Provider Event Booking App",
        "task": (
            "Build a Python stdlib-only local event booking app. Include SQLite persistence, app.py with "
            "--host and --port, event_store.py, static frontend files, and unittest tests. Endpoints: "
            "POST /events, GET /events, GET /events/{id}, PATCH /events/{id}, DELETE /events/{id}, "
            "POST /events/{id}/bookings, GET /events/{id}/bookings, GET /availability."
        ),
    },
    "live_provider_invoice_manager_app": {
        "keywords": (
            "live_provider_invoice_manager_app",
            "invoice manager app",
            "invoice manager",
            "invoice summary",
        ),
        "required": ("live_provider_medium_candidate",),
        "startup": "app.py",
        "doc": "docs/invoice_manager_workflow.md",
        "business": [
            "README.md",
            "app.py",
            "invoice_store.py",
            "static/index.html",
            "static/app.js",
            "static/styles.css",
            "tests/test_invoice_manager.py",
            "provenance.json",
        ],
        "description": "Live Provider Invoice Manager App",
        "task": (
            "Build a Python stdlib-only local invoice manager app. Include SQLite persistence, app.py with "
            "--host and --port, invoice_store.py, static frontend files, and unittest tests. Endpoints: "
            "POST /clients, GET /clients, POST /invoices, GET /invoices, GET /invoices/{id}, "
            "PATCH /invoices/{id}/status, POST /invoices/{id}/items, GET /summary."
        ),
    },
}

MEDIUM_FILE_CONTRACTS: dict[str, dict[str, Any]] = {
    "live_provider_inventory_manager_app": {
        "store_file": "inventory_store.py",
        "test_file": "tests/test_inventory.py",
        "routes": ["POST /products", "GET /products", "GET /products/{id}", "PATCH /products/{id}", "DELETE /products/{id}", "POST /products/{id}/adjust", "GET /low-stock", "GET /movements"],
        "store_methods": ["create_product", "list_products", "get_product", "update_product", "delete_product", "adjust_stock", "low_stock", "movements"],
        "frontend_fetch_paths": ["/products", "/products/{id}/adjust"],
    },
    "live_provider_knowledge_base_app": {
        "store_file": "kb_store.py",
        "test_file": "tests/test_knowledge_base.py",
        "routes": ["POST /articles", "GET /articles", "GET /articles/{id}", "PATCH /articles/{id}", "DELETE /articles/{id}", "GET /search?q=", "GET /tags"],
        "store_methods": ["create_article", "list_articles", "get_article", "update_article", "delete_article", "search", "tags"],
        "frontend_fetch_paths": ["/articles", "/search?q="],
    },
    "live_provider_event_booking_app": {
        "store_file": "event_store.py",
        "test_file": "tests/test_event_booking.py",
        "routes": ["POST /events", "GET /events", "GET /events/{id}", "PATCH /events/{id}", "DELETE /events/{id}", "POST /events/{id}/bookings", "GET /events/{id}/bookings", "GET /availability"],
        "store_methods": ["create_event", "list_events", "get_event", "update_event", "delete_event", "create_booking", "list_bookings", "availability"],
        "frontend_fetch_paths": ["/events", "/events/{id}/bookings", "/availability"],
    },
    "live_provider_invoice_manager_app": {
        "store_file": "invoice_store.py",
        "test_file": "tests/test_invoice_manager.py",
        "routes": ["POST /clients", "GET /clients", "POST /invoices", "GET /invoices", "GET /invoices/{id}", "PATCH /invoices/{id}/status", "POST /invoices/{id}/items", "GET /summary"],
        "store_methods": ["create_client", "list_clients", "create_invoice", "list_invoices", "get_invoice", "update_invoice_status", "add_invoice_item", "summary"],
        "frontend_fetch_paths": ["/clients", "/invoices", "/invoices/{id}/items", "/summary"],
    },
}


def _contract(project_id: str) -> dict[str, Any]:
    base = MEDIUM_FILE_CONTRACTS[project_id]
    required = [
        "README.md",
        "app.py",
        str(base["store_file"]),
        "static/index.html",
        "static/app.js",
        "static/styles.css",
        str(base["test_file"]),
    ]
    return {
        "case_name": project_id,
        "routes": list(base["routes"]),
        "store_methods": list(base["store_methods"]),
        "frontend_fetch_paths": list(base["frontend_fetch_paths"]),
        "test_commands": ["python -m unittest discover -v"],
        "required_files": required,
    }


def medium_project_contract(project_id: str) -> dict[str, Any]:
    return _contract(project_id)


_INVENTORY_FILES: dict[str, str] = {
    "README.md": (
        "# live_provider_inventory_manager_app\n\n"
        "Run: `python app.py --host 127.0.0.1 --port 8080`.\n\n"
        "The app stores products and stock movements in SQLite and serves a small static frontend.\n"
    ),
    "inventory_store.py": (
        "from __future__ import annotations\n\n"
        "import sqlite3\n"
        "from datetime import datetime, timezone\n"
        "from pathlib import Path\n\n"
        "def _now() -> str:\n"
        "    return datetime.now(timezone.utc).isoformat()\n\n"
        "def _row(row):\n"
        "    return dict(row) if row is not None else None\n\n"
        "class InventoryStore:\n"
        "    def __init__(self, db_path: str = 'inventory.db'):\n"
        "        self.db_path = db_path\n"
        "        if db_path != ':memory:':\n"
        "            Path(db_path).parent.mkdir(parents=True, exist_ok=True)\n"
        "        self.conn = sqlite3.connect(db_path, check_same_thread=False)\n"
        "        self.conn.row_factory = sqlite3.Row\n"
        "        self._init_schema()\n\n"
        "    def _init_schema(self) -> None:\n"
        "        self.conn.executescript('''\n"
        "        CREATE TABLE IF NOT EXISTS products (\n"
        "          id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "          sku TEXT UNIQUE NOT NULL,\n"
        "          name TEXT NOT NULL,\n"
        "          quantity INTEGER NOT NULL DEFAULT 0,\n"
        "          reorder_level INTEGER NOT NULL DEFAULT 0,\n"
        "          created_at TEXT NOT NULL,\n"
        "          updated_at TEXT NOT NULL\n"
        "        );\n"
        "        CREATE TABLE IF NOT EXISTS stock_movements (\n"
        "          id INTEGER PRIMARY KEY AUTOINCREMENT,\n"
        "          product_id INTEGER NOT NULL,\n"
        "          delta INTEGER NOT NULL,\n"
        "          reason TEXT NOT NULL,\n"
        "          created_at TEXT NOT NULL,\n"
        "          FOREIGN KEY(product_id) REFERENCES products(id)\n"
        "        );\n"
        "        ''')\n"
        "        self.conn.commit()\n\n"
        "    def create_product(self, data: dict) -> dict:\n"
        "        stamp = _now()\n"
        "        cur = self.conn.execute(\n"
        "            'INSERT INTO products (sku, name, quantity, reorder_level, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)',\n"
        "            (str(data.get('sku', '')).strip(), str(data.get('name', '')).strip(), int(data.get('quantity', 0)), int(data.get('reorder_level', 0)), stamp, stamp),\n"
        "        )\n"
        "        self.conn.commit()\n"
        "        return self.get_product(int(cur.lastrowid))\n\n"
        "    def list_products(self) -> list[dict]:\n"
        "        rows = self.conn.execute('SELECT * FROM products ORDER BY id').fetchall()\n"
        "        return [dict(row) for row in rows]\n\n"
        "    def get_product(self, product_id: int) -> dict | None:\n"
        "        return _row(self.conn.execute('SELECT * FROM products WHERE id=?', (int(product_id),)).fetchone())\n\n"
        "    def update_product(self, product_id: int, data: dict) -> dict | None:\n"
        "        current = self.get_product(product_id)\n"
        "        if not current:\n"
        "            return None\n"
        "        sku = str(data.get('sku', current['sku'])).strip()\n"
        "        name = str(data.get('name', current['name'])).strip()\n"
        "        quantity = int(data.get('quantity', current['quantity']))\n"
        "        reorder_level = int(data.get('reorder_level', current['reorder_level']))\n"
        "        self.conn.execute(\n"
        "            'UPDATE products SET sku=?, name=?, quantity=?, reorder_level=?, updated_at=? WHERE id=?',\n"
        "            (sku, name, quantity, reorder_level, _now(), int(product_id)),\n"
        "        )\n"
        "        self.conn.commit()\n"
        "        return self.get_product(product_id)\n\n"
        "    def delete_product(self, product_id: int) -> bool:\n"
        "        self.conn.execute('DELETE FROM stock_movements WHERE product_id=?', (int(product_id),))\n"
        "        cur = self.conn.execute('DELETE FROM products WHERE id=?', (int(product_id),))\n"
        "        self.conn.commit()\n"
        "        return cur.rowcount > 0\n\n"
        "    def adjust_stock(self, product_id: int, delta: int, reason: str = 'adjustment') -> dict | None:\n"
        "        product = self.get_product(product_id)\n"
        "        if not product:\n"
        "            return None\n"
        "        new_quantity = int(product['quantity']) + int(delta)\n"
        "        self.conn.execute('UPDATE products SET quantity=?, updated_at=? WHERE id=?', (new_quantity, _now(), int(product_id)))\n"
        "        self.conn.execute(\n"
        "            'INSERT INTO stock_movements (product_id, delta, reason, created_at) VALUES (?, ?, ?, ?)',\n"
        "            (int(product_id), int(delta), str(reason or 'adjustment'), _now()),\n"
        "        )\n"
        "        self.conn.commit()\n"
        "        return self.get_product(product_id)\n\n"
        "    def low_stock(self) -> list[dict]:\n"
        "        rows = self.conn.execute('SELECT * FROM products WHERE quantity <= reorder_level ORDER BY id').fetchall()\n"
        "        return [dict(row) for row in rows]\n\n"
        "    def movements(self) -> list[dict]:\n"
        "        rows = self.conn.execute('SELECT * FROM stock_movements ORDER BY id').fetchall()\n"
        "        return [dict(row) for row in rows]\n\n"
        "    def close(self) -> None:\n"
        "        self.conn.close()\n"
    ),
    "app.py": (
        "from __future__ import annotations\n\n"
        "import argparse\nimport json\nimport os\nfrom http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\nfrom pathlib import Path\n"
        "from inventory_store import InventoryStore\n\n"
        "STATIC = Path(__file__).parent / 'static'\n\n"
        "def _json(handler, status: int, payload):\n"
        "    data = json.dumps(payload).encode('utf-8')\n"
        "    handler.send_response(status); handler.send_header('Content-Type', 'application/json'); handler.send_header('Content-Length', str(len(data))); handler.end_headers(); handler.wfile.write(data)\n\n"
        "def _body(handler):\n"
        "    size = int(handler.headers.get('Content-Length', '0') or 0)\n"
        "    raw = handler.rfile.read(size).decode('utf-8') if size else '{}'\n"
        "    return json.loads(raw or '{}')\n\n"
        "def make_handler(store: InventoryStore):\n"
        "    class Handler(BaseHTTPRequestHandler):\n"
        "        def log_message(self, fmt, *args):\n"
        "            return\n"
        "        def do_GET(self):\n"
        "            path = self.path.split('?', 1)[0]\n"
        "            if path == '/':\n"
        "                return self._static('index.html')\n"
        "            if path.startswith('/static/'):\n"
        "                return self._static(path[len('/static/'):])\n"
        "            if path == '/products':\n"
        "                return _json(self, 200, {'products': store.list_products()})\n"
        "            if path.startswith('/products/'):\n"
        "                product = store.get_product(int(path.rsplit('/', 1)[-1]))\n"
        "                return _json(self, 200 if product else 404, product or {'error': 'not_found'})\n"
        "            if path == '/low-stock':\n"
        "                return _json(self, 200, {'products': store.low_stock()})\n"
        "            if path == '/movements':\n"
        "                return _json(self, 200, {'movements': store.movements()})\n"
        "            return _json(self, 404, {'error': 'not_found'})\n"
        "        def do_POST(self):\n"
        "            path = self.path.split('?', 1)[0]\n"
        "            if path == '/products':\n"
        "                return _json(self, 201, store.create_product(_body(self)))\n"
        "            if path.startswith('/products/') and path.endswith('/adjust'):\n"
        "                product_id = int(path.split('/')[2]); data = _body(self)\n"
        "                product = store.adjust_stock(product_id, int(data.get('delta', 0)), str(data.get('reason', 'adjustment')))\n"
        "                return _json(self, 200 if product else 404, product or {'error': 'not_found'})\n"
        "            return _json(self, 404, {'error': 'not_found'})\n"
        "        def do_PATCH(self):\n"
        "            path = self.path.split('?', 1)[0]\n"
        "            if path.startswith('/products/'):\n"
        "                product = store.update_product(int(path.rsplit('/', 1)[-1]), _body(self))\n"
        "                return _json(self, 200 if product else 404, product or {'error': 'not_found'})\n"
        "            return _json(self, 404, {'error': 'not_found'})\n"
        "        def do_DELETE(self):\n"
        "            path = self.path.split('?', 1)[0]\n"
        "            if path.startswith('/products/'):\n"
        "                ok = store.delete_product(int(path.rsplit('/', 1)[-1]))\n"
        "                return _json(self, 200 if ok else 404, {'deleted': ok})\n"
        "            return _json(self, 404, {'error': 'not_found'})\n"
        "        def _static(self, name):\n"
        "            target = (STATIC / name).resolve()\n"
        "            if STATIC.resolve() not in target.parents and target != STATIC.resolve():\n"
        "                return _json(self, 404, {'error': 'not_found'})\n"
        "            if not target.exists() or target.is_dir():\n"
        "                return _json(self, 404, {'error': 'not_found'})\n"
        "            data = target.read_bytes(); ctype = 'text/html' if target.suffix == '.html' else ('text/css' if target.suffix == '.css' else 'application/javascript')\n"
        "            self.send_response(200); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)\n"
        "    return Handler\n\n"
        "def main(argv=None):\n"
        "    p = argparse.ArgumentParser(); p.add_argument('--host', default='127.0.0.1'); p.add_argument('--port', type=int, default=8080); p.add_argument('--db', default=os.environ.get('INVENTORY_DB_PATH', 'inventory.db'))\n"
        "    args = p.parse_args(argv); store = InventoryStore(args.db); server = ThreadingHTTPServer((args.host, args.port), make_handler(store))\n"
        "    try: server.serve_forever()\n"
        "    finally: store.close(); server.server_close()\n"
        "if __name__ == '__main__': main()\n"
    ),
    "static/index.html": "<!doctype html><html><head><title>Inventory</title><link rel=\"stylesheet\" href=\"/static/styles.css\"></head><body><h1>Inventory Manager</h1><form id=\"product-form\"><input id=\"sku\" placeholder=\"SKU\"><input id=\"name\" placeholder=\"Name\"><input id=\"quantity\" type=\"number\" value=\"0\"><input id=\"reorder\" type=\"number\" value=\"0\"><button>Create</button></form><section id=\"products\"></section><script src=\"/static/app.js\"></script></body></html>\n",
    "static/app.js": (
        "async function api(path, options){ const res = await fetch(path, options); return res.json(); }\n"
        "async function load(){ const data = await api('/products'); document.getElementById('products').innerHTML = data.products.map(p => `<article><b>${p.sku}</b> ${p.name} qty ${p.quantity}<button data-id=\"${p.id}\">+1</button></article>`).join(''); }\n"
        "document.getElementById('product-form').addEventListener('submit', async e => { e.preventDefault(); await api('/products', {method:'POST', body: JSON.stringify({sku:sku.value,name:name.value,quantity:Number(quantity.value),reorder_level:Number(reorder.value)})}); await load(); });\n"
        "document.addEventListener('click', async e => { if(e.target.dataset.id){ await api(`/products/${e.target.dataset.id}/adjust`, {method:'POST', body: JSON.stringify({delta:1, reason:'frontend'})}); await load(); }});\n"
        "load();\n"
    ),
    "static/styles.css": "body{font-family:Arial,sans-serif;margin:2rem}article{border:1px solid #ccc;padding:.5rem;margin:.5rem 0}input,button{margin:.25rem}\n",
    "tests/__init__.py": "# unittest package marker\n",
    "tests/test_inventory.py": (
        "import unittest\nfrom inventory_store import InventoryStore\n\n"
        "class InventoryStoreTests(unittest.TestCase):\n"
        "    def test_product_flow(self):\n"
        "        store = InventoryStore(':memory:')\n"
        "        product = store.create_product({'sku': 'SKU1', 'name': 'Widget', 'quantity': 2, 'reorder_level': 3})\n"
        "        self.assertEqual(product['sku'], 'SKU1')\n"
        "        self.assertEqual(len(store.low_stock()), 1)\n"
        "        updated = store.adjust_stock(product['id'], 4, 'received')\n"
        "        self.assertEqual(updated['quantity'], 6)\n"
        "        self.assertEqual(len(store.movements()), 1)\n"
        "        store.close()\n"
        "if __name__ == '__main__': unittest.main()\n"
    ),
}


def _inventory_files() -> dict[str, str]:
    return dict(_INVENTORY_FILES)


def _knowledge_base_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_knowledge_base_app\n\nRun: `python app.py --host 127.0.0.1 --port 8080`.\n",
        "kb_store.py": (
            "from __future__ import annotations\n\n"
            "import sqlite3\nfrom datetime import datetime, timezone\nfrom pathlib import Path\n\n"
            "def _now() -> str:\n    return datetime.now(timezone.utc).isoformat()\n\n"
            "def _tags(value) -> str:\n    return ','.join([str(x).strip() for x in (value or []) if str(x).strip()]) if isinstance(value, list) else str(value or '')\n\n"
            "def _row(row):\n"
            "    if row is None: return None\n"
            "    out = dict(row); out['tags'] = [x for x in str(out.get('tags','')).split(',') if x]; return out\n\n"
            "class KnowledgeBaseStore:\n"
            "    def __init__(self, db_path: str = 'knowledge_base.db'):\n"
            "        self.db_path = db_path\n"
            "        if db_path != ':memory:': Path(db_path).parent.mkdir(parents=True, exist_ok=True)\n"
            "        self.conn = sqlite3.connect(db_path, check_same_thread=False); self.conn.row_factory = sqlite3.Row; self._init_schema()\n"
            "    def _init_schema(self):\n"
            "        self.conn.execute('CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, body TEXT NOT NULL, tags TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)'); self.conn.commit()\n"
            "    def create_article(self, data: dict) -> dict:\n"
            "        stamp = _now(); cur = self.conn.execute('INSERT INTO articles (title, body, tags, created_at, updated_at) VALUES (?, ?, ?, ?, ?)', (str(data.get('title','')).strip(), str(data.get('body','')), _tags(data.get('tags', [])), stamp, stamp)); self.conn.commit(); return self.get_article(int(cur.lastrowid))\n"
            "    def list_articles(self) -> list[dict]:\n"
            "        return [_row(row) for row in self.conn.execute('SELECT * FROM articles ORDER BY id').fetchall()]\n"
            "    def get_article(self, article_id: int) -> dict | None:\n"
            "        return _row(self.conn.execute('SELECT * FROM articles WHERE id=?', (int(article_id),)).fetchone())\n"
            "    def update_article(self, article_id: int, data: dict) -> dict | None:\n"
            "        current = self.get_article(article_id)\n"
            "        if not current: return None\n"
            "        self.conn.execute('UPDATE articles SET title=?, body=?, tags=?, updated_at=? WHERE id=?', (str(data.get('title', current['title'])), str(data.get('body', current['body'])), _tags(data.get('tags', current['tags'])), _now(), int(article_id))); self.conn.commit(); return self.get_article(article_id)\n"
            "    def delete_article(self, article_id: int) -> bool:\n"
            "        cur = self.conn.execute('DELETE FROM articles WHERE id=?', (int(article_id),)); self.conn.commit(); return cur.rowcount > 0\n"
            "    def search(self, query: str) -> list[dict]:\n"
            "        q = '%' + str(query or '').lower() + '%'; rows = self.conn.execute('SELECT * FROM articles WHERE lower(title) LIKE ? OR lower(body) LIKE ? OR lower(tags) LIKE ? ORDER BY id', (q, q, q)).fetchall(); return [_row(row) for row in rows]\n"
            "    def tags(self) -> list[str]:\n"
            "        values = set()\n"
            "        for row in self.conn.execute('SELECT tags FROM articles').fetchall():\n"
            "            values.update(x for x in str(row['tags']).split(',') if x)\n"
            "        return sorted(values)\n"
            "    def close(self): self.conn.close()\n"
        ),
        "app.py": (
            "from __future__ import annotations\n\n"
            "import argparse\nimport json\nimport os\nfrom http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\nfrom pathlib import Path\nfrom kb_store import KnowledgeBaseStore\n\n"
            "STATIC = Path(__file__).parent / 'static'\n\n"
            "def _json(handler, status, payload):\n"
            "    data = json.dumps(payload).encode('utf-8'); handler.send_response(status); handler.send_header('Content-Type','application/json'); handler.send_header('Content-Length', str(len(data))); handler.end_headers(); handler.wfile.write(data)\n"
            "def _body(handler):\n"
            "    size = int(handler.headers.get('Content-Length','0') or 0); raw = handler.rfile.read(size).decode('utf-8') if size else '{}'; return json.loads(raw or '{}')\n"
            "def _query(path):\n"
            "    if '?' not in path: return ''\n"
            "    for part in path.split('?',1)[1].split('&'):\n"
            "        if part.startswith('q='): return part[2:].replace('+',' ')\n"
            "    return ''\n"
            "def make_handler(store: KnowledgeBaseStore):\n"
            "    class Handler(BaseHTTPRequestHandler):\n"
            "        def log_message(self, fmt, *args): return\n"
            "        def do_GET(self):\n"
            "            path = self.path.split('?',1)[0]\n"
            "            if path == '/': return self._static('index.html')\n"
            "            if path.startswith('/static/'): return self._static(path[len('/static/'):])\n"
            "            if path == '/articles': return _json(self, 200, {'articles': store.list_articles()})\n"
            "            if path.startswith('/articles/'):\n"
            "                article = store.get_article(int(path.rsplit('/',1)[-1])); return _json(self, 200 if article else 404, article or {'error':'not_found'})\n"
            "            if path == '/search': return _json(self, 200, {'articles': store.search(_query(self.path))})\n"
            "            if path == '/tags': return _json(self, 200, {'tags': store.tags()})\n"
            "            return _json(self, 404, {'error':'not_found'})\n"
            "        def do_POST(self):\n"
            "            if self.path.split('?',1)[0] == '/articles': return _json(self, 201, store.create_article(_body(self)))\n"
            "            return _json(self, 404, {'error':'not_found'})\n"
            "        def do_PATCH(self):\n"
            "            path = self.path.split('?',1)[0]\n"
            "            if path.startswith('/articles/'):\n"
            "                article = store.update_article(int(path.rsplit('/',1)[-1]), _body(self)); return _json(self, 200 if article else 404, article or {'error':'not_found'})\n"
            "            return _json(self, 404, {'error':'not_found'})\n"
            "        def do_DELETE(self):\n"
            "            path = self.path.split('?',1)[0]\n"
            "            if path.startswith('/articles/'):\n"
            "                ok = store.delete_article(int(path.rsplit('/',1)[-1])); return _json(self, 200 if ok else 404, {'deleted': ok})\n"
            "            return _json(self, 404, {'error':'not_found'})\n"
            "        def _static(self, name):\n"
            "            target = (STATIC / name).resolve()\n"
            "            if STATIC.resolve() not in target.parents and target != STATIC.resolve(): return _json(self, 404, {'error':'not_found'})\n"
            "            if not target.exists() or target.is_dir(): return _json(self, 404, {'error':'not_found'})\n"
            "            data = target.read_bytes(); ctype = 'text/html' if target.suffix == '.html' else ('text/css' if target.suffix == '.css' else 'application/javascript')\n"
            "            self.send_response(200); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)\n"
            "    return Handler\n"
            "def main(argv=None):\n"
            "    p = argparse.ArgumentParser(); p.add_argument('--host', default='127.0.0.1'); p.add_argument('--port', type=int, default=8080); p.add_argument('--db', default=os.environ.get('KB_DB_PATH','knowledge_base.db'))\n"
            "    args = p.parse_args(argv); store = KnowledgeBaseStore(args.db); server = ThreadingHTTPServer((args.host, args.port), make_handler(store))\n"
            "    try: server.serve_forever()\n"
            "    finally: store.close(); server.server_close()\n"
            "if __name__ == '__main__': main()\n"
        ),
        "static/index.html": "<!doctype html><html><head><title>Knowledge Base</title><link rel=\"stylesheet\" href=\"/static/styles.css\"></head><body><h1>Knowledge Base</h1><form id=\"article-form\"><input id=\"title\" placeholder=\"Title\"><input id=\"tags\" placeholder=\"tags\"><textarea id=\"body\"></textarea><button>Create</button></form><input id=\"query\" placeholder=\"Search\"><button id=\"search\">Search</button><section id=\"articles\"></section><script src=\"/static/app.js\"></script></body></html>\n",
        "static/app.js": (
            "async function api(path, options){ const res = await fetch(path, options); return res.json(); }\n"
            "function render(rows){ articles.innerHTML = rows.map(a => `<article><h2>${a.title}</h2><p>${a.body}</p><small>${a.tags.join(', ')}</small></article>`).join(''); }\n"
            "async function load(){ const data = await api('/articles'); render(data.articles); }\n"
            "document.getElementById('article-form').addEventListener('submit', async e => { e.preventDefault(); await api('/articles', {method:'POST', body: JSON.stringify({title:title.value, body:body.value, tags:tags.value.split(',')})}); await load(); });\n"
            "document.getElementById('search').addEventListener('click', async () => { const data = await api('/search?q=' + query.value); render(data.articles); });\n"
            "load();\n"
        ),
        "static/styles.css": "body{font-family:Arial,sans-serif;margin:2rem}article{border:1px solid #ddd;padding:.75rem;margin:.5rem 0}textarea{display:block;width:30rem;height:6rem}\n",
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_knowledge_base.py": (
            "import unittest\nfrom kb_store import KnowledgeBaseStore\n\n"
            "class KnowledgeBaseStoreTests(unittest.TestCase):\n"
            "    def test_article_flow(self):\n"
            "        store = KnowledgeBaseStore(':memory:')\n"
            "        article = store.create_article({'title':'Install Guide','body':'Use local Python','tags':['docs','python']})\n"
            "        self.assertEqual(article['title'], 'Install Guide')\n"
            "        self.assertEqual(len(store.search('python')), 1)\n"
            "        self.assertIn('docs', store.tags())\n"
            "        updated = store.update_article(article['id'], {'body': 'Updated', 'tags': ['docs']})\n"
            "        self.assertEqual(updated['body'], 'Updated')\n"
            "        store.close()\n"
            "if __name__ == '__main__': unittest.main()\n"
        ),
    }


def _event_booking_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_event_booking_app\n\nRun: `python app.py --host 127.0.0.1 --port 8080`.\n",
        "event_store.py": r'''from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

def _now(): return datetime.now(timezone.utc).isoformat()
def _row(row): return dict(row) if row is not None else None

class EventStore:
    def __init__(self, db_path: str = 'events.db'):
        self.db_path = db_path
        if db_path != ':memory:': Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, date TEXT NOT NULL, capacity INTEGER NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY AUTOINCREMENT, event_id INTEGER NOT NULL, attendee_name TEXT NOT NULL, attendee_email TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(event_id) REFERENCES events(id));
        """)
        self.conn.commit()
    def create_event(self, data: dict) -> dict:
        stamp = _now()
        cur = self.conn.execute('INSERT INTO events (title,date,capacity,created_at,updated_at) VALUES (?,?,?,?,?)', (str(data.get('title','')).strip(), str(data.get('date','')).strip(), int(data.get('capacity', 0)), stamp, stamp))
        self.conn.commit(); return self.get_event(int(cur.lastrowid))
    def list_events(self) -> list[dict]:
        return [dict(row) for row in self.conn.execute('SELECT * FROM events ORDER BY id').fetchall()]
    def get_event(self, event_id: int) -> dict | None:
        return _row(self.conn.execute('SELECT * FROM events WHERE id=?', (int(event_id),)).fetchone())
    def update_event(self, event_id: int, data: dict) -> dict | None:
        cur = self.get_event(event_id)
        if not cur: return None
        self.conn.execute('UPDATE events SET title=?, date=?, capacity=?, updated_at=? WHERE id=?', (str(data.get('title', cur['title'])), str(data.get('date', cur['date'])), int(data.get('capacity', cur['capacity'])), _now(), int(event_id)))
        self.conn.commit(); return self.get_event(event_id)
    def delete_event(self, event_id: int) -> bool:
        self.conn.execute('DELETE FROM bookings WHERE event_id=?', (int(event_id),))
        cur = self.conn.execute('DELETE FROM events WHERE id=?', (int(event_id),))
        self.conn.commit(); return cur.rowcount > 0
    def create_booking(self, event_id: int, data: dict) -> dict:
        event = self.get_event(event_id)
        if not event: return {'error': 'not_found'}
        if len(self.list_bookings(event_id)) >= int(event['capacity']): return {'error': 'capacity_exceeded'}
        cur = self.conn.execute('INSERT INTO bookings (event_id,attendee_name,attendee_email,created_at) VALUES (?,?,?,?)', (int(event_id), str(data.get('attendee_name','')).strip(), str(data.get('attendee_email','')).strip(), _now()))
        self.conn.commit(); return dict(self.conn.execute('SELECT * FROM bookings WHERE id=?', (int(cur.lastrowid),)).fetchone())
    def list_bookings(self, event_id: int) -> list[dict]:
        return [dict(row) for row in self.conn.execute('SELECT * FROM bookings WHERE event_id=? ORDER BY id', (int(event_id),)).fetchall()]
    def availability(self) -> list[dict]:
        rows = []
        for event in self.list_events():
            booked = len(self.list_bookings(event['id']))
            rows.append({**event, 'booked': booked, 'remaining': int(event['capacity']) - booked})
        return rows
    def close(self): self.conn.close()
''',
        "app.py": r'''from __future__ import annotations
import argparse, json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from event_store import EventStore
STATIC = Path(__file__).parent / 'static'
def _json(h, status, payload):
    data=json.dumps(payload).encode('utf-8'); h.send_response(status); h.send_header('Content-Type','application/json'); h.send_header('Content-Length',str(len(data))); h.end_headers(); h.wfile.write(data)
def _body(h):
    raw=h.rfile.read(int(h.headers.get('Content-Length','0') or 0)).decode('utf-8') if h.headers.get('Content-Length') else '{}'; return json.loads(raw or '{}')
def make_handler(store: EventStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args): return
        def do_GET(self):
            path=self.path.split('?',1)[0]
            if path == '/': return self._static('index.html')
            if path.startswith('/static/'): return self._static(path[len('/static/'):])
            if path == '/events': return _json(self,200,{'events':store.list_events()})
            if path == '/availability': return _json(self,200,{'availability':store.availability()})
            if path.startswith('/events/') and path.endswith('/bookings'):
                return _json(self,200,{'bookings':store.list_bookings(int(path.split('/')[2]))})
            if path.startswith('/events/'):
                row=store.get_event(int(path.rsplit('/',1)[-1])); return _json(self,200 if row else 404,row or {'error':'not_found'})
            return _json(self,404,{'error':'not_found'})
        def do_POST(self):
            path=self.path.split('?',1)[0]
            if path == '/events': return _json(self,201,store.create_event(_body(self)))
            if path.startswith('/events/') and path.endswith('/bookings'):
                row=store.create_booking(int(path.split('/')[2]), _body(self)); return _json(self,409 if row.get('error') == 'capacity_exceeded' else (404 if row.get('error') else 201), row)
            return _json(self,404,{'error':'not_found'})
        def do_PATCH(self):
            path=self.path.split('?',1)[0]
            if path.startswith('/events/'):
                row=store.update_event(int(path.rsplit('/',1)[-1]), _body(self)); return _json(self,200 if row else 404,row or {'error':'not_found'})
            return _json(self,404,{'error':'not_found'})
        def do_DELETE(self):
            path=self.path.split('?',1)[0]
            if path.startswith('/events/'): return _json(self,200,{'deleted':store.delete_event(int(path.rsplit('/',1)[-1]))})
            return _json(self,404,{'error':'not_found'})
        def _static(self, name):
            target=(STATIC/name).resolve()
            if STATIC.resolve() not in target.parents and target != STATIC.resolve(): return _json(self,404,{'error':'not_found'})
            if not target.exists() or target.is_dir(): return _json(self,404,{'error':'not_found'})
            data=target.read_bytes(); c='text/html' if target.suffix=='.html' else ('text/css' if target.suffix=='.css' else 'application/javascript')
            self.send_response(200); self.send_header('Content-Type',c); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    return Handler
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8080); p.add_argument('--db',default=os.environ.get('EVENT_DB_PATH','events.db'))
    a=p.parse_args(argv); store=EventStore(a.db); server=ThreadingHTTPServer((a.host,a.port), make_handler(store))
    try: server.serve_forever()
    finally: store.close(); server.server_close()
if __name__ == '__main__': main()
''',
        "static/index.html": "<!doctype html><html><head><title>Event Booking</title><link rel=\"stylesheet\" href=\"/static/styles.css\"></head><body><h1>Event Booking</h1><form id=\"event-form\"><input id=\"title\" placeholder=\"Title\"><input id=\"date\" placeholder=\"Date\"><input id=\"capacity\" type=\"number\" value=\"2\"><button>Create</button></form><section id=\"events\"></section><script src=\"/static/app.js\"></script></body></html>\n",
        "static/app.js": "async function api(p,o){const r=await fetch(p,o);return r.json()}async function load(){const d=await api('/events');events.innerHTML=d.events.map(e=>`<article><b>${e.title}</b> ${e.date} cap ${e.capacity}<button data-id=\"${e.id}\">Book</button></article>`).join('')}eventForm=document.getElementById('event-form');eventForm.addEventListener('submit',async e=>{e.preventDefault();await api('/events',{method:'POST',body:JSON.stringify({title:title.value,date:date.value,capacity:Number(capacity.value)})});await load()});document.addEventListener('click',async e=>{if(e.target.dataset.id){await api(`/events/${e.target.dataset.id}/bookings`,{method:'POST',body:JSON.stringify({attendee_name:'Guest',attendee_email:'guest@example.test'})});await load()}});load();\n",
        "static/styles.css": "body{font-family:Arial,sans-serif;margin:2rem}article{border:1px solid #ccc;padding:.5rem;margin:.5rem 0}input,button{margin:.25rem}\n",
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_event_booking.py": "import unittest\nfrom event_store import EventStore\nclass EventStoreTests(unittest.TestCase):\n    def test_booking_flow(self):\n        s=EventStore(':memory:'); e=s.create_event({'title':'Demo','date':'2026-01-01','capacity':1}); self.assertEqual(len(s.list_events()),1); b=s.create_booking(e['id'],{'attendee_name':'A','attendee_email':'a@example.test'}); self.assertEqual(b['event_id'], e['id']); self.assertEqual(s.create_booking(e['id'],{'attendee_name':'B','attendee_email':'b@example.test'})['error'],'capacity_exceeded'); self.assertEqual(s.availability()[0]['remaining'],0); s.close()\nif __name__ == '__main__': unittest.main()\n",
    }


def _invoice_manager_files() -> dict[str, str]:
    return {
        "README.md": "# live_provider_invoice_manager_app\n\nRun: `python app.py --host 127.0.0.1 --port 8080`.\n",
        "invoice_store.py": r'''from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
def _now(): return datetime.now(timezone.utc).isoformat()
def _row(row): return dict(row) if row is not None else None
class InvoiceStore:
    def __init__(self, db_path: str = 'invoices.db'):
        self.db_path=db_path
        if db_path != ':memory:': Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn=sqlite3.connect(db_path, check_same_thread=False); self.conn.row_factory=sqlite3.Row
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, client_id INTEGER NOT NULL, number TEXT NOT NULL, status TEXT NOT NULL, subtotal REAL NOT NULL, tax REAL NOT NULL, total REAL NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS invoice_items (id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_id INTEGER NOT NULL, description TEXT NOT NULL, quantity REAL NOT NULL, unit_price REAL NOT NULL, line_total REAL NOT NULL);
        """); self.conn.commit()
    def create_client(self, data: dict) -> dict:
        cur=self.conn.execute('INSERT INTO clients (name,email,created_at) VALUES (?,?,?)',(str(data.get('name','')),str(data.get('email','')),_now())); self.conn.commit(); return _row(self.conn.execute('SELECT * FROM clients WHERE id=?',(cur.lastrowid,)).fetchone())
    def list_clients(self) -> list[dict]: return [dict(r) for r in self.conn.execute('SELECT * FROM clients ORDER BY id').fetchall()]
    def create_invoice(self, data: dict) -> dict:
        stamp=_now(); cur=self.conn.execute('INSERT INTO invoices (client_id,number,status,subtotal,tax,total,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',(int(data.get('client_id')),str(data.get('number','INV-1')),str(data.get('status','draft')),0.0,0.0,0.0,stamp,stamp)); self.conn.commit(); return self.get_invoice(int(cur.lastrowid))
    def list_invoices(self) -> list[dict]: return [self._invoice_with_items(r) for r in self.conn.execute('SELECT * FROM invoices ORDER BY id').fetchall()]
    def get_invoice(self, invoice_id: int) -> dict | None:
        row=self.conn.execute('SELECT * FROM invoices WHERE id=?',(int(invoice_id),)).fetchone(); return self._invoice_with_items(row) if row else None
    def _invoice_with_items(self, row) -> dict:
        out=dict(row); out['items']=[dict(r) for r in self.conn.execute('SELECT * FROM invoice_items WHERE invoice_id=? ORDER BY id',(out['id'],)).fetchall()]; return out
    def update_invoice_status(self, invoice_id: int, status: str) -> dict | None:
        if not self.get_invoice(invoice_id): return None
        self.conn.execute('UPDATE invoices SET status=?, updated_at=? WHERE id=?',(str(status),_now(),int(invoice_id))); self.conn.commit(); return self.get_invoice(invoice_id)
    def add_invoice_item(self, invoice_id: int, data: dict) -> dict | None:
        if not self.get_invoice(invoice_id): return None
        qty=float(data.get('quantity',1)); price=float(data.get('unit_price',0)); total=qty*price
        self.conn.execute('INSERT INTO invoice_items (invoice_id,description,quantity,unit_price,line_total) VALUES (?,?,?,?,?)',(int(invoice_id),str(data.get('description','')),qty,price,total)); self._recalc(invoice_id); self.conn.commit(); return self.get_invoice(invoice_id)
    def _recalc(self, invoice_id: int) -> None:
        subtotal=float(self.conn.execute('SELECT COALESCE(SUM(line_total),0) AS s FROM invoice_items WHERE invoice_id=?',(int(invoice_id),)).fetchone()['s']); tax=round(subtotal*0.1,2); self.conn.execute('UPDATE invoices SET subtotal=?, tax=?, total=?, updated_at=? WHERE id=?',(subtotal,tax,round(subtotal+tax,2),_now(),int(invoice_id)))
    def summary(self) -> dict:
        row=self.conn.execute('SELECT COUNT(*) AS count, COALESCE(SUM(total),0) AS total FROM invoices').fetchone(); return {'invoice_count': int(row['count']), 'total': float(row['total'])}
    def close(self): self.conn.close()
''',
        "app.py": r'''from __future__ import annotations
import argparse, json, os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from invoice_store import InvoiceStore
STATIC=Path(__file__).parent/'static'
def _json(h,s,p):
    d=json.dumps(p).encode('utf-8'); h.send_response(s); h.send_header('Content-Type','application/json'); h.send_header('Content-Length',str(len(d))); h.end_headers(); h.wfile.write(d)
def _body(h):
    raw=h.rfile.read(int(h.headers.get('Content-Length','0') or 0)).decode('utf-8') if h.headers.get('Content-Length') else '{}'; return json.loads(raw or '{}')
def make_handler(store: InvoiceStore):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args): return
        def do_GET(self):
            p=self.path.split('?',1)[0]
            if p == '/': return self._static('index.html')
            if p.startswith('/static/'): return self._static(p[len('/static/'):])
            if p == '/clients': return _json(self,200,{'clients':store.list_clients()})
            if p == '/invoices': return _json(self,200,{'invoices':store.list_invoices()})
            if p == '/summary': return _json(self,200,store.summary())
            if p.startswith('/invoices/'):
                row=store.get_invoice(int(p.rsplit('/',1)[-1])); return _json(self,200 if row else 404,row or {'error':'not_found'})
            return _json(self,404,{'error':'not_found'})
        def do_POST(self):
            p=self.path.split('?',1)[0]
            if p == '/clients': return _json(self,201,store.create_client(_body(self)))
            if p == '/invoices': return _json(self,201,store.create_invoice(_body(self)))
            if p.startswith('/invoices/') and p.endswith('/items'):
                row=store.add_invoice_item(int(p.split('/')[2]), _body(self)); return _json(self,200 if row else 404,row or {'error':'not_found'})
            return _json(self,404,{'error':'not_found'})
        def do_PATCH(self):
            p=self.path.split('?',1)[0]
            if p.startswith('/invoices/') and p.endswith('/status'):
                row=store.update_invoice_status(int(p.split('/')[2]), _body(self).get('status','draft')); return _json(self,200 if row else 404,row or {'error':'not_found'})
            return _json(self,404,{'error':'not_found'})
        def _static(self,name):
            t=(STATIC/name).resolve()
            if STATIC.resolve() not in t.parents and t != STATIC.resolve(): return _json(self,404,{'error':'not_found'})
            if not t.exists() or t.is_dir(): return _json(self,404,{'error':'not_found'})
            data=t.read_bytes(); c='text/html' if t.suffix=='.html' else ('text/css' if t.suffix=='.css' else 'application/javascript')
            self.send_response(200); self.send_header('Content-Type',c); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    return Handler
def main(argv=None):
    p=argparse.ArgumentParser(); p.add_argument('--host',default='127.0.0.1'); p.add_argument('--port',type=int,default=8080); p.add_argument('--db',default=os.environ.get('INVOICE_DB_PATH','invoices.db'))
    a=p.parse_args(argv); store=InvoiceStore(a.db); server=ThreadingHTTPServer((a.host,a.port), make_handler(store))
    try: server.serve_forever()
    finally: store.close(); server.server_close()
if __name__ == '__main__': main()
''',
        "static/index.html": "<!doctype html><html><head><title>Invoice Manager</title><link rel=\"stylesheet\" href=\"/static/styles.css\"></head><body><h1>Invoice Manager</h1><form id=\"client-form\"><input id=\"name\" placeholder=\"Client\"><input id=\"email\" placeholder=\"Email\"><button>Create client</button></form><section id=\"invoices\"></section><script src=\"/static/app.js\"></script></body></html>\n",
        "static/app.js": "async function api(p,o){const r=await fetch(p,o);return r.json()}async function load(){const d=await api('/invoices');invoices.innerHTML=d.invoices.map(i=>`<article>${i.number} ${i.status} $${i.total}</article>`).join('')}clientForm=document.getElementById('client-form');clientForm.addEventListener('submit',async e=>{e.preventDefault();const c=await api('/clients',{method:'POST',body:JSON.stringify({name:name.value,email:email.value})});await api('/invoices',{method:'POST',body:JSON.stringify({client_id:c.id,number:'INV-'+c.id})});await load()});load();\n",
        "static/styles.css": "body{font-family:Arial,sans-serif;margin:2rem}article{border:1px solid #ccc;padding:.5rem;margin:.5rem 0}input,button{margin:.25rem}\n",
        "tests/__init__.py": "# unittest package marker\n",
        "tests/test_invoice_manager.py": "import unittest\nfrom invoice_store import InvoiceStore\nclass InvoiceStoreTests(unittest.TestCase):\n    def test_invoice_flow(self):\n        s=InvoiceStore(':memory:'); c=s.create_client({'name':'Acme','email':'a@example.test'}); inv=s.create_invoice({'client_id':c['id'],'number':'INV-1'}); inv=s.add_invoice_item(inv['id'],{'description':'Work','quantity':2,'unit_price':50}); self.assertEqual(inv['subtotal'],100.0); self.assertEqual(inv['total'],110.0); inv=s.update_invoice_status(inv['id'],'sent'); self.assertEqual(inv['status'],'sent'); self.assertEqual(s.summary()['invoice_count'],1); s.close()\nif __name__ == '__main__': unittest.main()\n",
    }


def medium_candidate_files(project_id: str) -> dict[str, str]:
    builders = {
        "live_provider_inventory_manager_app": _inventory_files,
        "live_provider_knowledge_base_app": _knowledge_base_files,
        "live_provider_event_booking_app": _event_booking_files,
        "live_provider_invoice_manager_app": _invoice_manager_files,
    }
    return builders[project_id]()


def medium_required_files(project_id: str) -> set[str]:
    return set(_contract(project_id)["required_files"])


def medium_file_batches(project_id: str) -> list[list[str]]:
    store_file = str(MEDIUM_FILE_CONTRACTS[project_id]["store_file"])
    test_file = str(MEDIUM_FILE_CONTRACTS[project_id]["test_file"])
    return [
        ["README.md", "app.py", store_file],
        ["static/index.html", "static/app.js", "static/styles.css"],
        [test_file],
    ]


def extract_json_object(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        doc = json.loads(raw)
        return doc if isinstance(doc, dict) else {}
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {}
    try:
        doc = json.loads(match.group(0))
    except Exception:
        return {}
    return doc if isinstance(doc, dict) else {}


def medium_plan_prompt(project_id: str, goal_text: str) -> str:
    spec = MEDIUM_CANDIDATE_PROJECTS[project_id]
    files = ", ".join(sorted(medium_required_files(project_id)))
    return (
        "Return strict JSON only. No markdown fences.\n"
        "Stage 1: create a plan for a bounded local Python stdlib full-stack app. Do not write code in this response.\n"
        f"Project id: {project_id}\n"
        f"Required files: {files}\n"
        f"Task: {spec['task']}\n"
        f"User goal: {str(goal_text or '')[:1000]}\n"
        "The plan must cover API routes, frontend features, SQLite persistence, generated unittest tests, and file_manifest.\n"
        "Schema: {\"project_name\":\"...\",\"project_type\":\"fullstack_local_app\",\"architecture\":\"...\","
        "\"data_model\":[],\"api_routes\":[],\"frontend_features\":[],\"test_plan\":[],\"file_manifest\":[\"README.md\"]}\n"
    )


def normalize_medium_plan(project_id: str, doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    required = medium_required_files(project_id)
    manifest_raw = doc.get("file_manifest", [])
    if not isinstance(manifest_raw, list) and isinstance(doc.get("files"), list):
        manifest_raw = doc.get("files", [])
    manifest: list[str] = []
    if isinstance(manifest_raw, list):
        for item in manifest_raw:
            if isinstance(item, dict):
                value = item.get("path", item.get("file", item.get("name", "")))
            else:
                value = item
            rel = str(value).replace("\\", "/").strip().lstrip("/")
            if rel:
                manifest.append(rel)
    missing = sorted(required - set(manifest))
    unsafe = [item for item in manifest if not item or item.startswith("/") or ".." in item.split("/") or re.match(r"^[A-Za-z]:", item)]
    valid = bool(
        isinstance(doc, dict)
        and (str(doc.get("project_name", "")).strip() or str(doc.get("name", "")).strip())
        and (str(doc.get("project_type", "")).strip() or str(doc.get("type", "")).strip())
        and isinstance(doc.get("api_routes", doc.get("routes", [])), list)
        and isinstance(doc.get("frontend_features", doc.get("frontend", [])), list)
        and isinstance(doc.get("test_plan", doc.get("tests", [])), list)
        and not missing
        and not unsafe
    )
    plan = dict(doc)
    plan["file_manifest"] = manifest
    return plan, {
        "provider_plan_valid": valid,
        "provider_manifest_valid": not missing and not unsafe and bool(manifest),
        "provider_manifest_file_count": len(manifest),
        "missing_manifest_files": missing,
        "unsafe_manifest_files": unsafe,
    }


def medium_batch_prompt(
    *,
    project_id: str,
    goal_text: str,
    plan: dict[str, Any],
    allowed_files: list[str],
    feedback: str = "",
) -> str:
    spec = MEDIUM_CANDIDATE_PROJECTS[project_id]
    contract = _contract(project_id)
    details = (
        f"Implement store methods: {', '.join(contract['store_methods'])}. "
        f"HTTP app must serve: {', '.join(contract['routes'])}. "
        f"Frontend fetch paths should include: {', '.join(contract['frontend_fetch_paths'])}."
    )
    return (
        "Return strict JSON only. No markdown fences.\n"
        "Stage 3: generate only the requested files for this batch. Do not include other files.\n"
        "Use Python stdlib only. Do not import requests, urllib, subprocess, socket, eval, exec, or os.system.\n"
        "Tests must use unittest and should exercise store classes directly, not external HTTP clients.\n"
        f"Project id: {project_id}\n"
        f"Allowed files for this batch: {', '.join(allowed_files)}\n"
        f"Overall task: {spec['task']}\n"
        f"Implementation contract: {details}\n"
        f"Plan: {json.dumps(plan, ensure_ascii=False)[:1800]}\n"
        f"User goal: {str(goal_text or '')[:800]}\n"
        f"{feedback}\n"
        "Schema: {\"files\":[{\"path\":\"README.md\",\"content\":\"...\"}]}\n"
    )


def normalize_medium_batch(project_id: str, doc: dict[str, Any], allowed_files: list[str]) -> tuple[dict[str, str], list[str]]:
    allowed = {str(item).replace("\\", "/").strip().lstrip("/") for item in allowed_files}
    rows = doc.get("files")
    errors: list[str] = []
    files: dict[str, str] = {}
    if not isinstance(rows, list):
        return {}, ["missing_files_array"]
    for row in rows:
        if not isinstance(row, dict):
            errors.append("non_object_file")
            continue
        rel = str(row.get("path", "")).replace("\\", "/").strip().lstrip("/")
        content = str(row.get("content", ""))
        if rel not in allowed:
            errors.append(f"disallowed_path:{rel}")
            continue
        if not content.strip():
            errors.append(f"empty_file:{rel}")
            continue
        files[rel] = content.rstrip() + "\n"
    missing = sorted(allowed - set(files))
    errors.extend(f"missing_batch_file:{rel}" for rel in missing)
    return files, errors

