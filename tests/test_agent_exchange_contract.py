#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ctcp_adapters import dispatch_whiteboard
from tools.providers import api_agent


class AgentExchangeContractTests(unittest.TestCase):
    def test_dispatch_whiteboard_persists_sanitized_agent_exchange(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)

            request = {
                "role": "solution_architect",
                "action": "architecture_decision",
                "target_path": "artifacts/architecture_decision.md",
                "reason": "handoff to UX",
                "goal": "optimize agent generation flow",
                "agent_exchange": {
                    "schema_version": "ctcp-agent-exchange-v1",
                    "lane": "virtual_team",
                    "stage": "architecture",
                    "role": "solution_architect",
                    "goal": "optimize agent generation flow",
                    "input_refs": ["docs/12_virtual_team_contract.md"],
                    "context_needs": [
                        {
                            "kind": "repo",
                            "query": "dispatch whiteboard prompt handoff",
                            "reason": "next role needs current dispatch context path",
                            "budget": {"max_files": 4, "max_total_bytes": 8000},
                        }
                    ],
                    "decisions": ["Use dispatch whiteboard as the first transport."],
                    "open_questions": ["Later broker may materialize context_needs."],
                    "risks": ["Do not let packet bloat prompt context."],
                    "handoff": {
                        "next_role": "ux_designer",
                        "next_required_artifact": "ux_flow.md",
                        "must_preserve": ["run_dir remains runtime truth"],
                        "must_not_do": ["do not add provider credentials"],
                    },
                    "acceptance_hooks": ["prompt contains AGENT_EXCHANGE"],
                    "evidence": ["artifacts/support_whiteboard.json"],
                    "ignored_object": {"nested": "not rendered as raw object"},
                },
            }

            with mock.patch.object(dispatch_whiteboard.local_librarian, "search", return_value=[]):
                context = dispatch_whiteboard.prepare_dispatch_whiteboard_context(
                    run_dir=run_dir,
                    repo_root=repo_root,
                    request=request,
                )

            exchange = context.get("agent_exchange")
            self.assertIsInstance(exchange, dict)
            self.assertEqual(exchange.get("schema_version"), "ctcp-agent-exchange-v1")
            self.assertEqual(exchange.get("stage"), "architecture")
            self.assertIn("decisions", exchange)
            self.assertNotIn("ignored_object", exchange)
            self.assertEqual(dict(exchange.get("handoff", {})).get("next_role"), "ux_designer")

            board = json.loads((run_dir / "artifacts" / "support_whiteboard.json").read_text(encoding="utf-8"))
            entries = board.get("entries", [])
            exchange_entries = [
                row for row in entries
                if isinstance(row, dict) and row.get("kind") == "agent_exchange"
            ]
            self.assertEqual(len(exchange_entries), 1)
            self.assertEqual(dict(exchange_entries[0].get("agent_exchange", {})).get("role"), "solution_architect")
            snapshot_entries = dict(context.get("snapshot", {})).get("entries", [])
            self.assertTrue(
                [
                    row for row in snapshot_entries
                    if isinstance(row, dict) and row.get("kind") == "agent_exchange"
                ]
            )

    def test_api_agent_prompt_consumes_agent_exchange_packet(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)

            evidence: dict[str, Path] = {}
            for key in ("context", "constraints", "fix_brief", "externals"):
                path = run_dir / f"{key.upper()}.md"
                path.write_text(f"# {key}\n- sample\n", encoding="utf-8")
                evidence[key] = path

            prompt = api_agent._render_prompt(
                run_dir=run_dir,
                repo_root=repo_root,
                request={
                    "role": "solution_architect",
                    "action": "architecture_decision",
                    "goal": "optimize agent flow",
                    "target_path": "artifacts/architecture_decision.md",
                    "agent_exchange": {
                        "schema_version": "ctcp-agent-exchange-v1",
                        "lane": "virtual_team",
                        "stage": "architecture",
                        "role": "solution_architect",
                        "goal": "optimize agent flow",
                        "context_needs": [
                            {
                                "kind": "repo",
                                "query": "dispatch whiteboard prompt handoff",
                                "reason": "next role needs current prompt injection rules",
                                "budget": {"max_files": 6, "max_total_bytes": 12000},
                            }
                        ],
                        "decisions": ["Use dispatch whiteboard as packet transport."],
                        "handoff": {
                            "next_role": "ux_designer",
                            "next_required_artifact": "ux_flow.md",
                            "must_preserve": ["run_dir artifacts remain runtime truth"],
                            "must_not_do": ["do not add live API calls"],
                        },
                        "acceptance_hooks": ["prompt contains AGENT_EXCHANGE"],
                    },
                },
                evidence=evidence,
            )

            self.assertIn("# AGENT_EXCHANGE", prompt)
            self.assertIn("ctcp-agent-exchange-v1", prompt)
            self.assertIn("virtual_team", prompt)
            self.assertIn("Use dispatch whiteboard as packet transport.", prompt)
            self.assertIn("dispatch whiteboard prompt handoff", prompt)
            self.assertIn('"max_files": 6', prompt)
            self.assertIn("next_role: `ux_designer`", prompt)
            self.assertIn("do not add live API calls", prompt)


if __name__ == "__main__":
    unittest.main()
