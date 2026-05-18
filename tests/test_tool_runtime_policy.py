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


class ToolRuntimePolicyTests(unittest.TestCase):
    def _policy_module(self) -> tuple[ModuleType, tempfile.TemporaryDirectory[str], Path]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_tool_policy_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(H1_MANIFEST, out)
        sys.path.insert(0, str(out))
        self.addCleanup(lambda: sys.path.remove(str(out)) if str(out) in sys.path else None)
        self.addCleanup(td.cleanup)
        for key in list(sys.modules):
            if key == "runtime" or key.startswith("runtime."):
                sys.modules.pop(key, None)
        return importlib.import_module("runtime.runtime_tool_policy"), td, out

    def _tool(self, **overrides: object) -> dict[str, object]:
        tool: dict[str, object] = {
            "tool_name": "classify_input",
            "description": "Classify local input",
            "side_effect_level": "none",
            "requires_approval": False,
            "allowed_callers": ["CoordinatorAgent"],
            "audit_log_required": True,
        }
        tool.update(overrides)
        return tool

    def test_dry_run_never_executes(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("CoordinatorAgent", self._tool(), "dry-run", {})
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["reason"], "dry_run_never_executes")

    def test_requires_approval_enters_pending_approval(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("CoordinatorAgent", self._tool(requires_approval=True), "run", {})
        self.assertEqual(decision["status"], "pending_approval")
        self.assertEqual(decision["reason"], "requires_approval")

    def test_medium_or_high_side_effect_does_not_execute(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("CoordinatorAgent", self._tool(side_effect_level="medium"), "run", {})
        self.assertEqual(decision["status"], "pending_approval")

    def test_allowed_callers_mismatch_blocked(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("CoordinatorAgent", self._tool(allowed_callers=["OtherAgent"]), "run", {})
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["reason"], "permission_denied")

    def test_prohibited_actions_are_blocked(self) -> None:
        policy, _td, _out = self._policy_module()
        for phrase in ("rollback production", "refund customer", "legal admission"):
            with self.subTest(phrase=phrase):
                decision = policy.can_execute_tool("CoordinatorAgent", self._tool(description=phrase), "run", {})
                self.assertEqual(decision["status"], "blocked")
                self.assertEqual(decision["reason"], "prohibited_action")

    def test_audit_disabled_on_risky_tool_is_invalid_contract(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool(
            "CoordinatorAgent",
            self._tool(tool_name="urgent_symptom.screen", side_effect_level="medium", audit_log_required=False),
            "run",
            {},
        )
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["reason"], "invalid_tool_contract")

    def test_unknown_adapter_is_unsupported(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("CoordinatorAgent", self._tool(tool_name="unknown.local", side_effect_level="low"), "run", {})
        self.assertEqual(decision["status"], "unsupported")
        self.assertEqual(decision["reason"], "unsupported_tool")

    def test_missing_fields_safe_default_to_blocked(self) -> None:
        policy, _td, _out = self._policy_module()
        decision = policy.can_execute_tool("CoordinatorAgent", {"tool_name": "unknown.synthetic"}, "run", {})
        self.assertEqual(decision["status"], "blocked")
        self.assertEqual(decision["reason"], "invalid_tool_contract")


if __name__ == "__main__":
    unittest.main()
