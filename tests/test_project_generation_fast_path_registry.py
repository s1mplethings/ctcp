from __future__ import annotations

import unittest

from tools.providers.project_generation_fast_path_registry import detect_fast_path, fast_path_defaults, fast_path_provenance, registered_fast_path_ids


class ProjectGenerationFastPathRegistryTests(unittest.TestCase):
    def test_registry_dispatches_known_fast_paths(self) -> None:
        cases = {
            "local_issue_tracker_api": "Build issue tracker with sqlite POST /issues GET /issues PATCH /issues/{id}/status POST /issues/{id}/close",
            "todo_rest_api": "Build todo api POST /todos GET /todos PATCH /todos/{id} DELETE /todos/{id}",
            "markdown_notes_api": "Build markdown notes api POST /notes GET /notes PATCH /notes/{id} DELETE /notes/{id} GET /search",
            "simple_auth_api": "Build simple auth api POST /register POST /login GET /me POST /logout",
            "local_task_board_app": "Build full-stack task board frontend POST /api/tasks GET /api/tasks PATCH /api/tasks static frontend",
            "local_kanban_board_app": "Build full-stack kanban frontend POST /boards POST /boards/{board_id}/cards PATCH /cards/{card_id}/move cards CRUD",
            "csv_expense_analyzer": "Generate a CSV Expense Analyzer CLI with --input --output sample_expenses.csv category totals monthly totals",
            "log_analyzer_cli": "Generate a log analyzer CLI to parse log lines info/warn/error --input --output sample.log top error messages",
            "text_utils_package": "Generate a text utilities python package with slugify word_count extract_keywords normalize_whitespace",
            "terminal_quiz_game": "Generate a terminal quiz game with question loading --questions --answers sample_questions.json test-mode",
        }
        for expected, goal in cases.items():
            with self.subTest(expected=expected):
                match = detect_fast_path(goal)
                self.assertIsNotNone(match)
                self.assertEqual(match.project_id, expected)
                self.assertEqual(fast_path_defaults(expected)["generation_mode"], "concrete_fast_path")
                self.assertTrue(fast_path_provenance(expected)["local_materializer_used"])

    def test_registered_ids_include_phase_14_kanban(self) -> None:
        ids = registered_fast_path_ids()
        self.assertIn("local_kanban_board_app", ids)
        self.assertIn("local_task_board_app", ids)
        self.assertIn("simple_auth_api", ids)
        self.assertIn("csv_expense_analyzer", ids)
        self.assertIn("log_analyzer_cli", ids)
        self.assertIn("text_utils_package", ids)
        self.assertIn("terminal_quiz_game", ids)

    def test_kanban_fast_path_requires_kanban_goal(self) -> None:
        match = detect_fast_path(
            "Build a full-stack local app with a static frontend and saved cards, but no kanban board or card move workflow."
        )
        self.assertTrue(match is None or match.project_id != "local_kanban_board_app")


if __name__ == "__main__":
    unittest.main()
