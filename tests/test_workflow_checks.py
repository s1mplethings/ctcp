#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "workflow_checks.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("workflow_checks_for_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load scripts/workflow_checks.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_required_files(repo: Path, *, code_allowed: bool) -> None:
    (repo / "ai_context" / "templates" / "aidoc").mkdir(parents=True, exist_ok=True)
    (repo / "meta" / "tasks").mkdir(parents=True, exist_ok=True)
    (repo / "meta" / "reports").mkdir(parents=True, exist_ok=True)
    (repo / "ai_context" / "00_AI_CONTRACT.md").write_text("contract\n", encoding="utf-8")
    flag = "[x]" if code_allowed else "[ ]"
    (repo / "meta" / "tasks" / "CURRENT.md").write_text(
        f"# Task\n\n## Acceptance\n- {flag} Code changes allowed\n",
        encoding="utf-8",
    )
    (repo / "meta" / "reports" / "LAST.md").write_text("# report\n", encoding="utf-8")


def _configure_module(module, repo: Path) -> None:
    module.ROOT = repo
    module.TASK_CURRENT = repo / "meta" / "tasks" / "CURRENT.md"
    module.AI_CONTRACT = repo / "ai_context" / "00_AI_CONTRACT.md"
    module.AIDOC_TPL_DIR = repo / "ai_context" / "templates" / "aidoc"


def _set_changed_files(module, files: list[str]) -> None:
    def _fake_run_git(args: list[str]) -> str:
        key = " ".join(args)
        if key == "diff --name-only":
            return "\n".join(files) + ("\n" if files else "")
        if key == "diff --cached --name-only":
            return ""
        return ""

    module._run_git = _fake_run_git


def _run_main(module) -> tuple[int, str]:
    stream = io.StringIO()
    with redirect_stdout(stream):
        rc = int(module.main())
    return rc, stream.getvalue()


class WorkflowChecksTests(unittest.TestCase):
    def test_code_changes_require_doc_spec_first_change(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _write_required_files(repo, code_allowed=True)

            module = _load_module()
            _configure_module(module, repo)
            _set_changed_files(
                module,
                [
                    "src/main.cpp",
                    "meta/reports/LAST.md",
                ],
            )

            rc, out = _run_main(module)
            self.assertNotEqual(rc, 0)
            self.assertIn("docs/spec-first update", out)

    def test_code_changes_pass_with_doc_spec_first_change(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            _write_required_files(repo, code_allowed=True)

            module = _load_module()
            _configure_module(module, repo)
            _set_changed_files(
                module,
                [
                    "src/main.cpp",
                    "docs/00_overview.md",
                    "meta/reports/LAST.md",
                ],
            )

            rc, out = _run_main(module)
            self.assertEqual(rc, 0)
            self.assertIn("[workflow_checks] ok", out)


if __name__ == "__main__":
    unittest.main()
