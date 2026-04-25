from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.module_protection import evaluate_module_protection

SCRIPT_PATH = ROOT / "scripts" / "module_protection_check.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("module_protection_check_for_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load scripts/module_protection_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True)


def _init_repo(base: Path) -> None:
    _run(["git", "init"], base)
    _run(["git", "config", "user.email", "test@example.com"], base)
    _run(["git", "config", "user.name", "ctcp-test"], base)


def _write_contract(repo: Path) -> None:
    _write(
        repo / "contracts" / "module_freeze.json",
        json.dumps(
            {
                "schema_version": "ctcp-module-freeze-v1",
                "frozen_kernels": ["AGENTS.md", "scripts/verify_repo.ps1"],
                "lane_owned": ["docs/10_team_mode.md", "scripts/ctcp_support_bot.py"],
                "task_writable_defaults": ["docs/", "tests/", "meta/tasks/"],
                "lane_regression_tests": ["python -m unittest discover -s tests -p \"test_support_to_production_path.py\" -v"],
                "frozen_kernel_regression_tests": ["python -m unittest discover -s tests -p \"test_prompt_contract_check.py\" -v"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    )


def _write_task_card(
    repo: Path,
    *,
    frozen: bool,
    elevation_required: bool,
    elevation_signal: str,
    allowed: list[str],
    protected: list[str],
) -> None:
    lines = [
        "# Task - test",
        "",
        "## Write Scope / Protection",
        "",
        "- Allowed Write Paths:",
        *[f"  - `{item}`" for item in allowed],
        "- Protected Paths:",
        *[f"  - `{item}`" for item in protected],
        f"- Frozen Kernels Touched: `{'true' if frozen else 'false'}`",
        f"- Explicit Elevation Required: `{'true' if elevation_required else 'false'}`",
        f"- Explicit Elevation Signal: `{elevation_signal}`",
        "- Forbidden Bypass:",
        "  - `compiled PROMPT.md must not override AGENTS.md`",
        "- Acceptance Checks:",
        "  - `python -m unittest discover -s tests -p \"test_prompt_contract_check.py\" -v`",
    ]
    _write(repo / "meta" / "tasks" / "CURRENT.md", "\n".join(lines) + "\n")


class ModuleProtectionContractTests(unittest.TestCase):
    def test_frozen_kernel_change_requires_explicit_elevation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_module_protection_frozen_") as td:
            repo = Path(td)
            _write_contract(repo)
            _write_task_card(
                repo,
                frozen=False,
                elevation_required=False,
                elevation_signal="none",
                allowed=["AGENTS.md", "meta/tasks/"],
                protected=["AGENTS.md"],
            )

            doc = evaluate_module_protection(repo, changed_files=["AGENTS.md"])
            self.assertEqual(str(doc.get("ownership", "")), "frozen-kernel")
            violations = "\n".join(list(doc.get("violations", [])))
            self.assertIn("Frozen Kernels Touched", violations)
            self.assertIn("Explicit Elevation Required", violations)
            self.assertIn("Explicit Elevation Signal", violations)

    def test_lane_owned_change_requests_lane_regression(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_module_protection_lane_") as td:
            repo = Path(td)
            _write_contract(repo)
            _write_task_card(
                repo,
                frozen=False,
                elevation_required=False,
                elevation_signal="none",
                allowed=["docs/10_team_mode.md", "meta/tasks/"],
                protected=["AGENTS.md"],
            )

            doc = evaluate_module_protection(repo, changed_files=["docs/10_team_mode.md"])
            self.assertEqual(str(doc.get("ownership", "")), "lane-owned")
            self.assertTrue(bool(doc.get("requires_lane_regression", False)))
            self.assertFalse(bool(doc.get("requires_frozen_regression", False)))
            self.assertEqual(list(doc.get("violations", [])), [])

    def test_path_outside_allowed_write_scope_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_module_protection_scope_") as td:
            repo = Path(td)
            _write_contract(repo)
            _write_task_card(
                repo,
                frozen=False,
                elevation_required=False,
                elevation_signal="none",
                allowed=["docs/10_team_mode.md", "meta/tasks/"],
                protected=["AGENTS.md"],
            )

            doc = evaluate_module_protection(repo, changed_files=["scripts/ctcp_support_bot.py"])
            self.assertIn("path outside CURRENT.md Allowed Write Paths", "\n".join(list(doc.get("violations", []))))

    def test_module_protection_script_reports_json_and_exit_code(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_module_protection_script_") as td:
            repo = Path(td)
            _init_repo(repo)
            _write_contract(repo)
            _write_task_card(
                repo,
                frozen=False,
                elevation_required=False,
                elevation_signal="none",
                allowed=["docs/10_team_mode.md", "meta/tasks/"],
                protected=["AGENTS.md"],
            )
            target = repo / "docs" / "10_team_mode.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("lane-owned change\n", encoding="utf-8")

            module = _load_script_module()
            stream = io.StringIO()
            with redirect_stdout(stream):
                rc = int(module.main(["--root", str(repo), "--json"]))
            out = stream.getvalue()
            self.assertEqual(rc, 0)
            doc = json.loads(out)
            self.assertEqual(str(doc.get("ownership", "")), "lane-owned")


if __name__ == "__main__":
    unittest.main()
