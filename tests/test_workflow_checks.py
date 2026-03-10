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
        "\n".join(
            [
                "# Task",
                "",
                "## Analysis / Find",
                "- baseline checks complete",
                "",
                "## Integration Check",
                "upstream: test entry",
                "current_module: scripts/workflow_checks.py",
                "downstream: verify gate",
                "source_of_truth: meta/tasks/CURRENT.md",
                "fallback: stop with explicit error",
                "acceptance_test: tests/test_workflow_checks.py",
                "forbidden_bypass: skip CURRENT.md update",
                "user_visible_effect: verify gate blocks invalid workflow changes",
                "",
                "## Plan",
                "- check / contrast / fix loop",
                "- connected + accumulated + consumed",
                "- issue memory decision: keep explicit records",
                "- skillized: yes",
                "",
                "## Acceptance",
                f"- {flag} Code changes allowed",
                "",
                "task_purpose: validate workflow checks gate behavior",
                "allowed_behavior_change: tests and fixture expectations only",
                "forbidden_goal_shift: no runtime logic change",
                "in_scope_modules: scripts/workflow_checks.py, tests/test_workflow_checks.py",
                "out_of_scope_modules: tools/, frontend/",
                "completion_evidence: unit tests pass for workflow checks gate",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (repo / "meta" / "reports" / "LAST.md").write_text(
        "\n".join(
            [
                "# report",
                "",
                "### Readlist",
                "- scripts/workflow_checks.py",
                "",
                "### Plan",
                "- verify first failure and apply minimal fix strategy",
                "",
                "### Verify",
                "- first failure point captured",
                "- minimal fix strategy captured",
                "- python -m unittest tests/test_runtime_wiring_contract.py",
                "- python -m unittest tests/test_issue_memory_accumulation_contract.py",
                "- python -m unittest tests/test_skill_consumption_contract.py",
                "",
                "### Demo",
                "- workflow evidence recorded",
                "",
            ]
        ),
        encoding="utf-8",
    )


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
    def test_code_changes_require_current_update(self) -> None:
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
            self.assertIn("meta/tasks/CURRENT.md was not updated", out)

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
                    "meta/tasks/CURRENT.md",
                    "meta/reports/LAST.md",
                ],
            )

            rc, out = _run_main(module)
            self.assertEqual(rc, 0)
            self.assertIn("[workflow_checks] ok", out)


if __name__ == "__main__":
    unittest.main()
