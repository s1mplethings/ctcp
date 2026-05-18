from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

from tools.agent_manifest_consumer import generate_agent_scaffold


ROOT = Path(__file__).resolve().parents[1]
H1_MANIFEST = ROOT / "tests" / "agent_factory_benchmark" / "holdout_generated" / "output_h1_personal_productivity.json"


class WebToolRuntimePolicyTests(unittest.TestCase):
    def _policy_module(self) -> tuple[ModuleType, tempfile.TemporaryDirectory[str], Path]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_web_policy_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(H1_MANIFEST, out)
        sys.path.insert(0, str(out))
        self.addCleanup(lambda: sys.path.remove(str(out)) if str(out) in sys.path else None)
        self.addCleanup(td.cleanup)
        for key in list(sys.modules):
            if key == "runtime" or key.startswith("runtime."):
                sys.modules.pop(key, None)
        return importlib.import_module("runtime.runtime_tool_policy"), td, out

    def _web_tool(self, **overrides: object) -> dict[str, object]:
        tool: dict[str, object] = {
            "tool_name": "web_search",
            "description": "Search public web documents.",
            "side_effect_level": "none",
            "requires_approval": False,
            "allowed_callers": ["research_agent"],
            "audit_log_required": True,
            "runtime_adapter": "web_search",
        }
        tool.update(overrides)
        return tool

    def test_default_agent_cannot_web_search(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("CoordinatorAgent", self._web_tool(), "run", {})
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["reason"], "web_permission_denied")

    def test_research_agent_manifest_web_search_can_pass_policy(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("research_agent", self._web_tool(), "run", {})
        self.assertEqual(decision["status"], "executed")

    def test_web_permission_denied_conditions(self) -> None:
        policy, _td, _out = self._policy_module()
        cases = [
            self._web_tool(allowed_callers=["OtherAgent"]),
            self._web_tool(audit_log_required=False),
            self._web_tool(requires_approval=True),
            self._web_tool(side_effect_level="low"),
        ]
        for tool in cases:
            with self.subTest(tool=tool):
                decision = policy.can_execute_tool("research_agent", tool, "run", {})
                self.assertEqual(decision["status"], "blocked")
                self.assertEqual(decision["reason"], "web_permission_denied")

    def test_fetch_url_requires_manifest_authorization(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("research_agent", {"tool_name": "fetch_url", "runtime_adapter": "fetch_url"}, "run", {})
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["reason"], "web_permission_denied")

    def test_unknown_web_like_tool_is_unsupported(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool(
            "research_agent",
            {
                "tool_name": "web_lookup",
                "description": "Looks like web but is not supported.",
                "side_effect_level": "none",
                "requires_approval": False,
                "allowed_callers": ["research_agent"],
                "audit_log_required": True,
            },
            "run",
            {},
        )
        self.assertEqual(decision["status"], "unsupported")

    def test_dry_run_does_not_execute_web_tool(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("research_agent", self._web_tool(), "dry-run", {})
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["reason"], "dry_run_never_executes")


if __name__ == "__main__":
    unittest.main()
