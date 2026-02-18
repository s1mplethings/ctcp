#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


def ensure_includes(text: str, includes: list[str]) -> tuple[bool, str]:
    for needle in includes:
        if needle not in text:
            return False, f"missing expected text: {needle}"
    return True, "ok"


def ensure_excludes(text: str, excludes: list[str]) -> tuple[bool, str]:
    for needle in excludes:
        if needle in text:
            return False, f"unexpected text found: {needle}"
    return True, "ok"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

