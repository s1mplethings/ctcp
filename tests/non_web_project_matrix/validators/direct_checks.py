from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from tools.providers.project_generation_artifacts import normalize_output_contract_freeze
from tools.providers.project_generation_business_materializers import materialize_business_files


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests" / "non_web_project_matrix" / "fixtures"
FIXTURE_BY_PROJECT = {
    "csv_expense_analyzer": "csv_expense_analyzer.json",
    "log_analyzer_cli": "log_analyzer.json",
    "text_utils_package": "text_utils_package.json",
    "terminal_quiz_game": "terminal_quiz_game.json",
}


def goal_for(project: str) -> str:
    fixture = json.loads((FIXTURES / FIXTURE_BY_PROJECT[project]).read_text(encoding="utf-8"))
    return str(fixture["goal"])


def materialize_non_web_project(project: str) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, Any]]:
    temp = tempfile.TemporaryDirectory(prefix=f"ctcp_{project}_")
    run_dir = Path(temp.name)
    goal = goal_for(project)
    contract = normalize_output_contract_freeze(None, goal=goal, run_dir=run_dir)
    materialize_business_files(run_dir, goal, contract, [f"{project} fixture"])
    return temp, run_dir / str(contract["project_root"]), contract


def project_env(project_dir: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(project_dir) if not existing else str(project_dir) + os.pathsep + existing
    return env


def run_project_tests(project_dir: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-v"],
        cwd=project_dir,
        env=project_env(project_dir),
        capture_output=True,
        text=True,
        timeout=90,
    )
