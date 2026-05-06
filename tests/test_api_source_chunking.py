from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from llm_core.providers import api_source_chunking


class ApiSourceChunkingTests(unittest.TestCase):
    def test_batch_prompt_carries_interface_contract(self) -> None:
        interfaces = {
            "project_output/vn/src/vn/editor/__init__.py": {"defines": [], "imports": ["EditorActions"], "exports": ["EditorActions"]},
            "project_output/vn/src/vn/editor/actions.py": {"defines": ["EditorActions"], "imports": [], "exports": ["EditorActions"]},
        }

        prompt = api_source_chunking._batch_prompt(
            "base prompt",
            ["project_output/vn/src/vn/editor/actions.py"],
            1,
            1,
            interfaces,
        )

        self.assertIn("global Python interface contract", prompt)
        self.assertIn("EditorActions", prompt)
        self.assertIn("project_output/vn/src/vn/editor/actions.py", prompt)


if __name__ == "__main__":
    unittest.main()
