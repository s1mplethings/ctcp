from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.providers.project_generation_live_full_candidate import (
    normalize_candidate_manifest,
    safety_scan,
    syntax_validation,
    validate_candidate_runtime,
)


def manifest_validation(project_id: str, doc: dict[str, Any]) -> dict[str, Any]:
    _files, validation = normalize_candidate_manifest(project_id, doc)
    return validation


def candidate_safety_validation(files: dict[str, str]) -> dict[str, Any]:
    return safety_scan(files)


def candidate_python_validation(files: dict[str, str]) -> dict[str, Any]:
    return syntax_validation(files)


def candidate_runtime_validation(project_id: str, files: dict[str, str]) -> dict[str, Any]:
    return validate_candidate_runtime(project_id, files)


def run_generated_tests(project_dir: Path, timeout: int = 45) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-v"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return {"exit_code": proc.returncode, "stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]}
    except subprocess.TimeoutExpired as exc:
        return {"exit_code": 124, "stdout": str(exc.stdout or "")[-2000:], "stderr": str(exc.stderr or "")[-2000:]}


def parse_json_output(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}
