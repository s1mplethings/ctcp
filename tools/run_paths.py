#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path

RUNS_ROOT_ENV = "CTCP_RUNS_ROOT"
DEFAULT_RUNS_ROOT = Path.home() / ".ctcp" / "runs"


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
    return DEFAULT_RUNS_ROOT.resolve()


def get_repo_runs_root(root: Path) -> Path:
    return get_runs_root() / get_repo_slug(root)


def make_run_dir(root: Path, run_id: str) -> Path:
    return get_repo_runs_root(root) / run_id


def default_simlab_runs_root(root: Path) -> Path:
    return get_repo_runs_root(root) / "simlab_runs"
