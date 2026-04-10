#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.dispatch import result as new_result
from tools import dispatch_result_contract as old_result


class LlmCoreDispatchResultTests(unittest.TestCase):
    def test_provider_mode_mapping_is_stable(self) -> None:
        self.assertEqual(new_result.provider_mode("ollama_agent"), "local")
        self.assertEqual(new_result.provider_mode("api_agent"), "remote")
        self.assertEqual(new_result.provider_mode("manual_outbox"), "manual")
        self.assertEqual(new_result.provider_mode("mock_agent"), "mock")
        self.assertEqual(new_result.provider_mode("unknown_provider"), "unknown")

    def test_normalize_dispatch_result_downgrades_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            result = new_result.normalize_dispatch_result(
                run_dir=run_dir,
                request={"target_path": "artifacts/PLAN_draft.md"},
                result={"status": "executed"},
            )
        self.assertEqual(result["status"], "exec_failed")
        self.assertEqual(result["error_code"], "target_missing")

    def test_old_shim_reexports_new_contract(self) -> None:
        payload = old_result.apply_dispatch_evidence(
            {},
            request={"role": "librarian", "action": "context_pack"},
            provider="api_agent",
            note="forced local",
        )
        self.assertEqual(payload["provider_mode"], "local")
        self.assertTrue(payload["fallback_blocked"])
        self.assertIs(old_result.normalize_dispatch_result, new_result.normalize_dispatch_result)


if __name__ == "__main__":
    unittest.main()
