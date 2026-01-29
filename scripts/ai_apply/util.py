from __future__ import annotations
import os
import json
import hashlib
from pathlib import Path

SKIP_DIRS = {".git", ".svn", ".hg", "build", "dist", ".idea", ".vscode", "__pycache__", ".cache"}

def iter_files(root: Path, max_files: int = 6000):
    n = 0
    for p in root.rglob("*"):
        if n >= max_files:
            break
        if p.is_dir():
            continue
        parts = set(p.parts)
        if parts & SKIP_DIRS:
            continue
        yield p
        n += 1

def read_text(path: Path, max_bytes: int = 2_000_000) -> str:
    try:
        data = path.read_bytes()
        if len(data) > max_bytes:
            data = data[:max_bytes]
        return data.decode("utf-8", errors="ignore")
    except Exception:
        return ""

def sha1_of_files(paths):
    h = hashlib.sha1()
    for p in sorted(paths):
        try:
            h.update(p.encode("utf-8"))
        except Exception:
            pass
    return h.hexdigest()

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
