#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import contrast_rules


class ContrastRulesTests(unittest.TestCase):
    def test_doc_fail_classification(self) -> None:
        result = contrast_rules.classify_verify(
            rc=1,
            stdout="[verify_repo] doc index check (sync doc links --check)\n[sync_doc_links][error] out of sync",
            stderr="",
        )
        self.assertEqual(result["label"], "DOC_FAIL")

    def test_import_fail_classification(self) -> None:
        result = contrast_rules.classify_verify(
            rc=1,
            stdout="",
            stderr="ModuleNotFoundError: No module named 'foo'",
        )
        self.assertEqual(result["label"], "PY_IMPORT_FAIL")

    def test_unknown_classification(self) -> None:
        result = contrast_rules.classify_verify(
            rc=2,
            stdout="random failure text",
            stderr="no known gate keyword",
        )
        self.assertEqual(result["label"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()

