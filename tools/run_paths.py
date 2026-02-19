#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

RUNS_ROOT_ENV = "CTCP_RUNS_ROOT"


def _default_runs_root() -> Path:
    if os.name == "nt":
        localapp = os.environ.get("LOCALAPPDATA", "").strip()
        if localapp:
            return Path(localapp) / "ctcp" / "runs"
        return Path.home() / "AppData" / "Local" / "ctcp" / "runs"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ctcp" / "runs"
    return Path.home() / ".local" / "share" / "ctcp" / "runs"


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-._")
    return text or "ctcp"


def get_repo_slug(root: Path) -> str:
    return _slugify(root.resolve().name)


def get_runs_root() -> Path:
    raw = os.environ.get(RUNS_ROOT_ENV, "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return _default_runs_root().resolve()


def get_repo_runs_root(root: Path) -> Path:
    return get_runs_root() / get_repo_slug(root)


def make_run_dir(root: Path, run_id: str) -> Path:
    return get_repo_runs_root(root) / run_id


def default_simlab_runs_root(root: Path) -> Path:
    return get_repo_runs_root(root) / "simlab_runs"
