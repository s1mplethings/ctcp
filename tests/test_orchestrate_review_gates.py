#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import ctcp_orchestrate


def _write_json(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _prepare_until_reviews(run_dir: Path) -> None:
    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"
    artifacts.mkdir(parents=True, exist_ok=True)
    reviews.mkdir(parents=True, exist_ok=True)
    (artifacts / "guardrails.md").write_text(
        "\n".join(
            [
                "find_mode: resolver_only",
                "max_files: 20",
                "max_total_bytes: 200000",
                "max_iterations: 3",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (artifacts / "analysis.md").write_text("# analysis\n", encoding="utf-8")
    _write_json(
        artifacts / "find_result.json",
        {
            "schema_version": "ctcp-find-result-v1",
            "selected_workflow_id": "wf_orchestrator_only",
        },
    )
    _write_json(
        artifacts / "file_request.json",
        {
            "schema_version": "ctcp-file-request-v1",
            "goal": "review gate test",
            "needs": [],
            "budget": {"max_files": 5, "max_total_bytes": 50000},
            "reason": "test",
        },
    )
    _write_json(
        artifacts / "context_pack.json",
        {
            "schema_version": "ctcp-context-pack-v1",
            "goal": "review gate test",
            "repo_slug": "ctcp",
            "summary": "test",
            "files": [],
            "omitted": [],
        },
    )
    (artifacts / "PLAN_draft.md").write_text("Status: DRAFT\n", encoding="utf-8")


class OrchestrateReviewGateTests(unittest.TestCase):
    def test_invalid_contract_review_routes_to_contract_guardian(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            _prepare_until_reviews(run_dir)
            (run_dir / "reviews" / "review_contract.md").write_text("# invalid\n", encoding="utf-8")
            (run_dir / "reviews" / "review_cost.md").write_text("Verdict: APPROVE\n", encoding="utf-8")

            gate = ctcp_orchestrate.current_gate(run_dir, {"goal": "test"})
            self.assertEqual(gate.get("owner"), "Contract Guardian")
            self.assertEqual(gate.get("path"), "reviews/review_contract.md")

    def test_invalid_cost_review_routes_to_cost_controller(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            _prepare_until_reviews(run_dir)
            (run_dir / "reviews" / "review_contract.md").write_text("Verdict: APPROVE\n", encoding="utf-8")
            (run_dir / "reviews" / "review_cost.md").write_text("# invalid\n", encoding="utf-8")

            gate = ctcp_orchestrate.current_gate(run_dir, {"goal": "test"})
            self.assertEqual(gate.get("owner"), "Cost Controller")
            self.assertEqual(gate.get("path"), "reviews/review_cost.md")


if __name__ == "__main__":
    unittest.main()

