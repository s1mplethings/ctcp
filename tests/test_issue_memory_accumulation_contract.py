from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from _issue_memory import append_index, write_latest


FIXTURE_PATH = ROOT / "tests" / "fixtures" / "triplet_guard" / "issue_memory_cases.json"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        text = raw.strip()
        if not text:
            continue
        out.append(json.loads(text))
    return out


class IssueMemoryAccumulationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def _capture(self, repo: Path, issue_doc: dict) -> None:
        write_latest(repo, issue_doc)
        append_index(repo, issue_doc)

    def test_user_visible_failure_is_captured(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_issue_memory_capture_") as td:
            repo = Path(td)
            issue_doc = dict(self.fixture["user_visible_failure"])
            self._capture(repo, issue_doc)

            latest_json = _read_json(repo / "issue_memory" / "errors" / "latest.json")
            latest_md = repo / "issue_memory" / "errors" / "latest.md"
            index_path = repo / "issue_memory" / "errors" / "index.jsonl"
            index_rows = _read_jsonl(index_path)

            self.assertTrue(latest_md.exists())
            self.assertEqual(len(index_rows), 1)
            self.assertEqual(str(latest_json.get("issue_key", "")), "frontend.greeting_misroute.project_mode")

            failures = latest_json.get("failures", [])
            self.assertTrue(isinstance(failures, list) and failures, msg=latest_json)
            row = failures[0]
            for required_key in (
                "symptom",
                "likely_trigger",
                "affected_entrypoint",
                "expected_behavior",
            ):
                self.assertTrue(str(row.get(required_key, "")).strip(), msg=f"missing key: {required_key}")

    def test_repeated_failure_accumulates_or_updates(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_issue_memory_recur_") as td:
            repo = Path(td)
            first = dict(self.fixture["repeated_failure_first"])
            second = dict(self.fixture["repeated_failure_second"])
            self._capture(repo, first)
            self._capture(repo, second)

            index_rows = _read_jsonl(repo / "issue_memory" / "errors" / "index.jsonl")
            same_issue = [row for row in index_rows if str(row.get("issue_key", "")) == "frontend.internal_error_leakage.guard"]

            self.assertGreaterEqual(len(same_issue), 2, msg=index_rows)
            latest = same_issue[-1]
            self.assertGreaterEqual(int(latest.get("recurrence_count", 0) or 0), 2)

    def test_post_fix_state_is_reflected_in_latest_issue_record(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_issue_memory_post_fix_") as td:
            repo = Path(td)
            before_fix = dict(self.fixture["post_fix_failure"])
            after_fix = dict(self.fixture["post_fix_verified"])
            self._capture(repo, before_fix)
            self._capture(repo, after_fix)

            latest = _read_json(repo / "issue_memory" / "errors" / "latest.json")
            index_rows = _read_jsonl(repo / "issue_memory" / "errors" / "index.jsonl")

            self.assertTrue(bool(latest.get("pass", False)), msg=latest)
            self.assertGreaterEqual(len(index_rows), 2)
            latest_failures = latest.get("failures", [])
            self.assertTrue(latest_failures, msg=latest)
            last_row = latest_failures[0]
            self.assertEqual(str(last_row.get("fix_attempt_status", "")), "applied")
            self.assertEqual(str(last_row.get("regression_test_status", "")), "passing")


if __name__ == "__main__":
    unittest.main()
