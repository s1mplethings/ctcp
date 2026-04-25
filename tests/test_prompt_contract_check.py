#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "prompt_contract_check.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("prompt_contract_check_for_test", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load scripts/prompt_contract_check.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_valid_fixture(repo: Path) -> None:
    _write(
        repo / "AGENTS.md",
        "\n".join(
            [
                "## 2. Work Lanes",
                "### Delivery Lane",
                "### Virtual Team Lane",
                "Implementation entry gate for Virtual Team Lane:",
                "Do not treat Virtual Team Lane as optional styling.",
            ]
        ),
    )
    _write(
        repo / "docs" / "12_virtual_team_contract.md",
        "\n".join(
            [
                "## 2) Trigger Conditions",
                "## 3) Team Roles and Boundaries",
                "### 3.1 Product Lead",
                "### 3.3 Solution Architect",
                "## 4) Mandatory Team-Design Artifacts",
                "## 5) Design-to-Implementation Gate",
                "## 6) Forbidden Shortcuts",
                "## 8) Completion Standard",
            ]
        ),
    )
    _write(
        repo / "docs" / "10_team_mode.md",
        "\n".join(
            [
                "- `PROMPT.md`: compiled prompt derived from `AGENTS.md`, routed contracts, and `meta/tasks/CURRENT.md`.",
                "- support bot only consumes get_support_context + get_current_state_snapshot + get_render_state_snapshot for customer-facing truth.",
            ]
        ),
    )
    _write(
        repo / "docs" / "50_prompt_hierarchy_contract.md",
        "\n".join(
            [
                "AGENTS.md is the root contract.",
                "Source order includes meta/tasks/CURRENT.md.",
                "PROMPT.md is a compiled/derived artifact.",
                "Compiled prompts must not override the root contract or introduce new top-level rules.",
            ]
        ),
    )
    _write(
        repo / "agents" / "prompts" / "chair_plan_draft.md",
        "\n".join(
            [
                "You are CTCP's Chair/Planner for lane judgment and team-stage orchestration.",
                "- Lane: DELIVERY|VIRTUAL_TEAM",
                "- Stop: max_iterations=3",
                "### Product Direction",
                "### Architecture Direction",
                "### UX Flow",
                "### Role Handoff",
                "### Acceptance Matrix",
            ]
        ),
    )
    _write(
        repo / "docs" / "04_execution_flow.md",
        "\n".join(
            [
                "Formal work-lane split:",
                "- lane selection must be recorded before implementation work starts",
                "- if `Virtual Team Lane` is selected, required design artifacts must exist before implementation",
                "### Project Generation Fixed Subflow (Virtual Team Path)",
                "- `product_brief`, `interaction_design`, and `technical_plan` must all complete before `implementation`.",
            ]
        ),
    )
    _write(
        repo / "docs" / "11_task_progress_dialogue.md",
        "\n".join(
            [
                "- `current_lane`",
                "- `active_role`",
                "- `updated_artifacts`",
                "- `pending_decisions`",
                "### 4.3A Virtual Team Lane Progress",
            ]
        ),
    )
    _write(
        repo / "docs" / "14_persona_test_lab.md",
        "\n".join(
            [
                "- It does not redefine CTCP's Virtual Team Lane role model; that remains in `docs/12_virtual_team_contract.md`.",
                "- not the runtime role hierarchy itself; CTCP may legitimately use a Virtual Team Lane role model in production",
            ]
        ),
    )


def _run_main(module, *argv: str) -> tuple[int, str]:
    stream = io.StringIO()
    with redirect_stdout(stream):
        rc = int(module.main(list(argv)))
    return rc, stream.getvalue()


class PromptContractCheckTests(unittest.TestCase):
    def test_repo_prompt_contracts_pass(self) -> None:
        module = _load_module()
        rc, out = _run_main(module, "--root", str(ROOT))
        self.assertEqual(rc, 0)
        self.assertIn("[prompt_contract_check] SUMMARY", out)
        self.assertIn("failed=0", out)

    def test_missing_virtual_team_contract_file_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_prompt_contract_missing_") as td:
            repo = Path(td)
            _write_valid_fixture(repo)
            (repo / "docs" / "12_virtual_team_contract.md").unlink()

            module = _load_module()
            rc, out = _run_main(module, "--root", str(repo))
            self.assertNotEqual(rc, 0)
            self.assertIn("docs/12_virtual_team_contract.md", out)
            self.assertIn("file_missing", out)

    def test_patch_first_phrase_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_prompt_contract_patch_first_") as td:
            repo = Path(td)
            _write_valid_fixture(repo)
            _write(
                repo / "agents" / "prompts" / "chair_plan_draft.md",
                "\n".join(
                    [
                        "You are a patch-first coding agent.",
                        "- Lane: DELIVERY|VIRTUAL_TEAM",
                        "- Stop: max_iterations=3",
                        "### Product Direction",
                        "### Architecture Direction",
                        "### UX Flow",
                        "### Role Handoff",
                        "### Acceptance Matrix",
                    ]
                ),
            )

            module = _load_module()
            rc, out = _run_main(module, "--root", str(repo))
            self.assertNotEqual(rc, 0)
            self.assertIn("chair_not_patch_first", out)
            self.assertIn("forbidden marker present", out)

    def test_team_mode_unique_prompt_entry_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_prompt_contract_unique_prompt_") as td:
            repo = Path(td)
            _write_valid_fixture(repo)
            _write(
                repo / "docs" / "10_team_mode.md",
                "- `PROMPT.md`：给 coding agent 的输入（唯一入口）\n",
            )

            module = _load_module()
            rc, out = _run_main(module, "--root", str(repo))
            self.assertNotEqual(rc, 0)
            self.assertIn("team_mode_prompt_not_unique_entry", out)

    def test_missing_prompt_hierarchy_doc_fails(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_prompt_contract_missing_hierarchy_") as td:
            repo = Path(td)
            _write_valid_fixture(repo)
            (repo / "docs" / "50_prompt_hierarchy_contract.md").unlink()

            module = _load_module()
            rc, out = _run_main(module, "--root", str(repo))
            self.assertNotEqual(rc, 0)
            self.assertIn("docs/50_prompt_hierarchy_contract.md", out)


if __name__ == "__main__":
    unittest.main()
