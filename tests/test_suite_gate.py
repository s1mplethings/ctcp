#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.checks import suite_gate


class SuiteGateTests(unittest.TestCase):
    def _base_doc(self) -> dict[str, object]:
        return {
            "suite": {
                "id": "test-suite",
                "title": "Test Suite",
                "tier": "live",
                "env_gate": {},
            }
        }

    def test_load_doc_reads_json_payload(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            suite_path = Path(td) / "suite.live.yaml"
            suite_path.write_text(
                '{"suite":{"id":"json-suite","env_gate":{"required_env":["A"]}}}',
                encoding="utf-8",
            )
            doc = suite_gate._load_doc(suite_path)
        self.assertEqual(doc["suite"]["id"], "json-suite")

    def test_required_env_string_is_supported(self) -> None:
        doc = self._base_doc()
        doc["suite"]["env_gate"] = {"required_env": "OPENAI_API_KEY"}
        result = suite_gate.evaluate_suite_gate(
            doc,
            {"OPENAI_API_KEY": "x"},
            suite_file="tests/fixtures/local.live.yaml",
        )
        self.assertTrue(result["ready"])
        self.assertEqual(result["required_env"], ["OPENAI_API_KEY"])
        self.assertEqual(result["suite_file"], "tests/fixtures/local.live.yaml")

    def test_missing_required_env_returns_skip(self) -> None:
        doc = self._base_doc()
        doc["suite"]["env_gate"] = {"required_env": ["A", "B"]}
        result = suite_gate.evaluate_suite_gate(doc, {"A": "set"})
        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "skip")
        self.assertIn("missing required env: B", result["reasons"])

    def test_network_gate_reason_when_allow_list_missing(self) -> None:
        doc = self._base_doc()
        doc["suite"]["env_gate"] = {"require_network": True, "allow_network_env": []}
        result = suite_gate.evaluate_suite_gate(doc, {})
        self.assertFalse(result["ready"])
        self.assertIn("allow_network_env is empty", "\n".join(result["reasons"]))

    def test_network_gate_passes_when_flag_enabled(self) -> None:
        doc = self._base_doc()
        doc["suite"]["env_gate"] = {
            "require_network": True,
            "allow_network_env": ["CTCP_ALLOW_NETWORK"],
        }
        result = suite_gate.evaluate_suite_gate(doc, {"CTCP_ALLOW_NETWORK": "true"})
        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "pass")
        self.assertTrue(result["network_allowed"])


if __name__ == "__main__":
    unittest.main()
