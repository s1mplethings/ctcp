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


class ToolRuntimeRegistryTests(unittest.TestCase):
    def _runtime_module(self, name: str) -> tuple[ModuleType, tempfile.TemporaryDirectory[str], Path]:
        td = tempfile.TemporaryDirectory(prefix="ctcp_tool_registry_")
        out = Path(td.name) / "scaffold"
        generate_agent_scaffold(H1_MANIFEST, out)
        sys.path.insert(0, str(out))
        self.addCleanup(lambda: sys.path.remove(str(out)) if str(out) in sys.path else None)
        self.addCleanup(td.cleanup)
        for key in list(sys.modules):
            if key == "runtime" or key.startswith("runtime."):
                sys.modules.pop(key, None)
        return importlib.import_module(name), td, out

    def test_manifest_tool_normalization_with_full_fields(self) -> None:
        registry, _td, _out = self._runtime_module("runtime.runtime_tool_registry")
        tool = registry.normalize_tool_contract(
            {
                "tool_name": "create_draft",
                "description": "Create local draft",
                "side_effect_level": "low",
                "requires_approval": False,
                "allowed_callers": ["CoordinatorAgent"],
                "audit_log_required": True,
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "runtime_adapter": "local_deterministic",
                "adapter_name": "create_draft",
            }
        )
        self.assertEqual(tool["runtime_adapter"], "local_deterministic")
        self.assertEqual(tool["adapter_name"], "create_draft")
        self.assertFalse(tool["requires_approval"])

    def test_missing_fields_default_to_high_risk_unsupported(self) -> None:
        registry, _td, _out = self._runtime_module("runtime.runtime_tool_registry")
        tool = registry.normalize_tool_contract({"tool_name": "unknown"})
        self.assertEqual(tool["side_effect_level"], "high")
        self.assertTrue(tool["requires_approval"])
        self.assertTrue(tool["audit_log_required"])
        self.assertEqual(tool["runtime_adapter"], "unsupported")

    def test_known_local_adapter_executes_exact_name(self) -> None:
        registry, _td, _out = self._runtime_module("runtime.runtime_tool_registry")
        tool = registry.normalize_tool_contract({"tool_name": "extract_fields", "side_effect_level": "none", "requires_approval": False})
        adapter = registry.get_adapter(tool)
        self.assertIsNotNone(adapter)
        output = adapter.execute({"request": "capture quarterly planning tasks"}, {"tool_name": "extract_fields"})
        self.assertEqual(output["adapter"], "extract_fields")

    def test_near_match_tool_is_not_guessed(self) -> None:
        registry, _td, _out = self._runtime_module("runtime.runtime_tool_registry")
        tool = registry.normalize_tool_contract({"tool_name": "extract_field", "side_effect_level": "none", "requires_approval": False})
        self.assertEqual(tool["runtime_adapter"], "unsupported")
        self.assertIsNone(registry.get_adapter(tool))


if __name__ == "__main__":
    unittest.main()
