#!/usr/bin/env python3
from __future__ import annotations

import unittest

from scripts.worktree_cleanliness_report import (
    build_report,
    classify_path,
    parse_status_line,
    status_kind,
)


class WorktreeCleanlinessReportTests(unittest.TestCase):
    def test_parse_untracked_status_line(self) -> None:
        entry = parse_status_line("?? scripts/new_helper.py")
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.status_code, "??")
        self.assertEqual(entry.path, "scripts/new_helper.py")
        self.assertEqual(status_kind(entry), "untracked")

    def test_parse_rename_status_line_uses_new_path(self) -> None:
        entry = parse_status_line("R  docs/old.md -> docs/new.md")
        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.original_path, "docs/old.md")
        self.assertEqual(entry.path, "docs/new.md")
        self.assertEqual(status_kind(entry), "staged")

    def test_classifies_action_buckets(self) -> None:
        self.assertEqual(classify_path("scripts/tool.py"), "source_or_test_change")
        self.assertEqual(classify_path("tests/test_tool.py"), "source_or_test_change")
        self.assertEqual(classify_path("docs/cleanup_policy.md"), "docs_contract_or_workflow_change")
        self.assertEqual(classify_path("meta/tasks/archive/20260506-task.md"), "task_report_archive")
        self.assertEqual(classify_path("meta/reports/LAST.md"), "task_report_meta")
        self.assertEqual(classify_path("simlab/_runs/run-1/out.json"), "runtime_or_generated_output")

    def test_build_report_counts_categories_and_status_kinds(self) -> None:
        report = build_report(
            [
                " M docs/cleanup_policy.md",
                "?? scripts/worktree_cleanliness_report.py",
                "?? meta/tasks/archive/20260506-task.md",
                "?? simlab/_runs/run-1/out.json",
            ]
        )
        self.assertEqual(report["total_dirty"], 4)
        self.assertEqual(report["category_counts"]["docs_contract_or_workflow_change"], 1)
        self.assertEqual(report["category_counts"]["source_or_test_change"], 1)
        self.assertEqual(report["category_counts"]["task_report_archive"], 1)
        self.assertEqual(report["category_counts"]["runtime_or_generated_output"], 1)
        self.assertEqual(report["status_counts"]["modified_unstaged"], 1)
        self.assertEqual(report["status_counts"]["untracked"], 3)
        self.assertEqual(report["runtime_output_count"], 1)


if __name__ == "__main__":
    unittest.main()
